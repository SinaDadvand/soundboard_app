"""
Hotkey Manager for Virtual Soundboard
=====================================
Manages global system-wide hotkeys dynamically using the `keyboard` library.
Supports live rebinding, custom key combinations, and panic stop key.
"""

import threading

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except (ImportError, OSError, Exception) as e:
    keyboard = None
    KEYBOARD_AVAILABLE = False
    print(f"[HotkeyManager] Global OS keyboard hooks unavailable ({e}). In-browser hotkeys remain fully active.")


class HotkeyManager:
    def __init__(self, audio_engine, config_manager):
        self.audio_engine = audio_engine
        self.config_manager = config_manager
        self.registered_handlers = []
        self.lock = threading.Lock()
        self.listener_started = False

    def start_listener(self):
        """Start background keyboard listener loop if OS hooks are supported."""
        if not KEYBOARD_AVAILABLE or keyboard is None:
            return
        if not self.listener_started:
            try:
                t = threading.Thread(target=keyboard.wait, daemon=True)
                t.start()
                self.listener_started = True
                print("[HotkeyManager] Global keyboard listener started.")
            except Exception as e:
                print(f"[HotkeyManager] Notice: keyboard listener not started ({e})")

    def reload_all_hotkeys(self):
        """Unregister all existing hotkeys and register from latest config."""
        if not KEYBOARD_AVAILABLE or keyboard is None:
            return
        with self.lock:
            # Clear all existing hotkey handlers
            try:
                for handler in self.registered_handlers:
                    try:
                        keyboard.remove_hotkey(handler)
                    except Exception:
                        pass
                keyboard.clear_all_hotkeys()
            except Exception as e:
                print(f"[HotkeyManager] Warning when clearing hotkeys: {e}")
            self.registered_handlers.clear()

            # Register Panic Key
            panic_key = self.config_manager.config.get('panic_key', 'esc')
            if panic_key:
                try:
                    handler = keyboard.add_hotkey(panic_key, self.on_panic)
                    self.registered_handlers.append(handler)
                    print(f"[HotkeyManager] Registered Panic Key: {panic_key}")
                except Exception as e:
                    print(f"[HotkeyManager] Could not register panic key '{panic_key}': {e}")

            # Register each sound hotkey
            for sound in self.config_manager.config.get('sounds', []):
                hk = sound.get('hotkey')
                if hk:
                    self._register_sound_hotkey(sound)

    def _register_sound_hotkey(self, sound):
        hk = sound.get('hotkey')
        if not hk:
            return False
        
        sound_id = sound['id']
        filename = sound['filename']
        audio_dir = self.config_manager.audio_dir
        filepath = f"{audio_dir}/{filename}"

        def _trigger():
            # Fetch latest parameters from config in case volume/fx were updated live
            latest = self.config_manager.get_sound_by_id(sound_id) or sound
            vol = latest.get('volume', 1.0)
            spd = latest.get('speed', 1.0)
            pitch = latest.get('pitch', 0.0)
            print(f"[HotkeyManager] Triggered: {latest.get('name')} ({hk})")
            self.audio_engine.play(
                filepath,
                volume=vol,
                speed=spd,
                pitch_semitones=pitch,
                sound_id=sound_id
            )

        try:
            handler = keyboard.add_hotkey(hk, _trigger)
            self.registered_handlers.append(handler)
            return True
        except Exception as e:
            print(f"[HotkeyManager] Error registering hotkey '{hk}' for {sound.get('name')}: {e}")
            return False

    def rebind_sound_hotkey(self, sound_id, new_hotkey):
        """Update hotkey for a sound and refresh global listener."""
        sound = self.config_manager.get_sound_by_id(sound_id)
        if not sound:
            return False, "Sound not found"

        # If hotkey is being cleared
        if not new_hotkey or str(new_hotkey).strip() == "":
            self.config_manager.update_sound(sound_id, {'hotkey': None})
            self.reload_all_hotkeys()
            return True, "Hotkey removed"

        clean_hk = str(new_hotkey).strip().lower()

        # Check if another sound already uses this hotkey
        existing = self.config_manager.get_sound_by_hotkey(clean_hk)
        if existing and existing['id'] != sound_id:
            # Unbind from other sound
            self.config_manager.update_sound(existing['id'], {'hotkey': None})

        # Test if valid hotkey syntax
        if KEYBOARD_AVAILABLE and keyboard is not None:
            try:
                keyboard.parse_hotkey(clean_hk)
            except Exception as ex:
                return False, f"Invalid hotkey syntax: {ex}"

        # Update in config
        self.config_manager.update_sound(sound_id, {'hotkey': clean_hk})
        self.reload_all_hotkeys()
        return True, f"Hotkey bound to {clean_hk}"

    def update_panic_key(self, new_panic_key):
        """Update global panic stop key."""
        clean_key = str(new_panic_key).strip().lower() if new_panic_key else 'esc'
        self.config_manager.config['panic_key'] = clean_key
        self.config_manager.save_config()
        self.reload_all_hotkeys()
        return True

    def on_panic(self):
        print("[HotkeyManager] PANIC KEY TRIGGERED! Stopping all audio.")
        self.audio_engine.stop_all()
