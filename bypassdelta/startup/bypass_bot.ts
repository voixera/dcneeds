/*
 * Atomicals Bot for Discord
 * Copyright (C) 2026 Atomicals LancarJaya
 *
 * Licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License.
 * You may not use this file except in compliance with the License.
 * See the LICENSE file for more information.
 */

import {
  ActivityType,
  Client,
  Collection,
  GatewayIntentBits,
  Message,
  Partials,
  REST,
  Routes,
} from "discord.js"
import { config } from "dotenv"
import { Command } from "../modules/shared/types/command"
import { db } from "../modules/utils"
import { log_error } from "../modules/utils/error_logger"
import { recover_stuck_bypass_sessions, handle_auto_bypass } from "../modules/bypass/events/bypass"
import { handle_bypass_mobile_copy } from "../modules/bypass/interactions/bypass_mobile_copy"
import { handle_bypass_request_log } from "../modules/bypass/interactions/bypass_request_log"
import authorize_user_add_command from "../modules/bypass/routes/authorize_user_add"
import bypass_command from "../modules/bypass/routes/bypass"
import bypass_channel_set_command from "../modules/bypass/routes/bypass_channel_set"
import bypass_enabled_command from "../modules/bypass/routes/bypass_enabled"
import view_bypass_guild_command from "../modules/bypass/routes/view_bypass_guild"
import invite_bot_command from "../modules/general/routes/invite_bot"
import bypass_support_command from "../modules/support/routes/bypass_support"
import { handle_bypass_support_type_select } from "../modules/support/interactions/select_menus/bypass_support_type_select"

type bypass_client = Client & {
  commands : Collection<string, Command>
}

const __bypass_commands: Command[] = [
  authorize_user_add_command,
  bypass_command,
  bypass_channel_set_command,
  bypass_enabled_command,
  view_bypass_guild_command,
  invite_bot_command,
  bypass_support_command,
]

let __startup_promise: Promise<bypass_client | null> | null = null

function __is_message_content_enabled_in_env(): boolean {
  return (process.env.BYPASS_ENABLE_MESSAGE_CONTENT || "true").toLowerCase() !== "false"
}

function __is_disallowed_intents_error(error: unknown): boolean {
  const message = error instanceof Error ? error.message : String(error)
  const lowered = message.toLowerCase()

  return lowered.includes("disallowed intents")
    || lowered.includes("used disallowed intents")
    || lowered.includes("4014")
}

function __create_client(enable_message_content: boolean): bypass_client {
  const intents = [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.DirectMessages,
  ]

  if (enable_message_content) {
    intents.push(GatewayIntentBits.MessageContent)
  }

  const client = new Client({
    intents,
    partials: [
      Partials.Channel,
      Partials.Message,
      Partials.User,
      Partials.GuildMember,
    ],
    presence: {
      status     : "dnd",
      activities : [{
        name  : "DrxDvs Bypass v1.0",
        type  : ActivityType.Custom,
        state : "Made with ♥️ by DrxDvs",
      }],
    },
  }) as bypass_client

  client.commands = new Collection<string, Command>()

  for (const command of __bypass_commands) {
    client.commands.set(command.data.name, command)
  }

  return client
}

async function __register_commands(token: string, client_id: string): Promise<void> {
  const rest = new REST().setToken(token)
  const body = __bypass_commands.map(command => command.data.toJSON())

  await rest.put(Routes.applicationCommands(client_id), { body })
  console.warn(`[ - BYPASS - ] Registered ${body.length} commands`)
}

function __resolve_client_id(configured_client_id: string, fallback_client_id: string): string {
  const trimmed_configured = configured_client_id.trim()
  if (/^\d+$/.test(trimmed_configured)) {
    return trimmed_configured
  }

  const trimmed_fallback = fallback_client_id.trim()
  if (/^\d+$/.test(trimmed_fallback)) {
    return trimmed_fallback
  }

  return ""
}

async function __initialize_database(client: bypass_client): Promise<void> {
  try {
    await db.connect()
    await db.cleanup_expired_bypass_cache()
    setInterval(() => {
      void db.cleanup_expired_bypass_cache()
    }, 10 * 60 * 1000)

    await recover_stuck_bypass_sessions(client)
  } catch (error) {
    console.error("[ - BYPASS - ] Database init error:", error)
  }
}

async function __handle_command_interaction(client: bypass_client, interaction: any): Promise<void> {
  const command = client.commands.get(interaction.commandName)
  if (!command) return

  try {
    await command.execute(interaction)
  } catch (error) {
    console.error(`[ - BYPASS - ] Command error (${interaction.commandName}):`, error)
    await log_error(client, error as Error, `Bypass Command: ${interaction.commandName}`, {
      user    : interaction.user.tag,
      guild   : interaction.guild?.name || "DM",
      channel : interaction.channel?.id,
    })

    if (!interaction.deferred && !interaction.replied) {
      await interaction.reply({
        content   : "An unexpected error occurred while executing this command.",
        ephemeral : true,
      }).catch(() => {})
    }
  }
}

function __bind_events(client: bypass_client, token: string, client_id: string, enable_message_content: boolean): void {
  client.once("ready", async () => {
    console.warn(`[ - BYPASS - ] Bot logged in as ${client.user?.tag}`)
    console.warn(`[ - BYPASS - ] Serving ${client.guilds.cache.size} guilds`)

    if (!enable_message_content) {
      console.warn("[ - BYPASS - ] Message Content intent is disabled. Auto-bypass from normal messages is unavailable; use /bypass instead.")
    }

    const resolved_client_id = __resolve_client_id(client_id, client.user?.id || "")
    if (!resolved_client_id) {
      console.warn("[ - BYPASS - ] Client ID is missing or invalid, skipping slash command registration.")
    } else {
      try {
        await __register_commands(token, resolved_client_id)
      } catch (error) {
        console.error("[ - BYPASS - ] Failed to register commands:", error)
      }
    }

    await __initialize_database(client)
  })

  client.on("interactionCreate", async (interaction) => {
    if (interaction.isButton()) {
      try {
        if (interaction.customId.startsWith("bypass_mobile_copy:")) {
          await handle_bypass_mobile_copy(interaction)
          return
        }

        if (interaction.customId.startsWith("bypass_request_log:")) {
          await handle_bypass_request_log(interaction)
          return
        }
      } catch (error) {
        console.error("[ - BYPASS - ] Button error:", error)
        await log_error(client, error as Error, `Bypass Button: ${interaction.customId}`, {
          user    : interaction.user.tag,
          guild   : interaction.guild?.name || "DM",
          channel : interaction.channel?.id,
        })
      }

      return
    }

    if (interaction.isStringSelectMenu()) {
      try {
        if (interaction.customId.startsWith("bypass_support_type_select:")) {
          await handle_bypass_support_type_select(interaction)
          return
        }
      } catch (error) {
        console.error("[ - BYPASS - ] Select menu error:", error)
        await log_error(client, error as Error, `Bypass Select: ${interaction.customId}`, {
          user    : interaction.user.tag,
          guild   : interaction.guild?.name || "DM",
          channel : interaction.channel?.id,
        })
      }

      return
    }

    if (!interaction.isChatInputCommand()) return
    await __handle_command_interaction(client, interaction)
  })

  if (enable_message_content) {
    client.on("messageCreate", async (message: Message) => {
      if (message.author.bot) return
      await handle_auto_bypass(message)
    })
  }

  client.on("error", (error) => {
    console.error("[ - BYPASS - ] Client error:", error)
    void log_error(client, error, "Bypass Client Error", {})
  })

  process.on("unhandledRejection", (reason) => {
    console.error("[ - BYPASS - ] Unhandled rejection:", reason)
    void log_error(
      client,
      reason instanceof Error ? reason : new Error(String(reason)),
      "Bypass Unhandled Rejection",
      {}
    )
  })

  process.on("uncaughtException", (error) => {
    console.error("[ - BYPASS - ] Uncaught exception:", error)
    void log_error(client, error, "Bypass Uncaught Exception", {})
  })
}

export async function start_bypass_bot(): Promise<bypass_client | null> {
  if (__startup_promise) {
    return __startup_promise
  }

  __startup_promise = (async () => {
    try {
      config()

      if (process.env.NODE_ENV === "production") {
        console.log = () => {}
      }

      const bypass_token     = process.env.BYPASS_DISCORD_TOKEN?.trim() || ""
      const bypass_client_id = process.env.BYPASS_CLIENT_ID?.trim() || ""

      if (!bypass_token) {
        console.warn("[ - BYPASS - ] Token not configured, skipping startup")
        return null
      }

      let enable_message_content = __is_message_content_enabled_in_env()
      let client = __create_client(enable_message_content)
      __bind_events(client, bypass_token, bypass_client_id, enable_message_content)

      try {
        await client.login(bypass_token)
      } catch (error) {
        if (enable_message_content && __is_disallowed_intents_error(error)) {
          console.warn("[ - BYPASS - ] Message Content intent is not allowed for this bot. Retrying without it...")
          client.removeAllListeners()
          client.destroy()

          enable_message_content = false
          client = __create_client(enable_message_content)
          __bind_events(client, bypass_token, bypass_client_id, enable_message_content)
          await client.login(bypass_token)
        } else {
          throw error
        }
      }

      console.warn("[ - BYPASS - ] Login successful")
      return client
    } catch (error) {
      __startup_promise = null
      throw error
    }
  })()

  return __startup_promise
}

if (require.main === module) {
  start_bypass_bot().catch((error) => {
    console.error("[ - BYPASS - ] Startup failed:", error)
    process.exit(1)
  })
}
