const { EmbedBuilder } = require("discord.js");
const config = require("../config/env");
const { readDb, updateDb } = require("../database/jsonDb");
const { getMatchesStartingSoon, getFinishedMatches } = require("./worldCupService");
const { formatDateTime, formatMatchTitle } = require("../utils/format");
const logger = require("../utils/logger");

function getConfiguredChannelId() {
  const db = readDb();
  if (config.guildId && db.notificationChannels?.[config.guildId]) {
    return db.notificationChannels[config.guildId];
  }

  return null;
}

async function getNotificationChannel(client) {
  const configuredChannelId = getConfiguredChannelId();

  if (!configuredChannelId) return null;

  const channel = await client.channels.fetch(configuredChannelId);
  if (!channel || !channel.isTextBased()) return null;

  return channel;
}

function buildReminderEmbed(db, match) {
  return new EmbedBuilder()
    .setColor(0x1d4ed8)
    .setTitle("Pertandingan akan dimulai")
    .setDescription(formatMatchTitle(db, match))
    .addFields(
      {
        name: "Kickoff",
        value: formatDateTime(match.kickoff, config.timezone),
        inline: true,
      },
      {
        name: "Venue",
        value: match.venue,
        inline: true,
      },
      {
        name: "Match ID",
        value: match.id,
        inline: true,
      },
    );
}

function buildResultEmbed(db, match) {
  return new EmbedBuilder()
    .setColor(0x16a34a)
    .setTitle("Hasil pertandingan")
    .setDescription(formatMatchTitle(db, match))
    .addFields(
      {
        name: "Kickoff",
        value: formatDateTime(match.kickoff, config.timezone),
        inline: true,
      },
      {
        name: "Venue",
        value: match.venue,
        inline: true,
      },
      {
        name: "Match ID",
        value: match.id,
        inline: true,
      },
    );
}

async function runNotificationSweep(client) {
  const channel = await getNotificationChannel(client);
  if (!channel) return;

  const snapshot = readDb();
  const reminderLog = new Set(snapshot.notificationLog.matchReminders);
  const resultLog = new Set(snapshot.notificationLog.resultNotifications);

  const { db: reminderDb, matches: reminderMatches } = getMatchesStartingSoon(
    config.notificationLookaheadMinutes,
  );
  const remindersToSend = reminderMatches.filter((match) => !reminderLog.has(match.id));

  const { db: resultDb, matches: finishedMatches } = getFinishedMatches();
  const resultsToSend = finishedMatches.filter((match) => !resultLog.has(match.id));

  for (const match of remindersToSend) {
    await channel.send({ embeds: [buildReminderEmbed(reminderDb, match)] });
  }

  for (const match of resultsToSend) {
    await channel.send({ embeds: [buildResultEmbed(resultDb, match)] });
  }

  if (remindersToSend.length === 0 && resultsToSend.length === 0) return;

  updateDb((db) => {
    for (const match of remindersToSend) {
      if (!db.notificationLog.matchReminders.includes(match.id)) {
        db.notificationLog.matchReminders.push(match.id);
      }
    }

    for (const match of resultsToSend) {
      if (!db.notificationLog.resultNotifications.includes(match.id)) {
        db.notificationLog.resultNotifications.push(match.id);
      }
    }
  });
}

function startNotificationService(client) {
  const configuredChannelId = getConfiguredChannelId();

  if (!configuredChannelId) {
    logger.warn("Channel notifikasi belum diset. Notifikasi dinonaktifkan.");
    return;
  }

  runNotificationSweep(client).catch((error) => {
    logger.error("Gagal menjalankan sweep notifikasi awal.", error);
  });

  setInterval(() => {
    runNotificationSweep(client).catch((error) => {
      logger.error("Gagal menjalankan sweep notifikasi.", error);
    });
  }, config.notificationIntervalMs);

  logger.info("Service notifikasi pertandingan aktif.");
}

module.exports = {
  getNotificationChannel,
  runNotificationSweep,
  startNotificationService,
};
