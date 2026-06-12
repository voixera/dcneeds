const { EmbedBuilder } = require("discord.js");
const { truncate } = require("./format");

function createLiveEmbed({ title, color, response }) {
  return new EmbedBuilder()
    .setColor(color)
    .setTitle(title)
    .setDescription(truncate(response.text, 3900))
    .setFooter({ text: "Dibuat oleh:@voixera" });
}

module.exports = {
  createLiveEmbed,
};
