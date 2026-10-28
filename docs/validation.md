# Validation boundary

Automated cloud validation uses Debian, Python 3.12, optional Qt 6.8.3/PySide6,
and makepkg 7.0.0 tooling extracted under `/tmp`. It does not install an Arch
package or modify the system package database.

Checks prepared and run for this MVP:

- 42 Python fixture tests: Steam manifests and libraries, Flatpak, KeyValues
  errors, local history sorting/limits and account ambiguity, NVIDIA/hwmon parsers,
  process identification, protected processes, identity changes and force policy.
- Offscreen QML smoke: library → details → explicit Steam request, local-note
  requests, termination confirmation gate, two-page wraparound, single-page
  behavior, real key events while search has focus, and 480×540, 800×600,
  1280×800 item sizing. These are test fixtures; no real game launch or signal.
- Qt QML parser checks for every QML file; shell syntax checks; Python bytecode
  compilation; desktop-file validation; Git whitespace checks.
- `makepkg --printsrcinfo` generates `.SRCINFO`; regeneration is compared with
  the checked-in file. Source/desktop SHA-256 verification stays enabled.
- Debian packaging simulation: relocated makepkg 7.0.0 with `--nodeps` runs
  `check()` and `package()` into fakeroot staging. Temporary wrappers select
  the extracted fakeroot libraries and a pacman configuration with an empty
  database. This verifies archive assembly and payload, **not a successful real
  Arch package build**, dependency resolution, installation, or reproducibility.
  Payload checks verify runtime JS/QML/Python, launcher, license, and absence
  of configuration files or install hooks.

Live Quickshell IPC/window lifecycle, Caelestia visual parity, custom shell
configuration, Hyprland focus/shortcuts/fullscreen behavior, real Steam cache
fields/game launches, NVIDIA GTX 1660 SUPER fields, temperatures and real game
termination remain local checks. Upstream source inspection verifies the selected
Quickshell interfaces, not runtime execution in the user's package.

`namcap`, a clean Arch/CachyOS dependency-provider check, actual package installation,
and the future release URL are not verified in this cloud. Nothing is published.
The local source artifact deliberately supplies the unpublished release's exact
bytes for package review. See local-testing.md before trying it on CachyOS.

The `/tmp/aeory-*` tooling and wrappers are cloud-only. They are not repository
files, source-archive members, package payload, or runtime dependencies. Runtime
code invokes the installed Python/Quickshell/optional desktop tools by normal
PATH lookup; it has no cloud-tool paths. Test fixtures and optional PySide6 tests
are development-only and never install those wrappers on a user machine.

Exact cloud commands (from the checkout unless stated otherwise):

```bash
python3 -m unittest discover -s tests -v
PYTHONPATH=/tmp/aeorys-qt python3 tests/qml_smoke.py
for file in shell.qml components/*.qml; do /tmp/aeorys-qt/PySide6/qmlformat "$file" >/dev/null || exit 1; done
for script in scripts/*.sh scripts/aeory-gaming-dashboard packaging/*.sh packaging/PKGBUILD; do bash -n "$script" || exit 1; done
python3 -m compileall -q backend tests packaging/check-package.py
desktop-file-validate packaging/aeory-gaming-dashboard.desktop
git diff --check
```

Packaging simulation previously run from `packaging/`:

```bash
PATH=/tmp/aeory-tools/usr/bin:$PATH LD_LIBRARY_PATH=/tmp/aeory-tools/usr/lib/x86_64-linux-gnu MAKEPKG_LIBRARY=/tmp/aeory-tools/usr/share/makepkg /tmp/aeory-tools/usr/bin/makepkg --config /tmp/aeory-tools/makepkg-local.conf --nodeps --cleanbuild --force
PATH=/tmp/aeory-tools/usr/bin:$PATH python3 check-package.py aeory-gaming-dashboard-0.1.0-1-any.pkg.tar.zst
```

These cloud paths are an execution record, **not instructions or prerequisites
for the local launch**. The helper configuration intentionally does not represent
an installed Arch system. Real CachyOS package checking remains pending.
