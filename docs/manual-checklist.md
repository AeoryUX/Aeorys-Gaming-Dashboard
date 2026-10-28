# Manual integration checklist

These checks are **pending**, not passed by offscreen tests. Run without root on
the target desktop, using a game whose unsaved progress can safely be discarded.

- Record `qs --version`, Caelestia package versions and `hyprctl version`; inspect
  relevant `AGENTS.md`, Caelestia files, `shell.json`, monitor overrides, and the
  complete sourced Hyprland configuration. Redact private values before sharing.
- Inspect `hyprctl -j binds`; propose an unused shortcut and show the exact diff.
  Obtain approval before changing existing files. Check both key press/release
  bindings and global shortcuts. No default shortcut is assumed conflict-free.
- Run dependency check and toggle from this checkout. Confirm a single companion
  instance across repeated toggles, with Caelestia still running unchanged.
- Verify exactly Games and Gaming Resources dashboard pages, arrow buttons and
  two dots, keyboard navigation that leaves text input alone, consistent window
  size, secondary library/details views, and no automatic launch on navigation.
- Compare cached recent/top-played rankings with real Steam data. Missing cache
  or ambiguous accounts must show empty states, never invented hours/history.
- Confirm Escape, window close, reopening, keyboard navigation, and return of
  focus. Verify no focus theft on game launch, fullscreen transitions, another
  workspace, lock screen, or another monitor. Check floating/placement behavior
  before proposing any compositor rule.
- With a fullscreen game focused, toggle must stay hidden. End fullscreen and
  retry. If IPC workspace state is unavailable, opening must remain suppressed.
- Compare colour, font, size, spacing and corner radius with installed Caelestia.
  Change active theme and verify live scheme reload. Check light/dark themes,
  unreadable/malformed scheme files, missing fonts and monitor-specific overrides.
- Compare native/Flatpak Steam libraries and a second disk with Steam's installed
  list. Test disk disconnection, a partially installed game, invalid manifests,
  no games, search with no matches, and Flatpak path permissions.
- Open a real game page, inspect path/artwork and launch through Steam. Confirm
  the intended app starts; do not equate a launch request with success. Check Sober
  both installed and absent. Verify external links are labelled and opt-in.
- Save distinct notes for two games and restart. Confirm isolation, Unicode,
  atomic updates, and useful behavior on unwritable notes or malformed config.
- Scan native, Proton and Sober processes, comparing PID/executable/CPU/RSS with
  system tools. Check that uncertain wrappers are omitted, with limitations shown.
  Steam, Caelestia, Hyprland and unrelated apps must have no termination controls.
- Compare NVIDIA fields with `nvidia-smi`; unsupported per-process fields must
  remain unavailable and GPU-wide readings must be labelled separately. Check
  exact-PID background labels, CPU/GPU temperatures and absence of fault claims.
  Confirm no repeated polling, including while hidden.
- Cancel termination and verify nothing is signalled. Confirm a disposable game
  process; verify only that PID receives SIGTERM. If it exits, force quit must not
  be offered after refresh. If it survives five seconds, refresh and verify force
  quit is separate and shows the target again. Cancel it first, then test explicitly.
- Between scan and confirmation, exit/restart a game. Stale identity must be
  rejected. On missing pidfd support, termination must refuse without fallback.
- Stop/uninstall only the companion. Confirm Caelestia, Hyprland, Steam, Sober,
  Vesktop, notes and pre-existing configuration remain intact.
