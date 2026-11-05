"""
Discord Voice Bot Service for Virtual Soundboard
================================================
Streams processed soundboard audio (with real-time Pitch, Speed, Echo, Reverb DSP)
directly into Discord Voice Channels.

Supports full polyphony: multiple sounds and multiple copies of the same sound
play simultaneously over each other without cutting off.
"""

import os
import io
import asyncio
import threading
import logging
import soundfile as sf
import numpy as np

# Suppress overly verbose discord gateway logs
# Enable voice logging for deep diagnostics
logging.getLogger('discord').setLevel(logging.WARNING)
logging.getLogger('discord.voice_client').setLevel(logging.DEBUG)
logging.getLogger('discord.player').setLevel(logging.DEBUG)
logging.getLogger('discord.voice_state').setLevel(logging.DEBUG)
logging.getLogger('discord.gateway').setLevel(logging.INFO)

try:
    import discord
    from discord.ext import commands
    import struct
    DISCORD_AVAILABLE = True
    BasePCMAudio = discord.PCMAudio
    # Ensure Opus is loaded on Linux
    if not discord.opus.is_loaded():
        for opus_lib in ['libopus.so.0', 'libopus.so', '/usr/lib/x86_64-linux-gnu/libopus.so.0', '/usr/lib/aarch64-linux-gnu/libopus.so.0']:
            try:
                discord.opus.load_opus(opus_lib)
                break
            except Exception:
                pass

    # --- DAVE Protocol State-Machine Patch for discord.py 2.7.x ---
    # discord.py 2.7.x connects to DAVE (E2EE) voice channels, but its gateway handler
    # omits calls to state.dave_session.prepare_transition(...) and execute_transition(...),
    # causing dave_session.ready to remain False and unencrypted Opus frames to be dropped.
    try:
        import davey
        import discord.gateway
        import discord.voice_state

        _orig_recv_binary = discord.gateway.DiscordVoiceWebSocket.received_binary_message

        async def _patched_recv_binary(self, msg: bytes) -> None:
            self.seq_ack = struct.unpack_from('>H', msg, 0)[0]
            op = msg[2]
            state = self._connection

            if state.dave_session is not None:
                if op == self.MLS_PROPOSALS:
                    optype = msg[3]
                    try:
                        result = state.dave_session.process_proposals(
                            davey.ProposalsOperationType.append if optype == 0 else davey.ProposalsOperationType.revoke, msg[4:]
                        )
                        if isinstance(result, davey.CommitWelcome):
                            await self.send_binary(
                                discord.gateway.DiscordVoiceWebSocket.MLS_COMMIT_WELCOME,
                                result.commit + result.welcome if result.welcome else result.commit,
                            )
                            print(f"[DiscordService-DAVE] Generated and sent MLS commit & welcome to Discord gateway")
                    except Exception as pe:
                        print(f"[DiscordService-DAVE] Proposals processing notice: {pe}")
                    return

                elif op == self.MLS_ANNOUNCE_COMMIT_TRANSITION:
                    transition_id = struct.unpack_from('>H', msg, 3)[0]
                    try:
                        state.dave_session.process_commit(msg[5:])
                        try:
                            state.dave_session.prepare_transition(transition_id, state.dave_protocol_version)
                        except Exception as pe:
                            print(f"[DiscordService-DAVE] Prepare transition notice for id {transition_id}: {pe}")
                        if transition_id != 0:
                            state.dave_pending_transitions[transition_id] = state.dave_protocol_version
                            await self.send_transition_ready(transition_id)
                        else:
                            try:
                                state.dave_session.execute_transition(0)
                            except Exception:
                                pass
                        print(f"[DiscordService-DAVE] MLS commit transition {transition_id} processed | ready={state.dave_session.ready}, can_encrypt={state.can_encrypt}")
                    except Exception as ce:
                        print(f"[DiscordService-DAVE] Commit transition {transition_id} error: {ce}")
                        await state._recover_from_invalid_commit(transition_id)
                    return

                elif op == self.MLS_WELCOME:
                    transition_id = struct.unpack_from('>H', msg, 3)[0]
                    try:
                        state.dave_session.process_welcome(msg[5:])
                        try:
                            state.dave_session.prepare_transition(transition_id, state.dave_protocol_version)
                        except Exception as pe:
                            print(f"[DiscordService-DAVE] Prepare transition notice for id {transition_id}: {pe}")
                        if transition_id != 0:
                            state.dave_pending_transitions[transition_id] = state.dave_protocol_version
                            await self.send_transition_ready(transition_id)
                        else:
                            try:
                                state.dave_session.execute_transition(0)
                            except Exception:
                                pass
                        print(f"[DiscordService-DAVE] MLS welcome transition {transition_id} processed | ready={state.dave_session.ready}, can_encrypt={state.can_encrypt}")
                    except Exception as we:
                        print(f"[DiscordService-DAVE] Welcome transition {transition_id} error: {we}")
                        await state._recover_from_invalid_commit(transition_id)
                    return

            await _orig_recv_binary(self, msg)

        discord.gateway.DiscordVoiceWebSocket.received_binary_message = _patched_recv_binary

        _orig_exec_trans = discord.voice_state.VoiceConnectionState._execute_transition

        async def _patched_exec_trans(self, transition_id: int) -> None:
            if self.dave_session:
                try:
                    self.dave_session.execute_transition(transition_id)
                    print(f"[DiscordService-DAVE] Executed DAVE transition id {transition_id} | ready={self.dave_session.ready}, can_encrypt={self.can_encrypt}")
                except Exception as e:
                    print(f"[DiscordService-DAVE] Transition execute notice: {e}")
            await _orig_exec_trans(self, transition_id)

        discord.voice_state.VoiceConnectionState._execute_transition = _patched_exec_trans

        _orig_recv_msg = discord.gateway.DiscordVoiceWebSocket.received_message

        async def _patched_recv_msg(self, msg: dict) -> None:
            op = msg.get('op')
            data = msg.get('d')
            state = self._connection
            if state and state.dave_session and op == self.DAVE_PREPARE_TRANSITION and data:
                try:
                    trans_id = data.get('transition_id', 0)
                    proto_ver = data.get('protocol_version', state.dave_protocol_version)
                    state.dave_session.prepare_transition(trans_id, proto_ver)
                    print(f"[DiscordService-DAVE] Prepared transition id {trans_id} via Opcode 21 | ready={state.dave_session.ready}")
                    if trans_id == 0:
                        try:
                            state.dave_session.execute_transition(0)
                        except Exception:
                            pass
                except Exception as e:
                    pass
            await _orig_recv_msg(self, msg)

        discord.gateway.DiscordVoiceWebSocket.received_message = _patched_recv_msg

        # Property to accurately reflect DAVE encryption readiness:
        # Returns True only when DAVE is enabled (protocol > 0), dave_session exists, and session is ready/can_encrypt.
        @property
        def _safe_can_encrypt(self) -> bool:
            if self.dave_protocol_version == 0 or self.dave_session is None:
                return False
            return bool(getattr(self.dave_session, 'can_encrypt', False) and self.dave_session.ready)

        discord.voice_state.VoiceConnectionState.can_encrypt = _safe_can_encrypt

        def _safe_get_voice_packet(self, data: bytes):
            packet = data
            conn = self._connection
            if conn and conn.dave_protocol_version > 0 and conn.dave_session is not None:
                if conn.can_encrypt:
                    try:
                        packet = conn.dave_session.encrypt_opus(data)
                    except Exception:
                        # Caught during MLS key ratchet / transitions:
                        # Drop this frame instead of throwing an error into AudioPlayer.
                        return None
                else:
                    # DAVE is negotiated but transition hasn't executed yet.
                    # Drop silence frames during handshake so Discord doesn't receive unencrypted payloads.
                    return None

            header = bytearray(12)
            header[0] = 0x80
            header[1] = 0x78
            struct.pack_into('>H', header, 2, self.sequence)
            struct.pack_into('>I', header, 4, self.timestamp)
            struct.pack_into('>I', header, 8, self.ssrc)

            encrypt_packet = getattr(self, '_encrypt_' + self.mode)
            return encrypt_packet(header, packet)

        discord.voice_client.VoiceClient._get_voice_packet = _safe_get_voice_packet

        def _safe_send_audio_packet(self, data: bytes, *, encode: bool = True) -> None:
            self.checked_add('sequence', 1, 65535)
            if encode:
                encoded_data = self.encoder.encode(data, self.encoder.SAMPLES_PER_FRAME)
            else:
                encoded_data = data

            try:
                packet = self._get_voice_packet(encoded_data)
                if packet is not None:
                    self._connection.send_packet(packet)
            except Exception:
                # Catch any unexpected transport/encryption error to guarantee AudioPlayer thread never dies
                pass

            self.checked_add('timestamp', discord.opus.Encoder.SAMPLES_PER_FRAME, 4294967295)

        discord.voice_client.VoiceClient.send_audio_packet = _safe_send_audio_packet

        print(f"[DiscordService] DAVE protocol state-machine patch and resilient RTP streamer installed successfully.")
    except Exception as patch_err:
        print(f"[DiscordService] DAVE patch initialization notice: {patch_err}")

    print(f"[DiscordService] discord.py v{discord.__version__} initialized. Opus loaded: {discord.opus.is_loaded()}")
except (ImportError, Exception) as e:
    discord = None
    commands = None
    DISCORD_AVAILABLE = False
    BasePCMAudio = object
    print(f"[DiscordService] Discord initialization notice: {e}")


class DiscordMixerAudioSource(discord.AudioSource if DISCORD_AVAILABLE else object):
    """Real-time Multi-Track Audio Mixer for Discord Voice.
    Allows multiple sounds and multiple copies of the same sound to play simultaneously over each other.
    """
    def __init__(self):
        self.tracks = []
        self.lock = threading.Lock()
        self._log_counter = 0

    def add_track(self, raw_bytes: bytes):
        with self.lock:
            self.tracks.append(io.BytesIO(raw_bytes))
            print(f"[DiscordMixer] Added track ({len(raw_bytes)} bytes). Total active tracks: {len(self.tracks)}")

    def stop_all(self):
        with self.lock:
            self.tracks.clear()
            print("[DiscordMixer] Stopped all tracks in mixer.")

    def is_playing_any(self):
        with self.lock:
            return len(self.tracks) > 0

    def read(self):
        # 3840 bytes = 20ms frame of 48,000Hz * 2 channels * 2 bytes/sample (16-bit PCM)
        frame_bytes = 3840
        num_samples = 1920

        with self.lock:
            if not self.tracks:
                return b'\x00' * frame_bytes

            mixed = np.zeros(num_samples, dtype=np.int32)
            active_tracks = []

            for stream in self.tracks:
                chunk = stream.read(frame_bytes)
                if len(chunk) > 0:
                    if len(chunk) < frame_bytes:
                        chunk = chunk + (b'\x00' * (frame_bytes - len(chunk)))
                    samples = np.frombuffer(chunk, dtype=np.int16)
                    mixed += samples
                    if stream.tell() < stream.getbuffer().nbytes:
                        active_tracks.append(stream)

            finished_count = len(self.tracks) - len(active_tracks)
            self.tracks = active_tracks
            mixed_clipped = np.clip(mixed, -32768, 32767).astype(np.int16)

            self._log_counter += 1
            if self._log_counter % 25 == 0:
                peak = int(np.max(np.abs(mixed_clipped)))
                print(f"[DiscordMixer] Streaming frame #{self._log_counter}: active_tracks={len(active_tracks)}, peak_sample={peak}")

            if finished_count > 0:
                print(f"[DiscordMixer] Track completed. Remaining tracks in mixer: {len(active_tracks)}")

            return mixed_clipped.tobytes()

    def is_opus(self):
        return False


class DiscordService:
    def __init__(self, config_manager=None, audio_engine=None):
        self.config_manager = config_manager
        self.audio_engine = audio_engine
        self.bot = None
        self.loop = None
        self.thread = None
        self.voice_client = None
        self.mixer = DiscordMixerAudioSource()
        self.is_running = False
        self.is_connecting = False
        self.last_error = None
        self.lock = threading.Lock()

        # Load credentials from environment or config
        self.token = os.environ.get('DISCORD_BOT_TOKEN')
        self.default_guild_id = os.environ.get('DISCORD_GUILD_ID')
        self.default_channel_id = os.environ.get('DISCORD_VOICE_CHANNEL_ID')

        if not self.token and self.config_manager:
            self.token = self.config_manager.config.get('discord_token')
            self.default_guild_id = self.config_manager.config.get('discord_guild_id')
            self.default_channel_id = self.config_manager.config.get('discord_channel_id')

    def start(self, force=False):
        """Start Discord Bot event loop in a background daemon thread."""
        if not DISCORD_AVAILABLE:
            self.last_error = "discord.py not installed"
            print("[DiscordService] discord.py or PyNaCl not installed. Discord streaming disabled.")
            return False

        if not self.token or not self.token.strip():
            self.last_error = "No Bot Token provided"
            return False

        with self.lock:
            if not force and (self.is_running or (self.thread and self.thread.is_alive())):
                return True

            self.is_running = False
            self.is_connecting = True
            self.last_error = None
            self.thread = threading.Thread(target=self._run_bot_thread, daemon=True, name="DiscordBotThread")
            self.thread.start()
            print(f"[DiscordService] Background bot thread launched.")
            return True

    def _run_bot_thread(self):
        """Background thread target setting up dedicated asyncio loop."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        # Standard non-privileged intents
        intents = discord.Intents.default()
        try:
            intents.message_content = True
        except Exception:
            pass

        self.bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

        @self.bot.event
        async def on_ready():
            self.is_running = True
            self.is_connecting = False
            self.last_error = None
            bot_display_name = os.environ.get('BOT_NAME') or (f"Soundboard ({os.environ.get('USER_NAME').title()})" if os.environ.get('USER_NAME') else "Virtual Soundboard")
            try:
                activity = discord.Activity(type=discord.ActivityType.listening, name=bot_display_name)
                await self.bot.change_presence(activity=activity)
            except Exception as e:
                print(f"[DiscordService] Could not set presence: {e}")
            guild_list = [f"'{g.name}' (ID: {g.id})" for g in self.bot.guilds]
            print(f"[DiscordService] Logged in as {self.bot.user} (ID: {self.bot.user.id}) - Display: '{bot_display_name}'")
            print(f"[DiscordService] Connected to {len(self.bot.guilds)} server(s): {guild_list}")
            if len(self.bot.guilds) == 0:
                print(f"[DiscordService] NOTICE: Bot is not currently in any Discord servers. Invite it using: https://discord.com/oauth2/authorize?client_id={self.bot.user.id}&permissions=3145728&scope=bot%20applications.commands")
            if self.default_channel_id:
                try:
                    await self._join_channel_internal(int(self.default_channel_id))
                except Exception as e:
                    print(f"[DiscordService] Auto-join notice: {e}")

        @self.bot.command(name="join")
        async def cmd_join(ctx):
            if ctx.author.voice and ctx.author.voice.channel:
                channel = ctx.author.voice.channel
                await self._join_channel_internal(channel.id)
                await ctx.send(f"🔊 Joined **{channel.name}**!")
            else:
                await ctx.send("❌ You are not connected to a voice channel.")

        @self.bot.command(name="leave")
        async def cmd_leave(ctx):
            await self._leave_internal()
            await ctx.send("👋 Disconnected from voice channel.")

        @self.bot.command(name="sounds")
        async def cmd_sounds(ctx):
            if not self.config_manager:
                return
            sounds = self.config_manager.config.get('sounds', [])
            names = [s.get('name') for s in sounds[:25]]
            list_str = ", ".join(f"`{n}`" for n in names)
            await ctx.send(f"🎵 **Soundboard Clips ({len(sounds)} total):**\n{list_str}")

        clean_token = self.token.strip()
        print(f"[DiscordService] Connecting to Discord Gateway...")
        try:
            self.loop.run_until_complete(self.bot.start(clean_token))
        except (discord.errors.PrivilegedIntentsRequired, Exception) as e:
            err_str = str(e)
            if "Privileged" in err_str or "intent" in err_str.lower():
                print("[DiscordService] Privileged intents disabled in portal. Retrying with basic intents...")
                try:
                    basic_intents = discord.Intents.default()
                    self.bot = commands.Bot(command_prefix="!", intents=basic_intents, help_command=None)
                    self.loop.run_until_complete(self.bot.start(clean_token))
                except Exception as e2:
                    self.last_error = f"Error: {e2}"
                    print(f"[DiscordService] Fallback bot error: {e2}")
            else:
                self.last_error = f"Login Failed: {err_str}"
                print(f"[DiscordService] Bot error or shutdown: {e}")
        finally:
            self.is_running = False
            self.is_connecting = False

    async def _join_channel_internal(self, channel_id):
        channel = self.bot.get_channel(int(channel_id))
        if not channel or not isinstance(channel, (discord.VoiceChannel, discord.StageChannel)):
            return False, "Channel not found or not a voice channel"

        try:
            voice_client = channel.guild.voice_client
            if voice_client:
                if voice_client.channel.id == channel.id:
                    self.voice_client = voice_client
                else:
                    await voice_client.move_to(channel)
                    self.voice_client = voice_client
            else:
                self.voice_client = await channel.connect(timeout=15.0, reconnect=True)

            # Ensure continuous polyphonic mixer is attached to the voice client
            if self.voice_client and self.voice_client.is_connected() and not self.voice_client.is_playing():
                def _on_mixer_err(err):
                    if err:
                        print(f"[DiscordService] Initial mixer player stopped! Error: {err}")
                try:
                    self.voice_client.play(self.mixer, after=_on_mixer_err)
                except Exception as play_err:
                    print(f"[DiscordService] Initial mixer play notice: {play_err}")

            # Attempt to set distinguishable bot nickname in guild if configured
            bot_display_name = os.environ.get('BOT_NAME') or (f"Soundboard ({os.environ.get('USER_NAME').title()})" if os.environ.get('USER_NAME') else None)
            if bot_display_name and channel.guild and channel.guild.me:
                try:
                    await channel.guild.me.edit(nick=bot_display_name)
                except Exception:
                    pass

            print(f"[DiscordService] Successfully connected voice client to '{channel.name}' in '{channel.guild.name}' (VoiceClient: {self.voice_client})")
            return True, f"Connected to {channel.name}"
        except Exception as e:
            err_msg = f"{type(e).__name__}: {e}" if str(e).strip() else type(e).__name__
            print(f"[DiscordService] Voice connection error: {err_msg}")
            return False, f"Voice connect failed: {err_msg}"

    async def _leave_internal(self):
        self.mixer.stop_all()
        for vc in list(self.bot.voice_clients):
            try:
                if vc.is_playing():
                    vc.stop()
                await vc.disconnect(force=True)
            except Exception:
                pass
        self.voice_client = None
        return True, "Disconnected from voice"

    def join_channel(self, channel_id):
        """Threadsafe call to join a voice channel."""
        if not self.is_running or not self.loop:
            return False, "Discord Bot is not connected. Please verify Bot Token."

        future = asyncio.run_coroutine_threadsafe(
            self._join_channel_internal(channel_id),
            self.loop
        )
        try:
            return future.result(timeout=15)
        except Exception as e:
            return False, str(e)

    def leave_channel(self):
        """Threadsafe call to leave voice channel."""
        if not self.is_running or not self.loop:
            return False, "Discord Bot is not running"

        future = asyncio.run_coroutine_threadsafe(self._leave_internal(), self.loop)
        try:
            return future.result(timeout=5)
        except Exception as e:
            return False, str(e)

    def stop_all_sounds(self):
        """Stop all active audio streams in mixer immediately."""
        self.mixer.stop_all()

    def play_audio_array(self, audio_data: np.ndarray, sr: int = 48000):
        """Stream a float32 audio array to active Discord voice mixer (polyphonic)."""
        if not self.is_running or not self.loop:
            print("[DiscordService] Play dropped: Bot is not running or gateway loop is inactive.")
            return False

        async def _play():
            active_vc = None
            if self.voice_client and self.voice_client.is_connected():
                active_vc = self.voice_client
            elif self.bot and self.bot.voice_clients:
                active_vc = self.bot.voice_clients[0]

            if not active_vc or not active_vc.is_connected():
                print(f"[DiscordService] Play dropped: Bot is not connected to a voice channel! (voice_clients={len(self.bot.voice_clients) if self.bot else 0})")
                return False

            conn = getattr(active_vc, '_connection', None)
            dave_ver = getattr(conn, 'dave_protocol_version', None) if conn else None
            can_enc = getattr(conn, 'can_encrypt', None) if conn else None
            print(f"[DiscordService] VC state: connected={active_vc.is_connected()}, playing={active_vc.is_playing()}, mode={getattr(active_vc, 'mode', None)}, ssrc={getattr(active_vc, 'ssrc', None)}, dave_ver={dave_ver}, can_encrypt={can_enc}")

            # Ensure continuous polyphonic mixer is attached
            if not active_vc.is_playing():
                print("[DiscordService] VoiceClient was not playing! Re-attaching mixer...")
                def _on_mixer_err(err):
                    if err:
                        print(f"[DiscordService] Mixer player stopped! Error: {err}")
                try:
                    active_vc.play(self.mixer, after=_on_mixer_err)
                except Exception as play_err:
                    print(f"[DiscordService] Mixer play notice: {play_err}")

            # Resample to 48,000 Hz if needed (Discord standard sample rate)
            from scipy import signal
            target_sr = 48000
            data = audio_data
            if sr != target_sr:
                new_len = int(len(data) * target_sr / sr)
                data = signal.resample(data, new_len).astype(np.float32)

            if data.ndim == 1:
                data = np.column_stack((data, data))
            elif data.shape[1] > 2:
                data = data[:, :2]

            # Ensure contiguous 2-channel float32
            data = np.ascontiguousarray(data, dtype=np.float32)
            pcm16 = (np.clip(data, -1.0, 1.0) * 32767.0).astype(np.int16)
            pcm16 = np.ascontiguousarray(pcm16)
            raw_bytes = pcm16.tobytes()

            # Add to mixer (allows overlapping sounds and repeated plays of the same sound)
            self.mixer.add_track(raw_bytes)
            print(f"[DiscordService] Transmitting sound to Discord voice channel '{active_vc.channel.name}' ({len(raw_bytes)} bytes PCM, peak={int(np.max(np.abs(pcm16)))})")
            return True

        future = asyncio.run_coroutine_threadsafe(_play(), self.loop)
        try:
            return future.result(timeout=2)
        except Exception as e:
            print(f"[DiscordService] Playback error: {e}")
            return False

    def play_file_direct(self, filepath):
        """Play local file directly using discord.FFmpegPCMAudio to test raw Discord audio pipe."""
        if not self.is_running or not self.loop or not os.path.exists(filepath):
            return False, f"Not ready or file missing: {filepath}"

        async def _direct_play():
            active_vc = self.voice_client or (self.bot.voice_clients[0] if self.bot and self.bot.voice_clients else None)
            if not active_vc or not active_vc.is_connected():
                return False, "Not connected to a voice channel"

            if active_vc.is_playing():
                active_vc.stop()

            conn = getattr(active_vc, '_connection', None)
            dave_ver = getattr(conn, 'dave_protocol_version', None) if conn else None
            can_enc = getattr(conn, 'can_encrypt', None) if conn else None
            print(f"[DiscordService-Direct] Launching FFmpegPCMAudio for '{filepath}' | DAVE ver={dave_ver}, can_encrypt={can_enc}")

            source = discord.FFmpegPCMAudio(filepath)
            def _after(e):
                print(f"[DiscordService-Direct] FFmpeg playback completed. Exception: {e}")
                if active_vc.is_connected() and not active_vc.is_playing():
                    active_vc.play(self.mixer)

            active_vc.play(source, after=_after)
            return True, "Started FFmpegPCMAudio playback"

        future = asyncio.run_coroutine_threadsafe(_direct_play(), self.loop)
        try:
            return future.result(timeout=3)
        except Exception as e:
            return False, str(e)

    def get_status(self):
        """Return real-time Discord connection status."""
        configured = bool(self.token and self.token.strip())
        connected = bool(self.is_running and self.bot and self.bot.is_ready())
        voice_connected = False
        channel_name = None
        guild_name = None
        channel_id = None
        available_channels = []
        guild_count = 0
        guild_names = []
        bot_user_id = None
        invite_url = None

        if connected and self.bot:
            if self.bot.user:
                bot_user_id = str(self.bot.user.id)
                invite_url = f"https://discord.com/oauth2/authorize?client_id={bot_user_id}&permissions=3145728&scope=bot%20applications.commands"

            guild_count = len(self.bot.guilds)
            guild_names = [g.name for g in self.bot.guilds]

            for vc in self.bot.voice_clients:
                if vc.is_connected() and vc.channel:
                    voice_connected = True
                    channel_name = vc.channel.name
                    guild_name = vc.guild.name
                    channel_id = str(vc.channel.id)
                    break

            for guild in self.bot.guilds:
                for ch in guild.channels:
                    if isinstance(ch, (discord.VoiceChannel, discord.StageChannel)):
                        available_channels.append({
                            'id': str(ch.id),
                            'name': f"{guild.name} ➔ #{ch.name}",
                            'guild_id': str(guild.id),
                            'guild_name': guild.name
                        })

        return {
            'configured': configured,
            'connected': connected,
            'is_connecting': self.is_connecting,
            'error': self.last_error,
            'user': str(self.bot.user) if (connected and self.bot and self.bot.user) else None,
            'bot_user_id': bot_user_id,
            'invite_url': invite_url,
            'guild_count': guild_count,
            'guild_names': guild_names,
            'voice_connected': voice_connected,
            'channel_name': channel_name,
            'guild_name': guild_name,
            'channel_id': channel_id,
            'available_channels': available_channels
        }

    def update_config(self, token=None, guild_id=None, channel_id=None):
        """Update Discord credentials and start/restart bot."""
        if token is not None:
            clean = token.strip()
            self.token = clean if clean else None
        if guild_id is not None:
            self.default_guild_id = str(guild_id).strip()
        if channel_id is not None:
            self.default_channel_id = str(channel_id).strip()

        if self.config_manager:
            self.config_manager.config['discord_token'] = self.token
            self.config_manager.config['discord_guild_id'] = self.default_guild_id
            self.config_manager.config['discord_channel_id'] = self.default_channel_id
            self.config_manager.save_config()

        # Stop previous instance if running and force clean start
        self.stop()
        if self.token:
            self.start(force=True)

        return self.get_status()

    def stop(self):
        """Disconnect and stop the bot."""
        self.mixer.stop_all()
        if self.loop and self.bot:
            try:
                asyncio.run_coroutine_threadsafe(self._leave_internal(), self.loop)
                asyncio.run_coroutine_threadsafe(self.bot.close(), self.loop)
            except Exception:
                pass
        self.is_running = False
        self.is_connecting = False
        self.voice_client = None
