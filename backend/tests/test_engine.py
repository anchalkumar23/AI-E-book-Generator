import json
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def test_engine_prints_handshake_line():
    """The engine must print exactly one JSON line with ready/port/token."""
    proc = subprocess.Popen(
        [sys.executable, "-m", "app.engine"],
        cwd=BACKEND,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        line = proc.stdout.readline()
        data = json.loads(line)
        assert data["ready"] is True
        assert isinstance(data["port"], int) and 1024 < data["port"] < 65536
        assert isinstance(data["token"], str) and len(data["token"]) >= 32
    finally:
        proc.kill()
        proc.wait(timeout=10)
