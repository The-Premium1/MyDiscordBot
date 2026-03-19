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
    print(f'âœ… Logged in as {bot.user.name}')
    print(f'ðŸ“š Loaded Cogs: {len(bot.cogs)}')
    
    # Set bot status
    await bot.change_presence(activity=discord.Game(name="!help | Your Ultimate Bot"))

@bot.event
async def on_command_error(ctx, error):
    """Global error handler for all commands."""
    # Handle case where ctx.command is None
    command_name = ctx.command.name if ctx and ctx.command else "unknown"
    print(f"âš ï¸ Command Error in '{command_name}': {error}")
    import traceback
    traceback.print_exc()
    
    # Send error message to user (only if we have context)
    if ctx:
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(f"âŒ You don't have permission to use this command.")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send(f"âŒ I don't have permission to do that.")
        elif isinstance(error, commands.CommandNotFound):
            pass  # Ignore command not found
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"âŒ Missing argument: {error.param.name}")
        else:
            await ctx.send(f"âŒ Error: {str(error)[:100]}")

async def load_cogs():
    """Loads all cogs from the cogs folder."""
    cogs_dir = './cogs'
    if not os.path.exists(cogs_dir):
        print(f"âŒ Cogs directory not found!")
        return
    
    loaded_count = 0
    for filename in os.listdir(cogs_dir):
        if filename.endswith('.py') and filename != '__init__.py':
            try:
                await bot.load_extension(f'cogs.{filename[:-3]}')
                print(f'âœ… Loaded {filename}')
                loaded_count += 1
            except Exception as e:
                print(f'âŒ Failed to load {filename}: {e}')
    
    print(f'ðŸ“Š Total cogs loaded: {loaded_count}')

async def main():
    token = os.getenv('BOT_TOKEN')
    if not token:
        print("BOT_TOKEN not found in .env file!")
        return
    
    # Retry logic with exponential backoff for Discord connection issues
    max_retries = 5
    retry_delay = 3
    
    for attempt in range(max_retries):
        try:
            print(f"\nðŸ¤– Bot login attempt {attempt + 1}/{max_retries}...")
            async with bot:
                await load_cogs()
                await bot.start(token)
        except Exception as e:
            error_str = str(e).lower()
            # Don't retry on authentication errors
            if "401" in error_str or "unauthorized" in error_str or "invalid token" in error_str:
                print(f"âŒ FATAL: Invalid token - {e}")
                return
            
            # Retry on rate limits, connection errors, etc
            if attempt < max_retries - 1:
                print(f"âš ï¸ Connection failed: {type(e).__name__}")
                print(f"â³ Retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 60)  # Max 60s backoff
            else:
                print(f"âŒ Failed to connect after {max_retries} attempts")
                raise

if __name__ == '__main__':
    asyncio.run(main())