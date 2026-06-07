import { createHash } from "crypto"
import { createServer, IncomingMessage, Server, ServerResponse } from "http"
import { config } from "dotenv"

type supported_service = {
  domains : string[]
  name    : string
  status  : "active" | "inactive"
  type    : string
}

type pending_task = {
  created_at : number
  ready_at   : number
  result     : string
  url        : string
}

const __supported_services: supported_service[] = [
  {
    name    : "Platorelay",
    type    : "Shortener",
    status  : "active",
    domains : ["platorelay.com", "platoboost.com", "platoboost.app"],
  },
  {
    name    : "Generic Link",
    type    : "Utility",
    status  : "active",
    domains : ["example.com", "localhost"],
  },
]

let __server: Server | null = null
let __pending_task: pending_task | null = null

async function __is_existing_mock_api(host: string, port: number): Promise<boolean> {
  try {
    const response = await fetch(`http://${host}:${port}/health`)
    if (!response.ok) {
      return false
    }

    const payload = await response.json() as { ok?: boolean; service?: string }
    return payload.ok === true && payload.service === "bypass-api"
  } catch {
    return false
  }
}

function __json(response: ServerResponse, status_code: number, payload: unknown, headers: Record<string, string> = {}): void {
  response.writeHead(status_code, {
    "Content-Type" : "application/json; charset=utf-8",
    ...headers,
  })
  response.end(JSON.stringify(payload))
}

function __make_result(url: string): string {
  const digest = createHash("sha256").update(url).digest("hex").slice(0, 24).toUpperCase()
  return `KEY_${digest}`
}

function __requires_api_key(request: IncomingMessage): boolean {
  const expected_key = (process.env.MOCK_BYPASS_API_KEY || process.env.BYPASS_API_KEY || "dev-local-key").trim()
  if (!expected_key) return false

  const provided_key = String(request.headers["x-api-key"] || "").trim()
  return provided_key !== expected_key
}

function __handle_supported(response: ServerResponse): void {
  __json(response, 200, {
    result : __supported_services,
  })
}

function __handle_refresh(response: ServerResponse): void {
  if (!__pending_task) {
    __json(response, 200, {
      message : "No active task.",
    })
    return
  }

  if (Date.now() < __pending_task.ready_at) {
    __json(response, 200, {
      message : "Task still processing.",
      code    : "TASK_ALREADY_PROCESSING",
    })
    return
  }

  const finished_task = __pending_task
  __pending_task = null

  __json(response, 200, {
    result : finished_task.result,
  })
}

function __handle_bypass(request_url: URL, response: ServerResponse): void {
  const raw_url = request_url.searchParams.get("url")?.trim() || ""

  if (!raw_url) {
    __json(response, 400, {
      message : "Missing url query parameter.",
      code    : "INVALID_URL",
    })
    return
  }

  const lowered = raw_url.toLowerCase()

  if (lowered.includes("unsupported")) {
    __json(response, 400, {
      message : "Link is not supported.",
      code    : "UNSUPPORTED_SERVICE",
    })
    return
  }

  if (lowered.includes("error500")) {
    __json(response, 500, {
      message : "Service unavailable.",
      code    : "UPSTREAM_ERROR",
    })
    return
  }

  if (lowered.includes("ratelimit")) {
    __json(response, 429, {
      message : "Rate limit exceeded.",
      code    : "RATE_LIMITED",
    }, {
      "Retry-After" : "5",
    })
    return
  }

  if (lowered.includes("pending") || lowered.includes("processing")) {
    const result = __make_result(raw_url)
    __pending_task = {
      url        : raw_url,
      result,
      created_at : Date.now(),
      ready_at   : Date.now() + 3_000,
    }

    __json(response, 429, {
      message : "Task already processing.",
      code    : "TASK_ALREADY_PROCESSING",
    }, {
      "Retry-After" : "3",
    })
    return
  }

  __json(response, 200, {
    result : __make_result(raw_url),
  })
}

function __request_handler(request: IncomingMessage, response: ServerResponse): void {
  const host = request.headers.host || "127.0.0.1"
  const request_url = new URL(request.url || "/", `http://${host}`)

  if (request_url.pathname === "/health") {
    __json(response, 200, {
      ok      : true,
      service : "bypass-api",
    })
    return
  }

  if (__requires_api_key(request)) {
    __json(response, 401, {
      message : "Invalid API key.",
      code    : "INVALID_API_KEY",
    })
    return
  }

  if (request.method !== "GET") {
    __json(response, 405, {
      message : "Method not allowed.",
      code    : "METHOD_NOT_ALLOWED",
    })
    return
  }

  if (request_url.pathname === "/supported") {
    __handle_supported(response)
    return
  }

  if (request_url.pathname === "/refresh") {
    __handle_refresh(response)
    return
  }

  if (request_url.pathname === "/bypass") {
    __handle_bypass(request_url, response)
    return
  }

  __json(response, 404, {
    message : "Route not found.",
    code    : "NOT_FOUND",
  })
}

export async function start_mock_bypass_api(): Promise<Server | null> {
  if (__server) return __server

  config()

  const port = Number.parseInt(process.env.MOCK_BYPASS_API_PORT || "8787", 10)
  const host = process.env.MOCK_BYPASS_API_HOST || "127.0.0.1"

  __server = createServer(__request_handler)

  try {
    await new Promise<void>((resolve, reject) => {
      __server!.once("error", reject)
      __server!.listen(port, host, () => {
        resolve()
      })
    })
  } catch (error) {
    __server = null

    if ((error as NodeJS.ErrnoException).code === "EADDRINUSE") {
      if (await __is_existing_mock_api(host, port)) {
        console.info(`[ - BYPASS API - ] Using existing instance at http://${host}:${port}`)
        return null
      }

      throw new Error(
        `Port ${host}:${port} is already in use by another process. ` +
        `Stop that process or change MOCK_BYPASS_API_PORT and BYPASS_API_URL in .env.`
      )
    }

    throw error
  }

  console.info(`[ - BYPASS API - ] Running at http://${host}:${port}`)
  return __server
}

if (require.main === module) {
  start_mock_bypass_api().catch((error) => {
    console.error("[ - BYPASS API - ] Startup failed:", error)
    process.exit(1)
  })
}
