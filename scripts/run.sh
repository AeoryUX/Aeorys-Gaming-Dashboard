#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
bash "$project_dir/scripts/check-deps.sh"
echo 'Start this process, then use scripts/toggle.sh from another terminal to show the dashboard.'
exec qs -p "$project_dir" --no-duplicate
