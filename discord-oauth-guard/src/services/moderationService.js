const { PermissionFlagsBits } = require('discord.js');
const { buildDetectionEmbed, buildSimpleEmbed, colors } = require('../utils/embeds');
const { msToHuman } = require('../utils/time');
const logger = require('../utils/logger');

class ModerationService {
  constructor({ database, logChannelService }) {
    this.database = database;
    this.logChannelService = logChannelService;
  }

  async handleDetection({ message, risk, config, ocrText, attachmentUrls, imageHashes }) {
    if (risk.severity === 'safe') return;

    let actionTaken = 'Logged';

    await this.database.saveRiskScore({
      guildId: message.guild.id,
      userId: message.author.id,
      messageId: message.id,
      score: risk.score,
      severity: risk.severity,
      breakdown: risk.breakdown
    });

    await this.database.saveStrike({
      guildId: message.guild.id,
      userId: message.author.id,
      messageId: message.id,
      riskScore: risk.score,
      severity: risk.severity,
      reason: risk.reasons.join('; ')
    });

    if (risk.severity === 'malicious') {
      actionTaken = await this.handleMalicious({ message, risk, config });
    } else {
      actionTaken = await this.handleSuspicious({ message, risk, config });
    }

    await this.database.saveDetectedScam({
      guildId: message.guild.id,
      messageId: message.id,
      userId: message.author.id,
      username: message.author.tag,
      channelId: message.channel.id,
      riskScore: risk.score,
      severity: risk.severity,
      reasons: risk.reasons,
      keywords: risk.keywords,
      attachmentUrls,
      ocrText,
      imageHashes,
      actionTaken
    });

    const embed = buildDetectionEmbed({ message, risk, actionTaken, ocrText, attachmentUrls });
    await this.logChannelService.send(message.guild, embed, config).catch((error) => {
      logger.warn('Failed to send moderation log:', error.message);
    });
  }

  async handleMalicious({ message, risk, config }) {
    const actions = [];

    if (config.moderation.deleteMaliciousMessages && message.deletable) {
      await message.delete().then(() => actions.push('message deleted')).catch((error) => {
        logger.warn(`Failed to delete message ${message.id}:`, error.message);
      });
    }

    const member = await message.guild.members.fetch(message.author.id).catch(() => null);
    const botMember = message.guild.members.me;
    const canTimeout = config.moderation.enableAutoTimeout &&
      member?.moderatable &&
      botMember?.permissions.has(PermissionFlagsBits.ModerateMembers);

    if (canTimeout) {
      const reason = `OAuth Guard malicious score ${risk.score}: ${risk.keywords.join(', ') || 'suspicious image spam'}`;
      await member.timeout(config.moderation.timeoutDurationMs, reason)
        .then(async () => {
          actions.push(`timeout ${msToHuman(config.moderation.timeoutDurationMs)}`);
          await this.database.saveTimeout({
            guildId: message.guild.id,
            userId: message.author.id,
            durationMs: config.moderation.timeoutDurationMs,
            reason
          });
        })
        .catch((error) => logger.warn(`Failed to timeout ${message.author.id}:`, error.message));
    }

    return actions.length ? actions.join(', ') : 'malicious logged';
  }

  async handleSuspicious({ message, risk, config }) {
    const embed = buildSimpleEmbed(
      'Suspicious Attachment Warning',
      `${message.author}, your image was flagged for review. Please avoid posting giveaway, reward, Nitro, crypto, or external claim images unless a moderator confirms they are safe.\n\nRisk score: **${risk.score}/100**`,
      colors.suspicious
    );

    const warning = await message.reply({ embeds: [embed], allowedMentions: { users: [message.author.id] } })
      .catch((error) => {
        logger.warn(`Failed to send warning for ${message.id}:`, error.message);
        return null;
      });

    if (warning && config.moderation.warningDeleteAfterMs > 0) {
      setTimeout(() => {
        warning.delete().catch(() => {});
      }, config.moderation.warningDeleteAfterMs).unref();
    }

    return 'warning sent';
  }
}

module.exports = ModerationService;
