"""
Discord Voice Bot Service for Virtual Soundboard
================================================
Streams processed soundboard audio (with real-time Pitch, Speed, Echo, Reverb DSP)
directly into Discord Voice Channels.

Runs asynchronously in a background daemon thread alongside Flask.
"""

import os
import io
import asyncio
import threading
import logging
import soundfile as sf
import numpy as np

# Suppress overly verbose discord gateway logs
logging.getLogger('discord').setLevel(logging.WARNING)

try:
    import discord
    from discord.ext import commands
    DISCORD_AVAILABLE = True
    BasePCMAudio = discord.PCMAudio
except (ImportError, Exception):
    discord = None
    commands = None
    DISCORD_AVAILABLE = False
    BasePCMAudio = object


class DiscordAudioSource(BasePCMAudio):
    """Custom PCM Audio Source from in-memory raw 16-bit 48kHz stereo bytes."""
    def __init__(self, raw_bytes):
        self.stream = io.BytesIO(raw_bytes)
        if DISCORD_AVAILABLE and hasattr(super(), '__init__'):
            super().__init__(self.stream)


class DiscordService:
    def __init__(self, config_manager=None, audio_engine=None):
        self.config_manager = config_manager
        self.audio_engine = audio_engine
        self.bot = None
        self.loop = None
        self.thread = None
        self.voice_client = None
        self.is_running = False
        self.lock = threading.Lock()

        # Load credentials from environment or config
        self.token = os.environ.get('DISCORD_BOT_TOKEN')
        self.default_guild_id = os.environ.get('DISCORD_GUILD_ID')
        self.default_channel_id = os.environ.get('DISCORD_VOICE_CHANNEL_ID')

        if not self.token and self.config_manager:
            self.token = self.config_manager.config.get('discord_token')
            self.default_guild_id = self.config_manager.config.get('discord_guild_id')
            self.default_channel_id = self.config_manager.config.get('discord_channel_id')

    def start(self):
        """Start Discord Bot event loop in a background daemon thread."""
        if not DISCORD_AVAILABLE:
            print("[DiscordService] discord.py or PyNaCl not installed. Discord streaming disabled.")
            return False

        if not self.token:
            print("[DiscordService] No DISCORD_BOT_TOKEN provided. Discord bot is idle (configure via settings or .env).")
            return False

        if self.is_running:
            return True

        self.thread = threading.Thread(target=self._run_bot_thread, daemon=True, name="DiscordBotThread")
        self.thread.start()
        return True

    def _run_bot_thread(self):
        """Background thread target setting up dedicated asyncio loop."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        intents.guilds = True

        self.bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

        @self.bot.event
        async def on_ready():
            self.is_running = True
            print(f"[DiscordService] Logged in as {self.bot.user} (ID: {self.bot.user.id})")
            # Auto-join default voice channel if configured
            if self.default_channel_id:
                try:
                    await self._join_channel_internal(int(self.default_channel_id))
                except Exception as e:
                    print(f"[DiscordService] Auto-join notice: {e}")

        @self.bot.command(name="join")
        async def cmd_join(ctx):
            """Join author's voice channel."""
            if ctx.author.voice and ctx.author.voice.channel:
                channel = ctx.author.voice.channel
                await channel.connect()
                await ctx.send(f"🔊 Joined **{channel.name}**!")
            else:
                await ctx.send("❌ You are not connected to a voice channel.")

        @self.bot.command(name="leave")
        async def cmd_leave(ctx):
            """Disconnect from voice channel."""
            if ctx.voice_client:
                await ctx.voice_client.disconnect()
                await ctx.send("👋 Disconnected from voice channel.")
            else:
                await ctx.send("Not connected to any voice channel.")

        @self.bot.command(name="sounds")
        async def cmd_sounds(ctx):
            """List available sound clips."""
            if not self.config_manager:
                return
            sounds = self.config_manager.config.get('sounds', [])
            names = [s.get('name') for s in sounds[:25]]
            list_str = ", ".join(f"`{n}`" for n in names)
            await ctx.send(f"🎵 **Soundboard Clips ({len(sounds)} total):**\n{list_str}")

        try:
            self.loop.run_until_complete(self.bot.start(self.token))
        except Exception as e:
            print(f"[DiscordService] Bot error or shutdown: {e}")
        finally:
            self.is_running = False

    async def _join_channel_internal(self, channel_id):
        channel = self.bot.get_channel(int(channel_id))
        if not channel or not isinstance(channel, discord.VoiceChannel):
            return False, "Channel not found or not a voice channel"

        # Check existing voice client in this guild
        voice_client = channel.guild.voice_client
        if voice_client:
            if voice_client.channel.id == channel.id:
                self.voice_client = voice_client
                return True, f"Already connected to {channel.name}"
            await voice_client.move_to(channel)
            self.voice_client = voice_client
            return True, f"Moved to {channel.name}"
        else:
            self.voice_client = await channel.connect()
            return True, f"Connected to {channel.name}"

    def join_channel(self, channel_id):
        """Threadsafe call to join a voice channel."""
        if not self.is_running or not self.loop:
            return False, "Discord Bot is not running. Check Bot Token in settings."

        future = asyncio.run_coroutine_threadsafe(
            self._join_channel_internal(channel_id),
            self.loop
        )
        try:
            return future.result(timeout=10)
        except Exception as e:
            return False, str(e)

    def leave_channel(self):
        """Threadsafe call to leave voice channel."""
        if not self.is_running or not self.loop:
            return False, "Discord Bot is not running"

        async def _leave():
            for vc in list(self.bot.voice_clients):
                await vc.disconnect(force=True)
            self.voice_client = None
            return True, "Disconnected from voice"

        future = asyncio.run_coroutine_threadsafe(_leave(), self.loop)
        try:
            return future.result(timeout=5)
        except Exception as e:
            return False, str(e)

    def play_audio_array(self, audio_data: np.ndarray, sr: int = 48000):
        """
        Stream a float32 audio array (with DSP Pitch/Speed/Echo/Reverb) to active Discord voice client.
        Converts array to 48kHz 16-bit stereo PCM for Discord Opus encoder.
        """
        if not self.is_running or not self.loop:
            return False

        async def _play():
            active_vc = None
            if self.voice_client and self.voice_client.is_connected():
                active_vc = self.voice_client
            elif self.bot and self.bot.voice_clients:
                active_vc = self.bot.voice_clients[0]

            if not active_vc or not active_vc.is_connected():
                return False

            if active_vc.is_playing():
                active_vc.stop()

            # Resample to 48,000 Hz if needed (Discord standard sample rate)
            from scipy import signal
            target_sr = 48000
            data = audio_data
            if sr != target_sr:
                new_len = int(len(data) * target_sr / sr)
                data = signal.resample(data, new_len).astype(np.float32)

            # Ensure 2 channels
            if data.ndim == 1:
                data = np.column_stack((data, data))
            elif data.shape[1] > 2:
                data = data[:, :2]

            # Convert float32 [-1.0, 1.0] to 16-bit PCM bytes
            pcm16 = (np.clip(data, -1.0, 1.0) * 32767.0).astype(np.int16)
            raw_bytes = pcm16.tobytes()

            source = DiscordAudioSource(raw_bytes)
            active_vc.play(source)
            return True

        future = asyncio.run_coroutine_threadsafe(_play(), self.loop)
        try:
            return future.result(timeout=2)
        except Exception as e:
            print(f"[DiscordService] Playback error: {e}")
            return False

    def get_status(self):
        """Return real-time Discord connection status."""
        configured = bool(self.token)
        connected = bool(self.is_running and self.bot and self.bot.is_ready())
        voice_connected = False
        channel_name = None
        guild_name = None
        channel_id = None
        available_channels = []

        if connected and self.bot:
            for vc in self.bot.voice_clients:
                if vc.is_connected() and vc.channel:
                    voice_connected = True
                    channel_name = vc.channel.name
                    guild_name = vc.guild.name
                    channel_id = str(vc.channel.id)
                    break

            for guild in self.bot.guilds:
                for ch in guild.voice_channels:
                    available_channels.append({
                        'id': str(ch.id),
                        'name': f"{guild.name} ➔ #{ch.name}",
                        'guild_id': str(guild.id),
                        'guild_name': guild.name
                    })

        return {
            'configured': configured,
            'connected': connected,
            'user': str(self.bot.user) if (connected and self.bot and self.bot.user) else None,
            'voice_connected': voice_connected,
            'channel_name': channel_name,
            'guild_name': guild_name,
            'channel_id': channel_id,
            'available_channels': available_channels
        }

    def update_config(self, token=None, guild_id=None, channel_id=None):
        """Update Discord credentials and restart bot if token changed."""
        token_changed = False
        if token is not None and token.strip() != self.token:
            self.token = token.strip() if token.strip() else None
            token_changed = True
        if guild_id is not None:
            self.default_guild_id = str(guild_id).strip()
        if channel_id is not None:
            self.default_channel_id = str(channel_id).strip()

        if self.config_manager:
            self.config_manager.config['discord_token'] = self.token
            self.config_manager.config['discord_guild_id'] = self.default_guild_id
            self.config_manager.config['discord_channel_id'] = self.default_channel_id
            self.config_manager.save_config()

        if token_changed:
            self.stop()
            if self.token:
                self.start()

        return self.get_status()

    def stop(self):
        """Disconnect and stop the bot."""
        if self.is_running and self.loop and self.bot:
            async def _close():
                for vc in list(self.bot.voice_clients):
                    await vc.disconnect(force=True)
                await self.bot.close()

            asyncio.run_coroutine_threadsafe(_close(), self.loop)
            self.is_running = False
            self.voice_client = None
