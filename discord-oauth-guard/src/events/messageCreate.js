const logger = require('../utils/logger');

module.exports = {
  name: 'messageCreate',
  async execute(message, context) {
    try {
      await context.scanService.analyzeMessage(message);
    } catch (error) {
      logger.error('messageCreate handler failed:', error);
    }
  }
};
