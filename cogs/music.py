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

# FFmpeg detection - Railway runs on Linux, check system paths first
FFMPEG_EXE = None

# Try common Linux paths first
for path in ['/usr/bin/ffmpeg', '/usr/local/bin/ffmpeg', '/bin/ffmpeg']:
    if os.path.exists(path):
        FFMPEG_EXE = path
        break

# If not found, try which command (Unix-like systems)
if not FFMPEG_EXE:
    try:
        result = subprocess.run(['which', 'ffmpeg'], capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            FFMPEG_EXE = result.stdout.strip()
    except Exception:
        pass

# Last resort: Windows fallback for local dev
if not FFMPEG_EXE:
    local_path = os.path.join(os.path.dirname(__file__), '..', 'ffmpeg.exe')
    if os.path.exists(local_path):
        FFMPEG_EXE = local_path

# Log what we found
print(f"ðŸŽµ FFmpeg Detection: {FFMPEG_EXE if FFMPEG_EXE else 'NOT FOUND (will use system default)'}")

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
        # Enable warnings to catch YouTube issues - helps with debugging on Railway
        self.YDL_OPTIONS = {'format': 'bestaudio/best', 'noplaylist': True, 'quiet': False, 'no-warnings': False}
        
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
        # This fixes timing issues on distributed servers like Railway
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
            m.current = None  # Clear current so we don't loop the same song twice

        # 2. Play next song
        if len(m.queue) > 0:
            m.current = m.queue.pop(0)
            m.start_time = time.time()

            status_text = f"Playing: {m.current['title']}"
            print(f"ðŸŽµ {status_text}")
            asyncio.run_coroutine_threadsafe(self.update_vc_status(status_text), self.bot.loop)

            try:
                print(f"ðŸŽµ Creating PCM audio source for: {m.current['title']}")
                source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(m.current['url'], **self.FFMPEG_OPTIONS))
                source.volume = m.volume
                
                # Use guild_id in callback with error handling
                print(f"ðŸŽµ Starting playback with callback to play_next")
                def playback_finished(error):
                    if error:
                        print(f"âŒ Playback error: {error}")
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
                # Skip to next song on error
                if len(m.queue) > 0:
                    self.play_next(guild_id)
        else:
            m.current = None
            print(f"ðŸŽµ Queue empty, waiting for next song")
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
        if not ctx.author.voice:
            return await ctx.send("âŒ Join a voice channel first!")
        
        # Get or create voice client for this guild
        voice_client = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        if not voice_client:
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
                    print(f"ðŸŽ¤ Attempting to join VC (attempt {attempt + 1}/{max_retries})...")
                    # reconnect=False prevents auto-reconnect loops
                    voice_client = await ctx.author.voice.channel.connect(timeout=15.0, reconnect=False)
                    print(f"ðŸŽ¤ Connected to voice, waiting for stabilization...")
                    await asyncio.sleep(2.5)  # Increased to 2.5s for stability
                    
                    # Retry the is_connected check
                    for check_attempt in range(3):
                        if voice_client.is_connected():
                            print(f"âœ… Voice connection stable at check {check_attempt + 1}")
                            break
                        await asyncio.sleep(0.5)
                    else:
                        # All checks failed
                        raise Exception("Voice connection not stable after retries")
                    break  # Success, exit retry loop
                except Exception as e:
                    print(f"âŒ Attempt {attempt + 1} failed: {str(e)}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(1.0)
                    else:
                        error_msg = str(e) if str(e) else "Unable to join voice channel"
                        print(f"Play join error: {error_msg}")
                        return await ctx.send(f"âŒ Can't join: {error_msg[:100]}")

        async with ctx.typing():
            try:
                with yt_dlp.YoutubeDL(self.YDL_OPTIONS) as ydl:
                    search_query = f"ytsearch:{search}" if not search.startswith("http") else search
                    info = ydl.extract_info(search_query, download=False)
                    if 'entries' in info:
                        info = info['entries'][0]

                    self.manager.queue.append(info)
                    await ctx.send(f"âœ… Added to queue: **{info['title']}**")

                    # Always try to play if queue has songs and no music is playing
                    voice_client = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
                    if voice_client and voice_client.is_connected():
                        # If nothing is currently playing, start immediately
                        if not voice_client.is_playing():
                            print(f"ðŸŽµ Starting playback (queue has {len(self.manager.queue)} songs)")
                            self.play_next(ctx.guild.id)
                        else:
                            print(f"ðŸŽµ Music already playing, queued for later")
                            await ctx.send("â³ Added to queue, will play next!")
                    else:
                        print(f"âŒ Voice client not connected after adding to queue")
                        
            except yt_dlp.utils.DownloadError as e:
                if "Sign in to confirm you're not a bot" in str(e):
                    await ctx.send("âŒ YouTube is blocking this request. Try a different song or source.")
                else:
                    await ctx.send(f"âŒ YouTube error: {str(e)[:100]}")
            except Exception as e:
                error_str = str(e).lower()
                print(f"Play error: {str(e)}")
                if "ffmpeg" in error_str or ".exe" in error_str:
                    await ctx.send("âŒ Audio system not ready. FFmpeg may not be installed. Try again in a moment.")
                elif "not found" in error_str:
                    await ctx.send("âŒ Song not found. Try a different search term.")
                else:
                    await ctx.send(f"âŒ Error: {str(e)[:100]}")

    @commands.command(aliases=['q'])
    async def queue(self, ctx: commands.Context):
        """Displays the next 10 songs in the queue."""
        if not self.manager.queue:
            return await ctx.send("The queue is currently empty! â˜•")

        description = ""
        for i, song in enumerate(self.manager.queue[:10], 1):
            description += f"**{i}.** {song['title']}\n"

        embed = discord.Embed(title="ðŸŽ¶ Current Queue", description=description, color=discord.Color.blue())
        await ctx.send(embed=embed)

    @commands.command(aliases=['s'])
    async def skip(self, ctx: commands.Context):
        if not await self.check_voice_channels(ctx):
            return
        ctx.voice_client.stop()
        await ctx.send("â­ï¸ Skipped!")

    @commands.command()
    async def pause(self, ctx: commands.Context):
        if not await self.check_voice_channels(ctx):
            return
        if ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await self.update_vc_status("â˜• Chilling...")
            await ctx.send("â¸ï¸ Paused.")

    @commands.command()
    async def resume(self, ctx: commands.Context):
        if not await self.check_voice_channels(ctx):
            return
        if ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            if self.manager.current:
                await self.update_vc_status(f"ðŸ”Š Playing now: {self.manager.current['title']}")
            await ctx.send("â–¶ï¸ Resumed.")

    @commands.command(aliases=['leave', 'disconnect'])
    async def stop(self, ctx: commands.Context):
        """Stops the music and disconnects the bot."""
        # Get the actual voice client from the bot for this guild
        voice_client = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        
        if not voice_client:
            return await ctx.send("âŒ I'm not in a voice channel!")
        
        # Clear queue and stop music
        self.manager.queue.clear()
        self.manager.current = None
        
        if voice_client.is_playing():
            voice_client.stop()
        
        # Disconnect
        await voice_client.disconnect(force=True)
        await self.update_vc_status("â˜• Chilling...")
        await ctx.send("Disconnected.")

    @commands.command(aliases=['v', 'vol'])
    async def volume(self, ctx: commands.Context, vol: int):
        """Changes the volume (0-200)."""
        if not await self.check_voice_channels(ctx):
            return
        self.manager.volume = vol / 100
        if ctx.voice_client.source:
            ctx.voice_client.source.volume = self.manager.volume
        await ctx.send(f"ðŸ”Š Volume set to {vol}%")

    @commands.command()
    async def join(self, ctx: commands.Context):
        """Join the voice channel."""
        if not ctx.author.voice:
            return await ctx.send("âŒ Join a VC first!")
        
        target_channel = ctx.author.voice.channel
        
        # Check if bot is ALREADY in this exact channel
        voice_client = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        if voice_client and voice_client.is_connected():
            if voice_client.channel == target_channel:
                return await ctx.send("âœ… Already in your channel!")
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
            await self.update_vc_status("â˜• Chilling...")
            await ctx.send("Joined!")
            
        except asyncio.TimeoutError:
            await ctx.send("âŒ Connection timed out. Try again!")
            print(f"âŒ Join timeout for {target_channel.name}")
        except Exception as e:
            error_msg = str(e)[:80]
            await ctx.send(f"âŒ Can't join: {error_msg}")
            print(f"âŒ Join error: {error_msg}")

    @commands.command(aliases=['c'])
    async def clear(self, ctx: commands.Context):
        self.manager.queue.clear()
        await ctx.send("ðŸ§¹ Queue cleared!")

    @commands.command(aliases=['np'])
    async def nowplaying(self, ctx: commands.Context):
        """Shows the currently playing song with player controls."""
        if not self.manager.current:
            return await ctx.send("No song is currently playing! â˜•")
        await self.send_now_playing(ctx)

    @commands.command()
    async def ffmpegtest(self, ctx: commands.Context):
        """DEBUG: Check FFmpeg status on the server."""
        import shutil
        ffmpeg_path = shutil.which('ffmpeg')
        
        status = f"""
ðŸŽµ **FFmpeg Debug Info:**
- Detected path: `{FFMPEG_EXE or 'Not found'}`
- In PATH: `{ffmpeg_path or 'Not found'}`
- FFMPEG_OPTIONS: `{self.FFMPEG_OPTIONS}`
- Bot voice clients: `{len(self.bot.voice_clients)}`
        """
        await ctx.send(status)


async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
