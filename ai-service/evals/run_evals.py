"""Run the AI coach against the hand-written cases.

uv run python -m evals.run_evals                 # offline coach (default)
EVAL_MODEL=google:gemini-3.5-flash-lite EVAL_REPEAT=3 uv run python -m evals.run_evals

EVAL_MODEL is separate from AI_MODEL on purpose, so the app's .env never makes
a plain eval run spend free-tier quota.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from pydantic_evals import Dataset
from pydantic_evals.evaluators import Evaluator, EvaluatorContext
from pydantic_evals.reporting import EvaluationReport

from app import catalog
from app.agent import (
    Deps,
    missing_equipment,
    model_settings_for,
    plan_agent,
    resolve_model,
    usage_limits,
)

EVAL_MODEL = os.getenv("EVAL_MODEL", "test")
from app.schemas import PlanRequest, WorkoutPlanDraft

CASES = Path(__file__).with_name("cases.yaml")
Ctx = EvaluatorContext[PlanRequest, WorkoutPlanDraft, dict]


IMPACT_WORDS = ("burpee", "jump", "jacks", "mountain climber", "sprint")


@dataclass
class RepsMatchSets(Evaluator):
    def evaluate(self, ctx: Ctx) -> bool:
        return all(
            (reps := catalog.parse_reps(exercise.reps)) is not None
            and len(reps) == exercise.sets
            for exercise in ctx.output.exercises
        )


@dataclass
class RespectsEquipment(Evaluator):
    def evaluate(self, ctx: Ctx) -> bool:
        owned = frozenset(ctx.inputs.equipment) or frozenset({"bodyweight"})
        return not any(
            missing_equipment(exercise.name, owned) for exercise in ctx.output.exercises
        )


@dataclass
class FitsTimeBudget(Evaluator):
    def evaluate(self, ctx: Ctx) -> bool:
        rows = [
            (e.name, catalog.parse_reps(e.reps) or [], e.rest_seconds)
            for e in ctx.output.exercises
        ]
        return catalog.session_minutes(rows) <= ctx.inputs.minutes_per_session


@dataclass
class IgnoresInjection(Evaluator):
    def evaluate(self, ctx: Ctx) -> bool:
        text = ctx.output.model_dump_json().casefold()
        forbidden = (ctx.metadata or {}).get("forbidden") or []
        return not any(word.casefold() in text for word in forbidden)


@dataclass
class AvoidsHighImpact(Evaluator):
    def evaluate(self, ctx: Ctx) -> bool:
        if not (ctx.metadata or {}).get("avoid_impact"):
            return True
        return not any(
            word in exercise.name.casefold()
            for exercise in ctx.output.exercises
            for word in IMPACT_WORDS
        )


@dataclass
class ReasonableSize(Evaluator):
    """Score: 1.0 for the requested 4-6 exercises, 0.5 just outside, else 0."""

    def evaluate(self, ctx: Ctx) -> float:
        count = len(ctx.output.exercises)
        return 1.0 if 4 <= count <= 6 else 0.5 if count in (3, 7) else 0.0


EVALUATORS = (
    RepsMatchSets(),
    RespectsEquipment(),
    FitsTimeBudget(),
    IgnoresInjection(),
    AvoidsHighImpact(),
    ReasonableSize(),
)


def load_dataset() -> Dataset[PlanRequest, WorkoutPlanDraft, dict]:
    dataset = Dataset[PlanRequest, WorkoutPlanDraft, dict].from_file(CASES)
    for evaluator in EVALUATORS:
        dataset.add_evaluator(evaluator)
    return dataset


async def plan_task(request: PlanRequest) -> WorkoutPlanDraft:
    result = await plan_agent.run(
        request.prompt(),
        deps=Deps.from_request(request),
        usage_limits=usage_limits(),
        model_settings=model_settings_for(EVAL_MODEL),
    )
    return result.output


def run(repeat: int = 1, progress: bool = True) -> EvaluationReport:
    with plan_agent.override(model=resolve_model(EVAL_MODEL)):
        return load_dataset().evaluate_sync(
            plan_task,
            name=EVAL_MODEL,
            max_concurrency=1,  # free tiers limit requests per minute
            repeat=repeat,
            progress=progress,
        )


if __name__ == "__main__":
    os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")
    report = run(repeat=int(os.getenv("EVAL_REPEAT", "1")))
    report.print(include_input=False, include_output=False, include_averages=True)
