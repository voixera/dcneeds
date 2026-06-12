const { EmbedBuilder, SlashCommandBuilder } = require("discord.js");
const predictionService = require("../services/predictionService");

module.exports = {
  data: new SlashCommandBuilder()
    .setName("leaderboard")
    .setDescription("Lihat ranking prediksi pengguna.")
    .addIntegerOption((option) =>
      option
        .setName("jumlah")
        .setDescription("Jumlah ranking yang ditampilkan.")
        .setMinValue(1)
        .setMaxValue(20)
        .setRequired(false),
    ),

  async execute(interaction) {
    const limit = interaction.options.getInteger("jumlah") || 10;
    const leaderboard = predictionService.getLeaderboard(limit);

    if (leaderboard.length === 0) {
      await interaction.reply("Belum ada prediksi. Mulai dengan /prediksi.");
      return;
    }

    const lines = leaderboard.map((entry, index) => {
      const rank = String(index + 1).padStart(2, " ");
      return `${rank}. <@${entry.userId}> - ${entry.points} poin (${entry.predictions} prediksi)`;
    });

    const embed = new EmbedBuilder()
      .setColor(0x7c3aed)
      .setTitle("Leaderboard Prediksi")
      .setDescription(lines.join("\n"));

    await interaction.reply({ embeds: [embed] });
  },
};
