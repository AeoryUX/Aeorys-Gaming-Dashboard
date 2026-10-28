#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
bash "$project_dir/scripts/check-deps.sh" >/dev/null
# IPC is scoped to this config path; never addresses Caelestia's own process.
if qs -p "$project_dir" ipc call dashboard toggle 2>/dev/null; then
    exit 0
fi
qs -p "$project_dir" --no-duplicate --daemonize
for attempt in {1..30}; do
    if qs -p "$project_dir" ipc call dashboard toggle 2>/dev/null; then
        exit 0
    fi
    sleep 0.1
done
echo 'Dashboard IPC did not become ready. Run scripts/run.sh in a terminal for diagnostics.' >&2
exit 1
