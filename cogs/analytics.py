import discord
from discord.ext import commands
import aiohttp
from datetime import datetime
import os

ANALYTICS_TOKEN = os.environ.get('BOT_ANALYTICS_TOKEN', 'secret')
# Use environment variable for dashboard URL, with fallback for local development
DASHBOARD_URL = os.environ.get('DASHBOARD_URL', 'http://localhost:5000').rstrip('/')


class Analytics(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def log_command_usage(self, guild_id: int, command_name: str, user_id: int, success: bool = True):
        """Send analytics to dashboard."""
        if not guild_id:
            return
        
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(
                    f'{DASHBOARD_URL}/api/analytics',
                    headers={'Authorization': f'Bot {ANALYTICS_TOKEN}'},
                    json={
                        'guild_id': guild_id,
                        'command': command_name,
                        'user_id': user_id,
                        'success': success
                    }
                )
        except Exception as e:
            print(f"Analytics error: {e}")

    @commands.Cog.listener()
    async def on_command_completion(self, ctx: commands.Context):
        """Log successful command."""
        await self.log_command_usage(
            ctx.guild.id if ctx.guild else 0,
            ctx.command.name,
            ctx.author.id,
            True
        )

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """Log failed command."""
        await self.log_command_usage(
            ctx.guild.id if ctx.guild else 0,
            ctx.command.name if ctx.command else "unknown",
            ctx.author.id,
            False
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Analytics(bot))
