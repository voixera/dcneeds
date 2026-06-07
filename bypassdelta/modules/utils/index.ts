import { AttachmentBuilder, ChatInputCommandInteraction } from "discord.js"
import { Cache } from "./cache"
import * as component from "./components"
import {
  __bypass_logs_store,
  __bypass_stats_store,
  __guild_settings_store,
  cleanup_bypass_cache,
  get_pool,
} from "./database"

type guild_settings_map = {
  [key: string]: string
}

type bypass_log_record = Record<string, unknown>

const __cache = new Cache<unknown>(5 * 60_000, 5000, 10 * 60_000, "shared_cache")
let __db_connected = false

export const cache = {
  delete : (key: string) => __cache.delete(key),
  get    : <T>(key: string) => __cache.get(key) as T | undefined,
  set    : (key: string, value: unknown, ttl_ms?: number) => __cache.set(key, value, ttl_ms),
}

export const api = {
  async edit_deferred_reply(interaction: ChatInputCommandInteraction, message: Record<string, unknown>) {
    return await interaction.editReply(message as any)
  },

  async edit_deferred_reply_with_files(
    interaction: ChatInputCommandInteraction,
    message: Record<string, unknown>,
    files: Array<{ content: Buffer; name: string }>
  ) {
    try {
      await interaction.editReply({
        ...(message as any),
        files : files.map(file => new AttachmentBuilder(file.content, { name: file.name })),
      })

      return { error: null }
    } catch (error) {
      return { error }
    }
  },
}

export const guild_settings = {
  async get_all_guild_settings(guild_id: string): Promise<guild_settings_map | null> {
    return __guild_settings_store.get(guild_id)?.settings ?? null
  },

  async remove_guild_setting(guild_id: string, key: string): Promise<boolean> {
    const current = __guild_settings_store.get(guild_id)
    if (!current) return true

    delete current.settings[key]
    __guild_settings_store.set(guild_id, current)
    return true
  },

  async set_guild_setting(guild_id: string, key: string, value: string): Promise<boolean> {
    const current = __guild_settings_store.get(guild_id) || {
      guild_id,
      settings : {},
    }

    current.settings[key] = value
    __guild_settings_store.set(guild_id, current)
    return true
  },
}

export const db = {
  async connect(): Promise<void> {
    __db_connected = true
  },

  async find_many<T>(table: string, _filter: Record<string, unknown>): Promise<T[]> {
    if (table === "guild_settings") {
      return [...__guild_settings_store.values()] as T[]
    }

    return []
  },

  get_pool,

  async cleanup_expired_bypass_cache(): Promise<void> {
    cleanup_bypass_cache()
  },

  async increment_bypass_count(): Promise<void> {},

  async insert_bypass_log(log: bypass_log_record): Promise<void> {
    __bypass_logs_store.push(log)
  },

  is_connected(): boolean {
    return __db_connected
  },

  async record_bypass_guild_stat(guild_id: string): Promise<void> {
    __bypass_stats_store.set(guild_id, (__bypass_stats_store.get(guild_id) || 0) + 1)
  },
}

export { component }
