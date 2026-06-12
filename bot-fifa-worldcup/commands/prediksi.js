const { EmbedBuilder, SlashCommandBuilder } = require("discord.js");
const config = require("../config/env");
const predictionService = require("../services/predictionService");
const worldCupService = require("../services/worldCupService");
const { formatDateTime, formatMatchTitle, truncate } = require("../utils/format");

module.exports = {
  data: new SlashCommandBuilder()
    .setName("prediksi")
    .setDescription("Kirim atau ubah prediksi skor pertandingan.")
    .addStringOption((option) =>
      option
        .setName("match_id")
        .setDescription("Match ID dari /jadwal.")
        .setAutocomplete(true)
        .setRequired(true),
    )
    .addIntegerOption((option) =>
      option
        .setName("skor_tuan_rumah")
        .setDescription("Prediksi skor tim tuan rumah.")
        .setMinValue(0)
        .setMaxValue(20)
        .setRequired(true),
    )
    .addIntegerOption((option) =>
      option
        .setName("skor_tamu")
        .setDescription("Prediksi skor tim tamu.")
        .setMinValue(0)
        .setMaxValue(20)
        .setRequired(true),
    ),

  async autocomplete(interaction) {
    const focused = interaction.options.getFocused().toLowerCase();
    const { db, matches } = worldCupService.getPredictionOpenMatches(25);
    const choices = matches
      .filter((match) => {
        const label = `${match.id} ${formatMatchTitle(db, match)}`.toLowerCase();
        return label.includes(focused);
      })
      .map((match) => ({
        name: truncate(
          `${match.id} - ${formatMatchTitle(db, match)} (${formatDateTime(
            match.kickoff,
            config.timezone,
          )})`,
          100,
        ),
        value: match.id,
      }));

    await interaction.respond(choices);
  },

  async execute(interaction) {
    const matchId = interaction.options.getString("match_id", true);
    const homeScore = interaction.options.getInteger("skor_tuan_rumah", true);
    const awayScore = interaction.options.getInteger("skor_tamu", true);

    const { prediction, match, created } = predictionService.savePrediction({
      userId: interaction.user.id,
      username: interaction.user.username,
      matchId,
      homeScore,
      awayScore,
    });
    const { db } = worldCupService.findMatchById(match.id);

    const embed = new EmbedBuilder()
      .setColor(created ? 0x2563eb : 0xf59e0b)
      .setTitle(created ? "Prediksi tersimpan" : "Prediksi diperbarui")
      .setDescription(formatMatchTitle(db, match))
      .addFields(
        {
          name: "Prediksi kamu",
          value: `${prediction.homeScore} - ${prediction.awayScore}`,
          inline: true,
        },
        {
          name: "Kickoff",
          value: formatDateTime(match.kickoff, config.timezone),
          inline: true,
        },
        {
          name: "Match ID",
          value: match.id,
          inline: true,
        },
      )
      .setFooter({ text: "Poin dihitung otomatis setelah hasil pertandingan diinput." });

    await interaction.reply({ embeds: [embed] });
  },
};
