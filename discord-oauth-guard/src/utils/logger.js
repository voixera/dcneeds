const fs = require('node:fs');
const path = require('node:path');
const env = require('../config/env');

const levels = {
  error: 0,
  warn: 1,
  info: 2,
  debug: 3
};

const configuredLevel = levels[env.logLevel] ?? levels.info;
const logDir = path.resolve(process.cwd(), 'logs');
const logFile = path.join(logDir, 'oauth-guard.log');

function write(level, args) {
  if ((levels[level] ?? levels.info) > configuredLevel) return;

  const line = `[${new Date().toISOString()}] [${level.toUpperCase()}] ${args
    .map((arg) => (arg instanceof Error ? `${arg.stack || arg.message}` : String(arg)))
    .join(' ')}\n`;

  if (!fs.existsSync(logDir)) {
    fs.mkdirSync(logDir, { recursive: true });
  }

  fs.appendFile(logFile, line, () => {});
  const consoleMethod = level === 'error' ? 'error' : level === 'warn' ? 'warn' : 'log';
  console[consoleMethod](line.trim());
}

module.exports = {
  error: (...args) => write('error', args),
  warn: (...args) => write('warn', args),
  info: (...args) => write('info', args),
  debug: (...args) => write('debug', args)
};
