"""
Config Manager for Virtual Soundboard
=====================================
Handles JSON persistence for sounds, soundbanks/categories, hotkeys,
audio device routing, and FX defaults.
"""

import os
import json
import uuid

DEFAULT_NUMPAD_HOTKEYS = [
    # Ctrl + numpad
    'ctrl+7', 'ctrl+8', 'ctrl+9',
    'ctrl+4', 'ctrl+5', 'ctrl+6',
    'ctrl+1', 'ctrl+2', 'ctrl+3',
    'ctrl+0', 'ctrl+.',
    # Alt + numpad
    'alt+7', 'alt+8', 'alt+9',
    'alt+4', 'alt+5', 'alt+6',
    'alt+1', 'alt+2', 'alt+3',
    'alt+0', 'alt+.',
    # Ctrl + Alt + numpad
    'ctrl+alt+7', 'ctrl+alt+8', 'ctrl+alt+9',
    'ctrl+alt+4', 'ctrl+alt+5', 'ctrl+alt+6',
    'ctrl+alt+1', 'ctrl+alt+2', 'ctrl+alt+3',
    'ctrl+alt+0', 'ctrl+alt+.'
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
            "version": "2.0",
            "master_volume": 1.0,
            "panic_key": "esc",
            "primary_device": None,
            "secondary_device": None,
            "secondary_enabled": False,
            "active_category": "All",
            "categories": ["All", "Memes", "Gaming", "Quotes", "Favorites"],
            "sounds": []
        }

    def load_config(self):
        """Load configuration from JSON or generate initial config from audio folder."""
        config = self.get_default_config()
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    config.update(loaded)
            except Exception as e:
                print(f"[ConfigManager] Error reading config: {e}. Generating new.")
        
        # Sync with files in audio directory
        self.sync_audio_files(config)
        self.save_config(config)
        return config

    def sync_audio_files(self, config):
        """Ensure all audio files in the audio folder have config entries."""
        valid_exts = ('.mp3', '.wav', '.ogg', '.flac')
        existing_files = [f for f in os.listdir(self.audio_dir) if f.lower().endswith(valid_exts)]
        existing_files.sort()

        sound_map = {s['filename']: s for s in config.get('sounds', [])}
        updated_sounds = []

        used_hotkeys = {s['hotkey'] for s in config.get('sounds', []) if s.get('hotkey')}

        for idx, filename in enumerate(existing_files):
            if filename in sound_map:
                entry = sound_map[filename]
                # Ensure all fields exist
                entry.setdefault('id', str(uuid.uuid4())[:8])
                entry.setdefault('name', os.path.splitext(filename)[0])
                entry.setdefault('category', 'All')
                entry.setdefault('volume', 1.0)
                entry.setdefault('speed', 1.0)
                entry.setdefault('pitch', 0.0)
                entry.setdefault('order', idx)
                updated_sounds.append(entry)
            else:
                # Assign next unused default hotkey if available
                assigned_hotkey = None
                for hk in DEFAULT_NUMPAD_HOTKEYS:
                    if hk not in used_hotkeys:
                        assigned_hotkey = hk
                        used_hotkeys.add(hk)
                        break

                clean_name = os.path.splitext(filename)[0]
                new_entry = {
                    'id': str(uuid.uuid4())[:8],
                    'filename': filename,
                    'name': clean_name,
                    'category': 'All',
                    'hotkey': assigned_hotkey,
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

    def add_sound(self, filename, name=None, category="All", hotkey=None, volume=1.0, speed=1.0, pitch=0.0):
        """Add a newly uploaded sound file to configuration."""
        clean_name = name or os.path.splitext(filename)[0]
        sound_id = str(uuid.uuid4())[:8]
        entry = {
            'id': sound_id,
            'filename': filename,
            'name': clean_name,
            'category': category,
            'hotkey': hotkey,
            'volume': float(volume),
            'speed': float(speed),
            'pitch': float(pitch),
            'order': len(self.config.get('sounds', []))
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

    def add_category(self, category_name):
        cat = category_name.strip()
        if cat and cat not in self.config['categories']:
            self.config['categories'].append(cat)
            self.save_config()
            return True
        return False

    def delete_category(self, category_name):
        if category_name in self.config['categories'] and category_name != 'All':
            self.config['categories'].remove(category_name)
            # Reassign any sound in this category to 'All'
            for s in self.config['sounds']:
                if s.get('category') == category_name:
                    s['category'] = 'All'
            self.save_config()
            return True
        return False
