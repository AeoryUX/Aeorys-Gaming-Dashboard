import QtQuick
import Quickshell
import Quickshell.Io

QtObject {
    id: root
    property var colours: ({})
    property var appearance: ({})
    property string status: "Caelestia theme unavailable; using fallback colours."
    readonly property color surface: colours.surface ? "#" + colours.surface : "#191114"
    readonly property color container: colours.surfaceContainer ? "#" + colours.surfaceContainer : "#261d20"
    readonly property color foreground: colours.onSurface ? "#" + colours.onSurface : "#efdfe2"
    readonly property color secondary: colours.onSurfaceVariant ? "#" + colours.onSurfaceVariant : "#d5c2c6"
    readonly property color primary: colours.primary ? "#" + colours.primary : "#ffb0ca"
    readonly property string family: appearance.font?.body?.family || "GoogleSansFlex"
    readonly property real gap: 12 * (appearance.spacing?.scale || 1)
    readonly property real padding: 16 * (appearance.padding?.scale || 1)
    readonly property real rounding: 20 * (appearance.rounding?.scale || 1)
    readonly property real fontSize: (appearance.font?.body?.medium?.size || 14) * (appearance.font?.scale || 1)
    readonly property real animationDuration: Math.max(0, Math.min(1000, 200 * (appearance.anim?.durations?.scale ?? 1)))

    property FileView scheme: FileView {
        path: (Quickshell.env("XDG_STATE_HOME") || Quickshell.env("HOME") + "/.local/state") + "/caelestia/scheme.json"
        watchChanges: true
        printErrors: false
        onFileChanged: reload()
        onLoaded: {
            try {
                const parsed = JSON.parse(text())
                if (!parsed.colours) throw new Error("Missing colours")
                const checked = {}
                for (const key of ["surface", "surfaceContainer", "onSurface", "onSurfaceVariant", "primary"]) {
                    if (!/^[a-fA-F0-9]{6}$/.test(parsed.colours[key])) throw new Error("Invalid colour: " + key)
                    checked[key] = parsed.colours[key]
                }
                root.colours = checked
                root.status = "Following Caelestia’s active colour scheme."
            } catch (error) { root.status = "Theme could not be read; retaining last valid palette." }
        }
    }
    property FileView config: FileView {
        path: (Quickshell.env("XDG_CONFIG_HOME") || Quickshell.env("HOME") + "/.config") + "/caelestia/shell.json"
        watchChanges: true
        printErrors: false
        onFileChanged: reload()
        onLoaded: {
            try { root.appearance = JSON.parse(text()).appearance || ({}) }
            catch (error) { root.status = "Caelestia appearance configuration could not be read." }
        }
    }
}
