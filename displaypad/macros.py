"""Macro engine for DisplayPad.

Each macro has:
  - A key index (0-11)
  - An icon (PIL Image)
  - An action (callable)
  - Optional on_press/on_release distinction
"""

import subprocess
import requests
import json
import os
from dataclasses import dataclass, field
from typing import Callable, Optional
from PIL import Image


@dataclass
class Macro:
    name: str
    key_index: int
    icon: Image.Image
    on_press: Optional[Callable] = None
    on_release: Optional[Callable] = None


class MacroEngine:
    """Manages macros and dispatches key events."""

    def __init__(self):
        self.macros: dict[int, Macro] = {}  # key_index -> Macro

    def register(self, macro: Macro):
        self.macros[macro.key_index] = macro

    def unregister(self, key_index: int):
        self.macros.pop(key_index, None)

    def handle_key_down(self, key_num: int):
        """Handle key press (key_num is 1-based from device)."""
        key_index = key_num - 1  # convert to 0-based
        macro = self.macros.get(key_index)
        if macro and macro.on_press:
            try:
                macro.on_press()
            except Exception as e:
                print(f"Macro '{macro.name}' error: {e}")

    def handle_key_up(self, key_num: int):
        """Handle key release (key_num is 1-based from device)."""
        key_index = key_num - 1
        macro = self.macros.get(key_index)
        if macro and macro.on_release:
            try:
                macro.on_release()
            except Exception as e:
                print(f"Macro '{macro.name}' release error: {e}")


# ── Built-in macro actions ──────────────────────────────────────────────


def spotify_play_pause():
    """Toggle Spotify play/pause via AppleScript."""
    subprocess.run([
        "osascript", "-e",
        'tell application "Spotify" to playpause'
    ], capture_output=True)


def spotify_next():
    """Skip to next track via AppleScript."""
    subprocess.run([
        "osascript", "-e",
        'tell application "Spotify" to next track'
    ], capture_output=True)


def spotify_previous():
    """Go to previous track via AppleScript."""
    subprocess.run([
        "osascript", "-e",
        'tell application "Spotify" to previous track'
    ], capture_output=True)


def spotify_volume_up():
    """Increase Spotify volume by 10."""
    subprocess.run([
        "osascript", "-e",
        'tell application "Spotify" to set sound volume to (sound volume + 10)'
    ], capture_output=True)


def spotify_volume_down():
    """Decrease Spotify volume by 10."""
    subprocess.run([
        "osascript", "-e",
        'tell application "Spotify" to set sound volume to (sound volume - 10)'
    ], capture_output=True)


def spotify_get_current_track():
    """Get the currently playing track info."""
    result = subprocess.run([
        "osascript", "-e",
        'tell application "Spotify"\n'
        'set trackName to name of current track\n'
        'set artistName to artist of current track\n'
        'return trackName & " - " & artistName\n'
        'end tell'
    ], capture_output=True, text=True)
    return result.stdout.strip()


def make_api_call(url, method="GET", headers=None, body=None, callback=None):
    """Create an action that makes an HTTP API call.

    Args:
        url: The endpoint URL
        method: HTTP method (GET, POST, PUT, DELETE)
        headers: Optional dict of headers
        body: Optional dict for JSON body
        callback: Optional function(response) called with the result

    Returns:
        A callable that performs the API request.
    """
    def action():
        try:
            resp = requests.request(
                method=method,
                url=url,
                headers=headers or {},
                json=body if body else None,
                timeout=10,
            )
            print(f"API {method} {url} -> {resp.status_code}")
            if callback:
                callback(resp)
        except Exception as e:
            print(f"API call failed: {e}")

    return action


def run_shell_command(command):
    """Create an action that runs a shell command.

    Args:
        command: Shell command string.

    Returns:
        A callable.
    """
    def action():
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=30
            )
            if result.stdout:
                print(f"Command output: {result.stdout.strip()}")
            if result.returncode != 0 and result.stderr:
                print(f"Command error: {result.stderr.strip()}")
        except Exception as e:
            print(f"Shell command failed: {e}")

    return action


def open_app(app_name):
    """Create an action that opens a macOS application."""
    def action():
        subprocess.run(["open", "-a", app_name], capture_output=True)

    return action


def send_keystrokes(keys):
    """Create an action that sends keystrokes via AppleScript.

    Args:
        keys: AppleScript keystroke string, e.g. 'keystroke "v" using command down'
    """
    def action():
        subprocess.run([
            "osascript", "-e",
            f'tell application "System Events" to {keys}'
        ], capture_output=True)

    return action
