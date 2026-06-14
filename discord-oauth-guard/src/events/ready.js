const { ActivityType } = require('discord.js');
const logger = require('../utils/logger');

module.exports = {
  name: 'ready',
  once: true,
  async execute(client) {
    client.user.setPresence({
      status: 'dnd',
      activities: [
        {
          name: 'Protected Your Server',
          type: ActivityType.Watching
        }
      ]
    });

    logger.info(`Logged in as ${client.user.tag}`);
  }
};
