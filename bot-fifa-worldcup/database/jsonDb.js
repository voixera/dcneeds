const fs = require("fs");
const path = require("path");
const seedData = require("./seedData");

const databasePath = process.env.FIFA_DB_PATH || path.join(__dirname, "db.json");

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function ensureDatabase() {
  if (fs.existsSync(databasePath)) return;

  fs.mkdirSync(path.dirname(databasePath), { recursive: true });
  fs.writeFileSync(databasePath, JSON.stringify(clone(seedData), null, 2));
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
