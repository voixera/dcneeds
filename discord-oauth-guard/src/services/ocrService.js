const { recognize } = require('tesseract.js');
const sharp = require('sharp');
const defaultConfig = require('../config/defaultConfig');
const logger = require('../utils/logger');

function withTimeout(promise, timeoutMs, message) {
  let timeoutId;
  const timeoutPromise = new Promise((_, reject) => {
    timeoutId = setTimeout(() => reject(new Error(message)), timeoutMs);
  });

  return Promise.race([promise, timeoutPromise]).finally(() => clearTimeout(timeoutId));
}

class OcrService {
  async extractText(filePath, options = {}) {
    const language = options.language || defaultConfig.ocr.language;
    const timeoutMs = options.timeoutMs || defaultConfig.ocr.timeoutMs;

    try {
      const preparedImage = await sharp(filePath, { limitInputPixels: 4096 * 4096 })
        .resize({ width: 1600, height: 1600, fit: 'inside', withoutEnlargement: true })
        .greyscale()
        .normalize()
        .png()
        .toBuffer();

      const result = await withTimeout(
        recognize(preparedImage, language, {
          logger: (event) => logger.debug(`ocr ${event.status || 'status'} ${event.progress || 0}`)
        }),
        timeoutMs,
        `OCR timed out after ${timeoutMs}ms`
      );
      return (result?.data?.text || '').trim();
    } catch (error) {
      logger.warn(`OCR failed for ${filePath}:`, error.message);
      return '';
    }
  }
}

module.exports = OcrService;
