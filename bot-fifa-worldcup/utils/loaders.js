const fs = require("fs");
const path = require("path");
const { REST, Routes } = require("discord.js");
const config = require("../config/env");
const logger = require("./logger");

function getJavaScriptFiles(directory) {
  return fs
    .readdirSync(directory)
    .filter((file) => file.endsWith(".js"))
    .map((file) => path.join(directory, file));
}

function loadCommands(client) {
  const commandFiles = getJavaScriptFiles(path.join(__dirname, "..", "commands"));
  const commands = [];

  for (const file of commandFiles) {
    const command = require(file);

    if (!command.data || !command.execute) {
      logger.warn(`Command dilewati karena format tidak lengkap: ${file}`);
      continue;
    }

    client.commands.set(command.data.name, command);
    commands.push(command);
  }

  logger.info(`${commands.length} command berhasil dimuat.`);
  return commands;
}

function loadEvents(client) {
  const eventFiles = getJavaScriptFiles(path.join(__dirname, "..", "events"));

  for (const file of eventFiles) {
    const event = require(file);

    if (!event.name || !event.execute) {
      logger.warn(`Event dilewati karena format tidak lengkap: ${file}`);
      continue;
    }

    if (event.once) {
      client.once(event.name, (...args) => event.execute(...args));
    } else {
      client.on(event.name, (...args) => event.execute(...args));
    }
  }

  logger.info(`${eventFiles.length} event berhasil dimuat.`);
}

async function registerCommands(commands) {
  const rest = new REST({ version: "10" }).setToken(config.token);
  const body = commands.map((command) => command.data.toJSON());
  const route = config.guildId
    ? Routes.applicationGuildCommands(config.clientId, config.guildId)
    : Routes.applicationCommands(config.clientId);

  await rest.put(route, { body });

  const scope = config.guildId ? `guild ${config.guildId}` : "global";
  logger.info(`${body.length} slash command didaftarkan untuk scope ${scope}.`);
}

module.exports = {
  loadCommands,
  loadEvents,
  registerCommands,
};
