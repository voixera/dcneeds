const config = require("../config/env");

const OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses";
const WEB_SEARCH_TOOL = { type: "web_search", search_context_size: "low" };

function isConfigured() {
  return getOpenaiApiKeys().length > 0;
}

function assertConfigured() {
  if (!isConfigured()) {
    throw new Error("ChatGPT belum aktif. Set OPENAI_API_KEY di environment.");
  }
}

function getOpenaiApiKeys() {
  if (Array.isArray(config.openaiApiKeys) && config.openaiApiKeys.length > 0) {
    return config.openaiApiKeys;
  }

  return config.openaiApiKey ? [config.openaiApiKey] : [];
}

function isKeyRetryableError(status, details) {
  if ([401, 403, 429].includes(status)) return true;
  return /billing|insufficient_quota|invalid_api_key|quota|rate_limit/i.test(
    details,
  );
}

function formatOpenAiHttpError(status, details, keyIndex, keyCount) {
  const keyLabel =
    keyCount > 1 ? ` key ${keyIndex + 1}/${keyCount}` : "";

  return `OpenAI gagal${keyLabel} (${status}): ${details.slice(0, 300)}`;
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

function summarizeResponse(payload) {
  const outputTypes = (payload.output || [])
    .map((item) => {
      const status = item.status ? `:${item.status}` : "";
      return `${item.type || "unknown"}${status}`;
    })
    .join(", ");

  return [
    payload.status ? `status=${payload.status}` : null,
    payload.incomplete_details?.reason
      ? `reason=${payload.incomplete_details.reason}`
      : null,
    outputTypes ? `output=${outputTypes}` : null,
  ]
    .filter(Boolean)
    .join("; ");
}

async function answerWithWebSearch({ question }) {
  assertConfigured();
  const apiKeys = getOpenaiApiKeys();
  const requestBody = JSON.stringify({
    model: config.openaiModel,
    reasoning: { effort: "low" },
    tools: [WEB_SEARCH_TOOL],
    tool_choice: "auto",
    max_output_tokens: 800,
    instructions:
      "Kamu adalah asisten bot Discord untuk FIFA World Cup 2026. Gunakan web search untuk data terbaru. Jawab dalam bahasa Indonesia yang ringkas, jelas, dan enak dibaca di Discord embed. Jangan mengarang. Jangan tampilkan sumber, URL, citation, footnote, blok referensi, atau catatan terpisah. Jangan pakai tabel Markdown. Gunakan bullet list pendek, bold untuk bagian penting, dan maksimal 6 item.",
    input: `Gunakan web search sebelum menjawab. ${question}`,
  });

  for (let index = 0; index < apiKeys.length; index += 1) {
    const response = await fetch(OPENAI_RESPONSES_URL, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKeys[index]}`,
        "Content-Type": "application/json",
      },
      body: requestBody,
    });

    if (!response.ok) {
      const details = await response.text();
      const canTryNext =
        index < apiKeys.length - 1 &&
        isKeyRetryableError(response.status, details);

      if (canTryNext) continue;

      throw new Error(
        formatOpenAiHttpError(response.status, details, index, apiKeys.length),
      );
    }

    const payload = await response.json();
    const content = extractResponseText(payload);

    if (!content) {
      const summary = summarizeResponse(payload);
      throw new Error(
        `OpenAI tidak mengembalikan jawaban${summary ? ` (${summary})` : ""}.`,
      );
    }

    return {
      text: sanitizeAnswer(content),
    };
  }

  throw new Error("OpenAI gagal: tidak ada API key yang bisa dipakai.");
}

module.exports = {
  answerWithWebSearch,
  isConfigured,
};
