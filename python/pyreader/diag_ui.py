import tkinter as tk
from tkinter import scrolledtext
import sys
from pathlib import Path

# Ensure package imports work when running this file directly
try:
    import pyreader.cp2112 as cp
except Exception:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import cp2112 as cp
import threading
import time

def run_diagnose(text_widget):
    text_widget.delete('1.0', tk.END)
    text_widget.insert(tk.END, 'Running diagnose...\n')
    def worker():
        try:
            out = cp.diagnose(verbose=False)
            lines = []
            if not out.get('dll_found'):
                lines.append('DLL not loaded: ' + str(out.get('dll_error')))
            else:
                if 'lib_version_rc' in out:
                    lines.append(f"Library: rc={out['lib_version_rc']} version={out.get('lib_major','?')}.{out.get('lib_minor','?')} release={out.get('lib_is_release')}")
                if 'num_devices' in out:
                    lines.append(f"Devices found: {out['num_devices']} (rc={out.get('num_devices_rc')})")
                if 'open_rc' in out:
                    lines.append(f"Open device 0: rc={out['open_rc']} ({cp.status_str(out.get('open_rc'))})")
                if 'isopened' in out:
                    lines.append(f"Is opened: {out.get('isopened')} (rc={out.get('isopened_rc')})")
                if 'opened_serial' in out:
                    lines.append('Serial: ' + str(out.get('opened_serial')))
            if not lines:
                lines.append('No diagnostic information available.')
        except Exception as e:
            lines = [f'Exception during diagnose: {e}']
        def ui_update():
            text_widget.delete('1.0', tk.END)
            text_widget.insert(tk.END, '\n'.join(lines))
        text_widget.after(0, ui_update)
    t = threading.Thread(target=worker, daemon=True)
    t.start()


root = tk.Tk()
root.title('CP2112 Diagnostic UI')
root.geometry('600x300')

text = scrolledtext.ScrolledText(root, wrap=tk.WORD)
text.pack(fill=tk.BOTH, expand=True)

frame = tk.Frame(root)
frame.pack(fill=tk.X)

btn_refresh = tk.Button(frame, text='Refresh', command=lambda: run_diagnose(text))
btn_refresh.pack(side=tk.LEFT, padx=6, pady=6)

btn_quit = tk.Button(frame, text='Quit', command=root.destroy)
btn_quit.pack(side=tk.RIGHT, padx=6, pady=6)

# Run a first diagnose
run_diagnose(text)

root.mainloop()
