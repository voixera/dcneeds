import { start_bypass_bot } from "./startup/bypass_bot"

if (process.env.NODE_ENV === "production") {
  console.log = () => {}
}

void Promise.resolve()
  .then(() => start_bypass_bot())
  .then(() => {
    console.info("[ - LAUNCHER - ] Bypass bot startup invoked")
  })
  .catch((error) => {
    console.error("[ - LAUNCHER - ] Failed to start bypass bot:", error)
    process.exit(1)
  })
