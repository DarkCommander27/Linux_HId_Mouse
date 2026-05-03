#!/usr/bin/env python3
"""
hid_mouse_gui.py
----------------
Graphical front-end for the Linux HID Mouse gadget.

Requires:
    - setup_hid_gadget.sh to have been run as root beforehand.
    - Python 3 standard library only (tkinter is included with most distros).

Usage:
    python3 hid_mouse_gui.py
    # or, if /dev/hidg0 is not yet accessible without root:
    sudo python3 hid_mouse_gui.py
"""

import os
import sys
import threading
import time
import tkinter as tk
from typing import Optional
from tkinter import messagebox

# Allow running from any working directory
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from hid_mouse import HIDMouse  # noqa: E402 – local import after path fix

# --------------------------------------------------------------------------- #
# Colour palette
# --------------------------------------------------------------------------- #
BG_DARK    = "#1e1e2e"
BG_PANEL   = "#2a2a3e"
BG_BUTTON  = "#3a3a50"
BG_ACCENT  = "#7c3aed"       # purple accent
BG_GREEN   = "#059669"
BG_RED     = "#dc2626"
BG_GREY    = "#4b5563"
FG_WHITE   = "#f8fafc"
FG_DIM     = "#94a3b8"
FG_ACTIVE  = "#a5f3fc"       # cyan
FG_OK      = "#4ade80"       # green
FG_ERR     = "#f87171"       # red

FONT_TITLE  = ("Helvetica", 17, "bold")
FONT_LABEL  = ("Helvetica", 9)
FONT_BTN    = ("Helvetica", 13)
FONT_STATUS = ("Helvetica", 10, "bold")

# --------------------------------------------------------------------------- #
# Main GUI class
# --------------------------------------------------------------------------- #

class HIDMouseGUI:
    """Main application window."""

    # Continuous-movement repeat interval (seconds)
    _MOVE_INTERVAL = 0.04

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Linux HID Mouse")
        self.root.resizable(False, False)
        self.root.configure(bg=BG_DARK)

        self.mouse = HIDMouse()
        self._connected = False
        self._move_speed = tk.IntVar(value=10)
        self._moving = False
        self._move_thread: Optional[threading.Thread] = None

        self._build_ui()
        self._try_connect()

        # Bind window-close to graceful shutdown
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------------------------------------------------------------------- #
    # UI construction
    # ---------------------------------------------------------------------- #

    def _build_ui(self) -> None:
        self._build_header()
        self._build_status_bar()
        _hline(self.root)
        self._build_movement_section()
        _hline(self.root)
        self._build_buttons_section()
        _hline(self.root)
        self._build_scroll_section()
        _hline(self.root)
        self._build_footer()
        self._bind_keyboard()

    def _build_header(self) -> None:
        hdr = tk.Frame(self.root, bg="#16162a", pady=12)
        hdr.pack(fill=tk.X)
        tk.Label(
            hdr,
            text="🖱  Linux HID Mouse",
            font=FONT_TITLE,
            bg="#16162a",
            fg=FG_ACTIVE,
        ).pack()
        tk.Label(
            hdr,
            text="USB-C Gadget Controller",
            font=FONT_LABEL,
            bg="#16162a",
            fg=FG_DIM,
        ).pack()

    def _build_status_bar(self) -> None:
        bar = tk.Frame(self.root, bg=BG_DARK, padx=14, pady=6)
        bar.pack(fill=tk.X)

        tk.Label(bar, text="Status:", font=FONT_LABEL, bg=BG_DARK, fg=FG_DIM).pack(
            side=tk.LEFT
        )
        self._status_var = tk.StringVar(value="Disconnected")
        self._status_lbl = tk.Label(
            bar,
            textvariable=self._status_var,
            font=FONT_STATUS,
            bg=BG_DARK,
            fg=FG_ERR,
        )
        self._status_lbl.pack(side=tk.LEFT, padx=6)

        self._conn_btn = tk.Button(
            bar,
            text="Connect",
            command=self._toggle_connect,
            bg=BG_ACCENT,
            fg=FG_WHITE,
            relief=tk.FLAT,
            padx=12,
            pady=3,
            cursor="hand2",
            font=FONT_LABEL,
            activebackground="#6d28d9",
            activeforeground=FG_WHITE,
        )
        self._conn_btn.pack(side=tk.RIGHT)

    def _build_movement_section(self) -> None:
        outer = tk.Frame(self.root, bg=BG_DARK, padx=14, pady=10)
        outer.pack(fill=tk.X)

        _section_label(outer, "Movement")

        grid = tk.Frame(outer, bg=BG_DARK)
        grid.pack()

        # Arrow buttons layout:
        #       [  ▲  ]
        # [◄]   [ ⊙ ]   [►]
        #       [  ▼  ]
        arrow_cfg = dict(
            bg=BG_BUTTON, fg=FG_WHITE, relief=tk.FLAT,
            font=FONT_BTN, width=3, height=1, cursor="hand2",
            activebackground=BG_ACCENT, activeforeground=FG_WHITE,
        )

        up_btn    = tk.Button(grid, text="▲", **arrow_cfg)
        left_btn  = tk.Button(grid, text="◄", **arrow_cfg)
        center    = tk.Label(grid, text="⊙", bg=BG_DARK, fg=BG_GREY, font=FONT_BTN)
        right_btn = tk.Button(grid, text="►", **arrow_cfg)
        down_btn  = tk.Button(grid, text="▼", **arrow_cfg)

        up_btn.grid(   row=0, column=1, padx=3, pady=3)
        left_btn.grid( row=1, column=0, padx=3, pady=3)
        center.grid(   row=1, column=1, padx=3, pady=3)
        right_btn.grid(row=1, column=2, padx=3, pady=3)
        down_btn.grid( row=2, column=1, padx=3, pady=3)

        # Bind press/release for continuous movement
        for btn, dx, dy in [
            (up_btn,    0, -1),
            (down_btn,  0,  1),
            (left_btn, -1,  0),
            (right_btn, 1,  0),
        ]:
            btn.bind("<ButtonPress-1>",   lambda e, x=dx, y=dy: self._start_move(x, y))
            btn.bind("<ButtonRelease-1>", lambda e: self._stop_move())

        # Speed control
        spd = tk.Frame(outer, bg=BG_DARK)
        spd.pack(pady=(8, 0))
        tk.Label(spd, text="Speed:", font=FONT_LABEL, bg=BG_DARK, fg=FG_DIM).pack(
            side=tk.LEFT
        )
        tk.Scale(
            spd,
            from_=1, to=50,
            orient=tk.HORIZONTAL,
            variable=self._move_speed,
            length=170,
            bg=BG_DARK, fg=FG_WHITE,
            highlightthickness=0,
            troughcolor=BG_BUTTON,
            activebackground=BG_ACCENT,
            showvalue=True,
        ).pack(side=tk.LEFT, padx=6)

    def _build_buttons_section(self) -> None:
        outer = tk.Frame(self.root, bg=BG_DARK, padx=14, pady=10)
        outer.pack(fill=tk.X)

        _section_label(outer, "Mouse Buttons")

        row = tk.Frame(outer, bg=BG_DARK)
        row.pack()

        btn_cfg = dict(
            relief=tk.FLAT, fg=FG_WHITE, padx=14, pady=8,
            cursor="hand2", font=FONT_LABEL, width=9,
            activeforeground=FG_WHITE,
        )

        tk.Button(
            row, text="Left\nClick",
            bg=BG_GREEN, activebackground="#047857",
            command=lambda: self._click("left"),
            **btn_cfg,
        ).pack(side=tk.LEFT, padx=4)

        tk.Button(
            row, text="Middle\nClick",
            bg=BG_GREY, activebackground="#374151",
            command=lambda: self._click("middle"),
            **btn_cfg,
        ).pack(side=tk.LEFT, padx=4)

        tk.Button(
            row, text="Right\nClick",
            bg=BG_RED, activebackground="#b91c1c",
            command=lambda: self._click("right"),
            **btn_cfg,
        ).pack(side=tk.LEFT, padx=4)

        # Double-click shortcut
        dbl_row = tk.Frame(outer, bg=BG_DARK)
        dbl_row.pack(pady=(6, 0))
        tk.Button(
            dbl_row, text="Double Click (Left)",
            bg=BG_BUTTON, fg=FG_WHITE, relief=tk.FLAT,
            padx=14, pady=5, cursor="hand2", font=FONT_LABEL,
            activebackground=BG_ACCENT, activeforeground=FG_WHITE,
            command=lambda: self._double_click("left"),
        ).pack()

    def _build_scroll_section(self) -> None:
        outer = tk.Frame(self.root, bg=BG_DARK, padx=14, pady=10)
        outer.pack(fill=tk.X)

        _section_label(outer, "Scroll")

        row = tk.Frame(outer, bg=BG_DARK)
        row.pack()

        scroll_cfg = dict(
            bg=BG_BUTTON, fg=FG_WHITE, relief=tk.FLAT,
            padx=20, pady=6, cursor="hand2", font=FONT_LABEL, width=12,
            activebackground=BG_ACCENT, activeforeground=FG_WHITE,
        )

        tk.Button(
            row, text="▲  Scroll Up",
            command=lambda: self._scroll(3),
            **scroll_cfg,
        ).pack(side=tk.LEFT, padx=4)

        tk.Button(
            row, text="▼  Scroll Down",
            command=lambda: self._scroll(-3),
            **scroll_cfg,
        ).pack(side=tk.LEFT, padx=4)

    def _build_footer(self) -> None:
        ftr = tk.Frame(self.root, bg="#16162a", pady=5)
        ftr.pack(fill=tk.X)
        tk.Label(
            ftr,
            text="Arrow keys: move  |  Enter: left-click  |  +/-: speed",
            font=FONT_LABEL,
            bg="#16162a",
            fg=FG_DIM,
        ).pack()

    def _bind_keyboard(self) -> None:
        spd = self._move_speed

        def on_key_press(event: tk.Event) -> None:
            key = event.keysym
            s = spd.get()
            if key == "Left":
                self._start_move(-1, 0)
            elif key == "Right":
                self._start_move(1, 0)
            elif key == "Up":
                self._start_move(0, -1)
            elif key == "Down":
                self._start_move(0, 1)
            elif key == "Return":
                self._click("left")
            elif key == "plus" or key == "equal":
                spd.set(min(50, s + 1))
            elif key == "minus":
                spd.set(max(1, s - 1))

        def on_key_release(event: tk.Event) -> None:
            if event.keysym in ("Left", "Right", "Up", "Down"):
                self._stop_move()

        self.root.bind("<KeyPress>",   on_key_press)
        self.root.bind("<KeyRelease>", on_key_release)

    # ---------------------------------------------------------------------- #
    # Connection management
    # ---------------------------------------------------------------------- #

    def _try_connect(self) -> None:
        if self.mouse.open():
            self._set_connected(True)

    def _toggle_connect(self) -> None:
        if self._connected:
            self.mouse.close()
            self._set_connected(False)
        else:
            if self.mouse.open():
                self._set_connected(True)
            else:
                messagebox.showerror(
                    "Connection Failed",
                    "Could not open the HID device.\n\n"
                    "Please make sure:\n"
                    "  1. setup_hid_gadget.sh has been run as root.\n"
                    "  2. A USB-C cable connects this machine to a host.\n"
                    "  3. /dev/hidg0 exists and you have write permission\n"
                    "     (install udev/99-hid-mouse.rules if needed).",
                )

    def _set_connected(self, connected: bool) -> None:
        self._connected = connected
        if connected:
            self._status_var.set("Connected ✓")
            self._status_lbl.configure(fg=FG_OK)
            self._conn_btn.configure(text="Disconnect", bg=BG_RED, activebackground="#b91c1c")
        else:
            self._status_var.set("Disconnected")
            self._status_lbl.configure(fg=FG_ERR)
            self._conn_btn.configure(text="Connect", bg=BG_ACCENT, activebackground="#6d28d9")

    def _handle_device_failure(self) -> None:
        if not self._connected:
            return
        self._stop_move()
        self.mouse.close()
        self._set_connected(False)
        messagebox.showerror(
            "Device Disconnected",
            "The HID device is no longer writable.\n\n"
            "Reconnect the USB gadget and press Connect again.",
        )

    def _run_async_action(self, action) -> None:
        def _worker() -> None:
            if not action():
                self.root.after(0, self._handle_device_failure)

        threading.Thread(target=_worker, daemon=True).start()

    # ---------------------------------------------------------------------- #
    # Movement helpers
    # ---------------------------------------------------------------------- #

    def _start_move(self, dx: int, dy: int) -> None:
        self._stop_move()
        self._moving = True

        def _loop() -> None:
            while self._moving:
                spd = self._move_speed.get()
                self._send_move(dx * spd, dy * spd)
                time.sleep(self._MOVE_INTERVAL)

        self._move_thread = threading.Thread(target=_loop, daemon=True)
        self._move_thread.start()

    def _stop_move(self) -> None:
        self._moving = False

    def _send_move(self, x: int, y: int) -> None:
        if self._connected and not self.mouse.move(x, y):
            self.root.after(0, self._handle_device_failure)

    # ---------------------------------------------------------------------- #
    # Button / scroll helpers
    # ---------------------------------------------------------------------- #

    def _click(self, button: str) -> None:
        if self._connected:
            self._run_async_action(lambda: self.mouse.click(button))

    def _double_click(self, button: str) -> None:
        if self._connected:
            self._run_async_action(lambda: self.mouse.double_click(button))

    def _scroll(self, ticks: int) -> None:
        if self._connected and not self.mouse.scroll(ticks):
            self._handle_device_failure()

    # ---------------------------------------------------------------------- #
    # Clean shutdown
    # ---------------------------------------------------------------------- #

    def _on_close(self) -> None:
        self._stop_move()
        self.mouse.close()
        self.root.destroy()


# --------------------------------------------------------------------------- #
# UI utility helpers
# --------------------------------------------------------------------------- #

def _hline(parent: tk.Widget) -> None:
    tk.Frame(parent, bg="#3a3a50", height=1).pack(fill=tk.X, padx=12)


def _section_label(parent: tk.Widget, text: str) -> None:
    tk.Label(
        parent,
        text=text.upper(),
        font=FONT_LABEL,
        bg=BG_DARK,
        fg=FG_DIM,
    ).pack(anchor=tk.W, pady=(0, 6))


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #

def main() -> int:
    auto_exit_ms = os.environ.get("HID_MOUSE_AUTO_EXIT_MS")

    if sys.platform.startswith("linux"):
        has_display = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
        if not has_display:
            print(
                "[ERROR] No graphical display session was detected.\n"
                "Run linux-hid-mouse from a local desktop session, or launch it\n"
                "over X11 forwarding / Xvfb if you are working headlessly."
            )
            return 1

    try:
        root = tk.Tk()
    except tk.TclError as exc:
        print(f"[ERROR] Failed to initialize the GUI: {exc}")
        return 1

    HIDMouseGUI(root)

    if auto_exit_ms:
        try:
            delay_ms = max(1, int(auto_exit_ms))
        except ValueError:
            print(f"[ERROR] Invalid HID_MOUSE_AUTO_EXIT_MS value: {auto_exit_ms!r}")
            root.destroy()
            return 1
        root.after(delay_ms, root.destroy)

    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
