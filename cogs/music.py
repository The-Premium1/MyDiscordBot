import os
import time
import random
import asyncio
import logging
import subprocess
import shutil

import discord
from discord.ext import commands
import yt_dlp

logging.basicConfig(level=logging.INFO)

# FFmpeg detection
FFMPEG_EXE = None
for path in ['/usr/bin/ffmpeg', '/usr/local/bin/ffmpeg', '/bin/ffmpeg']:
    if os.path.exists(path):
        FFMPEG_EXE = path
        break

if not FFMPEG_EXE:
    try:
        result = subprocess.run(['which', 'ffmpeg'], capture_output=True, text=True, timeout=2)
        if result.returncode == 0 and result.stdout.strip():
            FFMPEG_EXE = result.stdout.strip()
    except Exception:
        pass

if not FFMPEG_EXE:
    local_path = os.path.join(os.path.dirname(__file__), '..', 'ffmpeg.exe')
    if os.path.exists(local_path):
        FFMPEG_EXE = local_path

print(f"🎵 FFmpeg: {FFMPEG_EXE or 'NOT FOUND'}")


class MusicManager:
    def __init__(self):
        self.queue = []
        self.current = None
        self.start_time = 0
        self.volume = 0.5
        self.player_message = None
        self.text_channel = None
        self.loop_mode = 0


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.manager = MusicManager()
        
        self.YDL_OPTIONS = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': False,
            'no-warnings': False,
            'socket_timeout': 30,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
        }
        
        self.FFMPEG_OPTIONS = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn -b:a 128k'
        }
        if FFMPEG_EXE:
            self.FFMPEG_OPTIONS['executable'] = FFMPEG_EXE
        
        print(f"✅ Music Cog Ready - FFmpeg: {FFMPEG_EXE or 'system default'}", flush=True)

    async def check_voice_channels(self, ctx: commands.Context) -> bool:
        if not ctx.voice_client:
            await ctx.send("🎧 I'm not in a voice channel!")
            return False
        if not ctx.author.voice or ctx.author.voice.channel != ctx.voice_client.channel:
            await ctx.send("🚫 You must be in my voice channel!")
            return False
        return True

    @commands.command()
    async def ffmpeg(self, ctx: commands.Context):
        """Check if FFmpeg is installed."""
        if FFMPEG_EXE:
            result = subprocess.run([FFMPEG_EXE, '-version'], capture_output=True, text=True, timeout=5)
            version_line = result.stdout.split('\n')[0] if result.stdout else "Unknown version"
            await ctx.send(f"✅ FFmpeg: {version_line}")
        else:
            await ctx.send("❌ FFmpeg not found!")

    @commands.command()
    async def checkperms(self, ctx: commands.Context):
        """Check if bot has voice permissions in this channel."""
        channel = ctx.author.voice.channel if ctx.author.voice else None
        
        if not channel:
            return await ctx.send("🎧 You're not in a voice channel!")
        
        perms = channel.permissions_for(ctx.guild.me)
        
        embed = discord.Embed(title="🔐 Bot Voice Permissions", color=discord.Color.blue())
        embed.add_field(name="Channel", value=channel.mention, inline=False)
        embed.add_field(name="Connect", value="✅" if perms.connect else "❌", inline=True)
        embed.add_field(name="Speak", value="✅" if perms.speak else "❌", inline=True)
        embed.add_field(name="Use Voice", value="✅" if perms.use_voice_activation else "❌", inline=True)
        embed.add_field(name="Manage Channels", value="✅" if perms.manage_channels else "❌", inline=True)
        
        if not perms.connect:
            embed.description = "❌ **Bot cannot connect to this voice channel!**"
        elif not perms.speak:
            embed.description = "⚠️ **Bot can connect but cannot speak!**"
        else:
            embed.description = "✅ **All permissions OK**"
        
        await ctx.send(embed=embed)

    @commands.command(aliases=['j'])
    async def join(self, ctx: commands.Context):
        """Join the voice channel."""
        if not ctx.author.voice:
            return await ctx.send("🎧 You're not in a voice channel!")
        
        channel = ctx.author.voice.channel
        
        # Check permissions
        perms = channel.permissions_for(ctx.guild.me)
        if not perms.connect:
            return await ctx.send("❌ I don't have permission to connect to this voice channel!")
        if not perms.speak:
            return await ctx.send("❌ I don't have permission to speak in this voice channel!")
        
        # If already in a channel
        if ctx.voice_client:
            if ctx.voice_client.channel == channel:
                return await ctx.send(f"✅ Already in {channel.mention}!")
            # Move to new channel
            try:
                await ctx.voice_client.move_to(channel)
                await asyncio.sleep(2)
                await ctx.send(f"🔀 Moved to {channel.mention}!")
                return
            except Exception as e:
                print(f"❌ MOVE ERROR: {e}")
                return await ctx.send(f"❌ Failed to move: {str(e)}")
        
        # Connect to new channel
        try:
            print(f"🔗 Attempting to connect to {channel} ({channel.id}) in guild {ctx.guild.id}...")
            vc = await asyncio.wait_for(channel.connect(timeout=30.0), timeout=35.0)
            print(f"✅ Connection object created: {vc}")
            print(f"   is_connected(): {vc.is_connected()}")
            
            await asyncio.sleep(5)  # Longer wait for voice handshake
            
            print(f"✅ After 5s wait - is_connected(): {vc.is_connected()}")
            
            if vc and vc.is_connected():
                await ctx.send(f"✅ Joined {channel.mention}!")
            else:
                await ctx.send(f"⚠️ Join attempted - status unclear. Try `!vc_status`")
                print(f"⚠️ WARNING: Connection object exists but is_connected() = False!")
                
        except asyncio.TimeoutError as e:
            print(f"❌ TIMEOUT: {e}")
            await ctx.send("❌ Connection timeout (Discord may be slow)")
        except Exception as e:
            print(f"❌ CONNECT ERROR: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            await ctx.send(f"❌ Failed to join: {type(e).__name__}: {str(e)}")

    @commands.command(aliases=['l', 'disconnect', 'dc'])
    async def leave(self, ctx: commands.Context):
        """Leave the voice channel."""
        if ctx.voice_client:
            try:
                await ctx.voice_client.disconnect(force=True)
                await ctx.send("👋 Left voice channel!")
            except Exception as e:
                await ctx.send(f"⚠️ Disconnect issue: {str(e)}")
        else:
            await ctx.send("❌ Not in a voice channel!")

    @commands.command(aliases=['p'])
    async def play(self, ctx: commands.Context, *, query: str = None):
        """Play a song from YouTube."""
        if not query:
            return await ctx.send("❌ Please provide a song name!")
        
        # Ensure bot is in voice
        if not ctx.voice_client:
            if not ctx.author.voice:
                return await ctx.send("🎧 Join a voice channel first!")
            try:
                await ctx.author.voice.channel.connect(timeout=10.0)
                await asyncio.sleep(2)  # Wait for connection to stabilize
            except Exception as e:
                return await ctx.send(f"❌ Failed to join voice: {str(e)}")
        
        vc = ctx.voice_client
        
        # Check if connection is actually ready
        if not vc or not vc.is_connected():
            return await ctx.send("❌ Not properly connected to voice!")
        
        await ctx.send(f"🔍 Searching for: {query}")
        
        try:
            with yt_dlp.YoutubeDL(self.YDL_OPTIONS) as ydl:
                info = ydl.extract_info(f"ytsearch:{query}", download=False)
                if not info or not info.get('entries'):
                    return await ctx.send("❌ No songs found!")
                
                song = info['entries'][0]
                url = song['url']
                title = song.get('title', 'Unknown')
                
                self.manager.current = {'title': title, 'url': url}
                source = discord.FFmpegPCMAudio(url, **self.FFMPEG_OPTIONS)
                
                if vc.is_playing():
                    vc.stop()
                
                vc.play(source, after=lambda e: print(f"Playback finished: {e}"))
                await ctx.send(f"🎵 Now Playing: **{title}**")
                
        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}")

    @commands.command(aliases=['s'])
    async def stop(self, ctx: commands.Context):
        """Stop the music."""
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await ctx.send("⏹️ Music stopped!")
        else:
            await ctx.send("❌ Nothing is playing!")

    @commands.command(aliases=['pa'])
    async def pause(self, ctx: commands.Context):
        """Pause the music."""
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.send("⏸️ Music paused!")
        else:
            await ctx.send("❌ Nothing is playing!")

    @commands.command(aliases=['res'])
    async def resume(self, ctx: commands.Context):
        """Resume the music."""
        if ctx.voice_client and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send("▶️ Music resumed!")
        else:
            await ctx.send("❌ Nothing is paused!")

    @commands.command(aliases=['q'])
    async def queue(self, ctx: commands.Context):
        """Show the queue."""
        if not self.manager.queue:
            return await ctx.send("❌ Queue is empty!")
        
        embed = discord.Embed(title="🎵 Queue", color=discord.Color.blue())
        for i, song in enumerate(self.manager.queue[:10], 1):
            embed.add_field(name=f"{i}.", value=song.get('title', 'Unknown')[:50], inline=False)
        
        if len(self.manager.queue) > 10:
            embed.add_field(name="...", value=f"and {len(self.manager.queue) - 10} more songs", inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(aliases=['c'])
    async def clear(self, ctx: commands.Context):
        """Clear the queue."""
        self.manager.queue.clear()
        await ctx.send("🧹 Queue cleared!")

    @commands.command()
    async def ping(self, ctx: commands.Context):
        """Check connection latency."""
        if ctx.voice_client and ctx.voice_client.is_connected():
            latency = ctx.voice_client.latency
            await ctx.send(f"🏓 Pong! Voice latency: {latency*1000:.0f}ms")
        else:
            await ctx.send("❌ Not connected to voice!")

    @commands.command()
    async def vc_status(self, ctx: commands.Context):
        """Show voice connection status."""
        vc = ctx.voice_client
        
        if not vc:
            return await ctx.send("❌ Not in a voice channel!")
        
        embed = discord.Embed(title="🎙️ Voice Status", color=discord.Color.blue() if vc.is_connected() else discord.Color.red())
        embed.add_field(name="Channel", value=vc.channel.mention if vc.channel else "None", inline=False)
        embed.add_field(name="Connected", value=f"**{vc.is_connected()}**", inline=True)
        embed.add_field(name="Playing", value=str(vc.is_playing()), inline=True)
        embed.add_field(name="Paused", value=str(vc.is_paused()), inline=True)
        embed.add_field(name="Latency", value=f"{vc.latency*1000:.0f}ms", inline=True)
        embed.add_field(name="Average Latency", value=f"{vc.average_latency*1000:.0f}ms", inline=True)
        
        # Debug info
        embed.add_field(name="State", value=str(vc._state) if hasattr(vc, '_state') else "Unknown", inline=False)
        
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    print("🔧 Loading Music cog...", flush=True)
    try:
        await bot.add_cog(Music(bot))
        print("✅ Music cog loaded!", flush=True)
    except Exception as e:
        print(f"❌ Failed to load Music cog: {e}", flush=True)
        import traceback
        traceback.print_exc()
