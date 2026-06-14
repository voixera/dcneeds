const { Database } = require('./database');

(async () => {
  const database = await new Database().connect();
  await database.db.close();
  console.log('SQLite database initialized.');
})().catch((error) => {
  console.error('Failed to initialize database:', error);
  process.exitCode = 1;
});
