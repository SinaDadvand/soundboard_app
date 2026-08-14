"""
Virtual Soundboard Launcher
===========================
A lightweight tkinter wrapper that:
  - Starts the Flask soundboard server in a background thread
  - Shows server status with a live indicator
  - "Open Soundboard in Browser" → http://127.0.0.1:5001
  - "Open Audio Folder"          → Windows Explorer on the audio directory

Works both as a plain Python script and as a PyInstaller .exe bundle.
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
# When frozen by PyInstaller --onefile:
#   sys._MEIPASS  → temp dir that holds the bundled Python code + assets
#   sys.executable → path to the running .exe
# When running as a plain script both point to the script's own directory.
# ─────────────────────────────────────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    _BUNDLE  = sys._MEIPASS                         # bundled code lives here
    _EXE_DIR = os.path.dirname(sys.executable)      # .exe lives here
else:
    _BUNDLE  = os.path.dirname(os.path.abspath(__file__))
    _EXE_DIR = _BUNDLE

# Audio folder always sits NEXT TO the exe so the user can manage their files.
AUDIO_FOLDER = os.path.join(_EXE_DIR, 'static', 'audio')
SERVER_URL   = 'http://127.0.0.1:5001'

os.makedirs(AUDIO_FOLDER, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# Flask server
# ─────────────────────────────────────────────────────────────────────────────
def _run_server():
    """Import app.py and run the Flask server.  Intended for a daemon thread."""
    if _BUNDLE not in sys.path:
        sys.path.insert(0, _BUNDLE)

    try:
        import app as sb
    except Exception as exc:
        msgbox.showerror('Import error', f'Could not load soundboard app:\n{exc}')
        return

    # Override AUDIO_FOLDER so the server reads from the exe's directory,
    # not from the temporary PyInstaller extraction folder.
    sb.AUDIO_FOLDER = AUDIO_FOLDER
    os.makedirs(AUDIO_FOLDER, exist_ok=True)

    # Initialize soundboard services (audio engine, hotkeys, config)
    try:
        if hasattr(sb, 'initialize_app'):
            sb.initialize_app()
        else:
            sb.load_sounds()
            sb.setup_hotkeys()
            sb.start_keyboard_listener()
    except Exception as e:
        print(f"[Launcher] Init notice: {e}")

    # Suppress werkzeug request-level logs in the background thread
    import logging
    logging.getLogger('werkzeug').setLevel(logging.ERROR)

    sb.app.run(host='127.0.0.1', port=5001, debug=False, use_reloader=False)


def _port_open(host='127.0.0.1', port=5001) -> bool:
    """Return True if the Flask server is accepting connections."""
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# GUI
# ─────────────────────────────────────────────────────────────────────────────
class SoundboardLauncher(tk.Tk):
    # ── Design tokens ────────────────────────────────────────────────────────
    C_BG     = '#0d0d1a'
    C_CARD   = '#15152b'
    C_ACCENT = '#7c6fe0'
    C_GREEN  = '#34d399'
    C_GREY   = '#7070a0'
    C_TEXT   = '#dde0f5'
    C_DIV    = '#1e1e3a'

    def __init__(self):
        super().__init__()
        self.title('Virtual Soundboard')
        self.geometry('370x295')
        self.resizable(False, False)
        self.configure(bg=self.C_BG)
        self.protocol('WM_DELETE_WINDOW', self._quit)

        self._build_ui()

        # Start the Flask server in a daemon thread
        threading.Thread(target=_run_server, daemon=True).start()

        # Begin polling until the server accepts connections
        self._poll_server()

    # ── UI construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        H_PAD = {'padx': 28}

        # Title
        tk.Label(self,
                 text='🎵  Virtual Soundboard',
                 font=('Segoe UI', 16, 'bold'),
                 fg=self.C_ACCENT, bg=self.C_BG) \
          .pack(anchor='w', pady=(26, 0), **H_PAD)

        # Status row
        row = tk.Frame(self, bg=self.C_BG)
        row.pack(anchor='w', pady=(9, 2), **H_PAD)

        self._dot = tk.Label(row, text='●', font=('Segoe UI', 12),
                             fg='#2a2a44', bg=self.C_BG)
        self._dot.pack(side='left')

        self._status_lbl = tk.Label(row, text='Starting server…',
                                    font=('Segoe UI', 10),
                                    fg=self.C_GREY, bg=self.C_BG)
        self._status_lbl.pack(side='left', padx=(7, 0))

        # Clickable URL (visible once server is running)
        self._url_lbl = tk.Label(self, text='',
                                  font=('Courier', 9),
                                  fg=self.C_ACCENT, bg=self.C_BG,
                                  cursor='hand2')
        self._url_lbl.pack(anchor='w', **H_PAD)
        self._url_lbl.bind('<Button-1>', lambda _: self._open_browser())

        # Divider
        tk.Frame(self, bg=self.C_DIV, height=1) \
          .pack(fill='x', padx=28, pady=14)

        # Primary action – open browser
        self._btn(
            '🌐   Open Soundboard in Browser',
            self.C_ACCENT, '#ffffff', self._open_browser
        ).pack(fill='x', padx=28, pady=(0, 10))

        # Secondary action – open audio folder
        self._btn(
            '📁   Open Audio Folder',
            self.C_CARD, self.C_TEXT, self._open_folder,
            border_color='#262648'
        ).pack(fill='x', padx=28)

        # Footer
        tk.Label(self,
                 text='Server stops when this window is closed.',
                 font=('Segoe UI', 8),
                 fg='#3a3a5a', bg=self.C_BG) \
          .pack(side='bottom', pady=10)

    def _btn(self, label: str, bg: str, fg: str, cmd,
             border_color: str = None) -> tk.Frame:
        """Return a styled flat button wrapped in a thin border frame."""
        outer = tk.Frame(self, bg=border_color or bg)
        inner = tk.Frame(outer, bg=bg)
        inner.pack(fill='both', padx=1, pady=1)

        b = tk.Button(inner, text=label, command=cmd,
                      bg=bg, fg=fg,
                      activebackground=self.C_ACCENT,
                      activeforeground='white',
                      font=('Segoe UI', 11, 'bold'),
                      relief='flat', bd=0, pady=12,
                      cursor='hand2')
        b.pack(fill='both')

        lighter = self._lighten(bg, 28)
        b.bind('<Enter>', lambda e, w=b: w.config(bg=lighter))
        b.bind('<Leave>', lambda e, w=b, c=bg: w.config(bg=c))
        return outer

    @staticmethod
    def _lighten(hex_col: str, amount: int = 28) -> str:
        """Return a slightly lighter hex colour for hover effect."""
        try:
            r = int(hex_col[1:3], 16)
            g = int(hex_col[3:5], 16)
            b = int(hex_col[5:7], 16)
            return (f'#{min(r + amount, 255):02x}'
                    f'{min(g + amount, 255):02x}'
                    f'{min(b + amount, 255):02x}')
        except Exception:
            return hex_col

    # ── Actions ────────────────────────────────────────────────────────────────
    def _open_browser(self):
        webbrowser.open(SERVER_URL)

    def _open_folder(self):
        os.makedirs(AUDIO_FOLDER, exist_ok=True)
        os.startfile(AUDIO_FOLDER)

    def _quit(self):
        self.destroy()
        # Force-kill the process so Flask's background thread also stops
        os._exit(0)

    # ── Server status polling ──────────────────────────────────────────────────
    def _poll_server(self):
        if _port_open():
            self._dot.config(fg=self.C_GREEN)
            self._status_lbl.config(text='Server running', fg=self.C_GREEN)
            self._url_lbl.config(text=SERVER_URL)
        else:
            self.after(500, self._poll_server)


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    SoundboardLauncher().mainloop()
