const { EmbedBuilder, SlashCommandBuilder } = require("discord.js");
const worldCupService = require("../services/worldCupService");

module.exports = {
  data: new SlashCommandBuilder()
    .setName("tim")
    .setDescription("Lihat informasi tim nasional.")
    .addStringOption((option) =>
      option
        .setName("nama")
        .setDescription("Nama tim nasional.")
        .setAutocomplete(true)
        .setRequired(true),
    ),

  async autocomplete(interaction) {
    const focused = interaction.options.getFocused();
    const teams = worldCupService.searchTeams(focused);

    await interaction.respond(
      teams.map((team) => ({
        name: `${team.name} (${team.fifaCode})`,
        value: team.name,
      })),
    );
  },

  async execute(interaction) {
    const query = interaction.options.getString("nama", true);
    const { team } = worldCupService.findTeam(query);

    if (!team) {
      await interaction.reply(`Tim "${query}" tidak ditemukan.`);
      return;
    }

    const embed = new EmbedBuilder()
      .setColor(0x0f766e)
      .setTitle(`${team.name} (${team.fifaCode})`)
      .setDescription(team.description || "Belum ada deskripsi tim.")
      .addFields(
        { name: "Grup", value: team.group || "-", inline: true },
        { name: "Federasi", value: team.federation || "-", inline: true },
        { name: "Pelatih", value: team.coach || "-", inline: true },
        { name: "Kapten", value: team.captain || "-", inline: true },
      );

    await interaction.reply({ embeds: [embed] });
  },
};
