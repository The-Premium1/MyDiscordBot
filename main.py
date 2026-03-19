import discord
from discord.ext import commands
import asyncio
import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from bot_data_connector import bot_connector

# Load environment variables
load_dotenv()

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
bot = commands.Bot(command_prefix='!', intents=intents)
bot.launch_time = datetime.now(timezone.utc)

# Connect dashboard to bot
bot_connector.set_bot(bot)

@bot.event
async def on_ready():
    print(f'✅ Logged in as {bot.user.name}')
    print(f'📚 Loaded Cogs: {len(bot.cogs)}')
    
    # Set bot status
    await bot.change_presence(activity=discord.Game(name="!help | Your Ultimate Bot"))

@bot.event
async def on_command_error(ctx, error):
    """Global error handler for all commands."""
    # Handle case where ctx.command is None
    command_name = ctx.command.name if ctx and ctx.command else "unknown"
    print(f"⚠️ Command Error in '{command_name}': {error}")
    import traceback
    traceback.print_exc()
    
    # Send error message to user (only if we have context)
    if ctx:
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(f"❌ You don't have permission to use this command.")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send(f"❌ I don't have permission to do that.")
        elif isinstance(error, commands.CommandNotFound):
            pass  # Ignore command not found
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing argument: {error.param.name}")
        else:
            await ctx.send(f"❌ Error: {str(error)[:100]}")

async def load_cogs():
    """Loads all cogs from the cogs folder."""
    cogs_dir = './cogs'
    if not os.path.exists(cogs_dir):
        print(f"❌ Cogs directory not found!")
        return
    
    loaded_count = 0
    for filename in os.listdir(cogs_dir):
        if filename.endswith('.py') and filename != '__init__.py':
            try:
                await bot.load_extension(f'cogs.{filename[:-3]}')
                print(f'✅ Loaded {filename}')
                loaded_count += 1
            except Exception as e:
                print(f'❌ Failed to load {filename}: {e}')
    
    print(f'📊 Total cogs loaded: {loaded_count}')

async def main():
    async with bot:
        await load_cogs()
        token = os.getenv('BOT_TOKEN')
        if not token:
            print("❌ BOT_TOKEN not found in .env file!")
            return
        await bot.start(token)

if __name__ == '__main__':
    asyncio.run(main())