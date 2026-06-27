const sharp = require('sharp');
const defaultConfig = require('../config/defaultConfig');
const logger = require('../utils/logger');

sharp.concurrency(1);
sharp.cache(false);

let tesseract = null;

function getTesseract() {
  if (!tesseract) {
    tesseract = require('tesseract.js');
  }
  return tesseract;
}

function withTimeout(promise, timeoutMs, message) {
  let timeoutId;
  const timeoutPromise = new Promise((_, reject) => {
    timeoutId = setTimeout(() => reject(new Error(message)), timeoutMs);
  });

  return Promise.race([promise, timeoutPromise]).finally(() => clearTimeout(timeoutId));
}

class OcrService {
  constructor() {
    this.activeJobs = 0;
    this.queue = [];
  }

  async runQueued(task, maxConcurrent) {
    if (this.activeJobs >= maxConcurrent) {
      await new Promise((resolve) => this.queue.push(resolve));
    }

    this.activeJobs += 1;
    try {
      return await task();
    } finally {
      this.activeJobs -= 1;
      const next = this.queue.shift();
      if (next) next();
    }
  }

  async extractText(filePath, options = {}) {
    const enabled = options.enabled ?? defaultConfig.ocr.enabled;
    if (!enabled) {
      logger.debug('OCR disabled, skipping image text extraction.');
      return '';
    }

    const language = options.language || defaultConfig.ocr.language;
    const timeoutMs = options.timeoutMs || defaultConfig.ocr.timeoutMs;
    const maxConcurrent = options.maxConcurrent || defaultConfig.ocr.maxConcurrent;
    const imageMaxDimension = options.imageMaxDimension || defaultConfig.ocr.imageMaxDimension;

    try {
      return await this.runQueued(async () => {
        const preparedImage = await sharp(filePath, { limitInputPixels: imageMaxDimension * imageMaxDimension * 4 })
          .resize({ width: imageMaxDimension, height: imageMaxDimension, fit: 'inside', withoutEnlargement: true })
          .greyscale()
          .normalize()
          .png()
          .toBuffer();

        const { recognize } = getTesseract();
        const result = await withTimeout(
          recognize(preparedImage, language, {
            logger: (event) => logger.debug(`ocr ${event.status || 'status'} ${event.progress || 0}`)
          }),
          timeoutMs,
          `OCR timed out after ${timeoutMs}ms`
        );
        return (result?.data?.text || '').trim();
      }, maxConcurrent);
    } catch (error) {
      logger.warn(`OCR failed for ${filePath}:`, error.message);
      return '';
    }
  }
}

module.exports = OcrService;
