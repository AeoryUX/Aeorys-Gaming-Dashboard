import QtQuick
import Quickshell
import Quickshell.Io

QtObject {
    id: root
    property var games: []
    property var history: ({continue_playing: [], most_played: [], status: "Steam play history has not been loaded.", warnings: []})
    property var warnings: []
    property var processes: []
    property var resources: ({gpus: [], cpu_temperatures: [], warnings: [], per_process_status: "GPU and temperature readings unavailable until refresh."})
    property string limitations: "Refresh running processes to inspect activity."
    property string message: ""
    property string notes: ""
    property string notesGame: ""
    property string operation: ""
    property bool busy: worker.running
    signal libraryLoaded()
    signal terminationSent(int pid, string token)
    signal processesRefreshed()
    property var currentArguments: []

    function request(arguments, input) {
        if (worker.running) {
            message = "Please wait for the current request to finish."
            return false
        }
        operation = arguments[0]
        currentArguments = arguments
        if (operation === "notes-get") notesGame = ""
        worker.input = input === undefined ? "" : input
        worker.stdinEnabled = operation === "notes-set"
        worker.command = ["python3", "-m", "backend"].concat(arguments)
        worker.running = true
        return true
    }

    property Process worker: Process {
        property string input: ""
        workingDirectory: Quickshell.shellDir
        onStarted: {
            if (stdinEnabled) {
                write(input)
                stdinEnabled = false
            }
        }
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const result = JSON.parse(text)
                    if (result.error) { root.message = result.error; return }
                    if (root.operation === "library") {
                        root.games = result.games
                        root.history = result.history
                        root.warnings = result.warnings
                        root.message = result.games.length ? "Library refreshed." : "No installed games found. Check Steam library paths and permissions."
                        root.libraryLoaded()
                    } else if (root.operation === "running") {
                        root.processes = result.processes
                        root.resources = result.resources
                        root.limitations = result.limitations
                        root.message = "Process scan complete."
                        root.processesRefreshed()
                    } else if (root.operation === "notes-get") {
                        root.notes = result.text
                        root.notesGame = root.currentArguments[1]
                    } else if (root.operation === "notes-set") {
                        root.message = "Personal notes saved locally."
                    } else {
                        root.message = result.message || "Request completed."
                        if (result.sent === "SIGTERM") root.terminationSent(result.pid, root.currentArguments[3])
                    }
                } catch (error) { root.message = "Backend returned unreadable output: " + error }
            }
        }
        stderr: StdioCollector {
            onStreamFinished: { if (text.trim()) root.message = "Backend diagnostic: " + text.trim() }
        }
        onExited: (exitCode, exitStatus) => {
            if (exitCode !== 0 && !root.message) root.message = "Backend failed; check Python 3 availability."
        }
    }
}
