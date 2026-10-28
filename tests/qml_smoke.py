"""Optional offscreen UI smoke test. Fixtures exist only in this test, never production."""
import os
from pathlib import Path
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from PySide6.QtCore import QMetaObject, QObject, Qt, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

app = QGuiApplication(sys.argv)
engine = QQmlApplicationEngine()
components = (Path(__file__).resolve().parents[1] / "components").as_uri()
source = r'''
import QtQuick
import QtQuick.Controls
import "COMPONENTS"
import "COMPONENTS/Navigation.js" as Navigation
ApplicationWindow {
    id: window
    width: 1000; height: 760; visible: true
    property QtObject mockBackend: QtObject {
        property var games: [{id: "steam:42", appid: "42", name: "Fixture Game", kind: "steam", install_path: "/fixture/game", artwork: null, protondb_url: "https://www.protondb.com/app/42", store_url: "https://store.steampowered.com/app/42/"}]
        property var history: ({continue_playing: [], most_played: [], status: "No cached history", warnings: []})
        property var warnings: []
        property var processes: []
        property var resources: ({gpus: [], cpu_temperatures: [], warnings: [], per_process_status: "Unavailable in fixture"})
        property bool busy: false
        property string message: ""
        property string limitations: "Fixture only"
        property string notes: "Fixture note"
        property string notesGame: "steam:42"
        property var lastArguments: []
        signal terminationSent(int pid, string token)
        signal processesRefreshed()
        function request(args, input) { lastArguments = args; return true }
    }
    property QtObject mockTheme: QtObject {
        property color surface: "#191114"
        property color container: "#261d20"
        property color foreground: "#efdfe2"
        property color secondary: "#d5c2c6"
        property color primary: "#ffb0ca"
        property string family: "Sans Serif"
        property int fontSize: 14
        property int gap: 12
        property int padding: 16
        property int rounding: 20
        property int animationDuration: 0
        property string status: "Test fixture"
    }
    Dashboard { id: dashboard; objectName: "dashboard"; anchors.fill: parent; backend: window.mockBackend; theme: window.mockTheme }
    function prepareKeyboard() { dashboard.showPage(0); dashboard.showLibrary() }
    function exerciseSinglePage() {
        dashboard.pages = [{id: "games", title: "Games"}]
        dashboard.showPage(0)
        dashboard.navigate(1)
        if (dashboard.pageIndex !== 0) throw new Error("Single-page navigation moved")
    }
    function findButton(item, label) {
        if (item.text === label && item.clicked) return item
        for (let child of item.children || []) {
            const found = findButton(child, label)
            if (found) return found
        }
        return null
    }
    function exercise() {
        if (Navigation.next(0, -1, 2) !== 1 || Navigation.next(1, 1, 2) !== 0 || Navigation.next(0, 1, 1) !== 0 || Navigation.normalize(10, 0) !== 0)
            throw new Error("Navigation boundary failure")
        if (mockBackend.lastArguments.length) throw new Error("Opening launched a game")
        dashboard.navigate(1)
        if (dashboard.pageIndex !== 1 || mockBackend.lastArguments[0] === "launch") throw new Error("Page navigation launched a game")
        dashboard.showLibrary()
        if (dashboard.matches().length !== 1) throw new Error("Library not displayed")
        const button = findButton(dashboard, "Fixture Game")
        if (!button) throw new Error("Game button missing")
        button.clicked()
        if (dashboard.selected.id !== "steam:42") throw new Error("Game page did not open")
        if (mockBackend.lastArguments[0] !== "notes-get") throw new Error("Notes not requested")
        findButton(dashboard, "Launch through Steam").clicked()
        if (mockBackend.lastArguments.join(",") !== "launch,steam:42") throw new Error("Wrong launch request")
        findButton(dashboard, "Save notes").clicked()
        if (mockBackend.lastArguments[0] !== "notes-set") throw new Error("Notes not saved")
        dashboard.showPage(1)
        if (mockBackend.lastArguments[0] !== "running") throw new Error("Process scan not requested")
        mockBackend.processes = [{game_id: "steam:42", pid: 999999, exe: "/fixture/game", token: "fixture", rss_bytes: 0, cpu_percent: null, confidence: "Test only"}]
        const terminateButton = findButton(dashboard, "Request graceful exit…")
        if (!terminateButton) throw new Error("Termination button missing")
        terminateButton.clicked()
        if (mockBackend.lastArguments[0] === "terminate") throw new Error("Termination bypassed confirmation")
        window.width = 480
        window.height = 540
        return true
    }
}
'''.replace("COMPONENTS", components)
warnings = []
engine.warnings.connect(lambda errors: warnings.extend(error.toString() for error in errors))
engine.loadData(source.encode(), QUrl("file:///tmp/aeorys-smoke.qml"))
if not engine.rootObjects():
    raise SystemExit("QML failed to load: " + "\n".join(warnings))
app.processEvents()
window = engine.rootObjects()[0]
if not QMetaObject.invokeMethod(window, "exercise", Qt.DirectConnection):
    raise SystemExit("Could not execute QML smoke test")
app.processEvents()
dialog = window.findChild(QObject, "terminationConfirmation")
QMetaObject.invokeMethod(dialog, "reject", Qt.DirectConnection)
QMetaObject.invokeMethod(window, "prepareKeyboard", Qt.DirectConnection)
app.processEvents()
dashboard = window.findChild(QQuickItem, "dashboard")
search = window.findChild(QQuickItem, "search")
search.forceActiveFocus()
app.processEvents()
assert dashboard.property("editingText"), "Search focus not recognized"
search.setProperty("text", "missing fixture")
app.processEvents()
QTest.keyClick(window, Qt.Key_Right)
assert dashboard.property("pageIndex") == 0, "Arrow key intercepted search input"
assert search.property("text") == "missing fixture"
dashboard.forceActiveFocus()
app.processEvents()
assert not dashboard.property("editingText")
QTest.keyClick(window, Qt.Key_Right)
assert dashboard.property("pageIndex") == 1, "Focused arrow navigation did not change page"
QTest.keyClick(window, Qt.Key_Left)
assert dashboard.property("pageIndex") == 0
for width, height in ((480, 540), (800, 600), (1280, 800)):
    window.setWidth(width)
    window.setHeight(height)
    app.processEvents()
    assert dashboard.width() == width and dashboard.height() == height
QMetaObject.invokeMethod(window, "exerciseSinglePage", Qt.DirectConnection)
app.processEvents()
if warnings:
    raise SystemExit("QML warnings: " + "\n".join(warnings))
print("PASS: QML flow, confirmation gate, two-page navigation, search focus, single page, three sizes")
