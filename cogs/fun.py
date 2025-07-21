import discord
from discord import app_commands
from discord.ext import commands
import random
import aiohttp
from PIL import Image, ImageDraw, ImageFont
import io
import textwrap

class Fun(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.jokes = [
            "Why don't scientists trust atoms? Because they make up everything!", "I told my wife she should embrace her mistakes. She gave me a hug.", "Why did the scarecrow win an award? Because he was outstanding in his field!", "I'm reading a book on anti-gravity. It's impossible to put down!", "What do you call a fake noodle? An Impasta!", "Why don't skeletons fight each other? They don't have the guts.", "What do you call cheese that isn't yours? Nacho cheese.", "Why did the bicycle fall over? Because it was two-tired.", "How does a penguin build its house? Igloos it together.", "I would tell you a joke about an empty pizza box, but it's too cheesy.", "What do you get when you cross a snowman and a vampire? Frostbite.", "Why are ghosts such bad liars? Because you can see right through them.", "What's orange and sounds like a parrot? A carrot.", "I invented a new word! Plagiarism.", "Did you hear about the mathematician who’s afraid of negative numbers? He’ll stop at nothing to avoid them.", "Why do we tell actors to 'break a leg?' Because every play has a cast.", "Helvetica and Times New Roman walk into a bar. 'Get out of here!' shouts the bartender. 'We don't serve your type.'", "Yesterday I saw a guy spill all his Scrabble letters on the road. I asked him, 'What’s the word on the street?'", "What’s the best thing about Switzerland? I don’t know, but the flag is a big plus.", "Why did the coffee file a police report? It got mugged.", "I'm so good at sleeping, I can do it with my eyes closed.", "Why was the big cat disqualified from the race? Because it was a cheetah.", "What do you call a bear with no teeth? A gummy bear.", "I asked the librarian if the library had any books on paranoia. She whispered, 'They're right behind you!'", "What did the zero say to the eight? Nice belt!", "What did one wall say to the other? I'll meet you at the corner.", "Why did the invisible man turn down the job offer? He couldn't see himself doing it.", "I have a joke about construction, but I'm still working on it.", "I used to play piano by ear, but now I use my hands.", "What do you call a boomerang that won't come back? A stick.", "Why did the golfer bring two pairs of pants? In case he got a hole in one.", "I'm on a seafood diet. I see food, and I eat it.", "What do you call a fish with no eyes? Fsh.", "Parallel lines have so much in common. It’s a shame they’ll never meet.", "My boss told me to have a good day, so I went home.", "Why can't you hear a pterodactyl go to the bathroom? Because the 'P' is silent.", "Why did the stadium get hot after the game? Because all the fans left.", "What's a vampire's favorite fruit? A neck-tarine.", "I don't trust stairs. They're always up to something.", "Why did the scarecrow get a promotion? He was outstanding in his field.", "What's brown and sticky? A stick.", "Why are pirates called pirates? Because they arrrr!", "I was wondering why the frisbee was getting bigger. Then it hit me.", "What do you call a lazy kangaroo? Pouch potato.", "Why was the math book sad? Because it had too many problems.", "What did the grape do when it got stepped on? It let out a little wine.", "Why don’t eggs tell jokes? They’d crack each other up.", "What’s the best way to watch a fly-fishing tournament? Live stream.", "What did the janitor say when he jumped out of the closet? 'Supplies!'", "I'm reading a horror story in Braille. Something bad is about to happen... I can feel it.", "What do you call an alligator in a vest? An investigator.", "If you see a robbery at an Apple Store, does that make you an iWitness?", "What do you call a sad strawberry? A blueberry.", "Why should you never trust a pig with a secret? Because it's bound to squeal.", "I got a new job as a human cannonball. They told me I'd be fired.", "Why did the Oreo go to the dentist? Because it lost its filling.", "How do you organize a space party? You planet.", "What has four wheels and flies? A garbage truck.", "What do you call a thieving alligator? A crook-o-dile.", "I used to be a baker, but I couldn't make enough dough.", "I have a fear of speed bumps. I'm slowly getting over it.", "Where do you learn to make ice cream? At sundae school.", "Why do bees have sticky hair? Because they use a honeycomb.", "How do you make a tissue dance? You put a little boogie in it.", "Why can’t a bicycle stand up by itself? It's two tired.", "Why did the tomato turn red? Because it saw the salad dressing!", "What do you call a pony with a cough? A little hoarse.", "Why was the belt arrested? For holding up a pair of pants.", "How do you find Will Smith in the snow? You look for the fresh prints.", "What do you call a man with a rubber toe? Roberto.", "Why is it annoying to eat next to basketball players? They're always dribbling.", "What do you call a factory that makes okay products? A satisfactory.", "I'm terrified of elevators. I'm going to start taking steps to avoid them.", "What do you call a dog that does magic tricks? A labracadabrador.", "What did the drummer call his twin daughters? Anna one, Anna two!", "Why did the cow go to outer space? To see the moooon.", "What do you call a sleeping bull? A bulldozer.", "Why did the can crusher quit his job? It was soda pressing.", "Why did the man get fired from the calendar factory? He took a couple of days off.", "What's the difference between a hippo and a zippo? One is really heavy, the other is a little lighter.", "I was going to tell a time-traveling joke, but you guys didn't like it.", "What do you get from a pampered cow? Spoiled milk.", "Why did the octopus beat the shark in a fight? Because it was well-armed.", "Why was the baby strawberry crying? Because its parents were in a jam."
        ]

    async def cog_unload(self):
        await self.session.close()

    @app_commands.command(name="joke", description="Tells a random joke.")
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    async def joke(self, interaction: discord.Interaction):
        embed = discord.Embed(title="Here's a joke for you!", description=random.choice(self.jokes), color=discord.Color.orange())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="fact", description="Get a random interesting fact.")
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    async def fact(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            async with self.session.get("https://uselessfacts.jsph.pl/random.json?language=en") as response:
                if response.status == 200:
                    data = await response.json()
                    embed = discord.Embed(title="Did you know?", description=data.get('text'), color=discord.Color.cyan())
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send("Could not fetch a fact right now, try again later.", ephemeral=True)
        except Exception:
            await interaction.followup.send("An error occurred while trying to get a fact.", ephemeral=True)

    @app_commands.command(name="avatar", description="Displays a user's avatar.")
    @app_commands.describe(member="The member whose avatar you want to see.")
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    async def avatar(self, interaction: discord.Interaction, member: discord.Member = None):
        target_member = member or interaction.user
        embed = discord.Embed(title=f"{target_member.name}'s Avatar", color=target_member.color)
        embed.set_image(url=target_member.display_avatar.url)
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name="love", description="Calculates the love compatibility between two members.")
    @app_commands.describe(member1="The first person.", member2="The second person.")
    @app_commands.checks.cooldown(1, 10, key=lambda i: i.user.id)
    async def love(self, interaction: discord.Interaction, member1: discord.Member, member2: discord.Member = None):
        target_member2 = member2 or interaction.user
        random.seed(member1.id + target_member2.id)
        love_percentage = random.randint(0, 100)
        random.seed()

        emoji = "💔"
        if 40 <= love_percentage < 75: emoji = "❤️"
        elif love_percentage >= 75: emoji = "💖"

        embed = discord.Embed(title="Love Calculator", color=discord.Color.red())
        embed.description = f"**{member1.name}** + **{target_member2.name}** = **{love_percentage}%** {emoji}"
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="emojify", description="Converts your text into emojis.")
    @app_commands.describe(text="The text to convert.")
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    async def emojify(self, interaction: discord.Interaction, text: str):
        if len(text) > 50:
            await interaction.response.send_message("Text is too long! Please keep it under 50 characters.", ephemeral=True)
            return
        emojis = ""
        for char in text.lower():
            if char.isalpha():
                emojis += f":regional_indicator_{char}: "
            elif char.isdigit():
                num_map = {'0': 'zero', '1': 'one', '2': 'two', '3': 'three', '4': 'four', 
                           '5': 'five', '6': 'six', '7': 'seven', '8': 'eight', '9': 'nine'}
                emojis += f":{num_map[char]}: "
            else:
                emojis += " "
        
        if emojis.strip(): await interaction.response.send_message(emojis)
        else: await interaction.response.send_message("Could not emojify the text.", ephemeral=True)

    @app_commands.command(name="poll", description="Creates a poll with up to 10 options.")
    @app_commands.describe(question="The question for the poll.", option1="The first choice.", option2="The second choice.", option3="Optional third choice.", option4="Optional fourth choice.", option5="Optional fifth choice.", option6="Optional sixth choice.", option7="Optional seventh choice.", option8="Optional eighth choice.", option9="Optional ninth choice.", option10="Optional tenth choice.")
    @app_commands.checks.cooldown(1, 15, key=lambda i: i.channel_id)
    async def poll(self, interaction: discord.Interaction, question: str, option1: str, option2: str, option3: str=None, option4: str=None, option5: str=None, option6: str=None, option7: str=None, option8: str=None, option9: str=None, option10: str=None):
        options = [opt for opt in [option1, option2, option3, option4, option5, option6, option7, option8, option9, option10] if opt is not None]
        reactions = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
        description = [f"{reactions[i]} {option}" for i, option in enumerate(options)]
        embed = discord.Embed(title=question, description="\n".join(description), color=discord.Color.blurple())
        embed.set_footer(text=f"Poll created by {interaction.user.name}")
        await interaction.response.send_message(embed=embed)
        poll_message = await interaction.original_response()
        for i in range(len(options)):
            await poll_message.add_reaction(reactions[i])

    @app_commands.command(name="clap", description="Adds a clap emoji between each word.")
    @app_commands.describe(text="The text to clapify.")
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    async def clap(self, interaction: discord.Interaction, text: str):
        if len(text.split()) < 2:
            await interaction.response.send_message("You need at least two words to clap!", ephemeral=True)
            return
        clapped_text = " 👏 ".join(text.split())
        await interaction.response.send_message(clapped_text)
        
    @app_commands.command(name="tweet", description="Generate an image of a fake tweet.")
    @app_commands.describe(text="The content of the tweet (max 280 chars).")
    @app_commands.checks.cooldown(1, 15, key=lambda i: i.user.id)
    async def tweet(self, interaction: discord.Interaction, text: str):
        await interaction.response.defer()
        
        if len(text) > 280:
            await interaction.followup.send("Tweet text cannot exceed 280 characters.", ephemeral=True)
            return

        user = interaction.user
        bg = Image.new('RGB', (1000, 400), color=(21, 32, 43))
        
        try:
            async with self.session.get(user.display_avatar.url) as response:
                if response.status == 200:
                    avatar_data = await response.read()
                    avatar = Image.open(io.BytesIO(avatar_data)).convert("RGBA")
                    avatar = avatar.resize((150, 150))
                    
                    mask = Image.new('L', avatar.size, 0)
                    draw_mask = ImageDraw.Draw(mask)
                    draw_mask.ellipse((0, 0) + avatar.size, fill=255)
                    bg.paste(avatar, (50, 50), mask)
        except Exception as e:
            print(f"Tweet avatar error: {e}")

        draw = ImageDraw.Draw(bg)
        try:
            font_bold = ImageFont.truetype("arialbd.ttf", 60)
            font_regular = ImageFont.truetype("arial.ttf", 50)
            font_handle = ImageFont.truetype("arial.ttf", 45)
        except IOError:
            print("Arial font not found, using default font for tweet command.")
            font_bold = ImageFont.load_default(size=60)
            font_regular = ImageFont.load_default(size=50)
            font_handle = ImageFont.load_default(size=45)

        draw.text((230, 60), user.display_name, font=font_bold, fill=(255, 255, 255))
        draw.text((230, 125), f"@{user.name}", font=font_handle, fill=(136, 153, 166))
        
        wrapped_text = textwrap.fill(text, width=35)
        draw.text((50, 230), wrapped_text, font=font_regular, fill=(255, 255, 255))

        buffer = io.BytesIO()
        bg.save(buffer, format='PNG')
        buffer.seek(0)
        
        await interaction.followup.send(file=discord.File(buffer, 'tweet.png'))

async def setup(bot: commands.Bot):
    await bot.add_cog(Fun(bot))