/*
 * Atomicals Bot for Discord
 * Copyright (C) 2026 Atomicals LancarJaya
 *
 * Licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License.
 * You may not use this file except in compliance with the License.
 * See the LICENSE file for more information.
 */

import * as component from "../../utils/components"

interface BuildBypassSuccessMessageOptions {
  invite_url           : string
  requested_by_user_id : string
  request_token        : string
  result               : string
  thumbnail_url?       : string
  time?                : number
}

/**
 * @description builds the shared bypass success message for slash and auto-bypass flows.
 * @param options - Success message options
 * @returns Component message payload
 */
export function build_bypass_success_message(options: BuildBypassSuccessMessageOptions) {
  const clean_result = options.result.trim()
  const footer = typeof options.time === "number" && Number.isFinite(options.time)
    ? `Completed in ${options.time.toFixed(1)}s | Requested by <@${options.requested_by_user_id}>`
    : `Requested by <@${options.requested_by_user_id}>`

  const header_section = component.section({
    content : [
      "## [OK] - Bypass Completed",
      "Your bypass was completed successfully. Use `/bypass` or send a link to start another bypass.",
    ],
    ...(options.thumbnail_url
      ? { accessory: component.thumbnail(options.thumbnail_url) }
      : {}),
  })

  return component.build_message({
    components: [
      component.container({
        accent_color : 0x5865F2,
        components: [header_section],
      }),
      component.container({
        accent_color : 0x5865F2,
        components: [
          component.text([
            "## # - Desktop Copy",
            "```",
            clean_result,
            "```",
          ]),
          component.divider(1),
          component.section({
            content   : footer,
            accessory : component.secondary_button(
              "Mobile Copy",
              `bypass_mobile_copy:${options.requested_by_user_id}:${options.request_token}`
            ),
          }),
        ],
      }),
      component.container({
        accent_color : 0x5865F2,
        components: [
          component.section({
            content   : "Want to invite the bot to your server? Click here ->",
            accessory : component.link_button("Invite BOT", options.invite_url),
          }),
        ],
      }),
    ],
  })
}
