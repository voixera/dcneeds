/*
 * Minimal launcher for the local bypass bot workspace.
 * Mirrors the reference repository layout with a single active startup target.
 */

import { start_bypass_bot } from "./startup/bypass_bot"
import { start_mock_bypass_api } from "./startup/mock_bypass_api"

if (process.env.NODE_ENV === "production") {
  console.log = () => {}
}

void Promise.resolve()
  .then(async () => {
    if ((process.env.MOCK_BYPASS_API_AUTOSTART || "true").toLowerCase() !== "false") {
      await start_mock_bypass_api()
    }
  })
  .then(() => start_bypass_bot())
  .then(() => {
    console.info("[ - LAUNCHER - ] Bypass bot startup invoked")
  })
  .catch((error) => {
    console.error("[ - LAUNCHER - ] Failed to start bypass bot:", error)
    process.exit(1)
  })
