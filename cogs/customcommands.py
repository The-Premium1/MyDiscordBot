import discord
from discord.ext import commands
import sqlite3
import os

DASHBOARD_DB = 'dashboard.db'


class CustomCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.custom_commands = {}
        self.load_custom_commands()

    def load_custom_commands(self):
        """Load custom commands from dashboard database."""
        if not os.path.exists(DASHBOARD_DB):
            return
        
        try:
            conn = sqlite3.connect(DASHBOARD_DB)
            cursor = conn.cursor()
            cursor.execute("SELECT guild_id, command_name, response FROM custom_commands")
            
            for guild_id, cmd_name, response in cursor.fetchall():
                if guild_id not in self.custom_commands:
                    self.custom_commands[guild_id] = {}
                self.custom_commands[guild_id][cmd_name.lower()] = response
            
            conn.close()
        except Exception as e:
            print(f"Error loading custom commands: {e}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Check for custom commands in messages."""
        if message.author.bot:
            return
        
        if not message.guild:
            return
        
        guild_id = message.guild.id
        prefix = '!'  # Default prefix
        
        # Check if message starts with prefix
        if not message.content.startswith(prefix):
            return
        
        # Get command name
        args = message.content[len(prefix):].split(' ')
        cmd_name = args[0].lower()
        
        # Check if custom command exists
        if guild_id in self.custom_commands:
            if cmd_name in self.custom_commands[guild_id]:
                response = self.custom_commands[guild_id][cmd_name]
                await message.channel.send(response)
                return

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def reloadcustom(self, ctx: commands.Context):
        """Reload custom commands from dashboard."""
        self.load_custom_commands()
        await ctx.send("✅ Custom commands reloaded!")


async def setup(bot: commands.Bot):
    await bot.add_cog(CustomCommands(bot))
