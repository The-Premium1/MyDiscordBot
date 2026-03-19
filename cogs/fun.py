import discord
from discord.ext import commands
import random
import aiohttp
import json

JOKES = [
    "Why did the scarecrow win an award? He was outstanding in his field!",
    "I told my computer I needed a break, and now it won't stop sending me Kit-Kat ads.",
    "Why don't scientists trust atoms? Because they make up everything!",
    "Did you hear about the guy who invented Lifesavers? He made a mint!",
    "What do you call fake spaghetti? An impasta!",
]

QUOTES = [
    "The only way to do great work is to love what you do. - Steve Jobs",
    "Innovation distinguishes between a leader and a follower. - Steve Jobs",
    "Life is what happens when you're busy making other plans. - John Lennon",
    "The future belongs to those who believe in the beauty of their dreams. - Eleanor Roosevelt",
    "It is during our darkest moments that we must focus to see the light. - Aristotle",
]

INSULTS = [
    "You are proof that evolution can go in reverse!",
    "Your family tree must be a cactus because everybody on it is a prick.",
    "Your brain is like a state prison, nobody's home.",
]


class Fun(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command()
    async def joke(self, ctx: commands.Context):
        """Tell a random joke."""
        joke = random.choice(JOKES)
        embed = discord.Embed(
            title="😄 Joke",
            description=joke,
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def quote(self, ctx: commands.Context):
        """Get an inspirational quote."""
        quote = random.choice(QUOTES)
        embed = discord.Embed(
            title="💭 Quote",
            description=quote,
            color=discord.Color.blurple()
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def meme(self, ctx: commands.Context):
        """Get a random meme from r/memes."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('https://meme-api.com/gimme') as r:
                    data = await r.json()
                    
                    embed = discord.Embed(
                        title=data['title'],
                        color=discord.Color.random()
                    )
                    embed.set_image(url=data['url'])
                    embed.set_footer(text=f"👍 {data['ups']} | 💬 {data['comments']}")
                    
                    await ctx.send(embed=embed)
        except:
            await ctx.send("❌ Error fetching meme!")

    @commands.command()
    async def avatar(self, ctx: commands.Context, member: discord.Member = None):
        """Show a member's avatar."""
        if member is None:
            member = ctx.author
        
        embed = discord.Embed(
            title=f"👤 {member}'s Avatar",
            color=member.color
        )
        embed.set_image(url=member.avatar.url if member.avatar else member.default_avatar.url)
        embed.add_field(name="Download", value=f"[Full Size]({member.avatar.url if member.avatar else member.default_avatar.url})")
        
        await ctx.send(embed=embed)

    @commands.command(aliases=['8ball'])
    async def eightball(self, ctx: commands.Context, *, question: str):
        """Magic 8-ball answers a yes/no question."""
        responses = [
            "Yes, definitely!",
            "No way!",
            "Maybe...",
            "Ask again later.",
            "Absolutely!",
            "Nope!",
            "Without a doubt!",
            "Doesn't look good.",
        ]
        
        embed = discord.Embed(
            title="🎱 Magic 8-Ball",
            color=discord.Color.purple()
        )
        embed.add_field(name="Question", value=question, inline=False)
        embed.add_field(name="Answer", value=random.choice(responses), inline=False)
        
        await ctx.send(embed=embed)

    @commands.command()
    async def dice(self, ctx: commands.Context, sides: int = 6):
        """Roll a dice."""
        if sides < 2:
            return await ctx.send("❌ Dice must have at least 2 sides!")
        
        result = random.randint(1, sides)
        embed = discord.Embed(
            title="🎲 Dice Roll",
            description=f"**{result}** / {sides}",
            color=discord.Color.random()
        )
        await ctx.send(embed=embed)

    @commands.command(aliases=['flip', 'coinflip'])
    async def coin(self, ctx: commands.Context):
        """Flip a coin."""
        result = random.choice(["Heads 🪙", "Tails 🪙"])
        embed = discord.Embed(
            title="🪙 Coin Flip",
            description=result,
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)

    @commands.command(aliases=['rps'])
    async def rockpaperscissors(self, ctx: commands.Context, choice: str):
        """Play rock paper scissors."""
        choices = ["rock", "paper", "scissors"]
        choice = choice.lower()
        
        if choice not in choices:
            return await ctx.send("❌ Choose: rock, paper, or scissors!")
        
        bot_choice = random.choice(choices)
        
        if choice == bot_choice:
            result = "🤝 It's a tie!"
        elif (choice == "rock" and bot_choice == "scissors") or \
             (choice == "paper" and bot_choice == "rock") or \
             (choice == "scissors" and bot_choice == "paper"):
            result = "✅ You won!"
        else:
            result = "❌ I won!"
        
        embed = discord.Embed(
            title="🎮 Rock Paper Scissors",
            color=discord.Color.random()
        )
        embed.add_field(name="Your Choice", value=f"**{choice}**", inline=True)
        embed.add_field(name="My Choice", value=f"**{bot_choice}**", inline=True)
        embed.add_field(name="Result", value=result, inline=False)
        
        await ctx.send(embed=embed)

    @commands.command()
    async def insult(self, ctx: commands.Context, member: discord.Member = None):
        """Roast someone (jokingly)."""
        if member is None:
            member = ctx.author
        
        insult = random.choice(INSULTS)
        embed = discord.Embed(
            title="🔥 Roast",
            description=f"{member.mention}\n\n{insult}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Fun(bot))
