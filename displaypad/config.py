"""Configuration management for DisplayPad macOS.

Stores key mappings (which macro on which key) as JSON.
"""

import json
import os

DEFAULT_CONFIG_PATH = os.path.expanduser("~/.config/displaypad/config.json")

DEFAULT_CONFIG = {
    "keys": {
        "0": {"type": "spotify", "action": "play_pause", "label": "Play\nPause"},
        "1": {"type": "spotify", "action": "previous", "label": "Prev"},
        "2": {"type": "spotify", "action": "next", "label": "Next"},
        "3": {"type": "spotify", "action": "vol_up", "label": "Vol +"},
        "4": {"type": "spotify", "action": "vol_down", "label": "Vol -"},
        "5": {"type": "spotify", "action": "now_playing", "label": "Now\nPlaying"},
        "6": {"type": "api", "action": "call", "label": "API\nCall",
               "url": "https://httpbin.org/get", "method": "GET"},
        "7": {"type": "none", "label": ""},
        "8": {"type": "none", "label": ""},
        "9": {"type": "none", "label": ""},
        "10": {"type": "none", "label": ""},
        "11": {"type": "none", "label": ""},
    }
}


def load_config(path=None):
    """Load configuration from JSON file."""
    path = path or DEFAULT_CONFIG_PATH
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return DEFAULT_CONFIG.copy()


def save_config(config, path=None):
    """Save configuration to JSON file."""
    path = path or DEFAULT_CONFIG_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(config, f, indent=2)
