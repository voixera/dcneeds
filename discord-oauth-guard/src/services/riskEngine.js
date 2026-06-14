class RiskEngine {
  score(context, config) {
    const breakdown = [];
    const reasons = [];
    const keywords = new Set(context.keywordMatches || []);

    const add = (points, code, reason) => {
      if (!points) return;
      breakdown.push({ points, code, reason });
      reasons.push(`+${points} ${reason}`);
    };

    if (keywords.size === 1) {
      add(config.weights.scamKeyword, 'scam_keyword', 'Scam keyword detected');
    }

    if (keywords.size >= 2) {
      add(config.weights.multipleScamKeywords, 'multiple_scam_keywords', 'Multiple scam keywords detected');
    }

    if (context.mentionsEveryone) {
      add(config.weights.mentionEveryone, 'mention_everyone', '@everyone or @here abuse');
    }

    if (context.massUserMentionCount >= config.spam.massMentionThreshold) {
      add(config.weights.massUserMention, 'mass_user_mentions', `Mass user mentions (${context.massUserMentionCount})`);
    }

    if (context.hasSuspiciousAttachment && (context.mentionsEveryone || context.massUserMentionCount > 0)) {
      add(config.weights.suspiciousAttachmentWithMention, 'suspicious_attachment_mentions', 'Suspicious attachment with mentions');
    }

    if (context.repeatedImageMatches?.length) {
      add(config.weights.repeatedImage, 'repeated_image', 'Same or similar image was seen before');
    }

    if (context.isVeryNewAccount) {
      add(config.weights.veryNewAccount, 'very_new_account', 'Account is very new');
    }

    if (context.spamPatterns?.hasMultiChannelSpam) {
      add(config.weights.spamAcrossChannels, 'spam_across_channels', 'Similar image activity across multiple channels');
    }

    if (context.spamPatterns?.hasRepeatedUserImage) {
      add(config.weights.repeatedImageByUser, 'repeated_user_image', 'User repeated the same image recently');
    }

    if (context.spamPatterns?.hasAttachmentBurst) {
      add(config.weights.attachmentBurst, 'attachment_burst', 'Many attachments in a short time window');
    }

    const score = Math.min(100, breakdown.reduce((sum, item) => sum + item.points, 0));
    const severity = score >= config.thresholds.malicious
      ? 'malicious'
      : score >= config.thresholds.suspicious
        ? 'suspicious'
        : 'safe';

    return {
      score,
      severity,
      breakdown,
      reasons,
      keywords: [...keywords]
    };
  }
}

module.exports = RiskEngine;
