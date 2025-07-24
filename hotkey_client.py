import keyboard
import requests
import time
import threading
from typing import Dict, Optional
import json

class SoundboardHotkeyClient:
    """
    Lightweight client that runs on host to provide global hotkeys
    for the containerized soundboard app.
    """
    
    def __init__(self, soundboard_url: str = "http://localhost:5000"):
        self.soundboard_url = soundboard_url.rstrip('/')
        self.sounds: Dict = {}
        self.hotkey_map: Dict[str, str] = {}
        self.running = False
        
    def test_connection(self) -> bool:
        """Test connection to the containerized app"""
        print("🔍 Testing connection to containerized soundboard...")
        
        # Test 1: Basic connectivity
        try:
            response = requests.get(f"{self.soundboard_url}/", timeout=3)
            if response.status_code == 200:
                print("✅ Basic connectivity: OK")
            else:
                print(f"❌ Basic connectivity failed: HTTP {response.status_code}")
                return False
        except requests.RequestException as e:
            print(f"❌ Basic connectivity failed: {e}")
            return False
        
        # Test 2: API endpoint
        try:
            response = requests.get(f"{self.soundboard_url}/api/sounds", timeout=3)
            if response.status_code == 200:
                sounds_data = response.json()
                print(f"✅ API endpoint: OK ({len(sounds_data)} sounds found)")
            else:
                print(f"❌ API endpoint failed: HTTP {response.status_code}")
                return False
        except requests.RequestException as e:
            print(f"❌ API endpoint failed: {e}")
            return False
        
        # Test 3: Play endpoint (try first sound)
        if self.hotkey_map:
            first_filename = next(iter(self.hotkey_map.values()))
            try:
                response = requests.get(f"{self.soundboard_url}/play/{first_filename}", timeout=3)
                if response.status_code == 200:
                    print(f"✅ Play endpoint: OK (tested with {first_filename})")
                else:
                    print(f"❌ Play endpoint failed: HTTP {response.status_code}")
                    return False
            except requests.RequestException as e:
                print(f"❌ Play endpoint failed: {e}")
                return False
        
        return True
    
    def load_sounds_from_server(self) -> bool:
        """Load sound mappings from the containerized app"""
        try:
            response = requests.get(f"{self.soundboard_url}/api/sounds", timeout=5)
            if response.status_code == 200:
                sounds_data = response.json()
                
                # Build hotkey mapping
                self.hotkey_map.clear()
                for sound in sounds_data:
                    hotkey = sound['hotkey']
                    filename = sound['filename']
                    self.hotkey_map[hotkey] = filename
                    
                print(f"✅ Loaded {len(self.hotkey_map)} hotkey mappings from server")
                return True
            else:
                print(f"❌ Server returned status {response.status_code}")
                return False
                
        except requests.RequestException as e:
            print(f"❌ Failed to connect to soundboard server: {e}")
            return False
    
    def play_sound(self, filename: str) -> None:
        """Send play request to the containerized app"""
        try:
            print(f"🎵 Attempting to play: {filename}")
            response = requests.get(f"{self.soundboard_url}/play/{filename}", timeout=2)
            if response.status_code == 200:
                print(f"✅ Successfully triggered: {filename}")
            else:
                print(f"❌ Failed to play {filename}: HTTP {response.status_code}")
                print(f"   Response: {response.text}")
        except requests.RequestException as e:
            print(f"❌ Error playing {filename}: {e}")
    
    def setup_hotkeys(self) -> None:
        """Setup global hotkeys using keyboard library"""
        print("Setting up global hotkeys...")
        
        registered_count = 0
        for hotkey, filename in self.hotkey_map.items():
            try:
                # Register the hotkey
                keyboard.add_hotkey(hotkey, self.play_sound, args=(filename,))
                print(f"📌 Registered: {hotkey} -> {filename}")
                registered_count += 1
            except Exception as e:
                print(f"❌ Failed to register {hotkey}: {e}")
        
        print(f"✅ Successfully registered {registered_count}/{len(self.hotkey_map)} hotkeys")
    
    def check_server_health(self) -> None:
        """Periodically check if server is still running"""
        while self.running:
            try:
                response = requests.get(f"{self.soundboard_url}/", timeout=3)
                if response.status_code != 200:
                    print("⚠️ Soundboard server seems to be down")
            except requests.RequestException:
                print("⚠️ Lost connection to soundboard server")
            
            time.sleep(30)  # Check every 30 seconds
    
    def start(self) -> None:
        """Start the hotkey client"""
        print("🎹 Starting Global Hotkey Client for Containerized Soundboard")
        print("=" * 60)
        
        # Load sound mappings from server
        if not self.load_sounds_from_server():
            print("❌ Cannot start - failed to load sounds from server")
            print("🔍 Make sure the containerized soundboard is running at:")
            print(f"   {self.soundboard_url}")
            return
        
        # Test connection
        if not self.test_connection():
            print("❌ Connection test failed - cannot continue")
            return
        
        # Setup hotkeys
        self.setup_hotkeys()
        
        # Start health check thread
        self.running = True
        health_thread = threading.Thread(target=self.check_server_health, daemon=True)
        health_thread.start()
        
        print("\n✅ Global hotkeys are now active!")
        print("🎵 You can now use hotkeys from any application")
        print("🐳 Audio will play through the containerized soundboard")
        print("\n🧪 Test a hotkey now to verify it's working...")
        print("\nHotkey mappings:")
        
        # Group and display hotkeys
        ctrl_hotkeys = [(k, v) for k, v in self.hotkey_map.items() if k.startswith('ctrl+') and not k.startswith('ctrl+alt+')]
        alt_hotkeys = [(k, v) for k, v in self.hotkey_map.items() if k.startswith('alt+') and not k.startswith('ctrl+alt+')]
        ctrl_alt_hotkeys = [(k, v) for k, v in self.hotkey_map.items() if k.startswith('ctrl+alt+')]
        
        if ctrl_hotkeys:
            print("\n🔵 Ctrl + Number Keys:")
            for hotkey, filename in ctrl_hotkeys:
                sound_name = filename.split('.')[0]
                print(f"  {hotkey.upper()} -> {sound_name}")
        
        if alt_hotkeys:
            print("\n🟡 Alt + Number Keys:")
            for hotkey, filename in alt_hotkeys:
                sound_name = filename.split('.')[0]
                print(f"  {hotkey.upper()} -> {sound_name}")
        
        if ctrl_alt_hotkeys:
            print("\n🟣 Ctrl + Alt + Number Keys:")
            for hotkey, filename in ctrl_alt_hotkeys:
                sound_name = filename.split('.')[0]
                print(f"  {hotkey.upper()} -> {sound_name}")
        
        print("\n💡 Tips:")
        print("   • Hotkeys work globally (from any application)")
        print("   • Keep this window open while using hotkeys")
        print("   • Audio plays through the web browser")
        print("   • Press Ctrl+C to stop")
        print("   • Try pressing one of the hotkeys above to test!")
        print("=" * 60)
        
        # Add a manual test hotkey
        print("\n🧪 Manual test: Press F12 to test the first sound")
        if self.hotkey_map:
            first_filename = next(iter(self.hotkey_map.values()))
            keyboard.add_hotkey('f12', self.play_sound, args=(first_filename,))
            print(f"   F12 will play: {first_filename}")
        
        try:
            # Keep the program running
            keyboard.wait()
        except KeyboardInterrupt:
            print("\n👋 Stopping Global Hotkey Client...")
            self.running = False

def main():
    """Main entry point"""
    client = SoundboardHotkeyClient()
    client.start()

if __name__ == "__main__":
    main()
