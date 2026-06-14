const { EmbedBuilder } = require('discord.js');
const { toDiscordTimestamp } = require('./time');

const colors = {
  safe: 0x2ecc71,
  suspicious: 0xf1c40f,
  malicious: 0xe74c3c,
  info: 0x3498db
};

function truncate(value, max = 1024) {
  const text = String(value ?? '');
  if (text.length <= max) return text || 'None';
  return `${text.slice(0, max - 3)}...`;
}

function buildDetectionEmbed({ message, risk, actionTaken, ocrText, attachmentUrls = [] }) {
  const embed = new EmbedBuilder()
    .setColor(colors[risk.severity] || colors.info)
    .setTitle(`OAuth Guard: ${risk.severity.toUpperCase()} detection`)
    .setDescription(`Risk score: **${risk.score}/100**`)
    .addFields(
      { name: 'User', value: `${message.author.tag}\n\`${message.author.id}\``, inline: true },
      { name: 'Channel', value: `<#${message.channel.id}>`, inline: true },
      { name: 'Action', value: actionTaken || 'Logged', inline: true },
      { name: 'Reasons', value: truncate(risk.reasons.join('\n') || 'No reasons'), inline: false },
      { name: 'Matched Keywords', value: truncate(risk.keywords.join(', ') || 'None'), inline: false },
      { name: 'Time', value: toDiscordTimestamp(new Date()), inline: true }
    )
    .setFooter({ text: 'discord-oauth-guard' })
    .setTimestamp();

  if (ocrText) {
    embed.addFields({ name: 'OCR Preview', value: truncate(ocrText.replace(/\s+/g, ' '), 900), inline: false });
  }

  if (attachmentUrls.length) {
    embed.addFields({ name: 'Attachments', value: truncate(attachmentUrls.join('\n'), 900), inline: false });
    embed.setImage(attachmentUrls[0]);
  }

  return embed;
}

function buildSimpleEmbed(title, description, color = colors.info) {
  return new EmbedBuilder()
    .setColor(color)
    .setTitle(title)
    .setDescription(description)
    .setTimestamp();
}

module.exports = {
  colors,
  truncate,
  buildDetectionEmbed,
  buildSimpleEmbed
};
