# Milo - A Fun-Focused Discord Bot

Milo is a powerful, multi-functional Discord bot built with Python and discord.py. It's packed with features ranging from economy and games to fun interactions, all designed to bring more entertainment to your server.

## ⚙️ Configuration and Setup

Follow these steps to get the bot up and running.

### 1. Clone the Repository

First, clone this repository to your local machine or server.

```bash
git clone https://github.com/msgaxzzz/Milo-discord-fun-bot.git
cd Milo-bot

Install Dependencies:
The project's dependencies are listed in the requirements.txt file. Install them using pip:
pip install -r requirements.txt



Create the Configuration File
The bot requires a config.json file in the root directory to store the bot token.
Create a file named config.json in the same directory as main.py.
Open the file and add the following content:
{
  "DISCORD_TOKEN": "YOUR_BOT_TOKEN_HERE"
}

Replace "YOUR_BOT_TOKEN_HERE" with your actual Discord bot token. You can get this from the https://discord.com/developers/applications


Running the Bot
Once the configuration is complete, you can start the bot with the following command:
python main.py