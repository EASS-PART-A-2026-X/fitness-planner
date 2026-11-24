import os
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

import fitness_planner_api as api

FRONTEND = Path(__file__).parents[1]
BACKEND = FRONTEND.parent / "backend"


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_backend(process: subprocess.Popen, url: str) -> None:
    deadline = time.monotonic() + 40
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("The test backend exited before becoming ready.")
        try:
            with urllib.request.urlopen(url, timeout=1):
                return
        except urllib.error.URLError, TimeoutError:
            time.sleep(0.25)
    raise TimeoutError("The test backend did not become ready.")


def test_workout_crud_against_live_backend(tmp_path, monkeypatch):
    if shutil.which("uv") is None:
        raise RuntimeError("uv is required to run the frontend integration test.")

    port = free_port()
    backend_url = f"http://127.0.0.1:{port}"
    process = subprocess.Popen(
        [
            "uv",
            "run",
            "--project",
            str(BACKEND),
            "fastapi",
            "run",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=BACKEND,
        env=os.environ | {"DATABASE_URL": f"sqlite:///{tmp_path / 'integration.db'}"},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )

    try:
        wait_for_backend(process, f"{backend_url}/health")
        monkeypatch.setattr(api, "BACKEND_URL", backend_url)

        token = api.register("integration-user", "a-secure-password")["access_token"]
        created = api.create_workout(
            token,
            {
                "emoji": "🏃",
                "title": "Integration plan",
                "goal": "Build strength",
                "frequency_per_week": 3,
                "experience_level": "beginner",
                "exercises": [{"exercise": "Squats", "count": 12}],
            },
        )
        updated = api.update_workout(
            token,
            created["id"],
            {
                "emoji": "🏃",
                "title": "Updated integration plan",
                "goal": "Build strength",
                "frequency_per_week": 3,
                "experience_level": "beginner",
                "exercises": [{"exercise": "Squats", "count": 12}],
            },
        )

        assert updated["title"] == "Updated integration plan"
        assert updated["emoji"] == "🏃"
        assert api.list_workouts(token)[-1]["title"] == updated["title"]
        assert api.complete_workout(token, created["id"])["completed_this_week"] == 1

        api.delete_workout(token, created["id"])
        assert all(
            workout["id"] != created["id"] for workout in api.list_workouts(token)
        )
    finally:
        process.terminate()
        process.wait(timeout=10)
