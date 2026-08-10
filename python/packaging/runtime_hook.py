"""PyInstaller runtime hook — register DLL search paths before imports."""
import os
import sys
from pathlib import Path

if getattr(sys, 'frozen', False):
    base = Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent))
    if hasattr(os, 'add_dll_directory'):
        try:
            os.add_dll_directory(str(base))
        except OSError:
            pass
    os.environ['PATH'] = str(base) + os.pathsep + os.environ.get('PATH', '')
