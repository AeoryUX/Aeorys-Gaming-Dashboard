#!/usr/bin/env bash
set -euo pipefail
if ! command -v python3 >/dev/null 2>&1; then
    echo 'Missing Python 3 (3.10+ required); no third-party Python packages are needed.' >&2
    exit 1
fi
python3 -c 'import sys; assert sys.version_info >= (3, 10), "Python 3.10+ required"'
if ! command -v qs >/dev/null 2>&1; then
    echo 'Missing Quickshell (qs). Install it using https://quickshell.org/docs/guide/install-setup/' >&2
    exit 1
fi
qs --version
if [[ -z "${WAYLAND_DISPLAY:-}" && -z "${DISPLAY:-}" ]]; then
    echo 'No graphical session detected. Run the dashboard in your desktop session.' >&2
    exit 1
fi
echo 'Quickshell and a graphical session are available; startup validates QML modules.'
