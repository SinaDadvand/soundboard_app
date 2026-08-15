"""
Virtual Soundboard - Web Server & Main Backend
==============================================
Flask server providing REST APIs and modern UI for:
- Sound playback with Volume, Pitch Shift, and Playback Speed FX
- Dual audio output routing (Speakers + Virtual Audio Cable for OBS/Discord)
- 3-Column Numpad Layout (Ctrl, Alt, Ctrl+Alt groups)
- Global Volume Rotary Knob, Panic Stop (Esc), and Sound Upload
"""

import sys
import os
import time
from flask import Flask, render_template, send_from_directory, jsonify, request, make_response
from werkzeug.utils import secure_filename

from audio_engine import AudioEngine
from config_manager import ConfigManager
from hotkey_manager import HotkeyManager

app = Flask(__name__)

app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max upload

# ── Dynamic Path Resolution (Works in normal Python & Frozen PyInstaller .exe) ──
if getattr(sys, 'frozen', False):
    EXE_DIR = os.path.dirname(sys.executable)
    BUNDLE_DIR = getattr(sys, '_MEIPASS', EXE_DIR)
    
    # Locate audio directory (in exe dir, parent dir, or bundle)
    audio_candidates = [
        os.path.join(EXE_DIR, 'static', 'audio'),
        os.path.join(os.path.dirname(EXE_DIR), 'static', 'audio'),
        os.path.join(BUNDLE_DIR, 'static', 'audio')
    ]
    AUDIO_FOLDER = next((p for p in audio_candidates if os.path.exists(p) and len(os.listdir(p)) > 0), audio_candidates[0])

    # Locate config JSON
    config_candidates = [
        os.path.join(EXE_DIR, 'soundboard_config.json'),
        os.path.join(os.path.dirname(EXE_DIR), 'soundboard_config.json'),
        os.path.join(BUNDLE_DIR, 'soundboard_config.json')
    ]
    CONFIG_PATH = next((p for p in config_candidates if os.path.exists(p)), os.path.join(EXE_DIR, 'soundboard_config.json'))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    AUDIO_FOLDER = os.path.join(BASE_DIR, 'static', 'audio')
    CONFIG_PATH = os.path.join(BASE_DIR, 'soundboard_config.json')

os.makedirs(AUDIO_FOLDER, exist_ok=True)
print(f"[Soundboard] Using Audio Folder: {AUDIO_FOLDER}")
print(f"[Soundboard] Using Config File: {CONFIG_PATH}")

# Initialize Core Services
audio_engine = AudioEngine(AUDIO_FOLDER)
config_manager = ConfigManager(config_path=CONFIG_PATH, audio_dir=AUDIO_FOLDER)
hotkey_manager = HotkeyManager(audio_engine, config_manager)

# Apply stored settings to engine
audio_engine.master_volume = config_manager.config.get('master_volume', 1.0)
audio_engine.set_devices(
    primary=config_manager.config.get('primary_device'),
    secondary=config_manager.config.get('secondary_device'),
    secondary_enabled=config_manager.config.get('secondary_enabled', False)
)


@app.after_request
def after_request(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


# ─────────────────────────────────────────────────────────────────────────────
# Core Pages
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    timestamp = str(int(time.time()))
    return render_template(
        'index.html',
        config=config_manager.config,
        timestamp=timestamp
    )


@app.route('/audio/<path:filename>')
def serve_audio(filename):
    return send_from_directory(AUDIO_FOLDER, filename)


# ─────────────────────────────────────────────────────────────────────────────
# REST API Endpoints
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/api/status', methods=['GET'])
def api_status():
    return jsonify({
        'status': 'ok',
        'master_volume': audio_engine.master_volume,
        'panic_key': config_manager.config.get('panic_key', 'esc'),
        'headset_enabled': audio_engine.headset_enabled,
        'cable_enabled': audio_engine.cable_enabled,
        'active_streams': len(audio_engine.active_streams),
        'sound_count': len(config_manager.config.get('sounds', []))
    })


@app.route('/api/routing_toggle', methods=['POST'])
def api_routing_toggle():
    data = request.get_json() or {}
    headset = data.get('headset_enabled', True)
    cable = data.get('cable_enabled', True)
    audio_engine.set_toggles(headset, cable)
    return jsonify({
        'status': 'success',
        'headset_enabled': audio_engine.headset_enabled,
        'cable_enabled': audio_engine.cable_enabled
    })


@app.route('/api/devices', methods=['GET'])
def api_get_devices():
    devices = audio_engine.list_output_devices()
    return jsonify({
        'devices': devices,
        'current_primary': audio_engine.primary_device_name,
        'current_secondary': audio_engine.secondary_device_name,
        'secondary_enabled': audio_engine.cable_enabled,
        'headset_enabled': audio_engine.headset_enabled,
        'cable_enabled': audio_engine.cable_enabled
    })


@app.route('/api/devices', methods=['POST'])
def api_set_devices():
    data = request.get_json() or {}
    primary = data.get('primary_device')
    secondary = data.get('secondary_device')
    secondary_enabled = bool(data.get('secondary_enabled', True))

    audio_engine.set_devices(primary, secondary, secondary_enabled)
    config_manager.config['primary_device'] = primary
    config_manager.config['secondary_device'] = secondary
    config_manager.config['secondary_enabled'] = secondary_enabled
    config_manager.save_config()

    return jsonify({
        'status': 'success',
        'primary_device': primary,
        'secondary_device': secondary,
        'secondary_enabled': secondary_enabled
    })


@app.route('/api/sounds', methods=['GET'])
def api_get_sounds():
    return jsonify({
        'sounds': config_manager.config.get('sounds', []),
        'master_volume': audio_engine.master_volume,
        'panic_key': config_manager.config.get('panic_key', 'esc')
    })


@app.route('/api/sounds/upload', methods=['POST'])
def api_upload_sound():
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'Empty filename'}), 400

    filename = secure_filename(file.filename)
    name = request.form.get('name') or os.path.splitext(filename)[0]
    hotkey = request.form.get('hotkey') or None

    valid_exts = ('.mp3', '.wav', '.ogg', '.flac')
    if not any(filename.lower().endswith(ext) for ext in valid_exts):
        return jsonify({'status': 'error', 'message': 'Supported formats: MP3, WAV, OGG, FLAC'}), 400

    save_path = os.path.join(AUDIO_FOLDER, filename)
    counter = 1
    base_name, ext = os.path.splitext(filename)
    while os.path.exists(save_path):
        filename = f"{base_name}_{counter}{ext}"
        save_path = os.path.join(AUDIO_FOLDER, filename)
        counter += 1

    file.save(save_path)

    new_entry = config_manager.add_sound(
        filename=filename,
        name=name,
        hotkey=hotkey,
        volume=1.0,
        speed=1.0,
        pitch=0.0
    )

    hotkey_manager.reload_all_hotkeys()
    return jsonify({'status': 'success', 'sound': new_entry})


@app.route('/api/sounds/<sound_id>/edit', methods=['POST'])
def api_edit_sound(sound_id):
    data = request.get_json() or {}
    sound = config_manager.get_sound_by_id(sound_id)
    if not sound:
        return jsonify({'status': 'error', 'message': 'Sound not found'}), 404

    updates = {}
    if 'name' in data:
        updates['name'] = data['name']
    if 'volume' in data:
        updates['volume'] = max(0.0, min(2.0, float(data['volume'])))
    if 'speed' in data:
        updates['speed'] = max(0.25, min(3.0, float(data['speed'])))
    if 'pitch' in data:
        updates['pitch'] = max(-12.0, min(12.0, float(data['pitch'])))

    updated = config_manager.update_sound(sound_id, updates)

    if 'hotkey' in data:
        hotkey_manager.rebind_sound_hotkey(sound_id, data['hotkey'])

    return jsonify({'status': 'success', 'sound': updated})


@app.route('/api/sounds/<sound_id>/rebind', methods=['POST'])
def api_rebind_sound(sound_id):
    data = request.get_json() or {}
    new_hotkey = data.get('hotkey')
    success, msg = hotkey_manager.rebind_sound_hotkey(sound_id, new_hotkey)
    if success:
        return jsonify({'status': 'success', 'message': msg})
    return jsonify({'status': 'error', 'message': msg}), 400


@app.route('/api/sounds/<sound_id>', methods=['DELETE'])
def api_delete_sound(sound_id):
    success = config_manager.delete_sound(sound_id, delete_file=True)
    if success:
        hotkey_manager.reload_all_hotkeys()
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error', 'message': 'Could not delete sound'}), 400


@app.route('/api/play/<sound_id>', methods=['POST', 'GET'])
def api_play_sound(sound_id):
    sound = config_manager.get_sound_by_id(sound_id)
    if not sound:
        for s in config_manager.config.get('sounds', []):
            if s['filename'] == sound_id:
                sound = s
                break

    if not sound:
        return jsonify({'status': 'error', 'message': 'Sound not found'}), 404

    filepath = os.path.join(AUDIO_FOLDER, sound['filename'])

    # Optional FX overrides from browser play
    data = request.get_json() if request.is_json else request.args
    volume = float(data.get('volume', sound.get('volume', 1.0)))
    speed = float(data.get('speed', sound.get('speed', 1.0)))
    pitch = float(data.get('pitch', sound.get('pitch', 0.0)))

    success = audio_engine.play(
        filepath,
        volume=volume,
        speed=speed,
        pitch_semitones=pitch,
        sound_id=sound['id']
    )

    if success:
        return jsonify({
            'status': 'success',
            'sound_id': sound['id'],
            'name': sound['name'],
            'volume': volume,
            'speed': speed,
            'pitch': pitch
        })
    return jsonify({'status': 'error', 'message': 'Playback failed'}), 500


@app.route('/api/stop', methods=['POST', 'GET'])
def api_stop_all():
    audio_engine.stop_all()
    return jsonify({'status': 'success', 'message': 'Stopped all playback'})


@app.route('/api/sounds/<sound_id>/stop', methods=['POST'])
def api_stop_sound(sound_id):
    audio_engine.stop_sound(sound_id)
    return jsonify({'status': 'success'})


@app.route('/api/master_volume', methods=['POST'])
def api_set_master_volume():
    data = request.get_json() or {}
    vol = float(data.get('volume', 1.0))
    vol = max(0.0, min(1.0, vol))
    audio_engine.master_volume = vol
    config_manager.config['master_volume'] = vol
    config_manager.save_config()
    return jsonify({'status': 'success', 'master_volume': vol})


@app.route('/api/panic_key', methods=['POST'])
def api_set_panic_key():
    data = request.get_json() or {}
    key = data.get('panic_key', 'esc')
    hotkey_manager.update_panic_key(key)
    return jsonify({'status': 'success', 'panic_key': config_manager.config.get('panic_key')})


def initialize_app():
    """Load config, preload audio files, register hotkeys and start keyboard listener."""
    print("\n" + "="*50)
    print("🎵  VIRTUAL SOUNDBOARD 2.1 INITIALIZING...")
    print("="*50)
    config_manager.sync_audio_files(config_manager.config)
    audio_engine.preload_directory()
    hotkey_manager.reload_all_hotkeys()
    hotkey_manager.start_listener()
    print(f"Loaded {len(config_manager.config.get('sounds', []))} sounds into 3 Numpad Groups.")
    print(f"Panic Key: [{config_manager.config.get('panic_key', 'esc').upper()}]")
    print("="*50 + "\n")


if __name__ == '__main__':
    initialize_app()
    app.run(host='0.0.0.0', port=5001, debug=False)
