const { EmbedBuilder, SlashCommandBuilder } = require("discord.js");
const worldCupService = require("../services/worldCupService");
const { formatStandingsTable } = require("../utils/format");

function codeBlock(value) {
  return `\`\`\`\n${value}\n\`\`\``;
}

module.exports = {
  data: new SlashCommandBuilder()
    .setName("klasemen")
    .setDescription("Lihat klasemen grup Piala Dunia.")
    .addStringOption((option) =>
      option
        .setName("grup")
        .setDescription("Nama grup, contoh: A.")
        .setMinLength(1)
        .setMaxLength(2)
        .setRequired(false),
    ),

  async execute(interaction) {
    const group = interaction.options.getString("grup");
    const embed = new EmbedBuilder().setColor(0xf59e0b).setTitle("Klasemen Grup");

    if (group) {
      const { db, rows } = worldCupService.getStandings(group);

      if (rows.length === 0) {
        await interaction.reply(`Klasemen grup ${group.toUpperCase()} belum tersedia.`);
        return;
      }

      embed.setTitle(`Klasemen Grup ${group.toUpperCase()}`);
      embed.setDescription(codeBlock(formatStandingsTable(db, rows)));
      await interaction.reply({ embeds: [embed] });
      return;
    }

    const { db, groups } = worldCupService.getGroupedStandings();

    for (const item of groups.slice(0, 8)) {
      embed.addFields({
        name: `Grup ${item.group}`,
        value: codeBlock(formatStandingsTable(db, item.rows)),
      });
    }

    await interaction.reply({ embeds: [embed] });
  },
};
