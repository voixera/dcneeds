const path = require("path");
require("dotenv").config({ path: path.resolve(__dirname, "..", "..", ".env") });

function firstValue(...values) {
  return values.find((value) => value && String(value).trim().length > 0);
}

function decodeClientIdFromToken(token) {
  if (!token || !token.includes(".")) return null;

  try {
    const [encodedClientId] = token.split(".");
    const decoded = Buffer.from(encodedClientId, "base64").toString("utf8");
    return /^\d+$/.test(decoded) ? decoded : null;
  } catch {
    return null;
  }
}

function toInteger(value, fallback) {
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) ? parsed : fallback;
}

const token = firstValue(
  process.env.DISCORD_FIFA_TOKEN,
  process.env.DISCORD_BOT_TOKEN,
  process.env.DISCORD_TOKEN,
);
const clientId = firstValue(
  process.env.DISCORD_FIFA_CLIENT_ID,
  process.env.CLIENT_ID,
  decodeClientIdFromToken(token),
);

const config = {
  token,
  clientId,
  guildId: firstValue(process.env.DISCORD_FIFA_GUILD_ID, process.env.GUILD_ID) || null,
  notificationChannelId:
    firstValue(
      process.env.DISCORD_FIFA_NOTIFICATION_CHANNEL_ID,
      process.env.NOTIFICATION_CHANNEL_ID,
    ) || null,
  timezone:
    firstValue(process.env.DISCORD_FIFA_TIMEZONE, process.env.TIMEZONE) ||
    "Asia/Jakarta",
  notificationLookaheadMinutes: toInteger(
    firstValue(
      process.env.DISCORD_FIFA_NOTIFICATION_LOOKAHEAD_MINUTES,
      process.env.NOTIFICATION_LOOKAHEAD_MINUTES,
    ),
    30,
  ),
  notificationIntervalMs:
    toInteger(
      firstValue(
        process.env.DISCORD_FIFA_NOTIFICATION_INTERVAL_SECONDS,
        process.env.NOTIFICATION_INTERVAL_SECONDS,
      ),
      60,
    ) * 1000,
  isDeployOnly: process.argv.includes("--deploy-only"),
};

function assertBotConfig() {
  const missing = [];

  if (!config.token) missing.push("DISCORD_FIFA_TOKEN atau DISCORD_BOT_TOKEN");
  if (!config.clientId) missing.push("DISCORD_FIFA_CLIENT_ID");

  if (missing.length > 0) {
    throw new Error(
      `Konfigurasi .env belum lengkap: ${missing.join(", ")} wajib diisi.`,
    );
  }
}

module.exports = {
  ...config,
  assertBotConfig,
};
