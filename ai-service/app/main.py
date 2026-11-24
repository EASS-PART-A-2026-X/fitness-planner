import asyncio
import logging
import os

from fastapi import FastAPI, HTTPException, Response, status
from pydantic_ai.exceptions import (
    ModelAPIError,
    ModelHTTPError,
    UnexpectedModelBehavior,
    UsageLimitExceeded,
    UserError,
)

from app.agent import (
    MODEL_NAME,
    Deps,
    is_offline,
    model_settings_for,
    plan_agent,
    usage_limits,
)
from app.baseline import build_plan
from app.schemas import PlanRequest, WorkoutPlanDraft

logger = logging.getLogger("ai-service")
# Real model gets 20 s; the offline fallback answers in milliseconds, so the
# whole request still fits the 25 s budget the backend expects.
RUN_TIMEOUT_SECONDS = 20
# When a real model is out of quota or failing, answer with the offline planner.
FALLBACK = os.getenv("AI_FALLBACK", "baseline") != "off"
FALLBACK_ERRORS = (
    UsageLimitExceeded,
    ModelAPIError,  # includes ModelHTTPError: Gemini free-tier 429s, 5xx, bad key
    UnexpectedModelBehavior,
    TimeoutError,
    UserError,  # e.g. AI_MODEL=google:... but GOOGLE_API_KEY is missing
)

app = FastAPI(
    title="Fitness Planner AI Coach",
    description="Drafts structured workout plans with a Pydantic AI agent.",
    version="1.0.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _fail(code: int, detail: str, exc: Exception) -> HTTPException:
    # Log the class and status only: never the user's text.
    logger.warning("plan failed: %s -> %s", type(exc).__name__, code)
    return HTTPException(status_code=code, detail=detail)


def _error_response(exc: Exception) -> HTTPException:
    if isinstance(exc, UsageLimitExceeded):
        return _fail(status.HTTP_429_TOO_MANY_REQUESTS, "AI budget exceeded", exc)
    if isinstance(exc, UnexpectedModelBehavior):
        return _fail(status.HTTP_502_BAD_GATEWAY, "AI returned invalid output", exc)
    if isinstance(exc, UserError) or (
        isinstance(exc, ModelHTTPError) and exc.status_code in {401, 403}
    ):
        return _fail(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "AI model misconfigured", exc
        )
    if isinstance(exc, ModelAPIError):
        return _fail(status.HTTP_500_INTERNAL_SERVER_ERROR, "AI provider failed", exc)
    return _fail(status.HTTP_504_GATEWAY_TIMEOUT, "AI model timed out", exc)


@app.post("/plan")
async def create_plan(body: PlanRequest, response: Response) -> WorkoutPlanDraft:
    try:
        async with asyncio.timeout(RUN_TIMEOUT_SECONDS):
            result = await plan_agent.run(
                body.model_dump_json(),
                deps=Deps.from_request(body),
                usage_limits=usage_limits(),
                model_settings=model_settings_for(MODEL_NAME),
            )
    except FALLBACK_ERRORS as exc:
        if not FALLBACK or is_offline(MODEL_NAME):
            raise _error_response(exc) from exc
        logger.warning("plan fell back to offline planner: %s", type(exc).__name__)
        response.headers["X-Plan-Source"] = "offline"
        return WorkoutPlanDraft.model_validate(build_plan(body))

    usage = result.usage
    logger.info(
        "plan ok: requests=%s tool_calls=%s tokens=%s",
        usage.requests,
        usage.tool_calls,
        usage.total_tokens,
    )
    response.headers["X-Plan-Source"] = "ai"
    return result.output
