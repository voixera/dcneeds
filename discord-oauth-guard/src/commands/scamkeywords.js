const { SlashCommandBuilder, EmbedBuilder, MessageFlags, PermissionFlagsBits } = require('discord.js');
const { colors, truncate } = require('../utils/embeds');
const defaultKeywords = require('../config/scamKeywords');

function formatKeywords(keywords) {
  return keywords.map((keyword) => `- ${keyword}`).join('\n');
}

module.exports = {
  data: new SlashCommandBuilder()
    .setName('scamkeywords')
    .setDescription('Manage scam OCR keyword detection.')
    .setDefaultMemberPermissions(PermissionFlagsBits.ModerateMembers)
    .addSubcommand((subcommand) =>
      subcommand
        .setName('list')
        .setDescription('List active scam keywords.')
    )
    .addSubcommand((subcommand) =>
      subcommand
        .setName('add')
        .setDescription('Add a scam keyword.')
        .addStringOption((option) =>
          option
            .setName('keyword')
            .setDescription('Keyword or phrase to detect.')
            .setRequired(true)
            .setMaxLength(100)
        )
    )
    .addSubcommand((subcommand) =>
      subcommand
        .setName('remove')
        .setDescription('Remove a scam keyword.')
        .addStringOption((option) =>
          option
            .setName('keyword')
            .setDescription('Keyword or phrase to remove.')
            .setRequired(true)
            .setMaxLength(100)
        )
    )
    .addSubcommand((subcommand) =>
      subcommand
        .setName('reset')
        .setDescription('Reset keywords to default.')
    ),

  async execute(interaction, context) {
    await interaction.deferReply({ flags: MessageFlags.Ephemeral });
    const subcommand = interaction.options.getSubcommand();
    const config = await context.configService.getGuildConfig(interaction.guildId);
    let keywords = [...config.scamKeywords];

    if (subcommand === 'add') {
      const keyword = interaction.options.getString('keyword', true).trim().toLowerCase();
      if (!keywords.some((item) => item.toLowerCase() === keyword)) {
        keywords.push(keyword);
        keywords = keywords.sort((a, b) => a.localeCompare(b));
        await context.configService.set(interaction.guildId, 'scamKeywords', keywords.join('\n'));
      }
    }

    if (subcommand === 'remove') {
      const keyword = interaction.options.getString('keyword', true).trim().toLowerCase();
      keywords = keywords.filter((item) => item.toLowerCase() !== keyword);
      await context.configService.set(interaction.guildId, 'scamKeywords', keywords.join('\n'));
    }

    if (subcommand === 'reset') {
      keywords = [...defaultKeywords];
      await context.configService.set(interaction.guildId, 'scamKeywords', keywords.join('\n'));
    }

    const embed = new EmbedBuilder()
      .setColor(colors.info)
      .setTitle('Scam Keywords')
      .setDescription(truncate(formatKeywords(keywords), 4000))
      .setFooter({ text: `${keywords.length} active keyword(s)` })
      .setTimestamp();

    await interaction.editReply({ embeds: [embed] });
  }
};
