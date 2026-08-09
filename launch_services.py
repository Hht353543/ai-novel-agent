"""Launch backend and frontend as detached background processes (Windows)."""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(ROOT, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

DETACHED = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200


def start(cmd, cwd, name):
    """Start a process detached, with stdout/stderr written to logs."""
    out = open(os.path.join(LOG_DIR, name + ".out.log"), "w", encoding="utf-8")
    err = open(os.path.join(LOG_DIR, name + ".err.log"), "w", encoding="utf-8")
    return subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=out,
        stderr=err,
        stdin=subprocess.DEVNULL,
        creationflags=DETACHED | CREATE_NEW_PROCESS_GROUP,
        close_fds=True,
    )


backend = start(
    [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
    os.path.join(ROOT, "backend"),
    "backend",
)
frontend = start(
    ["npm.cmd", "run", "dev"],
    os.path.join(ROOT, "frontend"),
    "frontend",
)

print(f"backend PID={backend.pid}, frontend PID={frontend.pid}")
