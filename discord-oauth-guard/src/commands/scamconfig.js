const { SlashCommandBuilder, EmbedBuilder, MessageFlags, PermissionFlagsBits } = require('discord.js');
const { colors } = require('../utils/embeds');
const { msToHuman } = require('../utils/time');

const configurableKeys = [
  'suspiciousThreshold',
  'maliciousThreshold',
  'timeoutDurationMs',
  'enableAutoTimeout',
  'deleteMaliciousMessages',
  'imageSimilarityDistance',
  'spamAttachmentThreshold',
  'spamChannelThreshold',
  'massMentionThreshold'
];

function addKeyChoices(option) {
  for (const key of configurableKeys) {
    option.addChoices({ name: key, value: key });
  }
  return option;
}

module.exports = {
  data: new SlashCommandBuilder()
    .setName('scamconfig')
    .setDescription('View or update OAuth Guard configuration.')
    .setDefaultMemberPermissions(PermissionFlagsBits.ManageGuild)
    .addSubcommand((subcommand) =>
      subcommand
        .setName('view')
        .setDescription('Show effective configuration.')
    )
    .addSubcommand((subcommand) =>
      subcommand
        .setName('set')
        .setDescription('Set a configuration value.')
        .addStringOption((option) =>
          addKeyChoices(
            option
              .setName('key')
              .setDescription('Configuration key.')
              .setRequired(true)
          )
        )
        .addStringOption((option) =>
          option
            .setName('value')
            .setDescription('New value.')
            .setRequired(true)
            .setMaxLength(200)
        )
    ),

  async execute(interaction, context) {
    await interaction.deferReply({ flags: MessageFlags.Ephemeral });
    const subcommand = interaction.options.getSubcommand();

    if (subcommand === 'set') {
      const key = interaction.options.getString('key', true);
      const value = interaction.options.getString('value', true).trim();
      await context.configService.set(interaction.guildId, key, value);
    }

    const config = await context.configService.getGuildConfig(interaction.guildId);
    const embed = new EmbedBuilder()
      .setColor(colors.info)
      .setTitle('OAuth Guard Configuration')
      .addFields(
        { name: 'Thresholds', value: `Suspicious: ${config.thresholds.suspicious}\nMalicious: ${config.thresholds.malicious}`, inline: true },
        { name: 'Timeout', value: `Enabled: ${config.moderation.enableAutoTimeout}\nDuration: ${msToHuman(config.moderation.timeoutDurationMs)}`, inline: true },
        { name: 'Message Actions', value: `Delete malicious: ${config.moderation.deleteMaliciousMessages}\nWarn cleanup: ${msToHuman(config.moderation.warningDeleteAfterMs)}`, inline: true },
        { name: 'Image Hash', value: `Similarity distance: ${config.images.similarityDistance}`, inline: true },
        { name: 'Spam Window', value: `Attachments: ${config.spam.attachmentThreshold}\nChannels: ${config.spam.channelThreshold}\nMass mentions: ${config.spam.massMentionThreshold}`, inline: true },
        { name: 'Keywords', value: `${config.scamKeywords.length} active keyword(s)`, inline: true }
      )
      .setTimestamp();

    await interaction.editReply({ embeds: [embed] });
  }
};
