# CP2112 Laptop Battery Reader

Python GUI utility for interacting with CP2112 SMBus devices on Windows. This project can detect CP2112 hardware, read and write SMBus data, inspect GPIO/latch state, and read Smart Battery-style registers such as voltage, current, temperature, state of charge, and manufacturer information.

## Features

- Detect CP2112 devices connected to the system
- Open and close devices and inspect their metadata
- Read and write raw SMBus transactions
- Read and write latch values
- Cancel active transfers and I/O operations
- Run diagnostics against the underlying DLL interface
- Read Smart Battery registers from a configurable slave address
- Generate battery summaries and export reports/logs from the GUI

## Requirements

- Windows
- Python 3.11 or newer
- PySide6
- The SLAB HID-to-SMBus DLL (`SLABHIDtoSMBus.dll`) available in the PATH or next to the executable

## Installation

From the project root:

```powershell
py -3 -m pip install -r requirements.txt
```

If you use a virtual environment, activate it first:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
py -3 -m pip install -r requirements.txt
```

## Running the GUI

```powershell
cd python
py -3 -m pyreader
```

## Project structure

```text
.
├── python/
│   ├── pyreader/
│   │   ├── __init__.py
│   │   ├── __main__.py
│   │   ├── cp2112.py
│   │   ├── diag_ui.py
│   │   └── main.py
│   ├── pyproject.toml
│   ├── README.md
│   └── requirements.txt
└── README.md
```

## Hardware notes

This project is intended for use with CP2112-based USB-SMBus adapters and Smart Battery hardware. You will need a compatible board and the proper wiring to your battery or device. Always connect the lines carefully and never connect the SMBus pins directly to the battery positive terminal.

## Notes

- The CP2112 wrapper relies on the SLAB HID-to-SMBus DLL and may require the DLL to be present in the working directory or in your PATH.
- This repository is intended for debugging, experimentation, and hardware interaction. Use it carefully with real devices.

## License

This project does not currently include a license file. If you plan to publish it publicly, consider adding a LICENSE file before sharing the repository.
