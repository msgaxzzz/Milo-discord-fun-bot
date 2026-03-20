import json
import re
from datetime import timedelta
from typing import Dict, List, Optional

import discord
from discord import app_commands
from discord.ext import commands


INVITE_RE = re.compile(r"(discord\.gg/|discord\.com/invite/)", re.IGNORECASE)
LINK_RE = re.compile(r"https?://", re.IGNORECASE)


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.loop.create_task(self.setup_database())

    async def setup_database(self):
        async with self.bot.db.cursor() as cursor:
            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS automod_settings (
                    guild_id INTEGER PRIMARY KEY,
                    filter_invites INTEGER NOT NULL DEFAULT 0,
                    filter_links INTEGER NOT NULL DEFAULT 0,
                    bad_words TEXT,
                    whitelist_channel_ids TEXT,
                    action TEXT NOT NULL DEFAULT 'delete'
                )
                """
            )
            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS moderation_warnings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    moderator_id INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            await cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_moderation_warnings_guild_user_created_at
                ON moderation_warnings(guild_id, user_id, created_at DESC)
                """
            )
        await self.bot.db.commit()

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

    async def get_automod_settings(self, guild_id: int) -> Dict[str, object]:
        async with self.bot.db.cursor() as cursor:
            await cursor.execute(
                """
                SELECT filter_invites, filter_links, bad_words, whitelist_channel_ids, action
                FROM automod_settings
                WHERE guild_id = ?
                """,
                (guild_id,),
            )
            row = await cursor.fetchone()

        if row is None:
            return {
                "filter_invites": False,
                "filter_links": False,
                "bad_words": [],
                "whitelist_channel_ids": [],
                "action": "delete",
            }

        filter_invites, filter_links, bad_words, whitelist_channel_ids, action = row
        return {
            "filter_invites": bool(filter_invites),
            "filter_links": bool(filter_links),
            "bad_words": [word for word in (bad_words or "").split(",") if word],
            "whitelist_channel_ids": self._deserialize_ids(whitelist_channel_ids),
            "action": action or "delete",
        }

    async def update_automod(self, guild_id: int, **fields):
        async with self.bot.db.cursor() as cursor:
            await cursor.execute("INSERT OR IGNORE INTO automod_settings (guild_id) VALUES (?)", (guild_id,))
            for field, value in fields.items():
                await cursor.execute(f"UPDATE automod_settings SET {field} = ? WHERE guild_id = ?", (value, guild_id))
        await self.bot.db.commit()

    async def mutate_whitelist(self, guild_id: int, channel_id: int, add: bool) -> List[int]:
        settings = await self.get_automod_settings(guild_id)
        current = set(settings["whitelist_channel_ids"])
        if add:
            current.add(channel_id)
        else:
            current.discard(channel_id)
        await self.update_automod(guild_id, whitelist_channel_ids=self._serialize_ids(list(current)))
        return sorted(current)

    async def add_warning(self, guild_id: int, user_id: int, moderator_id: int, reason: str) -> int:
        async with self.bot.db.cursor() as cursor:
            await cursor.execute(
                """
                INSERT INTO moderation_warnings (guild_id, user_id, moderator_id, reason, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (guild_id, user_id, moderator_id, reason, discord.utils.utcnow().isoformat()),
            )
            warning_id = cursor.lastrowid
        await self.bot.db.commit()
        return warning_id

    async def log_action(self, guild: discord.Guild, title: str, description: str, color: discord.Color):
        community = self.bot.get_cog("Community")
        if community:
            await community._log_to_modlog(guild, title, description, color)

    automod = app_commands.Group(name="automod", description="Configure basic automod rules.", guild_only=True)

    @automod.command(name="view", description="View the current automod settings.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def automod_view(self, interaction: discord.Interaction):
        settings = await self.get_automod_settings(interaction.guild_id)
        whitelist = ", ".join(f"<#{channel_id}>" for channel_id in settings["whitelist_channel_ids"]) or "Not set"
        bad_words = ", ".join(f"`{word}`" for word in settings["bad_words"]) or "Not set"
        embed = discord.Embed(title="Automod Settings", color=discord.Color.orange())
        embed.add_field(name="Invite Filter", value="On" if settings["filter_invites"] else "Off", inline=True)
        embed.add_field(name="Link Filter", value="On" if settings["filter_links"] else "Off", inline=True)
        embed.add_field(name="Action", value=settings["action"], inline=True)
        embed.add_field(name="Bad Words", value=bad_words, inline=False)
        embed.add_field(name="Whitelisted Channels", value=whitelist, inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @automod.command(name="toggle-invites", description="Turn invite filtering on or off.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def automod_toggle_invites(self, interaction: discord.Interaction, enabled: bool):
        await self.update_automod(interaction.guild_id, filter_invites=int(enabled))
        await interaction.response.send_message(f"Invite filtering is now {'on' if enabled else 'off'}.", ephemeral=True)

    @automod.command(name="toggle-links", description="Turn link filtering on or off.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def automod_toggle_links(self, interaction: discord.Interaction, enabled: bool):
        await self.update_automod(interaction.guild_id, filter_links=int(enabled))
        await interaction.response.send_message(f"Link filtering is now {'on' if enabled else 'off'}.", ephemeral=True)

    @automod.command(name="set-action", description="Choose what automod should do when it triggers.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.choices(
        action=[
            app_commands.Choice(name="Delete", value="delete"),
            app_commands.Choice(name="Warn", value="warn"),
            app_commands.Choice(name="Timeout", value="timeout"),
        ]
    )
    async def automod_set_action(self, interaction: discord.Interaction, action: app_commands.Choice[str]):
        await self.update_automod(interaction.guild_id, action=action.value)
        await interaction.response.send_message(f"Automod action set to `{action.value}`.", ephemeral=True)

    @automod.command(name="set-bad-words", description="Set a comma-separated list of blocked words.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def automod_set_bad_words(self, interaction: discord.Interaction, words: str):
        normalized = ",".join(sorted({word.strip().lower() for word in words.split(",") if word.strip()}))
        await self.update_automod(interaction.guild_id, bad_words=normalized or None)
        count = 0 if not normalized else len(normalized.split(","))
        await interaction.response.send_message(f"Stored {count} blocked word(s).", ephemeral=True)

    @automod.command(name="clear-bad-words", description="Clear all blocked words.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def automod_clear_bad_words(self, interaction: discord.Interaction):
        await self.update_automod(interaction.guild_id, bad_words=None)
        await interaction.response.send_message("Blocked words cleared.", ephemeral=True)

    @automod.command(name="whitelist-channel", description="Exclude a channel from automod checks.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def automod_whitelist_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        channels = await self.mutate_whitelist(interaction.guild_id, channel.id, add=True)
        await interaction.response.send_message(
            f"Automod whitelist updated. {len(channels)} channel(s) are exempt now.",
            ephemeral=True,
        )

    @automod.command(name="remove-whitelist-channel", description="Remove a channel from the automod whitelist.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def automod_remove_whitelist_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        channels = await self.mutate_whitelist(interaction.guild_id, channel.id, add=False)
        await interaction.response.send_message(
            f"Automod whitelist updated. {len(channels)} channel(s) remain exempt.",
            ephemeral=True,
        )

    @app_commands.command(name="warn", description="Warn a member and log it.")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_messages=True)
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        warning_id = await self.add_warning(interaction.guild_id, member.id, interaction.user.id, reason)
        await self.log_action(
            interaction.guild,
            "Member Warned",
            f"{member.mention} was warned by {interaction.user.mention}.\nReason: {reason}\nWarning ID: `{warning_id}`",
            discord.Color.orange(),
        )
        await interaction.response.send_message(
            f"Warning `{warning_id}` recorded for {member.mention}.",
            ephemeral=True,
        )

    @app_commands.command(name="warnings", description="View warning history for a member.")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_messages=True)
    async def warnings(self, interaction: discord.Interaction, member: discord.Member):
        async with self.bot.db.cursor() as cursor:
            await cursor.execute(
                """
                SELECT id, moderator_id, reason, created_at
                FROM moderation_warnings
                WHERE guild_id = ? AND user_id = ?
                ORDER BY created_at DESC
                LIMIT 10
                """,
                (interaction.guild_id, member.id),
            )
            rows = await cursor.fetchall()

        if not rows:
            await interaction.response.send_message(f"{member.mention} has no warnings in this server.", ephemeral=True)
            return

        lines = []
        for warning_id, moderator_id, reason, created_at in rows:
            moderator = interaction.guild.get_member(moderator_id)
            moderator_label = moderator.mention if moderator else f"`{moderator_id}`"
            lines.append(
                f"`{warning_id}` • {discord.utils.format_dt(discord.utils.parse_time(created_at), style='R')} • {moderator_label}\n{reason}"
            )

        embed = discord.Embed(title=f"Warnings for {member}", description="\n\n".join(lines), color=discord.Color.orange())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="clear-warning", description="Delete a single warning by id.")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clear_warning(self, interaction: discord.Interaction, warning_id: int):
        async with self.bot.db.cursor() as cursor:
            await cursor.execute(
                "DELETE FROM moderation_warnings WHERE id = ? AND guild_id = ?",
                (warning_id, interaction.guild_id),
            )
            deleted = cursor.rowcount
        await self.bot.db.commit()
        if not deleted:
            await interaction.response.send_message("Warning not found.", ephemeral=True)
            return

        await self.log_action(
            interaction.guild,
            "Warning Cleared",
            f"{interaction.user.mention} removed warning `{warning_id}`.",
            discord.Color.green(),
        )
        await interaction.response.send_message(f"Warning `{warning_id}` removed.", ephemeral=True)

    async def handle_violation(self, message: discord.Message, reason: str, action: str):
        deleted = False
        try:
            await message.delete()
            deleted = True
        except (discord.Forbidden, discord.HTTPException):
            deleted = False

        details = [f"User: {message.author.mention}", f"Channel: {message.channel.mention}", f"Reason: {reason}"]
        if not deleted:
            details.append("Action skipped because the original message could not be deleted")
            await self.log_action(message.guild, "Automod Triggered", "\n".join(details), discord.Color.red())
            return

        if action == "warn":
            warning_id = await self.add_warning(message.guild.id, message.author.id, self.bot.user.id, f"Automod: {reason}")
            details.append(f"Warning ID: `{warning_id}`")
            try:
                await message.channel.send(
                    f"{message.author.mention}, your message was removed by automod: {reason}",
                    delete_after=10,
                )
            except (discord.Forbidden, discord.HTTPException):
                pass
        elif action == "timeout" and isinstance(message.author, discord.Member):
            try:
                await message.author.timeout(discord.utils.utcnow() + timedelta(minutes=10), reason=f"Automod: {reason}")
                details.append("Action: timeout")
            except (discord.Forbidden, discord.HTTPException):
                details.append("Action: timeout failed, message removed only")
                try:
                    await message.channel.send(
                        f"{message.author.mention}, automod tried to time you out but lacked permission. Message removed.",
                        delete_after=10,
                    )
                except (discord.Forbidden, discord.HTTPException):
                    pass

        await self.log_action(message.guild, "Automod Triggered", "\n".join(details), discord.Color.red())

    @commands.Cog.listener("on_message")
    async def automod_listener(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return
        if not isinstance(message.author, discord.Member):
            return
        if not isinstance(message.channel, (discord.TextChannel, discord.Thread)):
            return
        if message.author.guild_permissions.manage_messages:
            return

        settings = await self.get_automod_settings(message.guild.id)
        whitelisted = settings["whitelist_channel_ids"]
        parent_id = getattr(message.channel, "parent_id", None)
        if message.channel.id in whitelisted or (parent_id and parent_id in whitelisted):
            return

        lowered = message.content.lower()
        violation = None
        if settings["filter_invites"] and INVITE_RE.search(message.content):
            violation = "Discord invite links are not allowed."
        elif settings["filter_links"] and LINK_RE.search(message.content):
            violation = "Links are not allowed."
        else:
            for word in settings["bad_words"]:
                if not word:
                    continue
                pattern = re.compile(rf"(?<!\w){re.escape(word)}(?!\w)", re.IGNORECASE)
                if pattern.search(lowered):
                    violation = f"Blocked word detected: `{word}`"
                    break

        if violation:
            await self.handle_violation(message, violation, settings["action"])


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
