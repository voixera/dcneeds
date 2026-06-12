const { Client, Collection, GatewayIntentBits } = require("discord.js");
const config = require("./config/env");
const logger = require("./utils/logger");
const {
  loadCommands,
  loadEvents,
  registerCommands,
} = require("./utils/loaders");

async function bootstrap() {
  config.assertBotConfig();

  const client = new Client({
    intents: [GatewayIntentBits.Guilds],
  });

  client.commands = new Collection();

  const commands = loadCommands(client);
  await registerCommands(commands);

  if (config.isDeployOnly) {
    logger.info("Slash command berhasil didaftarkan. Mode deploy-only selesai.");
    return;
  }

  loadEvents(client);
  await client.login(config.token);
}

bootstrap().catch((error) => {
  logger.error("Bot gagal dijalankan.", error);
  process.exit(1);
});
