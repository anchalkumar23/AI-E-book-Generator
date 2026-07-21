"""Engine bootstrap.

Picks a free loopback port, mints an auth token, then runs uvicorn.
The handshake line is printed by main.py's lifespan once the app is up.
Exits automatically if the parent process (the Tauri shell) goes away.
"""
import os
import secrets
import socket
import sys
import threading

import uvicorn


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _exit_when_parent_dies() -> None:
    """Blocks until stdin closes, which happens when the parent process exits."""
    for _ in sys.stdin:
        pass
    os._exit(0)


def main() -> None:
    port = _free_port()
    os.environ["ENGINE_PORT"] = str(port)
    os.environ["ENGINE_TOKEN"] = secrets.token_urlsafe(32)
    if len(sys.argv) > 1:
        os.environ["ENGINE_DB_DIR"] = sys.argv[1]

    threading.Thread(target=_exit_when_parent_dies, daemon=True).start()

    # Absolute, not `from .main`: frozen by PyInstaller this file runs as
    # __main__ with no parent package, and a relative import dies with
    # "attempted relative import with no known parent package".
    from app.main import app  # imported after env vars are set

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
