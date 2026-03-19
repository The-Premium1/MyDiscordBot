import discord
from discord.ext import commands
import re
from datetime import datetime

# Profanity list (expand as needed)
PROFANITY = ['badword1', 'badword2', 'badword3', 'damn', 'hell', 'crap']

# Common spam patterns
INVITE_REGEX = r'(https?://)?(www\.)?(discord\.(gg|io|me|li)|discordapp\.com/invite)/\S+'
URL_REGEX = r'https?://\S+'


class AutoMod(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.spam_tracker = {}

    async def get_automod_settings(self, guild_id: int) -> dict:
        """Get automod settings (placeholder - could be extended with database)."""
        return {
            'spam_enabled': True,
            'spam_threshold': 5,  # 5 messages in 10 seconds
            'profanity_enabled': True,
            'invite_enabled': True,
            'caps_enabled': True,
        }

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Check message for violations."""
        if message.author.bot or not message.guild:
            return
        
        if not message.guild.me.guild_permissions.manage_messages:
            return
        
        settings = await self.get_automod_settings(message.guild.id)
        
        # Spam check
        if settings['spam_enabled']:
            await self.check_spam(message)
        
        # Profanity check
        if settings['profanity_enabled']:
            await self.check_profanity(message)
        
        # Invite link check
        if settings['invite_enabled']:
            await self.check_invites(message)
        
        # Caps spam check
        if settings['caps_enabled']:
            await self.check_caps_spam(message)

    async def check_spam(self, message: discord.Message):
        """Detect rapid message spam."""
        user_id = message.author.id
        guild_id = message.guild.id
        key = f"{user_id}_{guild_id}"
        
        if key not in self.spam_tracker:
            self.spam_tracker[key] = []
        
        self.spam_tracker[key].append(datetime.utcnow())
        
        # Keep only messages from last 10 seconds
        cutoff = datetime.utcnow().timestamp() - 10
        self.spam_tracker[key] = [t for t in self.spam_tracker[key] if t.timestamp() > cutoff]
        
        # Check threshold (5 messages in 10 seconds)
        if len(self.spam_tracker[key]) > 5:
            try:
                await message.delete()
                await message.author.send("⚠️ **Spam Detected:** You're sending messages too quickly!")
                
                # Mute for 5 minutes
                mute_time = discord.utils.utcnow() + discord.ext.commands.timedelta(minutes=5)
                await message.author.timeout(mute_time, reason="Spam detection")
                
                # Log to channel
                logs_channel = discord.utils.get(message.guild.text_channels, name="mod-logs")
                if logs_channel:
                    embed = discord.Embed(
                        title="🤖 Spam Detected",
                        color=discord.Color.orange(),
                        timestamp=datetime.utcnow()
                    )
                    embed.add_field(name="User", value=message.author.mention)
                    embed.add_field(name="Action", value="Muted for 5 minutes")
                    await logs_channel.send(embed=embed)
            except:
                pass

    async def check_profanity(self, message: discord.Message):
        """Detect profanity."""
        content_lower = message.content.lower()
        
        for word in PROFANITY:
            if word in content_lower:
                try:
                    await message.delete()
                    embed = discord.Embed(
                        title="⚠️ Message Deleted",
                        description="Your message contained inappropriate language.",
                        color=discord.Color.red()
                    )
                    await message.author.send(embed=embed)
                    
                    # Log
                    logs_channel = discord.utils.get(message.guild.text_channels, name="mod-logs")
                    if logs_channel:
                        embed = discord.Embed(
                            title="🤖 Profanity Detected",
                            color=discord.Color.orange(),
                            timestamp=datetime.utcnow()
                        )
                        embed.add_field(name="User", value=message.author.mention)
                        embed.add_field(name="Message", value=message.content[:100])
                        await logs_channel.send(embed=embed)
                except:
                    pass
                break

    async def check_invites(self, message: discord.Message):
        """Detect Discord invite links."""
        if re.search(INVITE_REGEX, message.content):
            try:
                await message.delete()
                embed = discord.Embed(
                    title="⚠️ Invite Link Removed",
                    description="Discord invite links are not allowed.",
                    color=discord.Color.red()
                )
                await message.author.send(embed=embed)
                
                # Log
                logs_channel = discord.utils.get(message.guild.text_channels, name="mod-logs")
                if logs_channel:
                    embed = discord.Embed(
                        title="🤖 Invite Link Detected",
                        color=discord.Color.orange(),
                        timestamp=datetime.utcnow()
                    )
                    embed.add_field(name="User", value=message.author.mention)
                    embed.add_field(name="Link", value=message.content[:100])
                    await logs_channel.send(embed=embed)
            except:
                pass

    async def check_caps_spam(self, message: discord.Message):
        """Detect excessive caps."""
        content = message.content
        
        if len(content) < 5:
            return
        
        caps_count = sum(1 for c in content if c.isupper())
        caps_percentage = (caps_count / len(content)) * 100
        
        if caps_percentage > 70:  # More than 70% caps
            try:
                await message.delete()
                embed = discord.Embed(
                    title="⚠️ Message Deleted",
                    description="Stop SCREAMING! (Excessive caps detected)",
                    color=discord.Color.red()
                )
                await message.author.send(embed=embed)
                
                # Log
                logs_channel = discord.utils.get(message.guild.text_channels, name="mod-logs")
                if logs_channel:
                    embed = discord.Embed(
                        title="🤖 Caps Spam Detected",
                        color=discord.Color.orange(),
                        timestamp=datetime.utcnow()
                    )
                    embed.add_field(name="User", value=message.author.mention)
                    embed.add_field(name="Message", value=content[:100])
                    await logs_channel.send(embed=embed)
            except:
                pass

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def addprofanity(self, ctx: commands.Context, word: str):
        """Add a word to profanity filter."""
        if word not in PROFANITY:
            PROFANITY.append(word.lower())
            await ctx.send(f"✅ Added **{word}** to profanity filter!")
        else:
            await ctx.send("❌ Word already in filter!")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def removeprofanity(self, ctx: commands.Context, word: str):
        """Remove a word from profanity filter."""
        if word in PROFANITY:
            PROFANITY.remove(word.lower())
            await ctx.send(f"✅ Removed **{word}** from profanity filter!")
        else:
            await ctx.send("❌ Word not in filter!")


async def setup(bot: commands.Bot):
    await bot.add_cog(AutoMod(bot))
