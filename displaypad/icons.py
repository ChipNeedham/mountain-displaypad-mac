"""Icon generation for DisplayPad keys.

Generates 102x102 pixel icons with text labels, symbols, or from image files.
Uses extracted icons from Mountain Base Camp when available.
"""

from PIL import Image, ImageDraw, ImageFont
import os

ICON_SIZE = 102
ICONS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "icons")

# Map of spotify actions to their original Mountain icon files
SPOTIFY_ICON_MAP = {
    "play_pause": "01_PlayPause.png",
    "previous": "02_previous.png",
    "next": "03_next.png",
    "vol_up": "13_volume_plus.png",
    "vol_down": "14_volume_down.png",
    "now_playing": "12_Song_info.jpg",
}


def create_text_icon(text, bg_color=(30, 30, 30), text_color=(255, 255, 255), font_size=16):
    """Create a simple text icon."""
    img = Image.new("RGB", (ICON_SIZE, ICON_SIZE), bg_color)
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("/System/Library/Fonts/SFNSMono.ttf", font_size)
    except (OSError, IOError):
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
        except (OSError, IOError):
            font = ImageFont.load_default()

    lines = text.split("\n")
    total_height = len(lines) * (font_size + 4)
    y_start = (ICON_SIZE - total_height) // 2

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        x = (ICON_SIZE - tw) // 2
        y = y_start + i * (font_size + 4)
        draw.text((x, y), line, fill=text_color, font=font)

    return img


def load_icon(path):
    """Load an icon from a file path, resize to 102x102."""
    img = Image.open(path).convert("RGB")
    return img.resize((ICON_SIZE, ICON_SIZE), Image.LANCZOS)


def create_spotify_icon(label, action=None, bg_color=(30, 215, 96)):
    """Create a Spotify-themed icon.

    If action maps to an extracted Mountain icon, use that instead.
    """
    if action and action in SPOTIFY_ICON_MAP:
        icon_path = os.path.join(ICONS_DIR, SPOTIFY_ICON_MAP[action])
        if os.path.exists(icon_path):
            return load_icon(icon_path)

    return create_text_icon(label, bg_color=bg_color, text_color=(0, 0, 0), font_size=14)


def create_api_icon(label, bg_color=(66, 133, 244)):
    """Create an API-themed icon."""
    return create_text_icon(label, bg_color=bg_color, text_color=(255, 255, 255), font_size=14)
