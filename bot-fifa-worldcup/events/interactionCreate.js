const { Events, MessageFlags } = require("discord.js");
const logger = require("../utils/logger");

async function replyWithError(interaction, message) {
  const payload = {
    content: message,
    flags: MessageFlags.Ephemeral,
  };

  if (interaction.deferred || interaction.replied) {
    await interaction.followUp(payload);
    return;
  }

  await interaction.reply(payload);
}

module.exports = {
  name: Events.InteractionCreate,
  async execute(interaction) {
    if (!interaction.isChatInputCommand() && !interaction.isAutocomplete()) return;

    const command = interaction.client.commands.get(interaction.commandName);
    if (!command) return;

    try {
      if (interaction.isAutocomplete()) {
        if (command.autocomplete) {
          await command.autocomplete(interaction);
        }
        return;
      }

      await command.execute(interaction);
    } catch (error) {
      logger.error(`Command ${interaction.commandName} gagal.`, error);
      await replyWithError(interaction, error.message || "Terjadi kesalahan saat menjalankan command.");
    }
  },
};
