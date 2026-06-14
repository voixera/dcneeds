const fs = require('node:fs');
const path = require('node:path');
const { Collection } = require('discord.js');

function loadCommands(commandsPath = path.join(__dirname, '..', 'commands')) {
  const commands = new Collection();
  const files = fs.readdirSync(commandsPath).filter((file) => file.endsWith('.js'));

  for (const file of files) {
    const command = require(path.join(commandsPath, file));
    if (!command.data || !command.execute) {
      throw new Error(`Command ${file} must export data and execute.`);
    }
    commands.set(command.data.name, command);
  }

  return commands;
}

function loadEvents(client, context, eventsPath = path.join(__dirname, '..', 'events')) {
  const files = fs.readdirSync(eventsPath).filter((file) => file.endsWith('.js'));

  for (const file of files) {
    const event = require(path.join(eventsPath, file));
    if (!event.name || !event.execute) {
      throw new Error(`Event ${file} must export name and execute.`);
    }

    const handler = (...args) => event.execute(...args, context);
    if (event.once) {
      client.once(event.name, handler);
    } else {
      client.on(event.name, handler);
    }
  }
}

module.exports = {
  loadCommands,
  loadEvents
};
