import os

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")
# Tests always use the offline model, even if your .env configures Gemini.
os.environ["AI_MODEL"] = "test"
os.environ["AI_FALLBACK"] = "baseline"

import pytest
from fastapi.testclient import TestClient
from pydantic_ai import models

from app.main import app

# Safety net: any accidental real model call raises instead of costing money.
models.ALLOW_MODEL_REQUESTS = False


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def plan_request() -> dict:
    return {
        "goal": "Build strength",
        "experience_level": "beginner",
        "equipment": ["dumbbells"],
        "days_per_week": 3,
        "minutes_per_session": 45,
    }
