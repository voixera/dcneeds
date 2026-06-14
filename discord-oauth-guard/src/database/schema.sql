PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS detected_scams (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  guild_id TEXT NOT NULL,
  message_id TEXT,
  user_id TEXT NOT NULL,
  username TEXT,
  channel_id TEXT,
  risk_score INTEGER NOT NULL,
  severity TEXT NOT NULL,
  reasons TEXT NOT NULL DEFAULT '[]',
  keywords TEXT NOT NULL DEFAULT '[]',
  attachment_urls TEXT NOT NULL DEFAULT '[]',
  ocr_text TEXT,
  image_hashes TEXT NOT NULL DEFAULT '[]',
  action_taken TEXT,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS image_hashes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  guild_id TEXT NOT NULL,
  hash TEXT NOT NULL,
  message_id TEXT,
  user_id TEXT NOT NULL,
  channel_id TEXT,
  attachment_url TEXT,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS strike_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  guild_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  message_id TEXT,
  risk_score INTEGER NOT NULL,
  severity TEXT NOT NULL,
  reason TEXT,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS timeout_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  guild_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  duration_ms INTEGER NOT NULL,
  reason TEXT,
  moderator_id TEXT,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS risk_scores (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  guild_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  message_id TEXT,
  score INTEGER NOT NULL,
  severity TEXT NOT NULL,
  breakdown TEXT NOT NULL DEFAULT '[]',
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS configuration (
  guild_id TEXT NOT NULL,
  key TEXT NOT NULL,
  value TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  PRIMARY KEY (guild_id, key)
);

CREATE TABLE IF NOT EXISTS user_activity (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  guild_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  channel_id TEXT NOT NULL,
  message_id TEXT,
  attachment_hashes TEXT NOT NULL DEFAULT '[]',
  attachment_count INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE INDEX IF NOT EXISTS idx_detected_scams_guild_created ON detected_scams (guild_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_detected_scams_user_created ON detected_scams (guild_id, user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_image_hashes_guild_hash ON image_hashes (guild_id, hash);
CREATE INDEX IF NOT EXISTS idx_image_hashes_user_created ON image_hashes (guild_id, user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_strike_history_user_created ON strike_history (guild_id, user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_timeout_history_user_created ON timeout_history (guild_id, user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_risk_scores_guild_created ON risk_scores (guild_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_activity_user_created ON user_activity (guild_id, user_id, created_at DESC);
