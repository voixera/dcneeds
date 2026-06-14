const { SlashCommandBuilder, EmbedBuilder, MessageFlags, PermissionFlagsBits } = require('discord.js');
const { colors, truncate } = require('../utils/embeds');
const { toDiscordTimestamp } = require('../utils/time');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('scamlogs')
    .setDescription('Show recent OAuth Guard detections.')
    .setDefaultMemberPermissions(PermissionFlagsBits.ModerateMembers)
    .addIntegerOption((option) =>
      option
        .setName('limit')
        .setDescription('Number of logs to show.')
        .setMinValue(1)
        .setMaxValue(10)
    ),

  async execute(interaction, context) {
    await interaction.deferReply({ flags: MessageFlags.Ephemeral });
    const limit = interaction.options.getInteger('limit') || 5;
    const logs = await context.database.getRecentScams(interaction.guildId, limit);

    const embed = new EmbedBuilder()
      .setColor(colors.info)
      .setTitle('Recent Scam Logs')
      .setTimestamp();

    if (!logs.length) {
      embed.setDescription('No detections have been stored yet.');
    } else {
      for (const log of logs) {
        embed.addFields({
          name: `${log.severity.toUpperCase()} - ${log.risk_score}/100 - ${toDiscordTimestamp(log.created_at, 'R')}`,
          value: truncate(
            `User: <@${log.user_id}> (${log.user_id})\nChannel: <#${log.channel_id}>\nKeywords: ${log.keywords.join(', ') || 'None'}\nReasons: ${log.reasons.join('; ') || 'None'}`,
            1024
          ),
          inline: false
        });
      }
    }

    await interaction.editReply({ embeds: [embed] });
  }
};
