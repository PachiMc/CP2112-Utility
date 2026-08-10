# CP2112 Python GUI



## Requirements

* Install the required dependencies:

```bash
pip install -r requirements.txt
```

Use the system Python installation (Python >= 3.11 recommended). On Windows, the `py` launcher can be used:

```bash
py -3 -m pip install -r requirements.txt
```

Run the example GUI using the Windows Python launcher:

```bash
py -3 -m pyreader
```

## Features

* Detection of CP2112 devices and device open/close operations.
* Reading and writing SMBus transfers with configurable slave addresses and hexadecimal data.
* Latch read/write operations and transfer/I/O cancellation.
* Smart Battery-compatible register reading, including configurable device addresses, predefined registers, battery summaries, and report export.
* Visible logging in the GUI with export to text files for logs and reports.
