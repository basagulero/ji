const { SlashCommandBuilder } = require('discord.js');
const cleverbot = require('cleverbot-free');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('ask')
    .setDescription('Ask the AI a question')
    .addStringOption(option =>
      option.setName('question')
        .setDescription('What do you want to ask?')
        .setRequired(true)
    ),
  async execute(interaction) {
    const question = interaction.options.getString('question');
    await interaction.deferReply();
    try {
      const response = await cleverbot(question);
      await interaction.editReply(response);
    } catch (e) {
      await interaction.editReply("🤖 Sorry, I couldn't generate a reply.");
    }
  }
};
