import discord
from discord.ext import commands
import sqlite3
import random
from datetime import datetime, timedelta

LEVELING_DB = "leveling.db"

def init_leveling_db():
    conn = sqlite3.connect(LEVELING_DB)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER,
            guild_id INTEGER,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            PRIMARY KEY (user_id, guild_id)
        )
    ''')
    conn.commit()
    conn.close()

init_leveling_db()


class Leveling(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.xp_cooldown = {}

    def get_xp_for_level(self, level: int) -> int:
        """Calculate total XP needed for a level."""
        return level * 100

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Award XP on message."""
        if message.author.bot or not message.guild:
            return
        
        user_id = message.author.id
        guild_id = message.guild.id
        
        # Cooldown check (1 XP per 30 seconds max)
        cooldown_key = f"{user_id}_{guild_id}"
        if cooldown_key in self.xp_cooldown:
            if datetime.utcnow() < self.xp_cooldown[cooldown_key]:
                return
        
        self.xp_cooldown[cooldown_key] = datetime.utcnow() + timedelta(seconds=30)
        
        # Award XP (5-15 random)
        xp_gain = random.randint(5, 15)
        
        conn = sqlite3.connect(LEVELING_DB)
        cursor = conn.cursor()
        
        cursor.execute("SELECT level, xp FROM users WHERE user_id = ? AND guild_id = ?", (user_id, guild_id))
        row = cursor.fetchone()
        
        if not row:
            cursor.execute("INSERT INTO users (user_id, guild_id, xp, level) VALUES (?, ?, ?, ?)", 
                          (user_id, guild_id, xp_gain, 1))
        else:
            level, xp = row
            new_xp = xp + xp_gain
            xp_needed = self.get_xp_for_level(level + 1)
            
            if new_xp >= xp_needed:
                new_level = level + 1
                new_xp = 0
                cursor.execute("UPDATE users SET xp = ?, level = ? WHERE user_id = ? AND guild_id = ?",
                              (new_xp, new_level, user_id, guild_id))
                conn.commit()
                
                # Level up notification
                embed = discord.Embed(
                    title="🎉 Level Up!",
                    description=f"{message.author.mention} reached **Level {new_level}**!",
                    color=discord.Color.gold()
                )
                embed.set_thumbnail(url=message.author.avatar.url if message.author.avatar else None)
                await message.channel.send(embed=embed, delete_after=30)
                
                # Award role if exists
                level_role = discord.utils.get(message.guild.roles, name=f"Level {new_level}")
                if level_role:
                    try:
                        await message.author.add_roles(level_role)
                    except:
                        pass
            else:
                cursor.execute("UPDATE users SET xp = ? WHERE user_id = ? AND guild_id = ?",
                              (new_xp, user_id, guild_id))
        
        conn.commit()
        conn.close()

    @commands.command(aliases=['lvl', 'rank'])
    async def level(self, ctx: commands.Context, member: discord.Member = None):
        """Shows your level and XP."""
        if member is None:
            member = ctx.author
        
        conn = sqlite3.connect(LEVELING_DB)
        cursor = conn.cursor()
        cursor.execute("SELECT level, xp FROM users WHERE user_id = ? AND guild_id = ?", (member.id, ctx.guild.id))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            level = 1
            xp = 0
        else:
            level, xp = row
        
        xp_needed = self.get_xp_for_level(level + 1)
        
        embed = discord.Embed(
            title=f"📊 Level Info - {member}",
            color=member.color
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else None)
        embed.add_field(name="Level", value=f"**{level}**", inline=True)
        embed.add_field(name="Current XP", value=f"**{xp}** / **{xp_needed}**", inline=True)
        
        # Progress bar
        progress = int((xp / xp_needed) * 10)
        bar = "█" * progress + "░" * (10 - progress)
        embed.add_field(name="Progress", value=f"`{bar}` {int((xp/xp_needed)*100)}%", inline=False)
        
        await ctx.send(embed=embed)

    @commands.command()
    async def leaderboard(self, ctx: commands.Context, page: int = 1):
        """Shows the XP leaderboard."""
        conn = sqlite3.connect(LEVELING_DB)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, level, xp FROM users WHERE guild_id = ? ORDER BY level DESC, xp DESC LIMIT 10",
                      (ctx.guild.id,))
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return await ctx.send("❌ No users with XP yet!")
        
        embed = discord.Embed(
            title="🏆 Leaderboard",
            color=discord.Color.gold()
        )
        
        for i, (user_id, level, xp) in enumerate(rows, 1):
            user = ctx.guild.get_member(user_id)
            name = user.mention if user else f"<@{user_id}>"
            embed.add_field(
                name=f"#{i} - Level {level}",
                value=f"{name} | {xp} XP",
                inline=False
            )
        
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def addxp(self, ctx: commands.Context, member: discord.Member, amount: int):
        """Admin command to add XP to a user."""
        conn = sqlite3.connect(LEVELING_DB)
        cursor = conn.cursor()
        
        cursor.execute("SELECT level, xp FROM users WHERE user_id = ? AND guild_id = ?", (member.id, ctx.guild.id))
        row = cursor.fetchone()
        
        if not row:
            cursor.execute("INSERT INTO users (user_id, guild_id, xp, level) VALUES (?, ?, ?, ?)",
                          (member.id, ctx.guild.id, amount, 1))
        else:
            level, xp = row
            new_xp = xp + amount
            cursor.execute("UPDATE users SET xp = ? WHERE user_id = ? AND guild_id = ?",
                          (new_xp, member.id, ctx.guild.id))
        
        conn.commit()
        conn.close()
        
        await ctx.send(f"✅ Added {amount} XP to {member.mention}!")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def resetxp(self, ctx: commands.Context, member: discord.Member):
        """Admin command to reset a user's XP."""
        conn = sqlite3.connect(LEVELING_DB)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE user_id = ? AND guild_id = ?", (member.id, ctx.guild.id))
        conn.commit()
        conn.close()
        
        await ctx.send(f"✅ Reset XP for {member.mention}!")


async def setup(bot: commands.Bot):
    await bot.add_cog(Leveling(bot))
