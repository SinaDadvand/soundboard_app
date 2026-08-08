# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for Virtual Soundboard launcher
# Build with:  pyinstaller launcher.spec
#
# The resulting exe goes to:  dist\VirtualSoundboard.exe
# Audio files must be placed alongside the exe at:
#   dist\static\audio\*.mp3   (or .wav / .ogg)
#

block_cipher = None

a = Analysis(
    ['launcher.py'],
    pathex=['.'],
    binaries=[],
    # Bundle the Flask templates and static assets (CSS/JS).
    # Audio files are NOT bundled – they stay next to the exe so the user
    # can manage them via the "Open Audio Folder" button.
    datas=[
        ('templates',   'templates'),
        ('static/css',  'static/css'),
        ('static/js',   'static/js'),
        ('app.py',      '.'),          # included so launcher can import it
    ],
    hiddenimports=[
        # Flask + deps
        'flask',
        'flask.templating',
        'werkzeug',
        'werkzeug.serving',
        'werkzeug.middleware',
        'jinja2',
        'jinja2.ext',
        'click',
        'itsdangerous',
        'blinker',
        'markupsafe',
        # App deps
        'keyboard',
        'pygame',
        'pygame.mixer',
        'dotenv',
        'python_dotenv',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='VirtualSoundboard',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                # set True if UPX is installed for smaller file
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,             # no black console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='Virtual Soundboard Icon.ico',
)
