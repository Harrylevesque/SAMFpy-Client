#!/bin/sh
set -e

# ── Auto-detect host OS if not explicitly set ─────────────────────────────────
if [ -z "$HOST_OS" ]; then
    # WSL kernel string → Windows host
    if [ -f /proc/version ] && grep -qi "microsoft" /proc/version 2>/dev/null; then
        HOST_OS="windows"
    # host.docker.internal resolves on Docker Desktop (Mac & Windows)
    elif getent hosts host.docker.internal >/dev/null 2>&1; then
        # Default to mac; user can override with -e HOST_OS=windows
        HOST_OS="mac"
    else
        HOST_OS="linux"
    fi
fi

export HOST_OS
echo "[SAMFpy] Host OS: $HOST_OS"

exec /app/.venv/bin/python -c "
import runpy
SAMFpy = runpy.run_path('/app/ui.py')['SAMFpy']
SAMFpy().run()
"

