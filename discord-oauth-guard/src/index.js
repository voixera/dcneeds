const { Client, GatewayIntentBits, Partials } = require('discord.js');
const env = require('./config/env');
const { Database } = require('./database/database');
const ConfigService = require('./services/configService');
const OcrService = require('./services/ocrService');
const ImageHashService = require('./services/imageHashService');
const { ScamDetector } = require('./services/scamDetector');
const SpamPatternService = require('./services/spamPatternService');
const RiskEngine = require('./services/riskEngine');
const LogChannelService = require('./services/logChannelService');
const ModerationService = require('./services/moderationService');
const ScanService = require('./services/scanService');
const { loadCommands, loadEvents } = require('./utils/loaders');
const logger = require('./utils/logger');

async function main() {
  if (!env.discordToken) {
    throw new Error('DISCORD_TOKEN is required.');
  }

  const client = new Client({
    intents: [
      GatewayIntentBits.Guilds,
      GatewayIntentBits.GuildMessages,
      GatewayIntentBits.MessageContent,
      GatewayIntentBits.GuildMembers,
      GatewayIntentBits.GuildModeration
    ],
    partials: [Partials.Channel, Partials.Message]
  });

  const database = await new Database().connect();
  const configService = new ConfigService(database);
  const ocrService = new OcrService();
  const imageHashService = new ImageHashService();
  const scamDetector = new ScamDetector();
  const spamPatternService = new SpamPatternService(database);
  const riskEngine = new RiskEngine();
  const logChannelService = new LogChannelService(client);
  const moderationService = new ModerationService({ database, logChannelService });
  const scanService = new ScanService({
    database,
    configService,
    ocrService,
    imageHashService,
    scamDetector,
    spamPatternService,
    riskEngine,
    moderationService
  });

  const commands = loadCommands();
  const context = {
    client,
    database,
    commands,
    configService,
    ocrService,
    imageHashService,
    scamDetector,
    spamPatternService,
    riskEngine,
    logChannelService,
    moderationService,
    scanService
  };

  loadEvents(client, context);

  process.on('SIGINT', async () => {
    logger.info('SIGINT received. Shutting down.');
    await database.db?.close();
    client.destroy();
    process.exit(0);
  });

  process.on('SIGTERM', async () => {
    logger.info('SIGTERM received. Shutting down.');
    await database.db?.close();
    client.destroy();
    process.exit(0);
  });

  await client.login(env.discordToken);
}

main().catch((error) => {
  logger.error('Bot failed to start:', error);
  process.exitCode = 1;
});
