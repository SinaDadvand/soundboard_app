"""
Virtual Soundboard Launcher - Pro Edition
=========================================
Modern Tkinter desktop wrapper that:
  - Starts the Flask soundboard server in a background thread
  - Displays real-time server status with pulsing indicator
  - "Open Soundboard Dashboard" -> http://127.0.0.1:5001
  - "Open Audio Library Folder" -> Windows Explorer on audio files directory
  - Dark neon aesthetic matching the web UI
"""
import sys
import os
import threading
import webbrowser
import socket
import tkinter as tk
import tkinter.messagebox as msgbox

# ─────────────────────────────────────────────────────────────────────────────
# Path resolution
# ─────────────────────────────────────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    _BUNDLE = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    _EXE_DIR = os.path.dirname(sys.executable)
else:
    _BUNDLE = os.path.dirname(os.path.abspath(__file__))
    _EXE_DIR = _BUNDLE

# Audio folder resolution
audio_candidates = [
    os.path.join(_EXE_DIR, 'static', 'audio'),
    os.path.join(os.path.dirname(_EXE_DIR), 'static', 'audio'),
    os.path.join(_BUNDLE, 'static', 'audio')
]
AUDIO_FOLDER = next((p for p in audio_candidates if os.path.exists(p) and len(os.listdir(p)) > 0), audio_candidates[0])
SERVER_URL = 'http://127.0.0.1:5001'

os.makedirs(AUDIO_FOLDER, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# Flask server thread
# ─────────────────────────────────────────────────────────────────────────────
def _run_server():
    """Import app.py and run the Flask server in a daemon thread."""
    if _BUNDLE not in sys.path:
        sys.path.insert(0, _BUNDLE)

    try:
        import app as sb
        sb.initialize_app()
    except Exception as exc:
        msgbox.showerror('Import Error', f'Could not load soundboard app:\n{exc}')
        return

    import logging
    logging.getLogger('werkzeug').setLevel(logging.ERROR)

    sb.app.run(host='127.0.0.1', port=5001, debug=False, use_reloader=False)


def _port_open(host='127.0.0.1', port=5001) -> bool:
    """Return True if the Flask server is accepting connections."""
    try:
        with socket.create_connection((host, port), timeout=0.4):
            return True
    except OSError:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Modern Dark Launcher GUI
# ─────────────────────────────────────────────────────────────────────────────
class SoundboardLauncher(tk.Tk):
    # Modern Design Palette
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
        self.title('Soundboard Pro 2.1')
        self.geometry('400x330')
        self.resizable(False, False)
        self.configure(bg=self.C_BG)
        self.protocol('WM_DELETE_WINDOW', self._quit)

        # Set Window Icon
        icon_candidates = [
            os.path.join(_EXE_DIR, 'app_icon.ico'),
            os.path.join(_BUNDLE, 'app_icon.ico'),
            os.path.join(_EXE_DIR, 'neon_v_soundboard_icon.ico'),
            os.path.join(_BUNDLE, 'neon_v_soundboard_icon.ico')
        ]
        for icon_path in icon_candidates:
            if os.path.exists(icon_path):
                try:
                    self.iconbitmap(icon_path)
                    break
                except Exception:
                    pass

        self._build_ui()

        # Start Flask background server
        threading.Thread(target=_run_server, daemon=True).start()

        # Poll until server is ready
        self._poll_server()

    def _build_ui(self):
        # Outer Container Frame
        container = tk.Frame(self, bg=self.C_SURFACE, highlightbackground=self.C_BORDER, highlightthickness=1)
        container.pack(fill='both', expand=True, padx=16, pady=16)

        # Header Title Bar
        header = tk.Frame(container, bg=self.C_SURFACE)
        header.pack(fill='x', padx=18, pady=(18, 10))

        title_frame = tk.Frame(header, bg=self.C_SURFACE)
        title_frame.pack(side='left')

        tk.Label(title_frame, text='⚡ Soundboard Pro',
                 font=('Segoe UI', 15, 'bold'),
                 fg=self.C_TEXT, bg=self.C_SURFACE).pack(side='left')

        badge = tk.Label(title_frame, text=' NUMPAD ',
                         font=('Segoe UI', 8, 'bold'),
                         fg=self.C_GOLD, bg='#241c09',
                         highlightbackground='#5a440c', highlightthickness=1)
        badge.pack(side='left', padx=(8, 0))

        # Status Pill Box
        status_box = tk.Frame(container, bg='#0e111a', highlightbackground=self.C_BORDER, highlightthickness=1)
        status_box.pack(fill='x', padx=18, pady=(0, 14))

        status_row = tk.Frame(status_box, bg='#0e111a')
        status_row.pack(fill='x', padx=10, pady=8)

        self._dot = tk.Label(status_row, text='●', font=('Segoe UI', 11),
                             fg='#475569', bg='#0e111a')
        self._dot.pack(side='left')

        self._status_lbl = tk.Label(status_row, text='Initializing background engine…',
                                    font=('Segoe UI', 9, 'bold'),
                                    fg=self.C_MUTED, bg='#0e111a')
        self._status_lbl.pack(side='left', padx=(6, 0))

        self._url_lbl = tk.Label(status_row, text='',
                                  font=('Courier New', 9, 'bold'),
                                  fg=self.C_CYAN, bg='#0e111a',
                                  cursor='hand2')
        self._url_lbl.pack(side='right')
        self._url_lbl.bind('<Button-1>', lambda _: self._open_browser())

        # Action Buttons
        btn_box = tk.Frame(container, bg=self.C_SURFACE)
        btn_box.pack(fill='x', padx=18, pady=(4, 10))

        # 1. Primary Button: Open in Browser
        self._create_button(
            btn_box,
            text='🌐   Launch Web Dashboard',
            bg=self.C_CYAN,
            fg='#ffffff',
            hover_bg=self.C_CYAN_HOVER,
            cmd=self._open_browser
        ).pack(fill='x', pady=(0, 8))

        # 2. Secondary Button: Open Audio Folder
        self._create_button(
            btn_box,
            text='📁   Open Audio Library Folder',
            bg=self.C_KEYCAP,
            fg='#38bdf8',
            hover_bg=self.C_KEYCAP_HOVER,
            border_color=self.C_BORDER,
            cmd=self._open_folder
        ).pack(fill='x')

        # Footer Notice
        tk.Label(container,
                 text='Soundboard runs in background while this window is open.',
                 font=('Segoe UI', 8),
                 fg='#475569', bg=self.C_SURFACE) \
          .pack(side='bottom', pady=(0, 10))

    def _create_button(self, parent, text, bg, fg, hover_bg, cmd, border_color=None):
        border = tk.Frame(parent, bg=border_color or bg)
        btn = tk.Button(border, text=text, command=cmd,
                        bg=bg, fg=fg,
                        activebackground=hover_bg, activeforeground='#ffffff',
                        font=('Segoe UI', 10, 'bold'),
                        relief='flat', bd=0, pady=10,
                        cursor='hand2')
        btn.pack(fill='both', padx=1, pady=1)

        btn.bind('<Enter>', lambda e: btn.config(bg=hover_bg))
        btn.bind('<Leave>', lambda e: btn.config(bg=bg))
        return border

    def _open_browser(self):
        webbrowser.open(SERVER_URL)

    def _open_folder(self):
        os.makedirs(AUDIO_FOLDER, exist_ok=True)
        os.startfile(AUDIO_FOLDER)

    def _quit(self):
        self.destroy()
        os._exit(0)

    def _poll_server(self):
        if _port_open():
            self._dot.config(fg=self.C_GREEN)
            self._status_lbl.config(text='Server Active', fg=self.C_GREEN)
            self._url_lbl.config(text=SERVER_URL)
        else:
            self.after(400, self._poll_server)


if __name__ == '__main__':
    SoundboardLauncher().mainloop()
