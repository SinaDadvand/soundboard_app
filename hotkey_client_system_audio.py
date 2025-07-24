import keyboard
import requests
import time
import threading
from typing import Dict, Optional
import json
import pygame
import os

class SoundboardHotkeyClientSystemAudio:
    """
    True hybrid hotkey client that plays audio directly on the system
    instead of relying on browser Web Audio API. This solves the
    browser focus limitation completely.
    """
    
    def __init__(self, soundboard_url: str = "http://localhost:5000"):
        self.soundboard_url = soundboard_url.rstrip('/')
        self.sounds: Dict = {}
        self.hotkey_map: Dict[str, str] = {}
        self.running = False
        self.audio_cache: Dict = {}
        
        # Initialize pygame mixer for system audio
        self.init_pygame_mixer()
        
    def init_pygame_mixer(self):
        """Initialize pygame mixer for direct system audio playback"""
        try:
            pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=512)
            pygame.mixer.init()
            print("✅ System audio (pygame) initialized successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize system audio: {e}")
            return False
    
    def download_and_cache_audio(self, sound_file: str) -> bool:
        """Download audio file from container and cache it locally"""
        if sound_file in self.audio_cache:
            return True
            
        try:
            # Create local cache directory
            cache_dir = os.path.join(os.path.dirname(__file__), 'audio_cache')
            os.makedirs(cache_dir, exist_ok=True)
            
            # Download audio file from container
            response = requests.get(f"{self.soundboard_url}/audio/{sound_file}", timeout=10)
            if response.status_code == 200:
                cache_path = os.path.join(cache_dir, sound_file)
                with open(cache_path, 'wb') as f:
                    f.write(response.content)
                
                # Load into pygame
                sound = pygame.mixer.Sound(cache_path)
                self.audio_cache[sound_file] = sound
                print(f"📁 Cached: {sound_file}")
                return True
            else:
                print(f"❌ Failed to download {sound_file}: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error caching {sound_file}: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Test connection to the containerized app"""
        print("🔍 Testing connection to containerized soundboard...")
        
        try:
            response = requests.get(f"{self.soundboard_url}/", timeout=3)
            if response.status_code == 200:
                print("✅ Basic connectivity: OK")
            else:
                print(f"❌ Basic connectivity failed: HTTP {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Connection failed: {e}")
            return False

        try:
            response = requests.get(f"{self.soundboard_url}/api/sounds", timeout=3)
            if response.status_code == 200:
                sounds_data = response.json()
                print(f"✅ API endpoint: OK ({len(sounds_data)} sounds found)")
            else:
                print(f"❌ API endpoint failed: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ API test failed: {e}")
            return False

        return True

    def load_sounds(self) -> bool:
        """Load sound mappings from the containerized app"""
        try:
            response = requests.get(f"{self.soundboard_url}/api/sounds", timeout=5)
            if response.status_code == 200:
                sounds_list = response.json()
                
                # Convert list to dictionary format
                self.sounds = {}
                for sound_data in sounds_list:
                    hotkey = sound_data['hotkey']
                    filename = sound_data['filename']
                    self.sounds[hotkey] = filename
                
                print(f"✅ Loaded {len(self.sounds)} hotkey mappings from server")
                return True
            else:
                print(f"❌ Failed to load sounds: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error loading sounds: {e}")
            return False

    def create_hotkey_map(self):
        """Create mapping from keyboard combinations to sound files"""
        self.hotkey_map = self.sounds.copy()

    def cache_all_sounds(self):
        """Download and cache all audio files for offline playback"""
        print("📦 Downloading and caching all audio files...")
        cached_count = 0
        
        for hotkey, sound_file in self.hotkey_map.items():
            if self.download_and_cache_audio(sound_file):
                cached_count += 1
                
        print(f"✅ Successfully cached {cached_count}/{len(self.hotkey_map)} audio files")
        return cached_count > 0

    def play_sound_system(self, sound_file: str, hotkey: str):
        """Play sound directly through system audio (pygame)"""
        try:
            print(f"🎵 Hotkey {hotkey.upper()} pressed - playing {sound_file}")
            
            if sound_file in self.audio_cache:
                sound = self.audio_cache[sound_file]
                sound.play()
                print(f"✅ Playing {sound_file} via system audio")
            else:
                print(f"❌ Sound {sound_file} not in cache")
                
        except Exception as e:
            print(f"❌ Error playing sound: {e}")

    def setup_hotkeys(self):
        """Register all global hotkeys"""
        print("Setting up global hotkeys...")
        
        registered_count = 0
        for hotkey, sound_file in self.hotkey_map.items():
            try:
                keyboard.add_hotkey(hotkey, self.play_sound_system, args=(sound_file, hotkey))
                print(f"📌 Registered: {hotkey} -> {sound_file}")
                registered_count += 1
            except Exception as e:
                print(f"❌ Failed to register {hotkey}: {e}")
        
        print(f"✅ Successfully registered {registered_count}/{len(self.hotkey_map)} hotkeys")
        return registered_count > 0

    def run(self):
        """Main execution loop"""
        print("🎹 Starting System Audio Hotkey Client")
        print("============================================================")
        print("🔊 This version plays audio directly through your system")
        print("🌐 No browser focus limitations!")
        print("============================================================")
        
        if not self.load_sounds():
            print("❌ Failed to load sounds from server")
            return False
            
        if not self.test_connection():
            print("❌ Connection test failed")
            return False
            
        self.create_hotkey_map()
        
        # Cache all audio files for offline playback
        if not self.cache_all_sounds():
            print("❌ Failed to cache audio files")
            return False
        
        if not self.setup_hotkeys():
            print("❌ Failed to setup hotkeys")
            return False
            
        print("✅ System audio hotkeys are now active!")
        print("🎵 Audio plays directly through your speakers/headphones")
        print("🚀 Works from ANY application - no browser focus needed!")
        print("🐳 Container still provides the web interface")
        print("")
        
        # Display hotkey mappings
        self.display_hotkey_mappings()
        
        print("💡 Key Features:")
        print("   • Direct system audio playback (pygame)")
        print("   • No browser focus limitations")
        print("   • Cached audio files for fast playback")
        print("   • Global hotkeys work from any app")
        print("   • Press Ctrl+C to stop")
        print("============================================================")
        
        self.running = True
        
        try:
            keyboard.wait()
        except KeyboardInterrupt:
            print("\n👋 Stopping system audio hotkey client...")
            self.running = False
            pygame.mixer.quit()
            return True

    def display_hotkey_mappings(self):
        """Display organized hotkey mappings"""
        print("Hotkey mappings:")
        
        ctrl_hotkeys = {k: v for k, v in self.hotkey_map.items() if k.startswith('ctrl+') and 'alt' not in k}
        alt_hotkeys = {k: v for k, v in self.hotkey_map.items() if k.startswith('alt+') and 'ctrl' not in k}
        ctrl_alt_hotkeys = {k: v for k, v in self.hotkey_map.items() if 'ctrl+alt' in k}
        
        if ctrl_hotkeys:
            print("🔵 Ctrl + Number Keys:")
            for hotkey, sound_file in sorted(ctrl_hotkeys.items()):
                sound_name = sound_file.replace('.mp3', '').replace('.wav', '')
                print(f"  {hotkey.upper()} -> {sound_name}")
                
        if alt_hotkeys:
            print("🟡 Alt + Number Keys:")
            for hotkey, sound_file in sorted(alt_hotkeys.items()):
                sound_name = sound_file.replace('.mp3', '').replace('.wav', '')
                print(f"  {hotkey.upper()} -> {sound_name}")
                
        if ctrl_alt_hotkeys:
            print("🟣 Ctrl + Alt + Number Keys:")
            for hotkey, sound_file in sorted(ctrl_alt_hotkeys.items()):
                sound_name = sound_file.replace('.mp3', '').replace('.wav', '')
                print(f"  {hotkey.upper()} -> {sound_name}")

if __name__ == "__main__":
    client = SoundboardHotkeyClientSystemAudio()
    client.run()
