const { SlashCommandBuilder, EmbedBuilder, MessageFlags, PermissionFlagsBits } = require('discord.js');
const { colors } = require('../utils/embeds');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('scamstats')
    .setDescription('Show OAuth Guard detection statistics.')
    .setDefaultMemberPermissions(PermissionFlagsBits.ModerateMembers)
    .addIntegerOption((option) =>
      option
        .setName('days')
        .setDescription('Number of days to include.')
        .setMinValue(1)
        .setMaxValue(90)
    ),

  async execute(interaction, context) {
    await interaction.deferReply({ flags: MessageFlags.Ephemeral });
    const days = interaction.options.getInteger('days') || 7;
    const stats = await context.database.getStats(interaction.guildId, days);
    const totals = Object.fromEntries(stats.totals.map((row) => [row.severity, row.count]));

    const topUsers = stats.topUsers.length
      ? stats.topUsers.map((row, index) => `${index + 1}. <@${row.user_id}> - ${row.count} hits, max ${row.max_score}`).join('\n')
      : 'No detections yet.';

    const embed = new EmbedBuilder()
      .setColor(colors.info)
      .setTitle('OAuth Guard Stats')
      .setDescription(`Detection summary for the last **${days}** day(s).`)
      .addFields(
        { name: 'Total Detections', value: String(stats.recentCount), inline: true },
        { name: 'Stored Hashes', value: String(stats.hashCount), inline: true },
        { name: 'Safe', value: String(totals.safe || 0), inline: true },
        { name: 'Suspicious', value: String(totals.suspicious || 0), inline: true },
        { name: 'Malicious', value: String(totals.malicious || 0), inline: true },
        { name: 'Top Users', value: topUsers, inline: false }
      )
      .setTimestamp();

    await interaction.editReply({ embeds: [embed] });
  }
};
