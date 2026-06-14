const {
  ChannelType,
  EmbedBuilder,
  MessageFlags,
  PermissionFlagsBits,
  SlashCommandBuilder
} = require('discord.js');
const { getVoiceConnection } = require('@discordjs/voice');
const { colors } = require('../utils/embeds');

function formatChannel(channelId, fallback = 'Not set') {
  return channelId ? `<#${channelId}>` : fallback;
}

module.exports = {
  data: new SlashCommandBuilder()
    .setName('joinvoice')
    .setDescription('Keep the bot in a voice channel with mute and deafen enabled.')
    .setDefaultMemberPermissions(PermissionFlagsBits.ManageGuild)
    .addSubcommand((subcommand) =>
      subcommand
        .setName('join')
        .setDescription('Join and stay in a voice channel.')
        .addChannelOption((option) =>
          option
            .setName('channel')
            .setDescription('Voice channel to join. Defaults to your current voice channel.')
            .addChannelTypes(ChannelType.GuildVoice)
        )
    )
    .addSubcommand((subcommand) =>
      subcommand
        .setName('notify')
        .setDescription('Set the text channel for voice disconnect and kick notifications.')
        .addChannelOption((option) =>
          option
            .setName('channel')
            .setDescription('Text channel that will receive voice guard notifications.')
            .setRequired(true)
            .addChannelTypes(ChannelType.GuildText, ChannelType.GuildAnnouncement)
        )
    )
    .addSubcommand((subcommand) =>
      subcommand
        .setName('setchannel')
        .setDescription('Alias for notify: set where voice guard notifications are sent.')
        .addChannelOption((option) =>
          option
            .setName('channel')
            .setDescription('Text channel that will receive voice guard notifications.')
            .setRequired(true)
            .addChannelTypes(ChannelType.GuildText, ChannelType.GuildAnnouncement)
        )
    )
    .addSubcommand((subcommand) =>
      subcommand
        .setName('status')
        .setDescription('Show voice guard status.')
    )
    .addSubcommand((subcommand) =>
      subcommand
        .setName('leave')
        .setDescription('Leave voice and stop persistent auto-rejoin.')
    ),

  async execute(interaction, context) {
    await interaction.deferReply({ flags: MessageFlags.Ephemeral });
    const subcommand = interaction.options.getSubcommand();

    if (subcommand === 'join') {
      const selectedChannel = interaction.options.getChannel('channel');
      const member = await interaction.guild.members.fetch(interaction.user.id);
      const targetChannel = selectedChannel || member.voice.channel;

      if (!targetChannel) {
        await interaction.editReply('Join a voice channel first, or provide the `channel` option.');
        return;
      }

      await context.voiceGuardService.join(targetChannel, {
        actorId: interaction.user.id,
        notify: true
      });

      const embed = new EmbedBuilder()
        .setColor(colors.safe)
        .setTitle('Voice Guard Active')
        .setDescription(`Joined ${targetChannel} with self mute and self deafen enabled.\nThe bot will try to stay in this channel and rejoin if disconnected.`)
        .setTimestamp();

      await interaction.editReply({ embeds: [embed] });
      return;
    }

    if (subcommand === 'notify' || subcommand === 'setchannel') {
      const channel = interaction.options.getChannel('channel', true);
      await context.voiceGuardService.setNotifyChannel(interaction.guildId, channel.id);

      const embed = new EmbedBuilder()
        .setColor(colors.info)
        .setTitle('Voice Notification Channel Set')
        .setDescription(`Voice disconnect, kick, move, and rejoin notifications will be sent to ${channel}.`)
        .setTimestamp();

      await interaction.editReply({ embeds: [embed] });
      return;
    }

    if (subcommand === 'leave') {
      await context.voiceGuardService.leave(interaction.guild, {
        actorId: interaction.user.id,
        notify: true
      });

      const embed = new EmbedBuilder()
        .setColor(colors.info)
        .setTitle('Voice Guard Disabled')
        .setDescription('Bot left voice and persistent auto-rejoin was cleared.')
        .setTimestamp();

      await interaction.editReply({ embeds: [embed] });
      return;
    }

    const config = await context.configService.getGuildConfig(interaction.guildId);
    const connection = getVoiceConnection(interaction.guildId);
    const embed = new EmbedBuilder()
      .setColor(colors.info)
      .setTitle('Voice Guard Status')
      .addFields(
        { name: 'Saved Voice Channel', value: formatChannel(config.voice.channelId), inline: true },
        { name: 'Notify Channel', value: formatChannel(config.voice.notifyChannelId), inline: true },
        { name: 'Connection', value: connection ? connection.state.status : 'not connected', inline: true },
        { name: 'Mute / Deafen', value: 'self mute: true\nself deafen: true', inline: true },
        { name: 'Reconnect Delay', value: `${config.voice.reconnectDelayMs}ms`, inline: true }
      )
      .setTimestamp();

    await interaction.editReply({ embeds: [embed] });
  }
};
