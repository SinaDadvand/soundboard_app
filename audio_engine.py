"""
Audio Engine for Virtual Soundboard
===================================
Provides high-performance audio playback with:
- Dual-device routing (Primary speakers + Secondary Virtual Audio Cable/Mic)
- Real-time Volume, Pitch shifting, and Playback Speed FX
- Instant panic stop / individual clip stop
- Device enumeration and hot-swapping
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
        self.audio_cache = {}  # filename -> (data: np.ndarray, samplerate: int)
        self.active_streams = []  # list of active sd.OutputStream or stop events
        self.lock = threading.Lock()

        self.master_volume = 1.0  # 0.0 to 1.0
        self.primary_device = None  # None = system default
        self.secondary_device = None  # None = disabled
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

    def set_devices(self, primary_id=None, secondary_id=None, secondary_enabled=False):
        """Configure primary and secondary output devices."""
        with self.lock:
            self.primary_device = primary_id
            self.secondary_device = secondary_id
            self.secondary_enabled = secondary_enabled and (secondary_id is not None)

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
        """Change playback speed and pitch together (varispeed / tape speed)."""
        if speed_factor == 1.0 or speed_factor <= 0:
            return data
        
        num_samples = int(len(data) / speed_factor)
        if num_samples <= 0:
            return data
        
        # Resample both channels using scipy signal resample
        left = signal.resample(data[:, 0], num_samples)
        right = signal.resample(data[:, 1], num_samples)
        return np.column_stack((left, right)).astype(np.float32)

    @staticmethod
    def _phase_vocoder(d, rate, hop_length=512):
        """Simple phase vocoder for single-channel time stretching."""
        n_fft = 2048
        # Short-time Fourier transform
        _, _, stft = signal.stft(d, nperseg=n_fft, noverlap=n_fft - hop_length)
        
        # Phase vocoder time stretch
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
        
        # Method: Resample by pitch_ratio, then time-stretch by pitch_ratio to restore original length
        # 1. Resample
        new_len = int(len(data) / pitch_ratio)
        resampled_l = signal.resample(data[:, 0], new_len)
        resampled_r = signal.resample(data[:, 1], new_len)
        
        # 2. Time stretch back
        try:
            stretched_l = cls._phase_vocoder(resampled_l, 1.0 / pitch_ratio)
            stretched_r = cls._phase_vocoder(resampled_r, 1.0 / pitch_ratio)
            
            # Match lengths
            target_len = len(data)
            out_l = np.zeros(target_len, dtype=np.float32)
            out_r = np.zeros(target_len, dtype=np.float32)
            
            copy_len = min(target_len, len(stretched_l), len(stretched_r))
            out_l[:copy_len] = stretched_l[:copy_len]
            out_r[:copy_len] = stretched_r[:copy_len]
            
            return np.column_stack((out_l, out_r))
        except Exception:
            # Fallback to varispeed if phase vocoder fails
            return np.column_stack((resampled_l, resampled_r))

    def process_audio(self, raw_data, volume=1.0, speed=1.0, pitch_semitones=0.0):
        """Apply volume, pitch, and speed transformations."""
        processed = raw_data.copy()

        # Apply Pitch Shift if requested
        if pitch_semitones != 0:
            processed = self.apply_pitch_shift(processed, pitch_semitones)

        # Apply Playback Speed
        if speed != 1.0 and speed > 0:
            processed = self.apply_speed(processed, speed)

        # Apply Volume scaling
        eff_vol = max(0.0, min(2.0, float(volume) * float(self.master_volume)))
        if eff_vol != 1.0:
            processed = processed * eff_vol

        # Soft clip to prevent distortion
        np.clip(processed, -1.0, 1.0, out=processed)
        return processed

    def play(self, filepath, volume=1.0, speed=1.0, pitch_semitones=0.0, sound_id=None):
        """Play a sound file across configured devices."""
        try:
            data, sr = self.load_audio(filepath)
        except Exception as e:
            print(f"[AudioEngine] Failed to load audio {filepath}: {e}")
            return False

        # Apply effects
        audio_to_play = self.process_audio(data, volume=volume, speed=speed, pitch_semitones=pitch_semitones)

        # Determine target devices
        devices_to_play = []
        with self.lock:
            devices_to_play.append(self.primary_device)
            if self.secondary_enabled and self.secondary_device is not None:
                devices_to_play.append(self.secondary_device)

        # Launch playback in background threads
        stop_event = threading.Event()
        stream_entry = {
            'sound_id': sound_id or filepath,
            'stop_event': stop_event,
            'threads': []
        }

        def _play_on_device(dev_id):
            try:
                # Use blocking stream with stop event checking
                chunk_size = 2048
                with sd.OutputStream(samplerate=sr, channels=2, device=dev_id, dtype='float32') as stream:
                    pos = 0
                    total = len(audio_to_play)
                    while pos < total and not stop_event.is_set():
                        end = min(pos + chunk_size, total)
                        chunk = audio_to_play[pos:end]
                        stream.write(chunk)
                        pos = end
            except Exception as ex:
                print(f"[AudioEngine] Playback error on device {dev_id}: {ex}")

        with self.lock:
            self.active_streams.append(stream_entry)

        for dev_id in devices_to_play:
            t = threading.Thread(target=_play_on_device, args=(dev_id,), daemon=True)
            stream_entry['threads'].append(t)
            t.start()

        # Thread to clean up entry once done
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
