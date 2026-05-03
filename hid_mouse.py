#!/usr/bin/env python3
"""
hid_mouse.py
------------
Low-level HID mouse report sender.

Writes 4-byte HID reports to the Linux USB gadget device node (/dev/hidg0)
that was created by setup_hid_gadget.sh.

Report layout (4 bytes, matches the report descriptor in setup_hid_gadget.sh):
    Byte 0 – Buttons   : bitmask  (bit 0 = left, bit 1 = right, bit 2 = middle)
    Byte 1 – X         : signed 8-bit, range -127..127  (relative, pixels)
    Byte 2 – Y         : signed 8-bit, range -127..127  (relative, pixels)
    Byte 3 – Wheel     : signed 8-bit, range -127..127  (scroll ticks)

Usage example:
    with HIDMouse() as m:
        m.move(10, -5)     # move right 10, up 5
        m.click('left')    # left-click
        m.scroll(-3)       # scroll down 3 ticks
"""

import os
import struct
import time

DEFAULT_DEVICE = "/dev/hidg0"

# Button bitmask constants
BTN_LEFT   = 0x01
BTN_RIGHT  = 0x02
BTN_MIDDLE = 0x04

_BUTTON_MAP = {
    "left":   BTN_LEFT,
    "right":  BTN_RIGHT,
    "middle": BTN_MIDDLE,
}


def _clamp(value: int, lo: int = -127, hi: int = 127) -> int:
    """Clamp *value* to the closed interval [lo, hi]."""
    return max(lo, min(hi, value))


class HIDMouse:
    """Controls a USB HID mouse gadget by writing reports to *device*."""

    def __init__(self, device: str = DEFAULT_DEVICE):
        self.device = device
        self._fd = None

    # ---------------------------------------------------------------------- #
    # Connection management
    # ---------------------------------------------------------------------- #

    def open(self) -> bool:
        """Open the HID gadget device for writing.

        Returns True on success, False on failure (error is printed to stderr).
        """
        try:
            self._fd = open(self.device, "wb", buffering=0)
            return True
        except PermissionError:
            print(
                f"[HIDMouse] Permission denied: {self.device}\n"
                "  Try running as root or add your user to the 'input' group\n"
                "  and install udev/99-hid-mouse.rules."
            )
            return False
        except FileNotFoundError:
            print(
                f"[HIDMouse] Device not found: {self.device}\n"
                "  Run  sudo ./setup_hid_gadget.sh  first, then connect the\n"
                "  USB-C cable to a host computer."
            )
            return False

    def close(self) -> None:
        """Release the HID gadget device."""
        if self._fd is not None:
            try:
                self._fd.close()
            except OSError:
                pass
            self._fd = None

    @property
    def is_open(self) -> bool:
        return self._fd is not None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *_):
        self.close()

    # ---------------------------------------------------------------------- #
    # Low-level report
    # ---------------------------------------------------------------------- #

    def send_report(
        self,
        buttons: int = 0,
        x: int = 0,
        y: int = 0,
        scroll: int = 0,
    ) -> bool:
        """Send a raw 4-byte HID mouse report.

        Args:
            buttons: Button bitmask (BTN_LEFT | BTN_RIGHT | BTN_MIDDLE).
            x:       Horizontal movement (-127 to 127).
            y:       Vertical movement   (-127 to 127).
            scroll:  Scroll wheel delta  (-127 to 127).

        Returns True on success, False on failure.
        """
        if self._fd is None:
            return False

        # Buttons byte is unsigned (0-7); clamp axes to signed byte range.
        report = struct.pack(
            "Bbbb",
            buttons & 0x07,
            _clamp(x),
            _clamp(y),
            _clamp(scroll),
        )
        try:
            self._fd.write(report)
            return True
        except OSError as exc:
            print(f"[HIDMouse] Write error: {exc}")
            return False

    # ---------------------------------------------------------------------- #
    # High-level helpers
    # ---------------------------------------------------------------------- #

    def move(self, x: int, y: int) -> bool:
        """Move the mouse cursor by (*x*, *y*) pixels (relative)."""
        return self.send_report(x=x, y=y)

    def click(self, button: str = "left", hold_seconds: float = 0.05) -> bool:
        """Press and release a mouse button.

        Args:
            button:       One of 'left', 'right', 'middle'.
            hold_seconds: How long to hold the button down before releasing.
        """
        mask = _BUTTON_MAP.get(button.lower())
        if mask is None:
            raise ValueError(f"Unknown button: {button!r}. Use 'left', 'right', or 'middle'.")
        ok = self.send_report(buttons=mask)
        time.sleep(hold_seconds)
        self.send_report(buttons=0)
        return ok

    def double_click(self, button: str = "left") -> None:
        """Perform a double-click."""
        self.click(button)
        time.sleep(0.05)
        self.click(button)

    def scroll(self, ticks: int) -> bool:
        """Scroll the mouse wheel.

        Positive *ticks* scrolls up; negative scrolls down.
        """
        return self.send_report(scroll=ticks)
