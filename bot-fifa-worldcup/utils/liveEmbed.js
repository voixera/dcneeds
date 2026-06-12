const { EmbedBuilder } = require("discord.js");
const { truncate } = require("./format");

function formatSources(sources) {
  return sources
    .slice(0, 5)
    .map((source) => `[${source.index}] ${truncate(source.title, 80)}\n${source.link}`)
    .join("\n\n");
}

function createLiveEmbed({ title, color, response }) {
  const embed = new EmbedBuilder()
    .setColor(color)
    .setTitle(title)
    .setDescription(truncate(response.text, 3900))
    .setFooter({ text: `Jawaban dibuat Groq (${response.model}) dengan web search bawaan.` });

  if (response.sources?.length) {
    embed.addFields({
      name: "Sumber",
      value: truncate(formatSources(response.sources), 1000),
    });
  }

  return embed;
}

module.exports = {
  createLiveEmbed,
};
