import discord
from discord.ext import commands
import json
import os

STARBOARD_CONFIG = "starboard_config.json"

def load_starboard_config():
    if os.path.exists(STARBOARD_CONFIG):
        with open(STARBOARD_CONFIG, "r") as f:
            return json.load(f)
    return {}

def save_starboard_config(config):
    with open(STARBOARD_CONFIG, "w") as f:
        json.dump(config, f, indent=2)


class Starboard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.starboard_config = load_starboard_config()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """Handle star reactions."""
        if str(payload.emoji) != "⭐":
            return
        
        if payload.user_id == self.bot.user.id:
            return
        
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        
        guild_id = str(payload.guild_id)
        if guild_id not in self.starboard_config:
            return
        
        config = self.starboard_config[guild_id]
        threshold = config.get('threshold', 3)
        channel_id = config.get('channel_id')
        
        if not channel_id:
            return
        
        channel = guild.get_channel(channel_id)
        if not channel:
            return
        
        # Get message
        try:
            msg_channel = guild.get_channel(payload.channel_id)
            message = await msg_channel.fetch_message(payload.message_id)
        except:
            return
        
        # Check if already starred
        if any(entry.get('message_id') == payload.message_id for entry in config.get('starred', [])):
            return
        
        # Count stars
        stars = 0
        for reaction in message.reactions:
            if str(reaction.emoji) == "⭐":
                stars = reaction.count
                break
        
        if stars >= threshold:
            # Create starboard embed
            embed = discord.Embed(
                title="⭐ Starboard",
                description=message.content,
                color=discord.Color.gold()
            )
            
            embed.set_author(name=message.author.name, icon_url=message.author.avatar.url if message.author.avatar else None)
            embed.add_field(name="Original", value=f"[Jump to message]({message.jump_url})", inline=False)
            embed.set_footer(text=f"⭐ {stars} | {message.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Add images if any
            if message.attachments:
                embed.set_image(url=message.attachments[0].url)
            
            starboard_msg = await channel.send(embed=embed)
            
            # Store in config
            if 'starred' not in config:
                config['starred'] = []
            
            config['starred'].append({
                'message_id': payload.message_id,
                'starboard_message_id': starboard_msg.id
            })
            
            save_starboard_config(self.starboard_config)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setstarboard(self, ctx: commands.Context, channel: discord.TextChannel, threshold: int = 3):
        """Set starboard channel and threshold."""
        guild_id = str(ctx.guild.id)
        
        self.starboard_config[guild_id] = {
            'channel_id': channel.id,
            'threshold': threshold,
            'starred': []
        }
        
        save_starboard_config(self.starboard_config)
        await ctx.send(f"✅ Starboard set to {channel.mention} with threshold of {threshold} stars!")

    @commands.command()
    async def starboard(self, ctx: commands.Context):
        """Show top starred messages."""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.starboard_config:
            return await ctx.send("❌ Starboard not configured!")
        
        channel_id = self.starboard_config[guild_id].get('channel_id')
        if not channel_id:
            return await ctx.send("❌ Starboard channel not set!")
        
        channel = ctx.guild.get_channel(channel_id)
        if not channel:
            return await ctx.send("❌ Starboard channel not found!")
        
        # Get last 10 starboard messages
        messages = []
        async for message in channel.history(limit=10):
            messages.append(message)
        
        if not messages:
            return await ctx.send("❌ No starred messages yet!")
        
        embed = discord.Embed(
            title="⭐ Starboard",
            color=discord.Color.gold()
        )
        
        for i, msg in enumerate(messages, 1):
            if msg.embeds:
                original_embed = msg.embeds[0]
                embed.add_field(
                    name=f"#{i}",
                    value=f"{original_embed.description[:100]}...\n[View]({msg.jump_url})",
                    inline=False
                )
        
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Starboard(bot))
