import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio

class TicTacToeButton(discord.ui.Button['TicTacToe']):
    def __init__(self, x: int, y: int):
        super().__init__(style=discord.ButtonStyle.secondary, label='\u200b', row=y)
        self.x = x
        self.y = y

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: TicTacToe = self.view
        
        if interaction.user != view.current_player:
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return

        state = view.board[self.y][self.x]
        if state in (view.X, view.O):
            return

        if view.current_player == view.player1:
            self.style = discord.ButtonStyle.danger
            self.label = 'X'
            view.board[self.y][self.x] = view.X
            view.current_player = view.player2
            content = f"It's {view.player2.name}'s turn (O)."
        else:
            self.style = discord.ButtonStyle.success
            self.label = 'O'
            view.board[self.y][self.x] = view.O
            view.current_player = view.player1
            content = f"It's {view.player1.name}'s turn (X)."

        self.disabled = True
        winner = view.check_board_winner()
        if winner is not None:
            if winner == view.X:
                content = f"🏆 {view.player1.name} wins! 🏆"
            elif winner == view.O:
                content = f"🏆 {view.player2.name} wins! 🏆"
            else:
                content = "It's a tie!"
            
            for child in view.children:
                child.disabled = True
            
            view.stop()

        await interaction.response.edit_message(content=content, view=view)

class TicTacToe(discord.ui.View):
    X = -1
    O = 1
    Tie = 2

    def __init__(self, player1: discord.Member, player2: discord.Member):
        super().__init__(timeout=180)
        self.player1 = player1
        self.player2 = player2
        self.current_player = player1
        self.board = [
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
        ]

        for x in range(3):
            for y in range(3):
                self.add_item(TicTacToeButton(x, y))

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        
        message = await self.message.edit(content="Game timed out! No one made a move.", view=self)

    def check_board_winner(self):
        for i in range(3):
            if sum(self.board[i]) == 3: return self.O
            if sum(self.board[i]) == -3: return self.X
        
        for i in range(3):
            if self.board[0][i] + self.board[1][i] + self.board[2][i] == 3: return self.O
            if self.board[0][i] + self.board[1][i] + self.board[2][i] == -3: return self.X

        if self.board[0][0] + self.board[1][1] + self.board[2][2] == 3: return self.O
        if self.board[0][0] + self.board[1][1] + self.board[2][2] == -3: return self.X
        if self.board[0][2] + self.board[1][1] + self.board[2][0] == 3: return self.O
        if self.board[0][2] + self.board[1][1] + self.board[2][0] == -3: return self.X

        if all(i != 0 for row in self.board for i in row):
            return self.Tie

        return None

class Games(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_guess_games = set()

    @app_commands.command(name="eightball", description="Ask the magic 8-ball a question.")
    @app_commands.describe(question="The question you want to ask.")
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    async def eightball(self, interaction: discord.Interaction, question: str):
        responses = [
            "It is certain.", "It is decidedly so.", "Without a doubt.", "Yes – definitely.", "You may rely on it.", "As I see it, yes.", "Most likely.", "Outlook good.", "Yes.", "Signs point to yes.", "Reply hazy, try again.", "Ask again later.", "Better not tell you now.", "Cannot predict now.", "Concentrate and ask again.", "Don't count on it.", "My reply is no.", "My sources say no.", "Outlook not so good.", "Very doubtful."
        ]
        embed = discord.Embed(title="🎱 Magic 8-Ball 🎱", color=discord.Color.dark_blue())
        embed.add_field(name="Question", value=question, inline=False)
        embed.add_field(name="Answer", value=random.choice(responses), inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="coinflip", description="Flips a coin.")
    @app_commands.checks.cooldown(1, 3, key=lambda i: i.user.id)
    async def coinflip(self, interaction: discord.Interaction):
        result = random.choice(['Heads', 'Tails'])
        await interaction.response.send_message(f'The coin landed on: **{result}**')

    @app_commands.command(name="roll", description="Rolls a dice in NdN format (e.g., 2d6).")
    @app_commands.describe(dice="The dice to roll (e.g., 1d6, 2d8).")
    @app_commands.checks.cooldown(1, 3, key=lambda i: i.user.id)
    async def roll(self, interaction: discord.Interaction, dice: str):
        try:
            rolls, limit = map(int, dice.lower().split('d'))
        except Exception:
            await interaction.response.send_message('Format has to be in NdN (e.g., 1d6)!', ephemeral=True)
            return

        if not (1 <= rolls <= 100 and 1 <= limit <= 1000):
            await interaction.response.send_message("Please keep rolls between 1-100 and faces between 1-1000.", ephemeral=True)
            return

        results = [random.randint(1, limit) for _ in range(rolls)]
        total = sum(results)
        embed = discord.Embed(title=f"Dice Roll: {dice}", description=f"Total: **{total}**", color=discord.Color.red())
        embed.add_field(name="Individual Rolls", value=', '.join(map(str, results)), inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="guess", description="Starts a 'guess the number' game.")
    @app_commands.checks.cooldown(1, 60, key=lambda i: i.channel_id)
    async def guess(self, interaction: discord.Interaction):
        if interaction.channel.id in self.active_guess_games:
            await interaction.response.send_message("A game is already active in this channel!", ephemeral=True)
            return

        self.active_guess_games.add(interaction.channel.id)
        number_to_guess = random.randint(1, 100)
        attempts = 0
        
        await interaction.response.send_message(f"I've picked a number between 1 and 100. You have 60 seconds to guess it!")

        def check(m):
            return m.channel == interaction.channel and m.author == interaction.user and m.content.isdigit()

        try:
            while True:
                guess_msg = await self.bot.wait_for('message', timeout=60.0, check=check)
                guess = int(guess_msg.content)
                attempts += 1
                if guess < number_to_guess: await guess_msg.reply("Too low! Try again.", delete_after=5)
                elif guess > number_to_guess: await guess_msg.reply("Too high! Try again.", delete_after=5)
                else:
                    await guess_msg.reply(f"🎉 You got it! The number was **{number_to_guess}**. It took you {attempts} attempts.")
                    self.active_guess_games.remove(interaction.channel.id)
                    return
        except asyncio.TimeoutError:
            if interaction.channel.id in self.active_guess_games:
                await interaction.followup.send(f"Time's up! The number was {number_to_guess}.")
                self.active_guess_games.remove(interaction.channel.id)

    @app_commands.command(name="rps", description="Play Rock, Paper, Scissors with the bot.")
    @app_commands.describe(choice="Your choice.")
    @app_commands.choices(choice=[app_commands.Choice(name="Rock", value="rock"), app_commands.Choice(name="Paper", value="paper"), app_commands.Choice(name="Scissors", value="scissors")])
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    async def rockpaperscissors(self, interaction: discord.Interaction, choice: app_commands.Choice[str]):
        user_choice = choice.value
        bot_choice = random.choice(['rock', 'paper', 'scissors'])
        emoji_map = {'rock': '🗿', 'paper': '📄', 'scissors': '✂️'}
        result_text = f"You chose {emoji_map[user_choice]}, I chose {emoji_map[bot_choice]}.\n\n"
        
        if user_choice == bot_choice: result_text += "**It's a tie!**"
        elif (user_choice == 'rock' and bot_choice == 'scissors') or (user_choice == 'paper' and bot_choice == 'rock') or (user_choice == 'scissors' and bot_choice == 'paper'): result_text += "**You win!** 🎉"
        else: result_text += "**I win!** 🤖"
            
        await interaction.response.send_message(result_text)

    @app_commands.command(name="tictactoe", description="Play a game of Tic-Tac-Toe with another member.")
    @app_commands.describe(opponent="The member you want to challenge.")
    @app_commands.checks.cooldown(1, 30, key=lambda i: i.channel_id)
    async def tictactoe(self, interaction: discord.Interaction, opponent: discord.Member):
        if opponent == interaction.user:
            await interaction.response.send_message("You can't play against yourself!", ephemeral=True)
            return
        if opponent.bot:
            await interaction.response.send_message("You can't challenge a bot to a game of Tic-Tac-Toe!", ephemeral=True)
            return
        
        view = TicTacToe(interaction.user, opponent)
        await interaction.response.send_message(f"Tic-Tac-Toe: {interaction.user.name} vs {opponent.name}\nIt's {interaction.user.name}'s turn (X).", view=view)
        view.message = await interaction.original_response()


async def setup(bot: commands.Bot):
    await bot.add_cog(Games(bot))