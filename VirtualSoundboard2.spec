# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for Virtual Soundboard 2
# Generates dist\VirtualSoundboard2.exe with new Chevron Neon Icon
#

block_cipher = None

a = Analysis(
    ['launcher.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('static/css', 'static/css'),
        ('static/js', 'static/js'),
        ('app_icon.ico', '.'),
        ('app_icon.png', '.'),
        ('soundboard_config.json', '.'),
    ],
    hiddenimports=[
        # Flask + web stack
        'flask',
        'flask.templating',
        'werkzeug',
        'werkzeug.serving',
        'werkzeug.middleware',
        'jinja2',
        'click',
        'itsdangerous',
        'blinker',
        'markupsafe',
        # Audio Engine & DSP
        'sounddevice',
        'soundfile',
        'numpy',
        'scipy',
        'scipy.signal',
        'scipy.fft',
        'scipy.special',
        # Hotkeys & config
        'keyboard',
        'dotenv',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pygame', 'matplotlib', 'pandas'],
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
    name='VirtualSoundboard2',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app_icon.ico',
)
