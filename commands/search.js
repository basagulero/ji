const { SlashCommandBuilder } = require('discord.js');
const axios = require('axios');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('search')
    .setDescription('Search the internet')
    .addStringOption(option =>
      option.setName('query')
        .setDescription('What do you want to search for?')
        .setRequired(true)
    ),
  async execute(interaction) {
    const query = interaction.options.getString('query');
    await interaction.deferReply();
    try {
      const url = `https://lite.duckduckgo.com/lite/?q=${encodeURIComponent(query)}`;
      const res = await axios.get(url);
      const match = res.data.match(/<a rel="nofollow" class="result-link" href="(.*?)">(.*?)<\/a>/);
      if (match) {
        await interaction.editReply(`🔍 **${match[2]}**\n${match[1]}`);
      } else {
        await interaction.editReply('❌ No results found.');
      }
    } catch (e) {
      console.error(e);
      await interaction.editReply('⚠️ Error while searching.');
    }
  }
};
