import os
import asyncio
import subprocess
import discord
from discord.ext import commands
import yt_dlp

# FFmpeg path
FFMPEG_EXE = None
for path in ['/usr/bin/ffmpeg', '/usr/local/bin/ffmpeg', '/bin/ffmpeg']:
    if os.path.exists(path):
        FFMPEG_EXE = path
        break

print(f"🎵 FFmpeg available: {FFMPEG_EXE is not None}", flush=True)


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = []
        self.current = None
        
        self.ydl_opts = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
        }
        
        self.ffmpeg_opts = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn -b:a 128k'
        }
        if FFMPEG_EXE:
            self.ffmpeg_opts['executable'] = FFMPEG_EXE

    @commands.command()
    async def join(self, ctx):
        """Join voice channel."""
        if not ctx.author.voice:
            return await ctx.send("❌ You're not in a voice channel!")
        
        channel = ctx.author.voice.channel
        
        try:
            # Disconnect first if already connected
            if ctx.voice_client:
                await ctx.voice_client.disconnect(force=True)
                await asyncio.sleep(1)
            
            # Connect with longer timeout
            print(f"[JOIN] Connecting to {channel.name}...", flush=True)
            vc = await channel.connect(timeout=30.0, reconnect=True)
            
            print(f"[JOIN] Connected: {vc.is_connected()}", flush=True)
            await asyncio.sleep(3)
            print(f"[JOIN] After wait: {vc.is_connected()}", flush=True)
            
            if vc.is_connected():
                await ctx.send(f"✅ Joined {channel.mention}")
            else:
                await ctx.send("⚠️ Connection established but unstable")
        except Exception as e:
            print(f"[JOIN ERROR] {type(e).__name__}: {e}", flush=True)
            await ctx.send(f"❌ Failed to join: {str(e)[:100]}")

    @commands.command(aliases=['l', 'disconnect', 'dc'])
    async def leave(self, ctx):
        """Leave voice channel."""
        if ctx.voice_client:
            try:
                await ctx.voice_client.disconnect(force=True)
                await ctx.send("👋 Left voice channel!")
            except Exception as e:
                await ctx.send(f"❌ Error: {str(e)[:50]}")
        else:
            await ctx.send("❌ Not in voice!")

    @commands.command()
    async def status(self, ctx):
        """Check voice connection status."""
        if not ctx.voice_client:
            return await ctx.send("❌ Not in voice channel!")
        
        vc = ctx.voice_client
        embed = discord.Embed(title="🎙️ Voice Status", color=discord.Color.blue())
        embed.add_field(name="Channel", value=vc.channel.mention if vc.channel else "None", inline=False)
        embed.add_field(name="Connected", value=str(vc.is_connected()), inline=True)
        embed.add_field(name="Playing", value=str(vc.is_playing()), inline=True)
        embed.add_field(name="Latency", value=f"{vc.latency*1000:.0f}ms", inline=True)
        
        await ctx.send(embed=embed)

    @commands.command(aliases=['p'])
    async def play(self, ctx, *, query: str = None):
        """Play music from YouTube."""
        if not query:
            return await ctx.send("❌ Provide a song name!")
        
        # Join if not connected
        if not ctx.voice_client:
            if not ctx.author.voice:
                return await ctx.send("❌ Join a voice channel first!")
            try:
                await ctx.author.voice.channel.connect(timeout=30.0, reconnect=True)
                await asyncio.sleep(2)
            except Exception as e:
                return await ctx.send(f"❌ Failed to join: {str(e)[:50]}")
        
        vc = ctx.voice_client
        
        # Check connection
        if not vc or not vc.is_connected():
            print(f"[PLAY] Not connected: vc={vc}, is_connected={vc.is_connected() if vc else 'None'}", flush=True)
            return await ctx.send("❌ Not connected to voice!")
        
        if vc.is_playing():
            return await ctx.send("⚠️ Already playing! Use !stop first")
        
        await ctx.send(f"🔍 Searching: {query}")
        
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch1:{query}", download=False)
                
                if not info or 'entries' not in info or not info['entries']:
                    return await ctx.send("❌ No results found!")
                
                video = info['entries'][0]
                url = video.get('url')
                title = video.get('title', 'Unknown')
                
                print(f"[PLAY] Found: {title}", flush=True)
                print(f"[PLAY] URL: {url[:50]}...", flush=True)
                
                source = discord.FFmpegPCMAudio(url, **self.ffmpeg_opts)
                
                def after_play(error):
                    if error:
                        print(f"[PLAY] Playback error: {error}", flush=True)
                
                vc.play(source, after=after_play)
                await ctx.send(f"🎵 Playing: **{title}**")
                
        except Exception as e:
            print(f"[PLAY ERROR] {type(e).__name__}: {e}", flush=True)
            await ctx.send(f"❌ Error: {str(e)[:100]}")

    @commands.command(aliases=['s'])
    async def stop(self, ctx):
        """Stop playing."""
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await ctx.send("⏹️ Stopped!")
        else:
            await ctx.send("❌ Nothing playing!")

    @commands.command(aliases=['pa'])
    async def pause(self, ctx):
        """Pause playing."""
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.send("⏸️ Paused!")
        else:
            await ctx.send("❌ Nothing playing!")

    @commands.command(aliases=['res'])
    async def resume(self, ctx):
        """Resume playing."""
        if ctx.voice_client and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send("▶️ Resumed!")
        else:
            await ctx.send("❌ Nothing paused!")

    @commands.command()
    async def queue(self, ctx):
        """Show queue."""
        if not self.queue:
            return await ctx.send("❌ Queue is empty!")
        
        embed = discord.Embed(title="🎵 Queue", color=discord.Color.blue())
        for i, song in enumerate(self.queue[:10], 1):
            embed.add_field(name=f"{i}.", value=song[:50], inline=False)
        
        if len(self.queue) > 10:
            embed.add_field(name="...", value=f"+{len(self.queue) - 10} more", inline=False)
        
        await ctx.send(embed=embed)

    @commands.command()
    async def clear(self, ctx):
        """Clear queue."""
        self.queue.clear()
        await ctx.send("🧹 Queue cleared!")


async def setup(bot):
    print("[MUSIC] Loading Music cog...", flush=True)
    await bot.add_cog(Music(bot))
    print("[MUSIC] Music cog loaded!", flush=True)
