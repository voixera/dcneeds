/*
 * Atomicals Bot for Discord
 * Copyright (C) 2026 Atomicals LancarJaya
 *
 * Licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License.
 * You may not use this file except in compliance with the License.
 * See the LICENSE file for more information.
 */

// - bypass link service - \\

import { config } from "dotenv"
import { get_pool } from "../../utils/database"

config()

function __get_bypass_api_key(): string {
  return process.env.BYPASS_API_KEY || ""
}

function __get_bypass_api_url(): string {
  return process.env.BYPASS_API_URL || ""
}

function __get_bypass_refresh_url(): string {
  const api_url = __get_bypass_api_url()
  return api_url ? api_url.replace("/bypass", "/refresh") : ""
}

function __is_direct_lookup_disabled(): boolean {
  return (process.env.BYPASS_DISABLE_DIRECT_LOOKUP || "").toLowerCase() === "true"
}

const __bypass_global_timeout  = 120000  // - safety net — 2 min max total wait - \\
export const bypass_max_retry  = 3
const __bypass_max_retry       = bypass_max_retry
const __bypass_retry_ms        = 5000    // - wait before each retry - \\
const __bypass_default_backoff = 15      // - default backoff seconds on 429 - \\
const __refresh_interval_ms    = 2000    // - poll /v1/refresh every 2s - \\
const __refresh_max_wait_ms    = 55000   // - max polling window for processing tasks - \\
const __platoboost_domains     = ["platorelay.com", "platoboost.com", "platoboost.app"]

// - url-based result cache ttl - \\
const __url_cache_ttl_minutes  = 30

/**
 * @description builds a stable cache key from a URL.
 * @param url - The URL to hash
 * @returns Cache key string
 */
function __url_cache_key(url: string): string {
  return `bypass_url_cache_${Buffer.from(url.trim()).toString('base64').replace(/[+/=]/g, '').slice(0, 64)}`
}

/**
 * @description checks bypass_cache table for a previously bypassed result for this URL.
 * @param url - The URL to look up
 * @returns Cached result string or null
 */
async function __get_url_cache(url: string): Promise<string | null> {
  try {
    const row = await get_pool().query<{ url: string }>(
      `SELECT url FROM bypass_cache WHERE key = $1 AND expires_at > NOW() LIMIT 1`,
      [__url_cache_key(url)]
    )
    return row.rows[0]?.url ?? null
  } catch {
    return null
  }
}

/**
 * @description stores a bypass result in cache keyed by URL.
 * @param url    - The original URL
 * @param result - The bypassed result to cache
 */
async function __set_url_cache(url: string, result: string): Promise<void> {
  try {
    await get_pool().query(
      `INSERT INTO bypass_cache (key, url, expires_at)
       VALUES ($1, $2, NOW() + INTERVAL '${__url_cache_ttl_minutes} minutes')
       ON CONFLICT (key) DO UPDATE SET url = $2, expires_at = NOW() + INTERVAL '${__url_cache_ttl_minutes} minutes'`,
      [__url_cache_key(url), result]
    )
  } catch (err) {
    console.error(`[ - BYPASS CACHE - ] failed to store url cache:`, err)
  }
}

// - sliding window request tracker - \\
const __request_timestamps: number[] = []
const __track_window_ms              = 10_000

function __record_request(): void {
  const now = Date.now()
  __request_timestamps.push(now)
  // - prune entries outside the window - \\
  const cutoff = now - __track_window_ms
  while (__request_timestamps.length > 0 && __request_timestamps[0] < cutoff) {
    __request_timestamps.shift()
  }
}

/**
 * @description returns current API request rate stats for the last 10 seconds.
 * @returns Object with count in window and timestamps array copy
 */
export function get_request_stats(): { requests_last_10s: number; timestamps: number[] } {
  const now    = Date.now()
  const cutoff = now - __track_window_ms
  const recent = __request_timestamps.filter(t => t >= cutoff)
  return {
    requests_last_10s : recent.length,
    timestamps        : [...recent],
  }
}

// - global backoff: pause entire queue when rate limited - \\
let __backoff_until: number = 0

function __set_global_backoff(seconds: number): void {
  const until = Date.now() + seconds * 1000
  if (until > __backoff_until) {
    __backoff_until = until
    const { requests_last_10s } = get_request_stats()
    console.warn(`[ - BYPASS - ] global backoff set for ${seconds}s until ${new Date(until).toISOString()} (requests last 10s: ${requests_last_10s})`)
  }
}

/** 
 * @description returns remaining global backoff in ms (0 if not active). 
 * @returns Remaining global backoff in ms
 */
function __get_backoff_remaining_ms(): number {
  return Math.max(0, __backoff_until - Date.now())
}

// - global rate limit queue - \\
let __bypass_queue: Promise<void> = Promise.resolve()
let __queue_length                = 0

async function __enqueue_bypass<T>(task: () => Promise<T>): Promise<T> {
  __queue_length++
  console.warn(`[ - BYPASS - ] enqueuing request. queue length: ${__queue_length}`)
  const current      = __bypass_queue
  let   resolve_next!: () => void
  __bypass_queue     = new Promise(resolve => {
    resolve_next = resolve
  })

  await current

  // - if task aborted while waiting in queue, skip it - \\
  if ((task as any).aborted) {
    __queue_length--
    console.warn(`[ - BYPASS - ] task aborted while in queue. queue length: ${__queue_length}`)
    resolve_next()
    return Promise.reject(new Error("Queue task aborted"))
  }

  // - honour global backoff before firing the next request - \\
  const backoff_wait = __backoff_until - Date.now()
  if (backoff_wait > 0) {
    console.warn(`[ - BYPASS - ] respecting global backoff, waiting ${backoff_wait}ms...`)
    await new Promise(resolve => setTimeout(resolve, backoff_wait))
  }

  try {
    __record_request()
    console.warn(`[ - BYPASS - ] executing task from queue. queue length: ${__queue_length}`)
    
    // - execute task but do not block queue indefinitely - \\
    const task_promise = task()
    
    // - release next item after 1 second to prevent bursting - \\
    setTimeout(() => {
      resolve_next()
    }, 1000)

    return await task_promise
  } finally {
    __queue_length--
    console.warn(`[ - BYPASS - ] task finished. queue length: ${__queue_length}`)
  }
}

interface BypassResponse {
  success          : boolean
  result?          : string
  error?           : string
  time?            : number
  attempts?        : number
  is_client_error? : boolean
  retry_after?     : number
  api_code?        : string
}

interface SupportedService {
  name    : string
  type    : string
  status  : string
  domains : string[]
}

function __parse_json_payload(payload: string): any {
  if (!payload) return {}

  try {
    return JSON.parse(payload)
  } catch {
    return { message: payload }
  }
}

function __is_platoboost_url(url: URL): boolean {
  const hostname = url.hostname.toLowerCase()
  return __platoboost_domains.some(domain => (
    hostname === domain || hostname.endsWith(`.${domain}`)
  ))
}

function __extract_platoboost_ticket(url: URL): string {
  const query_ticket = url.searchParams.get("d") || url.searchParams.get("ticket")
  if (query_ticket?.trim()) return query_ticket.trim()

  const path_parts = url.pathname.split("/").filter(Boolean)
  if (path_parts.length >= 2 && ["a", "b"].includes(path_parts[0].toLowerCase())) {
    return decodeURIComponent(path_parts[1]).trim()
  }

  if (path_parts.length === 1 && path_parts[0].length > 24) {
    return decodeURIComponent(path_parts[0]).trim()
  }

  return ""
}

function __extract_platoboost_mode(url: URL): "a" | "b" {
  const path_parts = url.pathname.split("/").filter(Boolean)
  return path_parts[0]?.toLowerCase() === "b" ? "b" : "a"
}

function __normalize_platoboost_host(hostname: string): string {
  const normalized_hostname = hostname.toLowerCase()

  if (normalized_hostname.startsWith("auth.")) {
    return normalized_hostname.slice(5)
  }

  if (normalized_hostname.startsWith("www.")) {
    return normalized_hostname.slice(4)
  }

  return normalized_hostname
}

function __build_provider_candidate_urls(url: string): string[] {
  const trimmed_url = url.trim()

  try {
    const parsed_url = new URL(trimmed_url)
    if (!__is_platoboost_url(parsed_url)) {
      return [trimmed_url]
    }

    const ticket = __extract_platoboost_ticket(parsed_url)
    if (!ticket) {
      return [trimmed_url]
    }

    const mode              = __extract_platoboost_mode(parsed_url)
    const encoded_ticket    = encodeURIComponent(ticket)
    const normalized_host   = __normalize_platoboost_host(parsed_url.hostname)
    const candidate_urls    = new Set<string>()

    candidate_urls.add(trimmed_url)
    candidate_urls.add(`${parsed_url.protocol}//${parsed_url.host}/${mode}/${encoded_ticket}`)
    candidate_urls.add(`${parsed_url.protocol}//${normalized_host}/${mode}/${encoded_ticket}`)
    candidate_urls.add(`${parsed_url.protocol}//${normalized_host}/${mode}?d=${encoded_ticket}`)
    candidate_urls.add(`${parsed_url.protocol}//${normalized_host}/${mode}?ticket=${encoded_ticket}`)

    return [...candidate_urls]
  } catch {
    return [trimmed_url]
  }
}

function __extract_platoboost_key(payload: any): string | null {
  const candidates = [
    payload?.key,
    payload?.result,
    payload?.data?.key,
    payload?.data?.result,
    payload?.status?.key,
    payload?.status?.result,
    payload?.session?.key,
    payload?.session?.result,
    payload?.metadata?.key,
    payload?.metadata?.result,
  ]

  for (const candidate of candidates) {
    if (typeof candidate !== "string") continue

    const value = candidate.trim()
    if (value && value !== "KEY_NOT_FOUND") {
      return value
    }
  }

  return null
}

function __normalize_platoboost_error(input: unknown): string {
  const message = typeof input === "string"
    ? input.trim()
    : typeof (input as any)?.message === "string"
      ? (input as any).message.trim()
      : ""

  if (!message) {
    return "Unable to reach Platoboost right now."
  }

  const lower_message = message.toLowerCase()

  if (
    lower_message.includes("\"exp\" claim timestamp check failed")
    || lower_message.includes("jwt expired")
    || lower_message.includes("token expired")
  ) {
    return "This Platoboost link has expired. Generate a fresh link and try again."
  }

  if (
    lower_message.includes("missing ticket")
    || lower_message.includes("invalid ticket")
    || lower_message.includes("malformed ticket")
  ) {
    return "Invalid Platoboost link - missing ticket."
  }

  if (
    lower_message.includes("session not found")
    || lower_message.includes("ticket not found")
  ) {
    return "Platoboost could not find a session for that ticket."
  }

  return message
}

function __is_platoboost_client_error(message?: string): boolean {
  if (!message) return false

  const lower_message = message.toLowerCase()
  return (
    lower_message.includes("expired")
    || lower_message.includes("invalid platoboost link")
    || lower_message.includes("missing ticket")
    || lower_message.includes("could not find a session")
  )
}

function __is_provider_unsupported_result(result: BypassResponse): boolean {
  const lower_error = result.error?.toLowerCase() || ""

  return (
    lower_error.includes("not supported")
    || lower_error.includes("unsupported")
    || lower_error.includes("invalid url")
  )
}

async function __try_platoboost_lookup(url: string, attempt: number): Promise<BypassResponse | null> {
  let parsed_url: URL

  try {
    parsed_url = new URL(url)
  } catch {
    return null
  }

  if (!__is_platoboost_url(parsed_url)) {
    return null
  }

  const ticket = __extract_platoboost_ticket(parsed_url)
  if (!ticket) {
    return {
      success         : false,
      error           : "Invalid Platoboost link - missing ticket.",
      attempts        : attempt,
      is_client_error : true,
      api_code        : "PLATOBOOST_INVALID_TICKET",
    }
  }

  const start_time      = Date.now()
  const ticket_param    = encodeURIComponent(ticket)
  const platoboost_base = `${parsed_url.protocol}//${parsed_url.host}/api`
  const platoboost_root = `${parsed_url.protocol}//${parsed_url.host}`
  const request_headers = {
    "Accept"          : "application/json, text/plain, */*",
    "Accept-Language" : "en-US,en;q=0.9",
    "Referer"         : `${platoboost_root}/`,
    "Origin"          : platoboost_root,
    "User-Agent"      : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
  }

  try {
    const status_response = await fetch(`${platoboost_base}/session/status?ticket=${ticket_param}`, {
      method  : "GET",
      headers : request_headers,
    })
    const status_text = await status_response.text().catch(() => "")
    const status_data = __parse_json_payload(status_text)
    const status_key  = __extract_platoboost_key(status_data)

    if (status_key) {
      const elapsed = Number(((Date.now() - start_time) / 1000).toFixed(2))
      return {
        success  : true,
        result   : status_key,
        time     : elapsed,
        attempts : attempt,
      }
    }

    const status_message = typeof status_data?.message === "string"
      ? __normalize_platoboost_error(status_data.message)
      : ""

    if (!status_response.ok || __is_platoboost_client_error(status_message)) {
      return {
        success         : false,
        error           : status_message || `Platoboost returned HTTP ${status_response.status}.`,
        attempts        : attempt,
        is_client_error : __is_platoboost_client_error(status_message) || (status_response.status >= 400 && status_response.status < 500),
        api_code        : "PLATOBOOST_STATUS_ERROR",
      }
    }

    const metadata_response = await fetch(`${platoboost_base}/session/metadata?ticket=${ticket_param}`, {
      method  : "GET",
      headers : request_headers,
    })
    const metadata_text = await metadata_response.text().catch(() => "")
    const metadata_data = __parse_json_payload(metadata_text)
    const metadata_key  = __extract_platoboost_key(metadata_data)

    if (metadata_key) {
      const elapsed = Number(((Date.now() - start_time) / 1000).toFixed(2))
      return {
        success  : true,
        result   : metadata_key,
        time     : elapsed,
        attempts : attempt,
      }
    }

    const metadata_message = typeof metadata_data?.message === "string"
      ? __normalize_platoboost_error(metadata_data.message)
      : ""

    if (!metadata_response.ok || __is_platoboost_client_error(metadata_message)) {
      return {
        success         : false,
        error           : metadata_message || `Platoboost returned HTTP ${metadata_response.status}.`,
        attempts        : attempt,
        is_client_error : __is_platoboost_client_error(metadata_message) || (metadata_response.status >= 400 && metadata_response.status < 500),
        api_code        : "PLATOBOOST_METADATA_ERROR",
      }
    }

    const active_task_count = Array.isArray(metadata_data?.activeTaskQueue)
      ? metadata_data.activeTaskQueue.length
      : Array.isArray(status_data?.activeTaskQueue)
        ? status_data.activeTaskQueue.length
        : 0

    if (active_task_count > 0) {
      return {
        success  : false,
        error    : "Platoboost still has pending tasks for this ticket. The upstream bypass API must finish them before a key can be returned.",
        attempts : attempt,
        api_code : "PLATOBOOST_PENDING",
      }
    }

    if (
      status_data?.activeRevenueProfile
      || metadata_data?.activeRevenueProfile
      || metadata_data?.checkpoint
      || metadata_data?.captcha
      || status_data?.checkpoint
      || status_data?.captcha
    ) {
      return {
        success  : false,
        error    : "Platoboost accepted the ticket, but it still requires completing checkpoints or captcha before the key can be generated.",
        attempts : attempt,
        api_code : "PLATOBOOST_PENDING",
      }
    }

    return {
      success  : false,
      error    : "Platoboost accepted the ticket, but the key is not available yet.",
      attempts : attempt,
      api_code : "PLATOBOOST_PENDING",
    }
  } catch (error: any) {
    const message = __normalize_platoboost_error(error)

    return {
      success         : false,
      error           : message,
      attempts        : attempt,
      is_client_error : __is_platoboost_client_error(message),
      api_code        : "PLATOBOOST_LOOKUP_FAILED",
    }
  }
}

async function __request_bypass_provider(url: string, attempt: number): Promise<BypassResponse> {
  const trimmed_url = url.trim()
  const start_time  = Date.now()
  const params      = new URLSearchParams({ url: trimmed_url })
  const bypass_api_key = __get_bypass_api_key()
  const bypass_api_url = __get_bypass_api_url()
  const bypass_refresh_url = __get_bypass_refresh_url()
  const req_headers = {
    "x-api-key"       : bypass_api_key,
    "Accept-Encoding" : "gzip, deflate, br",
    "Connection"      : "keep-alive",
  }

  try {
    const response = await __enqueue_bypass(() => {
      console.warn(`[ - BYPASS - ] requesting: ${bypass_api_url}?${params}`)
      return fetch(`${bypass_api_url}?${params}`, {
        method  : "GET",
        headers : req_headers,
      }).catch(err => {
        console.error(`[ - BYPASS - ] fetch threw an error for attempt ${attempt}:`, err)
        throw err
      })
    })

    console.warn(`[ - BYPASS - ] response status for attempt ${attempt}: ${response.status} ${response.statusText}`)

    const resp_text      = await response.text().catch(() => "")
    const resp_data: any = __parse_json_payload(resp_text)

    const is_processing = (
      response.status === 429 && resp_data?.code === "TASK_ALREADY_PROCESSING"
    ) || resp_data?.code === "TASK_ALREADY_PROCESSING"

    if (is_processing) {
      console.warn(`[ - BYPASS - ] task already processing for attempt ${attempt}, polling /v1/refresh...`)
      const poll_deadline = Date.now() + __refresh_max_wait_ms

      while (Date.now() < poll_deadline) {
        await new Promise(r => setTimeout(r, __refresh_interval_ms))

        try {
          const poll_res       = await fetch(bypass_refresh_url)
          const poll_text      = await poll_res.text().catch(() => "")
          const poll_data: any = __parse_json_payload(poll_text)

          if (poll_res.ok && poll_data?.result) {
            const elapsed = ((Date.now() - start_time) / 1000).toFixed(2)
            console.warn(`[ - BYPASS - ] refresh hit for attempt ${attempt} in ${elapsed}s`)
            return { success: true, result: poll_data.result, time: parseFloat(elapsed), attempts: attempt }
          }
        } catch (poll_err) {
          console.warn(`[ - BYPASS - ] refresh poll error:`, poll_err)
        }
      }

      return { success: false, error: "Bypass timed out waiting for result.", attempts: attempt }
    }

    if (!response.ok) {
      const err_message = resp_data.message || resp_data.result || `HTTP ${response.status}`
      const err         = new Error(err_message)
        ; (err as any).status   = response.status
        ; (err as any).api_code = resp_data.code || ""

      const retry_after = response.headers.get("retry-after") || response.headers.get("Retry-After")
      if (retry_after) (err as any).retry_after = parseInt(retry_after, 10)

      throw err
    }

    const process_time = ((Date.now() - start_time) / 1000).toFixed(2)
    console.warn(`[ - BYPASS - ] response data for attempt ${attempt}:`, JSON.stringify(resp_data).substring(0, 500))

    if (resp_data?.result) {
      console.warn(`[ - BYPASS - ] success on attempt ${attempt} in ${process_time}s`)
      return { success: true, result: resp_data.result, time: parseFloat(process_time), attempts: attempt }
    }

    return { success: false, error: resp_data?.message || "No result found in response", attempts: attempt }

  } catch (error: any) {
    const message = typeof error?.message === "string" ? error.message : ""
    const name    = typeof error?.name === "string" ? error.name : ""

    if (message.includes("HTTP 5")) {
      console.warn(`[ - BYPASS - ] external api error (attempt ${attempt}):`, message)
    } else if (message.includes("HTTP 429") || error?.status === 429) {
      const backoff_s = (error?.retry_after && !isNaN(error.retry_after))
        ? Math.max(error.retry_after, __bypass_default_backoff)
        : __bypass_default_backoff
      __set_global_backoff(backoff_s)
      console.warn(`[ - BYPASS - ] rate limit (attempt ${attempt}):`, message)
    } else {
      console.error(`[ - BYPASS - ] error (attempt ${attempt}):`, message || error)
    }

    let error_message = "Unknown error occurred"

    if (name === "AbortError" || message.includes("aborted") || message.includes("timeout") || message.includes("timed out")) {
      error_message = "Request failed - the API took too long to complete. Please try again."
    } else if (message.includes("not supported") || message.includes("unsupported")) {
      error_message = "Link is not supported."
    } else if (message.includes("429")) {
      error_message = "Rate limit exceeded - Please wait a moment."
    } else if (message.includes("5")) {
      error_message = "Service unavailable - Please try again later."
    } else if (message) {
      error_message = message
    }

    const status          = error?.status
    const is_client_error = status >= 400 && status < 500 && status !== 429

    return {
      success         : false,
      error           : error_message,
      attempts        : attempt,
      is_client_error : is_client_error,
      retry_after     : error?.retry_after,
      api_code        : error?.api_code || "",
    }
  }
}

/**
 * @description bypasses a link once.
 * @param url     - The URL to bypass
 * @param attempt - Current attempt number (internal, starts at 1)
 * @returns Promise with bypass result
 */
async function bypass_link_once(url: string, attempt: number): Promise<BypassResponse> {
  const trimmed_url = url.trim()
  console.warn(`[ - BYPASS - ] starting attempt ${attempt} for url: ${trimmed_url}`)

  // - check url cache first (only on first attempt) - \\
  if (attempt === 1) {
    const cached = await __get_url_cache(trimmed_url)
    if (cached) {
      console.warn(`[ - BYPASS - ] cache hit for url: ${trimmed_url}`)
      return { success: true, result: cached, time: 0, attempts: 0 }
    }
  }

  const bypass_api_url = __get_bypass_api_url()
  const platoboost_result = __is_direct_lookup_disabled()
    ? null
    : await __try_platoboost_lookup(trimmed_url, attempt)
  if (platoboost_result?.success && platoboost_result.result) {
    console.warn(`[ - BYPASS - ] platoboost direct lookup succeeded for attempt ${attempt}`)
    __set_url_cache(trimmed_url, platoboost_result.result).catch(() => {})
    return platoboost_result
  }

  if (platoboost_result && (platoboost_result.is_client_error || !bypass_api_url)) {
    console.warn(`[ - BYPASS - ] platoboost direct lookup returned terminal result for attempt ${attempt}`)
    return platoboost_result
  }

  if (!bypass_api_url) {
    return {
      success         : false,
      error           : "Bypass API is not configured on this bot.",
      attempts        : attempt,
      is_client_error : true,
    }
  }

  const provider_urls = __build_provider_candidate_urls(trimmed_url)
  let last_provider_result: BypassResponse = {
    success  : false,
    error    : "Unknown error occurred",
    attempts : attempt,
  }

  for (let index = 0; index < provider_urls.length; index++) {
    const provider_url    = provider_urls[index]
    const provider_result = await __request_bypass_provider(provider_url, attempt)

    if (provider_result.success && provider_result.result) {
      __set_url_cache(trimmed_url, provider_result.result).catch(() => {})
      return provider_result
    }

    last_provider_result = provider_result

    const has_more_candidates = index < provider_urls.length - 1
    if (has_more_candidates && __is_provider_unsupported_result(provider_result)) {
      console.warn(`[ - BYPASS - ] provider rejected ${provider_url}, trying normalized platoboost url...`)
      continue
    }

    if (__is_provider_unsupported_result(provider_result) && platoboost_result) {
      return platoboost_result
    }

    return provider_result
  }

  return last_provider_result
}

/**
 * @description bypasses a link and retries if necessary.
 * @param url      - The URL to bypass
 * @param on_retry - Optional callback fired before each retry with attempt number and estimated total wait ms
 * @returns Promise with bypass result
 */
export async function bypass_link(
  url       : string,
  on_retry? : (attempt: number, wait_ms: number, is_processing: boolean) => void | Promise<void>
): Promise<BypassResponse> {
  console.warn(`[ - BYPASS - ] starting bypass_link for url: ${url}`)
  
  // - global timeout limit - \\
  let   global_timeout_id!: ReturnType<typeof setTimeout>
  const timeout_promise   = new Promise<BypassResponse>(resolve => {
    global_timeout_id = setTimeout(() => {
      console.warn(`[ - BYPASS - ] global timeout (${__bypass_global_timeout}ms) hit for url: ${url}`)
      resolve({ 
        success  : false, 
        error    : "Request failed - the API took too long to complete. Please try again.", 
        attempts : 0 
      })
    }, __bypass_global_timeout)
  })

  // - race api call against timeout - \\
  const result = await Promise.race([
    timeout_promise, 
    _run_bypass_link(url, on_retry)
  ])
  
  clearTimeout(global_timeout_id)
  console.warn(`[ - BYPASS - ] bypass_link finished for url: ${url} with success: ${result.success}`)
  return result
}

/**
 * @description internal function to run the bypass link logic.
 * @param url      - The URL to bypass
 * @param on_retry - Optional callback fired before each retry with attempt number and estimated total wait ms
 * @returns Promise with bypass result
 */
async function _run_bypass_link(
  url       : string,
  on_retry? : (attempt: number, wait_ms: number, is_processing: boolean) => void | Promise<void>
): Promise<BypassResponse> {
  let last_result: BypassResponse = { success: false, error: "Unknown error", attempts: 0 }

  for (let attempt = 1; attempt <= __bypass_max_retry; attempt++) {
    console.warn(`[ - BYPASS - ] _run_bypass_link loop starting attempt ${attempt} for url: ${url}`)
    last_result = await bypass_link_once(url, attempt)
    console.warn(`[ - BYPASS - ] _run_bypass_link loop finished attempt ${attempt} for url: ${url} with success: ${last_result.success}`)

    if (last_result.success) return last_result

    // - don't retry on unsupported links or client errors - no point - \\
    const is_unsupported = last_result.error?.toLowerCase().includes("not supported")
      || last_result.error?.toLowerCase().includes("unsupported")
    if (is_unsupported || last_result.is_client_error) {
      console.warn(`[ - BYPASS - ] _run_bypass_link aborting retries for url: ${url} (unsupported or client error)`)
      return last_result
    }

    if (attempt < __bypass_max_retry) {
      // - fixed 60s retry delay - \\
      let delay = __bypass_retry_ms
      if (last_result.retry_after && !isNaN(last_result.retry_after)) {
        delay = Math.max(delay, last_result.retry_after * 1000)
      }

      // - total wait = retry delay + remaining global backoff - \\
      const backoff_remaining = __get_backoff_remaining_ms()
      const total_wait_ms     = delay + backoff_remaining

      console.warn(`[ - BYPASS - ] attempt ${attempt} failed, retrying in ${total_wait_ms}ms (delay: ${delay}ms, backoff: ${backoff_remaining}ms)...`)

      if (on_retry) {
        try {
          console.warn(`[ - BYPASS - ] executing on_retry callback for attempt ${attempt + 1}`)
          await on_retry(attempt + 1, total_wait_ms, last_result.api_code === "TASK_ALREADY_PROCESSING")
          console.warn(`[ - BYPASS - ] finished on_retry callback for attempt ${attempt + 1}`)
        } catch (retry_err) {
          console.warn(`[ - BYPASS - ] failed to execute on_retry callback:`, retry_err)
        }
      }
      console.warn(`[ - BYPASS - ] waiting ${delay}ms before next attempt...`)
      await new Promise(resolve => setTimeout(resolve, delay))
      console.warn(`[ - BYPASS - ] wait finished, proceeding to next attempt...`)
    }
  }

  console.warn(`[ - BYPASS - ] all ${__bypass_max_retry} attempts failed for: ${url}`)
  return last_result
}

/**
 * @description retrieves a list of supported services for bypassing.
 * @returns Promise with list of supported services
 */
export async function get_supported_services(): Promise<SupportedService[]> {
  const bypass_api_url = __get_bypass_api_url()
  const bypass_api_key = __get_bypass_api_key()

  if (!bypass_api_url) {
    return []
  }

  try {
    const response = await __enqueue_bypass(async () => {
      return await fetch(`${bypass_api_url.replace('/bypass', '/supported')}`, {
        method  : "GET",
        headers : {
          "x-api-key"       : bypass_api_key,
          "Accept-Encoding" : "gzip, deflate, br",
          "Connection"      : "keep-alive",
        }
      })
    })

    if (!response.ok) throw new Error(`HTTP ${response.status}`)

    const data: any = await response.json()
    return data.result || []

  } catch (error: any) {
    console.error(`[ - BYPASS - ] error fetching services:`, error.message)
    return []
  }
}
