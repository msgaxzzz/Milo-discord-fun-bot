import platform
import re
import sys
from datetime import timedelta
from typing import Optional, Union

import discord
from discord import app_commands
from discord.ext import commands, tasks


REMINDER_LIMIT_SECONDS = 30 * 24 * 60 * 60
REMINDER_POLL_SECONDS = 30


def parse_duration_spec(value: str) -> Optional[int]:
    match = re.fullmatch(r"(\d+)([smhd])", value.lower())
    if not match:
        return None
    quantity, unit = match.groups()
    return int(quantity) * {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit]


class Utility(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        if not hasattr(bot, "start_time"):
            self.bot.start_time = discord.utils.utcnow()
        self.reminder_loop.start()

    def cog_unload(self):
        self.reminder_loop.cancel()

    async def setup_database(self):
        async with self.bot.db.cursor() as cursor:
            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    channel_id INTEGER,
                    guild_id INTEGER,
                    remind_at TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    recurring_seconds INTEGER,
                    delivery_failures INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS afk_statuses (
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    set_at TEXT NOT NULL,
                    PRIMARY KEY (guild_id, user_id)
                )
                """
            )
            await cursor.execute("PRAGMA table_info(reminders)")
            reminder_columns = [row[1] for row in await cursor.fetchall()]
            if "recurring_seconds" not in reminder_columns:
                await cursor.execute("ALTER TABLE reminders ADD COLUMN recurring_seconds INTEGER")
            if "delivery_failures" not in reminder_columns:
                await cursor.execute("ALTER TABLE reminders ADD COLUMN delivery_failures INTEGER NOT NULL DEFAULT 0")
        await self.bot.db.commit()

    async def get_afk_status(self, guild_id: int, user_id: int):
        async with self.bot.db.cursor() as cursor:
            await cursor.execute(
                "SELECT reason, set_at FROM afk_statuses WHERE guild_id = ? AND user_id = ?",
                (guild_id, user_id),
            )
            return await cursor.fetchone()

    async def set_afk_status(self, guild_id: int, user_id: int, reason: str):
        set_at = discord.utils.utcnow().isoformat()
        async with self.bot.db.cursor() as cursor:
            await cursor.execute(
                """
                INSERT INTO afk_statuses (guild_id, user_id, reason, set_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(guild_id, user_id)
                DO UPDATE SET reason = excluded.reason, set_at = excluded.set_at
                """,
                (guild_id, user_id, reason, set_at),
            )
        await self.bot.db.commit()

    async def clear_afk_status(self, guild_id: int, user_id: int):
        async with self.bot.db.cursor() as cursor:
            await cursor.execute(
                "DELETE FROM afk_statuses WHERE guild_id = ? AND user_id = ?",
                (guild_id, user_id),
            )
        await self.bot.db.commit()

    async def list_user_reminders(self, user_id: int):
        async with self.bot.db.cursor() as cursor:
            await cursor.execute(
                """
                SELECT id, guild_id, channel_id, remind_at, reason, recurring_seconds, delivery_failures
                FROM reminders
                WHERE user_id = ?
                ORDER BY remind_at ASC
                """,
                (user_id,),
            )
            return await cursor.fetchall()

    async def create_reminder(
        self,
        user_id: int,
        channel_id: Optional[int],
        guild_id: Optional[int],
        remind_at,
        reason: str,
        recurring_seconds: Optional[int] = None,
    ) -> int:
        async with self.bot.db.cursor() as cursor:
            await cursor.execute(
                """
                INSERT INTO reminders (user_id, channel_id, guild_id, remind_at, reason, recurring_seconds)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, channel_id, guild_id, remind_at.isoformat(), reason, recurring_seconds),
            )
            reminder_id = cursor.lastrowid
        await self.bot.db.commit()
        return reminder_id

    help_group = app_commands.Group(name="help", description="Get help with the bot's commands.")
    reminders_group = app_commands.Group(name="reminders", description="Manage your active reminders.")

    @app_commands.command(name="ping", description="Checks the bot's latency.")
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    async def ping(self, interaction: discord.Interaction):
        latency = self.bot.latency * 1000
        await interaction.response.send_message(f"Pong! Latency: {latency:.2f}ms")

    @app_commands.command(name="ping_raw", description="Checks the bot's detailed latency (Websocket & REST).")
    @app_commands.checks.cooldown(1, 10, key=lambda i: i.user.id)
    async def ping_raw(self, interaction: discord.Interaction):
        ws_latency = self.bot.latency * 1000
        rest_latency = round(self.bot.http.latency * 1000, 2) if self.bot.http.latency else "N/A"

        embed = discord.Embed(title="🏓 Pong!", color=discord.Color.blue())
        embed.add_field(name="WebSocket Latency", value=f"{ws_latency:.2f}ms", inline=False)
        embed.add_field(name="REST API Latency", value=f"{rest_latency}ms", inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="memberinfo", description="Displays information about a member.")
    @app_commands.guild_only()
    @app_commands.describe(member="The member to get info about.")
    @app_commands.checks.cooldown(1, 10, key=lambda i: i.user.id)
    async def memberinfo(self, interaction: discord.Interaction, member: discord.Member = None):
        target_member = member or interaction.user

        embed = discord.Embed(color=target_member.color, timestamp=discord.utils.utcnow())
        embed.set_author(name=f"User Info - {target_member}")
        if target_member.display_avatar:
            embed.set_thumbnail(url=target_member.display_avatar.url)
        embed.set_footer(
            text=f"Requested by {interaction.user.name}",
            icon_url=interaction.user.avatar.url if interaction.user.avatar else None,
        )

        embed.add_field(name="ID", value=target_member.id, inline=False)
        embed.add_field(name="Display Name", value=target_member.display_name, inline=True)
        embed.add_field(name="Bot?", value=target_member.bot, inline=True)
        embed.add_field(name="Created At", value=discord.utils.format_dt(target_member.created_at, style="F"), inline=False)

        if target_member.joined_at:
            embed.add_field(name="Joined At", value=discord.utils.format_dt(target_member.joined_at, style="F"), inline=False)

        roles = [role.mention for role in reversed(target_member.roles[1:])]
        roles_str = ", ".join(roles) if roles else "No roles"
        embed.add_field(
            name=f"Roles [{len(roles)}]",
            value=roles_str if len(roles_str) < 1024 else f"{len(roles)} roles (too many to display)",
            inline=False,
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="clear", description="Deletes a specified number of messages.")
    @app_commands.guild_only()
    @app_commands.describe(amount="The number of messages to delete (1-100).")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clear(self, interaction: discord.Interaction, amount: app_commands.Range[int, 1, 100]):
        me = interaction.guild.me or interaction.guild.get_member(self.bot.user.id)
        if me is None or not interaction.channel.permissions_for(me).manage_messages:
            await interaction.response.send_message(
                "I don't have permission to manage messages in this channel.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"Successfully deleted {len(deleted)} messages.", ephemeral=True)

    @app_commands.command(name="serverinfo", description="Displays detailed information about the server.")
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 10, key=lambda i: i.guild_id)
    async def serverinfo(self, interaction: discord.Interaction):
        guild = interaction.guild
        embed = discord.Embed(
            title=f"Server Info: {guild.name}", color=discord.Color.blue(), timestamp=discord.utils.utcnow()
        )

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        owner_text = guild.owner.mention if guild.owner else f"ID: {guild.owner_id}"
        embed.add_field(name="Owner", value=owner_text, inline=True)
        embed.add_field(name="ID", value=guild.id, inline=True)
        embed.add_field(name="Created At", value=discord.utils.format_dt(guild.created_at, "F"), inline=False)

        total_members = guild.member_count if guild.member_count is not None else len(guild.members)
        bots = sum(1 for member in guild.members if member.bot) if guild.members else 0
        humans = total_members - bots
        embed.add_field(name="Members", value=f"Total: {total_members}\nHumans: {humans}\nBots: {bots}", inline=True)

        channels_total = len(guild.text_channels) + len(guild.voice_channels)
        channels_total += len(guild.stage_channels) if hasattr(guild, "stage_channels") else 0
        channels_total += len(guild.forum_channels) if hasattr(guild, "forum_channels") else 0
        embed.add_field(
            name="Channels",
            value=(
                f"Total: {channels_total}\nText: {len(guild.text_channels)}\nVoice: {len(guild.voice_channels)}\n"
                f"Stage: {len(guild.stage_channels) if hasattr(guild, 'stage_channels') else 0}\n"
                f"Forum: {len(guild.forum_channels) if hasattr(guild, 'forum_channels') else 0}"
            ),
            inline=True,
        )
        embed.add_field(name="Roles", value=len(guild.roles), inline=True)

        if guild.features:
            embed.add_field(
                name="Features",
                value=", ".join(feature.replace("_", " ").title() for feature in guild.features),
                inline=False,
            )

        embed.set_footer(
            text=f"Requested by {interaction.user.name}",
            icon_url=interaction.user.avatar.url if interaction.user.avatar else None,
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="botinfo", description="Displays information and stats about the bot.")
    @app_commands.checks.cooldown(1, 10, key=lambda i: i.user.id)
    async def botinfo(self, interaction: discord.Interaction):
        delta_uptime = discord.utils.utcnow() - self.bot.start_time
        days = delta_uptime.days
        hours, remainder = divmod(int(delta_uptime.total_seconds() % 86400), 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"

        embed = discord.Embed(
            title=f"{self.bot.user.name} Stats", color=discord.Color.purple(), timestamp=discord.utils.utcnow()
        )
        if self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)

        embed.add_field(name="Developer", value="Sentinel Team", inline=True)
        embed.add_field(name="Servers", value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(name="Total Users", value=str(len(self.bot.users)), inline=True)
        embed.add_field(name="Python Version", value=sys.version.split(" ")[0], inline=True)
        embed.add_field(name="discord.py Version", value=discord.__version__, inline=True)
        embed.add_field(name="Uptime", value=uptime_str, inline=True)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="uptime", description="Shows how long the bot has been online, and server info.")
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    async def uptime(self, interaction: discord.Interaction):
        delta_uptime = discord.utils.utcnow() - self.bot.start_time
        days = delta_uptime.days
        hours, remainder = divmod(int(delta_uptime.total_seconds() % 86400), 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"

        embed = discord.Embed(title="Bot Uptime & System Info", color=discord.Color.teal())
        embed.add_field(name="Bot Uptime", value=f"**{uptime_str}**", inline=False)
        embed.add_field(
            name="Operating System",
            value=f"{platform.system()} {platform.release()} ({platform.version()})",
            inline=False,
        )
        embed.add_field(name="Architecture", value=platform.machine(), inline=False)

        await interaction.response.send_message(embed=embed)

    def _iter_commands(self):
        stack = list(self.bot.tree.get_commands())
        while stack:
            command = stack.pop(0)
            yield command
            if isinstance(command, app_commands.Group):
                stack[0:0] = command.commands

    def _get_full_command_name(self, command: Union[app_commands.Command, app_commands.Group]) -> str:
        parts = [command.name]
        parent = command.parent
        while parent is not None:
            parts.append(parent.name)
            parent = parent.parent
        return " ".join(reversed(parts))

    def _command_support_label(self, command: Union[app_commands.Command, app_commands.Group]) -> str:
        checks = getattr(command, "checks", [])
        if any(getattr(check, "__qualname__", "").endswith("guild_only.<locals>.predicate") for check in checks):
            return "Servers only"
        return "Servers and DMs"

    def _command_permission_label(self, command: Union[app_commands.Command, app_commands.Group]) -> Optional[str]:
        checks = getattr(command, "checks", [])
        for check in checks:
            qualname = getattr(check, "__qualname__", "")
            if "has_permissions" in qualname:
                closure = getattr(check, "__closure__", None) or []
                for cell in closure:
                    if isinstance(cell.cell_contents, dict) and cell.cell_contents:
                        return ", ".join(name.replace("_", " ").title() for name in cell.cell_contents.keys())
        return None

    async def command_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        current_lower = current.lower()
        return [
            app_commands.Choice(name=self._get_full_command_name(command), value=self._get_full_command_name(command))
            for command in self._iter_commands()
            if current_lower in self._get_full_command_name(command).lower()
        ][:25]

    @help_group.command(name="all", description="Lists all available commands.")
    async def help_all(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Bot Commands",
            description="Full command list grouped by cog.",
            color=discord.Color.blurple(),
        )

        for cog_name in sorted(self.bot.cogs.keys()):
            cog = self.bot.get_cog(cog_name)
            commands_list = [
                f"`/{self._get_full_command_name(command)}`"
                for command in cog.get_app_commands()
                for command in [command]
            ]
            expanded = []
            for command in cog.get_app_commands():
                if isinstance(command, app_commands.Group):
                    expanded.extend(f"`/{self._get_full_command_name(subcommand)}`" for subcommand in self._iter_group_commands(command))
                else:
                    expanded.append(f"`/{self._get_full_command_name(command)}`")

            if expanded:
                embed.add_field(name=cog_name, value=" ".join(expanded[:25]), inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    def _iter_group_commands(self, group: app_commands.Group):
        stack = list(group.commands)
        while stack:
            command = stack.pop(0)
            yield command
            if isinstance(command, app_commands.Group):
                stack[0:0] = command.commands

    @help_group.command(name="command", description="Get detailed help for a specific command.")
    @app_commands.autocomplete(command=command_autocomplete)
    @app_commands.describe(command="The command you need help with.")
    async def help_command(self, interaction: discord.Interaction, command: str):
        target = None
        for item in self._iter_commands():
            if self._get_full_command_name(item) == command:
                target = item
                break

        if target is None:
            await interaction.response.send_message(f"Command `{command}` not found.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"Help: `/{self._get_full_command_name(target)}`",
            description=target.description or "No description provided.",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Availability", value=self._command_support_label(target), inline=False)

        permission_label = self._command_permission_label(target)
        if permission_label:
            embed.add_field(name="Required Permissions", value=permission_label, inline=False)

        if isinstance(target, app_commands.Group):
            subcommands = [f"`/{self._get_full_command_name(item)}`" for item in self._iter_group_commands(target)]
            if subcommands:
                embed.add_field(name="Subcommands", value="\n".join(subcommands), inline=False)
        elif target.parameters:
            params = [f"`{param.name}`: {param.description or 'No description'}" for param in target.parameters]
            embed.add_field(name="Parameters", value="\n".join(params), inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="remindme", description="Sets a reminder for you.")
    @app_commands.describe(time="When to remind (e.g., 10s, 5m, 2h, 1d).", reason="What to be reminded of.")
    async def remindme(self, interaction: discord.Interaction, time: str, reason: str):
        seconds = parse_duration_spec(time)
        if seconds is None:
            await interaction.response.send_message(
                "Invalid time format. Use s, m, h, or d (e.g., `10s`, `5m`, `2h`, `1d`).",
                ephemeral=True,
            )
            return

        if seconds > REMINDER_LIMIT_SECONDS:
            await interaction.response.send_message("You cannot set a reminder for more than 30 days.", ephemeral=True)
            return

        remind_at = discord.utils.utcnow() + timedelta(seconds=seconds)
        reminder_id = await self.create_reminder(
            interaction.user.id,
            interaction.channel_id,
            interaction.guild_id,
            remind_at,
            reason,
        )

        await interaction.response.send_message(
            f"Reminder `{reminder_id}` created for **{time.lower()}** from now: `{reason}`",
            ephemeral=True,
        )

    @reminders_group.command(name="recurring", description="Create a recurring reminder.")
    @app_commands.describe(interval="How often to repeat, like 30m, 2h, or 1d.", reason="What to be reminded of.")
    async def reminders_recurring(self, interaction: discord.Interaction, interval: str, reason: str):
        seconds = parse_duration_spec(interval)
        if seconds is None:
            await interaction.response.send_message(
                "Invalid interval format. Use s, m, h, or d (e.g., `30m`, `2h`, `1d`).",
                ephemeral=True,
            )
            return
        if seconds > REMINDER_LIMIT_SECONDS:
            await interaction.response.send_message("Recurring interval cannot be more than 30 days.", ephemeral=True)
            return

        remind_at = discord.utils.utcnow() + timedelta(seconds=seconds)
        reminder_id = await self.create_reminder(
            interaction.user.id,
            interaction.channel_id,
            interaction.guild_id,
            remind_at,
            reason,
            recurring_seconds=seconds,
        )
        await interaction.response.send_message(
            f"Recurring reminder `{reminder_id}` created every **{interval.lower()}**: `{reason}`",
            ephemeral=True,
        )

    @reminders_group.command(name="list", description="List your active reminders.")
    async def reminders_list(self, interaction: discord.Interaction):
        reminders = await self.list_user_reminders(interaction.user.id)
        if not reminders:
            await interaction.response.send_message("You do not have any active reminders.", ephemeral=True)
            return

        lines = []
        for reminder_id, guild_id, channel_id, remind_at, reason, recurring_seconds, delivery_failures in reminders[:20]:
            if guild_id is None:
                scope = "DM"
            else:
                guild = self.bot.get_guild(guild_id)
                scope = guild.name if guild else f"Guild `{guild_id}`"
            channel_text = f", channel <#{channel_id}>" if channel_id else ""
            recurring_text = "" if not recurring_seconds else f" • repeats every `{int(recurring_seconds)}s`"
            failure_text = "" if not delivery_failures else f" • delivery failures: {delivery_failures}"
            lines.append(
                f"`{reminder_id}` • {discord.utils.format_dt(discord.utils.parse_time(remind_at), style='R')} • {scope}{channel_text}{recurring_text}{failure_text}\n{reason}"
            )

        embed = discord.Embed(title="Active Reminders", description="\n\n".join(lines), color=discord.Color.gold())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @reminders_group.command(name="cancel", description="Cancel one reminder by id.")
    @app_commands.describe(reminder_id="The reminder id shown by /reminders list.")
    async def reminders_cancel(self, interaction: discord.Interaction, reminder_id: int):
        async with self.bot.db.cursor() as cursor:
            await cursor.execute(
                "DELETE FROM reminders WHERE id = ? AND user_id = ?",
                (reminder_id, interaction.user.id),
            )
            deleted = cursor.rowcount
        await self.bot.db.commit()

        if deleted:
            await interaction.response.send_message(f"Reminder `{reminder_id}` canceled.", ephemeral=True)
        else:
            await interaction.response.send_message("Reminder not found.", ephemeral=True)

    @reminders_group.command(name="snooze", description="Push one reminder further into the future.")
    @app_commands.describe(reminder_id="The reminder id shown by /reminders list.", delay="How much longer, like 10m or 2h.")
    async def reminders_snooze(self, interaction: discord.Interaction, reminder_id: int, delay: str):
        seconds = parse_duration_spec(delay)
        if seconds is None:
            await interaction.response.send_message(
                "Invalid delay format. Use s, m, h, or d (e.g., `10m`, `2h`).",
                ephemeral=True,
            )
            return
        new_time = discord.utils.utcnow() + timedelta(seconds=seconds)
        async with self.bot.db.cursor() as cursor:
            await cursor.execute(
                """
                UPDATE reminders
                SET remind_at = ?, delivery_failures = 0
                WHERE id = ? AND user_id = ?
                """,
                (new_time.isoformat(), reminder_id, interaction.user.id),
            )
            updated = cursor.rowcount
        await self.bot.db.commit()
        if updated:
            await interaction.response.send_message(
                f"Reminder `{reminder_id}` snoozed for `{delay.lower()}`.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message("Reminder not found.", ephemeral=True)

    @reminders_group.command(name="clear", description="Clear all of your reminders.")
    async def reminders_clear(self, interaction: discord.Interaction):
        async with self.bot.db.cursor() as cursor:
            await cursor.execute("DELETE FROM reminders WHERE user_id = ?", (interaction.user.id,))
            deleted = cursor.rowcount
        await self.bot.db.commit()
        await interaction.response.send_message(f"Cleared {deleted} reminder(s).", ephemeral=True)

    @app_commands.command(name="afk", description="Set or update your AFK status in this server.")
    @app_commands.guild_only()
    @app_commands.describe(reason="The reason for your AFK status.")
    async def afk(self, interaction: discord.Interaction, reason: str = "AFK"):
        await self.set_afk_status(interaction.guild_id, interaction.user.id, reason)
        await interaction.response.send_message(f"{interaction.user.mention} is now AFK: **{reason}**")

    @app_commands.command(name="afk-clear", description="Clear your AFK status in this server.")
    @app_commands.guild_only()
    async def afk_clear(self, interaction: discord.Interaction):
        await self.clear_afk_status(interaction.guild_id, interaction.user.id)
        await interaction.response.send_message("Your AFK status has been cleared.", ephemeral=True)

    @commands.Cog.listener("on_message")
    async def afk_message_listener(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        own_status = await self.get_afk_status(message.guild.id, message.author.id)
        if own_status:
            await self.clear_afk_status(message.guild.id, message.author.id)
            await message.channel.send(f"Welcome back {message.author.mention}! Your AFK status has been removed.")

        notified = []
        for mentioned_user in message.mentions:
            if mentioned_user.bot:
                continue
            status = await self.get_afk_status(message.guild.id, mentioned_user.id)
            if not status:
                continue

            reason, set_at = status
            time_afk = discord.utils.utcnow() - discord.utils.parse_time(set_at)
            days = time_afk.days
            hours, remainder = divmod(int(time_afk.total_seconds() % 86400), 3600)
            minutes, seconds = divmod(remainder, 60)
            time_str = f"{days}d {hours}h {minutes}m {seconds}s"
            notified.append(f"{mentioned_user.display_name} is AFK: **{reason}** (for {time_str})")

        if notified:
            await message.channel.send("\n".join(notified))

    @tasks.loop(seconds=REMINDER_POLL_SECONDS)
    async def reminder_loop(self):
        now = discord.utils.utcnow().isoformat()
        async with self.bot.db.cursor() as cursor:
            await cursor.execute(
                """
                SELECT id, user_id, channel_id, reason, remind_at, recurring_seconds
                FROM reminders
                WHERE remind_at <= ?
                ORDER BY remind_at ASC
                """,
                (now,),
            )
            reminders = await cursor.fetchall()

        if not reminders:
            return

        for reminder_id, user_id, channel_id, reason, remind_at, recurring_seconds in reminders:
            user = self.bot.get_user(user_id)
            if user is None:
                try:
                    user = await self.bot.fetch_user(user_id)
                except discord.HTTPException:
                    user = None

            delivered = False
            if user is not None:
                try:
                    await user.send(f"**Reminder:** {reason}")
                    delivered = True
                except discord.Forbidden:
                    delivered = False

            if not delivered and channel_id is not None:
                channel = self.bot.get_channel(channel_id)
                if channel is None:
                    try:
                        channel = await self.bot.fetch_channel(channel_id)
                    except discord.HTTPException:
                        channel = None

                if channel is not None:
                    try:
                        mention = user.mention if user else f"<@{user_id}>"
                        await channel.send(f"Hey {mention}, you had a reminder: {reason}")
                        delivered = True
                    except discord.HTTPException:
                        delivered = False

            async with self.bot.db.cursor() as cursor:
                if delivered and recurring_seconds:
                    next_time = discord.utils.parse_time(remind_at)
                    while next_time <= discord.utils.utcnow():
                        next_time += timedelta(seconds=recurring_seconds)
                    await cursor.execute(
                        """
                        UPDATE reminders
                        SET remind_at = ?, delivery_failures = 0
                        WHERE id = ?
                        """,
                        (next_time.isoformat(), reminder_id),
                    )
                elif delivered:
                    await cursor.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
                else:
                    await cursor.execute(
                        """
                        UPDATE reminders
                        SET delivery_failures = delivery_failures + 1
                        WHERE id = ?
                        """,
                        (reminder_id,),
                    )
        await self.bot.db.commit()

    @reminder_loop.before_loop
    async def before_reminder_loop(self):
        await self.bot.wait_until_ready()
        await self.setup_database()


async def setup(bot: commands.Bot):
    await bot.add_cog(Utility(bot))
