const { SlashCommandBuilder, EmbedBuilder, MessageFlags, PermissionFlagsBits } = require('discord.js');
const { colors, truncate } = require('../utils/embeds');
const { toDiscordTimestamp } = require('../utils/time');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('scamhash')
    .setDescription('Inspect or remove stored image hashes.')
    .setDefaultMemberPermissions(PermissionFlagsBits.ModerateMembers)
    .addSubcommand((subcommand) =>
      subcommand
        .setName('list')
        .setDescription('List recent stored image hashes.')
        .addIntegerOption((option) =>
          option
            .setName('limit')
            .setDescription('Number of hashes to show.')
            .setMinValue(1)
            .setMaxValue(10)
        )
    )
    .addSubcommand((subcommand) =>
      subcommand
        .setName('delete')
        .setDescription('Delete a stored image hash.')
        .addStringOption((option) =>
          option
            .setName('hash')
            .setDescription('Exact perceptual hash to remove.')
            .setRequired(true)
            .setMinLength(16)
            .setMaxLength(128)
        )
    ),

  async execute(interaction, context) {
    await interaction.deferReply({ flags: MessageFlags.Ephemeral });
    const subcommand = interaction.options.getSubcommand();

    if (subcommand === 'delete') {
      const hash = interaction.options.getString('hash', true).trim();
      const deleted = await context.database.deleteHash(interaction.guildId, hash);
      const embed = new EmbedBuilder()
        .setColor(colors.info)
        .setTitle('Image Hash Deleted')
        .setDescription(`Deleted **${deleted}** row(s) for hash:\n\`${hash}\``)
        .setTimestamp();
      await interaction.editReply({ embeds: [embed] });
      return;
    }

    const limit = interaction.options.getInteger('limit') || 5;
    const hashes = await context.database.getRecentHashes(interaction.guildId, limit);
    const embed = new EmbedBuilder()
      .setColor(colors.info)
      .setTitle('Recent Image Hashes')
      .setTimestamp();

    if (!hashes.length) {
      embed.setDescription('No hashes have been stored yet.');
    } else {
      embed.setDescription(truncate(hashes.map((row) =>
        `\`${row.hash}\`\nUser: <@${row.user_id}> Channel: <#${row.channel_id}> ${toDiscordTimestamp(row.created_at, 'R')}`
      ).join('\n\n'), 4000));
    }

    await interaction.editReply({ embeds: [embed] });
  }
};
