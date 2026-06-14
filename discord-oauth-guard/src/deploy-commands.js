const { REST, Routes } = require('discord.js');
const env = require('./config/env');
const { loadCommands } = require('./utils/loaders');

async function deploy() {
  if (!env.discordToken) {
    throw new Error('DISCORD_TOKEN is required.');
  }
  if (!env.clientId) {
    throw new Error('CLIENT_ID is required.');
  }

  const commands = loadCommands();
  const payload = commands.map((command) => command.data.toJSON());
  const rest = new REST({ version: '10' }).setToken(env.discordToken);

  if (env.guildId) {
    await rest.put(Routes.applicationGuildCommands(env.clientId, env.guildId), { body: payload });
    console.log(`Registered ${payload.length} guild command(s) for ${env.guildId}.`);
    return;
  }

  await rest.put(Routes.applicationCommands(env.clientId), { body: payload });
  console.log(`Registered ${payload.length} global command(s).`);
}

deploy().catch((error) => {
  console.error('Failed to deploy commands:', error);
  process.exitCode = 1;
});
