import discord
from discord.ext import commands
from datetime import datetime
import psutil
import os


class Utilities(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx: commands.Context):
        """Check bot latency."""
        latency = round(self.bot.latency * 1000)
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"**Latency:** {latency}ms",
            color=discord.Color.green() if latency < 100 else discord.Color.orange()
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def serverinfo(self, ctx: commands.Context):
        """Shows server information."""
        guild = ctx.guild
        
        embed = discord.Embed(
            title=f"🏛️ {guild.name}",
            color=discord.Color.blurple(),
            timestamp=datetime.utcnow()
        )
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        embed.add_field(name="Server ID", value=guild.id, inline=True)
        embed.add_field(name="Owner", value=guild.owner.mention if guild.owner else "Unknown", inline=True)
        embed.add_field(name="Members", value=f"**{guild.member_count}**", inline=True)
        embed.add_field(name="Channels", value=f"**{len(guild.channels)}**", inline=True)
        embed.add_field(name="Roles", value=f"**{len(guild.roles)}**", inline=True)
        embed.add_field(name="Created", value=guild.created_at.strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="Verification Level", value=guild.verification_level, inline=True)
        embed.add_field(name="Boost Level", value=f"Level {guild.premium_tier}", inline=True)
        embed.add_field(name="Boosts", value=f"**{guild.premium_subscription_count}**", inline=True)
        
        await ctx.send(embed=embed)

    @commands.command()
    async def botinfo(self, ctx: commands.Context):
        """Shows bot information."""
        embed = discord.Embed(
            title="🤖 Bot Information",
            color=discord.Color.blurple()
        )
        
        if self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)
        
        embed.add_field(name="Bot Name", value=self.bot.user.mention, inline=True)
        embed.add_field(name="Bot ID", value=self.bot.user.id, inline=True)
        embed.add_field(name="Prefix", value="!", inline=True)
        embed.add_field(name="Ping", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        embed.add_field(name="Servers", value=len(self.bot.guilds), inline=True)
        embed.add_field(name="Users", value=sum(g.member_count for g in self.bot.guilds), inline=True)
        
        await ctx.send(embed=embed)

    @commands.command(name='commands')
    async def help(self, ctx: commands.Context, cog: str = None):
        """Shows all available commands."""
        if cog:
            cog_obj = self.bot.get_cog(cog.capitalize())
            if not cog_obj:
                return await ctx.send(f"❌ Cog **{cog}** not found!")
            
            commands_list = cog_obj.get_commands()
            embed = discord.Embed(
                title=f"📚 {cog.capitalize()} Commands",
                color=discord.Color.blurple()
            )
            
            for cmd in commands_list:
                embed.add_field(
                    name=f"!{cmd.name}",
                    value=cmd.help or "No description",
                    inline=False
                )
            
            return await ctx.send(embed=embed)
        
        # List all cogs
        embed = discord.Embed(
            title="📚 Available Commands",
            description="Use `!commands [category]` for more info",
            color=discord.Color.blurple()
        )
        
        for cog in self.bot.cogs:
            commands_list = self.bot.get_cog(cog).get_commands()
            if commands_list:
                embed.add_field(
                    name=f"**{cog}**",
                    value=f"{len(commands_list)} commands",
                    inline=True
                )
        
        await ctx.send(embed=embed)

    @commands.command()
    async def stats(self, ctx: commands.Context):
        """Shows bot statistics."""
        process = psutil.Process(os.getpid())
        
        total_commands = sum(len(self.bot.get_cog(cog).get_commands()) for cog in self.bot.cogs)
        
        embed = discord.Embed(
            title="📊 Bot Statistics",
            color=discord.Color.blurple()
        )
        embed.add_field(name="Total Guilds", value=len(self.bot.guilds), inline=True)
        embed.add_field(name="Total Users", value=sum(g.member_count for g in self.bot.guilds), inline=True)
        embed.add_field(name="Total Commands", value=total_commands, inline=True)
        embed.add_field(name="Total Cogs", value=len(self.bot.cogs), inline=True)
        embed.add_field(name="Memory Usage", value=f"{process.memory_info().rss / 1024 / 1024:.2f} MB", inline=True)
        embed.add_field(name="CPU Usage", value=f"{process.cpu_percent()}%", inline=True)
        
        await ctx.send(embed=embed)

    @commands.command()
    async def uptime(self, ctx: commands.Context):
        """Shows bot uptime."""
        uptime = datetime.utcnow() - self.bot.launch_time
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        embed = discord.Embed(
            title="⏱️ Bot Uptime",
            description=f"**{days}d {hours}h {minutes}m {seconds}s**",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def support(self, ctx: commands.Context):
        """Shows support/invite links."""
        embed = discord.Embed(
            title="🤝 Support & Invite",
            color=discord.Color.blurple()
        )
        embed.add_field(
            name="Invite Bot",
            value="[Click Here](https://discord.com/oauth2/authorize?client_id=YOUR_BOT_ID&scope=bot&permissions=8)",
            inline=False
        )
        embed.add_field(
            name="Support Server",
            value="[Discord Server](https://discord.gg/YourServerInvite)",
            inline=False
        )
        embed.add_field(
            name="GitHub",
            value="[Repository](https://github.com/yourrepo)",
            inline=False
        )
        
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Utilities(bot))
