import keyboard
import requests
import time
import threading
from typing import Dict, Optional
import json
import subprocess
import os

class SoundboardHotkeyClientSimple:
    """
    Simple enhanced hotkey client that forces browser tab refresh/activation
    for reliable audio playback when browser is not focused.
    """
    
    def __init__(self, soundboard_url: str = "http://localhost:5000"):
        self.soundboard_url = soundboard_url.rstrip('/')
        self.sounds: Dict = {}
        self.hotkey_map: Dict[str, str] = {}
        self.running = False
        
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

        try:
            test_sound = "Afraid.mp3"
            response = requests.post(f"{self.soundboard_url}/api/play", 
                                   json={"sound": test_sound}, timeout=3)
            if response.status_code == 200:
                print(f"✅ Play endpoint: OK (tested with {test_sound})")
            else:
                print(f"❌ Play endpoint failed: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Play test failed: {e}")
            return False

        return True

    def load_sounds(self) -> bool:
        """Load sound mappings from the containerized app"""
        try:
            response = requests.get(f"{self.soundboard_url}/api/sounds", timeout=5)
            if response.status_code == 200:
                self.sounds = response.json()
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
        self.hotkey_map = {}
        for hotkey, sound_info in self.sounds.items():
            if isinstance(sound_info, dict) and 'file' in sound_info:
                self.hotkey_map[hotkey] = sound_info['file']
            elif isinstance(sound_info, str):
                self.hotkey_map[hotkey] = sound_info

    def activate_browser_tab(self):
        """Force browser tab to become active using JavaScript injection"""
        try:
            # Send a special activation request to the container
            response = requests.post(f"{self.soundboard_url}/api/activate", 
                                   json={"action": "focus"}, timeout=2)
            if response.status_code == 200:
                print("🔄 Browser activation signal sent")
            else:
                print(f"⚠️ Browser activation failed: {response.status_code}")
        except Exception as e:
            print(f"⚠️ Browser activation error: {e}")

    def play_sound_enhanced(self, sound_file: str, hotkey: str):
        """Play sound with enhanced activation"""
        try:
            print(f"🎵 Hotkey {hotkey.upper()} pressed - playing {sound_file}")
            
            # Method 1: Send activation request
            self.activate_browser_tab()
            
            # Small delay to let browser respond
            time.sleep(0.05)
            
            # Method 2: Send play request
            response = requests.post(f"{self.soundboard_url}/api/play", 
                                   json={"sound": sound_file, "force": True}, timeout=2)
            
            if response.status_code == 200:
                print(f"✅ Sound request sent successfully")
            else:
                print(f"❌ Play request failed: HTTP {response.status_code}")
                
            # Method 3: Fallback - try to open browser tab
            if response.status_code != 200:
                print("🔄 Attempting browser fallback...")
                subprocess.run(['start', f'{self.soundboard_url}/?play={sound_file}'], 
                             shell=True, capture_output=True)
                
        except Exception as e:
            print(f"❌ Error playing sound: {e}")

    def setup_hotkeys(self):
        """Register all global hotkeys"""
        print("Setting up global hotkeys...")
        
        registered_count = 0
        for hotkey, sound_file in self.hotkey_map.items():
            try:
                keyboard.add_hotkey(hotkey, self.play_sound_enhanced, args=(sound_file, hotkey))
                print(f"📌 Registered: {hotkey} -> {sound_file}")
                registered_count += 1
            except Exception as e:
                print(f"❌ Failed to register {hotkey}: {e}")
        
        print(f"✅ Successfully registered {registered_count}/{len(self.hotkey_map)} hotkeys")
        return registered_count > 0

    def run(self):
        """Main execution loop"""
        print("🎹 Starting Enhanced Global Hotkey Client")
        print("============================================================")
        
        if not self.load_sounds():
            print("❌ Failed to load sounds from server")
            return False
            
        if not self.test_connection():
            print("❌ Connection test failed")
            return False
            
        self.create_hotkey_map()
        
        if not self.setup_hotkeys():
            print("❌ Failed to setup hotkeys")
            return False
            
        print("✅ Enhanced global hotkeys are now active!")
        print("🎵 Using multiple methods to ensure audio playback")
        print("🔄 Browser activation and fallback mechanisms enabled")
        print("🧪 Test a hotkey now - keep browser tab open!")
        print("")
        
        # Display hotkey mappings
        self.display_hotkey_mappings()
        
        print("💡 Tips:")
        print("   • Keep browser window/tab open")
        print("   • First hotkey press may need browser interaction")
        print("   • Audio works best after clicking in browser once")
        print("   • Press Ctrl+C to stop")
        print("============================================================")
        
        self.running = True
        
        try:
            keyboard.wait()
        except KeyboardInterrupt:
            print("\n👋 Stopping enhanced hotkey client...")
            self.running = False
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
    client = SoundboardHotkeyClientSimple()
    client.run()
