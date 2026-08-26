# Virtual Soundboard 2

A high-performance standalone soundboard and web interface with real-time DSP effects, dual audio routing (Headset + OBS/Discord Virtual Cable), and physical 3-tier Numpad key binding.

---

## Features
* **Physical 3-Tier Numpad Layout**: 33 audio clips sorted A–Z across `Ctrl`, `Alt`, and `Ctrl+Alt` modifiers matching standard physical numpad key positions (`7, 8, 9, 4, 5, 6, 1, 2, 3, 0, .`).
* **5-Knob Real-Time DSP Cluster**:
  * Master Volume (Gold)
  * Global Pitch Shift (-12 to +12 semitones, Cyan)
  * Global Playback Speed (0.5x to 2.0x, Pink)
  * Multi-Tap Echo (0% to 100%, Amber)
  * Algorithmic Room Reverb (0% to 100%, Purple)
* **Dual Output Routing**: Independent toggles for Headset and VB-Audio Virtual Cable (WASAPI native 2-channel stream for OBS / Discord).
* **Upload & Replace**: Upload new audio files directly to hotkey slots.
* **Panic Stop**: Instantly stop all audio with `Esc` or custom hotkey.

---

## Running the Application

### Option 1: Standalone Executable (Recommended)
Double-click `dist\VirtualSoundboard2.exe` or `scripts\launch-v2.bat`.

To create a desktop shortcut, run:
```powershell
powershell -ExecutionPolicy Bypass -File scripts\create-desktop-shortcut.ps1
```

### Option 2: Python Development Mode
```powershell
python -m venv venv
.\venv\Scripts\Activate
pip install -r requirements.txt
python launcher.py
```

---

## Building Standalone Executable
Double-click `build-executable.bat` or run:
```powershell
python -m PyInstaller VirtualSoundboard2.spec --clean --noconfirm
```

---

## Project Structure
```text
soundboard_app/
├── app.py                  # Web server & Cloud Run entrypoint
├── launcher.py             # Desktop GUI launcher & hotkey companion
├── build-executable.bat    # 1-Click desktop executable builder
├── Dockerfile              # Production container definition
├── requirements.txt        # Dependencies
├── soundboard_config.json  # Audio sound mappings & defaults
├── VirtualSoundboard2.spec # PyInstaller build spec
├── src/                    # Backend modules (audio_engine, auth, config, discord, hotkeys)
├── tests/                  # Unit and E2E automated test suites
├── docs/                   # Deployment & setup documentation
├── scripts/                # Deployment and launch utility scripts
├── assets/                 # App icons
├── static/                 # Audio files, CSS, JavaScript, favicons
└── templates/              # HTML frontend
```
