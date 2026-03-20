import discord
from discord.ext import commands
import asyncio
import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv
from bot_data_connector import bot_connector

# Force unbuffered output for Railway logs
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 1)
sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', 1)

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
    print(f'✅ Logged in as {bot.user.name}', flush=True)
    print(f'📚 Loaded Cogs: {len(bot.cogs)}', flush=True)
    
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
    print("🔧 Starting cog loading...", flush=True)
    
    cogs_dir = './cogs'
    print(f"📂 Looking for cogs in: {os.path.abspath(cogs_dir)}", flush=True)
    
    if not os.path.exists(cogs_dir):
        print(f"❌ Cogs directory not found at {os.path.abspath(cogs_dir)}!", flush=True)
        return
    
    print(f"✅ Cogs directory found!", flush=True)
    
    files = os.listdir(cogs_dir)
    print(f"📄 Files in cogs directory: {files}", flush=True)
    
    loaded_count = 0
    for filename in files:
        if filename.endswith('.py') and filename != '__init__.py':
            try:
                cog_name = filename[:-3]
                print(f"⏳ Loading {cog_name}...", flush=True)
                await bot.load_extension(f'cogs.{cog_name}')
                print(f'✅ Loaded {filename}', flush=True)
                loaded_count += 1
            except Exception as e:
                print(f'❌ Failed to load {filename}: {e}', flush=True)
                import traceback
                traceback.print_exc()
    
    print(f'📊 Total cogs loaded: {loaded_count}', flush=True)

async def main():
    token = os.getenv('BOT_TOKEN')
    if not token:
        print("❌ BOT_TOKEN not found in .env file!", flush=True)
        return
    
    print("🤖 Initializing bot...", flush=True)
    
    # Retry logic with exponential backoff for Discord connection issues
    max_retries = 5
    retry_delay = 3
    
    for attempt in range(max_retries):
        try:
            print(f"\n🤖 Bot login attempt {attempt + 1}/{max_retries}...", flush=True)
            async with bot:
                await load_cogs()
                print(f"🚀 Starting bot...", flush=True)
                await bot.start(token)
        except Exception as e:
            error_str = str(e).lower()
            # Don't retry on authentication errors
            if "401" in error_str or "unauthorized" in error_str or "invalid token" in error_str:
                print(f"❌ FATAL: Invalid token - {e}", flush=True)
                return
            
            # Retry on rate limits, connection errors, etc
            if attempt < max_retries - 1:
                print(f"⚠️ Connection failed: {type(e).__name__}", flush=True)
                print(f"⏳ Retrying in {retry_delay}s...", flush=True)
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 60)  # Max 60s backoff
            else:
                print(f"❌ Failed to connect after {max_retries} attempts", flush=True)
                raise

if __name__ == '__main__':
    asyncio.run(main())