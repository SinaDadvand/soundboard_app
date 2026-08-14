"""Unit test for ConfigManager and HotkeyManager"""
import os
from config_manager import ConfigManager
from audio_engine import AudioEngine
from hotkey_manager import HotkeyManager

def test_managers():
    base_dir = os.path.dirname(__file__)
    config_path = os.path.join(base_dir, 'test_soundboard_config.json')
    audio_dir = os.path.join(base_dir, 'static', 'audio')
    
    # 1. Test ConfigManager
    cm = ConfigManager(config_path=config_path, audio_dir=audio_dir)
    print(f"[TEST] Loaded {len(cm.config['sounds'])} sounds in config.")
    assert len(cm.config['sounds']) > 0, "Sounds list should not be empty"
    
    first_sound = cm.config['sounds'][0]
    first_id = first_sound['id']
    
    # Test update
    cm.update_sound(first_id, {'volume': 0.8, 'speed': 1.2, 'pitch': 2.0})
    updated = cm.get_sound_by_id(first_id)
    assert updated['volume'] == 0.8 and updated['speed'] == 1.2 and updated['pitch'] == 2.0
    
    # 2. Test HotkeyManager
    engine = AudioEngine(audio_dir)
    hm = HotkeyManager(engine, cm)
    
    # Test hotkey rebinding
    success, msg = hm.rebind_sound_hotkey(first_id, 'ctrl+shift+1')
    print(f"[TEST] Rebind result: {success}, {msg}")
    assert success, f"Failed to rebind: {msg}"
    
    # Test panic key update
    hm.update_panic_key('esc')
    assert cm.config['panic_key'] == 'esc'
    
    # Clean up test config file
    if os.path.exists(config_path):
        os.remove(config_path)
        
    print("[TEST] Config and Hotkey Managers tests passed successfully!")

if __name__ == '__main__':
    test_managers()
