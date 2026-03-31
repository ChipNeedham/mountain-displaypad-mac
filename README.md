# DisplayPad macOS Controller

Unofficial macOS controller for the [Mountain DisplayPad](https://mountain.gg/keypads/displaypad/) — a 12-key macro keypad with individual LCD displays on each key.

Mountain's official Base Camp software is Windows-only and the product is EOL. This project reverse-engineers the USB HID protocol to provide full macOS support.

## Features

- **Device communication** via USB HID (hidapi)
- **Custom icons** on each key (102x102 pixel IPS LCD displays)
- **Macro engine** with built-in support for:
  - Spotify control (play/pause, next, previous, volume)
  - HTTP API calls (any endpoint, method, headers, body)
  - Shell commands
  - App launcher
  - Keystroke simulation (via AppleScript)
- **Simple GUI** for configuration (tkinter)
- **Persistent config** saved to `~/.config/displaypad/config.json`
- **Original Mountain icons** extracted from Base Camp software

## Setup

```bash
# Install Python 3.12+ (if needed)
brew install python@3.12 python-tk@3.12

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

```bash
source venv/bin/activate
python main.py
```

1. Plug in your DisplayPad via USB-C
2. Click **Connect** in the app
3. Click any key in the grid to configure its macro
4. Click **Push to Device** to send icons to the physical keys
5. Press keys on the device to trigger macros

## Device Protocol

Reverse-engineered from [JeLuF/mountain-displaypad](https://github.com/JeLuF/mountain-displaypad):

- **USB**: VID `0x3282`, PID `0x0009`
- **Interfaces**: #1 (display data), #3 (control/buttons)
- **Display**: 102x102 px per key, BGR format, raw pixel transfer in 1024-byte HID chunks
- **Buttons**: Bit masks on HID report bytes 42 and 47

## Project Structure

```
displaypad-mac/
├── main.py                 # Entry point
├── displaypad/
│   ├── device.py           # USB HID protocol implementation
│   ├── macros.py           # Macro engine + built-in actions
│   ├── icons.py            # Icon generation and loading
│   ├── config.py           # JSON config management
│   └── gui.py              # tkinter GUI
├── icons/                  # Extracted Mountain Base Camp icons
└── requirements.txt
```

## Credits

- Protocol reverse engineering: [JeLuF/mountain-displaypad](https://github.com/JeLuF/mountain-displaypad)
- Original icons: Mountain Base Camp v1.9.9
- Related: [Mountain-BC/DisplayPad.SDK.Demo](https://github.com/Mountain-BC/DisplayPad.SDK.Demo)
