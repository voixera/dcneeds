const env = require('./env');
const scamKeywords = require('./scamKeywords');

const second = 1000;
const day = 24 * 60 * 60 * 1000;

module.exports = {
  scamKeywords,
  thresholds: {
    suspicious: env.suspiciousThreshold,
    malicious: env.maliciousThreshold
  },
  weights: {
    scamKeyword: 20,
    multipleScamKeywords: 40,
    mentionEveryone: 30,
    massUserMention: 20,
    suspiciousAttachmentWithMention: 20,
    repeatedImage: 25,
    veryNewAccount: 20,
    spamAcrossChannels: 30,
    repeatedImageByUser: 20,
    attachmentBurst: 20,
    manualScanMatchedKeyword: 15
  },
  moderation: {
    deleteMaliciousMessages: env.deleteMaliciousMessages,
    enableAutoTimeout: env.enableAutoTimeout,
    timeoutDurationMs: env.timeoutDurationMs,
    warningDeleteAfterMs: env.warningDeleteAfterMs
  },
  logging: {
    logChannelName: env.logChannelName,
    modLogChannelId: env.modLogChannelId,
    createLogChannel: env.createLogChannel
  },
  images: {
    maxBytes: env.imageMaxBytes,
    similarityDistance: env.imageSimilarityDistance,
    allowedContentTypes: new Set(['image/png', 'image/jpeg', 'image/jpg', 'image/webp', 'image/gif'])
  },
  ocr: {
    enabled: env.ocrEnabled,
    language: env.ocrLanguage,
    timeoutMs: env.ocrTimeoutMs,
    maxConcurrent: env.ocrMaxConcurrent,
    imageMaxDimension: env.ocrImageMaxDimension
  },
  spam: {
    windowMs: env.spamWindowSeconds * second,
    attachmentThreshold: env.spamAttachmentThreshold,
    channelThreshold: env.spamChannelThreshold,
    massMentionThreshold: env.massMentionThreshold
  },
  accounts: {
    veryNewMs: env.newAccountDays * day
  },
  voice: {
    channelId: null,
    notifyChannelId: env.voiceNotifyChannelId,
    reconnectDelayMs: env.voiceReconnectDelayMs
  }
};
