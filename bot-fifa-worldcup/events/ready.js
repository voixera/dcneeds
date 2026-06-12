const { ActivityType, Events } = require("discord.js");
const { startNotificationService } = require("../services/notificationService");
const logger = require("../utils/logger");

module.exports = {
  name: Events.ClientReady,
  once: true,
  execute(client) {
    logger.info(`Bot login sebagai ${client.user.tag}.`);

    client.user.setActivity("Nonton Pildun Dunia😹", {
      type: ActivityType.Watching,
    });

    startNotificationService(client);
  },
};
