import { existsSync, mkdirSync, readFileSync, writeFileSync } from "fs"
import { dirname, resolve } from "path"

const __owner_user_id = "975269168184168539"
const __authorized_users_file = resolve(process.cwd(), ".tmp", "authorized_users.json")

let __authorized_users: Set<string> | null = null

function __normalize_user_id(value: string): string | null {
  const trimmed = value.trim()
  return /^\d{5,30}$/.test(trimmed) ? trimmed : null
}

function __read_persisted_user_ids(): string[] {
  try {
    if (!existsSync(__authorized_users_file)) {
      return []
    }

    const raw = readFileSync(__authorized_users_file, "utf8")
    const parsed = JSON.parse(raw) as unknown

    if (!Array.isArray(parsed)) {
      return []
    }

    return parsed
      .map((value) => __normalize_user_id(String(value)))
      .filter((value): value is string => Boolean(value))
  } catch {
    return []
  }
}

function __read_env_user_ids(): string[] {
  return String(process.env.AUTHORIZED_USER_IDS || "")
    .split(",")
    .map((value) => __normalize_user_id(value))
    .filter((value): value is string => Boolean(value))
}

function __load_authorized_users(): Set<string> {
  return new Set<string>([
    __owner_user_id,
    ...__read_env_user_ids(),
    ...__read_persisted_user_ids(),
  ])
}

function __get_authorized_users(): Set<string> {
  if (!__authorized_users) {
    __authorized_users = __load_authorized_users()
  }

  return __authorized_users
}

function __persist_authorized_users(): void {
  const authorized_users = [...__get_authorized_users()].sort()

  mkdirSync(dirname(__authorized_users_file), { recursive: true })
  writeFileSync(__authorized_users_file, JSON.stringify(authorized_users, null, 2), "utf8")
}

export function is_authorized_user(user_id: string): boolean {
  const normalized_user_id = __normalize_user_id(user_id)
  if (!normalized_user_id) {
    return false
  }

  return __get_authorized_users().has(normalized_user_id)
}

export function add_authorized_user(user_id: string): { added: boolean; user_id: string | null } {
  const normalized_user_id = __normalize_user_id(user_id)
  if (!normalized_user_id) {
    return {
      added   : false,
      user_id : null,
    }
  }

  const authorized_users = __get_authorized_users()
  const already_authorized = authorized_users.has(normalized_user_id)

  authorized_users.add(normalized_user_id)

  if (!already_authorized) {
    __persist_authorized_users()
  }

  return {
    added   : !already_authorized,
    user_id : normalized_user_id,
  }
}

export function get_authorized_user_ids(): string[] {
  return [...__get_authorized_users()].sort()
}
