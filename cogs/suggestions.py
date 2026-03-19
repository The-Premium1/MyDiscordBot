import discord
from discord.ext import commands
import json
import os

SUGGESTIONS_CONFIG = "suggestions_config.json"

def load_suggestions_config():
    if os.path.exists(SUGGESTIONS_CONFIG):
        with open(SUGGESTIONS_CONFIG, "r") as f:
            return json.load(f)
    return {}

def save_suggestions_config(config):
    with open(SUGGESTIONS_CONFIG, "w") as f:
        json.dump(config, f, indent=2)


class Suggestions(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.suggestions_config = load_suggestions_config()

    @commands.command()
    async def suggest(self, ctx: commands.Context, *, suggestion: str):
        """Submit a suggestion."""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.suggestions_config:
            return await ctx.send("❌ Suggestions channel not configured! Ask admin to use `!setsuggestions`")
        
        channel_id = self.suggestions_config[guild_id]['channel_id']
        channel = ctx.guild.get_channel(channel_id)
        
        if not channel:
            return await ctx.send("❌ Suggestions channel not found!")
        
        embed = discord.Embed(
            title="💡 New Suggestion",
            description=suggestion,
            color=discord.Color.gold()
        )
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        embed.set_footer(text=f"ID: {ctx.author.id}")
        
        message = await channel.send(embed=embed)
        
        # Add voting reactions
        await message.add_reaction("👍")
        await message.add_reaction("👎")
        
        await ctx.send("✅ Suggestion submitted!")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setsuggestions(self, ctx: commands.Context, channel: discord.TextChannel):
        """Set the suggestions channel."""
        guild_id = str(ctx.guild.id)
        
        self.suggestions_config[guild_id] = {
            'channel_id': channel.id
        }
        
        save_suggestions_config(self.suggestions_config)
        await ctx.send(f"✅ Suggestions channel set to {channel.mention}!")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def approve(self, ctx: commands.Context, message_id: int, *, reason: str = None):
        """Approve a suggestion."""
        try:
            # Try to find message in suggestions channel
            guild_id = str(ctx.guild.id)
            if guild_id not in self.suggestions_config:
                return await ctx.send("❌ Suggestions channel not configured!")
            
            channel_id = self.suggestions_config[guild_id]['channel_id']
            channel = ctx.guild.get_channel(channel_id)
            
            message = await channel.fetch_message(message_id)
            
            # Edit embed
            embed = message.embeds[0]
            embed.color = discord.Color.green()
            embed.add_field(name="✅ Approved", value=reason or "Approved!", inline=False)
            embed.add_field(name="Approved by", value=ctx.author.mention, inline=False)
            
            await message.edit(embed=embed)
            await ctx.send("✅ Suggestion approved!")
        except:
            await ctx.send("❌ Suggestion not found!")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def deny(self, ctx: commands.Context, message_id: int, *, reason: str = None):
        """Deny a suggestion."""
        try:
            guild_id = str(ctx.guild.id)
            if guild_id not in self.suggestions_config:
                return await ctx.send("❌ Suggestions channel not configured!")
            
            channel_id = self.suggestions_config[guild_id]['channel_id']
            channel = ctx.guild.get_channel(channel_id)
            
            message = await channel.fetch_message(message_id)
            
            # Edit embed
            embed = message.embeds[0]
            embed.color = discord.Color.red()
            embed.add_field(name="❌ Denied", value=reason or "Denied!", inline=False)
            embed.add_field(name="Denied by", value=ctx.author.mention, inline=False)
            
            await message.edit(embed=embed)
            await ctx.send("✅ Suggestion denied!")
        except:
            await ctx.send("❌ Suggestion not found!")


async def setup(bot: commands.Bot):
    await bot.add_cog(Suggestions(bot))
