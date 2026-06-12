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

function normalizeSearchResult(result, index) {
  return {
    index: index + 1,
    title: result.title || "Tanpa judul",
    link: result.url || result.link,
    snippet: result.content || result.snippet || "",
    score: result.score || null,
  };
}

function extractSources(message) {
  const tools = message.executed_tools || [];
  const results = tools.flatMap((tool) => {
    const searchResults = tool.search_results;
    if (Array.isArray(searchResults)) return searchResults;
    return searchResults?.results || [];
  });

  const seen = new Set();
  return results
    .map(normalizeSearchResult)
    .filter((source) => {
      if (!source.link || seen.has(source.link)) return false;
      seen.add(source.link);
      return true;
    });
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
            "Kamu adalah asisten bot Discord untuk FIFA World Cup 2026. Gunakan web search bawaan Groq jika butuh data terbaru. Jawab dalam bahasa Indonesia yang ringkas, jelas, dan enak dibaca. Jangan mengarang. Jika sumber belum cukup, katakan data belum cukup pasti. Sertakan sitasi jika tersedia.",
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
    text: content,
    sources: extractSources(message),
  };
}

module.exports = {
  answerWithWebSearch,
  isConfigured,
};
