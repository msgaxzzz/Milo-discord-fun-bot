import string
from datetime import timedelta
from typing import Dict, Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks


DEFAULT_WELCOME_MESSAGE = "Welcome to {guild}, {member.mention}!"
DEFAULT_GOODBYE_MESSAGE = "{member} left {guild}."
SCHEDULE_POLL_SECONDS = 30
SCHEDULE_BATCH_SIZE = 20
TEMPLATE_FIELDS = {"member", "member.mention", "guild"}
MAX_SCHEDULE_DELIVERY_FAILURES = 5
MAX_ANNOUNCEMENT_LENGTH = 4000
SCHEDULE_RETRY_BASE_SECONDS = 300
SCHEDULE_RETRY_MAX_SECONDS = 21600


def parse_duration(value: str) -> Optional[int]:
    if not value:
        return None
    amount = value[:-1]
    unit = value[-1].lower()
    if not amount.isdigit() or unit not in {"m", "h", "d"}:
        return None
    return int(amount) * {"m": 60, "h": 3600, "d": 86400}[unit]


class Community(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.schedule_loop.start()

    def cog_unload(self):
        self.schedule_loop.cancel()

    async def setup_database(self):
        async with self.bot.db.cursor() as cursor:
            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS guild_settings (
                    guild_id INTEGER PRIMARY KEY,
                    welcome_channel_id INTEGER,
                    goodbye_channel_id INTEGER,
                    announcement_channel_id INTEGER,
                    modlog_channel_id INTEGER,
                    welcome_message TEXT,
                    goodbye_message TEXT
                )
                """
            )
            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS scheduled_announcements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    author_id INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    send_at TEXT NOT NULL,
                    interval_seconds INTEGER
                )
                """
            )
            await cursor.execute("PRAGMA table_info(scheduled_announcements)")
            announcement_columns = [row[1] for row in await cursor.fetchall()]
            if "delivery_failures" not in announcement_columns:
                await cursor.execute(
                    "ALTER TABLE scheduled_announcements ADD COLUMN delivery_failures INTEGER NOT NULL DEFAULT 0"
                )
            if "disabled" not in announcement_columns:
                await cursor.execute(
                    "ALTER TABLE scheduled_announcements ADD COLUMN disabled INTEGER NOT NULL DEFAULT 0"
                )
            if "last_error" not in announcement_columns:
                await cursor.execute("ALTER TABLE scheduled_announcements ADD COLUMN last_error TEXT")
            await cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_scheduled_announcements_due ON scheduled_announcements(disabled, send_at)"
            )
            await cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_scheduled_announcements_guild_send_at ON scheduled_announcements(guild_id, send_at)"
            )
        await self.bot.db.commit()

    async def get_settings(self, guild_id: int) -> Dict[str, Optional[int]]:
        async with self.bot.db.cursor() as cursor:
            await cursor.execute(
                """
                SELECT guild_id, welcome_channel_id, goodbye_channel_id, announcement_channel_id,
                       modlog_channel_id, welcome_message, goodbye_message
                FROM guild_settings
                WHERE guild_id = ?
                """,
                (guild_id,),
            )
            row = await cursor.fetchone()

        if row is None:
            return {
                "guild_id": guild_id,
                "welcome_channel_id": None,
                "goodbye_channel_id": None,
                "announcement_channel_id": None,
                "modlog_channel_id": None,
                "welcome_message": None,
                "goodbye_message": None,
            }

        keys = [
            "guild_id",
            "welcome_channel_id",
            "goodbye_channel_id",
            "announcement_channel_id",
            "modlog_channel_id",
            "welcome_message",
            "goodbye_message",
        ]
        return dict(zip(keys, row))

    async def update_setting(self, guild_id: int, field: str, value):
        async with self.bot.db.cursor() as cursor:
            await cursor.execute("INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)", (guild_id,))
            await cursor.execute(f"UPDATE guild_settings SET {field} = ? WHERE guild_id = ?", (value, guild_id))
        await self.bot.db.commit()

    def validate_template(self, template: str) -> Optional[str]:
        formatter = string.Formatter()
        try:
            for _, field_name, _, _ in formatter.parse(template):
                if field_name and field_name not in TEMPLATE_FIELDS:
                    return (
                        f"Unsupported placeholder `{field_name}`. "
                        "Use only `{member}`, `{member.mention}`, and `{guild}`."
                    )
        except ValueError as error:
            return f"Invalid template syntax: {error}"
        return None

    def render_template(self, template: Optional[str], member: discord.abc.User, guild: discord.Guild, default: str) -> str:
        text = template or default
        return text.format(member=member, guild=guild.name)

    def try_render_template(
        self, template: Optional[str], member: discord.abc.User, guild: discord.Guild, default: str
    ) -> tuple[Optional[str], Optional[str]]:
        try:
            return self.render_template(template, member, guild, default), None
        except Exception as error:
            return None, str(error)

    def schedule_retry_delay(self, failures: int) -> timedelta:
        seconds = min(SCHEDULE_RETRY_BASE_SECONDS * (2 ** max(failures - 1, 0)), SCHEDULE_RETRY_MAX_SECONDS)
        return timedelta(seconds=seconds)

    async def _resolve_channel(self, channel_id: Optional[int]):
        if channel_id is None:
            return None
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(channel_id)
            except discord.HTTPException:
                return None
        return channel

    async def _send_to_channel(
        self,
        channel_id: Optional[int],
        embed: Optional[discord.Embed] = None,
        content: Optional[str] = None,
    ) -> bool:
        channel = await self._resolve_channel(channel_id)
        if channel is None:
            return False

        try:
            if content is not None:
                await channel.send(content)
            elif embed is not None:
                await channel.send(embed=embed)
            return True
        except (discord.Forbidden, discord.HTTPException):
            return False

    async def _log_to_modlog(self, guild: discord.Guild, title: str, description: str, color: discord.Color):
        settings = await self.get_settings(guild.id)
        channel_id = settings["modlog_channel_id"]
        if channel_id is None:
            return

        embed = discord.Embed(title=title, description=description, color=color, timestamp=discord.utils.utcnow())
        await self._send_to_channel(channel_id, embed=embed)

    def _channel_value(self, channel_id: Optional[int]) -> str:
        return f"<#{channel_id}>" if channel_id else "Not set"

    async def _schedule_announcement(
        self,
        guild_id: int,
        channel_id: int,
        author_id: int,
        message: str,
        send_at,
        interval_seconds: Optional[int] = None,
    ) -> int:
        async with self.bot.db.cursor() as cursor:
            await cursor.execute(
                """
                INSERT INTO scheduled_announcements (guild_id, channel_id, author_id, message, send_at, interval_seconds)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (guild_id, channel_id, author_id, message, send_at.isoformat(), interval_seconds),
            )
            announcement_id = cursor.lastrowid
        await self.bot.db.commit()
        return announcement_id

    server_config = app_commands.Group(
        name="server-config",
        description="Configure community features for this server.",
        guild_only=True,
    )
    announcements = app_commands.Group(
        name="announcements",
        description="Manage scheduled announcements for this server.",
        guild_only=True,
    )

    @server_config.command(name="view", description="View the current server community settings.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def view(self, interaction: discord.Interaction):
        settings = await self.get_settings(interaction.guild_id)
        embed = discord.Embed(title=f"Server Config: {interaction.guild.name}", color=discord.Color.green())
        embed.add_field(name="Welcome Channel", value=self._channel_value(settings["welcome_channel_id"]), inline=False)
        embed.add_field(name="Goodbye Channel", value=self._channel_value(settings["goodbye_channel_id"]), inline=False)
        embed.add_field(
            name="Announcement Channel",
            value=self._channel_value(settings["announcement_channel_id"]),
            inline=False,
        )
        embed.add_field(name="Mod Log Channel", value=self._channel_value(settings["modlog_channel_id"]), inline=False)
        embed.add_field(
            name="Welcome Message",
            value=settings["welcome_message"] or DEFAULT_WELCOME_MESSAGE,
            inline=False,
        )
        embed.add_field(
            name="Goodbye Message",
            value=settings["goodbye_message"] or DEFAULT_GOODBYE_MESSAGE,
            inline=False,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @server_config.command(name="set-welcome-channel", description="Set the welcome channel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_welcome_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await self.update_setting(interaction.guild_id, "welcome_channel_id", channel.id)
        await interaction.response.send_message(f"Welcome channel set to {channel.mention}.", ephemeral=True)

    @server_config.command(name="set-goodbye-channel", description="Set the goodbye channel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_goodbye_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await self.update_setting(interaction.guild_id, "goodbye_channel_id", channel.id)
        await interaction.response.send_message(f"Goodbye channel set to {channel.mention}.", ephemeral=True)

    @server_config.command(name="set-announcement-channel", description="Set the announcement channel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_announcement_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await self.update_setting(interaction.guild_id, "announcement_channel_id", channel.id)
        await interaction.response.send_message(f"Announcement channel set to {channel.mention}.", ephemeral=True)

    @server_config.command(name="set-modlog-channel", description="Set the moderation log channel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_modlog_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await self.update_setting(interaction.guild_id, "modlog_channel_id", channel.id)
        await interaction.response.send_message(f"Mod log channel set to {channel.mention}.", ephemeral=True)

    @server_config.command(name="set-welcome-message", description="Set the welcome message template.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(message="Use {member}, {member.mention}, and {guild}. Type reset to clear.")
    async def set_welcome_message(self, interaction: discord.Interaction, message: str):
        if message.lower() != "reset":
            error = self.validate_template(message)
            if error:
                await interaction.response.send_message(error, ephemeral=True)
                return
        value = None if message.lower() == "reset" else message
        await self.update_setting(interaction.guild_id, "welcome_message", value)
        await interaction.response.send_message("Welcome message updated.", ephemeral=True)

    @server_config.command(name="set-goodbye-message", description="Set the goodbye message template.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(message="Use {member}, {member.mention}, and {guild}. Type reset to clear.")
    async def set_goodbye_message(self, interaction: discord.Interaction, message: str):
        if message.lower() != "reset":
            error = self.validate_template(message)
            if error:
                await interaction.response.send_message(error, ephemeral=True)
                return
        value = None if message.lower() == "reset" else message
        await self.update_setting(interaction.guild_id, "goodbye_message", value)
        await interaction.response.send_message("Goodbye message updated.", ephemeral=True)

    @server_config.command(name="preview-welcome", description="Preview the welcome message template.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def preview_welcome(self, interaction: discord.Interaction):
        settings = await self.get_settings(interaction.guild_id)
        content, error = self.try_render_template(
            settings["welcome_message"], interaction.user, interaction.guild, DEFAULT_WELCOME_MESSAGE
        )
        if error:
            await interaction.response.send_message(
                "The saved welcome template is invalid. Reset or update it before using previews.",
                ephemeral=True,
            )
            return
        await interaction.response.send_message(content, ephemeral=True)

    @server_config.command(name="preview-goodbye", description="Preview the goodbye message template.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def preview_goodbye(self, interaction: discord.Interaction):
        settings = await self.get_settings(interaction.guild_id)
        content, error = self.try_render_template(
            settings["goodbye_message"], interaction.user, interaction.guild, DEFAULT_GOODBYE_MESSAGE
        )
        if error:
            await interaction.response.send_message(
                "The saved goodbye template is invalid. Reset or update it before using previews.",
                ephemeral=True,
            )
            return
        await interaction.response.send_message(content, ephemeral=True)

    @server_config.command(name="reset-message", description="Reset one message template to its default.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.choices(
        target=[
            app_commands.Choice(name="Welcome", value="welcome_message"),
            app_commands.Choice(name="Goodbye", value="goodbye_message"),
        ]
    )
    async def reset_message(self, interaction: discord.Interaction, target: app_commands.Choice[str]):
        await self.update_setting(interaction.guild_id, target.value, None)
        await interaction.response.send_message(f"{target.name} message reset.", ephemeral=True)

    @server_config.command(name="reset-channel", description="Reset one configured channel slot.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.choices(
        target=[
            app_commands.Choice(name="Welcome", value="welcome_channel_id"),
            app_commands.Choice(name="Goodbye", value="goodbye_channel_id"),
            app_commands.Choice(name="Announcement", value="announcement_channel_id"),
            app_commands.Choice(name="Mod Log", value="modlog_channel_id"),
        ]
    )
    async def reset_channel(self, interaction: discord.Interaction, target: app_commands.Choice[str]):
        await self.update_setting(interaction.guild_id, target.value, None)
        await interaction.response.send_message(f"{target.name} channel reset.", ephemeral=True)

    @app_commands.command(name="announce", description="Send an announcement to the configured announcement channel.")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(message="Announcement content.")
    async def announce(self, interaction: discord.Interaction, message: str):
        if len(message) > MAX_ANNOUNCEMENT_LENGTH:
            await interaction.response.send_message(
                f"Announcement content is too long ({len(message)} chars). Maximum is {MAX_ANNOUNCEMENT_LENGTH}.",
                ephemeral=True,
            )
            return

        settings = await self.get_settings(interaction.guild_id)
        target_channel_id = settings["announcement_channel_id"] or interaction.channel_id
        channel = await self._resolve_channel(target_channel_id)
        if channel is None:
            await interaction.response.send_message(
                "The configured announcement channel no longer exists. Set a new one or use this command in another channel.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(description=message, color=discord.Color.blurple())
        embed.set_author(name=f"Announcement from {interaction.guild.name}")
        embed.set_footer(text=f"Sent by {interaction.user.display_name}")
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            await interaction.response.send_message(
                "I do not have permission to send messages in the configured announcement channel.",
                ephemeral=True,
            )
            return
        except discord.HTTPException:
            await interaction.response.send_message(
                "I could not send the announcement right now. Please try again later.",
                ephemeral=True,
            )
            return

        if target_channel_id == interaction.channel_id:
            await interaction.response.send_message("Announcement sent in this channel.", ephemeral=True)
        else:
            await interaction.response.send_message(f"Announcement sent to {channel.mention}.", ephemeral=True)

    @announcements.command(name="schedule", description="Schedule a future announcement.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(
        when="When to send it, like 10m, 2h, or 1d.",
        message="Announcement content.",
        repeat="Optional repeat interval like 1d. Leave empty for one-time.",
        channel="Optional target channel. Defaults to the configured announcement channel or current channel.",
    )
    async def schedule(
        self,
        interaction: discord.Interaction,
        when: str,
        message: str,
        repeat: Optional[str] = None,
        channel: Optional[discord.TextChannel] = None,
    ):
        delay_seconds = parse_duration(when)
        if delay_seconds is None:
            await interaction.response.send_message("Invalid `when` value. Use formats like `10m`, `2h`, or `1d`.", ephemeral=True)
            return
        if len(message) > MAX_ANNOUNCEMENT_LENGTH:
            await interaction.response.send_message(
                f"Announcement content is too long ({len(message)} chars). Maximum is {MAX_ANNOUNCEMENT_LENGTH}.",
                ephemeral=True,
            )
            return
        interval_seconds = parse_duration(repeat) if repeat else None
        if repeat and interval_seconds is None:
            await interaction.response.send_message("Invalid repeat interval. Use formats like `1h` or `1d`.", ephemeral=True)
            return

        settings = await self.get_settings(interaction.guild_id)
        target_channel_id = channel.id if channel else settings["announcement_channel_id"] or interaction.channel_id
        target_channel = await self._resolve_channel(target_channel_id)
        if target_channel is None:
            await interaction.response.send_message("The target announcement channel is unavailable.", ephemeral=True)
            return

        send_at = discord.utils.utcnow() + timedelta(seconds=delay_seconds)
        announcement_id = await self._schedule_announcement(
            interaction.guild_id,
            target_channel_id,
            interaction.user.id,
            message,
            send_at,
            interval_seconds=interval_seconds,
        )
        schedule_text = discord.utils.format_dt(send_at, style="F")
        repeat_text = "" if interval_seconds is None else f" Repeats every `{repeat}`."
        await interaction.response.send_message(
            f"Scheduled announcement `{announcement_id}` for {schedule_text} in {target_channel.mention}.{repeat_text}",
            ephemeral=True,
        )

    @announcements.command(name="list", description="List scheduled announcements for this server.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def list_scheduled(self, interaction: discord.Interaction):
        async with self.bot.db.cursor() as cursor:
            await cursor.execute(
                """
                SELECT id, channel_id, send_at, interval_seconds, message, delivery_failures, disabled, last_error
                FROM scheduled_announcements
                WHERE guild_id = ?
                ORDER BY send_at ASC
                LIMIT 20
                """,
                (interaction.guild_id,),
            )
            rows = await cursor.fetchall()

        if not rows:
            await interaction.response.send_message("No scheduled announcements for this server.", ephemeral=True)
            return

        lines = []
        for announcement_id, channel_id, send_at, interval_seconds, message, delivery_failures, disabled, last_error in rows:
            schedule = discord.utils.format_dt(discord.utils.parse_time(send_at), style="R")
            repeat_text = "" if interval_seconds is None else f" every `{interval_seconds}s`"
            status_text = " • paused" if disabled else ""
            failure_text = "" if not delivery_failures else f" • failures: {delivery_failures}"
            error_text = "" if not last_error else f"\nError: {last_error[:100]}"
            lines.append(f"`{announcement_id}` • <#{channel_id}> • {schedule}{repeat_text}{status_text}{failure_text}\n{message[:120]}{error_text}")

        embed = discord.Embed(title="Scheduled Announcements", description="\n\n".join(lines), color=discord.Color.blurple())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @announcements.command(name="diagnose", description="Show details and error info for a scheduled announcement.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(announcement_id="The announcement id from /announcements list.")
    async def diagnose_scheduled(self, interaction: discord.Interaction, announcement_id: int):
        async with self.bot.db.cursor() as cursor:
            await cursor.execute(
                """
                SELECT id, channel_id, author_id, message, send_at, interval_seconds,
                       delivery_failures, disabled, last_error
                FROM scheduled_announcements
                WHERE id = ? AND guild_id = ?
                """,
                (announcement_id, interaction.guild_id),
            )
            row = await cursor.fetchone()

        if not row:
            await interaction.response.send_message("Scheduled announcement not found.", ephemeral=True)
            return

        ann_id, channel_id, author_id, message, send_at, interval_seconds, failures, disabled, last_error = row
        embed = discord.Embed(
            title=f"Announcement `{ann_id}` Details",
            color=discord.Color.orange() if disabled else discord.Color.blurple(),
        )
        embed.add_field(name="Channel", value=f"<#{channel_id}>", inline=True)
        embed.add_field(name="Scheduled By", value=f"<@{author_id}>", inline=True)
        embed.add_field(name="Next Send", value=discord.utils.format_dt(discord.utils.parse_time(send_at), style="F"), inline=False)
        if interval_seconds:
            embed.add_field(name="Repeat Interval", value=f"{interval_seconds}s", inline=True)
        embed.add_field(name="Status", value="Paused (too many failures)" if disabled else "Active", inline=True)
        embed.add_field(name="Delivery Failures", value=str(failures), inline=True)
        if last_error:
            embed.add_field(name="Last Error", value=last_error[:1024], inline=False)
        embed.add_field(name="Content", value=message[:1024], inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @announcements.command(name="cancel", description="Cancel a scheduled announcement.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def cancel_scheduled(self, interaction: discord.Interaction, announcement_id: int):
        async with self.bot.db.cursor() as cursor:
            await cursor.execute(
                "DELETE FROM scheduled_announcements WHERE id = ? AND guild_id = ?",
                (announcement_id, interaction.guild_id),
            )
            deleted = cursor.rowcount
        await self.bot.db.commit()
        if deleted:
            await interaction.response.send_message(f"Scheduled announcement `{announcement_id}` canceled.", ephemeral=True)
        else:
            await interaction.response.send_message("Scheduled announcement not found.", ephemeral=True)

    @tasks.loop(seconds=SCHEDULE_POLL_SECONDS)
    async def schedule_loop(self):
        now = discord.utils.utcnow().isoformat()
        async with self.bot.db.cursor() as cursor:
            await cursor.execute(
                """
                SELECT id, guild_id, channel_id, author_id, message, send_at, interval_seconds, delivery_failures
                FROM scheduled_announcements
                WHERE disabled = 0 AND send_at <= ?
                ORDER BY send_at ASC
                LIMIT ?
                """,
                (now, SCHEDULE_BATCH_SIZE),
            )
            rows = await cursor.fetchall()

        for announcement_id, guild_id, channel_id, author_id, message, send_at, interval_seconds, delivery_failures in rows:
            guild = self.bot.get_guild(guild_id)
            channel = await self._resolve_channel(channel_id)
            delivered = False
            failure_reason = None
            if guild is not None and channel is not None:
                embed = discord.Embed(description=message, color=discord.Color.blurple())
                embed.set_author(name=f"Scheduled announcement from {guild.name}")
                user = guild.get_member(author_id)
                footer_name = user.display_name if user else str(author_id)
                embed.set_footer(text=f"Scheduled by {footer_name}")
                try:
                    await channel.send(embed=embed)
                    delivered = True
                except (discord.Forbidden, discord.HTTPException):
                    delivered = False
                    failure_reason = "failed to send the scheduled announcement in the configured channel"
            elif guild is None:
                failure_reason = "the target guild is unavailable to the bot"
            else:
                failure_reason = "the configured announcement channel is unavailable"

            async with self.bot.db.cursor() as cursor:
                if delivered and interval_seconds:
                    next_time = discord.utils.parse_time(send_at)
                    while next_time <= discord.utils.utcnow():
                        next_time += timedelta(seconds=interval_seconds)
                    await cursor.execute(
                        """
                        UPDATE scheduled_announcements
                        SET send_at = ?, delivery_failures = 0, disabled = 0, last_error = NULL
                        WHERE id = ?
                        """,
                        (next_time.isoformat(), announcement_id),
                    )
                elif delivered:
                    await cursor.execute("DELETE FROM scheduled_announcements WHERE id = ?", (announcement_id,))
                else:
                    next_failures = delivery_failures + 1
                    if next_failures >= MAX_SCHEDULE_DELIVERY_FAILURES:
                        await cursor.execute(
                            """
                            UPDATE scheduled_announcements
                            SET delivery_failures = ?, disabled = 1, last_error = ?
                            WHERE id = ?
                            """,
                            (next_failures, failure_reason, announcement_id),
                        )
                        if guild is not None:
                            await self._log_to_modlog(
                                guild,
                                "Scheduled Announcement Disabled",
                                f"Announcement `{announcement_id}` was paused after repeated delivery failures.\nReason: {failure_reason}",
                                discord.Color.orange(),
                            )
                    else:
                        retry_at = discord.utils.utcnow() + self.schedule_retry_delay(next_failures)
                        await cursor.execute(
                            """
                            UPDATE scheduled_announcements
                            SET send_at = ?, delivery_failures = ?, last_error = ?
                            WHERE id = ?
                            """,
                            (retry_at.isoformat(), next_failures, failure_reason, announcement_id),
                        )
            await self.bot.db.commit()

    @schedule_loop.before_loop
    async def before_schedule_loop(self):
        await self.bot.wait_until_ready()
        await self.setup_database()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        settings = await self.get_settings(member.guild.id)
        if settings["welcome_channel_id"]:
            try:
                text = self.render_template(settings["welcome_message"], member, member.guild, DEFAULT_WELCOME_MESSAGE)
                await self._send_to_channel(settings["welcome_channel_id"], content=text)
            except Exception:
                await self._log_to_modlog(
                    member.guild,
                    "Welcome Message Error",
                    "A welcome template could not be rendered. Reset or update the welcome message template.",
                    discord.Color.red(),
                )

        await self._log_to_modlog(
            member.guild,
            "Member Joined",
            f"{member.mention} joined the server.",
            discord.Color.green(),
        )

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        settings = await self.get_settings(member.guild.id)
        if settings["goodbye_channel_id"]:
            try:
                text = self.render_template(settings["goodbye_message"], member, member.guild, DEFAULT_GOODBYE_MESSAGE)
                await self._send_to_channel(settings["goodbye_channel_id"], content=text)
            except Exception:
                await self._log_to_modlog(
                    member.guild,
                    "Goodbye Message Error",
                    "A goodbye template could not be rendered. Reset or update the goodbye message template.",
                    discord.Color.red(),
                )

        await self._log_to_modlog(
            member.guild,
            "Member Left",
            f"{member} left the server.",
            discord.Color.orange(),
        )

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.guild is None or message.author.bot:
            return

        content = message.content.strip()
        if not content:
            content = "[no text content]"
        elif len(content) > 500:
            content = f"{content[:497]}..."

        await self._log_to_modlog(
            message.guild,
            "Message Deleted",
            f"Author: {message.author.mention}\nChannel: {message.channel.mention}\nContent: {content}",
            discord.Color.red(),
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Community(bot))
