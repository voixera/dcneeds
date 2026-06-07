/*
 * Atomicals Bot for Discord
 * Copyright (C) 2026 Atomicals LancarJaya
 *
 * Licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License.
 * You may not use this file except in compliance with the License.
 * See the LICENSE file for more information.
 */

import {
  ChatInputCommandInteraction,
  PermissionFlagsBits,
  SlashCommandBuilder,
} from "discord.js"
import { Command } from "../../shared/types/command"
import { component, guild_settings } from "../../utils"
import { is_authorized_user } from "../../utils/authorized_users"

/**
 * - 绕过启用命令 - \\
 * - bypass enabled command - \\
 */
const bypass_enabled_command: Command = {
  data: new SlashCommandBuilder()
    .setName("bypass-enabled")
    .setDescription("Enable or disable bypass feature in this server")
    .addBooleanOption((option) =>
      option
        .setName("enabled")
        .setDescription("Set true to enable, false to disable")
        .setRequired(true)
    )
    .addStringOption((option) =>
      option
        .setName("reason")
        .setDescription("Required when disabling bypass")
        .setRequired(false)
    )
    .setDefaultMemberPermissions(PermissionFlagsBits.ManageGuild) as SlashCommandBuilder,

  execute: async (interaction: ChatInputCommandInteraction) => {
    if (!is_authorized_user(interaction.user.id)) {
      const unauthorized_message = component.build_message({
        components: [
          component.container({
            components: [
              component.text([
                "## Access Denied",
                "",
                "Only authorized users can change bypass enabled status.",
              ]),
            ],
          }),
        ],
      })

      await interaction.reply({
        ...unauthorized_message,
        ephemeral : true,
      })
      return
    }

    const guild_id = interaction.guildId
    if (!guild_id) {
      const error_message = component.build_message({
        components: [
          component.container({
            components: [
              component.text([
                "## Invalid Context",
                "",
                "This command can only be used in a server.",
              ]),
            ],
          }),
        ],
      })

      await interaction.reply({
        ...error_message,
        ephemeral : true,
      })
      return
    }

    const enabled = interaction.options.getBoolean("enabled", true)
    const reason  = (interaction.options.getString("reason") || "").trim()

    if (!enabled && !reason) {
      const validation_message = component.build_message({
        components: [
          component.container({
            components: [
              component.text([
                "## Reason Required",
                "",
                "Reason is required when `enabled` is set to `false`.",
              ]),
            ],
          }),
        ],
      })

      await interaction.reply({
        ...validation_message,
        ephemeral : true,
      })
      return
    }

    if (enabled) {
      const saved = await guild_settings.set_guild_setting(guild_id, "bypass_enabled", "true")
      await guild_settings.remove_guild_setting(guild_id, "bypass_disabled_reason")

      const response_message = component.build_message({
        components: [
          component.container({
            components: [
              component.text([
                saved ? "## Bypass Enabled" : "## Failed to Save",
                "",
                saved
                  ? "Bypass feature is now enabled."
                  : "Could not update bypass status. Please try again.",
              ]),
            ],
          }),
        ],
      })

      await interaction.reply({
        ...response_message,
        ephemeral : true,
      })
      return
    }

    const enabled_saved = await guild_settings.set_guild_setting(guild_id, "bypass_enabled", "false")
    const reason_saved  = await guild_settings.set_guild_setting(guild_id, "bypass_disabled_reason", reason)

    const saved = enabled_saved && reason_saved

    const response_message = component.build_message({
      components: [
        component.container({
          components: [
            component.text([
              saved ? "## Bypass Disabled" : "## Failed to Save",
              "",
              saved
                ? `Under Maintenance, Reason: ${reason}`
                : "Could not update bypass status. Please try again.",
            ]),
          ],
        }),
      ],
    })

    await interaction.reply({
      ...response_message,
      ephemeral : true,
    })
  },
}

export default bypass_enabled_command
