import discord
from discord.ext import commands
from discord import app_commands
import os
import sys
import aiosqlite
import aiohttp
from collections import defaultdict
import datetime
from typing import Optional
import logging

from config_loader import load_runtime_config

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Constants
DATABASE_PATH = "database/main.db"
COGS_FOLDER = "cogs"
SPAM_THRESHOLD = 5
SPAM_TIMEFRAME = 7  # seconds


config = load_runtime_config()
TOKEN = config["DISCORD_TOKEN"]

if not TOKEN:
    logger.critical("FATAL ERROR: DISCORD_TOKEN not found in config.")
    sys.exit(1)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True


class FunBot(commands.Bot):
    def __init__(self, runtime_config: dict):
        super().__init__(command_prefix="!", intents=intents)
        self.config = runtime_config
        self.db: Optional[aiosqlite.Connection] = None
        self.http_session: Optional[aiohttp.ClientSession] = None
        self.user_message_timestamps = defaultdict(list)
        self.start_time = discord.utils.utcnow()

    async def setup_hook(self):
        """Initialize database and load cogs."""
        # Ensure database directory exists
        os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

        # Connect to database
        self.db = await aiosqlite.connect(DATABASE_PATH)
        await self.db.execute("PRAGMA journal_mode=WAL")
        await self.db.execute("PRAGMA foreign_keys=ON")
        logger.info("Successfully connected to the database.")
        self.http_session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))

        # Initialize database schema
        async with self.db.cursor() as cursor:
            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    message_id INTEGER PRIMARY KEY,
                    guild_id INTEGER,
                    user_id INTEGER,
                    timestamp TEXT
                )
            """
            )
        await self.db.commit()

        # Load all cogs
        for filename in os.listdir(COGS_FOLDER):
            if filename.endswith(".py"):
                try:
                    await self.load_extension(f"{COGS_FOLDER}.{filename[:-3]}")
                    logger.info(f"Loaded cog: {filename}")
                except Exception as e:
                    logger.error(f"Failed to load cog {filename}: {e}")

        # Sync slash commands
        await self.tree.sync()
        logger.info("Slash commands have been synced.")

    async def on_ready(self):
        print(f"Logged in as {self.user.name}")
        print(f"Bot ID: {self.user.id}")
        print("------")

    async def on_message(self, message: discord.Message):
        """Handle incoming messages for logging and spam detection."""
        if message.author.bot:
            return

        # Log message to database
        if message.guild and self.db:
            try:
                async with self.db.cursor() as cursor:
                    await cursor.execute(
                        "INSERT INTO messages (message_id, guild_id, user_id, timestamp) VALUES (?, ?, ?, ?)",
                        (message.id, message.guild.id, message.author.id, message.created_at.isoformat()),
                    )
                await self.db.commit()
            except Exception as e:
                logger.error(f"Error logging message to database: {e}")

        # Anti-spam detection
        now = discord.utils.utcnow()
        user_timestamps = self.user_message_timestamps[message.author.id]
        user_timestamps.append(now)

        # Clean old timestamps
        user_timestamps = [t for t in user_timestamps if (now - t).total_seconds() < SPAM_TIMEFRAME]
        self.user_message_timestamps[message.author.id] = user_timestamps

        if len(user_timestamps) > SPAM_THRESHOLD:
            if len(user_timestamps) == SPAM_THRESHOLD + 1:
                try:
                    await message.channel.send(
                        f"{message.author.mention}, please slow down! Your recent messages will be deleted.",
                        delete_after=10,
                    )

                    def is_spam_message(m):
                        return m.author == message.author and (now - m.created_at).total_seconds() < SPAM_TIMEFRAME

                    await message.channel.purge(limit=SPAM_THRESHOLD + 1, check=is_spam_message, before=message)
                except discord.Forbidden:
                    await message.channel.send(
                        f"Warning for {message.author.mention}: Spam detected, but I don't have permission to delete messages."
                    )
                except Exception as e:
                    logger.error(f"An error occurred during spam cleanup: {e}")

        # Process commands
        await self.process_commands(message)

    async def close(self):
        if self.http_session and not self.http_session.closed:
            await self.http_session.close()
        if self.db:
            await self.db.close()
            print("Database connection closed.")
        await super().close()


bot = FunBot(config)


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(
            f"This command is on cooldown. Please try again in {error.retry_after:.2f}s.", ephemeral=True
        )
    elif isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "You don't have the required permissions to use this command.", ephemeral=True
        )
    elif isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message(
            "A check failed, you might not be able to use this command.", ephemeral=True
        )
    else:
        print(f"An unhandled app command error occurred: {error}")
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "An unexpected error occurred. Please try again later.", ephemeral=True
            )
        else:
            await interaction.followup.send("An unexpected error occurred. Please try again later.", ephemeral=True)


print("Configuration loaded. Starting bot...")
bot.run(TOKEN)
