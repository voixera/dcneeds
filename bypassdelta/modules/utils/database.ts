type bypass_cache_row = {
  key        : string
  url        : string
  expires_at : number
}

type guild_settings_row = {
  guild_id  : string
  settings  : Record<string, string>
}

export const __bypass_cache_store   = new Map<string, bypass_cache_row>()
export const __guild_settings_store = new Map<string, guild_settings_row>()
export const __bypass_logs_store: unknown[] = []
export const __bypass_stats_store   = new Map<string, number>()

export function cleanup_bypass_cache(): void {
  const now = Date.now()

  for (const [key, row] of __bypass_cache_store.entries()) {
    if (row.expires_at <= now) {
      __bypass_cache_store.delete(key)
    }
  }
}

function __parse_interval_ms(sql: string): number {
  const match = sql.match(/interval '(\d+)\s+(minute|minutes|hour|hours)'/i)
  if (!match) return 5 * 60_000

  const amount = Number.parseInt(match[1], 10)
  const unit   = match[2].toLowerCase()

  return unit.startsWith("hour") ? amount * 60 * 60_000 : amount * 60_000
}

class memory_pool {
  async query<T = any>(sql: string, params: unknown[] = []): Promise<{ rows: T[] }> {
    cleanup_bypass_cache()

    const normalized_sql = sql.replace(/\s+/g, " ").trim().toLowerCase()

    if (
      normalized_sql.startsWith("select url from bypass_cache where key = $1")
      || normalized_sql.startsWith("select key, url from bypass_cache where key like 'bypass_session_%'")
    ) {
      if (normalized_sql.includes("key like 'bypass_session_%'")) {
        const rows = [...__bypass_cache_store.values()]
          .filter(row => row.key.startsWith("bypass_session_") && row.expires_at > Date.now())
          .map(row => ({ key: row.key, url: row.url })) as T[]

        return { rows }
      }

      const key = String(params[0] ?? "")
      const row = __bypass_cache_store.get(key)

      if (!row || row.expires_at <= Date.now()) {
        return { rows: [] }
      }

      return { rows: [{ url: row.url }] as T[] }
    }

    if (normalized_sql.startsWith("insert into bypass_cache")) {
      const key        = String(params[0] ?? "")
      const url        = String(params[1] ?? "")
      const expires_at = Date.now() + __parse_interval_ms(sql)

      __bypass_cache_store.set(key, { key, url, expires_at })
      return { rows: [] }
    }

    if (normalized_sql.startsWith("delete from bypass_cache where key = $1")) {
      const key = String(params[0] ?? "")
      __bypass_cache_store.delete(key)
      return { rows: [] }
    }

    return { rows: [] }
  }
}

const __pool = new memory_pool()

export function get_pool() {
  return __pool
}
