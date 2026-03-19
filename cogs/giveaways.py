import discord
from discord.ext import commands
import asyncio
import random
from datetime import datetime, timedelta
import sqlite3

GIVEAWAY_DB = "giveaways.db"

def init_giveaway_db():
    conn = sqlite3.connect(GIVEAWAY_DB)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS giveaways (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            message_id INTEGER,
            channel_id INTEGER,
            prize TEXT,
            winners INTEGER,
            end_time TEXT,
            creator_id INTEGER
        )
    ''')
    conn.commit()
    conn.close()

init_giveaway_db()


class Giveaways(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_giveaways = {}

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def giveaway(self, ctx: commands.Context, duration: str, winners: int, *, prize: str):
        """Start a giveaway. Duration format: 10m, 1h, 1d"""
        
        # Parse duration
        time_unit = duration[-1]
        try:
            time_amount = int(duration[:-1])
        except:
            return await ctx.send("❌ Invalid duration! Use format: 10m, 1h, 1d")
        
        if time_unit == 'm':
            delta = timedelta(minutes=time_amount)
        elif time_unit == 'h':
            delta = timedelta(hours=time_amount)
        elif time_unit == 'd':
            delta = timedelta(days=time_amount)
        else:
            return await ctx.send("❌ Invalid time unit! Use m (minutes), h (hours), or d (days)")
        
        end_time = datetime.utcnow() + delta
        
        embed = discord.Embed(
            title="🎁 Giveaway!",
            description=f"**Prize:** {prize}\n**Winners:** {winners}\n\nReact with 🎉 to enter!",
            color=discord.Color.gold()
        )
        embed.set_footer(text=f"Ends at {end_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        
        message = await ctx.send(embed=embed)
        await message.add_reaction("🎉")
        
        # Store in database
        conn = sqlite3.connect(GIVEAWAY_DB)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO giveaways (guild_id, message_id, channel_id, prize, winners, end_time, creator_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (ctx.guild.id, message.id, ctx.channel.id, prize, winners, end_time.isoformat(), ctx.author.id)
        )
        conn.commit()
        conn.close()
        
        # Wait for giveaway to end
        seconds_until_end = (end_time - datetime.utcnow()).total_seconds()
        await asyncio.sleep(seconds_until_end)
        
        # Fetch message and get reactions
        try:
            message = await ctx.channel.fetch_message(message.id)
        except:
            return
        
        # Get all users who reacted
        participants = []
        for reaction in message.reactions:
            if str(reaction.emoji) == "🎉":
                async for user in reaction.users():
                    if not user.bot:
                        participants.append(user)
        
        if len(participants) == 0:
            embed = discord.Embed(
                title="❌ Giveaway Ended",
                description=f"**Prize:** {prize}\n**Result:** No participants!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        else:
            selected_winners = random.sample(participants, min(winners, len(participants)))
            
            winner_mentions = ", ".join([winner.mention for winner in selected_winners])
            
            embed = discord.Embed(
                title="🎊 Giveaway Ended!",
                description=f"**Prize:** {prize}\n**Winners:** {winner_mentions}",
                color=discord.Color.green()
            )
            
            await ctx.send(embed=embed)
            
            # Try to DM winners
            for winner in selected_winners:
                try:
                    await winner.send(f"🎉 Congratulations! You won **{prize}** in {ctx.guild.name}!")
                except:
                    pass
        
        # Remove from database
        conn = sqlite3.connect(GIVEAWAY_DB)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM giveaways WHERE message_id = ?", (message.id,))
        conn.commit()
        conn.close()

    @commands.command()
    async def giveaways(self, ctx: commands.Context):
        """List active giveaways."""
        conn = sqlite3.connect(GIVEAWAY_DB)
        cursor = conn.cursor()
        cursor.execute("SELECT prize, winners, end_time FROM giveaways WHERE guild_id = ?", (ctx.guild.id,))
        giveaways = cursor.fetchall()
        conn.close()
        
        if not giveaways:
            return await ctx.send("❌ No active giveaways!")
        
        embed = discord.Embed(
            title="🎁 Active Giveaways",
            color=discord.Color.gold()
        )
        
        for prize, winners, end_time in giveaways:
            embed.add_field(
                name=prize,
                value=f"**Winners:** {winners}\n**Ends:** {end_time}",
                inline=False
            )
        
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Giveaways(bot))
