const config = require("../config/env");

const OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses";

function isConfigured() {
  return Boolean(config.openaiApiKey);
}

function assertConfigured() {
  if (!isConfigured()) {
    throw new Error("ChatGPT belum aktif. Set OPENAI_API_KEY di environment.");
  }
}

function sanitizeAnswer(text) {
  const withoutCitations = text
    .replace(/cite[^]+/g, "")
    .replace(/【[^】]+】/g, "")
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

function extractResponseText(payload) {
  if (payload.output_text) return payload.output_text;

  const parts = [];
  for (const item of payload.output || []) {
    if (item.type !== "message") continue;

    for (const content of item.content || []) {
      if (content.type === "output_text" && content.text) {
        parts.push(content.text);
      }
    }
  }

  return parts.join("\n").trim();
}

async function answerWithWebSearch({ question }) {
  assertConfigured();

  const response = await fetch(OPENAI_RESPONSES_URL, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${config.openaiApiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: config.openaiModel,
      reasoning: { effort: "low" },
      tools: [{ type: "web_search", search_context_size: "low" }],
      tool_choice: "required",
      max_output_tokens: 800,
      instructions:
        "Kamu adalah asisten bot Discord untuk FIFA World Cup 2026. Gunakan web search untuk data terbaru. Jawab dalam bahasa Indonesia yang ringkas, jelas, dan enak dibaca di Discord embed. Jangan mengarang. Jangan tampilkan sumber, URL, citation, footnote, blok referensi, atau catatan terpisah. Jangan pakai tabel Markdown. Gunakan bullet list pendek, bold untuk bagian penting, dan maksimal 6 item.",
      input: question,
    }),
  });

  if (!response.ok) {
    const details = await response.text();
    throw new Error(
      `OpenAI gagal (${response.status}): ${details.slice(0, 300)}`,
    );
  }

  const payload = await response.json();
  const content = extractResponseText(payload);

  if (!content) {
    throw new Error("OpenAI tidak mengembalikan jawaban.");
  }

  return {
    text: sanitizeAnswer(content),
  };
}

module.exports = {
  answerWithWebSearch,
  isConfigured,
};
