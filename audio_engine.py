"""
Audio Engine for Virtual Soundboard
===================================
High-performance audio playback engine supporting:
- Dual-device simultaneous routing (Headphones/Speakers + Virtual Audio Cable for OBS/Discord)
- Resilient fallback for Bluetooth headsets (Sony WF-1000XM4) and VB-Audio Virtual Cable
- Automatic sample rate conversion & channel mapping for WASAPI / DirectSound / MME
- Real-time volume, pitch shifting, and playback speed manipulation
- Panic stop & individual sound stop
"""

import os
import threading
import numpy as np
import soundfile as sf
import sounddevice as sd
from scipy import signal


class AudioEngine:
    def __init__(self, audio_dir=None):
        self.audio_dir = audio_dir
        self.audio_cache = {}  # filepath -> (data: np.ndarray, samplerate: int)
        self.active_streams = []
        self.lock = threading.Lock()

        self.master_volume = 1.0  # 0.0 to 1.0
        self.primary_device_name = None
        self.secondary_device_name = None
        self.secondary_enabled = False

    def list_output_devices(self):
        """Return a list of all available output devices on the system."""
        devices = []
        try:
            raw_devices = sd.query_devices()
            host_apis = sd.query_hostapis()
            
            for idx, dev in enumerate(raw_devices):
                if dev['max_output_channels'] > 0:
                    api_name = host_apis[dev['hostapi']]['name'] if dev['hostapi'] < len(host_apis) else ''
                    
                    # Filter out problematic 16ch driver entry to prevent user confusion
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

    def resolve_device_id(self, device_spec, is_secondary=False):
        """Resolve a device index by int ID or by name matching with smart fallbacks."""
        devices = self.list_output_devices()

        # If nothing specified for primary output, find the best working headphones/speakers
        if device_spec is None or device_spec == "":
            if is_secondary:
                return None
            
            # Find headphones (e.g. WF-1000XM4) or default speaker
            for d in devices:
                if any(k in d['name'].lower() for k in ['headphones', 'headset', 'speakers', 'dell']) and 'cable' not in d['name'].lower():
                    if 'wasapi' in d['hostapi'].lower() or 'mme' in d['hostapi'].lower():
                        return d['id']
            return None

        # If explicitly integer index
        if isinstance(device_spec, int):
            try:
                sd.query_devices(device_spec)
                return device_spec
            except Exception:
                pass

        spec_str = str(device_spec).lower()

        # Prefer WASAPI then MME then DirectSound
        api_priority = {'windows wasapi': 0, 'mme': 1, 'windows directsound': 2, 'windows wdm-ks': 3}
        sorted_devs = sorted(devices, key=lambda d: api_priority.get(d['hostapi'].lower(), 99))

        # 1. Exact match on display_name or name
        for d in sorted_devs:
            if d['display_name'].lower() == spec_str or d['name'].lower() == spec_str:
                return d['id']
            if str(d['id']) == spec_str:
                return d['id']

        # 2. Substring match
        for d in sorted_devs:
            if spec_str in d['display_name'].lower() or spec_str in d['name'].lower():
                return d['id']

        return None

    def set_devices(self, primary=None, secondary=None, secondary_enabled=False):
        """Configure primary and secondary output devices."""
        with self.lock:
            self.primary_device_name = primary
            self.secondary_device_name = secondary
            self.secondary_enabled = bool(secondary_enabled) and (secondary is not None)

    def load_audio(self, filepath):
        """Load and cache audio file as float32 stereo array."""
        if filepath in self.audio_cache:
            return self.audio_cache[filepath]

        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Audio file not found: {filepath}")

        data, sr = sf.read(filepath, dtype='float32')

        # Convert mono to stereo (N, 2)
        if data.ndim == 1:
            data = np.column_stack((data, data))
        elif data.shape[1] > 2:
            data = data[:, :2]

        data = np.ascontiguousarray(data, dtype=np.float32)
        self.audio_cache[filepath] = (data, sr)
        return data, sr

    def preload_directory(self, directory=None):
        """Preload all audio files in the specified directory."""
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
        """Change playback speed and pitch together (varispeed)."""
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
        """Phase vocoder for single-channel time stretching."""
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
        """Pitch shift without changing playback speed (semitones: -12 to +12)."""
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

    def process_audio(self, raw_data, volume=1.0, speed=1.0, pitch_semitones=0.0):
        """Apply volume, pitch, and speed transformations."""
        processed = raw_data.copy()

        if pitch_semitones != 0:
            processed = self.apply_pitch_shift(processed, pitch_semitones)

        if speed != 1.0 and speed > 0:
            processed = self.apply_speed(processed, speed)

        eff_vol = max(0.0, min(2.0, float(volume) * float(self.master_volume)))
        if eff_vol != 1.0:
            processed = processed * eff_vol

        np.clip(processed, -1.0, 1.0, out=processed)
        return np.ascontiguousarray(processed, dtype=np.float32)

    def play(self, filepath, volume=1.0, speed=1.0, pitch_semitones=0.0, sound_id=None):
        """Play audio across configured devices with automatic sample-rate & channel adaptation."""
        try:
            data, sr = self.load_audio(filepath)
        except Exception as e:
            print(f"[AudioEngine] Failed to load audio {filepath}: {e}")
            return False

        audio_to_play = self.process_audio(data, volume=volume, speed=speed, pitch_semitones=pitch_semitones)

        devices_to_play = []
        with self.lock:
            p_id = self.resolve_device_id(self.primary_device_name, is_secondary=False)
            devices_to_play.append(p_id)

            if self.secondary_enabled and self.secondary_device_name is not None:
                s_id = self.resolve_device_id(self.secondary_device_name, is_secondary=True)
                if s_id is not None and s_id != p_id:
                    devices_to_play.append(s_id)

        stop_event = threading.Event()
        stream_entry = {
            'sound_id': sound_id or filepath,
            'stop_event': stop_event,
            'threads': []
        }

        def _play_on_device(dev_id):
            try:
                target_sr = sr
                target_audio = audio_to_play
                target_channels = 2

                if dev_id is not None:
                    try:
                        dev_info = sd.query_devices(dev_id)
                        dev_def_sr = int(dev_info.get('default_samplerate', sr))
                        dev_max_ch = dev_info.get('max_output_channels', 2)

                        if dev_def_sr != sr and dev_def_sr > 0:
                            target_sr = dev_def_sr
                            new_len = int(len(audio_to_play) * target_sr / sr)
                            target_audio = signal.resample(audio_to_play, new_len).astype(np.float32)

                        if dev_max_ch == 1:
                            target_audio = target_audio[:, 0:1]
                            target_channels = 1
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
                # Fallback to default output device if a specific Bluetooth device was temporarily busy
                if dev_id is not None:
                    try:
                        with sd.OutputStream(samplerate=sr, channels=2, device=None, dtype='float32') as fallback_stream:
                            fallback_stream.write(np.ascontiguousarray(audio_to_play, dtype=np.float32))
                    except Exception:
                        pass

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
        """Stop all active instances of a specific sound."""
        with self.lock:
            for entry in list(self.active_streams):
                if entry['sound_id'] == sound_id:
                    entry['stop_event'].set()

    def stop_all(self):
        """Panic stop: Stop all active playing sounds immediately."""
        with self.lock:
            for entry in self.active_streams:
                entry['stop_event'].set()
            self.active_streams.clear()
        print("[AudioEngine] Stopped all playback.")
