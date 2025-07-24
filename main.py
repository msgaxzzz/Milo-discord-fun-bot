import discord
from discord.ext import commands
from discord import app_commands
import os
import json
import sys
import aiosqlite
from collections import defaultdict
import datetime

def load_config():
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("FATAL ERROR: config.json file not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        print("FATAL ERROR: Could not decode config.json.")
        sys.exit(1)

config = load_config()
TOKEN = config.get('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class FunBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.db = None
        self.user_message_timestamps = defaultdict(list)
        self.start_time = discord.utils.utcnow()

    async def setup_hook(self):
        self.db = await aiosqlite.connect('database/main.db')
        print("Successfully connected to the database.")
        
        async with self.db.cursor() as cursor:
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    message_id INTEGER PRIMARY KEY,
                    guild_id INTEGER,
                    user_id INTEGER,
                    timestamp TEXT
                )
            ''')
        await self.db.commit()
        
        cogs_folder = "cogs"
        for filename in os.listdir(cogs_folder):
            if filename.endswith(".py"):
                try:
                    await self.load_extension(f"{cogs_folder}.{filename[:-3]}")
                    print(f"Loaded cog: {filename}")
                except Exception as e:
                    print(f"Failed to load cog {filename}: {e}")
        
        await self.tree.sync()
        print("Slash commands have been synced.")

    async def on_ready(self):
        print(f'Logged in as {self.user.name}')
        print(f'Bot ID: {self.user.id}')
        print('------')

    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        self.dispatch("message", message)
        await self.process_commands(message)

    async def close(self):
        if self.db:
            await self.db.close()
            print("Database connection closed.")
        await super().close()

bot = FunBot()

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(f"This command is on cooldown. Please try again in {error.retry_after:.2f}s.", ephemeral=True)
    elif isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("You don't have the required permissions to use this command.", ephemeral=True)
    elif isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message("A check failed, you might not be able to use this command.", ephemeral=True)
    else:
        print(f"An unhandled app command error occurred: {error}")
        if not interaction.response.is_done():
            await interaction.response.send_message("An unexpected error occurred. Please try again later.", ephemeral=True)
        else:
            await interaction.followup.send("An unexpected error occurred. Please try again later.", ephemeral=True)

print("Configuration loaded. Starting bot...")
bot.run(TOKEN)