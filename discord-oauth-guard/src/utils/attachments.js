const fs = require('node:fs/promises');
const path = require('node:path');
const crypto = require('node:crypto');
const env = require('../config/env');
const config = require('../config/defaultConfig');

function extensionFromAttachment(attachment) {
  const parsed = path.extname(attachment.name || attachment.url || '').toLowerCase();
  if (parsed) return parsed;
  const contentType = attachment.contentType || '';
  if (contentType.includes('png')) return '.png';
  if (contentType.includes('webp')) return '.webp';
  if (contentType.includes('gif')) return '.gif';
  return '.jpg';
}

function isImageAttachment(attachment) {
  const contentType = attachment.contentType || '';
  const name = (attachment.name || '').toLowerCase();
  return (
    config.images.allowedContentTypes.has(contentType) ||
    /\.(png|jpe?g|webp|gif)$/i.test(name)
  );
}

async function downloadAttachment(attachment) {
  if (attachment.size && attachment.size > config.images.maxBytes) {
    throw new Error(`Attachment too large: ${attachment.size} bytes`);
  }

  await fs.mkdir(env.tempDir, { recursive: true });
  const extension = extensionFromAttachment(attachment);
  const fileName = `${Date.now()}-${crypto.randomUUID()}${extension}`;
  const filePath = path.join(env.tempDir, fileName);

  const response = await fetch(attachment.url);
  if (!response.ok) {
    throw new Error(`Failed to download attachment: HTTP ${response.status}`);
  }

  const arrayBuffer = await response.arrayBuffer();
  if (arrayBuffer.byteLength > config.images.maxBytes) {
    throw new Error(`Downloaded attachment too large: ${arrayBuffer.byteLength} bytes`);
  }

  await fs.writeFile(filePath, Buffer.from(arrayBuffer));
  return filePath;
}

async function safeUnlink(filePath) {
  if (!filePath) return;
  try {
    await fs.unlink(filePath);
  } catch {
    // Temporary files are cleaned on a best-effort basis.
  }
}

module.exports = {
  isImageAttachment,
  downloadAttachment,
  safeUnlink
};
