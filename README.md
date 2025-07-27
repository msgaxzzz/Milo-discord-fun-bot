# Milo - A Feature-Rich Discord Fun Bot

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/Python-3.7%2B-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![GitHub stars](https://img.shields.io/github/stars/msgaxzzz/Milo-discord-fun-bot.svg?style=social&label=Star)](https://github.com/msgaxzzz/Milo-discord-fun-bot/stargazers)

---
## Update Log For the latest feature updates and fixes, please check our complete update log: [View Update Log](https://github.com/msgaxzzz/Milo-discord-fun-bot/blob/main/CHANGELOG.md)

---

## Milo is a powerful, multi-functional Discord bot built with modern Python and discord.py.  
## Designed to be the ultimate entertainment hub for any server, Milo features a full economy system, interactive games, and an advanced AI chat with web-enabled search capabilities.

---
## ✨ Features

Milo is built with a modular cog architecture, with each module providing a unique set of features.

### 🤖 AI Chat & Tools (`/chat`)
- **Direct & Private Conversations**: Chat directly in any channel or in DMs with the bot.
- **Web-Enabled AI**: The AI can perform live Google searches for up-to-the-minute information on current events, news, and specific data.
- **Configurable Intelligence**:
  - **Dynamic Model Selection**: Choose the best AI model for the job (`gpt-4o`, `gpt-4o-mini`, etc.) for each conversation.
  - **Custom Personas**: Server admins can set a unique personality for the bot, making it act like anything from a pirate to a poet.
  - **Bring Your Own Key**: Admins can configure their own OpenAI API keys for their server.
- **Smart Context**: The bot remembers the context of your conversation in each channel and DM separately.
- **Optional Web Search**: Users can decide for each prompt whether to enable web search or not.

### 💰 Full Economy System (`/balance`, `/jobs`, etc.)
- **Currency & Wallet**: Earn and manage your own server currency (coins).
- **Multiple Income Streams**:
  - `/daily`: Claim your daily login bonus.
  - `/jobs freelance`: Quick, low-reward jobs with a short cooldown.
  - `/jobs regular`: Steady, medium-reward jobs with a medium cooldown.
  - `/jobs crime`: High-risk, high-reward jobs with a long cooldown.
- **Player vs. Player**:
  - `/transfer`: Securely transfer coins to other users.
  - `/rob`: Attempt to rob another user (with a chance of failure and a fine!).
- **Gambling**:
  - `/gamble`: A simple double-or-nothing dice game.
  - `/slots`: Try your luck at the slot machine!
- **Community**:
  - `/leaderboard`: See who the richest users on the server are.

### 🎮 Games & Fun (`/tictactoe`, `/guess`, etc.)
- **Interactive Games**:
  - `/tictactoe`: Challenge another server member to a game of Tic-Tac-Toe with interactive buttons.
  - `/guess`: A classic number guessing game against the bot.
- **Classic Fun**:
  - `/eightball`: Ask the magic 8-ball a question.
  - `/rps`: Play Rock, Paper, Scissors.
  - `/roll`: Roll dice in NdN format (e.g., `2d6`).
  - `/coinflip`: Flip a coin.
- **Creative & Social**:
  - `/tweet`: Generate an image of a fake tweet with your text and avatar.
  - `/love`: A "love calculator" to test compatibility between two users.
  - `/joke` & `/fact`: Get random jokes and interesting facts.
  - `/poll`: Create a simple poll with up to 10 options.
- **Text Manipulation**:
  - `/emojify`: Turn your text into emoji letters.
  - `/clap`: Add a 👏 between 👏 every 👏 word.

### 💕 GIF-Powered Interactions (`/hug`, `/slap`, etc.)
- Express yourself with animated GIFs for a more lively interaction!
- Commands include: `/hug`, `/pat`, `/slap`, `/kiss`, `/cuddle`, `/poke`.

### 🛠️ Utility & Tools (`/help`, `/serverinfo`, etc.)
- **Advanced Help System**: A multi-level help command (`/help all` and `/help command`).
- **Information Commands**:
  - `/serverinfo`: Get detailed stats about the current server.
  - `/memberinfo`: See details about a specific user.
  - `/botinfo`: View stats about the Milo bot itself.
  - `/avatar`: View a user's avatar in high resolution.
- **Personal Tools**:
  - `/remindme`: Set a personal reminder, and the bot will DM you.
- **Moderation**:
  - `/clear`: A simple command for admins to bulk-delete messages.

---

## 🚀 Getting Started

There are two ways to set up the bot: a one-line installer for new servers, or a manual setup for more control.

### Method 1: The Easy Way (One-Line Installer)
For a fresh Linux server, you can use this single command to download the installer script and run it automatically. It will check for dependencies, clone the repo, and set up the project structure for you.

## Installation:

```bash
curl -sSL https://raw.githubusercontent.com/msgaxzzz/Milo-discord-fun-bot/main/install.sh | bash
```
---

## Method 2: Manual Installation
Follow these steps to set up the bot on your local machine or server.

## 1. Clone the Repository
```bash
git clone https://github.com/msgaxzzz/Milo-discord-fun-bot.git
cd Milo-discord-fun-bot
```

Install Dependencies
The project's dependencies are listed in requirements.txt. Install them using pip:
# It's recommended to use python3 and pip3 on most systems

```bash
pip3 install -r requirements.txt
```

Create the Database Folder
The bot uses an SQLite database. You need to create a folder for it manually.
```bash
mkdir database
```

Running the Bot
Once the configuration is complete, start the bot with:
```bash
python3 main.py
```
