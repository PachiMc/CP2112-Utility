# Silicon Labs CP2112 runtime DLLs (Windows)

Place the following files from the **CP2112 SDK** in this folder before building the standalone executable:

| File | Description |
|------|-------------|
| `SLABHIDtoSMBus.dll` | HID-to-SMBus API |
| `SLABHIDDevice.dll` | HID device layer (required at runtime) |

## Where to get them

1. Download the [CP2112 SDK](https://www.silabs.com/developers/usb-to-i2c-bridge?tab=downloads) from Silicon Labs.
2. After installation, copy both DLLs from the SDK `Library` folder (typically `C:\SiliconLabs\CP211x\Library\x64\` on 64-bit Windows).
3. Paste them into this `vendor/` directory.

These DLLs are bundled into the release `.exe` by PyInstaller — end users do **not** need to install them separately (only the CP2112 USB driver).
