import asyncio
import logging
import os

from fastapi import FastAPI, HTTPException, Response, status
from pydantic_ai.exceptions import (
    FallbackExceptionGroup,
    ModelAPIError,
    ModelHTTPError,
    ModelTimeoutError,
    UnexpectedModelBehavior,
    UsageLimitExceeded,
    UserError,
)

from app.agent import (
    MODEL_NAME,
    PER_MODEL_TIMEOUT_SECONDS,
    Deps,
    is_offline,
    model_names,
    model_settings_for,
    plan_agent,
    usage_limits,
)
from app.baseline import build_plan
from app.schemas import PlanRequest, WorkoutPlanDraft

logger = logging.getLogger("ai-service")
if not logger.handlers:  # show INFO lines ("plan ok: …") next to uvicorn's logs
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("ai-service %(levelname)s: %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
# Worst case with two models: each gets a fast 503 + one retry + an 8 s
# timeout (about 9.5 s), so about 19 s; the offline coach then answers in
# milliseconds. The backend waits up to 30 s per attempt.
RUN_TIMEOUT_SECONDS = 25
# One quick retry when a model answers "busy" (503), then the next model.
BUSY_RETRY_DELAY_SECONDS = 0.75
# When every real model failed, answer with the offline coach instead.
FALLBACK = os.getenv("AI_FALLBACK", "baseline") != "off"


class AllModelsFailed(Exception):
    """Every model in AI_MODEL failed; `errors` holds one entry per attempt."""

    def __init__(self, errors: list[BaseException]):
        super().__init__(f"{len(errors)} model attempts failed")
        self.errors = errors


FALLBACK_ERRORS = (
    UsageLimitExceeded,
    ModelAPIError,  # includes 429 quota, 503 busy, timeouts, bad key (401/403)
    UnexpectedModelBehavior,
    TimeoutError,
    UserError,  # e.g. AI_MODEL=google:... but GOOGLE_API_KEY is missing
    FallbackExceptionGroup,
    AllModelsFailed,
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
    # Log error classes and status codes only: never the user's text.
    logger.warning("plan failed -> %s: %s", code, _reason(exc))
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
    if isinstance(exc, ModelAPIError | FallbackExceptionGroup | AllModelsFailed):
        return _fail(status.HTTP_500_INTERNAL_SERVER_ERROR, "AI provider failed", exc)
    return _fail(status.HTTP_504_GATEWAY_TIMEOUT, "AI model timed out", exc)


def _kind(exc: BaseException) -> str:
    """Short label for logs: '503', 'timeout', '429', ... Never user text."""
    if isinstance(exc, ModelTimeoutError | TimeoutError):
        return "timeout"
    status_code = getattr(exc, "status_code", None)
    return str(status_code) if status_code else type(exc).__name__


async def _run_once(body: PlanRequest, model: str | None):
    return await plan_agent.run(
        body.prompt(),
        model=model,
        deps=Deps.from_request(body),
        usage_limits=usage_limits(),
        model_settings=model_settings_for(model or MODEL_NAME),
    )


async def _run_chain(body: PlanRequest):
    """Try each model in AI_MODEL in order, failing fast.

    - 503 "high demand": one quick retry after 0.75 s, then the next model.
    - timeout (8 s per call), quota, invalid output: straight to the next model.
    - missing/invalid API key: stop, every Google model would fail the same way.
    """
    names = model_names(MODEL_NAME)
    if not names:  # offline coach
        return await _run_once(body, None)
    errors: list[BaseException] = []
    for name in names:
        short = name.split(":", 1)[-1]
        for attempt in (1, 2):
            try:
                async with asyncio.timeout(PER_MODEL_TIMEOUT_SECONDS + 2):
                    return await _run_once(body, name)
            except (
                ModelAPIError,
                TimeoutError,
                UsageLimitExceeded,
                UnexpectedModelBehavior,
            ) as exc:
                errors.append(exc)
                kind = _kind(exc)
                if kind in {"401", "403"}:
                    raise
                if kind == "503" and attempt == 1:
                    logger.info(
                        "%s busy (503); retrying in %ss",
                        short,
                        BUSY_RETRY_DELAY_SECONDS,
                    )
                    await asyncio.sleep(BUSY_RETRY_DELAY_SECONDS)
                    continue
                logger.warning("%s failed: %s; trying the next model", short, kind)
                break
    raise AllModelsFailed(errors)


def _describe(exc: BaseException) -> str:
    """e.g. 'gemini-3.5-flash-lite ModelUnavailableError 503'. Never user text."""
    model = getattr(exc, "model_name", "")
    status_code = getattr(exc, "status_code", "")
    return " ".join(
        str(part) for part in (model, type(exc).__name__, status_code) if part
    )


def _reason(exc: Exception) -> str:
    if isinstance(exc, AllModelsFailed):
        return "all models failed: " + "; ".join(
            f"{getattr(error, 'model_name', '') or '?'} {_kind(error)}"
            for error in exc.errors
        )
    if isinstance(exc, FallbackExceptionGroup):
        return "all models failed: " + "; ".join(
            _describe(inner) for inner in exc.exceptions
        )
    return _describe(exc)


@app.post("/plan")
async def create_plan(body: PlanRequest, response: Response) -> WorkoutPlanDraft:
    try:
        async with asyncio.timeout(RUN_TIMEOUT_SECONDS):
            result = await _run_chain(body)
    except FALLBACK_ERRORS as exc:
        if not FALLBACK or is_offline(MODEL_NAME):
            raise _error_response(exc) from exc
        logger.warning("plan used the offline coach: %s", _reason(exc))
        response.headers["X-Plan-Source"] = "offline"
        return WorkoutPlanDraft.model_validate(build_plan(body))

    usage = result.usage
    logger.info(
        "plan ok: model=%s requests=%s tool_calls=%s tokens=%s",
        result.response.model_name,
        usage.requests,
        usage.tool_calls,
        usage.total_tokens,
    )
    response.headers["X-Plan-Source"] = "ai"
    return result.output
