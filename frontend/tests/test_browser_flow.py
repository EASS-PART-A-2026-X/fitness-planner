"""Real-browser flows against all three services (run with `uv run pytest -m e2e`)."""

import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page, expect, sync_playwright

FRONTEND = Path(__file__).parents[1]
ROOT = FRONTEND.parent
pytestmark = pytest.mark.e2e


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for(process: subprocess.Popen, url: str) -> None:
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Server exited before becoming ready: {url}")
        try:
            with urllib.request.urlopen(url, timeout=1):
                return
        except urllib.error.URLError, TimeoutError:
            time.sleep(0.25)
    raise TimeoutError(f"Server did not become ready: {url}")


def api(base: str, path: str, *, method="GET", token=None, payload=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        f"{base}{path}",
        data=json.dumps(payload).encode() if payload is not None else None,
        headers=headers,
        method=method,
    )
    with urllib.request.urlopen(request) as response:
        return json.load(response) if response.status != 204 else None


def uv_server(project: Path, port: int, env: dict) -> subprocess.Popen:
    return subprocess.Popen(
        ["uv", "run", "--project", str(project), "fastapi", "run"]
        + ["--host", "127.0.0.1", "--port", str(port)],
        cwd=project,
        env=os.environ | env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )


@pytest.fixture(scope="module")
def stack(tmp_path_factory) -> Iterator[dict]:
    if shutil.which("uv") is None:
        pytest.skip("Install uv to run the browser end-to-end test.")
    ports = {name: free_port() for name in ("ai", "backend", "frontend")}
    urls = {name: f"http://127.0.0.1:{port}" for name, port in ports.items()}
    db = tmp_path_factory.mktemp("e2e") / "e2e.db"
    processes = [
        uv_server(
            ROOT / "ai-service",
            ports["ai"],
            # Offline coach: e2e runs must not spend the .env's free-tier quota.
            {"PYDANTIC_AI_NO_BANNER": "1", "AI_MODEL": "test"},
        ),
        uv_server(
            ROOT / "backend",
            ports["backend"],
            {"DATABASE_URL": f"sqlite:///{db}", "AI_SERVICE_URL": urls["ai"]},
        ),
    ]
    try:
        wait_for(processes[0], f"{urls['ai']}/health")
        wait_for(processes[1], f"{urls['backend']}/health")
        processes.append(
            subprocess.Popen(
                [sys.executable, "-m", "streamlit", "run", "streamlit_app.py"]
                + ["--server.address", "127.0.0.1", "--server.headless", "true"]
                + ["--server.port", str(ports["frontend"])],
                cwd=FRONTEND,
                # An empty key keeps analytics off (the real .env key is ignored).
                env=os.environ
                | {"BACKEND_URL": urls["backend"], "POSTHOG_API_KEY": ""},
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
            )
        )
        wait_for(processes[2], f"{urls['frontend']}/_stcore/health")
        yield urls
    finally:
        for process in processes:
            process.terminate()
            process.wait(timeout=10)


@pytest.fixture
def signed_in(stack) -> Iterator[tuple[Page, str]]:
    username = f"user-{uuid.uuid4().hex[:8]}"
    token = api(
        stack["backend"],
        "/auth/register",
        method="POST",
        payload={"username": username, "password": "a-secure-password"},
    )["access_token"]
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch()
        except PlaywrightError as exc:
            pytest.skip(
                f"Install Chromium: `uv run playwright install chromium` ({exc})"
            )
        page = browser.new_page(viewport={"width": 1400, "height": 1000})
        page.context.add_cookies(
            [
                {
                    "name": "fitness_planner_session",
                    "value": token,
                    "url": stack["frontend"],
                }
            ]
        )
        page.goto(stack["frontend"])
        expect(page.get_by_text(f"Signed in as {username}")).to_be_visible(
            timeout=20000
        )
        try:
            yield page, token
        finally:
            browser.close()


def test_create_train_and_delete_a_plan(stack, signed_in):
    page, token = signed_in
    title = f"Browser plan {uuid.uuid4().hex[:6]}"

    page.get_by_role("button", name="Create your first plan").click()
    page.get_by_role("button", name="Choose Lower body").click()
    expect(page.get_by_text("step 2 of 2")).to_be_visible()
    page.get_by_label("Workout name").fill(title)
    page.get_by_label("Goal").fill("Build strength")
    page.get_by_label("Exercise name").fill("Squats")
    page.get_by_label("Sets", exact=True).fill("2")
    page.get_by_label("Reps", exact=True).fill("12")
    page.get_by_role("button", name="Create plan").last.click()
    expect(page.get_by_text(f"Created {title}")).to_be_visible()

    page.reload()
    # Each test user owns exactly one plan, so "View" is unique on the page.
    expect(page.get_by_text(title, exact=True)).to_be_visible()
    page.get_by_role("button", name="View").click()
    expect(page.get_by_text("Planned exercises")).to_be_visible()
    page.get_by_role("button", name="Start workout").click()

    reps = page.get_by_label("Actual reps completed")
    reps.fill("9")
    reps.press("Enter")
    page.get_by_role("button", name="Complete set").click()
    page.get_by_role("button", name="Skip rest").click()
    expect(page.get_by_text("Set 2 of 2")).to_be_visible()
    page.get_by_role("button", name="Complete set").click()
    expect(page.get_by_text("Squats complete.")).to_be_visible()
    page.get_by_role("button", name="Finish workout").click()
    # The big celebration overlay plays alongside the success notice.
    expect(page.locator(".fp-cel-title")).to_have_text("Workout complete!")
    expect(page.get_by_text("Workout complete!").last).to_be_visible()

    done = api(stack["backend"], "/workouts/recent-completions", token=token)[0]
    assert done["checked_exercises"] == [
        {"name": "Squats", "sets": 2, "reps": "9, 12", "rest_seconds": 60}
    ]

    page.get_by_role("button", name="Plans", exact=True).click()
    expect(page.get_by_text("Training plans", exact=True)).to_be_visible()
    page.locator('[class*="st-key-fp-trash-"] button').first.click()
    dialog = page.get_by_role("dialog")
    expect(dialog.get_by_text("can't be undone")).to_be_visible()
    dialog.get_by_role("button", name="Delete plan").click()
    expect(page.get_by_text(f"Deleted {title}")).to_be_visible()
    assert api(stack["backend"], "/workouts", token=token) == []


def test_ai_fills_exercises_then_the_plan_is_saved(stack, signed_in):
    page, token = signed_in

    page.get_by_role("button", name="Create", exact=False).first.click()
    page.get_by_role("button", name="Choose Running").click()
    expect(page.get_by_text("step 2 of 2")).to_be_visible()
    page.get_by_label("Goal").fill("Run a 5k")
    page.get_by_role("button", name="Generate exercises").click()

    expect(page.get_by_text("Coach", exact=True)).to_be_visible(timeout=20000)
    assert api(stack["backend"], "/workouts", token=token) == []

    page.get_by_role("button", name="Create plan").last.click()
    expect(page.get_by_text("Created Running")).to_be_visible()
    plans = api(stack["backend"], "/workouts", token=token)
    assert len(plans) == 1
    assert plans[0]["goal"] == "Run a 5k"
    assert plans[0]["emoji"] == "running"
