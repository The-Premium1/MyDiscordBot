import discord
from discord.ext import commands
import asyncio
from datetime import datetime, timedelta
import sqlite3

REMINDERS_DB = "reminders.db"

def init_reminders_db():
    conn = sqlite3.connect(REMINDERS_DB)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            reminder_text TEXT,
            remind_time TEXT,
            created_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_reminders_db()


class Reminders(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.load_reminders()

    def load_reminders(self):
        """Load all active reminders from database."""
        conn = sqlite3.connect(REMINDERS_DB)
        cursor = conn.cursor()
        cursor.execute("SELECT id, user_id, reminder_text, remind_time FROM reminders")
        reminders = cursor.fetchall()
        conn.close()
        
        for reminder_id, user_id, text, remind_time in reminders:
            self.bot.loop.create_task(self.reminder_task(reminder_id, user_id, text, remind_time))

    async def reminder_task(self, reminder_id: int, user_id: int, text: str, remind_time: str):
        """Task that waits and sends reminder."""
        try:
            remind_dt = datetime.fromisoformat(remind_time)
            now = datetime.utcnow()
            
            if remind_dt <= now:
                # Already passed, delete it
                conn = sqlite3.connect(REMINDERS_DB)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
                conn.commit()
                conn.close()
                return
            
            # Wait until reminder time
            seconds = (remind_dt - now).total_seconds()
            await asyncio.sleep(seconds)
            
            # Send reminder
            user = await self.bot.fetch_user(user_id)
            
            embed = discord.Embed(
                title="⏰ Reminder",
                description=text,
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            await user.send(embed=embed)
            
            # Delete from database
            conn = sqlite3.connect(REMINDERS_DB)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error in reminder task: {e}")

    @commands.command()
    async def remind(self, ctx: commands.Context, duration: str, *, text: str):
        """Set a reminder. Duration format: 10m, 1h, 1d"""
        
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
        
        remind_time = datetime.utcnow() + delta
        
        # Store in database
        conn = sqlite3.connect(REMINDERS_DB)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO reminders (user_id, reminder_text, remind_time, created_at) VALUES (?, ?, ?, ?)",
            (ctx.author.id, text, remind_time.isoformat(), datetime.utcnow().isoformat())
        )
        reminder_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        embed = discord.Embed(
            title="⏰ Reminder Set",
            description=f"**Text:** {text}\n**Time:** {remind_time.strftime('%Y-%m-%d %H:%M:%S')}",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        
        # Start reminder task
        self.bot.loop.create_task(self.reminder_task(reminder_id, ctx.author.id, text, remind_time.isoformat()))

    @commands.command()
    async def reminders(self, ctx: commands.Context):
        """Show your active reminders."""
        conn = sqlite3.connect(REMINDERS_DB)
        cursor = conn.cursor()
        cursor.execute("SELECT id, reminder_text, remind_time FROM reminders WHERE user_id = ? ORDER BY remind_time ASC",
                      (ctx.author.id,))
        reminders = cursor.fetchall()
        conn.close()
        
        if not reminders:
            return await ctx.send("✅ No active reminders!")
        
        embed = discord.Embed(
            title="⏰ Your Reminders",
            color=discord.Color.blue()
        )
        
        for reminder_id, text, remind_time in reminders:
            time_left = (datetime.fromisoformat(remind_time) - datetime.utcnow()).total_seconds()
            
            if time_left < 60:
                time_str = f"{int(time_left)}s"
            elif time_left < 3600:
                time_str = f"{int(time_left/60)}m"
            else:
                time_str = f"{int(time_left/3600)}h"
            
            embed.add_field(
                name=f"#{reminder_id} - {text[:50]}",
                value=f"In **{time_str}**",
                inline=False
            )
        
        await ctx.send(embed=embed)

    @commands.command()
    async def removereminder(self, ctx: commands.Context, reminder_id: int):
        """Remove a reminder."""
        conn = sqlite3.connect(REMINDERS_DB)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM reminders WHERE id = ? AND user_id = ?", (reminder_id, ctx.author.id))
        if cursor.rowcount == 0:
            await ctx.send("❌ Reminder not found!")
        else:
            await ctx.send("✅ Reminder removed!")
        conn.commit()
        conn.close()


async def setup(bot: commands.Bot):
    await bot.add_cog(Reminders(bot))
