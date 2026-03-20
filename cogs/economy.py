import asyncio
import logging
import random

import discord
from discord import app_commands
from discord.ext import commands

logger = logging.getLogger(__name__)

# Constants
DEFAULT_BALANCE = 100
DAILY_MIN = 100
DAILY_MAX = 500
DAILY_COOLDOWN = 86400  # 24 hours
FREELANCE_MIN = 25
FREELANCE_MAX = 75
FREELANCE_COOLDOWN = 900  # 15 minutes
REGULAR_MIN = 100
REGULAR_MAX = 300
REGULAR_COOLDOWN = 3600  # 1 hour
CRIME_MIN = 500
CRIME_MAX = 1500
CRIME_FINE_MIN = 200
CRIME_FINE_MAX = 750
CRIME_SUCCESS_RATE = 0.50
CRIME_COOLDOWN = 21600  # 6 hours
ROB_SUCCESS_RATE = 0.40
ROB_MIN_VICTIM_BALANCE = 200
ROB_COOLDOWN = 1800  # 30 minutes
SLOTS_MIN_BET = 10


class Economy(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._guild_locks: dict[int, asyncio.Lock] = {}
        self.bot.loop.create_task(self.setup_database())

    def _guild_lock(self, guild_id: int) -> asyncio.Lock:
        lock = self._guild_locks.get(guild_id)
        if lock is None:
            lock = asyncio.Lock()
            self._guild_locks[guild_id] = lock
        return lock

    async def setup_database(self):
        columns = []
        async with self.bot.db.execute("PRAGMA table_info(users)") as cursor:
            columns = [row[1] for row in await cursor.fetchall()]

        if columns and "guild_id" not in columns:
            async with self.bot.db.cursor() as cursor:
                await cursor.execute("ALTER TABLE users RENAME TO users_legacy")
                await cursor.execute(
                    """
                    CREATE TABLE users (
                        guild_id INTEGER NOT NULL,
                        user_id INTEGER NOT NULL,
                        balance INTEGER NOT NULL DEFAULT 100,
                        PRIMARY KEY (guild_id, user_id)
                    )
                    """
                )
                await cursor.execute(
                    """
                    INSERT OR IGNORE INTO users (guild_id, user_id, balance)
                    SELECT DISTINCT COALESCE(messages.guild_id, 0), legacy.user_id, legacy.balance
                    FROM users_legacy AS legacy
                    LEFT JOIN messages
                        ON messages.user_id = legacy.user_id
                       AND messages.guild_id IS NOT NULL
                    """
                )
            logger.info("Migrated global economy balances to per-guild records.")
        else:
            async with self.bot.db.cursor() as cursor:
                await cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        guild_id INTEGER NOT NULL,
                        user_id INTEGER NOT NULL,
                        balance INTEGER NOT NULL DEFAULT 100,
                        PRIMARY KEY (guild_id, user_id)
                    )
                    """
                )

        await self.bot.db.commit()

    def _get_guild_id(self, interaction: discord.Interaction) -> int:
        if interaction.guild_id is None:
            raise app_commands.CheckFailure("This command can only be used in a server.")
        return interaction.guild_id

    async def _get_or_create_user_unlocked(self, guild_id: int, user_id: int) -> int:
        async with self.bot.db.cursor() as cursor:
            await cursor.execute(
                "SELECT balance FROM users WHERE guild_id = ? AND user_id = ?",
                (guild_id, user_id),
            )
            result = await cursor.fetchone()
            if result is None:
                await cursor.execute(
                    "INSERT INTO users (guild_id, user_id, balance) VALUES (?, ?, ?)",
                    (guild_id, user_id, DEFAULT_BALANCE),
                )
                await self.bot.db.commit()
                return DEFAULT_BALANCE
            return result[0]

    async def get_or_create_user(self, guild_id: int, user_id: int) -> int:
        async with self._guild_lock(guild_id):
            return await self._get_or_create_user_unlocked(guild_id, user_id)

    async def change_balance(self, guild_id: int, user_id: int, delta: int) -> int:
        async with self._guild_lock(guild_id):
            balance = await self._get_or_create_user_unlocked(guild_id, user_id)
            new_balance = balance + delta
            if new_balance < 0:
                raise ValueError("Balance cannot be negative.")

            async with self.bot.db.cursor() as cursor:
                await cursor.execute(
                    "UPDATE users SET balance = ? WHERE guild_id = ? AND user_id = ?",
                    (new_balance, guild_id, user_id),
                )
            await self.bot.db.commit()
            return new_balance

    async def transfer_balance(self, guild_id: int, sender_id: int, receiver_id: int, amount: int) -> tuple[int, int]:
        async with self._guild_lock(guild_id):
            sender_balance = await self._get_or_create_user_unlocked(guild_id, sender_id)
            if sender_balance < amount:
                raise ValueError("You do not have enough coins to make this transfer.")

            receiver_balance = await self._get_or_create_user_unlocked(guild_id, receiver_id)
            async with self.bot.db.cursor() as cursor:
                await cursor.execute(
                    "UPDATE users SET balance = ? WHERE guild_id = ? AND user_id = ?",
                    (sender_balance - amount, guild_id, sender_id),
                )
                await cursor.execute(
                    "UPDATE users SET balance = ? WHERE guild_id = ? AND user_id = ?",
                    (receiver_balance + amount, guild_id, receiver_id),
                )
            await self.bot.db.commit()
            return sender_balance - amount, receiver_balance + amount

    async def set_balance(self, guild_id: int, user_id: int, amount: int) -> int:
        async with self._guild_lock(guild_id):
            await self._get_or_create_user_unlocked(guild_id, user_id)
            async with self.bot.db.cursor() as cursor:
                await cursor.execute(
                    "UPDATE users SET balance = ? WHERE guild_id = ? AND user_id = ?",
                    (amount, guild_id, user_id),
                )
            await self.bot.db.commit()
            return amount

    jobs = app_commands.Group(name="jobs", description="Perform various jobs to earn coins.", guild_only=True)
    admin = app_commands.Group(name="economy-admin", description="Administer the server economy.", guild_only=True)

    @app_commands.command(name="balance", description="Check your or another member's coin balance.")
    @app_commands.guild_only()
    @app_commands.describe(member="The member whose balance you want to see.")
    @app_commands.checks.cooldown(1, 10, key=lambda i: (i.guild_id, i.user.id))
    async def balance(self, interaction: discord.Interaction, member: discord.Member = None):
        guild_id = self._get_guild_id(interaction)
        target_member = member or interaction.user
        balance = await self.get_or_create_user(guild_id, target_member.id)
        embed = discord.Embed(title=f"{target_member.name}'s Balance", color=discord.Color.green())
        embed.add_field(name="Coins", value=f"🪙 {balance}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="daily", description="Claim your daily reward.")
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, DAILY_COOLDOWN, key=lambda i: (i.guild_id, i.user.id))
    async def daily(self, interaction: discord.Interaction):
        guild_id = self._get_guild_id(interaction)
        daily_amount = random.randint(DAILY_MIN, DAILY_MAX)
        await self.change_balance(guild_id, interaction.user.id, daily_amount)

        embed = discord.Embed(
            title="Daily Reward!",
            description=f"You have claimed your daily reward of 🪙 **{daily_amount}** coins!",
            color=discord.Color.gold(),
        )
        await interaction.response.send_message(embed=embed)

    @daily.error
    async def daily_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            seconds = error.retry_after
            hours, remainder = divmod(int(seconds), 3600)
            minutes, _ = divmod(remainder, 60)
            await interaction.response.send_message(
                f"You've already claimed your daily reward. Please try again in **{hours}h {minutes}m**.",
                ephemeral=True,
            )

    @jobs.command(name="freelance", description="Do a quick freelance job for some extra cash.")
    @app_commands.checks.cooldown(1, FREELANCE_COOLDOWN, key=lambda i: (i.guild_id, i.user.id))
    async def jobs_freelance(self, interaction: discord.Interaction):
        guild_id = self._get_guild_id(interaction)
        amount = random.randint(FREELANCE_MIN, FREELANCE_MAX)
        await self.change_balance(guild_id, interaction.user.id, amount)

        messages = [
            f"You designed a logo for a local startup and earned 🪙 **{amount}**.",
            f"You wrote a short article for a blog and got paid 🪙 **{amount}**.",
            f"You helped someone with their homework and they tipped you 🪙 **{amount}**.",
        ]
        await interaction.response.send_message(random.choice(messages))

    @jobs_freelance.error
    async def freelance_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            minutes = int(error.retry_after / 60)
            await interaction.response.send_message(
                f"You need a break. You can do another freelance job in **{minutes}** minutes.", ephemeral=True
            )

    @jobs.command(name="regular", description="Work your regular shift for a steady income.")
    @app_commands.checks.cooldown(1, REGULAR_COOLDOWN, key=lambda i: (i.guild_id, i.user.id))
    async def jobs_regular(self, interaction: discord.Interaction):
        guild_id = self._get_guild_id(interaction)
        amount = random.randint(REGULAR_MIN, REGULAR_MAX)
        await self.change_balance(guild_id, interaction.user.id, amount)

        messages = [
            f"You completed your shift as a programmer and earned 🪙 **{amount}**.",
            f"You spent the day as a server janitor and got paid 🪙 **{amount}**.",
            f"You delivered pizzas all afternoon and made 🪙 **{amount}**.",
        ]
        await interaction.response.send_message(random.choice(messages))

    @jobs_regular.error
    async def regular_work_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            minutes = int(error.retry_after / 60)
            await interaction.response.send_message(
                f"You're tired from your shift. You can work again in **{minutes}** minutes.", ephemeral=True
            )

    @jobs.command(name="crime", description="Commit a crime for a high reward, but with high risk.")
    @app_commands.checks.cooldown(1, CRIME_COOLDOWN, key=lambda i: (i.guild_id, i.user.id))
    async def jobs_crime(self, interaction: discord.Interaction):
        guild_id = self._get_guild_id(interaction)
        balance = await self.get_or_create_user(guild_id, interaction.user.id)

        if random.random() < CRIME_SUCCESS_RATE:
            payout = random.randint(CRIME_MIN, CRIME_MAX)
            await self.change_balance(guild_id, interaction.user.id, payout)
            await interaction.response.send_message(
                f"🚨 **Success!** Your high-stakes bank heist went perfectly. You got away with 🪙 **{payout}**!"
            )
        else:
            fine = min(balance, random.randint(CRIME_FINE_MIN, CRIME_FINE_MAX))
            await self.change_balance(guild_id, interaction.user.id, -fine)
            await interaction.response.send_message(
                f"👮‍♂️ **BUSTED!** The silent alarm tripped during your operation. You were caught and fined 🪙 **{fine}**."
            )

    @jobs_crime.error
    async def crime_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            hours = int(error.retry_after / 3600)
            await interaction.response.send_message(
                f"You need to lay low for a while. You can try another crime in **{hours}** hours.", ephemeral=True
            )

    @app_commands.command(name="gamble", description="Gamble your coins for a chance to win big.")
    @app_commands.guild_only()
    @app_commands.describe(amount="The amount of coins you want to gamble.")
    @app_commands.checks.cooldown(1, 10, key=lambda i: (i.guild_id, i.user.id))
    async def gamble(self, interaction: discord.Interaction, amount: app_commands.Range[int, 1]):
        guild_id = self._get_guild_id(interaction)
        balance = await self.get_or_create_user(guild_id, interaction.user.id)

        if amount > balance:
            await interaction.response.send_message("You don't have enough coins to gamble that much.", ephemeral=True)
            return

        win = random.choice([True, False, False])
        delta = amount if win else -amount
        new_balance = await self.change_balance(guild_id, interaction.user.id, delta)

        if win:
            await interaction.response.send_message(
                f"🎉 **You won!** You gambled {amount} and won {amount} coins! Your new balance is 🪙 {new_balance}."
            )
        else:
            await interaction.response.send_message(
                f"💀 **You lost!** You gambled {amount} and lost it all. Your new balance is 🪙 {new_balance}."
            )

    @app_commands.command(name="leaderboard", description="Shows the top 10 richest users in the server.")
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 30, key=lambda i: i.guild_id)
    async def leaderboard(self, interaction: discord.Interaction):
        guild_id = self._get_guild_id(interaction)
        await interaction.response.defer()

        async with self.bot.db.cursor() as cursor:
            await cursor.execute(
                "SELECT user_id, balance FROM users WHERE guild_id = ? ORDER BY balance DESC LIMIT 10",
                (guild_id,),
            )
            top_users = await cursor.fetchall()

        if not top_users:
            await interaction.followup.send("The leaderboard is empty!")
            return

        embed = discord.Embed(title="🏆 Server Coin Leaderboard 🏆", color=discord.Color.gold())

        leaderboard_text = ""
        for rank, (user_id, balance) in enumerate(top_users, start=1):
            member = interaction.guild.get_member(user_id)
            if member is None:
                user_name = f"Unknown User (ID: {user_id})"
            else:
                user_name = member.display_name

            leaderboard_text += f"{rank}. {user_name} - 🪙 {balance}\n"

        embed.description = leaderboard_text
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="transfer", description="Transfer coins to another member.")
    @app_commands.guild_only()
    @app_commands.describe(
        member="The member you want to transfer coins to.", amount="The amount of coins to transfer."
    )
    @app_commands.checks.cooldown(1, 15, key=lambda i: (i.guild_id, i.user.id))
    async def transfer(
        self, interaction: discord.Interaction, member: discord.Member, amount: app_commands.Range[int, 1]
    ):
        guild_id = self._get_guild_id(interaction)
        sender_id = interaction.user.id
        receiver_id = member.id

        if sender_id == receiver_id:
            await interaction.response.send_message("You cannot transfer coins to yourself.", ephemeral=True)
            return

        if member.bot:
            await interaction.response.send_message("You cannot transfer coins to bots.", ephemeral=True)
            return

        try:
            await self.transfer_balance(guild_id, sender_id, receiver_id, amount)
        except ValueError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        await interaction.response.send_message(
            f"💸 You have successfully transferred 🪙 **{amount}** coins to {member.mention}!"
        )

    @app_commands.command(name="rob", description="Attempt to rob coins from another member.")
    @app_commands.guild_only()
    @app_commands.describe(member="The member you want to rob.")
    @app_commands.checks.cooldown(1, ROB_COOLDOWN, key=lambda i: (i.guild_id, i.user.id))
    async def rob(self, interaction: discord.Interaction, member: discord.Member):
        guild_id = self._get_guild_id(interaction)
        robber_id = interaction.user.id
        victim_id = member.id

        if robber_id == victim_id:
            await interaction.response.send_message("You can't rob yourself, you silly goose!", ephemeral=True)
            return

        if member.bot:
            await interaction.response.send_message("Bots are not part of the economy.", ephemeral=True)
            return

        async with self._guild_lock(guild_id):
            robber_balance = await self._get_or_create_user_unlocked(guild_id, robber_id)
            victim_balance = await self._get_or_create_user_unlocked(guild_id, victim_id)

            if victim_balance < ROB_MIN_VICTIM_BALANCE:
                self.rob.reset_cooldown(interaction)
                await interaction.response.send_message(
                    f"{member.name} is too poor to be worth robbing.", ephemeral=True
                )
                return

            async with self.bot.db.cursor() as cursor:
                if random.random() < ROB_SUCCESS_RATE:
                    robbed_amount = random.randint(int(victim_balance * 0.1), int(victim_balance * 0.25))
                    await cursor.execute(
                        "UPDATE users SET balance = ? WHERE guild_id = ? AND user_id = ?",
                        (robber_balance + robbed_amount, guild_id, robber_id),
                    )
                    await cursor.execute(
                        "UPDATE users SET balance = ? WHERE guild_id = ? AND user_id = ?",
                        (victim_balance - robbed_amount, guild_id, victim_id),
                    )
                    message = f"🚨 Success! You discreetly robbed 🪙 **{robbed_amount}** from {member.mention}!"
                else:
                    fine_amount = min(robber_balance, random.randint(int(robber_balance * 0.1), int(robber_balance * 0.2)))
                    await cursor.execute(
                        "UPDATE users SET balance = ? WHERE guild_id = ? AND user_id = ?",
                        (robber_balance - fine_amount, guild_id, robber_id),
                    )
                    message = (
                        f"👮‍♂️ Busted! Your robbery attempt on {member.mention} failed and you were fined 🪙 "
                        f"**{fine_amount}**."
                    )

            await self.bot.db.commit()

        await interaction.response.send_message(message)

    @rob.error
    async def rob_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            minutes = int(error.retry_after / 60)
            await interaction.response.send_message(
                f"You're on a cooldown. You can attempt another robbery in **{minutes}** minutes.", ephemeral=True
            )

    @app_commands.command(name="slots", description="Play the slot machine.")
    @app_commands.guild_only()
    @app_commands.describe(bet="The amount of coins you want to bet.")
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild_id, i.user.id))
    async def slots(self, interaction: discord.Interaction, bet: app_commands.Range[int, SLOTS_MIN_BET]):
        guild_id = self._get_guild_id(interaction)
        balance = await self.get_or_create_user(guild_id, interaction.user.id)

        if bet > balance:
            await interaction.response.send_message("You don't have enough coins to bet that much.", ephemeral=True)
            return

        reels = ["🍒", "🍊", "🍋", "🔔", "⭐", "💎"]
        spin = [random.choice(reels) for _ in range(3)]

        result_text = f"**[ {spin[0]} | {spin[1]} | {spin[2]} ]**\n\n"

        if spin[0] == spin[1] == spin[2]:
            if spin[0] == "💎":
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

        new_balance = await self.change_balance(guild_id, interaction.user.id, winnings)

        embed = discord.Embed(title="🎰 Slot Machine 🎰", description=result_text, color=discord.Color.dark_magenta())
        embed.set_footer(text=f"Your new balance is 🪙 {new_balance}")
        await interaction.response.send_message(embed=embed)

    @admin.command(name="add", description="Add coins to a member.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(member="The target member.", amount="How many coins to add.")
    async def admin_add(self, interaction: discord.Interaction, member: discord.Member, amount: app_commands.Range[int, 1]):
        guild_id = self._get_guild_id(interaction)
        balance = await self.change_balance(guild_id, member.id, amount)
        await interaction.response.send_message(
            f"Added 🪙 **{amount}** to {member.mention}. New balance: 🪙 {balance}.",
            ephemeral=True,
        )

    @admin.command(name="remove", description="Remove coins from a member.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(member="The target member.", amount="How many coins to remove.")
    async def admin_remove(
        self, interaction: discord.Interaction, member: discord.Member, amount: app_commands.Range[int, 1]
    ):
        guild_id = self._get_guild_id(interaction)
        current = await self.get_or_create_user(guild_id, member.id)
        removed = min(current, amount)
        balance = await self.change_balance(guild_id, member.id, -removed)
        await interaction.response.send_message(
            f"Removed 🪙 **{removed}** from {member.mention}. New balance: 🪙 {balance}.",
            ephemeral=True,
        )

    @admin.command(name="set", description="Set a member's balance exactly.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(member="The target member.", amount="The exact balance to set.")
    async def admin_set(self, interaction: discord.Interaction, member: discord.Member, amount: app_commands.Range[int, 0]):
        guild_id = self._get_guild_id(interaction)
        balance = await self.set_balance(guild_id, member.id, amount)
        await interaction.response.send_message(
            f"Set {member.mention}'s balance to 🪙 **{balance}**.",
            ephemeral=True,
        )

    @admin.command(name="reset-guild", description="Reset the server economy for all users.")
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_reset_guild(self, interaction: discord.Interaction):
        guild_id = self._get_guild_id(interaction)
        async with self._guild_lock(guild_id):
            async with self.bot.db.cursor() as cursor:
                await cursor.execute("DELETE FROM users WHERE guild_id = ?", (guild_id,))
            await self.bot.db.commit()
        await interaction.response.send_message("The server economy has been reset.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Economy(bot))
