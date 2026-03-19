import discord
from discord.ext import commands
from discord.ext.commands import clean_content

NUMBER_EMOJIS = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']


class Polls(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command()
    async def poll(self, ctx: commands.Context, *, question: str = None):
        """Create a poll. Format: !poll question | option1 | option2 | option3"""
        
        if not question or '|' not in question:
            return await ctx.send("❌ Format: `!poll question | option1 | option2 | option3`")
        
        parts = [p.strip() for p in question.split('|')]
        
        if len(parts) < 3:
            return await ctx.send("❌ You need at least a question and 2 options!")
        
        poll_question = parts[0]
        options = parts[1:]
        
        if len(options) > 10:
            return await ctx.send("❌ Maximum 10 options allowed!")
        
        embed = discord.Embed(
            title="📊 Poll",
            description=poll_question,
            color=discord.Color.blurple()
        )
        
        for i, option in enumerate(options):
            embed.add_field(name=f"{NUMBER_EMOJIS[i]} Option {i+1}", value=option, inline=False)
        
        embed.set_footer(text=f"Poll by {ctx.author.name}")
        
        message = await ctx.send(embed=embed)
        
        # Add reaction emojis
        for i in range(len(options)):
            await message.add_reaction(NUMBER_EMOJIS[i])

    @commands.command()
    async def quickpoll(self, ctx: commands.Context, *, question: str):
        """Create a quick yes/no poll."""
        embed = discord.Embed(
            title="📊 Quick Poll",
            description=question,
            color=discord.Color.blurple()
        )
        embed.set_footer(text=f"Poll by {ctx.author.name}")
        
        message = await ctx.send(embed=embed)
        await message.add_reaction("✅")
        await message.add_reaction("❌")


async def setup(bot: commands.Bot):
    await bot.add_cog(Polls(bot))
