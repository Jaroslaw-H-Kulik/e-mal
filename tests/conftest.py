"""
Layer 0 test harness: runs the real server.py as a subprocess against an
isolated copy of the data files, so tests exercise the actual HTTP API with
no mocking and can never touch the real data/genealogy_new_model.json.

server.py resolves 'data/...' paths relative to the process working
directory, and resolves data/documents relative to its own file location
(__file__) - copying server.py into the sandbox and launching it with the
sandbox as cwd satisfies both.
"""
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests

REPO_ROOT = Path(__file__).resolve().parent.parent

# Files/dirs copied into every sandbox. Kept minimal on purpose: the full
# data/ directory is ~424MB (mostly scanned document images) which would
# make every test slow to set up for no benefit while we're only exercising
# person/event/relationship endpoints.
SANDBOX_COPY = ["server.py", "web"]
SANDBOX_DATA_FILES = ["genealogy_new_model.json", "documents.json"]

STARTUP_TIMEOUT_SECONDS = 10


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_until_up(base_url: str, timeout: float) -> None:
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        try:
            requests.get(f"{base_url}/data/genealogy_new_model.json", timeout=0.5)
            return
        except requests.exceptions.ConnectionError as exc:
            last_error = exc
            time.sleep(0.1)
    raise RuntimeError(f"Server at {base_url} did not start within {timeout}s: {last_error}")


class LiveServer:
    """Handle to a sandboxed server.py instance for one test."""

    def __init__(self, base_url: str, sandbox_dir: Path):
        self.base_url = base_url
        self.sandbox_dir = sandbox_dir

    def get_state(self) -> dict:
        """Fetch the full persisted data file exactly as the frontend does."""
        resp = requests.get(f"{self.base_url}/data/genealogy_new_model.json")
        resp.raise_for_status()
        return resp.json()

    def post(self, endpoint: str, payload: dict) -> requests.Response:
        return requests.post(f"{self.base_url}{endpoint}", json=payload)


@pytest.fixture
def live_server(tmp_path):
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()

    for name in SANDBOX_COPY:
        src = REPO_ROOT / name
        dst = sandbox / name
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)

    data_dir = sandbox / "data"
    data_dir.mkdir()
    for name in SANDBOX_DATA_FILES:
        shutil.copy2(REPO_ROOT / "data" / name, data_dir / name)
    (data_dir / "documents").mkdir()

    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"

    # Imports server.py and calls run_server(port) directly rather than
    # `python server.py`, since the file hardcodes port 8001 in its
    # __main__ block. This needs no change to server.py: run_server()
    # already accepts a port argument.
    proc = subprocess.Popen(
        [sys.executable, "-c", f"import server; server.run_server({port})"],
        cwd=str(sandbox),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    try:
        _wait_until_up(base_url, STARTUP_TIMEOUT_SECONDS)
    except Exception:
        proc.terminate()
        try:
            out, _ = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            out, _ = proc.communicate()
        raise RuntimeError(f"Server failed to start:\n{out}")

    yield LiveServer(base_url, sandbox)

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
