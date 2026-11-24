"""HTTP client for the ai-service.

The ai-service owns the plan contract (``ai-service/app/schemas.py``). This
module keeps the backend's own copy and validates every response against it;
``tests/test_contract.py`` checks that both copies still agree.
"""

import logging
import os
from collections.abc import Iterator
from typing import Annotated, Literal

import httpx
from fastapi import Depends
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from tenacity import (
    Retrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from app.models.workout import Equipment

logger = logging.getLogger("backend.ai_client")

# One limit per phase. The frontend waits longer (100 s) than our worst case.
TIMEOUT = httpx.Timeout(connect=2.0, write=5.0, read=30.0, pool=2.0)
TRANSIENT_STATUS = {503, 504}
MAX_ATTEMPTS = 3  # bounded: 1 try + 2 retries
RETRY_WAIT = wait_exponential(multiplier=0.5, max=4)


class AIServiceUnavailable(Exception):
    """Nothing usable came back: refused, timed out, or the AI service failed."""


class AIServiceBadOutput(Exception):
    """The AI service answered, but the answer breaks the contract."""


class PerformedExercise(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    reps: str = Field(default="", max_length=1000)


class HistoryItem(BaseModel):
    workout_name: str = Field(min_length=1, max_length=200)
    completed_on: str = Field(min_length=10, max_length=10)
    exercises: list[PerformedExercise] = Field(default_factory=list, max_length=100)


class PlanRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=100)
    experience_level: str = Field(min_length=1, max_length=50)
    equipment: list[Equipment] = Field(min_length=1, max_length=8)
    days_per_week: int = Field(ge=1, le=7)
    minutes_per_session: int = Field(ge=10, le=180)
    notes: str = Field(default="", max_length=500)
    plan_name: str = Field(default="", max_length=200)
    recent_history: list[HistoryItem] = Field(default_factory=list, max_length=3)


class PlannedExercise(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = Field(min_length=1, max_length=200)
    sets: int = Field(ge=1, le=10)
    reps: str = Field(min_length=1, max_length=200)
    rest_seconds: int = Field(ge=0, le=600)
    notes: str = Field(default="", max_length=200)


class WorkoutPlanDraft(BaseModel):
    # Ignoring unknown fields keeps us compatible when the AI adds optional ones.
    model_config = ConfigDict(extra="ignore")

    title: str = Field(min_length=1, max_length=200)
    icon: Literal["weights", "running", "cycling", "yoga", "swimming", "boxing"]
    frequency_per_week: int = Field(ge=1, le=7)
    exercises: list[PlannedExercise] = Field(min_length=1, max_length=12)
    coach_notes: str = Field(default="", max_length=500)


def _is_transient(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in TRANSIENT_STATUS
    return isinstance(exc, (httpx.TimeoutException, httpx.ConnectError))


class AIClient:
    def __init__(self, base_url: str, transport: httpx.BaseTransport | None = None):
        self._client = httpx.Client(
            base_url=base_url, timeout=TIMEOUT, transport=transport
        )

    def close(self) -> None:
        self._client.close()

    def _post(self, payload: dict) -> httpx.Response:
        for attempt in Retrying(
            stop=stop_after_attempt(MAX_ATTEMPTS),
            wait=RETRY_WAIT,
            retry=retry_if_exception(_is_transient),
            reraise=True,
        ):
            with attempt:
                response = self._client.post("/plan", json=payload)
                response.raise_for_status()
                return response
        raise AssertionError("unreachable")  # pragma: no cover

    def plan(self, request: PlanRequest) -> WorkoutPlanDraft:
        try:
            response = self._post(request.model_dump(mode="json"))
        # HTTPStatusError subclasses HTTPError, so it must be caught first.
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code
            logger.warning("ai-service answered %s", code)
            if code == 502 or (400 <= code < 500 and code != 429):
                raise AIServiceBadOutput from exc
            raise AIServiceUnavailable from exc
        except httpx.HTTPError as exc:
            logger.warning("ai-service unreachable: %s", type(exc).__name__)
            raise AIServiceUnavailable from exc

        try:
            return WorkoutPlanDraft.model_validate(response.json())
        except (ValueError, ValidationError) as exc:
            logger.warning("ai-service broke the contract")
            raise AIServiceBadOutput from exc


def get_ai_client() -> Iterator[AIClient]:
    client = AIClient(os.getenv("AI_SERVICE_URL", "http://localhost:8001"))
    try:
        yield client
    finally:
        client.close()


AIClientDep = Annotated[AIClient, Depends(get_ai_client)]
