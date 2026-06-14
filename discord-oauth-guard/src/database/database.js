const fs = require('node:fs/promises');
const path = require('node:path');
const sqlite3 = require('sqlite3');
const { open } = require('sqlite');
const env = require('../config/env');

function serialize(value) {
  return JSON.stringify(value ?? []);
}

function parseJson(value, fallback = []) {
  if (!value) return fallback;
  try {
    return JSON.parse(value);
  } catch {
    return fallback;
  }
}

class Database {
  constructor(databasePath = env.databasePath) {
    this.databasePath = databasePath;
    this.db = null;
  }

  async connect() {
    await fs.mkdir(path.dirname(this.databasePath), { recursive: true });
    this.db = await open({
      filename: this.databasePath,
      driver: sqlite3.Database
    });

    const schema = await fs.readFile(path.join(__dirname, 'schema.sql'), 'utf8');
    await this.db.exec(schema);
    return this;
  }

  assertConnected() {
    if (!this.db) {
      throw new Error('Database is not connected. Call connect() first.');
    }
  }

  async getConfig(guildId, key) {
    this.assertConnected();
    const row = await this.db.get(
      'SELECT value FROM configuration WHERE guild_id = ? AND key = ?',
      guildId,
      key
    );
    return row ? row.value : null;
  }

  async getGuildConfig(guildId) {
    this.assertConnected();
    const rows = await this.db.all('SELECT key, value FROM configuration WHERE guild_id = ?', guildId);
    return rows.reduce((config, row) => {
      config[row.key] = row.value;
      return config;
    }, {});
  }

  async setConfig(guildId, key, value) {
    this.assertConnected();
    await this.db.run(
      `INSERT INTO configuration (guild_id, key, value, updated_at)
       VALUES (?, ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ','now'))
       ON CONFLICT(guild_id, key) DO UPDATE SET value = excluded.value, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now')`,
      guildId,
      key,
      String(value)
    );
  }

  async saveDetectedScam(record) {
    this.assertConnected();
    const result = await this.db.run(
      `INSERT INTO detected_scams (
        guild_id, message_id, user_id, username, channel_id, risk_score, severity,
        reasons, keywords, attachment_urls, ocr_text, image_hashes, action_taken, created_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ','now'))`,
      record.guildId,
      record.messageId,
      record.userId,
      record.username,
      record.channelId,
      record.riskScore,
      record.severity,
      serialize(record.reasons),
      serialize(record.keywords),
      serialize(record.attachmentUrls),
      record.ocrText || '',
      serialize(record.imageHashes),
      record.actionTaken || 'none'
    );
    return result.lastID;
  }

  async saveImageHash(record) {
    this.assertConnected();
    await this.db.run(
      `INSERT INTO image_hashes (guild_id, hash, message_id, user_id, channel_id, attachment_url, created_at)
       VALUES (?, ?, ?, ?, ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ','now'))`,
      record.guildId,
      record.hash,
      record.messageId,
      record.userId,
      record.channelId,
      record.attachmentUrl
    );
  }

  async getRecentImageHashes(guildId, limit = 2000) {
    this.assertConnected();
    return this.db.all(
      `SELECT id, guild_id, hash, message_id, user_id, channel_id, attachment_url, created_at
       FROM image_hashes
       WHERE guild_id = ?
       ORDER BY created_at DESC
       LIMIT ?`,
      guildId,
      limit
    );
  }

  async saveStrike(record) {
    this.assertConnected();
    await this.db.run(
      `INSERT INTO strike_history (guild_id, user_id, message_id, risk_score, severity, reason, created_at)
       VALUES (?, ?, ?, ?, ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ','now'))`,
      record.guildId,
      record.userId,
      record.messageId,
      record.riskScore,
      record.severity,
      record.reason
    );
  }

  async saveTimeout(record) {
    this.assertConnected();
    await this.db.run(
      `INSERT INTO timeout_history (guild_id, user_id, duration_ms, reason, moderator_id, created_at)
       VALUES (?, ?, ?, ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ','now'))`,
      record.guildId,
      record.userId,
      record.durationMs,
      record.reason,
      record.moderatorId || 'bot'
    );
  }

  async saveRiskScore(record) {
    this.assertConnected();
    await this.db.run(
      `INSERT INTO risk_scores (guild_id, user_id, message_id, score, severity, breakdown, created_at)
       VALUES (?, ?, ?, ?, ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ','now'))`,
      record.guildId,
      record.userId,
      record.messageId,
      record.score,
      record.severity,
      serialize(record.breakdown)
    );
  }

  async saveUserActivity(record) {
    this.assertConnected();
    await this.db.run(
      `INSERT INTO user_activity (guild_id, user_id, channel_id, message_id, attachment_hashes, attachment_count, created_at)
       VALUES (?, ?, ?, ?, ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ','now'))`,
      record.guildId,
      record.userId,
      record.channelId,
      record.messageId,
      serialize(record.attachmentHashes),
      record.attachmentCount
    );
  }

  async getRecentUserActivity(guildId, userId, sinceIso) {
    this.assertConnected();
    const rows = await this.db.all(
      `SELECT id, guild_id, user_id, channel_id, message_id, attachment_hashes, attachment_count, created_at
       FROM user_activity
       WHERE guild_id = ? AND user_id = ? AND created_at >= ?
       ORDER BY created_at DESC`,
      guildId,
      userId,
      sinceIso
    );
    return rows.map((row) => ({
      ...row,
      attachment_hashes: parseJson(row.attachment_hashes)
    }));
  }

  async getRecentScams(guildId, limit = 10) {
    this.assertConnected();
    const rows = await this.db.all(
      `SELECT * FROM detected_scams
       WHERE guild_id = ?
       ORDER BY created_at DESC
       LIMIT ?`,
      guildId,
      limit
    );
    return rows.map((row) => ({
      ...row,
      reasons: parseJson(row.reasons),
      keywords: parseJson(row.keywords),
      attachment_urls: parseJson(row.attachment_urls),
      image_hashes: parseJson(row.image_hashes)
    }));
  }

  async getStats(guildId, days = 7) {
    this.assertConnected();
    const since = new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString();
    const totals = await this.db.all(
      `SELECT severity, COUNT(*) AS count
       FROM detected_scams
       WHERE guild_id = ? AND created_at >= ?
       GROUP BY severity`,
      guildId,
      since
    );
    const topUsers = await this.db.all(
      `SELECT user_id, username, COUNT(*) AS count, MAX(risk_score) AS max_score
       FROM detected_scams
       WHERE guild_id = ? AND created_at >= ?
       GROUP BY user_id, username
       ORDER BY count DESC, max_score DESC
       LIMIT 5`,
      guildId,
      since
    );
    const recentCount = await this.db.get(
      'SELECT COUNT(*) AS count FROM detected_scams WHERE guild_id = ? AND created_at >= ?',
      guildId,
      since
    );
    const hashCount = await this.db.get(
      'SELECT COUNT(*) AS count FROM image_hashes WHERE guild_id = ?',
      guildId
    );
    return {
      days,
      totals,
      topUsers,
      recentCount: recentCount.count,
      hashCount: hashCount.count
    };
  }

  async getRecentHashes(guildId, limit = 10) {
    this.assertConnected();
    return this.db.all(
      `SELECT hash, user_id, channel_id, message_id, created_at
       FROM image_hashes
       WHERE guild_id = ?
       ORDER BY created_at DESC
       LIMIT ?`,
      guildId,
      limit
    );
  }

  async deleteHash(guildId, hash) {
    this.assertConnected();
    const result = await this.db.run(
      'DELETE FROM image_hashes WHERE guild_id = ? AND hash = ?',
      guildId,
      hash
    );
    return result.changes || 0;
  }
}

module.exports = {
  Database,
  parseJson
};
