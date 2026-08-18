"""
Audio Engine for Virtual Soundboard
===================================
High-performance audio playback engine supporting:
- Independent Headset / Virtual Cable destination toggle buttons
- Simultaneous multi-stream routing (Sony Headset/WF-1000XM4 + VB-Audio Virtual Cable)
- Automatic sample rate conversion & channel mapping for WASAPI / DirectSound / MME
- Real-time volume, pitch shifting, and playback speed manipulation
- Panic stop & individual sound stop
"""

import os
import threading
import numpy as np
import soundfile as sf
from scipy import signal

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except (OSError, ImportError, Exception) as e:
    sd = None
    SOUNDDEVICE_AVAILABLE = False
    print(f"[AudioEngine] Notice: sounddevice/PortAudio unavailable in headless mode ({e}).")


class AudioEngine:
    def __init__(self, audio_dir=None):
        self.audio_dir = audio_dir
        self.audio_cache = {}  # filepath -> (data: np.ndarray, samplerate: int)
        self.active_streams = []
        self.lock = threading.Lock()

        self.master_volume = 1.0  # 0.0 to 1.0
        self.global_pitch = 0.0   # -12.0 to +12.0 semitones
        self.global_speed = 1.0   # 0.5 to 2.0x
        self.global_echo = 0.0    # 0.0 to 1.0 (0% to 100%)
        self.global_reverb = 0.0  # 0.0 to 1.0 (0% to 100%)
        self.headset_enabled = True
        self.cable_enabled = True
        self.primary_device_name = None
        self.secondary_device_name = None
        self.discord_service = None

    def set_global_fx(self, pitch=None, speed=None, echo=None, reverb=None):
        """Update global DSP modifiers affecting both hotkeys and UI clicks."""
        with self.lock:
            if pitch is not None:
                self.global_pitch = max(-12.0, min(12.0, float(pitch)))
            if speed is not None:
                self.global_speed = max(0.25, min(3.0, float(speed)))
            if echo is not None:
                self.global_echo = max(0.0, min(1.0, float(echo)))
            if reverb is not None:
                self.global_reverb = max(0.0, min(1.0, float(reverb)))
        print(f"[AudioEngine] Global FX updated -> Pitch: {self.global_pitch}st, Speed: {self.global_speed}x, Echo: {int(self.global_echo*100)}%, Reverb: {int(self.global_reverb*100)}%")

    def list_output_devices(self):
        """Return a list of all available output devices on the system."""
        if not SOUNDDEVICE_AVAILABLE or sd is None:
            return []
        devices = []
        try:
            raw_devices = sd.query_devices()
            host_apis = sd.query_hostapis()
            
            for idx, dev in enumerate(raw_devices):
                if dev['max_output_channels'] > 0:
                    api_name = host_apis[dev['hostapi']]['name'] if dev['hostapi'] < len(host_apis) else ''
                    if 'CABLE In 16ch' in dev['name'] and dev['max_output_channels'] > 2:
                        continue

                    devices.append({
                        'id': idx,
                        'name': dev['name'],
                        'hostapi': api_name,
                        'display_name': f"{dev['name']} ({api_name})",
                        'channels': dev['max_output_channels'],
                        'default_samplerate': int(dev['default_samplerate']),
                        'is_default': idx == sd.default.device[1]
                    })
        except Exception as e:
            print(f"[AudioEngine] Error querying devices: {e}")
        return devices

    def resolve_headphone_device(self):
        """Find the user's primary headphones/headset (e.g. Sony Headset, WF-1000XM4, or default)."""
        devices = self.list_output_devices()
        
        # 1. If explicit device name configured
        if self.primary_device_name:
            spec_str = self.primary_device_name.lower()
            for d in devices:
                if 'wasapi' in d['hostapi'].lower() and (spec_str in d['display_name'].lower() or spec_str in d['name'].lower()):
                    return d['id']
            for d in devices:
                if spec_str in d['display_name'].lower() or spec_str in d['name'].lower():
                    return d['id']

        # 2. Auto-detect Sony Headset / WF-1000XM4 / Headphones (WASAPI preferred)
        for d in devices:
            d_name = d['name'].lower()
            if any(k in d_name for k in ['sony headset', '1000xm4', 'wireless stereo headset', 'headphones', 'headset']) and 'cable' not in d_name:
                if 'wasapi' in d['hostapi'].lower():
                    return d['id']
        for d in devices:
            d_name = d['name'].lower()
            if any(k in d_name for k in ['sony headset', '1000xm4', 'wireless stereo headset', 'headphones', 'headset']) and 'cable' not in d_name:
                return d['id']

        # 3. Fallback to speakers
        for d in devices:
            d_name = d['name'].lower()
            if any(k in d_name for k in ['speakers', 'dell']) and 'cable' not in d_name:
                if 'wasapi' in d['hostapi'].lower():
                    return d['id']
        for d in devices:
            d_name = d['name'].lower()
            if any(k in d_name for k in ['speakers', 'dell']) and 'cable' not in d_name:
                return d['id']

        return None

    def resolve_cable_device(self):
        """Find VB-Audio CABLE Input for streaming directly to OBS / Discord."""
        devices = self.list_output_devices()
        
        if self.secondary_device_name:
            spec_str = self.secondary_device_name.lower()
            # Prioritize WASAPI device match first
            for d in devices:
                if 'wasapi' in d['hostapi'].lower() and (spec_str in d['display_name'].lower() or spec_str in d['name'].lower()):
                    return d['id']
            for d in devices:
                if spec_str in d['display_name'].lower() or spec_str in d['name'].lower():
                    return d['id']

        # Prioritize WASAPI CABLE Input (dev 25) then other host APIs
        for d in devices:
            if 'cable input' in d['name'].lower() and 'wasapi' in d['hostapi'].lower():
                return d['id']
        for d in devices:
            if 'cable input' in d['name'].lower():
                return d['id']

        return None

    def set_devices(self, primary=None, secondary=None, secondary_enabled=True):
        with self.lock:
            self.primary_device_name = primary
            self.secondary_device_name = secondary
            self.cable_enabled = bool(secondary_enabled)

    def set_toggles(self, headset_enabled=True, cable_enabled=True):
        """Toggle output to Headset or Virtual Cable destinations."""
        with self.lock:
            self.headset_enabled = bool(headset_enabled)
            self.cable_enabled = bool(cable_enabled)
        print(f"[AudioEngine] Output routing updated -> Headset: {self.headset_enabled}, Virtual Cable: {self.cable_enabled}")

    def load_audio(self, filepath):
        """Load and cache audio file as float32 stereo array."""
        if filepath in self.audio_cache:
            return self.audio_cache[filepath]

        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Audio file not found: {filepath}")

        data, sr = sf.read(filepath, dtype='float32')

        if data.ndim == 1:
            data = np.column_stack((data, data))
        elif data.shape[1] > 2:
            data = data[:, :2]

        data = np.ascontiguousarray(data, dtype=np.float32)
        self.audio_cache[filepath] = (data, sr)
        return data, sr

    def preload_directory(self, directory=None):
        target_dir = directory or self.audio_dir
        if not target_dir or not os.path.exists(target_dir):
            return
        
        valid_exts = ('.mp3', '.wav', '.ogg', '.flac')
        for filename in os.listdir(target_dir):
            if filename.lower().endswith(valid_exts):
                try:
                    self.load_audio(os.path.join(target_dir, filename))
                except Exception as e:
                    print(f"[AudioEngine] Failed to load {filename}: {e}")

    @staticmethod
    def apply_speed(data, speed_factor):
        if speed_factor == 1.0 or speed_factor <= 0:
            return data
        
        num_samples = int(len(data) / speed_factor)
        if num_samples <= 0:
            return data
        
        left = signal.resample(data[:, 0], num_samples)
        right = signal.resample(data[:, 1], num_samples)
        out = np.column_stack((left, right)).astype(np.float32)
        return np.ascontiguousarray(out, dtype=np.float32)

    @staticmethod
    def _phase_vocoder(d, rate, hop_length=512):
        n_fft = 2048
        _, _, stft = signal.stft(d, nperseg=n_fft, noverlap=n_fft - hop_length)
        
        time_steps = np.arange(0, stft.shape[1], rate, dtype=np.float32)
        time_steps = time_steps[time_steps < stft.shape[1] - 1]
        
        d_out = np.zeros((stft.shape[0], len(time_steps)), dtype=complex)
        phase_acc = np.angle(stft[:, 0])
        d_out[:, 0] = stft[:, 0]
        
        dphi = np.pi * 2 * hop_length / n_fft
        for i in range(1, len(time_steps)):
            t = time_steps[i]
            t_floor = int(np.floor(t))
            frac = t - t_floor
            mag = (1.0 - frac) * np.abs(stft[:, t_floor]) + frac * np.abs(stft[:, t_floor + 1])
            dp = np.angle(stft[:, t_floor + 1]) - np.angle(stft[:, t_floor])
            phase_acc += dp
            d_out[:, i] = mag * np.exp(1j * phase_acc)
            
        _, stretched = signal.istft(d_out, nperseg=n_fft, noverlap=n_fft - hop_length)
        return stretched.astype(np.float32)

    @classmethod
    def apply_pitch_shift(cls, data, semitones):
        if semitones == 0:
            return data
        
        pitch_ratio = 2.0 ** (semitones / 12.0)
        new_len = int(len(data) / pitch_ratio)
        resampled_l = signal.resample(data[:, 0], new_len)
        resampled_r = signal.resample(data[:, 1], new_len)
        
        try:
            stretched_l = cls._phase_vocoder(resampled_l, 1.0 / pitch_ratio)
            stretched_r = cls._phase_vocoder(resampled_r, 1.0 / pitch_ratio)
            
            target_len = len(data)
            out_l = np.zeros(target_len, dtype=np.float32)
            out_r = np.zeros(target_len, dtype=np.float32)
            
            copy_len = min(target_len, len(stretched_l), len(stretched_r))
            out_l[:copy_len] = stretched_l[:copy_len]
            out_r[:copy_len] = stretched_r[:copy_len]
            
            out = np.column_stack((out_l, out_r))
            return np.ascontiguousarray(out, dtype=np.float32)
        except Exception:
            out = np.column_stack((resampled_l, resampled_r))
            return np.ascontiguousarray(out, dtype=np.float32)

    @staticmethod
    def apply_echo(data, sr, echo_level=0.0, delay_sec=0.22, feedback=0.45):
        """High performance multi-tap decaying feedback echo."""
        if echo_level <= 0.005:
            return data
        
        delay_samples = int(sr * delay_sec)
        if delay_samples <= 0:
            return data
            
        wet_mix = float(echo_level) * 0.75
        taps = 4
        out_len = len(data) + delay_samples * taps
        buffer = np.zeros((out_len, data.shape[1]), dtype=np.float32)
        buffer[:len(data)] = data
        
        for tap in range(1, taps + 1):
            offset = delay_samples * tap
            gain = (feedback ** tap) * wet_mix
            buffer[offset:offset + len(data)] += data * gain
            
        out = buffer[:len(data) + int(delay_samples * 1.5)]
        return np.ascontiguousarray(out, dtype=np.float32)

    @classmethod
    def apply_reverb(cls, data, sr, reverb_level=0.0):
        """Lush algorithmic synthetic room impulse response convolution."""
        if reverb_level <= 0.005:
            return data
        
        decay_sec = 0.6 + (float(reverb_level) * 1.4)  # 0.6s to 2.0s decay
        ir_len = int(sr * decay_sec)
        t = np.linspace(0, decay_sec, ir_len, endpoint=False, dtype=np.float32)
        
        np.random.seed(42)
        noise_l = np.random.randn(ir_len).astype(np.float32)
        noise_r = np.random.randn(ir_len).astype(np.float32)
        
        decay_curve = np.exp(-3.5 * t / decay_sec)
        ir_l = noise_l * decay_curve
        ir_r = noise_r * decay_curve
        
        # Lowpass filter impulse response for warm room acoustics
        b, a = signal.butter(2, min(0.9, 3600.0 / (sr / 2.0)), btype='low')
        ir_l = signal.lfilter(b, a, ir_l).astype(np.float32)
        ir_r = signal.lfilter(b, a, ir_r).astype(np.float32)
        
        norm_l = np.sqrt(np.sum(ir_l ** 2))
        norm_r = np.sqrt(np.sum(ir_r ** 2))
        if norm_l > 0: ir_l /= norm_l
        if norm_r > 0: ir_r /= norm_r
        
        wet_l = signal.fftconvolve(data[:, 0], ir_l)[:len(data) + int(sr * 0.4)]
        wet_r = signal.fftconvolve(data[:, 1], ir_r)[:len(data) + int(sr * 0.4)]
        wet = np.column_stack((wet_l, wet_r)).astype(np.float32)
        
        wet_gain = float(reverb_level) * 0.55
        dry_gain = 1.0 - (float(reverb_level) * 0.2)
        
        out_len = max(len(data), len(wet))
        out = np.zeros((out_len, 2), dtype=np.float32)
        out[:len(data)] += data * dry_gain
        out[:len(wet)] += wet * wet_gain
        
        return np.ascontiguousarray(out, dtype=np.float32)

    def process_audio(self, raw_data, sr=44100, volume=1.0, speed=1.0, pitch_semitones=0.0, echo=None, reverb=None):
        processed = raw_data.copy()

        # Combine clip-level FX with global engine FX
        total_pitch = float(pitch_semitones) + float(self.global_pitch)
        total_speed = float(speed) * float(self.global_speed)
        total_echo = float(echo) if echo is not None else float(self.global_echo)
        total_reverb = float(reverb) if reverb is not None else float(self.global_reverb)

        if total_pitch != 0:
            processed = self.apply_pitch_shift(processed, total_pitch)

        if total_speed != 1.0 and total_speed > 0:
            processed = self.apply_speed(processed, total_speed)

        if total_echo > 0.005:
            processed = self.apply_echo(processed, sr, echo_level=total_echo)

        if total_reverb > 0.005:
            processed = self.apply_reverb(processed, sr, reverb_level=total_reverb)

        eff_vol = max(0.0, min(2.0, float(volume) * float(self.master_volume)))
        if eff_vol != 1.0:
            processed = processed * eff_vol

        np.clip(processed, -1.0, 1.0, out=processed)
        return np.ascontiguousarray(processed, dtype=np.float32)

    def play(self, filepath, volume=1.0, speed=1.0, pitch_semitones=0.0, echo=None, reverb=None, sound_id=None):
        """Play audio across enabled output destinations (Headset and/or Virtual Cable)."""
        try:
            data, sr = self.load_audio(filepath)
        except Exception as e:
            print(f"[AudioEngine] Failed to load audio {filepath}: {e}")
            return False

        audio_to_play = self.process_audio(
            data,
            sr=sr,
            volume=volume,
            speed=speed,
            pitch_semitones=pitch_semitones,
            echo=echo,
            reverb=reverb
        )

        # 1. Stream to Discord Voice if active
        if self.discord_service:
            try:
                self.discord_service.play_audio_array(audio_to_play, sr=sr)
            except Exception as d_err:
                print(f"[AudioEngine] Notice on Discord voice stream: {d_err}")

        # 2. Local device output
        devices_to_play = []
        with self.lock:
            if self.headset_enabled:
                h_dev = self.resolve_headphone_device()
                if h_dev is not None:
                    devices_to_play.append(h_dev)

            if self.cable_enabled:
                c_dev = self.resolve_cable_device()
                if c_dev is not None and c_dev not in devices_to_play:
                    devices_to_play.append(c_dev)

        if not devices_to_play:
            h_dev = self.resolve_headphone_device()
            if h_dev is not None:
                devices_to_play.append(h_dev)

        # If running in cloud/headless environment without local audio hardware, return True
        if not devices_to_play or all(d is None for d in devices_to_play):
            return True

        stop_event = threading.Event()
        stream_entry = {
            'sound_id': sound_id or filepath,
            'stop_event': stop_event,
            'threads': []
        }

        def _play_on_device(dev_id):
            if dev_id is None:
                return
            try:
                target_sr = sr
                target_audio = audio_to_play
                target_channels = 2

                try:
                    dev_info = sd.query_devices(dev_id)
                    dev_def_sr = int(dev_info.get('default_samplerate', sr))
                    dev_max_ch = int(dev_info.get('max_output_channels', 2))

                    if dev_def_sr != sr and dev_def_sr > 0:
                        target_sr = dev_def_sr
                        new_len = int(len(audio_to_play) * target_sr / sr)
                        target_audio = signal.resample(audio_to_play, new_len).astype(np.float32)

                    if dev_max_ch == 1:
                        target_audio = target_audio[:, 0:1]
                        target_channels = 1
                    else:
                        target_channels = 2
                except Exception as dev_err:
                    print(f"[AudioEngine] Device query notice on {dev_id}: {dev_err}")

                target_audio = np.ascontiguousarray(target_audio, dtype=np.float32)
                chunk_size = 2048

                with sd.OutputStream(samplerate=target_sr, channels=target_channels, device=dev_id, dtype='float32') as stream:
                    pos = 0
                    total = len(target_audio)
                    while pos < total and not stop_event.is_set():
                        end = min(pos + chunk_size, total)
                        chunk = target_audio[pos:end]
                        stream.write(chunk)
                        pos = end
            except Exception as ex:
                print(f"[AudioEngine] Playback notice on device {dev_id}: {ex}")

        with self.lock:
            self.active_streams.append(stream_entry)

        for dev_id in devices_to_play:
            t = threading.Thread(target=_play_on_device, args=(dev_id,), daemon=True)
            stream_entry['threads'].append(t)
            t.start()

        def _cleanup():
            for t in stream_entry['threads']:
                t.join()
            with self.lock:
                if stream_entry in self.active_streams:
                    self.active_streams.remove(stream_entry)

        threading.Thread(target=_cleanup, daemon=True).start()
        return True

    def stop_sound(self, sound_id):
        with self.lock:
            for entry in list(self.active_streams):
                if entry['sound_id'] == sound_id:
                    entry['stop_event'].set()

    def stop_all(self):
        with self.lock:
            for entry in self.active_streams:
                entry['stop_event'].set()
            self.active_streams.clear()
        if self.discord_service:
            try:
                self.discord_service.stop_all_sounds()
            except Exception:
                pass
        print("[AudioEngine] Stopped all playback.")
