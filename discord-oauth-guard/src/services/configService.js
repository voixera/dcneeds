const defaultConfig = require('../config/defaultConfig');

function toBool(value, fallback) {
  if (value === undefined || value === null || value === '') return fallback;
  return ['1', 'true', 'yes', 'on'].includes(String(value).toLowerCase());
}

function toInt(value, fallback) {
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) ? parsed : fallback;
}

class ConfigService {
  constructor(database) {
    this.database = database;
  }

  async getGuildConfig(guildId) {
    const overrides = await this.database.getGuildConfig(guildId);
    const keywordOverride = overrides.scamKeywords
      ? overrides.scamKeywords.split('\n').map((keyword) => keyword.trim()).filter(Boolean)
      : defaultConfig.scamKeywords;

    return {
      ...defaultConfig,
      scamKeywords: keywordOverride,
      thresholds: {
        suspicious: toInt(overrides.suspiciousThreshold, defaultConfig.thresholds.suspicious),
        malicious: toInt(overrides.maliciousThreshold, defaultConfig.thresholds.malicious)
      },
      moderation: {
        ...defaultConfig.moderation,
        deleteMaliciousMessages: toBool(
          overrides.deleteMaliciousMessages,
          defaultConfig.moderation.deleteMaliciousMessages
        ),
        enableAutoTimeout: toBool(overrides.enableAutoTimeout, defaultConfig.moderation.enableAutoTimeout),
        timeoutDurationMs: toInt(overrides.timeoutDurationMs, defaultConfig.moderation.timeoutDurationMs),
        warningDeleteAfterMs: toInt(
          overrides.warningDeleteAfterMs,
          defaultConfig.moderation.warningDeleteAfterMs
        )
      },
      images: {
        ...defaultConfig.images,
        similarityDistance: toInt(overrides.imageSimilarityDistance, defaultConfig.images.similarityDistance)
      },
      spam: {
        ...defaultConfig.spam,
        attachmentThreshold: toInt(overrides.spamAttachmentThreshold, defaultConfig.spam.attachmentThreshold),
        channelThreshold: toInt(overrides.spamChannelThreshold, defaultConfig.spam.channelThreshold),
        massMentionThreshold: toInt(overrides.massMentionThreshold, defaultConfig.spam.massMentionThreshold)
      },
      voice: {
        ...defaultConfig.voice,
        channelId: overrides.voiceChannelId || defaultConfig.voice.channelId,
        notifyChannelId: overrides.voiceNotifyChannelId || defaultConfig.voice.notifyChannelId,
        reconnectDelayMs: toInt(overrides.voiceReconnectDelayMs, defaultConfig.voice.reconnectDelayMs)
      }
    };
  }

  async set(guildId, key, value) {
    await this.database.setConfig(guildId, key, value);
  }

  async resetKeywords(guildId) {
    await this.database.setConfig(guildId, 'scamKeywords', defaultConfig.scamKeywords.join('\n'));
  }
}

module.exports = ConfigService;
