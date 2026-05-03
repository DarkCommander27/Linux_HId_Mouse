#!/bin/bash
# build_executable.sh
# Build a standalone executable for the Tkinter GUI using PyInstaller.

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_NAME="linux-hid-mouse"
DIST_DIR="$PROJECT_DIR/dist"
BUILD_DIR="$PROJECT_DIR/build/pyinstaller"

has_shared_python() {
    local candidate="$1"
    [ -n "$candidate" ] || return 1
    [ -x "$candidate" ] || return 1
    "$candidate" - <<'PY' >/dev/null 2>&1
import sysconfig
raise SystemExit(0 if sysconfig.get_config_var("Py_ENABLE_SHARED") else 1)
PY
}

has_tkinter() {
    local candidate="$1"
    [ -n "$candidate" ] || return 1
    [ -x "$candidate" ] || return 1
    "$candidate" - <<'PY' >/dev/null 2>&1
import tkinter
PY
}

pick_python() {
    local env_python="${PYTHON:-}"
    local candidates=()

    if [ -n "$env_python" ]; then
        candidates+=("$env_python")
    fi

    candidates+=("$(command -v python3 2>/dev/null || true)")
    candidates+=("/usr/bin/python3")

    local candidate
    for candidate in "${candidates[@]}"; do
        if has_shared_python "$candidate" && has_tkinter "$candidate"; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done

    return 1
}

cd "$PROJECT_DIR"

BUILD_PYTHON="$(pick_python || true)"

if [ -z "$BUILD_PYTHON" ]; then
    echo "[ERROR] No compatible Python interpreter was found for PyInstaller."
    echo "PyInstaller on Linux requires a Python build with shared libpython enabled"
    echo "and a working tkinter installation."
    echo "Try a distro Python such as /usr/bin/python3 plus the tkinter package"
    echo "(for example: sudo apt install python3-tk), or rebuild Python with --enable-shared."
    exit 1
fi

PYINSTALLER_CMD=()
if "$BUILD_PYTHON" -m PyInstaller --version >/dev/null 2>&1; then
    PYINSTALLER_CMD=("$BUILD_PYTHON" -m PyInstaller)
elif command -v pipx >/dev/null 2>&1; then
    PYINSTALLER_CMD=(pipx run --python "$BUILD_PYTHON" pyinstaller)
else
    echo "[ERROR] PyInstaller is not installed for $BUILD_PYTHON."
    echo "Install it with: $BUILD_PYTHON -m pip install --user pyinstaller"
    echo "Or install pipx and rerun this script."
    exit 1
fi

mkdir -p "$BUILD_DIR" "$DIST_DIR"

"${PYINSTALLER_CMD[@]}" \
    --noconfirm \
    --clean \
    --onefile \
    --windowed \
    --distpath "$DIST_DIR" \
    --workpath "$BUILD_DIR" \
    --specpath "$BUILD_DIR" \
    --name "$APP_NAME" \
    hid_mouse_gui.py

echo "[INFO] Built with: $BUILD_PYTHON"
echo "[INFO] Build complete: $PROJECT_DIR/dist/$APP_NAME"