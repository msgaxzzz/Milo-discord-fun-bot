import discord
from discord import app_commands
from discord.ext import commands
import aiohttp

class Media(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()

    async def cog_unload(self):
        await self.session.close()

    @app_commands.command(name="meme", description="Fetches a random meme.")
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    async def meme(self, interaction: discord.Interaction):
        await interaction.response.defer()
        async with self.session.get('https://meme-api.com/gimme') as response:
            if response.status == 200:
                data = await response.json()
                embed = discord.Embed(title=data['title'], url=data['postLink'], color=discord.Color.blue())
                embed.set_image(url=data['url'])
                embed.set_footer(text=f"From r/{data['subreddit']} | Upvotes: {data['ups']}")
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send("Could not fetch a meme, please try again.")

    @app_commands.command(name="cat", description="Fetches a random cat picture.")
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    async def cat(self, interaction: discord.Interaction):
        await interaction.response.defer()
        async with self.session.get('https://api.thecatapi.com/v1/images/search') as response:
            if response.status == 200:
                data = await response.json()
                embed = discord.Embed(title="Here's a random cat!", color=discord.Color.purple())
                embed.set_image(url=data[0]['url'])
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send("Could not fetch a cat picture, the cats are hiding!")

    @app_commands.command(name="dog", description="Fetches a random dog picture.")
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    async def dog(self, interaction: discord.Interaction):
        await interaction.response.defer()
        async with self.session.get('https://dog.ceo/api/breeds/image/random') as response:
            if response.status == 200:
                data = await response.json()
                embed = discord.Embed(title="Here's a random dog!", color=discord.Color.gold())
                embed.set_image(url=data['message'])
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send("Could not fetch a dog picture, the dogs are playing fetch!")

async def setup(bot: commands.Bot):
    await bot.add_cog(Media(bot))