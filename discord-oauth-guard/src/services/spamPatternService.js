const { sinceIso } = require('../utils/time');

function countMatchingHashes(currentHashes, activities) {
  const current = new Set(currentHashes);
  let repeated = 0;
  for (const activity of activities) {
    for (const hash of activity.attachment_hashes || []) {
      if (current.has(hash)) repeated += 1;
    }
  }
  return repeated;
}

class SpamPatternService {
  constructor(database) {
    this.database = database;
  }

  async analyze({ guildId, userId, channelId, messageId, attachmentHashes, attachmentCount, config }) {
    await this.database.saveUserActivity({
      guildId,
      userId,
      channelId,
      messageId,
      attachmentHashes,
      attachmentCount
    });

    const activities = await this.database.getRecentUserActivity(
      guildId,
      userId,
      sinceIso(config.spam.windowMs)
    );

    const totalAttachments = activities.reduce((sum, activity) => sum + activity.attachment_count, 0);
    const channels = new Set(activities.map((activity) => activity.channel_id));
    const repeatedHashCount = countMatchingHashes(attachmentHashes, activities.filter((a) => a.message_id !== messageId));

    return {
      totalAttachments,
      distinctChannelCount: channels.size,
      repeatedHashCount,
      hasAttachmentBurst: totalAttachments >= config.spam.attachmentThreshold,
      hasMultiChannelSpam: channels.size >= config.spam.channelThreshold,
      hasRepeatedUserImage: repeatedHashCount > 0
    };
  }
}

module.exports = SpamPatternService;
