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
    """Load all sound files and assign default hotkeys"""
    hotkey_base = ['f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f11', 'f12']
    for filename in os.listdir(AUDIO_FOLDER):
        if filename.endswith(('.mp3', '.wav', '.ogg')):
            filepath = os.path.join(AUDIO_FOLDER, filename)
            sound = pygame.mixer.Sound(filepath)
            # Assign a hotkey if we haven't run out of default hotkeys
            hotkey = hotkey_base.pop(0) if hotkey_base else None
            sounds[filename] = {
                'sound': sound,
                'hotkey': hotkey
            }

def play_sound(filename):
    """Play a sound file using pygame mixer"""
    if filename in sounds:
        sounds[filename]['sound'].play()

def setup_hotkeys():
    """Setup keyboard hotkeys for each sound"""
    for filename, data in sounds.items():
        if data['hotkey']:
            keyboard.on_press_key(data['hotkey'], 
                                lambda e, f=filename: play_sound(f))

def start_keyboard_listener():
    """Start the keyboard listener in a separate thread"""
    keyboard_thread = threading.Thread(target=keyboard.wait)
    keyboard_thread.daemon = True
    keyboard_thread.start()

@app.route('/')
def index():
    # Get list of audio files with their hotkeys
    audio_files = [{
        'filename': filename,
        'hotkey': data['hotkey']
    } for filename, data in sounds.items()]
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
    print("\nHotkey mappings:")
    for filename, data in sounds.items():
        if data['hotkey']:
            print(f"{filename}: {data['hotkey']}")
    print("\nAccess the web interface at http://localhost:5000")
    print("The soundboard will respond to hotkeys even when the browser is not focused")
    print("=" * 25)
    app.run(host='0.0.0.0', port=5000, debug=False)
