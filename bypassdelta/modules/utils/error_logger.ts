import { Client } from "discord.js"

export async function log_error(
  _client: Client,
  error: Error,
  scope: string,
  context: Record<string, unknown> = {}
): Promise<void> {
  console.error(`[ - ${scope} - ]`, error, context)
}
