import json
import logging
from collections import defaultdict
from datetime import timedelta
from typing import Any, Dict, List, Optional, Tuple

import discord
from discord import app_commands
from discord.ext import commands, tasks


logger = logging.getLogger(__name__)

DEFAULT_API_BASE = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-3.5-turbo"
MAX_CONVERSATION_HISTORY = 10
MAX_PERSONA_LENGTH = 500
MAX_EMBED_FIELD_LENGTH = 1024
MAX_EMBED_DESCRIPTION_LENGTH = 4096
CONVERSATION_TTL = timedelta(hours=6)
COOLDOWN_RETENTION = timedelta(days=1)
DEFAULT_PERSONA = (
    "You are Milo, a friendly and helpful Discord bot. "
    "You can access real-time information using the 'google_search' tool for current events or specific data. "
    "Keep your answers concise and engaging."
)


class Chat(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.conversations: Dict[Tuple[Any, ...], List[Dict[str, Any]]] = defaultdict(list)
        self.chat_cooldowns: Dict[Tuple[int, int], discord.utils.utcnow] = {}
        self.conversation_last_used: Dict[Tuple[Any, ...], discord.utils.utcnow] = {}
        self.load_config()
        self.bot.loop.create_task(self.setup_database())
        self._prune_cooldowns.start()

    def cog_unload(self):
        self._prune_cooldowns.cancel()

    def load_config(self):
        config = getattr(self.bot, "config", {})
        self.default_api_key = config.get("OPENAI_API_KEY")
        self.api_base = config.get("OPENAI_API_BASE", DEFAULT_API_BASE)
        self.allow_user_keys = config.get("ALLOW_USER_KEYS", True)
        self.default_model = config.get("DEFAULT_CHAT_MODEL", DEFAULT_MODEL)
        self.allowed_models = config.get("ALLOWED_CHAT_MODELS", [DEFAULT_MODEL])
        self.google_api_key = config.get("GOOGLE_API_KEY")
        self.google_cse_id = config.get("GOOGLE_CSE_ID")
        self.enable_web_search = bool(self.google_api_key and self.google_cse_id)

    @tasks.loop(minutes=10)
    async def _prune_cooldowns(self):
        now = discord.utils.utcnow()
        expired = [key for key, ts in self.chat_cooldowns.items() if (now - ts) > COOLDOWN_RETENTION]
        for key in expired:
            del self.chat_cooldowns[key]

    async def setup_database(self):
        async with self.bot.db.cursor() as cursor:
            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS guild_configs (
                    guild_id INTEGER PRIMARY KEY,
                    openai_key TEXT,
                    persona TEXT
                )
                """
            )
            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_policies (
                    guild_id INTEGER PRIMARY KEY,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    cooldown_seconds INTEGER NOT NULL DEFAULT 8,
                    daily_usage_limit INTEGER,
                    allowed_channel_ids TEXT,
                    blocked_channel_ids TEXT,
                    allowed_role_ids TEXT
                )
                """
            )
            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_usage (
                    guild_id INTEGER NOT NULL,
                    usage_date TEXT NOT NULL,
                    usage_count INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (guild_id, usage_date)
                )
                """
            )

            columns = await self._table_columns(cursor, "guild_configs")
            if "persona" not in columns:
                await cursor.execute("ALTER TABLE guild_configs ADD COLUMN persona TEXT")
        await self.bot.db.commit()

    async def _table_columns(self, cursor, table_name: str) -> List[str]:
        await cursor.execute(f"PRAGMA table_info({table_name})")
        return [row[1] for row in await cursor.fetchall()]

    @property
    def session(self):
        return self.bot.http_session

    def _context_key(self, interaction: discord.Interaction) -> Tuple[Any, ...]:
        if interaction.guild_id:
            return ("guild", interaction.guild_id, interaction.channel_id, interaction.user.id)
        return ("dm", interaction.user.id)

    def _serialize_ids(self, ids: List[int]) -> Optional[str]:
        cleaned = sorted({int(item) for item in ids})
        return json.dumps(cleaned) if cleaned else None

    def _deserialize_ids(self, raw: Optional[str]) -> List[int]:
        if not raw:
            return []
        try:
            values = json.loads(raw)
        except json.JSONDecodeError:
            return []
        return [int(item) for item in values if str(item).isdigit()]

    async def get_guild_config(self, guild_id: Optional[int]):
        if not guild_id:
            return None, None
        async with self.bot.db.cursor() as cursor:
            await cursor.execute("SELECT openai_key, persona FROM guild_configs WHERE guild_id = ?", (guild_id,))
            return await cursor.fetchone()

    async def set_guild_key(self, guild_id: int, key: Optional[str] = None):
        async with self.bot.db.cursor() as cursor:
            await cursor.execute("INSERT OR IGNORE INTO guild_configs (guild_id) VALUES (?)", (guild_id,))
            await cursor.execute("UPDATE guild_configs SET openai_key = ? WHERE guild_id = ?", (key, guild_id))
        await self.bot.db.commit()

    async def set_guild_persona(self, guild_id: int, persona: Optional[str] = None):
        async with self.bot.db.cursor() as cursor:
            await cursor.execute("INSERT OR IGNORE INTO guild_configs (guild_id) VALUES (?)", (guild_id,))
            await cursor.execute("UPDATE guild_configs SET persona = ? WHERE guild_id = ?", (persona, guild_id))
        await self.bot.db.commit()

    async def get_policy(self, guild_id: Optional[int]) -> Dict[str, Any]:
        default_policy = {
            "enabled": True,
            "cooldown_seconds": 8,
            "daily_usage_limit": None,
            "allowed_channel_ids": [],
            "blocked_channel_ids": [],
            "allowed_role_ids": [],
        }
        if not guild_id:
            return default_policy

        async with self.bot.db.cursor() as cursor:
            await cursor.execute(
                """
                SELECT enabled, cooldown_seconds, daily_usage_limit, allowed_channel_ids,
                       blocked_channel_ids, allowed_role_ids
                FROM chat_policies
                WHERE guild_id = ?
                """,
                (guild_id,),
            )
            row = await cursor.fetchone()

        if row is None:
            return default_policy

        enabled, cooldown_seconds, daily_usage_limit, allowed_channel_ids, blocked_channel_ids, allowed_role_ids = row
        return {
            "enabled": bool(enabled),
            "cooldown_seconds": (
                default_policy["cooldown_seconds"] if cooldown_seconds is None else int(cooldown_seconds)
            ),
            "daily_usage_limit": daily_usage_limit,
            "allowed_channel_ids": self._deserialize_ids(allowed_channel_ids),
            "blocked_channel_ids": self._deserialize_ids(blocked_channel_ids),
            "allowed_role_ids": self._deserialize_ids(allowed_role_ids),
        }

    async def update_policy(self, guild_id: int, **fields):
        async with self.bot.db.cursor() as cursor:
            await cursor.execute("INSERT OR IGNORE INTO chat_policies (guild_id) VALUES (?)", (guild_id,))
            for field, value in fields.items():
                await cursor.execute(f"UPDATE chat_policies SET {field} = ? WHERE guild_id = ?", (value, guild_id))
        await self.bot.db.commit()

    async def mutate_id_list(self, guild_id: int, field: str, value: int, add: bool):
        policy = await self.get_policy(guild_id)
        current = set(policy[field])
        if add:
            current.add(value)
        else:
            current.discard(value)
        await self.update_policy(guild_id, **{field: self._serialize_ids(list(current))})
        return sorted(current)

    async def get_usage_count(self, guild_id: int) -> int:
        usage_date = discord.utils.utcnow().date().isoformat()
        async with self.bot.db.cursor() as cursor:
            await cursor.execute(
                "SELECT usage_count FROM chat_usage WHERE guild_id = ? AND usage_date = ?",
                (guild_id, usage_date),
            )
            row = await cursor.fetchone()
        return row[0] if row else 0

    async def increment_usage(self, guild_id: int):
        usage_date = discord.utils.utcnow().date().isoformat()
        async with self.bot.db.cursor() as cursor:
            await cursor.execute(
                """
                INSERT INTO chat_usage (guild_id, usage_date, usage_count)
                VALUES (?, ?, 1)
                ON CONFLICT(guild_id, usage_date)
                DO UPDATE SET usage_count = usage_count + 1
                """,
                (guild_id, usage_date),
            )
        await self.bot.db.commit()

    async def validate_api_key(self, api_key: str) -> Tuple[bool, str]:
        headers = {"Authorization": f"Bearer {api_key}"}
        try:
            async with self.session.get(f"{self.api_base}/models", headers=headers) as response:
                if response.status == 200:
                    return True, "API key is valid."

                try:
                    error_data = await response.json()
                    error_message = error_data.get("error", {}).get("message", "Unknown API error.")
                except Exception:
                    error_message = "Unknown API error."
                return False, f"{response.status}: {error_message}"
        except Exception as error:
            return False, str(error)

    async def enforce_policy(self, interaction: discord.Interaction, policy: Dict[str, Any]) -> Optional[str]:
        if not interaction.guild_id:
            return None
        if not policy["enabled"]:
            return "AI chat is disabled in this server."
        if interaction.channel_id in policy["blocked_channel_ids"]:
            return "AI chat is disabled in this channel."
        if policy["allowed_channel_ids"] and interaction.channel_id not in policy["allowed_channel_ids"]:
            return "AI chat is only allowed in specific channels configured by the server admins."
        if policy["allowed_role_ids"]:
            member = interaction.user if isinstance(interaction.user, discord.Member) else None
            if member is None:
                return "AI chat is restricted to specific roles in this server."
            member_role_ids = {role.id for role in member.roles}
            if not member_role_ids.intersection(policy["allowed_role_ids"]):
                return "You do not have one of the roles required to use AI chat here."

        cooldown_seconds = max(int(policy["cooldown_seconds"]), 0)
        if cooldown_seconds > 0:
            cooldown_key = (interaction.guild_id, interaction.user.id)
            now = discord.utils.utcnow()
            last_used = self.chat_cooldowns.get(cooldown_key)
            if last_used and (now - last_used).total_seconds() < cooldown_seconds:
                remaining = cooldown_seconds - int((now - last_used).total_seconds())
                return f"You're on cooldown for this server. Try again in {remaining}s."

        usage_limit = policy["daily_usage_limit"]
        if usage_limit:
            usage_count = await self.get_usage_count(interaction.guild_id)
            if usage_count >= usage_limit:
                return "This server has reached its daily AI chat usage cap."

        return None

    def define_tools(self):
        return [
            {
                "type": "function",
                "function": {
                    "name": "google_search",
                    "description": "Get real-time information from the web for recent events or specific data.",
                    "parameters": {
                        "type": "object",
                        "properties": {"query": {"type": "string", "description": "The search query."}},
                        "required": ["query"],
                    },
                },
            }
        ]

    async def execute_google_search(self, query: str):
        url = "https://www.googleapis.com/customsearch/v1"
        params = {"key": self.google_api_key, "cx": self.google_cse_id, "q": query, "num": 5}
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    items = data.get("items", [])
                    snippets = [item.get("snippet", "") for item in items]
                    return json.dumps({"results": snippets}) if snippets else json.dumps({"error": "No results found."})

                error_data = await response.json()
                error_message = error_data.get("error", {}).get("message", "Unknown error.")
                return json.dumps({"error": f"Failed to fetch search results. Status: {response.status} - {error_message}"})
        except Exception as error:
            return json.dumps({"error": f"An error occurred during search: {error}"})

    async def model_autocomplete(self, interaction: discord.Interaction, current: str):
        current_lower = current.lower()
        return [
            app_commands.Choice(name=model, value=model)
            for model in self.allowed_models
            if current_lower in model.lower()
        ]

    def _channel_labels(self, guild: discord.Guild, ids: List[int]) -> str:
        if not ids:
            return "Not set"
        labels = []
        for channel_id in ids:
            channel = guild.get_channel(channel_id)
            labels.append(channel.mention if channel else f"`{channel_id}`")
        return ", ".join(labels)

    def _role_labels(self, guild: discord.Guild, ids: List[int]) -> str:
        if not ids:
            return "Not set"
        labels = []
        for role_id in ids:
            role = guild.get_role(role_id)
            labels.append(role.mention if role else f"`{role_id}`")
        return ", ".join(labels)

    def _truncate_field_value(self, value: str, limit: int = MAX_EMBED_FIELD_LENGTH) -> str:
        if len(value) <= limit:
            return value
        return f"{value[: limit - 1].rstrip()}…"

    def _trim_history(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if len(messages) <= MAX_CONVERSATION_HISTORY:
            return messages
        return messages[0:1] + messages[-(MAX_CONVERSATION_HISTORY - 1) :]

    def _prune_runtime_state(self) -> None:
        now = discord.utils.utcnow()
        expired_conversations = [
            key for key, last_used in self.conversation_last_used.items() if now - last_used > CONVERSATION_TTL
        ]
        for key in expired_conversations:
            self.conversation_last_used.pop(key, None)
            self.conversations.pop(key, None)

        expired_cooldowns = [
            key for key, last_used in self.chat_cooldowns.items() if now - last_used > COOLDOWN_RETENTION
        ]
        for key in expired_cooldowns:
            self.chat_cooldowns.pop(key, None)

    def _set_conversation_state(self, context_key: Tuple[Any, ...], messages: List[Dict[str, Any]]) -> None:
        if messages:
            self.conversations[context_key] = messages
            self.conversation_last_used[context_key] = discord.utils.utcnow()
            return
        self.conversations.pop(context_key, None)
        self.conversation_last_used.pop(context_key, None)

    chat_config = app_commands.Group(
        name="chat-config",
        description="Configure the AI chat settings for a server.",
        guild_only=True,
    )

    @chat_config.command(name="set-key", description="Set a custom OpenAI API key for this server.")
    @app_commands.describe(key="Your OpenAI API key. Use 'reset' to remove.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_key(self, interaction: discord.Interaction, key: str):
        if not self.allow_user_keys:
            await interaction.response.send_message("The bot owner has disabled custom API keys.", ephemeral=True)
            return
        if key.lower() == "reset":
            await self.set_guild_key(interaction.guild.id)
            await interaction.response.send_message("Server API key removed.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        valid, detail = await self.validate_api_key(key)
        if not valid:
            await interaction.followup.send(f"API key validation failed: {detail}", ephemeral=True)
            return
        await self.set_guild_key(interaction.guild.id, key)
        await interaction.followup.send("Server API key validated and saved.", ephemeral=True)

    @chat_config.command(name="set-persona", description="Set a custom personality for the AI.")
    @app_commands.describe(persona="A description of the AI's personality. Use 'reset' to remove.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_persona(self, interaction: discord.Interaction, persona: str):
        if len(persona) > MAX_PERSONA_LENGTH:
            await interaction.response.send_message("Persona is too long (max 500 chars).", ephemeral=True)
            return
        if persona.lower() == "reset":
            await self.set_guild_persona(interaction.guild.id)
            await interaction.response.send_message("AI persona reset to default.", ephemeral=True)
            return
        await self.set_guild_persona(interaction.guild.id, persona)
        await interaction.response.send_message("AI persona updated.", ephemeral=True)

    @chat_config.command(name="set-enabled", description="Enable or disable AI chat in this server.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_enabled(self, interaction: discord.Interaction, enabled: bool):
        await self.update_policy(interaction.guild.id, enabled=int(enabled))
        state = "enabled" if enabled else "disabled"
        await interaction.response.send_message(f"AI chat is now {state} for this server.", ephemeral=True)

    @chat_config.command(name="set-cooldown", description="Set the per-user chat cooldown for this server.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(seconds="Cooldown in seconds. Use 0 to disable.")
    async def set_cooldown(self, interaction: discord.Interaction, seconds: app_commands.Range[int, 0, 600]):
        await self.update_policy(interaction.guild.id, cooldown_seconds=int(seconds))
        await interaction.response.send_message(f"Chat cooldown set to {seconds}s.", ephemeral=True)

    @chat_config.command(name="set-usage-cap", description="Set the per-day chat usage cap for this server.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(limit="Maximum successful chat requests per day. Use 0 to remove the cap.")
    async def set_usage_cap(self, interaction: discord.Interaction, limit: app_commands.Range[int, 0, 5000]):
        value = None if limit == 0 else int(limit)
        await self.update_policy(interaction.guild.id, daily_usage_limit=value)
        label = "removed" if value is None else str(value)
        await interaction.response.send_message(f"Daily usage cap set to {label}.", ephemeral=True)

    @chat_config.command(name="allow-channel", description="Allow AI chat only in a specific channel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def allow_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        channels = await self.mutate_id_list(interaction.guild.id, "allowed_channel_ids", channel.id, add=True)
        await interaction.response.send_message(
            f"Allowed channels updated. {len(channels)} channel(s) are now allowlisted.",
            ephemeral=True,
        )

    @chat_config.command(name="block-channel", description="Block AI chat in a specific channel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def block_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        channels = await self.mutate_id_list(interaction.guild.id, "blocked_channel_ids", channel.id, add=True)
        await interaction.response.send_message(
            f"Blocked channels updated. {len(channels)} channel(s) are now blocked.",
            ephemeral=True,
        )

    @chat_config.command(name="clear-channel-rules", description="Clear channel allow/block rules for AI chat.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def clear_channel_rules(self, interaction: discord.Interaction):
        await self.update_policy(interaction.guild.id, allowed_channel_ids=None, blocked_channel_ids=None)
        await interaction.response.send_message("Channel rules cleared.", ephemeral=True)

    @chat_config.command(name="allow-role", description="Restrict AI chat to members with a specific role.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def allow_role(self, interaction: discord.Interaction, role: discord.Role):
        roles = await self.mutate_id_list(interaction.guild.id, "allowed_role_ids", role.id, add=True)
        await interaction.response.send_message(
            f"Allowed roles updated. {len(roles)} role(s) are now allowlisted.",
            ephemeral=True,
        )

    @chat_config.command(name="remove-role", description="Remove a role from the AI chat allowlist.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def remove_role(self, interaction: discord.Interaction, role: discord.Role):
        roles = await self.mutate_id_list(interaction.guild.id, "allowed_role_ids", role.id, add=False)
        await interaction.response.send_message(
            f"Allowed roles updated. {len(roles)} role(s) remain allowlisted.",
            ephemeral=True,
        )

    @chat_config.command(name="clear-role-rules", description="Remove all role-based AI chat restrictions.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def clear_role_rules(self, interaction: discord.Interaction):
        await self.update_policy(interaction.guild.id, allowed_role_ids=None)
        await interaction.response.send_message("Role restrictions cleared.", ephemeral=True)

    @chat_config.command(name="view", description="View the current chat configuration.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def view_config(self, interaction: discord.Interaction):
        self._prune_runtime_state()
        guild_config = await self.get_guild_config(interaction.guild.id) or (None, None)
        guild_key, guild_persona = guild_config
        policy = await self.get_policy(interaction.guild.id)
        usage_count = await self.get_usage_count(interaction.guild.id)

        embed = discord.Embed(title=f"Chat Configuration for {interaction.guild.name}", color=discord.Color.blue())
        key_status = "Not configured"
        if guild_key:
            key_status = f"`{guild_key[:5]}...{guild_key[-4:]}` (custom)"
        elif self.default_api_key:
            key_status = "Using bot default key"

        embed.add_field(name="Server API Key", value=key_status, inline=False)
        embed.add_field(
            name="AI Persona",
            value=self._truncate_field_value(guild_persona or DEFAULT_PERSONA),
            inline=False,
        )
        embed.add_field(name="Web Search", value="Enabled" if self.enable_web_search else "Disabled", inline=False)
        embed.add_field(name="API Base URL", value=self._truncate_field_value(f"`{self.api_base}`"), inline=False)
        embed.add_field(
            name="Allowed Models",
            value=self._truncate_field_value(", ".join(f"`{model}`" for model in self.allowed_models)),
            inline=False,
        )
        embed.add_field(name="Chat Enabled", value="Yes" if policy["enabled"] else "No", inline=True)
        embed.add_field(name="Cooldown", value=f"{policy['cooldown_seconds']}s", inline=True)
        embed.add_field(
            name="Daily Usage Cap",
            value="Not set" if policy["daily_usage_limit"] is None else f"{usage_count}/{policy['daily_usage_limit']}",
            inline=True,
        )
        embed.add_field(
            name="Allowed Channels",
            value=self._truncate_field_value(self._channel_labels(interaction.guild, policy["allowed_channel_ids"])),
            inline=False,
        )
        embed.add_field(
            name="Blocked Channels",
            value=self._truncate_field_value(self._channel_labels(interaction.guild, policy["blocked_channel_ids"])),
            inline=False,
        )
        embed.add_field(
            name="Allowed Roles",
            value=self._truncate_field_value(self._role_labels(interaction.guild, policy["allowed_role_ids"])),
            inline=False,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @chat_config.command(name="test", description="Validate the effective API key for this server.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def test_config(self, interaction: discord.Interaction):
        guild_config = await self.get_guild_config(interaction.guild.id) or (None, None)
        guild_key, _ = guild_config
        api_key = guild_key or self.default_api_key
        if not api_key:
            await interaction.response.send_message("No API key is configured to test.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        valid, detail = await self.validate_api_key(api_key)
        if valid:
            await interaction.followup.send("API key validation succeeded.", ephemeral=True)
        else:
            await interaction.followup.send(f"API key validation failed: {detail}", ephemeral=True)

    @chat_config.command(name="models", description="Show the configured default and allowed chat models.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def list_models(self, interaction: discord.Interaction):
        embed = discord.Embed(title="Chat Models", color=discord.Color.blurple())
        embed.add_field(name="Default Model", value=f"`{self.default_model}`", inline=False)
        embed.add_field(
            name="Allowed Models",
            value=self._truncate_field_value("\n".join(f"`{model}`" for model in self.allowed_models)),
            inline=False,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="chat", description="Chat with the AI, with optional live web search.")
    @app_commands.describe(
        prompt="What to talk about?",
        model="Choose a specific AI model.",
        search_web="Set to true to allow the AI to search the web for current info.",
    )
    @app_commands.autocomplete(model=model_autocomplete)
    async def chat(self, interaction: discord.Interaction, prompt: str, model: Optional[str] = None, search_web: bool = False):
        self._prune_runtime_state()
        guild_id = interaction.guild.id if interaction.guild else None
        chosen_model = model or self.default_model
        policy = await self.get_policy(guild_id)

        if chosen_model not in self.allowed_models:
            await interaction.response.send_message("That model is not allowed for this bot.", ephemeral=True)
            return
        if search_web and not self.enable_web_search:
            await interaction.response.send_message(
                "Web search is not configured by the bot owner.",
                ephemeral=True,
            )
            return

        if interaction.guild_id:
            policy_error = await self.enforce_policy(interaction, policy)
            if policy_error:
                await interaction.response.send_message(policy_error, ephemeral=True)
                return

        guild_config = await self.get_guild_config(guild_id) or (None, None)
        api_key, persona = guild_config
        api_key = api_key or self.default_api_key
        if not api_key:
            await interaction.response.send_message(
                "AI chat is not configured. An admin must set an API key.",
                ephemeral=True,
            )
            return

        await interaction.response.defer()
        context_key = self._context_key(interaction)
        existing_messages = list(self.conversations.get(context_key, []))
        if not existing_messages:
            existing_messages = [{"role": "system", "content": persona or DEFAULT_PERSONA}]

        original_messages = list(existing_messages)
        working_messages = list(existing_messages)
        working_messages.append({"role": "user", "content": prompt})
        self._set_conversation_state(context_key, working_messages)

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"model": chosen_model, "messages": working_messages}
        if self.enable_web_search and search_web:
            payload["tools"] = self.define_tools()
            payload["tool_choice"] = "auto"

        final_answer = None
        try:
            async with self.session.post(f"{self.api_base}/chat/completions", headers=headers, json=payload) as response:
                if response.status != 200:
                    error_data = await response.json()
                    error_message = error_data.get("error", {}).get("message", "An unknown API error occurred.")
                    self._set_conversation_state(context_key, original_messages)
                    await interaction.followup.send(f"API Error: {response.status} - {error_message}", ephemeral=True)
                    return

                data = await response.json()
                ai_message = data["choices"][0]["message"]

                if ai_message.get("tool_calls") and self.enable_web_search and search_web:
                    thinking_message = await interaction.followup.send("Searching the web...", wait=True)
                    working_messages.append(ai_message)
                    self._set_conversation_state(context_key, working_messages)
                    tool_call = ai_message["tool_calls"][0]
                    function_args = json.loads(tool_call["function"]["arguments"])
                    query = function_args.get("query", "")
                    tool_response = await self.execute_google_search(query)

                    working_messages.append(
                        {
                            "tool_call_id": tool_call["id"],
                            "role": "tool",
                            "name": tool_call["function"]["name"],
                            "content": tool_response,
                        }
                    )
                    self._set_conversation_state(context_key, working_messages)

                    final_payload = {"model": chosen_model, "messages": working_messages}
                    async with self.session.post(
                        f"{self.api_base}/chat/completions",
                        headers=headers,
                        json=final_payload,
                    ) as final_response:
                        if final_response.status != 200:
                            self._set_conversation_state(context_key, original_messages)
                            await thinking_message.edit(content="The model failed after web search. Please try again.")
                            return
                        final_data = await final_response.json()
                        final_answer = final_data["choices"][0]["message"]["content"]
                        await thinking_message.edit(
                            content=self._truncate_field_value(final_answer, MAX_EMBED_DESCRIPTION_LENGTH)
                        )
                else:
                    final_answer = ai_message.get("content") or "The model returned an empty response."
                    await interaction.edit_original_response(content=final_answer)

                working_messages.append({"role": "assistant", "content": final_answer})
                self._set_conversation_state(context_key, self._trim_history(working_messages))

                if interaction.guild_id:
                    cooldown_key = (interaction.guild_id, interaction.user.id)
                    self.chat_cooldowns[cooldown_key] = discord.utils.utcnow()
                    await self.increment_usage(interaction.guild_id)

        except Exception as error:
            logger.exception("Chat processing error: %s", error)
            self._set_conversation_state(context_key, original_messages)
            await interaction.followup.send("An unexpected error occurred. Please try again later.", ephemeral=True)

    @app_commands.command(name="chat-reset", description="Reset your conversation history with the AI.")
    async def chat_reset(self, interaction: discord.Interaction):
        self._prune_runtime_state()
        context_key = self._context_key(interaction)
        self._set_conversation_state(context_key, [])
        await interaction.response.send_message("Your conversation history has been reset.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Chat(bot))
