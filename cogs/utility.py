import discord
from discord import app_commands
from discord.ext import commands
import datetime
import re
import asyncio
import sys

class Utility(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        if not hasattr(bot, 'start_time'):
            self.bot.start_time = discord.utils.utcnow()

    help_group = app_commands.Group(name="help", description="Get help with the bot's commands.")

    @app_commands.command(name="ping", description="Checks the bot's latency.")
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    async def ping(self, interaction: discord.Interaction):
        latency = self.bot.latency * 1000
        await interaction.response.send_message(f'Pong! Latency: {latency:.2f}ms')
        
    @app_commands.command(name="memberinfo", description="Displays information about a member.")
    @app_commands.describe(member="The member to get info about.")
    @app_commands.checks.cooldown(1, 10, key=lambda i: i.user.id)
    async def memberinfo(self, interaction: discord.Interaction, member: discord.Member = None):
        target_member = member or interaction.user
        
        embed = discord.Embed(color=target_member.color, timestamp=discord.utils.utcnow())
        embed.set_author(name=f"User Info - {target_member}")
        if target_member.display_avatar:
             embed.set_thumbnail(url=target_member.display_avatar.url)
        embed.set_footer(text=f"Requested by {interaction.user.name}", icon_url=interaction.user.avatar.url)
        
        embed.add_field(name="ID", value=target_member.id, inline=False)
        embed.add_field(name="Display Name", value=target_member.display_name, inline=True)
        embed.add_field(name="Bot?", value=target_member.bot, inline=True)
        
        created_at = discord.utils.format_dt(target_member.created_at, style='F')
        embed.add_field(name="Created At", value=created_at, inline=False)
        
        joined_at = discord.utils.format_dt(target_member.joined_at, style='F')
        embed.add_field(name="Joined At", value=joined_at, inline=False)

        roles = [role.mention for role in reversed(target_member.roles[1:])]
        roles_str = ", ".join(roles) if roles else "No roles"
        embed.add_field(name=f"Roles [{len(roles)}]", value=roles_str if len(roles_str) < 1024 else f"{len(roles)} roles (too many to display)", inline=False)
        
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name="clear", description="Deletes a specified number of messages.")
    @app_commands.describe(amount="The number of messages to delete (1-100).")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clear(self, interaction: discord.Interaction, amount: app_commands.Range[int, 1, 100]):
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"Successfully deleted {len(deleted)} messages.", ephemeral=True)

    @app_commands.command(name="serverinfo", description="Displays detailed information about the server.")
    @app_commands.checks.cooldown(1, 10, key=lambda i: i.guild_id)
    async def serverinfo(self, interaction: discord.Interaction):
        guild = interaction.guild
        embed = discord.Embed(title=f"Server Info: {guild.name}", color=discord.Color.blue(), timestamp=discord.utils.utcnow())
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
    
        owner_text = "Unknown"
        if guild.owner:
            owner_text = guild.owner.mention
        else:
            try:
                # 如果服主对象不在缓存，就通过ID去主动获取
                owner = await guild.fetch_member(guild.owner_id)
                owner_text = owner.mention
            except (discord.NotFound, discord.HTTPException):
                owner_text = f"ID: {guild.owner_id}"

        embed.add_field(name="Owner", value=owner_text, inline=True)
        embed.add_field(name="ID", value=guild.id, inline=True)
        embed.add_field(name="Created At", value=discord.utils.format_dt(guild.created_at, 'F'), inline=False)
        
        bots = sum(1 for member in guild.members if member.bot)
        embed.add_field(name="Members", value=f"Total: {guild.member_count}\nHumans: {guild.member_count - bots}\nBots: {bots}", inline=True)
        
        channels = len(guild.text_channels) + len(guild.voice_channels)
        embed.add_field(name="Channels", value=f"Total: {channels}\nText: {len(guild.text_channels)}\nVoice: {len(guild.voice_channels)}", inline=True)
        
        embed.add_field(name="Roles", value=len(guild.roles), inline=True)
        
        if guild.features:
            embed.add_field(name="Features", value=", ".join(f.replace('_', ' ').title() for f in guild.features), inline=False)

        embed.set_footer(text=f"Requested by {interaction.user.name}", icon_url=interaction.user.avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="botinfo", description="Displays information and stats about the bot.")
    @app_commands.checks.cooldown(1, 10, key=lambda i: i.user.id)
    async def botinfo(self, interaction: discord.Interaction):
        delta_uptime = discord.utils.utcnow() - self.bot.start_time
        hours, remainder = divmod(int(delta_uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)
        uptime = f"{days}d {hours}h {minutes}m {seconds}s"

        embed = discord.Embed(title=f"{self.bot.user.name} Stats", color=discord.Color.purple(), timestamp=discord.utils.utcnow())
        
        
        if self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)
        
        
        developer_name = "Sentinel Team" 
        embed.add_field(name="Developer", value=developer_name, inline=True)
        embed.add_field(name="Servers", value=f"{len(self.bot.guilds)}", inline=True)
        embed.add_field(name="Total Users", value=f"{len(self.bot.users)}", inline=True)
        embed.add_field(name="Python Version", value=f"{sys.version.split(' ')[0]}", inline=True)
        embed.add_field(name="discord.py Version", value=f"{discord.__version__}", inline=True)
        embed.add_field(name="Uptime", value=uptime, inline=True)
        
        await interaction.response.send_message(embed=embed)

    async def command_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        commands = self.bot.tree.get_commands()
        return [
            app_commands.Choice(name=command.name, value=command.name)
            for command in commands if current.lower() in command.name.lower()
        ]

    @help_group.command(name="all", description="Lists all available commands.")
    async def help_all(self, interaction: discord.Interaction):
        embed = discord.Embed(title="Bot Commands", description="Here is a list of all available commands.", color=discord.Color.blurple())
        
        cogs_names = sorted(self.bot.cogs.keys())
        for cog_name in cogs_names:
            cog = self.bot.get_cog(cog_name)
            commands = cog.get_app_commands()
            if not commands:
                continue
            
            command_list = [f"`/{command.name}`" for command in commands]
            embed.add_field(name=cog_name, value=" ".join(command_list), inline=False)

        await interaction.response.send_message(embed=embed)

    @help_group.command(name="command", description="Get detailed help for a specific command.")
    @app_commands.autocomplete(command=command_autocomplete)
    @app_commands.describe(command="The command you need help with.")
    async def help_command(self, interaction: discord.Interaction, command: str):
        cmd = self.bot.tree.get_command(command)
        if not cmd:
            await interaction.response.send_message(f"Command `{command}` not found.", ephemeral=True)
            return

        embed = discord.Embed(title=f"Help: `/{cmd.name}`", description=cmd.description, color=discord.Color.blurple())
        
        if cmd.parameters:
            params = [f"`{param.name}`: {param.description}" for param in cmd.parameters]
            embed.add_field(name="Parameters", value="\n".join(params), inline=False)
            
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="remindme", description="Sets a reminder for you.")
    @app_commands.describe(time="When to remind (e.g., 10s, 5m, 2h, 1d).", reason="What to be reminded of.")
    async def remindme(self, interaction: discord.Interaction, time: str, reason: str):
        time_regex = re.compile(r"(\d+)([smhd])")
        time_match = time_regex.match(time.lower())

        if not time_match:
            await interaction.response.send_message("Invalid time format. Use s, m, h, or d (e.g., `10s`, `5m`, `2h`, `1d`).", ephemeral=True)
            return
        
        quantity, unit = map(time_match.groups(), [int, str])

        if unit == 's': seconds = quantity
        elif unit == 'm': seconds = quantity * 60
        elif unit == 'h': seconds = quantity * 3600
        elif unit == 'd': seconds = quantity * 86400
        else: seconds = 0

        if seconds > 2592000: 
            await interaction.response.send_message("You cannot set a reminder for more than 30 days.", ephemeral=True)
            return

        await interaction.response.send_message(f"⏰ Okay! I will remind you in **{quantity}{unit}** about: `{reason}`", ephemeral=True)
        
        await asyncio.sleep(seconds)
        
        try:
            await interaction.user.send(f"**Reminder:** {reason}")
        except discord.Forbidden:
            try:
                await interaction.channel.send(f"Hey {interaction.user.mention}, you had a reminder: {reason}")
            except discord.HTTPException:
                pass

async def setup(bot: commands.Bot):
    await bot.add_cog(Utility(bot))