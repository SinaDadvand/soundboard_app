"""
Virtual Soundboard Launcher - Pro Edition 2.4 (Multi-User Cloud Run)
====================================================================
Modern Tkinter desktop companion for Windows that supports:
  1. Cloud Run Mode:
     - Select GCP Environment (ADT, SPT, PRD)
     - Select Per-User Cloud Run Service (Sina, Cesar, Shared Base, or Custom)
     - Launches Cloud Run web dashboard in default browser
     - Runs background Windows Global Hotkey Companion to stream triggers directly
       from fullscreen games (Numpad hotkeys + ESC panic stop)
  2. Local Mode:
     - Runs local Flask server & hooks local audio hardware
"""

import sys
import os
import threading
import webbrowser
import socket
import json
import urllib.request
import urllib.error
import tkinter as tk
import tkinter.messagebox as msgbox

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except (ImportError, OSError, Exception) as e:
    keyboard = None
    KEYBOARD_AVAILABLE = False

# ─────────────────────────────────────────────────────────────────────────────
# Path & Environment Resolution
# ─────────────────────────────────────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    _BUNDLE = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    _EXE_DIR = os.path.dirname(sys.executable)
else:
    _BUNDLE = os.path.dirname(os.path.abspath(__file__))
    _EXE_DIR = _BUNDLE

audio_candidates = [
    os.path.join(_EXE_DIR, 'static', 'audio'),
    os.path.join(os.path.dirname(_EXE_DIR), 'static', 'audio'),
    os.path.join(_BUNDLE, 'static', 'audio')
]
AUDIO_FOLDER = next((p for p in audio_candidates if os.path.exists(p) and len(os.listdir(p)) > 0), audio_candidates[0])
LOCAL_SERVER_URL = 'http://127.0.0.1:5001'
COMPANION_API_KEY = os.environ.get('COMPANION_API_KEY', 'soundboard-companion-key-2026')
SETTINGS_FILE = os.path.join(_EXE_DIR, 'launcher_settings.json')

ENVIRONMENTS = {
    'ADT': {
        'name': 'ADT (Non-Prod / Dev)',
        'badge': 'DEV',
        'default_service': 'sina',
        'services': {
            'sina': {
                'label': '👤 Sina',
                'description': 'Sina Personal Cloud Run',
                'url': 'https://soundboard-user-sina-adt-454499904362.us-west1.run.app'
            },
            'cesar': {
                'label': '👤 Cesar',
                'description': 'Cesar Personal Cloud Run',
                'url': 'https://soundboard-user-cesar-adt-454499904362.us-west1.run.app'
            },
            'shared': {
                'label': '🌐 Shared Base',
                'description': 'Shared Base App (ADT)',
                'url': 'https://soundboard-app-fb-adt-454499904362.us-west1.run.app'
            }
        }
    },
    'SPT': {
        'name': 'SPT (Staging)',
        'badge': 'STAGE',
        'default_service': 'sina',
        'services': {
            'sina': {
                'label': '👤 Sina',
                'description': 'Sina Staging Cloud Run',
                'url': 'https://soundboard-user-sina-spt-454499904362.us-west1.run.app'
            },
            'cesar': {
                'label': '👤 Cesar',
                'description': 'Cesar Staging Cloud Run',
                'url': 'https://soundboard-user-cesar-spt-454499904362.us-west1.run.app'
            },
            'shared': {
                'label': '🌐 Shared Base',
                'description': 'Shared Base App (SPT)',
                'url': 'https://soundboard-app-fb-spt-454499904362.us-west1.run.app'
            }
        }
    },
    'PRD': {
        'name': 'PRD (Production)',
        'badge': 'PROD',
        'default_service': 'sina',
        'services': {
            'sina': {
                'label': '👤 Sina',
                'description': 'Sina Production Cloud Run',
                'url': 'https://soundboard-user-sina-prd-454499904362.us-west1.run.app'
            },
            'cesar': {
                'label': '👤 Cesar',
                'description': 'Cesar Production Cloud Run',
                'url': 'https://soundboard-user-cesar-prd-454499904362.us-west1.run.app'
            },
            'shared': {
                'label': '🌐 Shared Base',
                'description': 'Shared Base App (PRD)',
                'url': 'https://soundboard-app-prd-454499904362.us-west1.run.app'
            }
        }
    }
}

os.makedirs(AUDIO_FOLDER, exist_ok=True)


def _load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_settings(settings):
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Local Flask Server Thread
# ─────────────────────────────────────────────────────────────────────────────
def _run_local_server():
    """Import app.py and run the Flask server in a daemon thread."""
    if _BUNDLE not in sys.path:
        sys.path.insert(0, _BUNDLE)

    try:
        import app as sb
        sb.initialize_app()
    except Exception as exc:
        print(f"[Launcher] Could not load local soundboard app: {exc}")
        return

    import logging
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    sb.app.run(host='127.0.0.1', port=5001, debug=False, use_reloader=False)


def _port_open(host='127.0.0.1', port=5001) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.3):
            return True
    except OSError:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Cloud Run Hotkey Relay Companion
# ─────────────────────────────────────────────────────────────────────────────
class CloudHotkeyCompanion:
    """Hooks global Windows hotkeys and sends triggers to remote Cloud Run instance."""

    def __init__(self, target_url: str, on_status_change=None):
        self.target_url = target_url.rstrip('/')
        self.on_status_change = on_status_change
        self.registered_handlers = []
        self.sound_count = 0
        self.is_active = False

    def sync_and_hook(self):
        if not KEYBOARD_AVAILABLE or keyboard is None:
            if self.on_status_change:
                self.on_status_change(False, "Global keyboard hooks unavailable on this system.")
            return False

        try:
            # Clear existing hotkeys
            self.unhook_all()

            # Query Cloud Run for sound list & hotkey mappings
            req = urllib.request.Request(
                f"{self.target_url}/api/sounds",
                headers={'X-Companion-Key': COMPANION_API_KEY, 'User-Agent': 'SoundboardDesktopCompanion/2.4'}
            )

            with urllib.request.urlopen(req, timeout=6) as response:
                data = json.loads(response.read().decode('utf-8'))

            sounds = data.get('sounds', [])
            panic_key = data.get('panic_key', 'esc')
            hooked_count = 0

            # Register Panic Key
            if panic_key:
                try:
                    h = keyboard.add_hotkey(panic_key, self._trigger_panic)
                    self.registered_handlers.append(h)
                except Exception as e:
                    print(f"[Companion] Could not register panic key '{panic_key}': {e}")

            # Register each sound hotkey
            for sound in sounds:
                hk = sound.get('hotkey')
                sid = sound.get('id')
                if hk and sid:
                    try:
                        h = keyboard.add_hotkey(hk, lambda s_id=sid: self._trigger_play(s_id))
                        self.registered_handlers.append(h)
                        hooked_count += 1
                    except Exception as e:
                        print(f"[Companion] Could not hook '{hk}': {e}")

            self.sound_count = hooked_count
            self.is_active = True
            if self.on_status_change:
                self.on_status_change(True, f"Connected · {hooked_count} Global Hotkeys Active ⚡")
            return True

        except Exception as e:
            self.is_active = False
            if self.on_status_change:
                self.on_status_change(False, f"Connection notice: {e}")
            return False

    def unhook_all(self):
        if KEYBOARD_AVAILABLE and keyboard is not None:
            try:
                for h in self.registered_handlers:
                    try:
                        keyboard.remove_hotkey(h)
                    except Exception:
                        pass
                keyboard.clear_all_hotkeys()
            except Exception:
                pass
        self.registered_handlers.clear()
        self.is_active = False

    def _trigger_play(self, sound_id):
        def _post():
            try:
                url = f"{self.target_url}/api/play/{sound_id}"
                req = urllib.request.Request(
                    url,
                    data=b'{}',
                    headers={
                        'Content-Type': 'application/json',
                        'X-Companion-Key': COMPANION_API_KEY,
                        'User-Agent': 'SoundboardDesktopCompanion/2.4'
                    },
                    method='POST'
                )
                with urllib.request.urlopen(req, timeout=4) as resp:
                    pass
            except Exception as exc:
                print(f"[Companion] Play trigger error ({sound_id}): {exc}")

        threading.Thread(target=_post, daemon=True).start()

    def _trigger_panic(self):
        def _post():
            try:
                url = f"{self.target_url}/api/panic"
                req = urllib.request.Request(
                    url,
                    data=b'{}',
                    headers={
                        'Content-Type': 'application/json',
                        'X-Companion-Key': COMPANION_API_KEY,
                        'User-Agent': 'SoundboardDesktopCompanion/2.4'
                    },
                    method='POST'
                )
                with urllib.request.urlopen(req, timeout=3) as resp:
                    pass
            except Exception as exc:
                print(f"[Companion] Panic trigger error: {exc}")

        threading.Thread(target=_post, daemon=True).start()


# ─────────────────────────────────────────────────────────────────────────────
# Modern Dark Desktop GUI
# ─────────────────────────────────────────────────────────────────────────────
class SoundboardLauncher(tk.Tk):
    C_BG = '#0b0d13'
    C_SURFACE = '#121622'
    C_BORDER = '#222a3d'
    C_CYAN = '#06b6d4'
    C_CYAN_HOVER = '#0891b2'
    C_KEYCAP = '#181d2a'
    C_KEYCAP_HOVER = '#22293b'
    C_GREEN = '#10b981'
    C_GOLD = '#d4af37'
    C_TEXT = '#f8fafc'
    C_MUTED = '#94a3b8'

    def __init__(self):
        super().__init__()
        self.title('Virtual Soundboard Pro 2.4')
        self.geometry('500x560')
        self.resizable(False, False)
        self.configure(bg=self.C_BG)
        self.protocol('WM_DELETE_WINDOW', self._quit)

        # Set Window Icon
        icon_candidates = [
            os.path.join(_EXE_DIR, 'app_icon.ico'),
            os.path.join(_BUNDLE, 'app_icon.ico'),
            os.path.join(_EXE_DIR, 'assets', 'app_icon.ico'),
            os.path.join(_BUNDLE, 'assets', 'app_icon.ico'),
            os.path.join(_EXE_DIR, 'static', 'favicon.ico')
        ]
        for icon_path in icon_candidates:
            if os.path.exists(icon_path):
                try:
                    self.iconbitmap(icon_path)
                    break
                except Exception:
                    pass

        # Load saved user settings
        saved = _load_settings()
        init_env = saved.get('selected_env', 'ADT')
        if init_env not in ENVIRONMENTS:
            init_env = 'ADT'
        init_service = saved.get('selected_service', 'sina')
        if init_service not in ENVIRONMENTS[init_env]['services'] and init_service != 'custom':
            init_service = 'sina'

        self.current_mode = tk.StringVar(value='cloud') # 'local' or 'cloud'
        self.selected_env = tk.StringVar(value=init_env)
        self.selected_service = tk.StringVar(value=init_service)
        self.custom_url_var = tk.StringVar(value='')

        self.cloud_companion = None
        self.local_server_started = False

        self._build_ui()
        self._sync_url_and_ui()

    def _build_ui(self):
        container = tk.Frame(self, bg=self.C_SURFACE, highlightbackground=self.C_BORDER, highlightthickness=1)
        container.pack(fill='both', expand=True, padx=14, pady=14)

        # Header Title Bar
        header = tk.Frame(container, bg=self.C_SURFACE)
        header.pack(fill='x', padx=16, pady=(16, 10))

        title_frame = tk.Frame(header, bg=self.C_SURFACE)
        title_frame.pack(side='left')

        tk.Label(title_frame, text='⚡ Soundboard Pro',
                 font=('Segoe UI', 14, 'bold'),
                 fg=self.C_TEXT, bg=self.C_SURFACE).pack(side='left')

        badge = tk.Label(title_frame, text=' V2.4 Cloud ',
                         font=('Segoe UI', 8, 'bold'),
                         fg=self.C_GOLD, bg='#241c09',
                         highlightbackground='#5a440c', highlightthickness=1)
        badge.pack(side='left', padx=(8, 0))

        # Mode Selector (Tabs)
        mode_box = tk.Frame(container, bg='#0e111a', highlightbackground=self.C_BORDER, highlightthickness=1)
        mode_box.pack(fill='x', padx=16, pady=(0, 12))

        mode_row = tk.Frame(mode_box, bg='#0e111a')
        mode_row.pack(fill='x', padx=4, pady=4)

        self._cloud_tab_btn = tk.Button(
            mode_row, text='☁️  Cloud Run Mode',
            command=lambda: self._set_mode('cloud'),
            font=('Segoe UI', 9, 'bold'),
            bg=self.C_CYAN, fg='#ffffff',
            activebackground=self.C_CYAN_HOVER, activeforeground='#ffffff',
            relief='flat', bd=0, pady=6, cursor='hand2'
        )
        self._cloud_tab_btn.pack(side='left', fill='x', expand=True, padx=(0, 2))

        self._local_tab_btn = tk.Button(
            mode_row, text='🏠  Local Server Mode',
            command=lambda: self._set_mode('local'),
            font=('Segoe UI', 9, 'bold'),
            bg='#181d2a', fg=self.C_MUTED,
            activebackground='#22293b', activeforeground=self.C_TEXT,
            relief='flat', bd=0, pady=6, cursor='hand2'
        )
        self._local_tab_btn.pack(side='right', fill='x', expand=True, padx=(2, 0))

        # Cloud Run Config Frame
        self._cloud_frame = tk.Frame(container, bg=self.C_SURFACE)
        self._cloud_frame.pack(fill='x', padx=16, pady=(0, 10))

        # ── Step 1: Environment Selection ──────────────────────────────────────
        tk.Label(self._cloud_frame, text='1. Select Environment:',
                 font=('Segoe UI', 9, 'bold'), fg=self.C_TEXT, bg=self.C_SURFACE).pack(anchor='w', pady=(0, 4))

        env_btn_box = tk.Frame(self._cloud_frame, bg=self.C_SURFACE)
        env_btn_box.pack(fill='x', pady=(0, 10))

        self._env_buttons = {}
        for code, info in ENVIRONMENTS.items():
            btn = tk.Button(
                env_btn_box,
                text=f"{code} · {info['badge']}",
                command=lambda c=code: self._select_env(c),
                font=('Segoe UI', 9, 'bold'),
                bg=self.C_KEYCAP, fg=self.C_MUTED,
                activebackground=self.C_KEYCAP_HOVER, activeforeground=self.C_TEXT,
                relief='flat', bd=0, pady=6, cursor='hand2'
            )
            btn.pack(side='left', fill='x', expand=True, padx=2)
            self._env_buttons[code] = btn

        # ── Step 2: Per-User Cloud Run Service Selection ───────────────────────
        tk.Label(self._cloud_frame, text='2. Select Cloud Run Instance (Per-User):',
                 font=('Segoe UI', 9, 'bold'), fg=self.C_TEXT, bg=self.C_SURFACE).pack(anchor='w', pady=(0, 4))

        self._service_btn_box = tk.Frame(self._cloud_frame, bg=self.C_SURFACE)
        self._service_btn_box.pack(fill='x', pady=(0, 10))
        self._service_buttons = {}

        # ── Step 3: Target URL Field ──────────────────────────────────────────
        url_box = tk.Frame(self._cloud_frame, bg=self.C_SURFACE)
        url_box.pack(fill='x', pady=(0, 4))

        tk.Label(url_box, text='Target Endpoint URL:', font=('Segoe UI', 8), fg=self.C_MUTED, bg=self.C_SURFACE).pack(anchor='w')
        self._url_entry = tk.Entry(
            url_box, textvariable=self.custom_url_var,
            font=('Segoe UI', 8), bg='#0b0d13', fg='#38bdf8',
            insertbackground='#38bdf8', highlightbackground=self.C_BORDER, highlightthickness=1, bd=0
        )
        self._url_entry.pack(fill='x', pady=(2, 0), ipady=4)
        self._url_entry.bind('<KeyRelease>', lambda e: self._on_url_typed())

        # Status Pill Box
        status_box = tk.Frame(container, bg='#0e111a', highlightbackground=self.C_BORDER, highlightthickness=1)
        status_box.pack(fill='x', padx=16, pady=(4, 12))

        status_row = tk.Frame(status_box, bg='#0e111a')
        status_row.pack(fill='x', padx=10, pady=8)

        self._dot = tk.Label(status_row, text='●', font=('Segoe UI', 11), fg='#475569', bg='#0e111a')
        self._dot.pack(side='left')

        self._status_lbl = tk.Label(
            status_row, text='Ready to connect',
            font=('Segoe UI', 9, 'bold'), fg=self.C_MUTED, bg='#0e111a'
        )
        self._status_lbl.pack(side='left', padx=(6, 0))

        # Main Action Buttons Frame
        btn_box = tk.Frame(container, bg=self.C_SURFACE)
        btn_box.pack(fill='x', padx=16, pady=(0, 8))

        # Primary Launch Button
        self._main_btn = tk.Button(
            btn_box,
            text='⚡   Launch Cloud Soundboard & Start Hotkeys',
            command=self._launch_current_mode,
            bg=self.C_CYAN, fg='#ffffff',
            activebackground=self.C_CYAN_HOVER, activeforeground='#ffffff',
            font=('Segoe UI', 10, 'bold'),
            relief='flat', bd=0, pady=10, cursor='hand2'
        )
        self._main_btn.pack(fill='x', pady=(0, 6))

        # Secondary Button Box (Sync Hotkeys, Open Web UI & Audio Folder)
        sec_btn_box = tk.Frame(btn_box, bg=self.C_SURFACE)
        sec_btn_box.pack(fill='x')

        self._sync_btn = tk.Button(
            sec_btn_box, text='🔄  Re-sync Hotkeys',
            command=self._resync_hotkeys,
            bg=self.C_KEYCAP, fg='#38bdf8',
            activebackground=self.C_KEYCAP_HOVER, activeforeground='#ffffff',
            font=('Segoe UI', 9, 'bold'),
            relief='flat', bd=0, pady=6, cursor='hand2'
        )
        self._sync_btn.pack(side='left', fill='x', expand=True, padx=(0, 2))

        self._browser_btn = tk.Button(
            sec_btn_box, text='🌐  Open Web UI',
            command=self._open_web_ui,
            bg=self.C_KEYCAP, fg=self.C_TEXT,
            activebackground=self.C_KEYCAP_HOVER, activeforeground='#ffffff',
            font=('Segoe UI', 9, 'bold'),
            relief='flat', bd=0, pady=6, cursor='hand2'
        )
        self._browser_btn.pack(side='left', fill='x', expand=True, padx=2)

        self._folder_btn = tk.Button(
            sec_btn_box, text='📁  Audio Folder',
            command=self._open_folder,
            bg=self.C_KEYCAP, fg=self.C_MUTED,
            activebackground=self.C_KEYCAP_HOVER, activeforeground='#ffffff',
            font=('Segoe UI', 9, 'bold'),
            relief='flat', bd=0, pady=6, cursor='hand2'
        )
        self._folder_btn.pack(side='right', fill='x', expand=True, padx=(2, 0))

        # Footer Notice
        self._footer_lbl = tk.Label(
            container,
            text='Global in-game hotkeys active while this launcher runs.',
            font=('Segoe UI', 8), fg='#475569', bg=self.C_SURFACE
        )
        self._footer_lbl.pack(side='bottom', pady=(0, 8))

    def _sync_url_and_ui(self):
        curr_env = self.selected_env.get()
        curr_srv = self.selected_service.get()

        # Update environment button styles
        for code, btn in self._env_buttons.items():
            if code == curr_env:
                btn.config(bg=self.C_CYAN, fg='#ffffff')
            else:
                btn.config(bg=self.C_KEYCAP, fg=self.C_MUTED)

        # Rebuild / update service buttons for selected environment
        for widget in self._service_btn_box.winfo_children():
            widget.destroy()
        self._service_buttons.clear()

        env_info = ENVIRONMENTS.get(curr_env, ENVIRONMENTS['ADT'])
        service_defs = env_info['services']

        for s_code, s_data in service_defs.items():
            is_active = (curr_srv == s_code)
            btn = tk.Button(
                self._service_btn_box,
                text=s_data['label'],
                command=lambda sc=s_code: self._select_service(sc),
                font=('Segoe UI', 9, 'bold'),
                bg=self.C_CYAN if is_active else self.C_KEYCAP,
                fg='#ffffff' if is_active else self.C_MUTED,
                activebackground=self.C_CYAN_HOVER if is_active else self.C_KEYCAP_HOVER,
                activeforeground='#ffffff' if is_active else self.C_TEXT,
                relief='flat', bd=0, pady=6, cursor='hand2'
            )
            btn.pack(side='left', fill='x', expand=True, padx=2)
            self._service_buttons[s_code] = btn

        # Custom service button
        is_custom = (curr_srv == 'custom')
        cust_btn = tk.Button(
            self._service_btn_box,
            text='⚙️ Custom',
            command=lambda: self._select_service('custom'),
            font=('Segoe UI', 9, 'bold'),
            bg=self.C_CYAN if is_custom else self.C_KEYCAP,
            fg='#ffffff' if is_custom else self.C_MUTED,
            activebackground=self.C_CYAN_HOVER if is_custom else self.C_KEYCAP_HOVER,
            activeforeground='#ffffff' if is_custom else self.C_TEXT,
            relief='flat', bd=0, pady=6, cursor='hand2'
        )
        cust_btn.pack(side='left', fill='x', expand=True, padx=2)
        self._service_buttons['custom'] = cust_btn

        # Update Target URL value
        if curr_srv in service_defs:
            self.custom_url_var.set(service_defs[curr_srv]['url'])

        # Save active choice to settings
        _save_settings({
            'selected_env': curr_env,
            'selected_service': curr_srv,
            'custom_url': self.custom_url_var.get()
        })

    def _select_env(self, env_code):
        self.selected_env.set(env_code)
        # Keep same service code if it exists in new env, else fallback to env's default
        curr_srv = self.selected_service.get()
        env_services = ENVIRONMENTS[env_code]['services']
        if curr_srv not in env_services and curr_srv != 'custom':
            self.selected_service.set(ENVIRONMENTS[env_code]['default_service'])
        self._sync_url_and_ui()

    def _select_service(self, service_code):
        self.selected_service.set(service_code)
        self._sync_url_and_ui()

    def _on_url_typed(self):
        # If user manually types a URL that doesn't match predefined, mark as custom
        url = self.custom_url_var.get().strip()
        curr_env = self.selected_env.get()
        env_services = ENVIRONMENTS.get(curr_env, {}).get('services', {})
        matched = False
        for s_code, s_data in env_services.items():
            if url == s_data['url']:
                self.selected_service.set(s_code)
                matched = True
                break
        if not matched:
            self.selected_service.set('custom')

        for sc, btn in self._service_buttons.items():
            if sc == self.selected_service.get():
                btn.config(bg=self.C_CYAN, fg='#ffffff')
            else:
                btn.config(bg=self.C_KEYCAP, fg=self.C_MUTED)

        _save_settings({
            'selected_env': curr_env,
            'selected_service': self.selected_service.get(),
            'custom_url': url
        })

    def _set_mode(self, mode):
        self.current_mode.set(mode)
        if mode == 'cloud':
            self._cloud_tab_btn.config(bg=self.C_CYAN, fg='#ffffff')
            self._local_tab_btn.config(bg='#181d2a', fg=self.C_MUTED)
            self._cloud_frame.pack(fill='x', padx=16, pady=(0, 10))
            self._main_btn.config(text='⚡   Launch Cloud Soundboard & Start Hotkeys')
            self._sync_btn.pack(side='left', fill='x', expand=True, padx=(0, 2))
            self._browser_btn.pack(side='left', fill='x', expand=True, padx=2)
            self._footer_lbl.config(text='Global in-game hotkeys active while this launcher runs.')
            self._sync_url_and_ui()
        else:
            self._local_tab_btn.config(bg=self.C_CYAN, fg='#ffffff')
            self._cloud_tab_btn.config(bg='#181d2a', fg=self.C_MUTED)
            self._cloud_frame.pack_forget()
            self._main_btn.config(text='🌐   Launch Local Web Dashboard (127.0.0.1:5001)')
            self._sync_btn.pack_forget()
            self._browser_btn.pack_forget()
            self._footer_lbl.config(text='Local audio engine & Discord server run on your PC.')
            self._start_local_mode_server()

    def _launch_current_mode(self):
        mode = self.current_mode.get()
        if mode == 'cloud':
            target_url = self.custom_url_var.get().strip()
            if not target_url:
                msgbox.showerror("Error", "Please enter a valid Cloud Run URL.")
                return

            webbrowser.open(target_url)

            # Start Cloud Hotkey Companion in background
            env = self.selected_env.get()
            srv = self.selected_service.get().title()
            self._status_lbl.config(text=f"Connecting to {env} · {srv}…", fg=self.C_MUTED)
            self._dot.config(fg=self.C_GOLD)

            def _connect():
                self.cloud_companion = CloudHotkeyCompanion(
                    target_url,
                    on_status_change=self._on_companion_status
                )
                self.cloud_companion.sync_and_hook()

            threading.Thread(target=_connect, daemon=True).start()

        else:
            self._start_local_mode_server()
            webbrowser.open(LOCAL_SERVER_URL)

    def _open_web_ui(self):
        target_url = self.custom_url_var.get().strip()
        if target_url:
            webbrowser.open(target_url)

    def _start_local_mode_server(self):
        if not self.local_server_started:
            threading.Thread(target=_run_local_server, daemon=True).start()
            self.local_server_started = True
            self._poll_local_server()

    def _poll_local_server(self):
        if _port_open():
            self._dot.config(fg=self.C_GREEN)
            self._status_lbl.config(text='Local Server Active (127.0.0.1:5001)', fg=self.C_GREEN)
        else:
            self.after(400, self._poll_local_server)

    def _on_companion_status(self, is_ok, message):
        def _update():
            if is_ok:
                self._dot.config(fg=self.C_GREEN)
                self._status_lbl.config(text=message, fg=self.C_GREEN)
            else:
                self._dot.config(fg='#ef4444')
                self._status_lbl.config(text=message, fg='#ef4444')
        self.after(0, _update)

    def _resync_hotkeys(self):
        target_url = self.custom_url_var.get().strip()
        if not target_url:
            return
        self._status_lbl.config(text='Re-syncing hotkeys…', fg=self.C_GOLD)
        self._dot.config(fg=self.C_GOLD)

        def _sync():
            self.cloud_companion = CloudHotkeyCompanion(
                target_url,
                on_status_change=self._on_companion_status
            )
            self.cloud_companion.sync_and_hook()

        threading.Thread(target=_sync, daemon=True).start()

    def _open_folder(self):
        os.makedirs(AUDIO_FOLDER, exist_ok=True)
        if hasattr(os, 'startfile'):
            os.startfile(AUDIO_FOLDER)
        else:
            import subprocess
            subprocess.Popen(['xdg-open', AUDIO_FOLDER])

    def _quit(self):
        if self.cloud_companion:
            self.cloud_companion.unhook_all()
        self.destroy()
        os._exit(0)


if __name__ == '__main__':
    SoundboardLauncher().mainloop()
