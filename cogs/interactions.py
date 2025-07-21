import discord
from discord import app_commands
from discord.ext import commands
import aiohttp

class Interactions(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()

    async def cog_unload(self):
        await self.session.close()

    async def get_gif(self, category: str):
        try:
            async with self.session.get(f'https://api.waifu.pics/sfw/{category}') as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('url')
        except Exception as e:
            print(f"Could not fetch GIF for category {category}: {e}")
            return None

    async def create_interaction_embed(self, interaction: discord.Interaction, member: discord.Member, category: str, self_message: str, other_message: str):
        await interaction.response.defer()
        gif_url = await self.get_gif(category)

        if not gif_url:
            await interaction.followup.send(f"Sorry, couldn't get a GIF right now. But... {other_message.format(user=interaction.user.mention, target=member.mention)}", ephemeral=True)
            return

        message = self_message if member == interaction.user else other_message.format(user=interaction.user.mention, target=member.mention)
        
        embed = discord.Embed(
            description=message,
            color=discord.Color.from_rgb(255, 182, 193) # Pink
        )
        embed.set_image(url=gif_url)
        
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="hug", description="Give someone a hug.")
    @app_commands.describe(member="The person you want to hug.")
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    async def hug(self, interaction: discord.Interaction, member: discord.Member):
        await self.create_interaction_embed(
            interaction,
            member,
            category='hug',
            self_message="You can't hug yourself, but I can! Here's a hug from me to you.",
            other_message="{user} gives {target} a big, warm hug!"
        )

    @app_commands.command(name="pat", description="Pat someone's head.")
    @app_commands.describe(member="The person you want to pat.")
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    async def pat(self, interaction: discord.Interaction, member: discord.Member):
         await self.create_interaction_embed(
            interaction,
            member,
            category='pat',
            self_message="Feeling a bit lonely? I'll pat your head for you. *pats*",
            other_message="{user} gently pats {target}'s head. Aww."
        )

    @app_commands.command(name="slap", description="Slap someone.")
    @app_commands.describe(member="The person you want to slap.")
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    async def slap(self, interaction: discord.Interaction, member: discord.Member):
        if member == self.bot.user:
            await interaction.response.send_message(f"Ouch! What did I do to deserve that, {interaction.user.mention}?")
            return
            
        await self.create_interaction_embed(
            interaction,
            member,
            category='slap',
            self_message="{user} slaps themself in confusion!",
            other_message="Oof! {user} slaps {target} right across the face!"
        )
    
    @app_commands.command(name="kiss", description="Give someone a kiss.")
    @app_commands.describe(member="The person you want to kiss.")
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    async def kiss(self, interaction: discord.Interaction, member: discord.Member):
        await self.create_interaction_embed(
            interaction,
            member,
            category='kiss',
            self_message="Blowing a kiss to yourself in the mirror, nice!",
            other_message="{user} gives {target} a sweet kiss. Mwah!"
        )

    @app_commands.command(name="cuddle", description="Cuddle with someone.")
    @app_commands.describe(member="The person you want to cuddle with.")
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    async def cuddle(self, interaction: discord.Interaction, member: discord.Member):
        await self.create_interaction_embed(
            interaction,
            member,
            category='cuddle',
            self_message="Cuddling with a pillow is nice, but here's a virtual one!",
            other_message="{user} snuggles up and cuddles with {target}. So cozy!"
        )

    @app_commands.command(name="poke", description="Poke someone.")
    @app_commands.describe(member="The person you want to poke.")
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    async def poke(self, interaction: discord.Interaction, member: discord.Member):
        await self.create_interaction_embed(
            interaction,
            member,
            category='poke',
            self_message="You poke yourself. Why?",
            other_message="Hey! {user} just poked {target}."
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Interactions(bot))