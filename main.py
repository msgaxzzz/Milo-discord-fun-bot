import asyncio
import os
import sys
from collections import defaultdict
import datetime
from pathlib import Path
from typing import Optional
import logging


def _find_local_venv_python() -> Optional[Path]:
    project_root = Path(__file__).resolve().parent
    candidates = [
        project_root / ".venv" / "bin" / "python",
        project_root / ".venv" / "Scripts" / "python.exe",
    ]
    return next((candidate for candidate in candidates if candidate.exists()), None)


def _maybe_reexec_into_local_venv() -> None:
    if sys.prefix != sys.base_prefix:
        return

    venv_python = _find_local_venv_python()
    if not venv_python:
        return

    os.execv(str(venv_python), [str(venv_python), __file__, *sys.argv[1:]])


_maybe_reexec_into_local_venv()

try:
    import aiohttp
    import aiosqlite
    import discord
    from discord import app_commands
    from discord.ext import commands

    from config_loader import load_runtime_config
except ModuleNotFoundError as exc:
    missing_package = exc.name or "a required package"
    print(
        f"Missing Python dependency: {missing_package}\n"
        "Create and activate a local virtual environment, then install requirements:\n"
        "  python3 -m venv .venv\n"
        "  source .venv/bin/activate\n"
        "  python -m pip install -r requirements.txt",
        file=sys.stderr,
    )
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Constants
DATABASE_PATH = "database/main.db"
COGS_FOLDER = "cogs"
SPAM_THRESHOLD = 5
SPAM_TIMEFRAME = 7  # seconds
MESSAGE_LOG_BATCH_SIZE = 50
MESSAGE_LOG_FLUSH_SECONDS = 2


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
        self.message_log_queue: asyncio.Queue[Optional[tuple[int, int, int, str]]] = asyncio.Queue()
        self.message_log_task: Optional[asyncio.Task] = None
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
        self.message_log_task = asyncio.create_task(self._message_log_worker())

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

    async def _flush_message_logs(self, batch: list[tuple[int, int, int, str]]) -> None:
        if not batch or not self.db:
            return
        async with self.db.cursor() as cursor:
            await cursor.executemany(
                "INSERT OR IGNORE INTO messages (message_id, guild_id, user_id, timestamp) VALUES (?, ?, ?, ?)",
                batch,
            )
        await self.db.commit()

    async def _message_log_worker(self) -> None:
        batch: list[tuple[int, int, int, str]] = []
        loop = asyncio.get_running_loop()
        try:
            while True:
                item = await self.message_log_queue.get()
                if item is None:
                    break
                batch.append(item)
                deadline = loop.time() + MESSAGE_LOG_FLUSH_SECONDS
                while len(batch) < MESSAGE_LOG_BATCH_SIZE:
                    timeout = deadline - loop.time()
                    if timeout <= 0:
                        break
                    try:
                        item = await asyncio.wait_for(self.message_log_queue.get(), timeout=timeout)
                    except asyncio.TimeoutError:
                        break
                    if item is None:
                        await self._flush_message_logs(batch)
                        return
                    batch.append(item)
                await self._flush_message_logs(batch)
                batch.clear()
        except asyncio.CancelledError:
            if batch:
                await self._flush_message_logs(batch)
            raise

        if batch:
            await self._flush_message_logs(batch)

    async def on_message(self, message: discord.Message):
        """Handle incoming messages for logging and spam detection."""
        if message.author.bot:
            return

        # Log message to database
        if message.guild and self.db:
            try:
                await self.message_log_queue.put(
                    (message.id, message.guild.id, message.author.id, message.created_at.isoformat())
                )
            except Exception as e:
                logger.error(f"Error logging message to database: {e}")

        # Anti-spam detection
        now = discord.utils.utcnow()
        spam_key = (message.guild.id if message.guild else 0, message.channel.id, message.author.id)
        user_timestamps = self.user_message_timestamps[spam_key]
        user_timestamps.append(now)

        # Clean old timestamps
        user_timestamps = [t for t in user_timestamps if (now - t).total_seconds() < SPAM_TIMEFRAME]
        self.user_message_timestamps[spam_key] = user_timestamps

        if len(user_timestamps) > SPAM_THRESHOLD:
            if len(user_timestamps) == SPAM_THRESHOLD + 1:
                try:
                    await message.channel.send(
                        f"{message.author.mention}, please slow down! Your recent messages will be deleted.",
                        delete_after=10,
                    )

                    def is_spam_message(m):
                        return m.author == message.author and (now - m.created_at).total_seconds() < SPAM_TIMEFRAME

                    try:
                        await message.delete()
                    except discord.HTTPException:
                        pass
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
        if self.message_log_task:
            await self.message_log_queue.put(None)
            try:
                await self.message_log_task
            except Exception:
                logger.exception("Error while flushing queued message logs during shutdown.")
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
