from flask import Flask, render_template, send_from_directory, jsonify
import os
import keyboard
import pygame.mixer
import threading
from time import sleep

app = Flask(__name__)

# Configuration
AUDIO_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'audio')
os.makedirs(AUDIO_FOLDER, exist_ok=True)

# Initialize pygame mixer
pygame.mixer.init()

# Dictionary to store sound objects and their hotkeys
sounds = {}

def load_sounds():
    """Load all sound files and assign default hotkeys in numpad order"""
    # Define key order with symbols for both Ctrl and Alt combinations
    numpad_keys = [
        # First set with Ctrl
        ('ctrl+7', '7', 'ctrl'), ('ctrl+8', '8', 'ctrl'), ('ctrl+9', '9', 'ctrl'),
        ('ctrl+4', '4', 'ctrl'), ('ctrl+5', '5', 'ctrl'), ('ctrl+6', '6', 'ctrl'),
        ('ctrl+1', '1', 'ctrl'), ('ctrl+2', '2', 'ctrl'), ('ctrl+3', '3', 'ctrl'),
        ('ctrl+0', '0', 'ctrl'), ('ctrl+.', '.', 'ctrl'),
        # Second set with Alt
        ('alt+7', '7', 'alt'), ('alt+8', '8', 'alt'), ('alt+9', '9', 'alt'),
        ('alt+4', '4', 'alt'), ('alt+5', '5', 'alt'), ('alt+6', '6', 'alt'),
        ('alt+1', '1', 'alt'), ('alt+2', '2', 'alt'), ('alt+3', '3', 'alt'),
        ('alt+0', '0', 'alt'), ('alt+.', '.', 'alt')
    ]
    
    # Get all audio files and sort them
    audio_files = [f for f in os.listdir(AUDIO_FOLDER) if f.endswith(('.mp3', '.wav', '.ogg'))]
    audio_files.sort()    # Map files to hotkeys
    total_hotkeys = len(numpad_keys)
    
    for i, filename in enumerate(audio_files):
        if i >= total_hotkeys:
            break
            
        filepath = os.path.join(AUDIO_FOLDER, filename)
        sound = pygame.mixer.Sound(filepath)
        hotkey_data = numpad_keys[i]
        
        sounds[filename] = {
            'sound': sound,
            'hotkey': hotkey_data[0],
            'symbol': hotkey_data[1],
            'modifier': hotkey_data[2],
            'order': i,
            'name': filename.split('.')[0]
        }

def play_sound(filename):
    """Play a sound file using pygame mixer"""
    if filename in sounds:
        sounds[filename]['sound'].play()

def setup_hotkeys():
    """Setup keyboard hotkeys for each sound"""
    for filename, data in sounds.items():
        if data['hotkey']:
            keyboard.add_hotkey(data['hotkey'], play_sound, args=(filename,))

def start_keyboard_listener():
    """Start the keyboard listener in a separate thread"""
    keyboard_thread = threading.Thread(target=keyboard.wait)
    keyboard_thread.daemon = True
    keyboard_thread.start()

@app.route('/')
def index():
    # Get list of audio files with their hotkeys and symbols, sorted by numpad order
    audio_files = [{
        'filename': filename,
        'hotkey': data['hotkey'],
        'symbol': data['symbol'],
        'modifier': data['modifier'],
        'name': data['name']
    } for filename, data in sorted(sounds.items(), key=lambda x: x[1]['order'])]
    return render_template('index.html', audio_files=audio_files)

@app.route('/audio/<path:filename>')
def serve_audio(filename):
    return send_from_directory(AUDIO_FOLDER, filename)

@app.route('/play/<path:filename>')
def play_audio(filename):
    play_sound(filename)
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    print("\n=== Virtual Soundboard ===")
    print("Loading sounds and setting up hotkeys...")
    load_sounds()
    setup_hotkeys()
    start_keyboard_listener()
    
    # Group sounds by modifier for clearer display
    ctrl_sounds = []
    alt_sounds = []
    for filename, data in sorted(sounds.items(), key=lambda x: x[1]['order']):
        if data['modifier'] == 'ctrl':
            ctrl_sounds.append(f"{data['name']}: Ctrl + {data['symbol']}")
        else:
            alt_sounds.append(f"{data['name']}: Alt + {data['symbol']}")
    
    print("\nCtrl Key Mappings:")
    for mapping in ctrl_sounds:
        print(mapping)
    
    print("\nAlt Key Mappings:")
    for mapping in alt_sounds:
        print(mapping)
    
    print("\nAccess the web interface at http://localhost:5000")
    print("Use Ctrl or Alt with number keys to play different sounds")
    print("The soundboard will respond to hotkeys even when the browser is not focused")
    print("=" * 25)
    app.run(host='0.0.0.0', port=5000, debug=False)
