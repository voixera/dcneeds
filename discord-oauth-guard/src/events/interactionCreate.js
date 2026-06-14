const { MessageFlags } = require('discord.js');
const logger = require('../utils/logger');

module.exports = {
  name: 'interactionCreate',
  async execute(interaction, context) {
    if (!interaction.isChatInputCommand()) return;

    const command = context.commands.get(interaction.commandName);
    if (!command) return;

    try {
      await command.execute(interaction, context);
    } catch (error) {
      logger.error(`Command /${interaction.commandName} failed:`, error);
      const payload = {
        content: 'Command failed. Check bot logs for details.',
        flags: MessageFlags.Ephemeral
      };

      if (interaction.deferred || interaction.replied) {
        await interaction.followUp(payload).catch(() => {});
      } else {
        await interaction.reply(payload).catch(() => {});
      }
    }
  }
};
