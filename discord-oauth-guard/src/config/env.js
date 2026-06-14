const path = require('node:path');
const dotenv = require('dotenv');

dotenv.config();

function toBool(value, fallback = false) {
  if (value === undefined || value === null || value === '') return fallback;
  return ['1', 'true', 'yes', 'on'].includes(String(value).toLowerCase());
}

function toInt(value, fallback) {
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function toPath(value, fallback) {
  return path.resolve(process.cwd(), value || fallback);
}

module.exports = {
  discordToken: process.env.DISCORD_TOKEN,
  clientId: process.env.CLIENT_ID,
  guildId: process.env.GUILD_ID || null,
  databasePath: toPath(process.env.DATABASE_PATH, './data/oauth-guard.sqlite'),
  tempDir: toPath(process.env.TEMP_DIR, './data/tmp'),
  logLevel: process.env.LOG_LEVEL || 'info',
  logChannelName: process.env.LOG_CHANNEL_NAME || 'oauth-guard-logs',
  modLogChannelId: process.env.MOD_LOG_CHANNEL_ID || null,
  createLogChannel: toBool(process.env.CREATE_LOG_CHANNEL, true),
  suspiciousThreshold: toInt(process.env.SUSPICIOUS_THRESHOLD, 40),
  maliciousThreshold: toInt(process.env.MALICIOUS_THRESHOLD, 70),
  deleteMaliciousMessages: toBool(process.env.DELETE_MALICIOUS_MESSAGES, true),
  enableAutoTimeout: toBool(process.env.ENABLE_AUTO_TIMEOUT, true),
  timeoutDurationMs: toInt(process.env.TIMEOUT_DURATION_MS, 60 * 60 * 1000),
  warningDeleteAfterMs: toInt(process.env.WARNING_DELETE_AFTER_MS, 15 * 1000),
  ocrLanguage: process.env.OCR_LANGUAGE || 'eng',
  ocrTimeoutMs: toInt(process.env.OCR_TIMEOUT_MS, 30 * 1000),
  imageMaxBytes: toInt(process.env.IMAGE_MAX_BYTES, 8 * 1024 * 1024),
  imageSimilarityDistance: toInt(process.env.IMAGE_SIMILARITY_DISTANCE, 8),
  newAccountDays: toInt(process.env.NEW_ACCOUNT_DAYS, 7),
  spamWindowSeconds: toInt(process.env.SPAM_WINDOW_SECONDS, 120),
  spamAttachmentThreshold: toInt(process.env.SPAM_ATTACHMENT_THRESHOLD, 4),
  spamChannelThreshold: toInt(process.env.SPAM_CHANNEL_THRESHOLD, 3),
  massMentionThreshold: toInt(process.env.MASS_MENTION_THRESHOLD, 5)
};
