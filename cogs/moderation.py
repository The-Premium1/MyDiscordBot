import discord
from discord.ext import commands
import asyncio
import sqlite3
from datetime import datetime, timedelta

# Initialize SQLite database for warnings
DB_PATH = "warnings.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS warnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            guild_id INTEGER,
            moderator_id INTEGER,
            reason TEXT,
            timestamp TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def is_mod_or_admin(self, member: discord.Member) -> bool:
        """Check if member has mod/admin permissions."""
        return member.guild_permissions.administrator or member.guild_permissions.moderate_members

    async def log_action(self, guild_id: int, action: str, moderator: discord.Member, target: discord.Member, reason: str = None):
        """Log moderation action to logs channel if it exists."""
        # Find logs channel
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return
        
        logs_channel = discord.utils.get(guild.text_channels, name="mod-logs")
        if not logs_channel:
            return
        
        embed = discord.Embed(
            title=f"📋 {action} Executed",
            color=discord.Color.red() if action in ["Ban", "Kick", "Mute"] else discord.Color.orange(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Target", value=f"{target.mention} ({target.id})", inline=False)
        embed.add_field(name="Moderator", value=f"{moderator.mention} ({moderator.id})", inline=False)
        if reason:
            embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_thumbnail(url=target.avatar.url if target.avatar else None)
        
        try:
            await logs_channel.send(embed=embed)
        except Exception as e:
            print(f"Error logging action: {e}")

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        """Kicks a member from the server."""
        if not await self.is_mod_or_admin(ctx.author):
            return await ctx.send("❌ You don't have permission to kick members!")
        
        if member == ctx.author:
            return await ctx.send("❌ You can't kick yourself!")
        
        if member.top_role >= ctx.author.top_role:
            return await ctx.send("❌ You can't kick someone with equal or higher role!")
        
        try:
            await member.send(f"You were kicked from **{ctx.guild.name}** for: {reason}")
        except:
            pass
        
        await member.kick(reason=reason)
        await ctx.send(f"✅ **{member}** has been kicked!\n**Reason:** {reason}")
        await self.log_action(ctx.guild.id, "Kick", ctx.author, member, reason)

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        """Bans a member from the server."""
        if not await self.is_mod_or_admin(ctx.author):
            return await ctx.send("❌ You don't have permission to ban members!")
        
        if member == ctx.author:
            return await ctx.send("❌ You can't ban yourself!")
        
        if member.top_role >= ctx.author.top_role:
            return await ctx.send("❌ You can't ban someone with equal or higher role!")
        
        try:
            await member.send(f"You were banned from **{ctx.guild.name}** for: {reason}")
        except:
            pass
        
        await member.ban(reason=reason)
        await ctx.send(f"🚫 **{member}** has been banned!\n**Reason:** {reason}")
        await self.log_action(ctx.guild.id, "Ban", ctx.author, member, reason)

    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def mute(self, ctx: commands.Context, member: discord.Member, duration: str = "10m", *, reason: str = "No reason provided"):
        """Mutes a member temporarily. Duration: 10m, 1h, 1d, etc."""
        if not await self.is_mod_or_admin(ctx.author):
            return await ctx.send("❌ You don't have permission to mute members!")
        
        if member == ctx.author:
            return await ctx.send("❌ You can't mute yourself!")
        
        if member.top_role >= ctx.author.top_role:
            return await ctx.send("❌ You can't mute someone with equal or higher role!")
        
        # Parse duration
        time_unit = duration[-1]
        try:
            time_amount = int(duration[:-1])
        except:
            return await ctx.send("❌ Invalid duration! Use format: 10m, 1h, 1d")
        
        if time_unit == 'm':
            mute_time = timedelta(minutes=time_amount)
        elif time_unit == 'h':
            mute_time = timedelta(hours=time_amount)
        elif time_unit == 'd':
            mute_time = timedelta(days=time_amount)
        else:
            return await ctx.send("❌ Invalid time unit! Use m (minutes), h (hours), or d (days)")
        
        try:
            await member.timeout(mute_time, reason=reason)
            await ctx.send(f"🔇 **{member}** has been muted for **{duration}**!\n**Reason:** {reason}")
            await self.log_action(ctx.guild.id, "Mute", ctx.author, member, f"{reason} (Duration: {duration})")
        except Exception as e:
            await ctx.send(f"❌ Error muting member: {e}")

    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def unmute(self, ctx: commands.Context, member: discord.Member):
        """Unmutes a member."""
        if not await self.is_mod_or_admin(ctx.author):
            return await ctx.send("❌ You don't have permission to unmute members!")
        
        try:
            await member.timeout(None)
            await ctx.send(f"🔊 **{member}** has been unmuted!")
            await self.log_action(ctx.guild.id, "Unmute", ctx.author, member)
        except Exception as e:
            await ctx.send(f"❌ Error unmuting member: {e}")

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def softban(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        """Softbans a member (kicks and deletes messages from last 7 days)."""
        if not await self.is_mod_or_admin(ctx.author):
            return await ctx.send("❌ You don't have permission to softban members!")
        
        if member == ctx.author:
            return await ctx.send("❌ You can't softban yourself!")
        
        if member.top_role >= ctx.author.top_role:
            return await ctx.send("❌ You can't softban someone with equal or higher role!")
        
        try:
            await member.send(f"You were softbanned from **{ctx.guild.name}** for: {reason}")
        except:
            pass
        
        await member.ban(reason=reason, delete_message_seconds=7*24*60*60)  # Delete messages from last 7 days
        await asyncio.sleep(1)
        await ctx.guild.unban(member, reason=f"Softban: {reason}")
        
        await ctx.send(f"⚠️ **{member}** has been softbanned!\n**Reason:** {reason}")
        await self.log_action(ctx.guild.id, "Softban", ctx.author, member, reason)

    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def warn(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        """Warns a member and stores the warning."""
        if not await self.is_mod_or_admin(ctx.author):
            return await ctx.send("❌ You don't have permission to warn members!")
        
        if member == ctx.author:
            return await ctx.send("❌ You can't warn yourself!")
        
        # Store warning in database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO warnings (user_id, guild_id, moderator_id, reason, timestamp) VALUES (?, ?, ?, ?, ?)",
            (member.id, ctx.guild.id, ctx.author.id, reason, datetime.utcnow().isoformat())
        )
        conn.commit()
        conn.close()
        
        # Get total warnings
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM warnings WHERE user_id = ? AND guild_id = ?", (member.id, ctx.guild.id))
        total_warns = cursor.fetchone()[0]
        conn.close()
        
        await ctx.send(f"⚠️ **{member}** has been warned!\n**Reason:** {reason}\n**Total Warnings:** {total_warns}")
        await self.log_action(ctx.guild.id, "Warn", ctx.author, member, reason)
        
        try:
            await member.send(f"You received a warning in **{ctx.guild.name}** for: {reason}")
        except:
            pass

    @commands.command(aliases=['warnings', 'w'])
    async def warns(self, ctx: commands.Context, member: discord.Member = None):
        """Shows warnings for a member."""
        if member is None:
            member = ctx.author
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT moderator_id, reason, timestamp FROM warnings WHERE user_id = ? AND guild_id = ? ORDER BY timestamp DESC",
            (member.id, ctx.guild.id)
        )
        warns = cursor.fetchall()
        conn.close()
        
        if not warns:
            return await ctx.send(f"✅ **{member}** has no warnings!")
        
        embed = discord.Embed(
            title=f"⚠️ Warnings for {member}",
            description=f"Total: **{len(warns)}** warnings",
            color=discord.Color.orange()
        )
        
        for i, (mod_id, reason, timestamp) in enumerate(warns, 1):
            mod = ctx.guild.get_member(mod_id)
            mod_name = mod.mention if mod else f"<@{mod_id}>"
            embed.add_field(
                name=f"Warning #{i}",
                value=f"**Moderator:** {mod_name}\n**Reason:** {reason}\n**Date:** {timestamp.split('T')[0]}",
                inline=False
            )
        
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx: commands.Context, *, user: str):
        """Unbans a user. Use: !unban username#0000 or user_id"""
        if not await self.is_mod_or_admin(ctx.author):
            return await ctx.send("❌ You don't have permission to unban members!")
        
        try:
            # Try to parse as ID first
            user_id = int(user)
            ban_entry = None
            async for entry in ctx.guild.bans():
                if entry.user.id == user_id:
                    ban_entry = entry
                    break
            
            if not ban_entry:
                return await ctx.send("❌ User not found in ban list!")
            
            await ctx.guild.unban(ban_entry.user, reason=f"Unbanned by {ctx.author}")
            await ctx.send(f"✅ **{ban_entry.user}** has been unbanned!")
            await self.log_action(ctx.guild.id, "Unban", ctx.author, ban_entry.user)
        except ValueError:
            # Try as username
            async for entry in ctx.guild.bans():
                if str(entry.user) == user or entry.user.name == user:
                    await ctx.guild.unban(entry.user, reason=f"Unbanned by {ctx.author}")
                    await ctx.send(f"✅ **{entry.user}** has been unbanned!")
                    await self.log_action(ctx.guild.id, "Unban", ctx.author, entry.user)
                    return
            
            await ctx.send("❌ User not found!")

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def banlist(self, ctx: commands.Context):
        """Shows all banned users."""
        bans = await ctx.guild.bans()
        
        if not bans:
            return await ctx.send("✅ No banned users!")
        
        embed = discord.Embed(
            title=f"🚫 Banned Users ({len(bans)})",
            color=discord.Color.red()
        )
        
        ban_list = []
        for entry in bans:
            ban_list.append(f"**{entry.user}** ({entry.user.id})\nReason: {entry.reason or 'No reason'}")
        
        # Split into chunks of 5 to avoid embed field limits
        for i in range(0, len(ban_list), 5):
            chunk = "\n\n".join(ban_list[i:i+5])
            embed.add_field(name=f"Bans {i+1}-{min(i+5, len(ban_list))}", value=chunk, inline=False)
        
        await ctx.send(embed=embed)

    @commands.command()
    async def userinfo(self, ctx: commands.Context, member: discord.Member = None):
        """Shows user info and moderation history."""
        if member is None:
            member = ctx.author
        
        embed = discord.Embed(
            title=f"👤 User Info - {member}",
            color=member.color,
            timestamp=datetime.utcnow()
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else None)
        
        embed.add_field(name="User ID", value=member.id, inline=True)
        embed.add_field(name="Account Created", value=member.created_at.strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="Joined Server", value=member.joined_at.strftime("%Y-%m-%d") if member.joined_at else "Unknown", inline=True)
        embed.add_field(name="Status", value=str(member.status), inline=True)
        embed.add_field(name="Bot", value="Yes ✅" if member.bot else "No", inline=True)
        
        roles = [r.mention for r in member.roles if r.name != "@everyone"]
        embed.add_field(name=f"Roles ({len(roles)})", value=", ".join(roles) if roles else "No roles", inline=False)
        
        # Get warnings count
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM warnings WHERE user_id = ? AND guild_id = ?", (member.id, ctx.guild.id))
        warns = cursor.fetchone()[0]
        conn.close()
        
        embed.add_field(name="⚠️ Warnings", value=str(warns), inline=True)
        embed.add_field(name="🔇 Muted", value="Yes" if member.is_timed_out() else "No", inline=True)
        
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def purge(self, ctx: commands.Context, amount: int = 10):
        """Deletes the last X messages in channel."""
        if amount < 1 or amount > 100:
            return await ctx.send("❌ Purge amount must be between 1 and 100!")
        
        deleted = await ctx.channel.purge(limit=amount)
        await ctx.send(f"🧹 Deleted {len(deleted)} messages!", delete_after=5)
        await self.log_action(ctx.guild.id, "Purge", ctx.author, ctx.author, f"Deleted {len(deleted)} messages in {ctx.channel.mention}")

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def lockdown(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """Locks a channel (mutes @everyone)."""
        if channel is None:
            channel = ctx.channel
        
        try:
            overwrite = channel.overwrites_for(ctx.guild.default_role)
            overwrite.send_messages = False
            await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
            await ctx.send(f"🔒 **{channel.mention}** has been locked!")
            await self.log_action(ctx.guild.id, "Lockdown", ctx.author, ctx.author, f"Locked {channel.mention}")
        except Exception as e:
            await ctx.send(f"❌ Error locking channel: {e}")

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """Unlocks a channel."""
        if channel is None:
            channel = ctx.channel
        
        try:
            overwrite = channel.overwrites_for(ctx.guild.default_role)
            overwrite.send_messages = None
            await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
            await ctx.send(f"🔓 **{channel.mention}** has been unlocked!")
            await self.log_action(ctx.guild.id, "Unlock", ctx.author, ctx.author, f"Unlocked {channel.mention}")
        except Exception as e:
            await ctx.send(f"❌ Error unlocking channel: {e}")

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx: commands.Context, seconds: int = 0):
        """Sets slowmode. Use 0 to disable."""
        if seconds < 0 or seconds > 21600:  # 6 hours max
            return await ctx.send("❌ Slowmode must be between 0 and 21600 seconds!")
        
        try:
            await ctx.channel.edit(slowmode_delay=seconds)
            if seconds == 0:
                await ctx.send("✅ Slowmode disabled!")
            else:
                await ctx.send(f"⏱️ Slowmode set to {seconds}s!")
            await self.log_action(ctx.guild.id, "Slowmode", ctx.author, ctx.author, f"Set to {seconds}s")
        except Exception as e:
            await ctx.send(f"❌ Error: {e}")

    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def history(self, ctx: commands.Context, member: discord.Member):
        """Shows moderation history for a member."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT moderator_id, reason, timestamp FROM warnings WHERE user_id = ? AND guild_id = ? ORDER BY timestamp DESC LIMIT 10",
            (member.id, ctx.guild.id)
        )
        warns = cursor.fetchall()
        conn.close()
        
        embed = discord.Embed(
            title=f"📋 Moderation History - {member}",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        
        if not warns:
            embed.description = "✅ No moderation history!"
        else:
            for i, (mod_id, reason, timestamp) in enumerate(warns, 1):
                mod = ctx.guild.get_member(mod_id)
                mod_name = mod.mention if mod else f"<@{mod_id}>"
                embed.add_field(
                    name=f"Action #{i}",
                    value=f"**Moderator:** {mod_name}\n**Reason:** {reason}\n**Date:** {timestamp.split('T')[0]}",
                    inline=False
                )
        
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
