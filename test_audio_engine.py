"""Unit test for AudioEngine"""
import os
import time
import numpy as np
from audio_engine import AudioEngine

def test_engine():
    audio_dir = os.path.join(os.path.dirname(__file__), 'static', 'audio')
    engine = AudioEngine(audio_dir)
    
    # 1. Test Device listing
    devices = engine.list_output_devices()
    print(f"[TEST] Found {len(devices)} audio output devices.")
    assert len(devices) > 0, "No output devices found"
    
    # 2. Test Audio Loading
    test_file = os.path.join(audio_dir, 'All Day.mp3')
    data, sr = engine.load_audio(test_file)
    print(f"[TEST] Loaded audio {test_file}: shape={data.shape}, sr={sr}")
    assert data.ndim == 2 and data.shape[1] == 2, "Audio should be stereo"
    
    # 3. Test Speed effect
    speed_fast = engine.apply_speed(data, 1.5)
    print(f"[TEST] Speed 1.5x length: {len(speed_fast)} (original: {len(data)})")
    assert len(speed_fast) < len(data), "1.5x speed should result in shorter sample length"
    
    # 4. Test Pitch effect
    pitch_up = engine.apply_pitch_shift(data[:22050], 4.0)  # +4 semitones on 0.5s slice
    print(f"[TEST] Pitch shifted +4 semitones: shape={pitch_up.shape}")
    assert pitch_up.shape == data[:22050].shape, "Pitch shift output shape should match input"
    
    # 5. Test Volume processing
    scaled = engine.process_audio(data, volume=0.5, speed=1.0, pitch_semitones=0.0)
    assert np.max(np.abs(scaled)) <= np.max(np.abs(data)) + 1e-4
    
    # 6. Test Playback and Stop
    print("[TEST] Testing play and stop...")
    engine.play(test_file, volume=0.1, sound_id="test_clip")
    time.sleep(0.2)
    assert len(engine.active_streams) > 0, "Should have active stream"
    engine.stop_all()
    time.sleep(0.1)
    print("[TEST] All tests passed successfully!")

if __name__ == '__main__':
    test_engine()
