import keyboard
import requests
import time
import threading
from typing import Dict, Optional
import json
import ctypes
from ctypes import wintypes
import win32gui
import win32con
import win32process
import psutil

class SoundboardHotkeyClientEnhanced:
    """
    Enhanced hotkey client that briefly activates browser window for audio playback,
    then returns focus to the original application.
    """
    
    def __init__(self, soundboard_url: str = "http://localhost:5000"):
        self.soundboard_url = soundboard_url.rstrip('/')
        self.sounds: Dict = {}
        self.hotkey_map: Dict[str, str] = {}
        self.running = False
        self.browser_window = None
        self.last_active_window = None
        
    def find_browser_window(self):
        """Find the browser window containing our soundboard"""
        def enum_windows_callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                window_title = win32gui.GetWindowText(hwnd)
                # Look for common browser titles that might contain our soundboard
                browser_keywords = ['localhost:5000', 'soundboard', 'chrome', 'firefox', 'edge', 'browser']
                if any(keyword.lower() in window_title.lower() for keyword in browser_keywords):
                    windows.append((hwnd, window_title))
        
        windows = []
        win32gui.EnumWindows(enum_windows_callback, windows)
        
        # Prefer windows that explicitly mention localhost:5000
        for hwnd, title in windows:
            if 'localhost:5000' in title.lower() or 'soundboard' in title.lower():
                self.browser_window = hwnd
                print(f"🌐 Found soundboard browser window: {title}")
                return hwnd
                
        # Fallback to any browser window
        if windows:
            self.browser_window = windows[0][0]
            print(f"🌐 Using browser window: {windows[0][1]}")
            return windows[0][0]
            
        print("⚠️ No browser window found - audio may not work when browser is not focused")
        return None

    def get_foreground_window(self):
        """Get the currently active window"""
        return win32gui.GetForegroundWindow()

    def set_foreground_window(self, hwnd):
        """Set the specified window as foreground"""
        try:
            # Get current foreground window
            current_hwnd = win32gui.GetForegroundWindow()
            current_thread_id = win32process.GetWindowThreadProcessId(current_hwnd)[0]
            target_thread_id = win32process.GetWindowThreadProcessId(hwnd)[0]
            
            # Attach input to target thread
            if current_thread_id != target_thread_id:
                ctypes.windll.user32.AttachThreadInput(current_thread_id, target_thread_id, True)
            
            # Bring window to front
            win32gui.SetForegroundWindow(hwnd)
            win32gui.SetActiveWindow(hwnd)
            
            # Detach threads
            if current_thread_id != target_thread_id:
                ctypes.windll.user32.AttachThreadInput(current_thread_id, target_thread_id, False)
                
            return True
        except Exception as e:
            print(f"⚠️ Could not set foreground window: {e}")
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

    def play_sound_enhanced(self, sound_file: str, hotkey: str):
        """Play sound with enhanced browser focus management"""
        try:
            print(f"🎵 Hotkey {hotkey.upper()} pressed - playing {sound_file}")
            
            # Remember the current active window
            self.last_active_window = self.get_foreground_window()
            
            # If we have a browser window, briefly activate it
            if self.browser_window:
                print(f"🔄 Temporarily activating browser for audio...")
                self.set_foreground_window(self.browser_window)
                time.sleep(0.1)  # Brief delay for browser to become active
            
            # Send play request to container
            response = requests.post(f"{self.soundboard_url}/api/play", 
                                   json={"sound": sound_file}, timeout=2)
            
            if response.status_code == 200:
                print(f"✅ Sound request sent successfully")
                # Give audio time to start
                time.sleep(0.2)
            else:
                print(f"❌ Play request failed: HTTP {response.status_code}")
                
            # Return focus to the original window
            if self.last_active_window and self.last_active_window != self.browser_window:
                print(f"🔄 Returning focus to original application...")
                self.set_foreground_window(self.last_active_window)
                
        except Exception as e:
            print(f"❌ Error playing sound: {e}")
            # Try to restore focus anyway
            if self.last_active_window:
                self.set_foreground_window(self.last_active_window)

    def setup_hotkeys(self):
        """Register all global hotkeys"""
        print("Setting up global hotkeys...")
        
        registered_count = 0
        for hotkey, sound_file in self.hotkey_map.items():
            try:
                # Register the hotkey with our enhanced play function
                keyboard.add_hotkey(hotkey, self.play_sound_enhanced, args=(sound_file, hotkey))
                print(f"📌 Registered: {hotkey} -> {sound_file}")
                registered_count += 1
            except Exception as e:
                print(f"❌ Failed to register {hotkey}: {e}")
        
        print(f"✅ Successfully registered {registered_count}/{len(self.hotkey_map)} hotkeys")
        return registered_count > 0

    def run(self):
        """Main execution loop"""
        print("🎹 Starting Enhanced Global Hotkey Client for Containerized Soundboard")
        print("============================================================")
        
        # Load sounds from server
        if not self.load_sounds():
            print("❌ Failed to load sounds from server")
            return False
            
        # Test connection
        if not self.test_connection():
            print("❌ Connection test failed")
            return False
            
        # Find browser window
        self.find_browser_window()
            
        # Create hotkey mappings
        self.create_hotkey_map()
        
        # Setup hotkeys
        if not self.setup_hotkeys():
            print("❌ Failed to setup hotkeys")
            return False
            
        print("✅ Enhanced global hotkeys are now active!")
        print("🎵 Hotkeys will briefly activate browser window for audio playback")
        print("🔄 Focus will automatically return to your original application")
        print("🐳 Audio plays through the containerized soundboard")
        print("🧪 Test a hotkey now to verify it's working...")
        print("")
        
        # Display hotkey mappings
        self.display_hotkey_mappings()
        
        print("💡 Enhanced Features:")
        print("   • Automatic browser window activation")
        print("   • Focus restoration to original app")
        print("   • Better audio playback reliability")
        print("   • Press Ctrl+C to stop")
        print("============================================================")
        
        self.running = True
        
        try:
            # Keep the program running
            keyboard.wait()
        except KeyboardInterrupt:
            print("\n👋 Stopping enhanced hotkey client...")
            self.running = False
            return True

    def display_hotkey_mappings(self):
        """Display organized hotkey mappings"""
        print("Hotkey mappings:")
        
        # Group hotkeys by modifier
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
    client = SoundboardHotkeyClientEnhanced()
    client.run()
