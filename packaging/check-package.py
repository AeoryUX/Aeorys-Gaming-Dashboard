"""Validate package payload without installing or extracting it."""
from pathlib import Path
import subprocess
import sys

archive = Path(sys.argv[1]).resolve()
names = subprocess.check_output(["bsdtar", "-tf", str(archive)], text=True).splitlines()
required = {
    "usr/bin/aeory-gaming-dashboard",
    "usr/share/aeory-gaming-dashboard/shell.qml",
    "usr/share/aeory-gaming-dashboard/backend/__main__.py",
    "usr/share/aeory-gaming-dashboard/backend/history.py",
    "usr/share/aeory-gaming-dashboard/backend/resources.py",
    "usr/share/aeory-gaming-dashboard/components/Dashboard.qml",
    "usr/share/aeory-gaming-dashboard/components/Navigation.js",
    "usr/share/applications/aeory-gaming-dashboard.desktop",
    "usr/share/licenses/aeory-gaming-dashboard/LICENSE",
}
assert required.issubset(names), f"Missing package files: {required - set(names)}"
assert all(name.startswith("usr/") or name in {".BUILDINFO", ".MTREE", ".PKGINFO"} for name in names), "Unexpected configuration, hook, or non-/usr payload"
assert not any("__pycache__" in name or name.endswith(".pyc") for name in names)
license_bytes = subprocess.check_output(["bsdtar", "-xOf", str(archive), "usr/share/licenses/aeory-gaming-dashboard/LICENSE"])
assert license_bytes == (Path(__file__).resolve().parents[1] / "LICENSE").read_bytes()
print("PASS: package runtime files, JS import, desktop entry, license, and no user configuration/hooks")
