"""
Mountain DisplayPad USB HID communication layer.

Protocol reverse-engineered from JeLuF/mountain-displaypad (Node.js).
Two HID interfaces are used:
  - Interface 1: Display data (image transfer)
  - Interface 3: Device control (init, image commands, button input)
"""

import hid
import time
import threading
from collections import deque
from PIL import Image

VENDOR_ID = 0x3282
PRODUCT_ID = 0x0009

ICON_SIZE = 102
NUM_KEYS = 12
NUM_KEYS_PER_ROW = 6
NUM_TOTAL_PIXELS = ICON_SIZE * ICON_SIZE  # 10404
PIXEL_DATA_SIZE = NUM_TOTAL_PIXELS * 3     # 31212 (BGR, 3 bytes/pixel)
PACKET_SIZE = 31438                         # padded pixel buffer
HEADER_SIZE = 306                           # image header (all zeros)
CHUNK_SIZE = 1024

# 64-byte init message (sent to interface 3)
INIT_MSG = bytes.fromhex(
    "00118000000100000000000000000000"
    "00000000000000000000000000000000"
    "00000000000000000000000000000000"
    "00000000000000000000000000000000"
)

# 64-byte image transfer start message (sent to interface 3)
# Byte 5 (0xFF) is overwritten with key index before sending
IMG_MSG = bytes.fromhex(
    "0021000000FF3d0000656500000000000000000000000000000000000000000000"
    "0000000000000000000000000000000000000000000000000000000000000000"
)

# Button bit masks
# data[42] bits for keys 1-7, data[47] bits for keys 8-12
KEY_MASKS = {
    1:  (42, 0x02),
    2:  (42, 0x04),
    3:  (42, 0x08),
    4:  (42, 0x10),
    5:  (42, 0x20),
    6:  (42, 0x40),
    7:  (42, 0x80),
    8:  (47, 0x01),
    9:  (47, 0x02),
    10: (47, 0x04),
    11: (47, 0x08),
    12: (47, 0x10),
}


def find_displaypad_interfaces():
    """Find the DisplayPad HID device interfaces.

    Returns:
        dict with 'display' (interface 1) and 'control' (interface 3) device info,
        or None if not found.
    """
    devices = hid.enumerate(VENDOR_ID, PRODUCT_ID)
    display_dev = None
    control_dev = None

    for dev in devices:
        if dev["interface_number"] == 1:
            display_dev = dev
        elif dev["interface_number"] == 3:
            control_dev = dev

    if display_dev and control_dev:
        return {"display": display_dev, "control": control_dev}
    return None


def rgb_to_bgr_buffer(image):
    """Convert a PIL Image to a BGR byte buffer for the DisplayPad.

    Args:
        image: PIL Image, will be resized to 102x102 if needed.

    Returns:
        bytes of length PACKET_SIZE with BGR pixel data.
    """
    img = image.convert("RGB").resize((ICON_SIZE, ICON_SIZE), Image.LANCZOS)
    pixels = img.load()

    buf = bytearray(PACKET_SIZE)
    offset = 0
    for y in range(ICON_SIZE):
        for x in range(ICON_SIZE):
            r, g, b = pixels[x, y]
            buf[offset] = b
            buf[offset + 1] = g
            buf[offset + 2] = r
            offset += 3

    return bytes(buf)


def solid_color_buffer(r, g, b):
    """Create a solid color BGR buffer for one key."""
    buf = bytearray(PACKET_SIZE)
    offset = 0
    for _ in range(NUM_TOTAL_PIXELS):
        buf[offset] = b
        buf[offset + 1] = g
        buf[offset + 2] = r
        offset += 3
    return bytes(buf)


class DisplayPad:
    """Interface to the Mountain DisplayPad device."""

    def __init__(self):
        self.display = None   # HID handle for interface 1 (display)
        self.control = None   # HID handle for interface 3 (control)
        self.initialized = False
        self._key_state = [False] * (NUM_KEYS + 1)  # 1-based indexing
        self._on_key_down = None
        self._on_key_up = None
        self._listener_thread = None
        self._running = False
        self._queue = deque()
        self._transferring = False
        self._lock = threading.Lock()

    def open(self):
        """Open connection to the DisplayPad."""
        info = find_displaypad_interfaces()
        if info is None:
            raise RuntimeError(
                "DisplayPad not found. Check USB connection and permissions.\n"
                f"Looking for VID={VENDOR_ID:#06x} PID={PRODUCT_ID:#06x}"
            )

        self.display = hid.device()
        self.display.open_path(info["display"]["path"])

        self.control = hid.device()
        self.control.open_path(info["control"]["path"])

        # Set non-blocking on control for reading
        self.control.set_nonblocking(False)

        self._send_init()

    def _send_init(self):
        """Send initialization message and wait for acknowledgment."""
        self.control.write(INIT_MSG)

        # Wait for init response (data[0] == 0x11)
        timeout = time.time() + 3.0
        while time.time() < timeout:
            data = self.control.read(64, timeout_ms=500)
            if data and data[0] == 0x11:
                self.initialized = True
                return

        raise RuntimeError("DisplayPad did not respond to initialization")

    def close(self):
        """Close all device handles."""
        self._running = False
        if self._listener_thread:
            self._listener_thread.join(timeout=2.0)
        if self.display:
            self.display.close()
            self.display = None
        if self.control:
            self.control.close()
            self.control = None
        self.initialized = False

    def set_key_image(self, key_index, image):
        """Set the image for a key (0-based index, 0-11).

        Args:
            key_index: int 0-11
            image: PIL Image (any size, will be resized to 102x102)
        """
        pixel_data = rgb_to_bgr_buffer(image)
        self._enqueue_transfer(key_index, pixel_data)

    def set_key_color(self, key_index, r, g, b):
        """Fill a key with a solid color (0-based index)."""
        pixel_data = solid_color_buffer(r, g, b)
        self._enqueue_transfer(key_index, pixel_data)

    def clear_key(self, key_index):
        """Clear a key (set to black)."""
        self.set_key_color(key_index, 0, 0, 0)

    def clear_all(self):
        """Clear all keys."""
        for i in range(NUM_KEYS):
            self.clear_key(i)

    def _enqueue_transfer(self, key_index, pixel_data):
        """Add an image transfer to the queue."""
        with self._lock:
            self._queue.append((key_index, pixel_data))
            if not self._transferring:
                self._process_queue()

    def _process_queue(self):
        """Process the next item in the transfer queue."""
        if not self._queue:
            self._transferring = False
            return

        self._transferring = True
        key_index, pixel_data = self._queue.popleft()
        self._transfer_image(key_index, pixel_data)

    def _transfer_image(self, key_index, pixel_data):
        """Execute the image transfer protocol for one key.

        Protocol:
        1. Send IMG_MSG with key_index to control interface
        2. Wait for ACK (data[0]==0x21, data[1]==0x00, data[2]==0x00)
        3. Send pixel data in 1024-byte chunks to display interface
        4. Send full payload again to display interface
        5. Wait for completion (data[0]==0x21, data[1]==0x00, data[2]==0xff)
        """
        # Step 1: Send IMG_MSG
        msg = bytearray(IMG_MSG)
        msg[5] = key_index
        self.control.write(bytes(msg))

        # Step 2: Wait for ACK
        timeout = time.time() + 3.0
        acked = False
        while time.time() < timeout:
            data = self.control.read(64, timeout_ms=500)
            if data and data[0] == 0x21:
                if data[1] == 0x00 and data[2] == 0x00:
                    acked = True
                    break

        if not acked:
            # Timeout - reset and retry
            self._send_init()
            with self._lock:
                self._process_queue()
            return

        # Step 3: Send pixel data in chunks
        header = bytes(HEADER_SIZE)  # 306 zero bytes
        full_data = header + pixel_data

        for i in range(0, len(full_data), CHUNK_SIZE):
            chunk = full_data[i:i + CHUNK_SIZE]
            self.display.write(b'\x00' + chunk)

        # Step 4: Send full payload again (no report ID prefix)
        self.display.write(full_data)

        # Step 5: Wait for completion
        timeout = time.time() + 5.0
        while time.time() < timeout:
            data = self.control.read(64, timeout_ms=500)
            if data and data[0] == 0x21:
                if data[1] == 0x00 and data[2] == 0xff:
                    break

        # Process next in queue
        with self._lock:
            self._process_queue()

    def on_key_down(self, callback):
        """Register callback for key press. callback(key_index) where key_index is 1-12."""
        self._on_key_down = callback

    def on_key_up(self, callback):
        """Register callback for key release. callback(key_index) where key_index is 1-12."""
        self._on_key_up = callback

    def start_listening(self):
        """Start listening for button events in a background thread."""
        self._running = True
        self._listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._listener_thread.start()

    def _listen_loop(self):
        """Background thread that reads button events from the control interface."""
        while self._running:
            try:
                data = self.control.read(64, timeout_ms=100)
                if not data:
                    continue

                if data[0] == 0x01:
                    self._process_buttons(data)

            except Exception:
                if self._running:
                    time.sleep(0.1)

    def _process_buttons(self, data):
        """Process button state from HID report."""
        for key_num, (byte_idx, mask) in KEY_MASKS.items():
            if byte_idx < len(data):
                pressed = bool(data[byte_idx] & mask)
                was_pressed = self._key_state[key_num]

                if pressed and not was_pressed:
                    self._key_state[key_num] = True
                    if self._on_key_down:
                        self._on_key_down(key_num)
                elif not pressed and was_pressed:
                    self._key_state[key_num] = False
                    if self._on_key_up:
                        self._on_key_up(key_num)
