#!/bin/bash
# teardown_hid_gadget.sh
# Removes the USB HID Mouse gadget configuration created by setup_hid_gadget.sh.
# Must be run as root.
#
# Usage:
#   sudo ./teardown_hid_gadget.sh

set -e
shopt -s nullglob

GADGET_NAME="hid_mouse"
CONFIGFS_HOME="/sys/kernel/config"
GADGET_DIR="$CONFIGFS_HOME/usb_gadget/$GADGET_NAME"

info()  { echo "[INFO]  $*"; }
error() { echo "[ERROR] $*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || error "This script must be run as root (sudo)."

if [ ! -d "$GADGET_DIR" ]; then
    info "Gadget '$GADGET_NAME' is not configured – nothing to do."
    exit 0
fi

cd "$GADGET_DIR"

# Unbind from UDC first
info "Unbinding gadget from UDC..."
echo "" > UDC 2>/dev/null || true

# Remove function symlinks from all configs
info "Removing configuration links..."
for cfg in configs/*; do
    [ -d "$cfg" ] || continue
    for link in "$cfg"/*; do
        [ -L "$link" ] && rm -f "$link"
    done
done

# Remove configuration string directories then config directories
for cfg_str in configs/*/strings/*; do
    [ -d "$cfg_str" ] && rmdir "$cfg_str"
done
for cfg_strings in configs/*/strings; do
    [ -d "$cfg_strings" ] && rmdir "$cfg_strings"
done
for cfg in configs/*; do
    [ -d "$cfg" ] && rmdir "$cfg"
done

# Remove functions
info "Removing HID function..."
for fn in functions/*; do
    [ -d "$fn" ] && rmdir "$fn"
done

# Remove string descriptors
for str in strings/*; do
    [ -d "$str" ] && rmdir "$str"
done

# Remove top-level directories created by setup
for dir in configs functions strings; do
    [ -d "$dir" ] && rmdir "$dir"
done

# Remove gadget directory
cd /
rmdir "$GADGET_DIR"

info "Gadget '$GADGET_NAME' has been removed."
