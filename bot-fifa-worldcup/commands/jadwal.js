const { EmbedBuilder, SlashCommandBuilder } = require("discord.js");
const config = require("../config/env");
const worldCupService = require("../services/worldCupService");
const { formatMatchLine } = require("../utils/format");

module.exports = {
  data: new SlashCommandBuilder()
    .setName("jadwal")
    .setDescription("Lihat jadwal pertandingan Piala Dunia.")
    .addStringOption((option) =>
      option
        .setName("tim")
        .setDescription("Filter berdasarkan nama tim.")
        .setAutocomplete(true)
        .setRequired(false),
    )
    .addIntegerOption((option) =>
      option
        .setName("jumlah")
        .setDescription("Jumlah pertandingan yang ditampilkan.")
        .setMinValue(1)
        .setMaxValue(10)
        .setRequired(false),
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
    const team = interaction.options.getString("tim");
    const limit = interaction.options.getInteger("jumlah") || 5;
    const { db, matches } = worldCupService.getUpcomingMatches({ team, limit });

    if (matches.length === 0) {
      await interaction.reply("Belum ada jadwal pertandingan yang cocok dengan filter tersebut.");
      return;
    }

    const embed = new EmbedBuilder()
      .setColor(0x2563eb)
      .setTitle("Jadwal Piala Dunia")
      .setDescription(
        matches.map((match) => formatMatchLine(db, match, config.timezone)).join("\n\n"),
      )
      .setFooter({ text: "Gunakan Match ID dari jadwal untuk /prediksi." });

    await interaction.reply({ embeds: [embed] });
  },
};
