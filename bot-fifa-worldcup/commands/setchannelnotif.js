const {
  ChannelType,
  EmbedBuilder,
  MessageFlags,
  PermissionFlagsBits,
  SlashCommandBuilder,
} = require("discord.js");
const config = require("../config/env");
const { updateDb } = require("../database/jsonDb");

function isWhitelisted(userId) {
  return config.notificationWhitelistIds.length === 0
    ? true
    : config.notificationWhitelistIds.includes(userId);
}

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
        flags: MessageFlags.Ephemeral,
      });
      return;
    }

    if (!isWhitelisted(interaction.user.id)) {
      await interaction.reply({
        content: "Kamu tidak punya akses untuk memakai command ini.",
        flags: MessageFlags.Ephemeral,
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
          name: "Akses",
          value:
            config.notificationWhitelistIds.length > 0
              ? "Whitelist aktif"
              : "Whitelist tidak diatur",
          inline: true,
        },
      );

    await interaction.reply({ embeds: [embed], flags: MessageFlags.Ephemeral });
  },
};
