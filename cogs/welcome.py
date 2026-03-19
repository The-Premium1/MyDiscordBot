import discord
from discord.ext import commands
import json
import os

WELCOME_CONFIG = "welcome_config.json"

def load_welcome_config():
    if os.path.exists(WELCOME_CONFIG):
        with open(WELCOME_CONFIG, "r") as f:
            return json.load(f)
    return {}

def save_welcome_config(config):
    with open(WELCOME_CONFIG, "w") as f:
        json.dump(config, f, indent=2)


class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.welcome_config = load_welcome_config()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Send welcome message when member joins."""
        guild_id = str(member.guild.id)
        
        if guild_id not in self.welcome_config:
            return
        
        config = self.welcome_config[guild_id]
        
        # Welcome DM
        if config.get('dm_enabled'):
            try:
                embed = discord.Embed(
                    title=f"👋 Welcome to {member.guild.name}!",
                    description=config.get('dm_message', 'Welcome to our server!'),
                    color=discord.Color.green()
                )
                embed.set_thumbnail(url=member.guild.icon.url if member.guild.icon else None)
                await member.send(embed=embed)
            except:
                pass
        
        # Welcome channel message
        if config.get('channel_enabled'):
            channel_id = config.get('channel_id')
            if channel_id:
                channel = member.guild.get_channel(channel_id)
                if channel:
                    message = config.get('channel_message', f'Welcome {member.mention}!').format(user=member.mention, server=member.guild.name)
                    embed = discord.Embed(
                        title="👋 New Member!",
                        description=message,
                        color=discord.Color.green()
                    )
                    embed.set_thumbnail(url=member.avatar.url if member.avatar else None)
                    await channel.send(embed=embed)
        
        # Auto role
        if config.get('autorole_enabled'):
            role_id = config.get('autorole_id')
            if role_id:
                role = member.guild.get_role(role_id)
                if role:
                    try:
                        await member.add_roles(role)
                    except:
                        pass

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Send goodbye message when member leaves."""
        guild_id = str(member.guild.id)
        
        if guild_id not in self.welcome_config:
            return
        
        config = self.welcome_config[guild_id]
        
        if config.get('goodbye_enabled'):
            channel_id = config.get('goodbye_channel_id')
            if channel_id:
                channel = member.guild.get_channel(channel_id)
                if channel:
                    message = config.get('goodbye_message', f'{member} left the server.').format(user=member.mention, server=member.guild.name)
                    embed = discord.Embed(
                        title="👋 Member Left",
                        description=message,
                        color=discord.Color.red()
                    )
                    embed.set_thumbnail(url=member.avatar.url if member.avatar else None)
                    await channel.send(embed=embed)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setwelcome(self, ctx: commands.Context, channel: discord.TextChannel):
        """Set the welcome channel."""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.welcome_config:
            self.welcome_config[guild_id] = {}
        
        self.welcome_config[guild_id]['channel_enabled'] = True
        self.welcome_config[guild_id]['channel_id'] = channel.id
        self.welcome_config[guild_id]['channel_message'] = 'Welcome {user} to {server}!'
        
        save_welcome_config(self.welcome_config)
        await ctx.send(f"✅ Welcome channel set to {channel.mention}!")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setwelcomedm(self, ctx: commands.Context, *, message: str = None):
        """Set welcome DM message."""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.welcome_config:
            self.welcome_config[guild_id] = {}
        
        self.welcome_config[guild_id]['dm_enabled'] = True
        self.welcome_config[guild_id]['dm_message'] = message or 'Welcome to our server!'
        
        save_welcome_config(self.welcome_config)
        await ctx.send("✅ Welcome DM enabled!")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setgoodbye(self, ctx: commands.Context, channel: discord.TextChannel, *, message: str = None):
        """Set goodbye message."""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.welcome_config:
            self.welcome_config[guild_id] = {}
        
        self.welcome_config[guild_id]['goodbye_enabled'] = True
        self.welcome_config[guild_id]['goodbye_channel_id'] = channel.id
        self.welcome_config[guild_id]['goodbye_message'] = message or '{user} left the server.'
        
        save_welcome_config(self.welcome_config)
        await ctx.send(f"✅ Goodbye message enabled for {channel.mention}!")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setautorole(self, ctx: commands.Context, role: discord.Role):
        """Set auto-role for new members."""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.welcome_config:
            self.welcome_config[guild_id] = {}
        
        self.welcome_config[guild_id]['autorole_enabled'] = True
        self.welcome_config[guild_id]['autorole_id'] = role.id
        
        save_welcome_config(self.welcome_config)
        await ctx.send(f"✅ Auto-role set to {role.mention}!")


async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot))
