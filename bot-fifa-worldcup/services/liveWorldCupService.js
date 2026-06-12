const config = require("../config/env");
const groqService = require("./groqService");

function isConfigured() {
  return config.liveAnswersEnabled && groqService.isConfigured();
}

function buildQuestion(type, params = {}) {
  const team = params.team || params.query || "";
  const group = params.group || "";
  const limit = params.limit || 5;

  if (type === "jadwal") {
    return `Tampilkan ${limit} jadwal pertandingan Piala Dunia 2026${
      team ? ` untuk ${team}` : " terdekat"
    }. Sertakan tanggal, jam jika tersedia, lawan, grup, dan venue.`;
  }

  if (type === "hasil") {
    return `Tampilkan ${limit} hasil pertandingan terbaru Piala Dunia 2026${
      team ? ` untuk ${team}` : ""
    }. Sertakan skor dan grup jika tersedia.`;
  }

  if (type === "klasemen") {
    return `Tampilkan klasemen Piala Dunia 2026${
      group ? ` Grup ${group.toUpperCase()}` : " yang relevan"
    }. Sertakan poin, main, menang, seri, kalah, dan selisih gol jika tersedia.`;
  }

  if (type === "tim") {
    return `Berikan informasi tim nasional ${team} di Piala Dunia 2026: grup, lawan, jadwal, pemain/pelatih penting jika tersedia, dan catatan singkat.`;
  }

  return `Jawab tentang Piala Dunia 2026: ${team || group}`;
}

async function answer(type, params = {}) {
  if (!isConfigured()) {
    throw new Error(
      "Live Groq belum aktif. Set GROQ_API_KEY dan gunakan model groq/compound atau groq/compound-mini.",
    );
  }

  const question = buildQuestion(type, params);
  const response = await groqService.answerWithWebSearch({ question });

  return {
    ...response,
    model: config.groqModel,
  };
}

module.exports = {
  answer,
  isConfigured,
};
