const { SlashCommandBuilder, EmbedBuilder, MessageFlags, PermissionFlagsBits } = require('discord.js');
const { colors, truncate } = require('../utils/embeds');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('scamscan')
    .setDescription('Manually scan text or an image attachment.')
    .setDefaultMemberPermissions(PermissionFlagsBits.ModerateMembers)
    .addStringOption((option) =>
      option
        .setName('text')
        .setDescription('Text to scan.')
        .setMaxLength(2000)
    )
    .addAttachmentOption((option) =>
      option
        .setName('image')
        .setDescription('Image attachment to OCR and scan.')
    ),

  async execute(interaction, context) {
    await interaction.deferReply({ flags: MessageFlags.Ephemeral });
    const text = interaction.options.getString('text') || '';
    const image = interaction.options.getAttachment('image');

    if (!text && !image) {
      await interaction.editReply({ content: 'Provide text, an image, or both.' });
      return;
    }

    const result = await context.scanService.scanManual({
      guildId: interaction.guildId,
      userId: interaction.user.id,
      userCreatedTimestamp: interaction.user.createdTimestamp,
      channelId: interaction.channelId,
      text,
      attachments: image ? [image] : []
    });

    const embed = new EmbedBuilder()
      .setColor(colors[result.risk.severity] || colors.info)
      .setTitle('Manual Scam Scan')
      .setDescription(`Risk score: **${result.risk.score}/100**\nSeverity: **${result.risk.severity}**`)
      .addFields(
        { name: 'Matched Keywords', value: truncate(result.risk.keywords.join(', ') || 'None'), inline: false },
        { name: 'Reasons', value: truncate(result.risk.reasons.join('\n') || 'No risk signals'), inline: false }
      )
      .setTimestamp();

    if (result.ocrText) {
      embed.addFields({ name: 'OCR Text', value: truncate(result.ocrText.replace(/\s+/g, ' '), 1000), inline: false });
    }

    if (result.imageHashes.length) {
      embed.addFields({ name: 'Image Hashes', value: result.imageHashes.map((hash) => `\`${hash}\``).join('\n'), inline: false });
    }

    await interaction.editReply({ embeds: [embed] });
  }
};
