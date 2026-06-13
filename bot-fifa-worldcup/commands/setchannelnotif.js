const {
  ChannelType,
  EmbedBuilder,
  PermissionFlagsBits,
  SlashCommandBuilder,
} = require("discord.js");
const config = require("../config/env");
const { updateDb } = require("../database/jsonDb");

module.exports = {
  data: new SlashCommandBuilder()
    .setName("setchannelnotif")
    .setDescription("Atur channel untuk notifikasi pertandingan Piala Dunia.")
    .setDefaultMemberPermissions(PermissionFlagsBits.ManageGuild)
    .addChannelOption((option) =>
      option
        .setName("channel")
        .setDescription("Channel text untuk menerima notifikasi.")
        .addChannelTypes(ChannelType.GuildText, ChannelType.GuildAnnouncement)
        .setRequired(true),
    ),

  async execute(interaction) {
    const channel = interaction.options.getChannel("channel", true);

    if (!interaction.guildId) {
      await interaction.reply({
        content: "Command ini hanya bisa dipakai di server.",
        ephemeral: true,
      });
      return;
    }

    updateDb((db) => {
      db.notificationChannels ||= {};
      db.notificationChannels[interaction.guildId] = channel.id;
    });

    const embed = new EmbedBuilder()
      .setColor(0x22c55e)
      .setTitle("Channel notifikasi disimpan")
      .setDescription(`Notifikasi Piala Dunia sekarang akan dikirim ke ${channel}.`)
      .addFields(
        { name: "Server", value: interaction.guild.name, inline: true },
        { name: "Channel", value: `${channel}`, inline: true },
        {
          name: "Fallback",
          value: config.notificationChannelId ? "Masih ada channel default di env." : "-",
          inline: true,
        },
      );

    await interaction.reply({ embeds: [embed], ephemeral: true });
  },
};
