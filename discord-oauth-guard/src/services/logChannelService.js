const { ChannelType, PermissionFlagsBits } = require('discord.js');
const defaultConfig = require('../config/defaultConfig');
const logger = require('../utils/logger');

class LogChannelService {
  constructor(client) {
    this.client = client;
    this.cache = new Map();
  }

  async resolve(guild, config = defaultConfig) {
    if (!guild) return null;
    if (this.cache.has(guild.id)) return this.cache.get(guild.id);

    if (config.logging.modLogChannelId) {
      const channel = await guild.channels.fetch(config.logging.modLogChannelId).catch(() => null);
      if (channel?.isTextBased()) {
        this.cache.set(guild.id, channel);
        return channel;
      }
    }

    const existing = guild.channels.cache.find(
      (channel) => channel.name === config.logging.logChannelName && channel.isTextBased()
    );
    if (existing) {
      this.cache.set(guild.id, existing);
      return existing;
    }

    if (!config.logging.createLogChannel) return null;

    const me = guild.members.me;
    if (!me?.permissions.has(PermissionFlagsBits.ManageChannels)) {
      logger.warn(`Missing ManageChannels in ${guild.id}; cannot create log channel.`);
      return null;
    }

    const channel = await guild.channels.create({
      name: config.logging.logChannelName,
      type: ChannelType.GuildText,
      topic: 'Automatic logs from discord-oauth-guard'
    });
    this.cache.set(guild.id, channel);
    return channel;
  }

  async send(guild, embed, config = defaultConfig) {
    const channel = await this.resolve(guild, config);
    if (!channel) return false;
    await channel.send({ embeds: [embed] });
    return true;
  }
}

module.exports = LogChannelService;
