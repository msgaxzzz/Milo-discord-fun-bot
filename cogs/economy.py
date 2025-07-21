import discord
from discord import app_commands
from discord.ext import commands
import random
import datetime

class Economy(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.loop.create_task(self.setup_database())

    async def setup_database(self):
        async with self.bot.db.cursor() as cursor:
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    balance INTEGER DEFAULT 100
                )
            ''')
        await self.bot.db.commit()

    async def get_or_create_user(self, user_id):
        async with self.bot.db.cursor() as cursor:
            await cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
            result = await cursor.fetchone()
            if result is None:
                await cursor.execute("INSERT INTO users (user_id, balance) VALUES (?, ?)", (user_id, 100))
                await self.bot.db.commit()
                return 100
            return result[0]

    jobs = app_commands.Group(name="jobs", description="Perform various jobs to earn coins.")

    @app_commands.command(name="balance", description="Check your or another member's coin balance.")
    @app_commands.describe(member="The member whose balance you want to see.")
    @app_commands.checks.cooldown(1, 10, key=lambda i: i.user.id)
    async def balance(self, interaction: discord.Interaction, member: discord.Member = None):
        target_member = member or interaction.user
        balance = await self.get_or_create_user(target_member.id)
        embed = discord.Embed(title=f"{target_member.name}'s Balance", color=discord.Color.green())
        embed.add_field(name="Coins", value=f"🪙 {balance}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="daily", description="Claim your daily reward.")
    @app_commands.checks.cooldown(1, 86400, key=lambda i: i.user.id)
    async def daily(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        await self.get_or_create_user(user_id)
        daily_amount = random.randint(100, 500)
        
        async with self.bot.db.cursor() as cursor:
            await cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (daily_amount, user_id))
        await self.bot.db.commit()
        
        embed = discord.Embed(title="Daily Reward!", description=f"You have claimed your daily reward of 🪙 **{daily_amount}** coins!", color=discord.Color.gold())
        await interaction.response.send_message(embed=embed)

    @daily.error
    async def daily_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            seconds = error.retry_after
            hours, remainder = divmod(int(seconds), 3600)
            minutes, _ = divmod(remainder, 60)
            await interaction.response.send_message(f"You've already claimed your daily reward. Please try again in **{hours}h {minutes}m**.", ephemeral=True)
    
    @jobs.command(name="freelance", description="Do a quick freelance job for some extra cash.")
    @app_commands.checks.cooldown(1, 900, key=lambda i: i.user.id)
    async def jobs_freelance(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        await self.get_or_create_user(user_id)
        amount = random.randint(25, 75)
        
        async with self.bot.db.cursor() as cursor:
            await cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        await self.bot.db.commit()
        
        messages = [
            f"You designed a logo for a local startup and earned 🪙 **{amount}**.",
            f"You wrote a short article for a blog and got paid 🪙 **{amount}**.",
            f"You helped someone with their homework and they tipped you 🪙 **{amount}**."
        ]
        await interaction.response.send_message(random.choice(messages))
        
    @jobs_freelance.error
    async def freelance_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            minutes = int(error.retry_after / 60)
            await interaction.response.send_message(f"You need a break. You can do another freelance job in **{minutes}** minutes.", ephemeral=True)

    @jobs.command(name="regular", description="Work your regular shift for a steady income.")
    @app_commands.checks.cooldown(1, 3600, key=lambda i: i.user.id)
    async def jobs_regular(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        await self.get_or_create_user(user_id)
        amount = random.randint(100, 300)
        
        async with self.bot.db.cursor() as cursor:
            await cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        await self.bot.db.commit()

        messages = [
            f"You completed your shift as a programmer and earned 🪙 **{amount}**.",
            f"You spent the day as a server janitor and got paid 🪙 **{amount}**.",
            f"You delivered pizzas all afternoon and made 🪙 **{amount}**."
        ]
        await interaction.response.send_message(random.choice(messages))

    @jobs_regular.error
    async def regular_work_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            minutes = int(error.retry_after / 60)
            await interaction.response.send_message(f"You're tired from your shift. You can work again in **{minutes}** minutes.", ephemeral=True)
            
    @jobs.command(name="crime", description="Commit a crime for a high reward, but with high risk.")
    @app_commands.checks.cooldown(1, 21600, key=lambda i: i.user.id)
    async def jobs_crime(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        balance = await self.get_or_create_user(user_id)
        
        success_chance = 0.50
        if random.random() < success_chance:
            payout = random.randint(500, 1500)
            async with self.bot.db.cursor() as cursor:
                await cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (payout, user_id))
            await self.bot.db.commit()
            await interaction.response.send_message(f"🚨 **Success!** Your high-stakes bank heist went perfectly. You got away with 🪙 **{payout}**!")
        else:
            fine = random.randint(200, 750)
            fine = min(balance, fine) 
            async with self.bot.db.cursor() as cursor:
                await cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (fine, user_id))
            await self.bot.db.commit()
            await interaction.response.send_message(f"👮‍♂️ **BUSTED!** The silent alarm tripped during your operation. You were caught and fined 🪙 **{fine}**.")

    @jobs_crime.error
    async def crime_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            hours = int(error.retry_after / 3600)
            await interaction.response.send_message(f"You need to lay low for a while. You can try another crime in **{hours}** hours.", ephemeral=True)

    @app_commands.command(name="gamble", description="Gamble your coins for a chance to win big.")
    @app_commands.describe(amount="The amount of coins you want to gamble.")
    @app_commands.checks.cooldown(1, 10, key=lambda i: i.user.id)
    async def gamble(self, interaction: discord.Interaction, amount: app_commands.Range[int, 1]):
        user_id = interaction.user.id
        balance = await self.get_or_create_user(user_id)
        
        if amount > balance:
            await interaction.response.send_message("You don't have enough coins to gamble that much.", ephemeral=True)
            return

        win = random.choice([True, False, False])

        async with self.bot.db.cursor() as cursor:
            if win:
                new_balance = balance + amount
                await cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))
                await interaction.response.send_message(f"🎉 **You won!** You gambled {amount} and won {amount} coins! Your new balance is 🪙 {new_balance}.")
            else:
                new_balance = balance - amount
                await cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))
                await interaction.response.send_message(f"💀 **You lost!** You gambled {amount} and lost it all. Your new balance is 🪙 {new_balance}.")
        await self.bot.db.commit()

    @app_commands.command(name="leaderboard", description="Shows the top 10 richest users in the server.")
    @app_commands.checks.cooldown(1, 30, key=lambda i: i.guild_id)
    async def leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        async with self.bot.db.cursor() as cursor:
            await cursor.execute("SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT 10")
            top_users = await cursor.fetchall()

        if not top_users:
            await interaction.followup.send("The leaderboard is empty!")
            return

        embed = discord.Embed(title="🏆 Server Coin Leaderboard 🏆", color=discord.Color.gold())
        
        leaderboard_text = ""
        for rank, (user_id, balance) in enumerate(top_users, start=1):
            try:
                user = await self.bot.fetch_user(user_id)
                user_name = user.name
            except discord.NotFound:
                user_name = f"Unknown User (ID: {user_id})"

            leaderboard_text += f"{rank}. {user_name} - 🪙 {balance}\n"

        embed.description = leaderboard_text
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="transfer", description="Transfer coins to another member.")
    @app_commands.describe(member="The member you want to transfer coins to.", amount="The amount of coins to transfer.")
    @app_commands.checks.cooldown(1, 15, key=lambda i: i.user.id)
    async def transfer(self, interaction: discord.Interaction, member: discord.Member, amount: app_commands.Range[int, 1]):
        sender_id = interaction.user.id
        receiver_id = member.id

        if sender_id == receiver_id:
            await interaction.response.send_message("You cannot transfer coins to yourself.", ephemeral=True)
            return

        sender_balance = await self.get_or_create_user(sender_id)

        if sender_balance < amount:
            await interaction.response.send_message("You do not have enough coins to make this transfer.", ephemeral=True)
            return
        
        await self.get_or_create_user(receiver_id)

        async with self.bot.db.cursor() as cursor:
            await cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, sender_id))
            await cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, receiver_id))
        
        await self.bot.db.commit()
        await interaction.response.send_message(f"💸 You have successfully transferred 🪙 **{amount}** coins to {member.mention}!")

    @app_commands.command(name="rob", description="Attempt to rob coins from another member.")
    @app_commands.describe(member="The member you want to rob.")
    @app_commands.checks.cooldown(1, 1800, key=lambda i: i.user.id)
    async def rob(self, interaction: discord.Interaction, member: discord.Member):
        robber_id = interaction.user.id
        victim_id = member.id

        if robber_id == victim_id:
            await interaction.response.send_message("You can't rob yourself, you silly goose!", ephemeral=True)
            return
        
        robber_balance = await self.get_or_create_user(robber_id)
        victim_balance = await self.get_or_create_user(victim_id)

        if victim_balance < 200:
            await interaction.response.send_message(f"{member.name} is too poor to be worth robbing.", ephemeral=True)
            self.rob.reset_cooldown(interaction)
            return

        success_chance = 0.40
        if random.random() < success_chance:
            robbed_amount = random.randint(int(victim_balance * 0.1), int(victim_balance * 0.25))
            async with self.bot.db.cursor() as cursor:
                await cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (robbed_amount, robber_id))
                await cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (robbed_amount, victim_id))
            await self.bot.db.commit()
            await interaction.response.send_message(f"🚨 Success! You discreetly robbed 🪙 **{robbed_amount}** from {member.mention}!")
        else:
            fine_amount = random.randint(int(robber_balance * 0.1), int(robber_balance * 0.2))
            fine_amount = min(robber_balance, fine_amount) 
            async with self.bot.db.cursor() as cursor:
                await cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (fine_amount, robber_id))
            await self.bot.db.commit()
            await interaction.response.send_message(f"👮‍♂️ Busted! Your robbery attempt on {member.mention} failed and you were fined 🪙 **{fine_amount}**.")

    @rob.error
    async def rob_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            minutes = int(error.retry_after / 60)
            await interaction.response.send_message(f"You're on a cooldown. You can attempt another robbery in **{minutes}** minutes.", ephemeral=True)

    @app_commands.command(name="slots", description="Play the slot machine.")
    @app_commands.describe(bet="The amount of coins you want to bet.")
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    async def slots(self, interaction: discord.Interaction, bet: app_commands.Range[int, 10]):
        user_id = interaction.user.id
        balance = await self.get_or_create_user(user_id)

        if bet > balance:
            await interaction.response.send_message("You don't have enough coins to bet that much.", ephemeral=True)
            return

        reels = ['🍒', '🍊', '🍋', '🔔', '⭐', '💎']
        spin = [random.choice(reels) for _ in range(3)]
        
        result_text = f"**[ {spin[0]} | {spin[1]} | {spin[2]} ]**\n\n"

        winnings = 0
        if spin[0] == spin[1] == spin[2]:
            if spin[0] == '💎':
                winnings = bet * 20
                result_text += f"💎 JACKPOT! 💎 You won **{winnings}** coins!"
            else:
                winnings = bet * 10
                result_text += f"🎉 BIG WIN! 🎉 You won **{winnings}** coins!"
        elif spin[0] == spin[1] or spin[1] == spin[2]:
            winnings = bet * 2
            result_text += f"👍 Nice! You won **{winnings}** coins!"
        else:
            winnings = -bet
            result_text += "☠️ Aw, tough luck! You lost your bet."

        new_balance = balance + winnings
        async with self.bot.db.cursor() as cursor:
            await cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))
        await self.bot.db.commit()
        
        embed = discord.Embed(title="🎰 Slot Machine 🎰", description=result_text, color=discord.Color.dark_magenta())
        embed.set_footer(text=f"Your new balance is 🪙 {new_balance}")
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Economy(bot))