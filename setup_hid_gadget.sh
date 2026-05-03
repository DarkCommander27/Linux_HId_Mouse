#!/bin/bash
# setup_hid_gadget.sh
# Configures the Linux USB-C port as a USB HID Mouse gadget so that the
# connected host computer sees this machine as a standard USB mouse.
#
# Requirements:
#   - Linux kernel with CONFIG_USB_GADGET, CONFIG_USB_CONFIGFS, and
#     CONFIG_USB_F_HID enabled (built-in or as modules).
#   - A USB Device Controller (UDC) – typically available on laptops /
#     SBCs that expose USB OTG / device-mode on their USB-C port.
#   - Must be run as root.
#
# Usage:
#   sudo ./setup_hid_gadget.sh [udc_name]
#
# If udc_name is omitted the first available UDC is used automatically.

set -e

GADGET_NAME="hid_mouse"
CONFIGFS_HOME="/sys/kernel/config"
GADGET_DIR="$CONFIGFS_HOME/usb_gadget/$GADGET_NAME"

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
info()  { echo "[INFO]  $*"; }
error() { echo "[ERROR] $*" >&2; exit 1; }

# --------------------------------------------------------------------------- #
# Root check
# --------------------------------------------------------------------------- #
[ "$(id -u)" -eq 0 ] || error "This script must be run as root (sudo)."

# --------------------------------------------------------------------------- #
# Already configured?
# --------------------------------------------------------------------------- #
if [ -d "$GADGET_DIR" ]; then
    info "Gadget '$GADGET_NAME' is already configured."
    info "Run teardown_hid_gadget.sh first to reconfigure."
    exit 0
fi

# --------------------------------------------------------------------------- #
# Load required kernel modules
# --------------------------------------------------------------------------- #
info "Loading kernel modules..."
modprobe libcomposite || error "Failed to load libcomposite. Is USB gadget support enabled in this kernel?"

# Mount configfs if not already mounted
if ! mountpoint -q "$CONFIGFS_HOME"; then
    mount -t configfs none "$CONFIGFS_HOME" || error "Failed to mount configfs."
fi

# --------------------------------------------------------------------------- #
# Create gadget
# --------------------------------------------------------------------------- #
info "Creating USB gadget '$GADGET_NAME'..."
mkdir -p "$GADGET_DIR"
cd "$GADGET_DIR"

# USB 2.0 device descriptor
echo 0x0200 > bcdUSB           # USB 2.0
echo 0x00   > bDeviceClass     # Defined at interface level
echo 0x00   > bDeviceSubClass
echo 0x00   > bDeviceProtocol
echo 0x0104 > idVendor         # Linux Foundation – multifunction composite
echo 0x0001 > idProduct        # HID mouse product
echo 0x0100 > bcdDevice        # Device release v1.0

# String descriptors (English)
mkdir -p strings/0x409
echo "HID_MOUSE_001"    > strings/0x409/serialnumber
echo "Linux HID Mouse"  > strings/0x409/manufacturer
echo "Linux HID Mouse"  > strings/0x409/product

# Configuration descriptor
mkdir -p configs/c.1/strings/0x409
echo "HID Mouse Configuration" > configs/c.1/strings/0x409/configuration
echo 250                       > configs/c.1/MaxPower   # 250 × 2 mA = 500 mA max

# --------------------------------------------------------------------------- #
# HID function – standard 4-byte boot-compatible mouse report
# --------------------------------------------------------------------------- #
# Report layout (4 bytes):
#   Byte 0 : Buttons – bit0=left, bit1=right, bit2=middle, bits3-7=padding
#   Byte 1 : X axis  – signed, -127..127 (relative movement)
#   Byte 2 : Y axis  – signed, -127..127 (relative movement)
#   Byte 3 : Wheel   – signed, -127..127 (scroll)
# --------------------------------------------------------------------------- #
mkdir -p functions/hid.usb0
echo 1 > functions/hid.usb0/protocol       # 1 = Mouse (boot protocol)
echo 1 > functions/hid.usb0/subclass       # 1 = Boot Interface Subclass
echo 4 > functions/hid.usb0/report_length  # 4 bytes per report

# HID report descriptor – mouse with 3 buttons + X/Y/Wheel axes
# (conforms to the USB HID Usage Tables 1.12, page 27)
#
# Byte sequence (hex):
#   05 01        Usage Page (Generic Desktop)
#   09 02        Usage (Mouse)
#   a1 01        Collection (Application)
#   09 01          Usage (Pointer)
#   a1 00          Collection (Physical)
#   05 09            Usage Page (Button)
#   19 01            Usage Minimum (Button 1)
#   29 03            Usage Maximum (Button 3)
#   15 00            Logical Minimum (0)
#   25 01            Logical Maximum (1)
#   95 03            Report Count (3)
#   75 01            Report Size (1)
#   81 02            Input (Data,Var,Abs)
#   95 01            Report Count (1) – padding
#   75 05            Report Size (5)
#   81 03            Input (Const)    – padding
#   05 01            Usage Page (Generic Desktop)
#   09 30            Usage (X)
#   09 31            Usage (Y)
#   09 38            Usage (Wheel)
#   15 81            Logical Minimum (-127)
#   25 7f            Logical Maximum (127)
#   75 08            Report Size (8)
#   95 03            Report Count (3)
#   81 06            Input (Data,Var,Rel)
#   c0             End Collection
#   c0           End Collection
echo -ne '\x05\x01\x09\x02\xa1\x01\x09\x01\xa1\x00\x05\x09\x19\x01\x29\x03\x15\x00\x25\x01\x95\x03\x75\x01\x81\x02\x95\x01\x75\x05\x81\x03\x05\x01\x09\x30\x09\x31\x09\x38\x15\x81\x25\x7f\x75\x08\x95\x03\x81\x06\xc0\xc0' \
    > functions/hid.usb0/report_desc

# Link function into the configuration
ln -s functions/hid.usb0 configs/c.1/

# --------------------------------------------------------------------------- #
# Bind to a UDC
# --------------------------------------------------------------------------- #
UDC="${1:-}"
if [ -z "$UDC" ]; then
    UDC=$(find /sys/class/udc -mindepth 1 -maxdepth 1 -printf '%f\n' 2>/dev/null | head -1)
fi

if [ -z "$UDC" ]; then
    error "No USB Device Controller found in /sys/class/udc.\n" \
          "Make sure your USB-C port supports device / OTG mode and the\n" \
          "appropriate UDC driver is loaded (e.g. dwc3, musb, chipidea)."
fi

info "Binding gadget to UDC: $UDC"
echo "$UDC" > UDC || error "Failed to bind gadget to UDC: $UDC"

info "Done! HID mouse gadget is active."
info "HID device node: /dev/hidg0"
info "Connect the USB-C cable to a host computer – it should enumerate as a mouse."
info "Run the GUI with: python3 hid_mouse_gui.py"
