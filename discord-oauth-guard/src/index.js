const { REST } = require('@discordjs/rest');
const { Routes } = require('discord-api-types/v10');
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
const VoiceGuardService = require('./services/voiceGuardService');
const { loadCommands, loadEvents } = require('./utils/loaders');
const logger = require('./utils/logger');

const DEFAULT_REQUIRED_SHARDS = 1;
const MAX_TIMEOUT_MS = 2_147_483_647;

function stripTokenPrefix(token) {
  return token.replace(/^(Bot|Bearer)\s*/i, '');
}

function formatDuration(ms) {
  const totalSeconds = Math.ceil(ms / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  const parts = [];
  if (hours) parts.push(`${hours}h`);
  if (minutes) parts.push(`${minutes}m`);
  if (seconds || parts.length === 0) parts.push(`${seconds}s`);
  return parts.join(' ');
}

async function sleep(ms) {
  let remaining = ms;
  while (remaining > 0) {
    const delay = Math.min(remaining, MAX_TIMEOUT_MS);
    await new Promise((resolve) => setTimeout(resolve, delay));
    remaining -= delay;
  }
}

function getRequiredShardCount(client) {
  if (Array.isArray(client.options.shards)) {
    return client.options.shards.length;
  }

  if (Number.isInteger(client.options.shardCount) && client.options.shardCount > 0) {
    return client.options.shardCount;
  }

  return DEFAULT_REQUIRED_SHARDS;
}

async function waitForSessionStartSlot(client, token) {
  const rest = new REST({ version: '10' }).setToken(stripTokenPrefix(token));
  const requiredShards = getRequiredShardCount(client);
  let retries = 0;

  while (true) {
    const gatewayInfo = await rest.get(Routes.gatewayBot());
    const sessionLimit = gatewayInfo?.session_start_limit;
    const remaining = Number(sessionLimit?.remaining);

    if (!Number.isFinite(remaining) || remaining >= requiredShards) {
      return;
    }

    retries += 1;
    if (env.discordLoginMaxRetries > 0 && retries > env.discordLoginMaxRetries) {
      throw new Error(
        `Discord session start limit is still exhausted after ${env.discordLoginMaxRetries} retries.`
      );
    }

    const resetAfter = Number(sessionLimit?.reset_after);
    const waitMs = Math.max(
      Number.isFinite(resetAfter) ? resetAfter + env.discordLoginRetryBufferMs : env.discordLoginRetryBufferMs,
      env.discordLoginRetryBufferMs
    );
    const retryAt = new Date(Date.now() + waitMs).toISOString();
    const retryLimit = env.discordLoginMaxRetries > 0 ? ` (${retries}/${env.discordLoginMaxRetries})` : '';

    logger.warn(
      `Discord session start limit exhausted${retryLimit}: need ${requiredShards} shard(s), ` +
        `${remaining} remaining. Retrying login in ${formatDuration(waitMs)} at ${retryAt}.`
    );
    await sleep(waitMs);
  }
}

async function main() {
  if (!env.discordToken) {
    throw new Error('DISCORD_TOKEN is required.');
  }

  const client = new Client({
    intents: [
      GatewayIntentBits.Guilds,
      GatewayIntentBits.GuildMessages,
      GatewayIntentBits.MessageContent,
      GatewayIntentBits.GuildModeration,
      GatewayIntentBits.GuildVoiceStates
    ],
    partials: [Partials.Channel, Partials.Message]
  });

  await waitForSessionStartSlot(client, env.discordToken);

  const database = await new Database().connect();
  const configService = new ConfigService(database);
  const ocrService = new OcrService();
  const imageHashService = new ImageHashService();
  const scamDetector = new ScamDetector();
  const spamPatternService = new SpamPatternService(database);
  const riskEngine = new RiskEngine();
  const logChannelService = new LogChannelService(client);
  const voiceGuardService = new VoiceGuardService({ client, configService, logChannelService });
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
    voiceGuardService,
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
