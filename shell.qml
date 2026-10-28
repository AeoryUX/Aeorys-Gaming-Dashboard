//@ pragma AppId org.aeorys.GamingDashboard
import Quickshell
import Quickshell.Io
import Quickshell.Hyprland
import QtQuick
import "components"

ShellRoot {
    id: root
    readonly property bool fullscreenOrUnknown: !Hyprland.focusedWorkspace || Hyprland.focusedWorkspace.hasFullscreen
    onFullscreenOrUnknownChanged: { if (fullscreenOrUnknown) window.visible = false }
    Backend { id: backend }
    Theme { id: theme }
    IpcHandler {
        target: "dashboard"
        function toggle(): string {
            if (window.visible) { window.visible = false; return "Dashboard hidden." }
            if (root.fullscreenOrUnknown) return "Dashboard stayed hidden: focused workspace is fullscreen or unavailable."
            window.visible = true
            return "Dashboard opened."
        }
        function hide(): void { window.visible = false }
    }
    FloatingWindow {
        id: window
        title: "Aeory Gaming Dashboard"
        visible: false
        implicitWidth: Math.min(900, Math.max(320, (screen?.width || 1000) - 64))
        implicitHeight: Math.min(680, Math.max(280, (screen?.height || 800) - 96))
        color: theme.surface
        onVisibleChanged: { if (visible && !backend.busy) backend.request(["library"]) }
        Dashboard {
            anchors.fill: parent
            backend: backend
            theme: theme
            onCloseRequested: window.visible = false
        }
        Shortcut { sequence: "Escape"; onActivated: window.visible = false }
    }
}
