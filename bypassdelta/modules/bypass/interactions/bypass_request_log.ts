/*
 * Atomicals Bot for Discord
 * Copyright (C) 2026 Atomicals LancarJaya
 *
 * Licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License.
 * You may not use this file except in compliance with the License.
 * See the LICENSE file for more information.
 */

import { ButtonInteraction, AttachmentBuilder } from "discord.js"
import { db }                                   from "../../utils"
import { is_authorized_user }                   from "../../utils/authorized_users"

/**
 * - 查看请求日志按钮 - \\
 * - view request log button - \\
 *
 * @param {ButtonInteraction} interaction - button interaction
 * @returns {Promise<void>}
 */
export async function handle_bypass_request_log(interaction: ButtonInteraction): Promise<void> {
  try {
    const [, request_id] = interaction.customId.split(":")

    if (!request_id) {
      await interaction.reply({
        content   : "Invalid log button. Please try the bypass again.", ephemeral: true,
      })
      return
    }

    // - 仅开发者可用 - \\
    // - developer only - \\
    if (!is_authorized_user(interaction.user.id)) {
      await interaction.reply({
        content   : "This button is restricted to authorized users only.", ephemeral: true,
      })
      return
    }

    const log_key = `bypass_log_${request_id}`

    const result = await db.get_pool().query(
      `SELECT url FROM bypass_cache WHERE key = $1 AND expires_at > NOW()`,
      [log_key]
    )

    if (!result.rows || result.rows.length === 0) {
      await interaction.reply({
        content   : "Log expired or not found.", ephemeral: true,
      })
      return
    }

    const log_text = result.rows[0].url
    const buffer   = Buffer.from(log_text, "utf-8")

    await interaction.reply({
      files     : [new AttachmentBuilder(buffer, { name: `${log_key}.txt` })], ephemeral: true,
    })

  } catch (error) {
    try {
      await interaction.reply({
        content   : "Failed to retrieve log.", ephemeral: true,
      })
    } catch { /* already replied */ }
  }
}
