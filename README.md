# CP2112 Battery Analyzer

Standalone desktop application for diagnosing and repairing laptop batteries via the Silicon Labs **CP2112** HID-to-SMBus USB adapter and the Smart Battery System (SBS v1.1) protocol.

## Features

- **Battery dashboard** — live SOC, voltage, current, temperature, cell voltages
- **SBS v1.1 registers** — full Smart Battery register table with CSV export
- **Unseal / seal** — presets for TI BQ20Zxx, BQ30xx, BQ40xx, Sony/Sanyo, and custom keys
- **Raw SMBus I/O** — direct transfers and GPIO latch control
- **Diagnostics & logs** — built-in DLL/device checks and exportable activity log
- **Health assessment** — automatic warnings for SOH, cycles, cell imbalance, and protection flags
- **Dark mode** — enabled by default (toggle in View menu)
- **Clipboard snapshot** — copy full battery readout with one click
- **Configurable polling** — auto-monitor interval from 1–60 seconds
- **Connection guide** — pinout reference and unseal key cheat sheet

## Download

Pre-built Windows executables are available on the [**Releases**](https://github.com/PachiMc/CP2112-Utility/releases) page.

The `.exe` is fully standalone — Silicon Labs DLLs are bundled inside. Only the CP2112 **USB driver** must be installed separately ([Silicon Labs download](https://www.silabs.com/developers/usb-to-i2c-bridge?tab=downloads)).

## Run from source

### Requirements

- Windows 10/11
- Python 3.11+
- PySide6
- `SLABHIDtoSMBus.dll` and `SLABHIDDevice.dll` in `python/vendor/` (see [vendor README](python/vendor/README.md))

### Install and run

```powershell
cd python
py -3 -m pip install -r requirements.txt
py -3 -m pyreader
```

Or double-click `python/run.bat`.

## Build standalone executable

1. Copy both Silicon Labs DLLs into `python/vendor/` (see [vendor README](python/vendor/README.md)).
2. Run the build script:

```powershell
cd python
.\build.bat
```

Output: `python/dist/CP2112-Battery-Analyzer.exe`

## Project structure

```
.
├── .github/workflows/release.yml   # Windows release CI
├── python/
│   ├── packaging/
│   │   ├── cp2112_analyzer.spec  # PyInstaller spec
│   │   └── runtime_hook.py       # DLL path setup for frozen exe
│   ├── pyreader/
│   │   ├── main.py               # PySide6 GUI
│   │   ├── cp2112.py             # ctypes CP2112 wrapper
│   │   ├── paths.py              # Resource / DLL path helpers
│   │   └── icon.ico / icon.png
│   ├── vendor/                   # SLAB DLLs (not in git by default)
│   ├── build.bat                 # One-click Windows build
│   ├── run.bat                   # Dev launcher
│   ├── run_app.py                # PyInstaller entry point
│   ├── pyproject.toml
│   └── requirements.txt
└── README.md
```

## Hardware connection

```
CP2112 USB Adapter          Laptop Battery
──────────────────          ──────────────
  SDA  ──────────────────►  SMBus Data  (SDA)
  SCL  ──────────────────►  SMBus Clock (SCL)
  GND  ──────────────────►  Ground      (GND / −)
```

Default SMBus address: `0x0B` (7-bit) for standard SBS laptop batteries.

## License

MIT
