import discord
from discord.ext import commands
from datetime import datetime
import json
import os

# Store logs channel per guild
LOGS_CONFIG = "logs_config.json"

def load_logs_config():
    if os.path.exists(LOGS_CONFIG):
        with open(LOGS_CONFIG, "r") as f:
            return json.load(f)
    return {}

def save_logs_config(config):
    with open(LOGS_CONFIG, "w") as f:
        json.dump(config, f, indent=2)


class Logging(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logs_channels = load_logs_config()

    async def get_logs_channel(self, guild: discord.Guild) -> discord.TextChannel:
        """Get the logs channel for this guild if it's been set."""
        guild_id = str(guild.id)
        if guild_id not in self.logs_channels:
            return None
        
        channel_id = self.logs_channels[guild_id]
        channel = guild.get_channel(channel_id)
        return channel

    async def log_embed(self, guild: discord.Guild, embed: discord.Embed):
        """Send an embed to the logs channel if set."""
        logs_channel = await self.get_logs_channel(guild)
        if not logs_channel:
            return
        
        try:
            await logs_channel.send(embed=embed)
        except Exception as e:
            print(f"Error logging to channel: {e}")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Log when a member joins."""
        embed = discord.Embed(
            title="👋 Member Joined",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Member", value=f"{member.mention} ({member.id})", inline=False)
        embed.add_field(name="Account Created", value=member.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=False)
        embed.set_thumbnail(url=member.avatar.url if member.avatar else None)
        
        await self.log_embed(member.guild, embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Log when a member leaves or is kicked/banned."""
        embed = discord.Embed(
            title="👋 Member Left",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Member", value=f"{member.mention} ({member.id})", inline=False)
        embed.add_field(name="Joined Server", value=member.joined_at.strftime("%Y-%m-%d %H:%M:%S") if member.joined_at else "Unknown", inline=False)
        embed.set_thumbnail(url=member.avatar.url if member.avatar else None)
        
        await self.log_embed(member.guild, embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        """Log when a message is deleted."""
        if message.author.bot:
            return
        
        embed = discord.Embed(
            title="🗑️ Message Deleted",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Author", value=f"{message.author.mention} ({message.author.id})", inline=False)
        embed.add_field(name="Channel", value=message.channel.mention, inline=False)
        embed.add_field(name="Content", value=message.content[:1024] if message.content else "(No text content)", inline=False)
        
        await self.log_embed(message.guild, embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        """Log when a message is edited."""
        if before.author.bot or before.content == after.content:
            return
        
        embed = discord.Embed(
            title="✏️ Message Edited",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Author", value=f"{before.author.mention} ({before.author.id})", inline=False)
        embed.add_field(name="Channel", value=before.channel.mention, inline=False)
        embed.add_field(name="Before", value=before.content[:1024] if before.content else "(No text)", inline=False)
        embed.add_field(name="After", value=after.content[:1024] if after.content else "(No text)", inline=False)
        
        await self.log_embed(before.guild, embed)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Log role changes, nickname changes, etc."""
        # Check for role changes
        if before.roles != after.roles:
            added_roles = set(after.roles) - set(before.roles)
            removed_roles = set(before.roles) - set(after.roles)
            
            embed = discord.Embed(
                title="🔄 Member Roles Updated",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Member", value=f"{after.mention} ({after.id})", inline=False)
            
            if added_roles:
                roles_text = ", ".join([r.mention for r in added_roles])
                embed.add_field(name="✅ Added Roles", value=roles_text, inline=False)
            
            if removed_roles:
                roles_text = ", ".join([r.mention for r in removed_roles])
                embed.add_field(name="❌ Removed Roles", value=roles_text, inline=False)
            
            await self.log_embed(before.guild, embed)
        
        # Check for nickname changes
        if before.nick != after.nick:
            embed = discord.Embed(
                title="📝 Nickname Changed",
                color=discord.Color.blurple(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Member", value=f"{after.mention} ({after.id})", inline=False)
            embed.add_field(name="Before", value=before.nick or "No nickname", inline=False)
            embed.add_field(name="After", value=after.nick or "No nickname", inline=False)
            
            await self.log_embed(before.guild, embed)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        """Log when a channel is created."""
        embed = discord.Embed(
            title="➕ Channel Created",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Channel", value=f"{channel.mention} ({channel.name})", inline=False)
        embed.add_field(name="Type", value=str(channel.type), inline=False)
        
        await self.log_embed(channel.guild, embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        """Log when a channel is deleted."""
        embed = discord.Embed(
            title="➖ Channel Deleted",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Channel", value=channel.name, inline=False)
        embed.add_field(name="Type", value=str(channel.type), inline=False)
        
        await self.log_embed(channel.guild, embed)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setlogs(self, ctx: commands.Context, channel: discord.TextChannel):
        """Set the logs channel. Logs will be sent here."""
        guild_id = str(ctx.guild.id)
        self.logs_channels[guild_id] = channel.id
        save_logs_config(self.logs_channels)
        await ctx.send(f"✅ Logs channel set to {channel.mention}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def removelogs(self, ctx: commands.Context):
        """Remove the logs channel - logging will be disabled."""
        guild_id = str(ctx.guild.id)
        if guild_id in self.logs_channels:
            del self.logs_channels[guild_id]
            save_logs_config(self.logs_channels)
            await ctx.send("✅ Logs channel removed. Logging disabled.")
        else:
            await ctx.send("❌ No logs channel was set!")


async def setup(bot: commands.Bot):
    await bot.add_cog(Logging(bot))
