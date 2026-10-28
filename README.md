# Aeory Gaming Dashboard

A local Linux gaming companion for Caelestia Shell. QML presents the interface;
a separate Python backend reads Steam libraries, launches through Steam, stores
personal notes, and conservatively identifies running game processes.

This is an initial implementation, **not yet verified inside the target desktop**.
The development workspace is Debian and has no Hyprland/Quickshell session.
The dashboard component is tested offscreen; Quickshell IPC, live theme changes,
focus behavior, real game launch, and real game termination require the manual
checks below. No fake games or statistics appear in production.

## Target and dependencies

- CachyOS, Hyprland 0.56.2 on Wayland.
- Caelestia Shell 2.5.0-1; CLI 1.1.3-1.
- Quickshell 0.3.2 at commit `9b0f339`, with `Quickshell.Io` and
  `Quickshell.Hyprland` support, QtQuick Controls and Layouts.
- Python 3.10+; **no third-party Python packages for normal use**.
- Native Steam or Flatpak Steam. Flatpak is optional for Sober detection/launch.
- Caelestia's existing font installation; system fallback if unavailable.

No root access, NVIDIA utilities, driver changes, service restarts, system tuning,
telemetry, or network API keys are required. The i5-14400F and GTX 1660 SUPER need
no special handling. Existing `nvidia-smi` is optional; unsupported readings stay
unavailable. The app never installs or changes drivers.

## Two-page dashboard

**Games** shows the last three played installed games, each with an explicit
launch button, and a compact top five by total cached Steam playtime. Library
search and game details are secondary views, not extra dashboard pages.

**Gaming Resources** lists confidently detected game processes and lets you select
one for CPU/RAM and available GPU/VRAM readings. Background window matches are
highlighted without recommending that they be closed. Readings are snapshots;
opening that page or pressing Refresh requests a scan. There is no repeating
hardware polling, including while hidden.

Use the left/right arrow buttons or Left/Right keys while focused. Arrow shortcuts
are disabled in text inputs and confirmation dialogs. Tab/Shift+Tab move through
controls; Enter/Space activate focused buttons. Page indicators show two dots.
Both pages share the same window dimensions, clamped to the screen; content
scrolls. Page fades follow the base Caelestia animation-duration scale. Opening,
navigation, search, and refresh never launch a game automatically.

History comes from the selected Steam account's
`userdata/<id>/config/localconfig.vdf`, using `Playtime` (minutes) and `LastPlayed`
(Unix seconds) under `UserLocalConfigStore/Software/Valve/Steam/apps`. This is an
internal local cache format, not a stable public API; the target user's cache
has not been inspected. Cached fields are labelled **Steam-reported · local
cache**, may be stale/incomplete, and are never inferred from installed-game
manifests. No locally tracked session time is collected. Missing or invalid fields
produce empty states. Only installed games are included so entries can be launched.
Multiple accounts are not merged: choose one explicitly in the optional config,
using its numeric `userdata` directory name:

```json
{"libraries": ["/mnt/Games/SteamLibrary"], "steam_user_id": "12345678"}
```

Steam's public Web API is a different potential source, requiring credentials
and network/privacy decisions. This MVP does not request it or scrape community
profiles. Local cache parsing and ranking are tested with fixtures, not claimed
verified against the user's real Steam history.

## Start

Keep this checkout at a stable absolute path. From the checkout:

```bash
bash scripts/check-deps.sh
bash scripts/toggle.sh
```

Toggle starts a separate, initially hidden Quickshell process if necessary, then
addresses only that configuration's IPC target. It does not restart Caelestia.
The window remains hidden when the focused workspace is fullscreen or unknown,
and hides if that condition develops. Escape closes the dashboard without
stopping games. There is no polling that automatically opens the dashboard.

For startup diagnostics, run `bash scripts/run.sh` in a terminal, then toggle
from another terminal. Missing Quickshell or a graphical session produces an
explanation. The current cloud workspace cannot run this desktop command.

## Library and game pages

The backend reads native Steam roots (`~/.local/share/Steam`, `~/.steam/steam`,
`~/.steam/root`) and Flatpak Steam's data directory. It follows modern and legacy
`libraryfolders.vdf` entries, deduplicates root symlinks, and scans
`steamapps/appmanifest_*.acf`. Entries require Steam's fully-installed flag and
an existing installation directory. Incomplete, unreadable, or missing installs
produce warnings. Steam manifests can also describe installed tools; this first
version does not parse Steam's binary app-type database to classify those tools.

For nonstandard roots, optionally create a **new**
`~/.config/aeorys-gaming/config.json` (respecting `XDG_CONFIG_HOME`):

```json
{"libraries": ["/mnt/Games/SteamLibrary"]}
```

These paths are library roots, not `steamapps` directories. No filesystem-wide
scan or external metadata lookup occurs. Refresh after mounting a disk or
installing a game. Sober appears only when `flatpak info org.vinegarhq.Sober`
succeeds. Other Sober packaging formats are not currently detected.

Pages show the manifest title, local cached artwork when available, installation
path, Steam launch action, labelled external Steam/ProtonDB links, and local notes.
There are no compatibility scores. External links open only when clicked.
Launch requests use validated numeric app IDs and argv arrays, never shell
evaluation. A successful request does not prove the game started.

Notes are private files under `$XDG_DATA_HOME/aeorys-gaming` (default
`~/.local/share/aeorys-gaming`), written atomically with mode 0600 and limited to
64 KiB. They are not synced. Save before navigating away; notes are not autosaved.

## Running-game troubleshooting

Refresh scans same-user `/proc` entries. A Steam match requires an app ID in
the process environment plus an executable within the matching installation,
or a recognized Wine executable with an absolute Unix game `.exe` argument in
that installation. Sober requires both its executable name and Flatpak ID.
Missing app IDs, Windows-only paths, wrappers, and process permissions can prevent
identification. Absence from the list is not proof that a game is stopped.

Activity shows actual per-process RSS and a short CPU sample (100% = one logical
core). Refresh takes a new sample. RSS may include shared memory; results are not
whole-game totals. No background game is judged unwanted.

NVIDIA `pmon` readings are associated only with an exact detected PID and rechecked
process identity. Unsupported SM utilization or framebuffer-memory fields remain
unavailable; game totals are not invented by summing processes. Separate
`--query-gpu` readings are explicitly GPU-wide. CPU package temperatures come from
readable `coretemp`/`k10temp` hwmon labels; GPU temperatures are GPU-wide context.
Temperature alone is never used to diagnose cooling. Exact Hyprland client PIDs
can mark a window foreground/background; unmatched wrappers remain unknown.
When the dashboard itself is focused, game windows may naturally be background.

Graceful exit opens a confirmation showing game ID, PID, executable, and identity
token. The backend opens a Linux pidfd and revalidates UID, start time, executable,
argv, and game association before signalling that **single process**. It does not
signal groups or descendants and excludes shell/client/helper executable names.
Only selected Steam/Proton/Sober processes are eligible; no broad `pkill`, sudo,
or launcher shutdown is used. Games may ignore SIGTERM or show no save prompt.

After a successful graceful request, wait at least five seconds and refresh.
Only if that same process survives does a separate force-quit button appear.
Force quit requires a second confirmation and a recent successful graceful
attempt (5–300 seconds, same boot); identity is checked again. PID reuse or
identity changes cause refusal. Missing pidfd support causes refusal, never a
less-safe fallback. No real game signals were sent during development tests.

## Tests

```bash
python3 -m unittest discover -s tests -v
python3 -m backend library
python3 -m backend running
for script in scripts/*.sh scripts/aeory-gaming-dashboard packaging/*.sh; do bash -n "$script" || exit 1; done
```

The suite generates isolated Steam/proc fixtures, including malformed manifests,
multiple libraries, Flatpak, symlinks, protected processes and stale identities.
Signal tests are mocked. An empty real cloud library is an expected result,
not a successful real-game launch test.

Optional Qt component smoke test, using fixtures only inside the test:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
QT_QPA_PLATFORM=offscreen .venv/bin/python tests/qml_smoke.py
```

See [exact local run/package instructions](docs/local-testing.md),
[integration decisions](docs/integration.md) and the
[manual desktop checklist](docs/manual-checklist.md) before installing shortcuts
or launcher entries. Replay capture, uploads, accounts, social features, other
launchers, and desktop performance profiles are outside this build.
