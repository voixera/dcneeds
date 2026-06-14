const {
  entersState,
  getVoiceConnection,
  joinVoiceChannel,
  VoiceConnectionStatus
} = require('@discordjs/voice');
const {
  AuditLogEvent,
  ChannelType,
  EmbedBuilder,
  PermissionFlagsBits
} = require('discord.js');
const { colors, truncate } = require('../utils/embeds');
const logger = require('../utils/logger');

const auditWindowMs = 8000;

class VoiceGuardService {
  constructor({ client, configService, logChannelService }) {
    this.client = client;
    this.configService = configService;
    this.logChannelService = logChannelService;
    this.expectedDisconnects = new Set();
    this.reconnectTimers = new Map();
    this.trackedConnections = new WeakSet();
  }

  async join(channel, options = {}) {
    if (!channel || channel.type !== ChannelType.GuildVoice) {
      throw new Error('Target channel must be a voice channel.');
    }

    const botMember = channel.guild.members.me;
    const permissions = channel.permissionsFor(botMember);
    if (!permissions?.has(PermissionFlagsBits.ViewChannel) || !permissions?.has(PermissionFlagsBits.Connect)) {
      throw new Error(`Missing permission to join #${channel.name}.`);
    }

    const connection = joinVoiceChannel({
      channelId: channel.id,
      guildId: channel.guild.id,
      adapterCreator: channel.guild.voiceAdapterCreator,
      selfDeaf: true,
      selfMute: true
    });

    this.trackConnection(connection, channel.guild);
    await entersState(connection, VoiceConnectionStatus.Ready, 20_000);

    if (options.persist !== false) {
      await this.configService.set(channel.guild.id, 'voiceChannelId', channel.id);
    }

    if (options.notify) {
      await this.sendNotice(channel.guild, {
        title: 'Voice Guard Joined',
        description: `Bot joined <#${channel.id}> with self mute and self deafen enabled.`,
        color: colors.info,
        fields: [
          { name: 'Requested By', value: options.actorId ? `<@${options.actorId}>` : 'System', inline: true }
        ]
      });
    }

    return connection;
  }

  async leave(guild, options = {}) {
    this.expectedDisconnects.add(guild.id);
    const connection = getVoiceConnection(guild.id);
    if (connection) connection.destroy();

    if (options.clear !== false) {
      await this.configService.set(guild.id, 'voiceChannelId', '');
    }

    if (options.notify) {
      await this.sendNotice(guild, {
        title: 'Voice Guard Left',
        description: 'Persistent voice channel was cleared and the bot left voice.',
        color: colors.info,
        fields: [
          { name: 'Requested By', value: options.actorId ? `<@${options.actorId}>` : 'System', inline: true }
        ]
      });
    }
  }

  async setNotifyChannel(guildId, channelId) {
    await this.configService.set(guildId, 'voiceNotifyChannelId', channelId);
  }

  async restoreConfiguredConnections() {
    for (const guild of this.client.guilds.cache.values()) {
      const config = await this.configService.getGuildConfig(guild.id);
      if (!config.voice.channelId) continue;

      const channel = await guild.channels.fetch(config.voice.channelId).catch(() => null);
      if (!channel) {
        await this.sendNotice(guild, {
          title: 'Voice Guard Restore Failed',
          description: `Configured voice channel \`${config.voice.channelId}\` no longer exists.`,
          color: colors.suspicious
        });
        continue;
      }

      await this.join(channel, { persist: false }).catch((error) => {
        logger.warn(`Failed to restore voice guard in ${guild.id}:`, error.message);
      });
    }
  }

  async handleVoiceStateUpdate(oldState, newState) {
    if (oldState.member?.id !== this.client.user?.id) return;

    const guild = oldState.guild || newState.guild;
    const config = await this.configService.getGuildConfig(guild.id);
    const oldChannelId = oldState.channelId;
    const newChannelId = newState.channelId;

    if (oldChannelId && !newChannelId) {
      if (this.expectedDisconnects.delete(guild.id)) return;

      const audit = await this.findRecentVoiceAudit(guild);
      await this.sendNotice(guild, {
        title: 'Voice Guard Disconnected',
        description: `Bot was disconnected from <#${oldChannelId}>.`,
        color: colors.malicious,
        fields: [
          { name: 'Detected Executor', value: audit?.executor ? `<@${audit.executor.id}>` : 'Unknown or network disconnect', inline: true },
          { name: 'Audit Event', value: audit?.event || 'Unavailable', inline: true },
          { name: 'Auto Rejoin', value: config.voice.channelId ? `<#${config.voice.channelId}>` : 'No saved voice channel', inline: true }
        ]
      });

      await this.scheduleRejoin(guild, config);
      return;
    }

    if (oldChannelId && newChannelId && oldChannelId !== newChannelId && config.voice.channelId && newChannelId !== config.voice.channelId) {
      const audit = await this.findRecentVoiceAudit(guild);
      await this.sendNotice(guild, {
        title: 'Voice Guard Moved',
        description: `Bot was moved from <#${oldChannelId}> to <#${newChannelId}>.`,
        color: colors.suspicious,
        fields: [
          { name: 'Detected Executor', value: audit?.executor ? `<@${audit.executor.id}>` : 'Unknown', inline: true },
          { name: 'Saved Channel', value: `<#${config.voice.channelId}>`, inline: true }
        ]
      });

      await this.scheduleRejoin(guild, config);
    }
  }

  trackConnection(connection, guild) {
    if (this.trackedConnections.has(connection)) return;
    this.trackedConnections.add(connection);

    connection.on('stateChange', async (_, newState) => {
      if (newState.status !== VoiceConnectionStatus.Disconnected) return;

      try {
        await Promise.race([
          entersState(connection, VoiceConnectionStatus.Signalling, 5000),
          entersState(connection, VoiceConnectionStatus.Connecting, 5000)
        ]);
      } catch {
        const config = await this.configService.getGuildConfig(guild.id);
        await this.scheduleRejoin(guild, config);
      }
    });

    connection.on('error', (error) => {
      logger.warn(`Voice connection error in ${guild.id}:`, error.message);
    });
  }

  async scheduleRejoin(guild, config) {
    if (!config.voice.channelId || this.reconnectTimers.has(guild.id)) return;

    const timer = setTimeout(async () => {
      this.reconnectTimers.delete(guild.id);
      const latestConfig = await this.configService.getGuildConfig(guild.id);
      if (!latestConfig.voice.channelId) return;

      const channel = await guild.channels.fetch(latestConfig.voice.channelId).catch(() => null);
      if (!channel) {
        await this.sendNotice(guild, {
          title: 'Voice Guard Rejoin Failed',
          description: `Saved voice channel \`${latestConfig.voice.channelId}\` was not found.`,
          color: colors.malicious
        });
        return;
      }

      await this.join(channel, { persist: false })
        .then(() => this.sendNotice(guild, {
          title: 'Voice Guard Rejoined',
          description: `Bot rejoined <#${channel.id}> and stayed muted/deafened.`,
          color: colors.safe
        }))
        .catch((error) => this.sendNotice(guild, {
          title: 'Voice Guard Rejoin Failed',
          description: truncate(error.message, 1000),
          color: colors.malicious
        }));
    }, config.voice.reconnectDelayMs);

    timer.unref();
    this.reconnectTimers.set(guild.id, timer);
  }

  async sendNotice(guild, { title, description, color, fields = [] }) {
    const config = await this.configService.getGuildConfig(guild.id);
    const embed = new EmbedBuilder()
      .setColor(color)
      .setTitle(title)
      .setDescription(description)
      .setTimestamp()
      .setFooter({ text: 'discord-oauth-guard voice guard' });

    if (fields.length) {
      embed.addFields(...fields);
    }

    const notifyChannelId = config.voice.notifyChannelId;
    if (notifyChannelId) {
      const channel = await guild.channels.fetch(notifyChannelId).catch(() => null);
      if (channel?.isTextBased()) {
        await channel.send({ embeds: [embed] }).catch((error) => {
          logger.warn(`Failed to send voice notice to ${notifyChannelId}:`, error.message);
        });
        return;
      }
    }

    await this.logChannelService.send(guild, embed, config).catch((error) => {
      logger.warn(`Failed to send voice notice fallback in ${guild.id}:`, error.message);
    });
  }

  async findRecentVoiceAudit(guild) {
    const botMember = guild.members.me;
    if (!botMember?.permissions.has(PermissionFlagsBits.ViewAuditLog)) return null;

    for (const type of [AuditLogEvent.MemberDisconnect, AuditLogEvent.MemberMove]) {
      const logs = await guild.fetchAuditLogs({ type, limit: 3 }).catch(() => null);
      const entry = logs?.entries.find((item) => Date.now() - item.createdTimestamp <= auditWindowMs);
      if (entry) {
        return {
          executor: entry.executor,
          event: type === AuditLogEvent.MemberDisconnect ? 'Member Disconnect' : 'Member Move'
        };
      }
    }

    return null;
  }
}

module.exports = VoiceGuardService;
