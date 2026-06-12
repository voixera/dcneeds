const { EmbedBuilder, SlashCommandBuilder } = require("discord.js");
const config = require("../config/env");
const liveWorldCupService = require("../services/liveWorldCupService");
const worldCupService = require("../services/worldCupService");
const { formatMatchLine } = require("../utils/format");
const { createLiveEmbed } = require("../utils/liveEmbed");
const logger = require("../utils/logger");

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

    await interaction.deferReply();

    if (liveWorldCupService.isConfigured()) {
      try {
        const response = await liveWorldCupService.answer("hasil", { team, limit });
        const embed = createLiveEmbed({
          title: "Hasil Terbaru Piala Dunia",
          color: 0x16a34a,
          response,
        });

        await interaction.editReply({ embeds: [embed] });
        return;
      } catch (error) {
        logger.warn("Live answer /hasil gagal, pakai data lokal.", error);
      }
    }

    const { db, matches } = worldCupService.getLatestResults({ team, limit });

    if (matches.length === 0) {
      await interaction.editReply("Belum ada hasil pertandingan yang cocok dengan filter tersebut.");
      return;
    }

    const embed = new EmbedBuilder()
      .setColor(0x16a34a)
      .setTitle("Hasil Terbaru Piala Dunia")
      .setDescription(
        matches.map((match) => formatMatchLine(db, match, config.timezone)).join("\n\n"),
      );

    await interaction.editReply({ embeds: [embed] });
  },
};
