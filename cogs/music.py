import os
import time
import random
import asyncio
import logging
import subprocess

import discord
from discord.ext import commands
import yt_dlp

logging.basicConfig(level=logging.INFO)

# FFmpeg detection - check standard Linux paths
FFMPEG_EXE = None

# Try common Linux paths (Dockerfile installs to /usr/bin)
for path in ['/usr/bin/ffmpeg', '/usr/local/bin/ffmpeg', '/bin/ffmpeg']:
    if os.path.exists(path):
        FFMPEG_EXE = path
        break

# If not found, try which command (Unix-like systems)
if not FFMPEG_EXE:
    try:
        result = subprocess.run(['which', 'ffmpeg'], capture_output=True, text=True, timeout=2)
        if result.returncode == 0 and result.stdout.strip():
            FFMPEG_EXE = result.stdout.strip()
    except Exception:
        pass

# Windows fallback for local dev
if not FFMPEG_EXE:
    local_path = os.path.join(os.path.dirname(__file__), '..', 'ffmpeg.exe')
    if os.path.exists(local_path):
        FFMPEG_EXE = local_path

# Log result
if FFMPEG_EXE:
    print(f"ðŸŽµ FFmpeg Detection: FOUND at {FFMPEG_EXE}")
else:
    print(f"ðŸŽµ FFmpeg Detection: NOT FOUND")

# DEBUG: Check if ffmpeg exists in common locations
import shutil
ffmpeg_in_path = shutil.which('ffmpeg')
print(f"ðŸŽµ FFmpeg in PATH: {ffmpeg_in_path}")


class MusicManager:
    def __init__(self):
        self.queue = []
        self.current = None
        self.start_time = 0
        self.volume = 0.5
        self.player_message = None
        self.text_channel = None
        self.loop_mode = 0  # 0 = Off, 1 = Single Song, 2 = Whole Queue


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.manager = MusicManager()
        # Add proper User-Agent to bypass YouTube bot detection
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
        
        # Build FFMPEG options - only set executable if explicitly found
        self.FFMPEG_OPTIONS = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn -b:a 128k'
        }
        if FFMPEG_EXE:
            self.FFMPEG_OPTIONS['executable'] = FFMPEG_EXE
        
        print(f"ðŸŽµ Music Cog Ready - FFmpeg: {FFMPEG_EXE or 'system default'}")

    async def check_voice_channels(self, ctx: commands.Context) -> bool:
        if not ctx.voice_client:
            await ctx.send("ðŸŽ§ I'm not in a voice channel!")
            return False
        if not ctx.author.voice or ctx.author.voice.channel != ctx.voice_client.channel:
            await ctx.send("ðŸš« You must be in my voice channel!")
            return False
        return True

    async def update_vc_status(self, text: str):
        """Updates the Bot's Activity AND the Voice Channel Status bubble."""
        # Keep text plain to avoid encoding issues
        await self.bot.change_presence(activity=discord.Game(name=text))
        for vc in self.bot.voice_clients:
            try:
                # Note: The bot MUST have 'Manage Channels' permission for this to work
                await vc.channel.edit(status=text[:128])  # Max 128 chars for status
            except Exception as e:
                pass

    class PlayerView(discord.ui.View):
        def __init__(self, cog: 'Music', ctx: commands.Context, song_info: dict):
            super().__init__(timeout=None)
            self.cog = cog
            self.ctx = ctx
            self.song_info = song_info

        def create_embed(self):
            m = self.cog.manager
            elapsed = int(time.time() - m.start_time) if m.start_time > 0 else 0
            total = self.song_info.get('duration', 0) or 0
            bar_size = 15
            progress = int((elapsed / total) * bar_size) if total > 0 else 0
            bar = "â–¬" * progress + "ðŸ”˜" + "â–¬" * max(0, bar_size - progress - 1)

            def fmt(s): return f"{s//60:02d}:{s%60:02d}"
            loop_statuses = ["Off", "ðŸ”‚ Song", "ðŸ” Queue"]

            embed = discord.Embed(
                title=self.song_info.get('title', 'Playing'),
                url=self.song_info.get('webpage_url'),
                color=discord.Color.from_rgb(30, 30, 30)
            )
            embed.set_thumbnail(url=self.song_info.get('thumbnail'))
            embed.add_field(name="Timeline", value=f"`{fmt(elapsed)}` {bar} `{fmt(total)}`", inline=False)
            embed.add_field(name="Status", value=f"ðŸ”Š {int(m.volume * 100)}% | ðŸ”„ Loop: {loop_statuses[m.loop_mode]}", inline=True)
            embed.add_field(name="Queue", value=f"ðŸŽ¶ {len(m.queue)} songs", inline=True)
            return embed

        @discord.ui.button(label="Pause/Resume", style=discord.ButtonStyle.blurple, row=0)
        async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.ctx.voice_client.is_playing():
                self.ctx.voice_client.pause()
                await self.cog.update_vc_status("â˜• Chilling...")
                await interaction.response.send_message("â¸ï¸ Music paused.", ephemeral=True)
            elif self.ctx.voice_client.is_paused():
                self.ctx.voice_client.resume()
                await self.cog.update_vc_status(f"ðŸ”Š Playing now: {self.song_info['title']}")
                await interaction.response.send_message("â–¶ï¸ Music resumed.", ephemeral=True)
            await interaction.message.edit(embed=self.create_embed(), view=self)

        @discord.ui.button(emoji="ðŸ”€", style=discord.ButtonStyle.gray, row=0)
        async def shuffle_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if len(self.cog.manager.queue) < 2:
                return await interaction.response.send_message("Not enough songs to shuffle!", ephemeral=True)
            random.shuffle(self.cog.manager.queue)
            await interaction.response.send_message("ðŸ”€ Queue shuffled!", ephemeral=True)
            await interaction.message.edit(embed=self.create_embed(), view=self)

        @discord.ui.button(label="Loop: Off", style=discord.ButtonStyle.gray, row=0)
        async def loop_toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
            m = self.cog.manager
            m.loop_mode = (m.loop_mode + 1) % 3
            modes = ["Loop: Off", "Loop: Song", "Loop: Queue"]
            button.label = modes[m.loop_mode]
            await interaction.response.edit_message(embed=self.create_embed(), view=self)

        @discord.ui.button(emoji="â®ï¸", style=discord.ButtonStyle.gray, row=1)
        async def restart_song(self, interaction: discord.Interaction, button: discord.ui.Button):
            if not await self.cog.check_voice_channels(self.ctx):
                return
            await interaction.response.defer()
            self.ctx.voice_client.stop()
            self.cog.manager.queue.insert(0, self.song_info)
            await interaction.followup.send("â®ï¸ Restarting song...", ephemeral=True)

        @discord.ui.button(emoji="âª", style=discord.ButtonStyle.gray, row=1)
        async def backward(self, interaction: discord.Interaction, button: discord.ui.Button):
            await self.seek_helper(interaction, -10)

        @discord.ui.button(emoji="â©", style=discord.ButtonStyle.gray, row=1)
        async def forward(self, interaction: discord.Interaction, button: discord.ui.Button):
            await self.seek_helper(interaction, 10)

        @discord.ui.button(emoji="â­ï¸", style=discord.ButtonStyle.gray, row=1)
        async def skip_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.ctx.voice_client.stop()
            await interaction.response.send_message("â­ï¸ Skipped!", ephemeral=True)

        @discord.ui.button(emoji="ðŸ”‰", style=discord.ButtonStyle.gray, row=2)
        async def vol_down(self, interaction: discord.Interaction, button: discord.ui.Button):
            m = self.cog.manager
            m.volume = max(0.0, m.volume - 0.1)
            if self.ctx.voice_client and self.ctx.voice_client.source:
                try:
                    self.ctx.voice_client.source.volume = m.volume
                except Exception:
                    pass
            await interaction.response.send_message(f"ðŸ”Š Volume set to {int(m.volume*100)}%", ephemeral=True)
            await interaction.message.edit(embed=self.create_embed(), view=self)

        @discord.ui.button(emoji="ðŸ”Š", style=discord.ButtonStyle.gray, row=2)
        async def vol_up(self, interaction: discord.Interaction, button: discord.ui.Button):
            m = self.cog.manager
            m.volume = min(2.0, m.volume + 0.1)
            if self.ctx.voice_client and self.ctx.voice_client.source:
                try:
                    self.ctx.voice_client.source.volume = m.volume
                except Exception:
                    pass
            await interaction.response.send_message(f"ðŸ”Š Volume set to {int(m.volume*100)}%", ephemeral=True)
            await interaction.message.edit(embed=self.create_embed(), view=self)

        async def seek_helper(self, interaction: discord.Interaction, seconds: int):
            if not await self.cog.check_voice_channels(self.ctx):
                return
            await interaction.response.defer()
            m = self.cog.manager
            elapsed = int(time.time() - m.start_time) if m.start_time else 0
            new_time = max(0, elapsed + seconds)
            if self.ctx.voice_client:
                try:
                    if self.ctx.voice_client.source:
                        self.ctx.voice_client.source.cleanup()
                except Exception:
                    pass
                self.ctx.voice_client.stop()
                await asyncio.sleep(0.5)
                opts = dict(self.cog.FFMPEG_OPTIONS)
                opts['before_options'] = f"-ss {new_time} " + self.cog.FFMPEG_OPTIONS['before_options']
                source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(self.song_info['url'], **opts))
                source.volume = m.volume
                m.queue.insert(0, self.song_info)
                self.ctx.voice_client.play(source, after=lambda e: self.cog.play_next(self.ctx.guild.id))
                m.start_time = time.time() - new_time
                await interaction.message.edit(embed=self.create_embed(), view=self)

    # Note: play_next is now guild-based and called via 'after' callback automatically

    def play_next(self, guild_id: int):
        """Play next song in queue using guild_id (not context-dependent)."""
        m = self.manager
        
        # Get voice client using guild_id (not context-specific)
        guild = self.bot.get_guild(guild_id)
        if not guild:
            print(f"âŒ Guild {guild_id} not found")
            return
        
        voice_client = discord.utils.get(self.bot.voice_clients, guild=guild)
        if not voice_client:
            print(f"âŒ No voice client for guild {guild_id}")
            m.current = None
            return
        
        # CRITICAL: Check if voice client is actually connected before playing
        if not voice_client.is_connected():
            print(f"âŒ Voice client exists but NOT CONNECTED for guild {guild_id}")
            m.current = None
            return
        
        # Small delay to ensure voice connection is truly ready before playback
        time.sleep(0.2)
        
        print(f"ðŸŽµ play_next called: queue_len={len(m.queue)}, is_playing={voice_client.is_playing()}")
        
        # Cleanup previous source if still exists
        try:
            if hasattr(voice_client, 'source') and voice_client.source:
                voice_client.source.cleanup()
        except Exception as e:
            print(f"âš ï¸ Source cleanup error: {e}")

        # 1. Handle Loop Modes
        if m.current:
            if m.loop_mode == 1:
                m.queue.insert(0, m.current)
            elif m.loop_mode == 2:
                m.queue.append(m.current)
            m.current = None

        # 2. Play next song
        if len(m.queue) > 0:
            m.current = m.queue.pop(0)
            m.start_time = time.time()

            status_text = f"Playing: {m.current['title']}"
            print(f"ðŸŽµ {status_text}")
            asyncio.run_coroutine_threadsafe(self.update_vc_status(status_text), self.bot.loop)

            try:
                print(f"ðŸŽµ Creating audio source for: {m.current['title']}")
                print(f"ðŸŽµ FFmpeg path: {FFMPEG_EXE}")
                print(f"ðŸŽµ URL: {m.current['url'][:80]}...")
                
                # Create audio source with FFmpeg
                source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(
                    m.current['url'], 
                    **self.FFMPEG_OPTIONS
                ))
                source.volume = m.volume
                
                print(f"ðŸŽµ Audio source created, starting playback...")
                
                def playback_finished(error):
                    if error:
                        print(f"âŒ Playback error: {error}")
                    else:
                        print(f"âœ… Song finished, playing next...")
                    self.play_next(guild_id)
                
                voice_client.play(source, after=playback_finished)
                print(f"âœ… Playback started for {m.current['title']}")
                
                asyncio.run_coroutine_threadsafe(self.update_vc_status(status_text), self.bot.loop)
            except Exception as e:
                print(f"âŒ Play Error: {type(e).__name__}: {str(e)}")
                import traceback
                traceback.print_exc()
                asyncio.run_coroutine_threadsafe(self.update_vc_status("Chilling..."), self.bot.loop)
                m.current = None
                if len(m.queue) > 0:
                    self.play_next(guild_id)
        else:
            m.current = None
            print(f"ðŸŽµ Queue empty")
            asyncio.run_coroutine_threadsafe(self.update_vc_status("Chilling..."), self.bot.loop)

    async def send_now_playing(self, ctx: commands.Context):
        m = self.manager
        if not m.current:
            return
        view = self.PlayerView(self, ctx, m.current)
        embed = view.create_embed()
        if m.player_message:
            try:
                await m.player_message.delete()
            except Exception:
                pass
        m.player_message = await ctx.send(embed=embed, view=view)

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'ðŸŽµ Music cog loaded!')
        self.bot.loop.create_task(self.idle_check())
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Handle voice state changes - clean up if bot disconnected"""
        if member == self.bot.user:
            if before.channel and not after.channel:
                # Bot was disconnected (intentional disconnect, not a reconnect loop)
                self.manager.queue.clear()
                self.manager.current = None
                print("ðŸŽµ Bot disconnected from voice channel - cleaning up queue")

    async def idle_check(self):
        """Disabled: was causing bot to disconnect after 3 mins of silence"""
        return

    # --- COMMANDS ---

    @commands.command(aliases=['p'])
    async def play(self, ctx: commands.Context, *, search: str):
        """Plays a song from YouTube."""
        print(f"ðŸŽµ PLAY command called: search='{search}'")
        
        if not ctx.author.voice:
            print(f"âŒ User not in voice channel")
            return await ctx.send("Join a voice channel first!")
        
        print(f"ðŸŽµ User in voice channel: {ctx.author.voice.channel.name}")
        
        # Get or create voice client for this guild
        voice_client = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        if not voice_client:
            print(f"ðŸŽµ No existing voice client, attempting to join...")
            # If bot is already in a different channel, disconnect first
            existing_vc = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
            if existing_vc and existing_vc.channel != ctx.author.voice.channel:
                print(f"ðŸŽ¤ Bot in different channel, disconnecting first...")
                await existing_vc.disconnect(force=True)
                await asyncio.sleep(1.0)
            
            # Retry logic for joining voice
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    print(f"ðŸŽ¤ Join attempt {attempt + 1}/{max_retries}...")
                    voice_client = await ctx.author.voice.channel.connect(timeout=15.0, reconnect=False)
                    print(f"ðŸŽ¤ Connected to voice")
                    await asyncio.sleep(2.5)
                    
                    for check_attempt in range(3):
                        if voice_client.is_connected():
                            print(f"âœ… Voice connection stable")
                            break
                        await asyncio.sleep(0.5)
                    else:
                        raise Exception("Voice connection not stable after retries")
                    break
                except Exception as e:
                    print(f"âŒ Join attempt {attempt + 1} failed: {str(e)}")
                    error_str = str(e).lower()
                    
                    await asyncio.sleep(1.5)
                    voice_client = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
                    if voice_client and voice_client.is_connected():
                        print(f"âœ… Voice connection established (ignoring error)")
                        break
                    
                    if attempt < max_retries - 1:
                        await asyncio.sleep(1.0)
                    else:
                        print(f"âŒ Could not join voice after {max_retries} attempts")
                        return

        print(f"âœ… Voice client ready: is_connected={voice_client.is_connected()}")

        async with ctx.typing():
            try:
                print(f"ðŸŽµ Searching YouTube for: {search}")
                with yt_dlp.YoutubeDL(self.YDL_OPTIONS) as ydl:
                    search_query = f"ytsearch:{search}" if not search.startswith("http") else search
                    info = ydl.extract_info(search_query, download=False)
                    if 'entries' in info:
                        info = info['entries'][0]

                    print(f"âœ… Found song: {info['title']}")
                    self.manager.queue.append(info)
                    print(f"ðŸŽµ Added to queue. Queue length: {len(self.manager.queue)}")
                    await ctx.send(f"Added to queue: **{info['title']}**")

                    # Always try to play if queue has songs and no music is playing
                    voice_client = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
                    if voice_client and voice_client.is_connected():
                        print(f"âœ… Voice client connected, checking if playing...")
                        # If nothing is currently playing, start immediately
                        if not voice_client.is_playing():
                            print(f"ðŸŽµ Starting playback (queue: {len(self.manager.queue)} songs)")
                            self.play_next(ctx.guild.id)
                        else:
                            print(f"ðŸŽµ Music already playing, song queued for later")
                            await ctx.send("Added to queue, will play next!")
                    else:
                        print(f"âŒ Voice client not connected after adding to queue")
                        
            except yt_dlp.utils.DownloadError as e:
                print(f"âŒ YouTube error: {str(e)}")
                if "Sign in to confirm you're not a bot" in str(e):
                    await ctx.send("YouTube is blocking this request. Try a different song or source.")
                else:
                    await ctx.send(f"YouTube error: {str(e)[:100]}")
            except Exception as e:
                error_str = str(e).lower()
                print(f"âŒ Play error: {type(e).__name__}: {str(e)}")
                import traceback
                traceback.print_exc()
                if "ffmpeg" in error_str or ".exe" in error_str:
                    await ctx.send("Audio system not ready. FFmpeg may not be installed. Try again in a moment.")
                elif "not found" in error_str:
                    await ctx.send("Song not found. Try a different search term.")
                else:
                    await ctx.send(f"Error: {str(e)[:100]}")

    @commands.command(aliases=['q'])
    async def queue(self, ctx: commands.Context):
        """Displays the next 10 songs in the queue."""
        if not self.manager.queue:
            return await ctx.send("The queue is currently empty!")

        description = ""
        for i, song in enumerate(self.manager.queue[:10], 1):
            description += f"**{i}.** {song['title']}\n"

        embed = discord.Embed(title="Current Queue", description=description, color=discord.Color.blue())
        await ctx.send(embed=embed)

    @commands.command(aliases=['s'])
    async def skip(self, ctx: commands.Context):
        if not await self.check_voice_channels(ctx):
            return
        ctx.voice_client.stop()
        await ctx.send("Skipped!")

    @commands.command()
    async def pause(self, ctx: commands.Context):
        if not await self.check_voice_channels(ctx):
            return
        if ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await self.update_vc_status("Paused")
            await ctx.send("Paused.")

    @commands.command()
    async def resume(self, ctx: commands.Context):
        if not await self.check_voice_channels(ctx):
            return
        if ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            if self.manager.current:
                await self.update_vc_status(f"Playing: {self.manager.current['title']}")
            await ctx.send("Resumed.")

    @commands.command(aliases=['leave', 'disconnect'])
    async def stop(self, ctx: commands.Context):
        """Stops the music and disconnects the bot."""
        # Get the actual voice client from the bot for this guild
        voice_client = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        
        if not voice_client:
            return await ctx.send("I'm not in a voice channel!")
        
        # Clear queue and stop music
        self.manager.queue.clear()
        self.manager.current = None
        
        if voice_client.is_playing():
            voice_client.stop()
        
        # Disconnect
        await voice_client.disconnect(force=True)
        await self.update_vc_status("Chilling...")
        await ctx.send("Disconnected.")

    @commands.command(aliases=['v', 'vol'])
    async def volume(self, ctx: commands.Context, vol: int):
        """Changes the volume (0-200)."""
        if not await self.check_voice_channels(ctx):
            return
        self.manager.volume = vol / 100
        if ctx.voice_client.source:
            ctx.voice_client.source.volume = self.manager.volume
        await ctx.send(f"Volume set to {vol}%")

    @commands.command()
    async def join(self, ctx: commands.Context):
        """Join the voice channel."""
        if not ctx.author.voice:
            return await ctx.send("Join a VC first!")
        
        target_channel = ctx.author.voice.channel
        
        # Check if bot is ALREADY in this exact channel
        voice_client = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        if voice_client and voice_client.is_connected():
            if voice_client.channel == target_channel:
                return await ctx.send("Already in your channel!")
            else:
                # In different channel - disconnect first before joining new one
                print(f"ðŸŽ¤ Bot in {voice_client.channel.name}, moving to {target_channel.name}...")
                await voice_client.disconnect(force=True)
                await asyncio.sleep(1.0)  # Wait for clean disconnect
        
        # Try to join - Discord auto-disconnects from old channels
        try:
            print(f"ðŸŽ¤ Joining {target_channel.name}...")
            # reconnect=False prevents auto-reconnect loops that cause the bot to rejoin after disconnect
            voice_client = await target_channel.connect(timeout=10.0, reconnect=False)
            
            # Railway needs more time for connection to be fully established
            print(f"ðŸŽ¤ Voice connected, waiting for stabilization...")
            await asyncio.sleep(2.5)  # Increased to 2.5s for distributed server stability
            
            # Multi-check to ensure connection is truly stable
            for check in range(3):
                if voice_client.is_connected():
                    print(f"âœ… Connection verified at check {check + 1}")
                    break
                await asyncio.sleep(0.3)
            else:
                await ctx.send("âŒ Failed to connect to voice!")
                return
            
            print(f"âœ… Joined {target_channel.name}")
            await self.update_vc_status("Chilling...")
            await ctx.send("Joined!")
            
        except asyncio.TimeoutError:
            await ctx.send("Connection timed out. Try again!")
            print(f"âŒ Join timeout for {target_channel.name}")
        except Exception as e:
            error_msg = str(e)
            # Don't show 4006 errors to user - they often succeed anyway
            if "4006" not in error_msg:
                await ctx.send(f"Can't join: {error_msg[:80]}")
            print(f"âŒ Join error: {error_msg}")

    @commands.command()
    async def ffmpeg(self, ctx: commands.Context):
        """Check FFmpeg status and system info."""
        ffmpeg_status = "Found" if FFMPEG_EXE else "NOT FOUND"
        ffmpeg_path = FFMPEG_EXE or "Not installed"
        
        embed = discord.Embed(title="FFmpeg Status", color=discord.Color.green() if FFMPEG_EXE else discord.Color.red())
        embed.add_field(name="Status", value=ffmpeg_status, inline=False)
        embed.add_field(name="Path", value=f"`{ffmpeg_path}`", inline=False)
        embed.add_field(name="System", value=f"Python {__import__('sys').version.split()[0]}", inline=False)
        
        # Try to get FFmpeg version
        try:
            result = subprocess.run([FFMPEG_EXE or 'ffmpeg', '-version'], capture_output=True, text=True, timeout=2)
            version_line = result.stdout.split('\n')[0] if result.stdout else "Unable to get version"
            embed.add_field(name="Version", value=f"```{version_line}```", inline=False)
        except:
            embed.add_field(name="Version", value="Unable to detect", inline=False)
        
        await ctx.send(embed=embed)

    @commands.command()
    async def test(self, ctx: commands.Context):
        """Test if FFmpeg and voice connection work."""
        if not ctx.author.voice:
            return await ctx.send("Join a voice channel first!")
        
        voice_client = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        if not voice_client:
            try:
                voice_client = await ctx.author.voice.channel.connect(timeout=10.0, reconnect=False)
                await ctx.send("Joined voice channel")
            except Exception as e:
                return await ctx.send(f"Can't join voice: {str(e)[:80]}")
        
        # Test FFmpeg
        await ctx.send(f"FFmpeg path: `{FFMPEG_EXE or 'system default'}`")
        await ctx.send(f"FFMPEG_OPTIONS: ```{self.FFMPEG_OPTIONS}```")
        
        # Test if voice client can play
        if voice_client.is_connected():
            await ctx.send("Voice connection: OK")
        else:
            await ctx.send("Voice connection: FAILED")

    @commands.command(aliases=['c'])
    async def clear(self, ctx: commands.Context):
        self.manager.queue.clear()
        await ctx.send("ðŸ§¹ Queue cleared!")

    @commands.command(aliases=['np'])
    async def nowplaying(self, ctx: commands.Context):
        """Shows the currently playing song with player controls."""
        if not self.manager.current:
            return await ctx.send("No song is currently playing!")
        await self.send_now_playing(ctx)



async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
