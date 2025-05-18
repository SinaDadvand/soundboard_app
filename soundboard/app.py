from flask import Flask, render_template, send_from_directory
import os

app = Flask(__name__)

# Configuration
AUDIO_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'audio')
os.makedirs(AUDIO_FOLDER, exist_ok=True)

@app.route('/')
def index():
    # Get list of audio files
    audio_files = []
    for filename in os.listdir(AUDIO_FOLDER):
        if filename.endswith(('.mp3', '.wav', '.ogg')):
            audio_files.append(filename)
    return render_template('index.html', audio_files=audio_files)

@app.route('/audio/<path:filename>')
def serve_audio(filename):
    return send_from_directory(AUDIO_FOLDER, filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
