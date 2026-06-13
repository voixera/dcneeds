const fs = require("fs");
const path = require("path");
const seedData = require("./seedData");

const databasePath = process.env.FIFA_DB_PATH || path.join(__dirname, "db.json");

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function getUnchangedMatchIds(existingData) {
  const existingMatches = new Map(
    (existingData.matches || []).map((match) => [match.id, match]),
  );

  return new Set(
    seedData.matches
      .filter((match) => {
        const existingMatch = existingMatches.get(match.id);
        return (
          existingMatch &&
          existingMatch.homeTeamId === match.homeTeamId &&
          existingMatch.awayTeamId === match.awayTeamId
        );
      })
      .map((match) => match.id),
  );
}

function ensureDatabase() {
  if (!fs.existsSync(databasePath)) {
    fs.mkdirSync(path.dirname(databasePath), { recursive: true });
    fs.writeFileSync(databasePath, JSON.stringify(clone(seedData), null, 2));
    return;
  }

  const existingData = JSON.parse(fs.readFileSync(databasePath, "utf8"));
  if (existingData.metadata?.version === seedData.metadata.version) {
    if (!existingData.notificationChannels) {
      existingData.notificationChannels = {};
      writeDb(existingData);
    }
    return;
  }

  const unchangedMatchIds = getUnchangedMatchIds(existingData);
  const migratedData = {
    ...clone(seedData),
    notificationChannels: {
      ...(existingData.notificationChannels || {}),
    },
    predictions: (existingData.predictions || []).filter((prediction) =>
      unchangedMatchIds.has(prediction.matchId),
    ),
    notificationLog: {
      matchReminders: (
        existingData.notificationLog?.matchReminders || []
      ).filter((matchId) => unchangedMatchIds.has(matchId)),
      resultNotifications: (
        existingData.notificationLog?.resultNotifications || []
      ).filter((matchId) => unchangedMatchIds.has(matchId)),
    },
  };

  fs.mkdirSync(path.dirname(databasePath), { recursive: true });
  fs.writeFileSync(databasePath, JSON.stringify(migratedData, null, 2));
}

function readDb() {
  ensureDatabase();
  return JSON.parse(fs.readFileSync(databasePath, "utf8"));
}

function writeDb(data) {
  fs.mkdirSync(path.dirname(databasePath), { recursive: true });
  fs.writeFileSync(databasePath, JSON.stringify(data, null, 2));
}

function updateDb(mutator) {
  const data = readDb();
  const result = mutator(data);
  writeDb(data);
  return result;
}

module.exports = {
  databasePath,
  readDb,
  updateDb,
  writeDb,
};
