import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import "Navigation.js" as Navigation

Rectangle {
    id: root
    required property var backend
    required property var theme
    property var selected: null
    property var pages: [{id: "games", title: "Games"}, {id: "resources", title: "Gaming Resources"}]
    property string secondaryView: ""
    property int pageIndex: 0
    readonly property string currentPage: pages[pageIndex]?.id || "games"
    readonly property bool runningPage: currentPage === "resources" && !secondaryView
    readonly property bool editingText: {
        const item = root.Window.window?.activeFocusItem
        return item instanceof TextInput || item instanceof TextEdit
    }
    property var pendingTarget: null
    property bool pendingForce: false
    property var graceful: ({})
    property var forceEligible: ({})
    property string selectedProcessToken: ""
    property bool showIdentificationDetails: false
    signal closeRequested()
    color: theme.surface

    function showPage(index) {
        selected = null
        secondaryView = ""
        pageIndex = Navigation.normalize(index, pages.length)
        fade.restart()
        if (runningPage && !backend.busy) backend.request(["running"])
    }

    function navigate(direction) {
        if (pages.length > 1) showPage(Navigation.next(pageIndex, direction, pages.length))
    }

    function showLibrary() { selected = null; secondaryView = "library" }

    Shortcut { sequence: "Left"; enabled: root.visible && !root.editingText && !confirmation.visible && root.pages.length > 1; onActivated: root.navigate(-1) }
    Shortcut { sequence: "Right"; enabled: root.visible && !root.editingText && !confirmation.visible && root.pages.length > 1; onActivated: root.navigate(1) }
    NumberAnimation { id: fade; target: pageContent; property: "opacity"; from: 0.25; to: 1; duration: root.theme.animationDuration }

    Connections {
        target: root.backend
        function onTerminationSent(pid, token) {
            const updated = Object.assign({}, root.graceful)
            updated[token] = Date.now()
            root.graceful = updated
        }
        function onProcessesRefreshed() {
            const eligible = {}
            for (const process of root.backend.processes) {
                const attemptedAt = root.graceful[process.token]
                if (attemptedAt !== undefined && Date.now() - attemptedAt >= 5000)
                    eligible[process.token] = true
            }
            root.forceEligible = eligible
            if (!root.backend.processes.some(process => process.token === root.selectedProcessToken))
                root.selectedProcessToken = root.backend.processes[0]?.token || ""
        }
    }

    function matches() {
        return backend.games.filter(game => game.name.toLowerCase().includes(search.text.toLowerCase()))
    }

    component TextLabel: Label {
        color: root.theme.foreground
        font.family: root.theme.family
        font.pixelSize: root.theme.fontSize
        textFormat: Text.PlainText
        wrapMode: Text.Wrap
    }
    component Action: Button {
        id: action
        font.family: root.theme.family
        font.pixelSize: root.theme.fontSize
        contentItem: Text {
            text: action.text
            textFormat: Text.PlainText
            color: action.enabled ? root.theme.foreground : root.theme.secondary
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            color: action.down ? root.theme.primary : root.theme.container
            radius: root.theme.rounding
            border.width: action.activeFocus ? 2 : 0
            border.color: root.theme.primary
            opacity: action.enabled ? 1 : 0.5
        }
        padding: root.theme.padding
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: root.theme.padding * 1.5
        spacing: root.theme.gap
        ColumnLayout {
            Layout.fillWidth: true
            TextLabel { text: "Aeory Gaming"; font.pixelSize: 22; font.weight: Font.Medium; Layout.fillWidth: true }
            RowLayout {
                Layout.fillWidth: true
                Action { text: "‹"; Accessible.name: "Previous page"; enabled: root.pages.length > 1; onClicked: root.navigate(-1) }
                TextLabel { text: root.selected ? root.selected.name : root.secondaryView === "library" ? "Library" : root.pages[root.pageIndex]?.title || "Gaming"; font.weight: Font.Medium; horizontalAlignment: Text.AlignHCenter; Layout.fillWidth: true }
                Action { text: "›"; Accessible.name: "Next page"; enabled: root.pages.length > 1; onClicked: root.navigate(1) }
                Action { text: "×"; Accessible.name: "Close dashboard"; onClicked: root.closeRequested() }
            }
            Row {
                Layout.alignment: Qt.AlignHCenter
                spacing: 6
                visible: root.pages.length > 1
                Repeater {
                    model: root.pages.length
                    delegate: Rectangle {
                        required property int index
                        width: index === root.pageIndex ? 16 : 6
                        height: 6
                        radius: 3
                        color: index === root.pageIndex ? root.theme.primary : root.theme.secondary
                    }
                }
            }
        }

        RowLayout {
            visible: !root.selected && root.secondaryView === "library"
            TextField {
                id: search
                objectName: "search"
                Layout.fillWidth: true
                placeholderText: "Search installed games"
                focus: true
                Accessible.name: "Search installed games"
                color: root.theme.foreground
                font.family: root.theme.family
                background: Rectangle { color: root.theme.container; radius: root.theme.rounding }
                padding: root.theme.padding
            }
            Action { text: "Refresh"; enabled: !root.backend.busy; onClicked: root.backend.request(["library"]) }
        }

        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            contentWidth: availableWidth
            ColumnLayout {
                id: pageContent
                width: parent.width
                spacing: root.theme.gap

                ColumnLayout {
                    visible: !root.selected && root.secondaryView === "library"
                    Layout.fillWidth: true
                    Action { text: "Back to Games"; onClicked: root.showPage(0) }
                    Repeater {
                        model: root.matches()
                        delegate: Action {
                            required property var modelData
                            Layout.fillWidth: true
                            text: modelData.name
                            enabled: !root.backend.busy
                            onClicked: {
                                root.selected = modelData
                                root.backend.notes = ""
                                root.backend.request(["notes-get", modelData.id])
                            }
                        }
                    }
                    TextLabel {
                        Layout.fillWidth: true
                        visible: root.matches().length === 0
                        text: root.backend.busy ? "Reading installed libraries…" : "No matching installed games. Refresh after installing a game, or check library paths and permissions."
                    }
                    Repeater {
                        model: root.backend.warnings
                        delegate: TextLabel { required property string modelData; text: modelData; Layout.fillWidth: true }
                    }
                }

                ColumnLayout {
                    visible: !root.selected && !root.secondaryView && root.currentPage === "games"
                    Layout.fillWidth: true
                    TextLabel { text: root.backend.history.status; Layout.fillWidth: true }
                    TextLabel { text: "Continue Playing · last 3"; font.weight: Font.Medium }
                    Repeater {
                        model: root.backend.history.continue_playing
                        delegate: RowLayout {
                            required property var modelData
                            Layout.fillWidth: true
                            TextLabel { text: modelData.name; font.weight: Font.Medium; Layout.fillWidth: true }
                            TextLabel {
                                Layout.fillWidth: true
                                text: Qt.formatDateTime(new Date(modelData.last_played * 1000), "dd MMM yyyy")
                            }
                            Action { text: "Launch"; Accessible.name: "Launch " + modelData.name; enabled: !root.backend.busy; onClicked: root.backend.request(["launch", modelData.id]) }
                        }
                    }
                    TextLabel {
                        Layout.fillWidth: true
                        visible: root.backend.history.continue_playing.length === 0
                        text: root.backend.busy ? "Reading Steam cache…" : "No reliable recent-play history available for installed games."
                    }
                    TextLabel { text: "Most Played · top 5"; font.weight: Font.Medium }
                    Repeater {
                        model: root.backend.history.most_played
                        delegate: TextLabel {
                            required property var modelData
                            Layout.fillWidth: true
                            text: modelData.name + " · " + (modelData.playtime_minutes / 60).toFixed(1) + " h · Steam-reported (local cache)"
                        }
                    }
                    TextLabel { text: "Steam playtime unavailable. No locally tracked time is collected."; visible: root.backend.history.most_played.length === 0; Layout.fillWidth: true }
                    Repeater {
                        model: root.backend.history.warnings
                        delegate: TextLabel { required property string modelData; text: modelData; Layout.fillWidth: true }
                    }
                    Action { text: "Open Library"; onClicked: root.showLibrary() }
                    Action { text: "Refresh Steam cache"; enabled: !root.backend.busy; onClicked: root.backend.request(["library"]) }
                }

                ColumnLayout {
                    visible: root.selected !== null
                    Layout.fillWidth: true
                    Action { text: "Back to Library"; onClicked: root.showLibrary() }
                    TextLabel { text: root.selected?.name || ""; font.pixelSize: 24 }
                    Image {
                        source: root.selected?.artwork || ""
                        visible: status === Image.Ready
                        sourceSize.width: 360
                        Layout.preferredHeight: 180
                        Layout.fillWidth: true
                        fillMode: Image.PreserveAspectFit
                    }
                    TextLabel { text: "Installation: " + (root.selected?.install_path || ""); Layout.fillWidth: true }
                    Action { text: "Launch through " + (root.selected?.kind === "steam" ? "Steam" : "Sober"); enabled: !root.backend.busy; onClicked: root.backend.request(["launch", root.selected.id]) }
                    Action { text: "ProtonDB ↗ (external community reports)"; visible: root.selected?.kind === "steam"; onClicked: Qt.openUrlExternally(root.selected.protondb_url) }
                    Action { text: "Steam store ↗ (external)"; visible: root.selected?.kind === "steam"; onClicked: Qt.openUrlExternally(root.selected.store_url) }
                    TextLabel { text: "Personal notes · stored only on this device" }
                    TextArea {
                        id: notes
                        objectName: "notes"
                        Layout.fillWidth: true
                        Layout.preferredHeight: 120
                        text: root.backend.notes
                        textFormat: TextEdit.PlainText
                        wrapMode: TextEdit.Wrap
                        color: root.theme.foreground
                        font.family: root.theme.family
                        background: Rectangle { color: root.theme.container; radius: root.theme.rounding }
                        Accessible.name: "Personal game notes"
                    }
                    Action { text: "Save notes"; enabled: !root.backend.busy && root.backend.notesGame === root.selected?.id; onClicked: root.backend.request(["notes-set", root.selected.id], notes.text) }
                }

                ColumnLayout {
                    visible: root.runningPage
                    Layout.fillWidth: true
                    Action { text: "Refresh processes"; enabled: !root.backend.busy; onClicked: root.backend.request(["running"]) }
                    ComboBox {
                        Layout.fillWidth: true
                        visible: root.backend.processes.length > 0
                        model: root.backend.processes.map(process => (process.game_name || process.game_id) + " · PID " + process.pid + " · " + (process.window_activity || "unknown"))
                        currentIndex: Math.max(0, root.backend.processes.findIndex(process => process.token === root.selectedProcessToken))
                        Accessible.name: "Select detected game process"
                        font.family: root.theme.family
                        palette.button: root.theme.container
                        palette.buttonText: root.theme.foreground
                        onActivated: index => root.selectedProcessToken = root.backend.processes[index].token
                    }
                    TextLabel { visible: root.backend.processes.length === 0; text: "No confidently identified game processes. This does not prove no games are running."; Layout.fillWidth: true }
                    Repeater {
                        model: root.backend.processes
                        delegate: ColumnLayout {
                            id: processRow
                            required property var modelData
                            required property int index
                            Layout.fillWidth: true
                            visible: modelData.token === root.selectedProcessToken || (!root.selectedProcessToken && index === 0)
                            TextLabel { text: processRow.modelData.window_activity === "background" ? "Background window detected · may be intentional" : processRow.modelData.window_activity === "foreground" ? "Foreground game window" : "Window activity unavailable"; color: root.theme.primary; Layout.fillWidth: true }
                            TextLabel {
                                Layout.fillWidth: true
                                text: processRow.modelData.game_id + " · PID " + processRow.modelData.pid + "\n" + processRow.modelData.exe + "\nRSS: " + (processRow.modelData.rss_bytes / 1048576).toFixed(1) + " MiB · CPU: " + (processRow.modelData.cpu_percent === null ? "unavailable" : processRow.modelData.cpu_percent.toFixed(1) + "% of one core") + "\n" + processRow.modelData.confidence
                            }
                            Repeater {
                                model: processRow.modelData.gpu_samples || []
                                delegate: TextLabel {
                                    required property var modelData
                                    Layout.fillWidth: true
                                    text: "This process · GPU " + modelData.gpu_index + ": " + (modelData.gpu_percent === null ? "utilization unavailable" : modelData.gpu_percent + "% SM utilization") + " · VRAM " + (modelData.vram_mib === null ? "unavailable" : modelData.vram_mib + " MiB")
                                }
                            }
                            ColumnLayout {
                                Action {
                                    text: "Request graceful exit…"
                                    enabled: !root.backend.busy
                                    onClicked: { root.pendingTarget = processRow.modelData; root.pendingForce = false; confirmation.open() }
                                }
                                Action {
                                    text: "Force quit…"
                                    visible: root.forceEligible[processRow.modelData.token] === true
                                    enabled: !root.backend.busy
                                    onClicked: { root.pendingTarget = processRow.modelData; root.pendingForce = true; confirmation.open() }
                                }
                            }
                        }
                    }
                    TextLabel { text: root.backend.resources.per_process_status; Layout.fillWidth: true }
                    Repeater {
                        model: root.backend.resources.gpus
                        delegate: TextLabel {
                            required property var modelData
                            Layout.fillWidth: true
                            text: "GPU-wide context · " + modelData.name + ": " + (modelData.utilization_percent === null ? "unavailable" : modelData.utilization_percent + "%") + " · VRAM " + (modelData.vram_used_mib === null ? "unavailable" : modelData.vram_used_mib + " MiB") + " · " + (modelData.temperature_c === null ? "temperature unavailable" : modelData.temperature_c + " °C")
                        }
                    }
                    TextLabel { text: "GPU-wide utilization, VRAM and temperature unavailable."; visible: root.backend.resources.gpus.length === 0; Layout.fillWidth: true }
                    Repeater {
                        model: root.backend.resources.cpu_temperatures
                        delegate: TextLabel { required property var modelData; text: modelData.label + ": " + modelData.celsius + " °C · system context"; Layout.fillWidth: true }
                    }
                    TextLabel { text: "CPU temperature unavailable."; visible: root.backend.resources.cpu_temperatures.length === 0 }
                    TextLabel { text: "Temperatures alone do not diagnose a cooling fault. Readings update only on request."; Layout.fillWidth: true }
                    Repeater {
                        model: root.backend.resources.warnings
                        delegate: TextLabel { required property string modelData; text: modelData; Layout.fillWidth: true }
                    }
                    Action { text: root.showIdentificationDetails ? "Hide identification details" : "Identification and troubleshooting"; onClicked: root.showIdentificationDetails = !root.showIdentificationDetails }
                    TextLabel { text: root.backend.limitations; visible: root.showIdentificationDetails; Layout.fillWidth: true }
                    TextLabel { text: "Window activity uses exact Hyprland PID matches only. Unknown wrappers remain unclassified. A background game may be intentional. If a game is missing, verify its Steam app ID and installation path; no broad process termination is offered."; visible: root.showIdentificationDetails; Layout.fillWidth: true }
                }
            }
        }
        TextLabel { Layout.fillWidth: true; text: root.backend.message }
        TextLabel { Layout.fillWidth: true; text: root.theme.status; font.pixelSize: 11 }
    }

    Dialog {
        id: confirmation
        objectName: "terminationConfirmation"
        anchors.centerIn: parent
        width: Math.min(parent.width - 40, 600)
        modal: true
        font.family: root.theme.family
        palette.window: root.theme.container
        palette.windowText: root.theme.foreground
        palette.text: root.theme.foreground
        palette.button: root.theme.surface
        palette.buttonText: root.theme.foreground
        palette.highlight: root.theme.primary
        title: root.pendingForce ? "Confirm force quit" : "Confirm graceful termination"
        standardButtons: Dialog.Ok | Dialog.Cancel
        contentItem: TextLabel {
            text: (root.pendingForce ? "Force quit may lose unsaved progress. It is allowed only if the same process survived a graceful request for at least 5 seconds.\n\n" : "Ask this one game process to exit. Unsaved progress may be lost.\n\n")
                + (root.pendingTarget ? root.pendingTarget.game_id + " · PID " + root.pendingTarget.pid + "\n" + root.pendingTarget.exe + "\nIdentity: " + root.pendingTarget.token : "")
                + "\n\nNo process group, launcher, or shell will be targeted."
        }
        onAccepted: {
            const target = root.pendingTarget
            const arguments = ["terminate", String(target.pid), "--confirm", target.token]
            if (root.pendingForce) arguments.push("--force")
            root.backend.request(arguments)
        }
    }
}
