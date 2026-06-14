const logger = require('../utils/logger');

module.exports = {
  name: 'voiceStateUpdate',
  async execute(oldState, newState, context) {
    try {
      await context.voiceGuardService.handleVoiceStateUpdate(oldState, newState);
    } catch (error) {
      logger.error('voiceStateUpdate handler failed:', error);
    }
  }
};
