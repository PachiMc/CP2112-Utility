# -*- mode: python ; coding: utf-8 -*-
# ============================================================
#  CP2112 Battery Analyzer  –  PyInstaller build spec
#  Generates a single-file executable for Windows / Linux / macOS
#
#  Usage:
#    pip install pyinstaller
#    pyinstaller cp2112_analyzer.spec
#
#  Output:
#    dist/CP2112-Battery-Analyzer.exe   (Windows)
#    dist/CP2112-Battery-Analyzer       (Linux / macOS)
# ============================================================

import sys
from pathlib import Path

APP_NAME    = 'CP2112-Battery-Analyzer'
SCRIPT      = str(Path('run_app.py'))
ICON_ICO    = str(Path('pyreader/icon.ico'))   # Windows / Linux
ICON_PNG    = str(Path('pyreader/icon.png'))   # macOS fallback
VERSION     = '1.0.0'

# ── Data files bundled inside the frozen executable ─────────────
#    (source, destination-folder-inside-bundle)
datas = [
    ('pyreader/icon.ico',         'pyreader'),
    ('pyreader/icon.png',         'pyreader'),
]

# Windows: bundle the Silicon Labs DLLs next to the executable
hiddenimports = []
binaries = []
if sys.platform == 'win32':
    from glob import glob
    for dll in glob('pyreader/*.dll'):
        binaries.append((dll, '.'))       # land in root of bundle

# ── Analysis ────────────────────────────────────────────────────
a = Analysis(
    [SCRIPT],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'scipy'],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

# ── One-file EXE (Windows / Linux) ──────────────────────────────
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # no console window on Windows
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON_ICO if sys.platform == 'win32' else (ICON_PNG if sys.platform != 'darwin' else None),
    version_file=None,
)

# ── macOS .app bundle ────────────────────────────────────────────
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name=f'{APP_NAME}.app',
        icon=ICON_PNG,
        bundle_identifier='com.cp2112.battery-analyzer',
        info_plist={
            'CFBundleName':             'CP2112 Battery Analyzer',
            'CFBundleDisplayName':      'CP2112 Battery Analyzer',
            'CFBundleVersion':          VERSION,
            'CFBundleShortVersionString': VERSION,
            'NSHighResolutionCapable':  True,
            'NSHumanReadableCopyright': 'Open Source – MIT License',
        },
    )
