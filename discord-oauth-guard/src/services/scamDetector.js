function normalizeText(text) {
  return String(text || '')
    .toLowerCase()
    .replace(/[^\p{L}\p{N}@#:$./\s-]/gu, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function keywordToPattern(keyword) {
  const escaped = keyword
    .toLowerCase()
    .split(/\s+/)
    .map((part) => part.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
    .join('\\s+');
  return new RegExp(`\\b${escaped}\\b`, 'iu');
}

class ScamDetector {
  constructor(keywords = []) {
    this.keywords = keywords;
  }

  setKeywords(keywords) {
    this.keywords = keywords;
  }

  scanText(text, keywords = this.keywords) {
    const normalized = normalizeText(text);
    const matchedKeywords = [];

    for (const keyword of keywords) {
      if (keywordToPattern(keyword).test(normalized)) {
        matchedKeywords.push(keyword);
      }
    }

    return {
      normalizedText: normalized,
      matchedKeywords,
      hasScamKeyword: matchedKeywords.length > 0,
      hasMultipleKeywords: matchedKeywords.length >= 2
    };
  }

  scanMessageContent(message, keywords = this.keywords) {
    return this.scanText(message.content || '', keywords);
  }
}

module.exports = {
  ScamDetector,
  normalizeText
};
