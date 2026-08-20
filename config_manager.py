"""
Config Manager for Virtual Soundboard
=====================================
Handles JSON persistence for sounds, hotkeys, audio device routing,
and per-clip FX parameters (volume, pitch, speed).
Organized into 3 standard numpad modifier sections: Ctrl, Alt, Ctrl+Alt.
"""

import os
import json
import uuid

# 3 Numpad Layout Groups (ordered as: 7, 8, 9, 4, 5, 6, 1, 2, 3, 0, .)
NUMPAD_KEY_ORDER = [
    # Ctrl Group
    ('ctrl+7', '7', 'ctrl'), ('ctrl+8', '8', 'ctrl'), ('ctrl+9', '9', 'ctrl'),
    ('ctrl+4', '4', 'ctrl'), ('ctrl+5', '5', 'ctrl'), ('ctrl+6', '6', 'ctrl'),
    ('ctrl+1', '1', 'ctrl'), ('ctrl+2', '2', 'ctrl'), ('ctrl+3', '3', 'ctrl'),
    ('ctrl+0', '0', 'ctrl'), ('ctrl+.', '.', 'ctrl'),

    # Alt Group
    ('alt+7', '7', 'alt'), ('alt+8', '8', 'alt'), ('alt+9', '9', 'alt'),
    ('alt+4', '4', 'alt'), ('alt+5', '5', 'alt'), ('alt+6', '6', 'alt'),
    ('alt+1', '1', 'alt'), ('alt+2', '2', 'alt'), ('alt+3', '3', 'alt'),
    ('alt+0', '0', 'alt'), ('alt+.', '.', 'alt'),

    # Ctrl + Alt Group
    ('ctrl+alt+7', '7', 'ctrl+alt'), ('ctrl+alt+8', '8', 'ctrl+alt'), ('ctrl+alt+9', '9', 'ctrl+alt'),
    ('ctrl+alt+4', '4', 'ctrl+alt'), ('ctrl+alt+5', '5', 'ctrl+alt'), ('ctrl+alt+6', '6', 'ctrl+alt'),
    ('ctrl+alt+1', '1', 'ctrl+alt'), ('ctrl+alt+2', '2', 'ctrl+alt'), ('ctrl+alt+3', '3', 'ctrl+alt'),
    ('ctrl+alt+0', '0', 'ctrl+alt'), ('ctrl+alt+.', '.', 'ctrl+alt')
]


class ConfigManager:
    def __init__(self, config_path=None, audio_dir=None):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_path = config_path or os.path.join(base_dir, 'soundboard_config.json')
        self.audio_dir = audio_dir or os.path.join(base_dir, 'static', 'audio')
        os.makedirs(self.audio_dir, exist_ok=True)
        self.config = self.load_config()

    def get_default_config(self):
        return {
            "version": "2.2",
            "master_volume": 0.9,
            "global_pitch": 0.0,
            "global_speed": 1.0,
            "global_echo": 0.0,
            "global_reverb": 0.0,
            "panic_key": "esc",
            "primary_device": None,
            "secondary_device": None,
            "secondary_enabled": True,
            "headset_enabled": True,
            "cable_enabled": True,
            "sounds": []
        }

    def load_config(self):
        """Load configuration from JSON or initialize from audio directory."""
        config = self.get_default_config()
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    config.update(loaded)
            except Exception as e:
                print(f"[ConfigManager] Error reading config: {e}. Generating new.")
        
        self.sync_audio_files(config)
        self.save_config(config)
        return config

    def sync_audio_files(self, config, force_reassign_hotkeys=True):
        """Ensure all audio files in the audio folder have structured numpad config entries sorted A to Z."""
        valid_exts = ('.mp3', '.wav', '.ogg', '.flac')
        existing_files = [f for f in os.listdir(self.audio_dir) if f.lower().endswith(valid_exts)]
        existing_files.sort(key=lambda x: x.lower())

        sound_map = {s['filename']: s for s in config.get('sounds', [])}
        updated_sounds = []

        total_keys = len(NUMPAD_KEY_ORDER)

        for idx, filename in enumerate(existing_files):
            key_info = NUMPAD_KEY_ORDER[idx] if idx < total_keys else (None, None, 'custom')

            if filename in sound_map:
                entry = sound_map[filename]
                entry.setdefault('id', str(uuid.uuid4())[:8])
                entry.setdefault('name', os.path.splitext(filename)[0])
                if force_reassign_hotkeys or not entry.get('hotkey'):
                    entry['hotkey'] = key_info[0]
                    entry['symbol'] = key_info[1]
                    entry['modifier'] = key_info[2]
                entry.setdefault('volume', 1.0)
                entry.setdefault('speed', 1.0)
                entry.setdefault('pitch', 0.0)
                entry['order'] = idx
                updated_sounds.append(entry)
            else:
                clean_name = os.path.splitext(filename)[0]
                new_entry = {
                    'id': str(uuid.uuid4())[:8],
                    'filename': filename,
                    'name': clean_name,
                    'hotkey': key_info[0],
                    'symbol': key_info[1],
                    'modifier': key_info[2],
                    'volume': 1.0,
                    'speed': 1.0,
                    'pitch': 0.0,
                    'order': idx
                }
                updated_sounds.append(new_entry)

        config['sounds'] = updated_sounds

    def save_config(self, config=None):
        """Save current configuration to JSON file."""
        if config is not None:
            self.config = config
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
            return True
        except Exception as e:
            print(f"[ConfigManager] Error saving config: {e}")
            return False

    def get_sound_by_id(self, sound_id):
        for s in self.config.get('sounds', []):
            if s['id'] == sound_id:
                return s
        return None

    def get_sound_by_hotkey(self, hotkey):
        if not hotkey:
            return None
        clean_hk = hotkey.strip().lower()
        for s in self.config.get('sounds', []):
            if s.get('hotkey') and s['hotkey'].strip().lower() == clean_hk:
                return s
        return None

    def update_sound(self, sound_id, updates):
        """Update properties of an existing sound entry."""
        for s in self.config.get('sounds', []):
            if s['id'] == sound_id:
                s.update(updates)
                self.save_config()
                return s
        return None

    def replace_sound_by_hotkey(self, hotkey, filename, name=None, volume=1.0, speed=1.0, pitch=0.0, delete_old_file=False):
        """Replace existing sound assigned to a given hotkey with a new file."""
        clean_hk = str(hotkey).strip().lower()
        existing = self.get_sound_by_hotkey(clean_hk)
        if not existing:
            return None

        old_file = existing.get('filename')
        if delete_old_file and old_file and old_file != filename:
            old_path = os.path.join(self.audio_dir, old_file)
            if os.path.exists(old_path):
                try:
                    os.remove(old_path)
                except Exception as e:
                    print(f"[ConfigManager] Notice deleting replaced audio file {old_path}: {e}")

        existing['filename'] = filename
        existing['name'] = name or os.path.splitext(filename)[0]
        existing['volume'] = float(volume)
        existing['speed'] = float(speed)
        existing['pitch'] = float(pitch)
        self.save_config()
        return existing

    def add_sound(self, filename, name=None, hotkey=None, volume=1.0, speed=1.0, pitch=0.0):
        """Add a newly uploaded sound file to configuration, replacing if hotkey already exists."""
        if hotkey:
            replaced = self.replace_sound_by_hotkey(hotkey, filename, name=name, volume=volume, speed=speed, pitch=pitch)
            if replaced:
                return replaced

        clean_name = name or os.path.splitext(filename)[0]
        sound_id = str(uuid.uuid4())[:8]
        
        idx = len(self.config.get('sounds', []))
        key_info = NUMPAD_KEY_ORDER[idx] if idx < len(NUMPAD_KEY_ORDER) else (hotkey, None, 'custom')

        entry = {
            'id': sound_id,
            'filename': filename,
            'name': clean_name,
            'hotkey': hotkey or key_info[0],
            'symbol': key_info[1],
            'modifier': key_info[2],
            'volume': float(volume),
            'speed': float(speed),
            'pitch': float(pitch),
            'order': idx
        }
        self.config['sounds'].append(entry)
        self.save_config()
        return entry

    def delete_sound(self, sound_id, delete_file=True):
        """Remove sound from config and optionally delete file."""
        sound = self.get_sound_by_id(sound_id)
        if not sound:
            return False

        if delete_file:
            filepath = os.path.join(self.audio_dir, sound['filename'])
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except Exception as e:
                    print(f"[ConfigManager] Could not delete audio file {filepath}: {e}")

        self.config['sounds'] = [s for s in self.config['sounds'] if s['id'] != sound_id]
        self.save_config()
        return True
