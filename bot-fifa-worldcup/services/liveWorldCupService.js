const config = require("../config/env");
const openaiService = require("./openaiService");

function isConfigured() {
  return config.liveAnswersEnabled && openaiService.isConfigured();
}

function buildQuestion(type, params = {}) {
  const team = params.team || params.query || "";
  const group = params.group || "";
  const limit = params.limit || 5;
  const style =
    "Format jawaban: bullet list Discord yang rapi, bukan tabel Markdown. Jangan tampilkan sumber, link, sitasi, nomor referensi, atau bagian Catatan/Sumber. Jika hasil belum resmi, tulis singkat di item pertandingan tersebut.";

  if (type === "jadwal") {
    return `Tampilkan ${limit} jadwal pertandingan Piala Dunia 2026${
      team ? ` untuk ${team}` : " terdekat"
    }. Sertakan tanggal, jam jika tersedia, lawan, grup, dan venue. ${style}`;
  }

  if (type === "hasil") {
    return `Tampilkan ${limit} hasil pertandingan terbaru Piala Dunia 2026${
      team ? ` untuk ${team}` : ""
    }. Sertakan skor dan grup jika tersedia. ${style}`;
  }

  if (type === "klasemen") {
    return `Tampilkan klasemen Piala Dunia 2026${
      group ? ` Grup ${group.toUpperCase()}` : " yang relevan"
    }. Sertakan poin, main, menang, seri, kalah, dan selisih gol jika tersedia. ${style}`;
  }

  if (type === "tim") {
    return `Berikan informasi tim nasional ${team} di Piala Dunia 2026: grup, lawan, jadwal, pemain/pelatih penting jika tersedia, dan ringkasan singkat. ${style}`;
  }

  return `Jawab tentang Piala Dunia 2026: ${team || group}. ${style}`;
}

async function answer(type, params = {}) {
  if (!isConfigured()) {
    throw new Error(
      "Live ChatGPT belum aktif. Set OPENAI_API_KEY di environment.",
    );
  }

  const question = buildQuestion(type, params);
  const response = await openaiService.answerWithWebSearch({ question });

  return {
    ...response,
    model: config.openaiModel,
  };
}

module.exports = {
  answer,
  isConfigured,
};
