# Run this review branch on CachyOS

Use the review checkout containing this work, not the unchanged upstream `main`.
All changes remain on task branch `work`; no merge, release, or AUR publication
is authorized. The review branch is pushed only when requested. From that checkout:

```bash
git switch work
python3 -m unittest discover -s tests -v
python3 -m backend library
python3 -m backend running
bash scripts/check-deps.sh
bash scripts/toggle.sh
```

For development logs, run `bash scripts/run.sh` in one terminal and
`bash scripts/toggle.sh` in another. These commands use the checkout as a separate
Quickshell configuration. They do not edit installed Caelestia, Hyprland or
Vesktop files, install services, or bind keys. Expected target versions and runtime
dependencies are listed in README.md. Optional QML smoke-test setup is there too.

Test exactly two dashboard pages: Games and Gaming Resources. Verify arrows and
two-dot indicator, Left/Right while focused, Tab/Shift+Tab, and that arrows in
search and notes only move the text cursor. Compare panel dimensions on both pages
and on a smaller display. Library and game details must stay secondary views.
Check honest empty states with missing history, no games, multiple accounts,
unmounted libraries and missing hardware tools. Opening/switching must never launch.

Validate cached Playtime/LastPlayed fields against your actual Steam account before
trusting rankings. Check the configured account, missing fields and stale caches;
no locally tracked time is recorded. Inspect your real `shell.json` and compare
the theme, animation scale, typography, spacing, light/dark modes and any monitor
overrides. Cloud fixtures do not establish live visual parity.

Check GPU-wide and per-process readings against your installed `nvidia-smi`.
The GTX 1660 SUPER/driver may not expose `pmon` fields; unavailable is expected.
Confirm that CPU/RAM are labelled per process, GPU-wide context is not presented
as the game's usage, background windows are not called unwanted, and temperatures
do not produce cooling diagnoses. Refresh is manual; no recurring hardware
queries run while visible or hidden. A requested in-flight scan may finish after
hiding the panel.

Use the detailed [manual checklist](manual-checklist.md) for focus/fullscreen,
launch and termination tests. No real games were launched or signalled in cloud.
To stop just the development companion, from the same checkout:

```bash
qs -p "$PWD" kill
```

## Integration review and rollback

No existing shell configuration is changed by the development method or package.
Any future shortcut, compositor rule or launcher-actions edit needs review of the
actual configuration, a conflict check, and approval of the exact diff first.
Before an approved edit, back up each affected file to a fresh timestamped path:

```bash
cp --preserve=all -- /actual/config/file /actual/config/file.aeory-backup-YYYYMMDD-HHMMSS
```

Use an unused backup name; never overwrite an existing backup. For rollback, stop
the companion, compare the backup with current content and reverse only the
approved diff. Restore the complete backup only if no intervening user edits would
be lost. Remove only the uniquely named dashboard launcher/shortcut entries you
installed. Do not delete shared configuration directories or restart services.

## Local package review and installation

Review `packaging/PKGBUILD` before executing it. The source release URL is reserved
for a future review-approved release and **does not exist yet**. The following
creates a deterministic local artifact whose SHA-256 is pinned in PKGBUILD, so
no unpublished release needs downloading. It includes only the enumerated source
paths, no `.git`, environments, notes, or caches:

```bash
bash packaging/prepare-source.sh
cd packaging
makepkg --verifysource
makepkg --printsrcinfo > /tmp/aeory.SRCINFO
diff -u .SRCINFO /tmp/aeory.SRCINFO
makepkg --cleanbuild
python3 check-package.py ./aeory-gaming-dashboard-0.1.0-1-any.pkg.tar.zst
namcap PKGBUILD aeory-gaming-dashboard-0.1.0-1-any.pkg.tar.zst
```

Use the installed `quickshell-git` provider if it provides `quickshell`; do not
replace your running shell package. Resolve missing declared dependencies using
your normal package workflow. After reviewing the package contents, install with:

```bash
sudo pacman -U ./aeory-gaming-dashboard-0.1.0-1-any.pkg.tar.zst
aeory-gaming-dashboard check
aeory-gaming-dashboard toggle
```

Package installation requires the normal pacman privilege; app execution does
not. It installs under `/usr` only, with no install hook, service, shell-config
edit, or automatic launch. The desktop entry should appear in Caelestia's app
launcher; verify locally. A custom bar button is not installed.

For package removal, stop only its process, then remove the package:

```bash
qs -p /usr/share/aeory-gaming-dashboard kill
sudo pacman -R aeory-gaming-dashboard
```

Local notes and optional app configuration remain. Do not publish the PKGBUILD
until the exact source artifact is deliberately released at the stated URL,
metadata/checksums are regenerated as needed, and clean Arch/CachyOS build and
live desktop tests pass. Cloud makepkg checks cannot validate installed Arch
dependency providers or hardware integration. `namcap` remains a local check
if unavailable in the cloud.
