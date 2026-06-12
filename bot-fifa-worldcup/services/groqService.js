const config = require("../config/env");

const GROQ_CHAT_COMPLETIONS_URL =
  "https://api.groq.com/openai/v1/chat/completions";

function isConfigured() {
  return Boolean(config.groqApiKey);
}

function assertConfigured() {
  if (!isConfigured()) {
    throw new Error("Groq belum aktif. Set GROQ_API_KEY di environment.");
  }
}

function sanitizeAnswer(text) {
  const withoutCitations = text
    .replace(/cite[^]+/g, "")
    .replace(/\s*\[(?:\d+|source|sumber|referensi)[^\]]*\]/gi, "");
  const lines = withoutCitations.split(/\r?\n/);
  const kept = [];
  let skippingSourceBlock = false;

  for (const line of lines) {
    const trimmed = line.trim();
    const normalized = trimmed.toLowerCase();

    if (/^(sumber|sources?|referensi|references?)\b/.test(normalized)) {
      skippingSourceBlock = true;
      continue;
    }

    if (/^(catatan|notes?)\b/.test(normalized)) continue;

    if (skippingSourceBlock) continue;

    if (/https?:\/\//i.test(trimmed)) continue;

    kept.push(line.replace(/\s{2,}/g, " ").trimEnd());
  }

  const cleaned = kept.join("\n").replace(/\n{3,}/g, "\n\n").trim();
  return cleaned || withoutCitations.trim();
}

async function answerWithWebSearch({ question }) {
  assertConfigured();

  const response = await fetch(GROQ_CHAT_COMPLETIONS_URL, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${config.groqApiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: config.groqModel,
      temperature: 0.2,
      max_tokens: 750,
      search_settings: {
        exclude_domains: ["reddit.com", "facebook.com", "instagram.com", "tiktok.com"],
      },
      messages: [
        {
          role: "system",
          content:
            "Kamu adalah asisten bot Discord untuk FIFA World Cup 2026. Gunakan web search bawaan Groq jika butuh data terbaru. Jawab dalam bahasa Indonesia yang ringkas, jelas, dan enak dibaca di Discord embed. Jangan mengarang. Jangan tampilkan sumber, URL, citation, footnote, blok referensi, atau catatan terpisah. Jangan pakai tabel Markdown. Gunakan bullet list pendek, bold untuk bagian penting, dan maksimal 6 item.",
        },
        {
          role: "user",
          content: question,
        },
      ],
    }),
  });

  if (!response.ok) {
    const details = await response.text();
    throw new Error(`Groq gagal (${response.status}): ${details.slice(0, 300)}`);
  }

  const payload = await response.json();
  const message = payload.choices?.[0]?.message;
  const content = message?.content?.trim();

  if (!content) {
    throw new Error("Groq tidak mengembalikan jawaban.");
  }

  return {
    text: sanitizeAnswer(content),
  };
}

module.exports = {
  answerWithWebSearch,
  isConfigured,
};
