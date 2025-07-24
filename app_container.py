from flask import Flask, render_template, send_from_directory, jsonify, request
import os

app = Flask(__name__)

# Configuration
AUDIO_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'audio')
os.makedirs(AUDIO_FOLDER, exist_ok=True)

# Dictionary to store sound information without pygame dependency
sounds = {}

def load_sounds():
    """Load all sound files and assign default hotkeys in numpad order"""
    # Define key order with symbols for Ctrl, Alt, and Ctrl+Alt combinations
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
        ('alt+0', '0', 'alt'), ('alt+.', '.', 'alt'),
        # Third set with Ctrl+Alt
        ('ctrl+alt+7', '7', 'ctrl+alt'), ('ctrl+alt+8', '8', 'ctrl+alt'), ('ctrl+alt+9', '9', 'ctrl+alt'),
        ('ctrl+alt+4', '4', 'ctrl+alt'), ('ctrl+alt+5', '5', 'ctrl+alt'), ('ctrl+alt+6', '6', 'ctrl+alt'),
        ('ctrl+alt+1', '1', 'ctrl+alt'), ('ctrl+alt+2', '2', 'ctrl+alt'), ('ctrl+alt+3', '3', 'ctrl+alt'),
        ('ctrl+alt+0', '0', 'ctrl+alt'), ('ctrl+alt+.', '.', 'ctrl+alt')
    ]
    
    # Get all audio files and sort them
    audio_files = [f for f in os.listdir(AUDIO_FOLDER) if f.endswith(('.mp3', '.wav', '.ogg'))]
    audio_files.sort()
    
    # Map files to hotkeys
    total_hotkeys = len(numpad_keys)
    
    for i, filename in enumerate(audio_files):
        if i >= total_hotkeys:
            break
            
        filepath = os.path.join(AUDIO_FOLDER, filename)
        hotkey_data = numpad_keys[i]
        
        sounds[filename] = {
            'filepath': filepath,
            'hotkey': hotkey_data[0],
            'symbol': hotkey_data[1],
            'modifier': hotkey_data[2],
            'order': i,
            'name': filename.split('.')[0]
        }

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
    return render_template('index_container.html', audio_files=audio_files)

@app.route('/audio/<path:filename>')
def serve_audio(filename):
    return send_from_directory(AUDIO_FOLDER, filename)

@app.route('/play/<path:filename>')
def play_audio(filename):
    # For container version, we just return success - audio will be played by browser
    if filename in sounds:
        return jsonify({'status': 'success', 'audio_url': f'/audio/{filename}'})
    return jsonify({'status': 'error', 'message': 'Sound not found'})

@app.route('/api/sounds')
def get_sounds():
    """API endpoint to get all sounds data"""
    audio_files = [{
        'filename': filename,
        'hotkey': data['hotkey'],
        'symbol': data['symbol'],
        'modifier': data['modifier'],
        'name': data['name'],
        'audio_url': f'/audio/{filename}'
    } for filename, data in sorted(sounds.items(), key=lambda x: x[1]['order'])]
    return jsonify(audio_files)

@app.route('/api/play', methods=['POST'])
def api_play_sound():
    """API endpoint for hotkey client to trigger sound playback"""
    try:
        data = request.get_json()
        sound_name = data.get('sound', '')
        force_play = data.get('force', False)
        
        if sound_name in sounds:
            return jsonify({
                'status': 'success', 
                'audio_url': f'/audio/{sound_name}',
                'sound': sound_name,
                'force': force_play
            })
        else:
            return jsonify({'status': 'error', 'message': 'Sound not found'}), 404
            
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/activate', methods=['POST'])
def api_activate():
    """API endpoint to signal browser activation"""
    try:
        data = request.get_json()
        action = data.get('action', 'focus')
        
        return jsonify({
            'status': 'success',
            'action': action,
            'message': 'Activation signal received'
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    print("\n=== Virtual Soundboard (Container Version) ===")
    print("Loading sounds...")
    load_sounds()
    
    # Group sounds by modifier for clearer display
    ctrl_sounds = []
    alt_sounds = []
    ctrl_alt_sounds = []
    for filename, data in sorted(sounds.items(), key=lambda x: x[1]['order']):
        if data['modifier'] == 'ctrl':
            ctrl_sounds.append(f"{data['name']}: Ctrl + {data['symbol']}")
        elif data['modifier'] == 'alt':
            alt_sounds.append(f"{data['name']}: Alt + {data['symbol']}")
        else:  # ctrl+alt
            ctrl_alt_sounds.append(f"{data['name']}: Ctrl + Alt + {data['symbol']}")
    
    print(f"\nLoaded {len(sounds)} sounds:")
    print(f"- Ctrl combinations: {len(ctrl_sounds)}")
    print(f"- Alt combinations: {len(alt_sounds)}")
    print(f"- Ctrl+Alt combinations: {len(ctrl_alt_sounds)}")
    
    print("\nAccess the web interface at http://localhost:5000")
    print("Note: In container mode, hotkeys work only when the browser tab is focused")
    print("Click on sound buttons to play audio through the web interface")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=False)
