const { isImageAttachment, downloadAttachment, safeUnlink } = require('../utils/attachments');
const logger = require('../utils/logger');

class ScanService {
  constructor({
    database,
    configService,
    ocrService,
    imageHashService,
    scamDetector,
    spamPatternService,
    riskEngine,
    moderationService
  }) {
    this.database = database;
    this.configService = configService;
    this.ocrService = ocrService;
    this.imageHashService = imageHashService;
    this.scamDetector = scamDetector;
    this.spamPatternService = spamPatternService;
    this.riskEngine = riskEngine;
    this.moderationService = moderationService;
  }

  async analyzeMessage(message) {
    if (!message.guild || message.author.bot) return null;

    const imageAttachments = [...message.attachments.values()].filter(isImageAttachment);
    if (!imageAttachments.length) return null;

    const config = await this.configService.getGuildConfig(message.guild.id);
    const result = await this.scan({
      guildId: message.guild.id,
      userId: message.author.id,
      userCreatedTimestamp: message.author.createdTimestamp,
      channelId: message.channel.id,
      messageId: message.id,
      text: message.content || '',
      attachments: imageAttachments,
      mentionsEveryone: message.mentions.everyone,
      massUserMentionCount: message.mentions.users.size,
      config,
      persistHashes: true,
      persistActivity: true
    });

    await this.moderationService.handleDetection({
      message,
      risk: result.risk,
      config,
      ocrText: result.ocrText,
      attachmentUrls: result.attachmentUrls,
      imageHashes: result.imageHashes
    });

    return result;
  }

  async scanManual({ guildId, userId, userCreatedTimestamp, channelId, text = '', attachments = [] }) {
    const imageAttachments = attachments.filter(isImageAttachment);
    const config = await this.configService.getGuildConfig(guildId);

    return this.scan({
      guildId,
      userId,
      userCreatedTimestamp,
      channelId,
      messageId: `manual-${Date.now()}`,
      text,
      attachments: imageAttachments,
      mentionsEveryone: /@everyone|@here/i.test(text),
      massUserMentionCount: (text.match(/<@!?\d+>/g) || []).length,
      config,
      persistHashes: false,
      persistActivity: false
    });
  }

  async scan({
    guildId,
    userId,
    userCreatedTimestamp,
    channelId,
    messageId,
    text,
    attachments,
    mentionsEveryone,
    massUserMentionCount,
    config,
    persistHashes,
    persistActivity
  }) {
    const attachmentUrls = attachments.map((attachment) => attachment.url);
    const imageHashes = [];
    const repeatedImageMatches = [];
    const ocrTexts = [];

    const previousHashes = await this.database.getRecentImageHashes(guildId);

    for (const attachment of attachments) {
      let filePath;
      try {
        filePath = await downloadAttachment(attachment);
        const [ocrText, hash] = await Promise.all([
          this.ocrService.extractText(filePath, config.ocr),
          this.imageHashService.generateHash(filePath)
        ]);

        if (ocrText) ocrTexts.push(ocrText);
        if (hash) {
          imageHashes.push(hash);
          const similar = this.imageHashService.findSimilar(hash, previousHashes, config.images.similarityDistance);
          if (similar) repeatedImageMatches.push(similar);

          if (persistHashes) {
            await this.database.saveImageHash({
              guildId,
              hash,
              messageId,
              userId,
              channelId,
              attachmentUrl: attachment.url
            });
          }
        }
      } catch (error) {
        logger.warn(`Failed to process attachment ${attachment.url}:`, error.message);
      } finally {
        await safeUnlink(filePath);
      }
    }

    let spamPatterns = null;
    if (persistActivity) {
      spamPatterns = await this.spamPatternService.analyze({
        guildId,
        userId,
        channelId,
        messageId,
        attachmentHashes: imageHashes,
        attachmentCount: attachments.length,
        config
      });
    }

    const ocrText = ocrTexts.join('\n\n');
    const detection = this.scamDetector.scanText(`${text}\n${ocrText}`, config.scamKeywords);
    const hasSuspiciousAttachment = detection.hasScamKeyword || repeatedImageMatches.length > 0;
    const isVeryNewAccount = Date.now() - userCreatedTimestamp <= config.accounts.veryNewMs;

    const risk = this.riskEngine.score({
      keywordMatches: detection.matchedKeywords,
      mentionsEveryone,
      massUserMentionCount,
      hasSuspiciousAttachment,
      repeatedImageMatches,
      isVeryNewAccount,
      spamPatterns
    }, config);

    return {
      risk,
      ocrText,
      attachmentUrls,
      imageHashes,
      repeatedImageMatches,
      spamPatterns,
      detection
    };
  }
}

module.exports = ScanService;
