function toDiscordTimestamp(date = new Date(), style = 'f') {
  const seconds = Math.floor(new Date(date).getTime() / 1000);
  return `<t:${seconds}:${style}>`;
}

function msToHuman(ms) {
  const seconds = Math.floor(ms / 1000);
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);

  const parts = [];
  if (days) parts.push(`${days}d`);
  if (hours) parts.push(`${hours}h`);
  if (minutes) parts.push(`${minutes}m`);
  if (!parts.length) parts.push(`${seconds}s`);
  return parts.join(' ');
}

function sinceIso(msAgo) {
  return new Date(Date.now() - msAgo).toISOString();
}

module.exports = {
  toDiscordTimestamp,
  msToHuman,
  sinceIso
};
