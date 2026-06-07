type cache_entry<T> = {
  expires_at : number
  value      : T
}

export class Cache<T> {
  private readonly store = new Map<string, cache_entry<T>>()

  constructor(
    private readonly default_ttl_ms: number = 60_000,
    private readonly _max_size: number = 1000,
    private readonly _sweep_interval_ms: number = 60_000,
    private readonly _name: string = "cache"
  ) {}

  get(key: string): T | undefined {
    const entry = this.store.get(key)
    if (!entry) return undefined

    if (entry.expires_at <= Date.now()) {
      this.store.delete(key)
      return undefined
    }

    return entry.value
  }

  set(key: string, value: T, ttl_ms: number = this.default_ttl_ms): void {
    this.store.set(key, {
      value,
      expires_at : Date.now() + Math.max(0, ttl_ms),
    })
  }

  delete(key: string): void {
    this.store.delete(key)
  }

  clear(): void {
    this.store.clear()
  }
}
