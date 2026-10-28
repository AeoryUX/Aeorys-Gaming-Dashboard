# Caelestia integration decisions

## Inspection evidence and limits

The user reported Caelestia Shell `2.5.0-1`, CLI `1.1.3-1`, Quickshell
`0.3.2.r11.g9b0f339-1`, and Hyprland `0.56.2`. The accessible workspace is Debian;
none of those desktop executables or user configurations is installed here.
No `AGENTS.md` instructions were found under `/workspace`.

Inspected upstream sources:

- [Caelestia v2.5.0](https://github.com/caelestia-dots/shell/tree/v2.5.0),
  commit `d999d4878ee4cec134168e60d913714566a8cfa6`.
- [Quickshell 9b0f339](https://github.com/quickshell-mirror/quickshell/tree/9b0f339b19057f4731bf3b48293307d7ef241671),
  exactly matching the reported package commit.

`services/Colours.qml` and `utils/Paths.qml` establish the read-only scheme path
`$XDG_STATE_HOME/caelestia/scheme.json` (default `~/.local/state/caelestia`) and its
`colours` object. `README.md` documents `shell.json` appearance and launcher
actions. `plugin/src/Caelestia/Config/tokens.hpp` defines spacing/padding tokens.
`modules/bar/Bar.qml` selects a fixed set of entry delegates; `shell.qml` imports
modules explicitly. No general third-party module-loading API was found in this
inspection. Caelestia's own C++ QML plugin is not evidence of such an API.

Quickshell's `src/io/process.hpp`, `datastream.hpp`, `fileview.hpp`,
`ipchandler.hpp`, `src/core/qmlglobal.hpp`, Hyprland IPC workspace/QML headers,
and `src/launch/parsecommand.cpp` establish the Process, StdioCollector,
FileView, IPC, shellDir, fullscreen-workspace, path selection, daemonize, and
no-duplicate interfaces used here. Source verification is **not** execution
verification in the user's installed package.

## Options and recommendation

1. A dynamically loaded native extension would be ideal if the installed shell
   explicitly supported it. No such loader was found; do not invent one.
2. Import the dashboard into Caelestia's root/drawer components. This could reuse
   all its live tokens and transitions, but requires patching shell files and
   maintaining those patches through updates. Not selected.
3. A separate Quickshell configuration, with a Python backend, scoped IPC,
   read-only theme/config access, and launcher entry. **Recommended and implemented
   as the initial candidate.** Caelestia source remains untouched.

The candidate uses a regular compositor-managed window rather than a layer-shell
surface that claims exclusive keyboard focus. Its application ID is
`org.aeorys.GamingDashboard`. Hyprland placement/floating rules may be needed to
match the user's layout; none have been installed or presumed valid. It suppresses
opening on fullscreen/unknown focused workspaces and uses Escape to hide.
Multi-monitor placement, close/reopen focus, and fullscreen transitions require
live testing. It does not automatically dismiss Caelestia drawers.

Theme colours follow the saved scheme via a watched, read-only file. The base
`shell.json` appearance supplies font family/size and spacing/padding/rounding
scales, with Caelestia-style defaults and explicit fallback status. This is an
adapter to internal file formats, not a promised stable theme API. Monitor-specific
overrides, transient theme previews, variable-font axes, all typography roles,
animations, and transparency effects are not fully replicated. User configuration
inspection and visual comparison are still required before claiming native parity.

## Installation and optional integration

The scripts run from the checkout without installing or editing other files.
First complete the manual checks. Normal use requires no root.

**Before changing existing Hyprland or Caelestia files, obtain the user's approval
for the exact proposed diff.** Inspect the user's actual sourced configuration
and `hyprctl -j binds` first. No shortcut has been selected or installed because
the binding inventory is unavailable. A proposed binding can execute:

```text
bash /ABSOLUTE/PATH/Aeorys-Gaming-Dashboard/scripts/toggle.sh
```

For a launcher entry, review the supplied desktop-entry template and replace the
absolute-path placeholder. Install it as a new uniquely named
`$XDG_DATA_HOME/applications/org.aeorys.GamingDashboard.desktop` only after checking
for an existing file. Caelestia's application launcher should discover it through
its desktop-entry model; verify this on the installed version. A configured
Caelestia launcher action is another supported option, but changing the existing
actions array needs an approved merge preserving all existing entries.

A dedicated bar button would require editing the fixed bar delegate source in
the inspected version. Defer that patch; the launcher entry is less invasive.
No service, autostart entry, compositor rule, or shortcut is installed by this repo.

## Update and uninstall

Before updating, save/commit any local changes. Pull using `git pull --ff-only`
from a stable checkout, rerun tests, then stop and restart only the companion.
Keep the checkout path stable: the launcher path and IPC selection depend on it.
After Caelestia/Quickshell upgrades, recheck the referenced interfaces and manual
checklist. Do not overwrite the shell's configuration to resolve drift.

To stop only this companion, use `qs -p /ABSOLUTE/PATH/Aeorys-Gaming-Dashboard kill`.
Never run an unscoped `pkill qs`. Remove only the new dashboard desktop entry and
any exact shortcut/autostart lines you explicitly approved; preserve surrounding
config. Remove the checkout if desired. Keep local notes by default. Optional
personal-data deletion concerns only `$XDG_DATA_HOME/aeorys-gaming` and the optional
`$XDG_CONFIG_HOME/aeorys-gaming` directory; inspect them before deleting. Steam,
Sober, Caelestia, Hyprland and Vesktop files remain untouched.
