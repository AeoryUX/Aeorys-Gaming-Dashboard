#!/usr/bin/env bash
# Produce the exact reproducible source artifact referenced by the review PKGBUILD.
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"
tar --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner --mode='u+rwX,go+rX,go-w' \
    --exclude=__pycache__ --exclude='*.pyc' \
    --transform='s,^,aeory-gaming-dashboard-0.1.0/,' \
    -cf - backend components scripts shell.qml README.md LICENSE tests requirements-dev.txt docs \
    | gzip -n > packaging/aeory-gaming-dashboard-0.1.0.tar.gz
sha256sum packaging/aeory-gaming-dashboard-0.1.0.tar.gz
