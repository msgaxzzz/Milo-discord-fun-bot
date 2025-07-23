import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
import math
import random

class Farming(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.loop.create_task(self.setup_database())
        
        self.crops = {
            "wheat": {"name": "Wheat 🌾", "cost": 10, "growth": 600, "reward": 25, "xp": 5, "level": 1},
            "potato": {"name": "Potato 🥔", "cost": 25, "growth": 1800, "reward": 75, "xp": 15, "level": 2},
            "carrot": {"name": "Carrot 🥕", "cost": 50, "growth": 3600, "reward": 180, "xp": 30, "level": 5},
            "strawberry": {"name": "Strawberry 🍓", "cost": 150, "growth": 7200, "reward": 500, "xp": 100, "level": 10}
        }
        
        self.land_types = {
            1: {"name": "Barren Land", "mod": 1.0, "cost": 0},
            2: {"name": "Decent Soil", "mod": 0.9, "cost": 1000},
            3: {"name": "Fertile Land", "mod": 0.75, "cost": 5000}
        }

    async def setup_database(self):
        async with self.bot.db.cursor() as cursor:
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS farms (
                    user_id INTEGER PRIMARY KEY,
                    crop TEXT,
                    plant_time TEXT,
                    land_type INTEGER DEFAULT 1,
                    level INTEGER DEFAULT 1,
                    xp INTEGER DEFAULT 0
                )
            ''')
        await self.bot.db.commit()

    async def get_farm_data(self, user_id: int):
        async with self.bot.db.cursor() as cursor:
            await cursor.execute("SELECT * FROM farms WHERE user_id = ?", (user_id,))
            result = await cursor.fetchone()
            if not result:
                await cursor.execute("INSERT INTO farms (user_id) VALUES (?)", (user_id,))
                await self.bot.db.commit()
                await cursor.execute("SELECT * FROM farms WHERE user_id = ?", (user_id,))
                result = await cursor.fetchone()
        
        keys = ["user_id", "crop", "plant_time", "land_type", "level", "xp"]
        return dict(zip(keys, result))

    def get_xp_for_next_level(self, level: int):
        return math.floor(100 * (level ** 1.5))

    farm = app_commands.Group(name="farm", description="Manage your farm, grow crops, and level up.")

    @farm.command(name="profile", description="View your farm profile, including level and status.")
    async def profile(self, interaction: discord.Interaction):
        await interaction.response.defer()
        farm_data = await self.get_farm_data(interaction.user.id)
        
        embed = discord.Embed(title=f"{interaction.user.name}'s Farm Profile", color=discord.Color.green())
        
        level = farm_data["level"]
        xp = farm_data["xp"]
        xp_needed = self.get_xp_for_next_level(level)
        progress = min(int((xp / xp_needed) * 20), 20)
        progress_bar = '🟩' * progress + '⬛' * (20 - progress)

        embed.add_field(name="📜 Level", value=f"**{level}**", inline=True)
        embed.add_field(name="🌱 XP", value=f"{xp} / {xp_needed}", inline=True)
        embed.add_field(name="📊 Progress", value=f"`{progress_bar}`", inline=False)
        embed.add_field(name="🏞️ Land", value=self.land_types[farm_data["land_type"]]["name"], inline=True)
        
        if not farm_data["crop"]:
            embed.add_field(name="🌾 Current Crop", value="Plot is empty.", inline=True)
        else:
            crop_name = farm_data["crop"]
            crop_data = self.crops[crop_name]
            plant_time = datetime.fromisoformat(farm_data["plant_time"])
            land_mod = self.land_types[farm_data["land_type"]]["mod"]
            harvest_time = plant_time + timedelta(seconds=crop_data["growth"] * land_mod)
            
            embed.add_field(name="🌾 Current Crop", value=crop_data["name"], inline=True)
            if datetime.utcnow() >= harvest_time:
                embed.add_field(name="⏰ Status", value="✅ **Ready to Harvest!**", inline=False)
            else:
                embed.add_field(name="⏰ Ready In", value=f"{discord.utils.format_dt(harvest_time, style='R')}", inline=False)

        await interaction.followup.send(embed=embed)

    @farm.command(name="shop", description="Open the seed shop to buy new crops.")
    async def shop(self, interaction: discord.Interaction):
        farm_data = await self.get_farm_data(interaction.user.id)
        user_level = farm_data["level"]

        embed = discord.Embed(title="🌱 Seed Shop", description="Select a seed to plant from the shop.", color=discord.Color.dark_gold())
        for key, crop in self.crops.items():
            unlocked = user_level >= crop["level"]
            emoji = "✅" if unlocked else "🔒"
            embed.add_field(
                name=f"{crop['name']} (Lvl {crop['level']}) {emoji}",
                value=f"Cost: 🪙 {crop['cost']}\nReward: 🪙 {crop['reward']}\nXP: {crop['xp']}",
                inline=True
            )
        
        await interaction.response.send_message(embed=embed)

    @farm.command(name="plant", description="Plant a crop in your farm.")
    @app_commands.describe(crop="The name of the crop to plant (e.g., wheat, potato).")
    async def plant(self, interaction: discord.Interaction, crop: str):
        crop_name = crop.lower()
        if crop_name not in self.crops:
            await interaction.response.send_message(f"That's not a valid crop! Check the `/farm shop` for options.", ephemeral=True)
            return

        farm_data = await self.get_farm_data(interaction.user.id)
        if farm_data["crop"]:
            await interaction.response.send_message("You already have a crop growing!", ephemeral=True)
            return

        crop_data = self.crops[crop_name]
        if farm_data["level"] < crop_data["level"]:
            await interaction.response.send_message(f"You're not a high enough level! You need to be level {crop_data['level']} to plant {crop_data['name']}.", ephemeral=True)
            return
            
        economy_cog = self.bot.get_cog('Economy')
        if not economy_cog:
            await interaction.response.send_message("The economy system is currently unavailable.", ephemeral=True)
            return

        user_balance = await economy_cog.get_or_create_user(interaction.user.id)
        if user_balance < crop_data["cost"]:
            await interaction.response.send_message(f"You don't have enough coins! Planting {crop_data['name']} costs 🪙 {crop_data['cost']}.", ephemeral=True)
            return
        
        async with self.bot.db.cursor() as cursor:
            await cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (crop_data["cost"], interaction.user.id))
            await cursor.execute("UPDATE farms SET crop = ?, plant_time = ? WHERE user_id = ?", (crop_name, datetime.utcnow().isoformat(), interaction.user.id))
        await self.bot.db.commit()

        land_mod = self.land_types[farm_data["land_type"]]["mod"]
        growth_seconds = crop_data["growth"] * land_mod
        growth_hours = round(growth_seconds / 3600, 1)

        await interaction.response.send_message(f"You've successfully planted **{crop_data['name']}** for 🪙 {crop_data['cost']}! It will be ready in {growth_hours} hours.")

    @farm.command(name="harvest", description="Harvest your fully grown crop for coins and XP.")
    async def harvest(self, interaction: discord.Interaction):
        farm_data = await self.get_farm_data(interaction.user.id)
        if not farm_data["crop"]:
            await interaction.response.send_message("You don't have anything planted right now.", ephemeral=True)
            return

        crop_name = farm_data["crop"]
        crop_data = self.crops[crop_name]
        plant_time = datetime.fromisoformat(farm_data["plant_time"])
        land_mod = self.land_types[farm_data["land_type"]]["mod"]
        harvest_time = plant_time + timedelta(seconds=crop_data["growth"] * land_mod)

        if datetime.utcnow() < harvest_time:
            time_left = harvest_time - datetime.utcnow()
            await interaction.response.send_message(f"Your {crop_data['name']} isn't ready yet! Come back in {discord.utils.format_dt(harvest_time, style='R')}.", ephemeral=True)
            return
        
        economy_cog = self.bot.get_cog('Economy')
        if not economy_cog:
            await interaction.response.send_message("The economy system is currently unavailable.", ephemeral=True)
            return
        
        base_reward = crop_data["reward"]
        base_xp = crop_data["xp"]
        event_message = ""
        
        # Random Event
        roll = random.random()
        if roll < 0.1: # 10% chance of a bad event
            base_reward = int(base_reward * 0.5)
            event_message = "\n\n**Oh no! A swarm of pests ate half your harvest!** 🐛"
        elif roll > 0.95: # 5% chance of a good event
            base_reward = int(base_reward * 1.5)
            base_xp = int(base_xp * 1.5)
            event_message = "\n\n**Amazing! A bountiful harvest! You got extra coins and XP!** ✨"
        
        new_xp = farm_data["xp"] + base_xp
        current_level = farm_data["level"]
        xp_needed = self.get_xp_for_next_level(current_level)
        level_up_message = ""

        while new_xp >= xp_needed:
            current_level += 1
            new_xp -= xp_needed
            xp_needed = self.get_xp_for_next_level(current_level)
            level_up_message += f"\n🎉 **LEVEL UP! You are now Farm Level {current_level}!** 🎉"

        async with self.bot.db.cursor() as cursor:
            await cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (base_reward, interaction.user.id))
            await cursor.execute("UPDATE farms SET crop = NULL, plant_time = NULL, level = ?, xp = ? WHERE user_id = ?", (current_level, new_xp, interaction.user.id))
        await self.bot.db.commit()

        await interaction.response.send_message(f"You harvested your **{crop_data['name']}** and earned 🪙 **{base_reward}** and **{base_xp} XP**!{event_message}{level_up_message}")

    @farm.command(name="upgrade", description="Upgrade your farm land for faster growth times.")
    async def upgrade(self, interaction: discord.Interaction):
        farm_data = await self.get_farm_data(interaction.user.id)
        current_land_level = farm_data["land_type"]

        if current_land_level >= len(self.land_types):
            await interaction.response.send_message("You already have the best land available!", ephemeral=True)
            return

        next_land_level = current_land_level + 1
        upgrade_data = self.land_types[next_land_level]
        
        economy_cog = self.bot.get_cog('Economy')
        if not economy_cog:
            await interaction.response.send_message("The economy system is currently unavailable.", ephemeral=True)
            return

        user_balance = await economy_cog.get_or_create_user(interaction.user.id)
        if user_balance < upgrade_data["cost"]:
            await interaction.response.send_message(f"You don't have enough coins! Upgrading to **{upgrade_data['name']}** costs 🪙 {upgrade_data['cost']}.", ephemeral=True)
            return

        async with self.bot.db.cursor() as cursor:
            await cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (upgrade_data["cost"], interaction.user.id))
            await cursor.execute("UPDATE farms SET land_type = ? WHERE user_id = ?", (next_land_level, interaction.user.id))
        await self.bot.db.commit()

        await interaction.response.send_message(f"Congratulations! You've spent 🪙 {upgrade_data['cost']} to upgrade your farm to **{upgrade_data['name']}**! Your crops will now grow faster.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Farming(bot))