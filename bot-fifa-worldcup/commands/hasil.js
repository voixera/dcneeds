const { EmbedBuilder, SlashCommandBuilder } = require("discord.js");
const config = require("../config/env");
const worldCupService = require("../services/worldCupService");
const { formatMatchLine } = require("../utils/format");

module.exports = {
  data: new SlashCommandBuilder()
    .setName("hasil")
    .setDescription("Lihat hasil pertandingan terbaru Piala Dunia.")
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
        .setDescription("Jumlah hasil yang ditampilkan.")
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
    const { db, matches } = worldCupService.getLatestResults({ team, limit });

    if (matches.length === 0) {
      await interaction.reply("Belum ada hasil pertandingan yang cocok dengan filter tersebut.");
      return;
    }

    const embed = new EmbedBuilder()
      .setColor(0x16a34a)
      .setTitle("Hasil Terbaru Piala Dunia")
      .setDescription(
        matches.map((match) => formatMatchLine(db, match, config.timezone)).join("\n\n"),
      );

    await interaction.reply({ embeds: [embed] });
  },
};
