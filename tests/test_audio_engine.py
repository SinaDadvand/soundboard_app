"""Unit test for AudioEngine"""
import os
import sys
import time
import numpy as np

# Resolve project root and src directory
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT_DIR, 'src')
for p in [ROOT_DIR, SRC_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from src.audio_engine import AudioEngine

def test_engine():
    audio_dir = os.path.join(ROOT_DIR, 'static', 'audio')
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
    
    # 5. Test Echo effect
    echoed = engine.apply_echo(data[:22050], sr, echo_level=0.5)
    print(f"[TEST] Echo applied: shape={echoed.shape}")
    assert len(echoed) >= len(data[:22050]), "Echo output length should be >= input"

    # 6. Test Reverb effect
    reverbed = engine.apply_reverb(data[:22050], sr, reverb_level=0.6)
    print(f"[TEST] Reverb applied: shape={reverbed.shape}")
    assert len(reverbed) >= len(data[:22050]), "Reverb output length should be >= input"

    # 7. Test Global FX processing
    engine.set_global_fx(pitch=2.0, speed=1.1, echo=0.3, reverb=0.4)
    processed = engine.process_audio(data[:22050], sr=sr, volume=0.8)
    assert processed.shape[1] == 2 and np.max(np.abs(processed)) <= 1.0

    # 8. Test Playback and Stop
    print("[TEST] Testing play and stop...")
    engine.play(test_file, volume=0.1, sound_id="test_clip")
    time.sleep(0.2)
    assert len(engine.active_streams) > 0, "Should have active stream"
    engine.stop_all()
    time.sleep(0.1)
    print("[TEST] All tests passed successfully!")

if __name__ == '__main__':
    test_engine()
