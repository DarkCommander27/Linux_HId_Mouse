# Linux HID Mouse

Turn any Linux laptop or single-board computer with a USB-C port (that
supports USB Device / OTG mode) into a USB HID mouse. The host computer
that you plug into sees the Linux machine as a standard USB mouse – not as
a PC – and can be controlled through a graphical user interface running on
the Linux device.

```
  ┌─────────────────────┐           USB-C cable           ┌──────────────────┐
  │  Linux Machine       │ ──────────────────────────────► │  Host Computer   │
  │  (acts as USB mouse) │                                 │  (Windows/macOS/ │
  │  hid_mouse_gui.py   │◄──  control via GUI             │   Linux/etc.)    │
  └─────────────────────┘                                  └──────────────────┘
```

---

## Requirements

| Requirement | Details |
|---|---|
| **Linux kernel** | `CONFIG_USB_GADGET`, `CONFIG_USB_CONFIGFS`, `CONFIG_USB_F_HID` (built-in or as modules) |
| **UDC driver** | `dwc3`, `musb`, `chipidea`, or similar – depends on your hardware |
| **Python** | 3.8 or later (only the standard library is used) |
| **Root access** | Required for `setup_hid_gadget.sh` and `teardown_hid_gadget.sh` |

### Tested hardware

- Raspberry Pi Zero 2 W / Pi 4 (via the micro-USB / USB-C OTG port)
- Laptops with Intel/AMD USB-C controllers that expose a UDC
  (check `ls /sys/class/udc` – at least one entry must exist)

---

## Quick start

### 1 – Clone the repository

```bash
git clone https://github.com/DarkCommander27/Linux_HId_Mouse.git
cd Linux_HId_Mouse
```

### 2 – Set up the USB HID gadget (run once per boot)

```bash
sudo ./setup_hid_gadget.sh
```

The script will:
1. Load the `libcomposite` kernel module.
2. Create a USB gadget in `configfs` that presents itself as a USB HID
   mouse to the host.
3. Bind the gadget to the first available UDC (USB Device Controller).

After the script finishes, `/dev/hidg0` will appear.

> **Tip:** You can pass a specific UDC name as the first argument if your
> system has multiple UDCs:
> ```bash
> sudo ./setup_hid_gadget.sh fe980000.usb
> ```

### 3 – Install udev rules (one-time, optional but recommended)

This allows you to run the GUI without `sudo`:

```bash
sudo cp udev/99-hid-mouse.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
sudo usermod -aG input "$USER"
# Log out and back in, or run: newgrp input
```

### 4 – Connect the USB-C cable

Plug the USB-C cable into the Linux machine's OTG/device-mode port and
connect the other end to the host computer. The host should enumerate the
device as a **USB mouse**.

### 5 – Launch the GUI

```bash
python3 hid_mouse_gui.py
```

If you skipped the udev step, run with `sudo`:

```bash
sudo python3 hid_mouse_gui.py
```

---

## GUI overview

```
┌──────────────────────────────────┐
│  🖱  Linux HID Mouse             │
│       USB-C Gadget Controller    │
├──────────────────────────────────┤
│ Status: Connected ✓  [Disconnect]│
├──────────────────────────────────┤
│  MOVEMENT                        │
│            [▲]                   │
│       [◄]  ⊙  [►]               │
│            [▼]                   │
│  Speed: ──●─────────── 10        │
├──────────────────────────────────┤
│  MOUSE BUTTONS                   │
│  [Left Click] [Middle] [Right]   │
│        [Double Click (Left)]     │
├──────────────────────────────────┤
│  SCROLL                          │
│  [▲ Scroll Up]  [▼ Scroll Down]  │
├──────────────────────────────────┤
│ Arrow keys: move | Enter: click  │
└──────────────────────────────────┘
```

| Control | Action |
|---|---|
| Arrow buttons / keyboard arrows | Move the mouse cursor (hold for continuous movement) |
| Speed slider / `+` `-` keys | Adjust movement speed (1–50) |
| Left / Middle / Right Click | Press and release that mouse button |
| Double Click | Two left-clicks in quick succession |
| Scroll Up / Down | Rotate the scroll wheel |
| Enter | Left-click |
| Connect / Disconnect | Open or close `/dev/hidg0` |

---

## Tear down

To remove the HID gadget configuration:

```bash
sudo ./teardown_hid_gadget.sh
```

---

## File overview

| File | Description |
|---|---|
| `setup_hid_gadget.sh` | Configures Linux as a USB HID mouse gadget via `configfs` |
| `teardown_hid_gadget.sh` | Removes the gadget configuration |
| `hid_mouse.py` | Python module – writes HID reports to `/dev/hidg0` |
| `hid_mouse_gui.py` | Tkinter GUI for controlling the mouse |
| `udev/99-hid-mouse.rules` | udev rule for non-root access to `/dev/hidg0` |

---

## HID report format

Each mouse action is encoded as a **4-byte HID report**:

| Byte | Field | Range | Description |
|---|---|---|---|
| 0 | Buttons | 0–7 | Bit 0=Left, Bit 1=Right, Bit 2=Middle |
| 1 | X | −127..127 | Horizontal movement (relative) |
| 2 | Y | −127..127 | Vertical movement (relative) |
| 3 | Wheel | −127..127 | Scroll wheel (positive = up) |

---

## Troubleshooting

**`/dev/hidg0` does not appear**

- Verify that your kernel has HID gadget support:
  ```bash
  modinfo usb_f_hid
  ```
- Check `ls /sys/class/udc` – at least one entry must exist.
- Some USB-C ports are host-only (no OTG). Check your hardware specs.

**Permission denied on `/dev/hidg0`**

- Install the udev rule (step 3 above).
- Or simply run the GUI with `sudo`.

**Host does not detect a mouse**

- Unplug and re-plug the cable after running `setup_hid_gadget.sh`.
- Some hosts need a moment to enumerate. Check Device Manager (Windows)
  or `lsusb` (Linux) on the host side.

---

## License

MIT
