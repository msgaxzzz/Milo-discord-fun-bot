import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional


DEFAULT_WELCOME_MESSAGE = "Welcome to {guild}, {member.mention}!"
DEFAULT_GOODBYE_MESSAGE = "{member} left {guild}."


class Community(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.loop.create_task(self.setup_database())

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
        await self.bot.db.commit()

    async def get_settings(self, guild_id: int) -> dict:
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

    def _format_message(self, template: Optional[str], member: discord.abc.User, guild: discord.Guild) -> str:
        text = template or DEFAULT_WELCOME_MESSAGE
        return text.format(member=member, guild=guild.name)

    async def _send_to_channel(
        self,
        channel_id: Optional[int],
        embed: Optional[discord.Embed] = None,
        content: Optional[str] = None,
    ):
        if channel_id is None:
            return

        channel = self.bot.get_channel(channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(channel_id)
            except discord.HTTPException:
                return

        if content is not None:
            await channel.send(content)
        elif embed is not None:
            await channel.send(embed=embed)

    server_config = app_commands.Group(
        name="server-config",
        description="Configure community features for this server.",
        guild_only=True,
    )

    @server_config.command(name="view", description="View the current server community settings.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def view(self, interaction: discord.Interaction):
        settings = await self.get_settings(interaction.guild_id)
        embed = discord.Embed(title=f"Server Config: {interaction.guild.name}", color=discord.Color.green())

        def channel_value(channel_id: Optional[int]) -> str:
            return f"<#{channel_id}>" if channel_id else "Not set"

        embed.add_field(name="Welcome Channel", value=channel_value(settings["welcome_channel_id"]), inline=False)
        embed.add_field(name="Goodbye Channel", value=channel_value(settings["goodbye_channel_id"]), inline=False)
        embed.add_field(
            name="Announcement Channel", value=channel_value(settings["announcement_channel_id"]), inline=False
        )
        embed.add_field(name="Mod Log Channel", value=channel_value(settings["modlog_channel_id"]), inline=False)
        embed.add_field(
            name="Welcome Message", value=settings["welcome_message"] or DEFAULT_WELCOME_MESSAGE, inline=False
        )
        embed.add_field(
            name="Goodbye Message", value=settings["goodbye_message"] or DEFAULT_GOODBYE_MESSAGE, inline=False
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @server_config.command(name="set-welcome-channel", description="Set the welcome channel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(channel="Use an empty mention reset command instead if you want to clear it.")
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
    @app_commands.describe(message="Use {member} or {member.mention} and {guild}. Type reset to clear.")
    async def set_welcome_message(self, interaction: discord.Interaction, message: str):
        value = None if message.lower() == "reset" else message
        await self.update_setting(interaction.guild_id, "welcome_message", value)
        await interaction.response.send_message("Welcome message updated.", ephemeral=True)

    @server_config.command(name="set-goodbye-message", description="Set the goodbye message template.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(message="Use {member} and {guild}. Type reset to clear.")
    async def set_goodbye_message(self, interaction: discord.Interaction, message: str):
        value = None if message.lower() == "reset" else message
        await self.update_setting(interaction.guild_id, "goodbye_message", value)
        await interaction.response.send_message("Goodbye message updated.", ephemeral=True)

    @server_config.command(name="reset-channel", description="Reset one configured channel slot.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(
        target="Which configured channel to reset."
    )
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
        settings = await self.get_settings(interaction.guild_id)
        target_channel_id = settings["announcement_channel_id"] or interaction.channel_id
        channel = interaction.guild.get_channel(target_channel_id) or await interaction.guild.fetch_channel(target_channel_id)

        embed = discord.Embed(description=message, color=discord.Color.blurple())
        embed.set_author(name=f"Announcement from {interaction.guild.name}")
        embed.set_footer(text=f"Sent by {interaction.user.display_name}")
        await channel.send(embed=embed)

        if target_channel_id == interaction.channel_id:
            await interaction.response.send_message("Announcement sent in this channel.", ephemeral=True)
        else:
            await interaction.response.send_message(f"Announcement sent to {channel.mention}.", ephemeral=True)

    async def _log_to_modlog(self, guild: discord.Guild, title: str, description: str, color: discord.Color):
        settings = await self.get_settings(guild.id)
        channel_id = settings["modlog_channel_id"]
        if channel_id is None:
            return

        embed = discord.Embed(title=title, description=description, color=color, timestamp=discord.utils.utcnow())
        await self._send_to_channel(channel_id, embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        settings = await self.get_settings(member.guild.id)
        if settings["welcome_channel_id"]:
            text = (settings["welcome_message"] or DEFAULT_WELCOME_MESSAGE).format(
                member=member, guild=member.guild.name
            )
            await self._send_to_channel(settings["welcome_channel_id"], content=text)

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
            text = (settings["goodbye_message"] or DEFAULT_GOODBYE_MESSAGE).format(
                member=member, guild=member.guild.name
            )
            await self._send_to_channel(settings["goodbye_channel_id"], content=text)

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
