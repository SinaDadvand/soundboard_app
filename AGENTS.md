# Virtual Soundboard Pro — Agent & AI Developer Guide (`AGENTS.md`)

This document provides a comprehensive technical overview and architecture reference for **Antigravity**, **Cursor**, **Copilot**, or any AI coding assistant / engineer working on this codebase.

---

## 1. Project Overview & Operational Modes

**Virtual Soundboard Pro** is a dual-mode low-latency soundboard with real-time DSP audio processing, Discord voice streaming, Firebase authentication, and global physical numpad hotkeys.

### Dual Operating Modes:
1. **☁️ Cloud Run Mode (Web + In-Game Companion)**:
   - Hosted on Google Cloud Run with Firebase Auth (Google Sign-In) and an environment-variable email allowlist (`ALLOWED_USERS`).
   - Streams audio directly into Discord voice channels.
   - Includes in-browser HTML5 Web Audio playback when **🎧 Headset** is toggled ON (offline by default to prevent Discord duplicate echo).
   - Real-time Server-Sent Events (`/api/events`) sync web UI animations and local playback with remote triggers.
   - Desktop **Cloud Hotkey Companion** hooks OS-level keyboard events and sends authenticated async HTTP triggers (`X-Companion-Key`) to Cloud Run from fullscreen games.
2. **🏠 Local Mode (Standalone Native DSP Engine)**:
   - Runs locally on `http://127.0.0.1:5001`.
   - Directly routes audio to physical headphones/speakers and VB-Audio Virtual Cable (for OBS / Discord desktop mic input).

---

## 2. Directory Structure & Key Files

```text
soundboard_app/
├── app.py                      # Core Flask web server & Cloud Run entrypoint
├── launcher.py                 # Desktop Tkinter GUI & Global Hotkey Relay Companion
├── build-executable.bat        # 1-Click PyInstaller compiler for Windows
├── Dockerfile                  # Production Debian-based container definition
├── requirements.txt            # Python dependencies (pinned versions)
├── soundboard_config.json      # Audio clip metadata, volume/FX overrides, hotkeys
├── VirtualSoundboard2.spec     # PyInstaller spec for standalone executable
├── README.md                   # Human-facing documentation with architecture diagrams
├── AGENTS.md                   # AI / Agent reference guide (this file)
├── .dockerignore               # Container build exclusion rules
├── .gitignore                  # Git repository exclusion rules
│
├── src/                        # Core backend Python modules
│   ├── __init__.py
│   ├── audio_engine.py         # DSP processing (Pitch, Speed, Echo, Reverb), PortAudio/WASAPI
│   ├── auth_service.py         # Firebase Admin token verification & email allowlist RBAC
│   ├── config_manager.py       # Configuration loading, sync, and sound definitions
│   ├── discord_service.py      # Discord voice bot & streaming gateway via discord.py
│   └── hotkey_manager.py       # Local OS keyboard listener via 'keyboard'
│
├── tests/                      # Automated test suites (16 test suites, 100% pass)
│   ├── __init__.py
│   ├── test_audio_engine.py    # DSP transformations & device query tests
│   ├── test_e2e_api.py         # End-to-end Flask REST API, auth & companion tests
│   └── test_managers.py        # ConfigManager & HotkeyManager tests
│
├── docs/                       # Architecture & setup guides
│   ├── CLOUD_RUN_DEPLOYMENT.md # Terraform + Cloud Build GCP deployment guide
│   └── DISCORD_SETUP.md        # Discord Developer Portal Bot configuration guide
│
├── scripts/                    # Helper utilities
│   ├── cloudbuild.yaml         # Cloud Build trigger configuration
│   ├── create-desktop-shortcut.ps1
│   ├── deploy-artifact-registry.ps1
│   ├── launch-v2.bat
│   └── start-soundboard.bat
│
├── assets/                     # Branding & icons
│   ├── app_icon.ico
│   └── app_icon.png
│
├── static/                     # Web assets
│   ├── audio/                  # Audio clips (.mp3, .wav)
│   ├── css/                    # Dark neon responsive stylesheets
│   ├── js/                     # Frontend state, Web Audio engine, SSE client
│   ├── favicon.ico             # Multi-resolution raster favicon (16/32/48/64/128/256px)
│   ├── favicon.png             # 512x512 PNG favicon
│   └── favicon.svg             # Vector soundboard chevron icon
│
└── templates/                  # Frontend templates
    └── index.html              # Main HTML5 soundboard interface
```

---

## 3. Subsystem Deep-Dive

### A. Web Server (`app.py`)
- **Framework**: Flask (Gunicorn with 1 worker + 8 threads in production).
- **Key Endpoints**:
  - `GET /`: Serves `index.html`.
  - `GET /api/sounds`: Returns list of 33 sounds with IDs, names, hotkeys, audio URLs, and FX parameters.
  - `POST /api/play/<id>`: Triggers audio playback (local DSP engine in local mode; Discord bot streaming + SSE broadcast in Cloud Run). Accepts parameter overrides (`volume`, `pitch`, `speed`, `echo`, `reverb`).
  - `POST /api/panic` or `POST /api/stop`: Immediately terminates all active audio playback across hardware, Discord, and connected browsers.
  - `GET /api/events`: Server-Sent Events (SSE) stream broadcasting `{type: 'play_sound', id: ...}` and `{type: 'stop_all'}` to synchronize web tabs with remote hotkey triggers.
  - `GET /api/auth/me`: Validates Firebase token and returns user profile.

### B. DSP Audio Engine (`src/audio_engine.py`)
- **Technologies**: `numpy`, `scipy.signal`, `sounddevice`, `soundfile`.
- **Effects Chain**:
  1. **Volume Scaling**: Gain multiplier `[0.0, 2.0]`.
  2. **Pitch Shifting**: Resampling + linear interpolation over `[-12.0, +12.0]` semitones.
  3. **Speed Modification**: Sinc/linear rate resampling over `[0.5x, 2.0x]`.
  4. **Multi-Tap Delay / Echo**: Feedback attenuation loop `[0.0, 1.0]`.
  5. **Schroeder-Style Algorithmic Reverb**: Multi-comb + all-pass diffusion filters `[0.0, 1.0]`.
- **Output Routing**: Uses PortAudio / WASAPI native 2-channel audio streams for direct hardware playback and VB-Audio Virtual Cable.

### C. Authentication & Access Control (`src/auth_service.py`)
- **Firebase Authentication**: Decodes Bearer ID tokens via `firebase_admin.auth.verify_id_token`.
- **Email Allowlist (RBAC)**: Checks authenticated user email against `ALLOWED_USERS` environment variable (comma-separated list, lowercased).
- **Companion Key Bypass**: `X-Companion-Key: soundboard-companion-key-2026` allows authenticated requests from the desktop background launcher without interactive browser prompts.

### D. Desktop Launcher GUI & Hotkey Relay (`launcher.py`)
- **GUI Framework**: Python `tkinter` with a dark neon interface (`#0b0d13`).
- **Environment Switcher**:
  - **ADT (Non-Prod / Dev)**: `https://soundboard-app-fb-adt-454499904362.us-west1.run.app`
  - **SPT (Staging)**: `https://soundboard-app-spt-454499904362.us-west1.run.app`
  - **PRD (Production)**: `https://soundboard-app-prd-454499904362.us-west1.run.app`
  - **Custom URL**: Direct endpoint input.
- **Global Hotkey Companion**: Worker thread using `keyboard.add_hotkey()` that translates physical numpad keystrokes into async HTTP `POST /api/play/<id>` and `POST /api/panic` calls.

---

## 4. Critical Invariants & Rules

1. **Default Knob & Volume Settings**:
   - Every build, test run, and config sync **MUST** maintain Master Volume at **90% (`0.9`)** and all FX knobs in normal reset position (`pitch: 0.0`, `speed: 1.0`, `echo: 0.0`, `reverb: 0.0`).
2. **Headphone Button Default**:
   - In Cloud Run mode, `#toggle-headset-btn` **MUST start OFF / Offline by default** in both HTML and JavaScript to avoid duplicate audio echo when connected to Discord voice.
3. **Favicon & Static Caching**:
   - Favicons are served with `Cache-Control: public, max-age=604800` so Firefox and Chromium persist the bookmark icon in `places.sqlite`. Other dynamic endpoints maintain `no-store`.
4. **PyInstaller Binary Locking**:
   - On Windows, if `dist/VirtualSoundboard2.exe` is currently running, PyInstaller will throw `PermissionError: [WinError 5] Access is denied`. Always terminate running instances before rebuilding (`taskkill /F /IM VirtualSoundboard2.exe`).

---

## 5. Development & Test Commands

```powershell
# 1. Run all unit & E2E tests
python -m unittest discover -s tests

# 2. Run individual test suites
python tests/test_audio_engine.py
python tests/test_e2e_api.py
python tests/test_managers.py

# 3. Build standalone Windows executable (.exe)
.\build-executable.bat
# or:
python -m PyInstaller VirtualSoundboard2.spec --clean --noconfirm

# 4. Start web server locally
python app.py

# 5. Start desktop launcher GUI locally
python launcher.py
```
