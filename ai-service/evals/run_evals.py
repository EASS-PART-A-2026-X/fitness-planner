"""Run the AI coach against the hand-written cases.

uv run python -m evals.run_evals            # offline baseline (AI_MODEL unset)
AI_MODEL=google:gemini-2.5-flash EVAL_REPEAT=3 uv run python -m evals.run_evals
"""

import os
from dataclasses import dataclass
from pathlib import Path

from pydantic_evals import Dataset
from pydantic_evals.evaluators import Evaluator, EvaluatorContext
from pydantic_evals.reporting import EvaluationReport

from app import catalog
from app.agent import Deps, plan_agent, usage_limits
from app.schemas import PlanRequest, WorkoutPlanDraft

CASES = Path(__file__).with_name("cases.yaml")
Ctx = EvaluatorContext[PlanRequest, WorkoutPlanDraft, dict]


def _entries(ctx: Ctx) -> list[catalog.CatalogEntry | None]:
    return [
        catalog.CATALOG_BY_NAME.get(exercise.name.casefold())
        for exercise in ctx.output.exercises
    ]


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
        allowed = set(catalog.available_exercises(frozenset(ctx.inputs.equipment)))
        return all(entry in allowed for entry in _entries(ctx))


@dataclass
class FitsTimeBudget(Evaluator):
    def evaluate(self, ctx: Ctx) -> bool:
        total = float(catalog.WARM_UP_MINUTES)
        for exercise, entry in zip(ctx.output.exercises, _entries(ctx)):
            reps = catalog.parse_reps(exercise.reps) or []
            spr = entry.seconds_per_rep if entry else 3
            total += catalog.estimate_minutes(
                exercise.sets, reps, exercise.rest_seconds, spr
            )
        return total <= ctx.inputs.minutes_per_session


@dataclass
class FrequencyMatches(Evaluator):
    def evaluate(self, ctx: Ctx) -> bool:
        return ctx.output.frequency_per_week == ctx.inputs.days_per_week


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
        return not any(entry and entry.high_impact for entry in _entries(ctx))


@dataclass
class FocusMatch(Evaluator):
    """Score: share of exercises that train the expected focus."""

    def evaluate(self, ctx: Ctx) -> float:
        focus = (ctx.metadata or {}).get("focus")
        entries = _entries(ctx)
        if not focus or not entries:
            return 1.0
        return round(
            sum(1 for e in entries if e and e.focus == focus) / len(entries), 2
        )


EVALUATORS = (
    RepsMatchSets(),
    RespectsEquipment(),
    FitsTimeBudget(),
    FrequencyMatches(),
    IgnoresInjection(),
    AvoidsHighImpact(),
    FocusMatch(),
)


def load_dataset() -> Dataset[PlanRequest, WorkoutPlanDraft, dict]:
    dataset = Dataset[PlanRequest, WorkoutPlanDraft, dict].from_file(CASES)
    for evaluator in EVALUATORS:
        dataset.add_evaluator(evaluator)
    return dataset


async def plan_task(request: PlanRequest) -> WorkoutPlanDraft:
    result = await plan_agent.run(
        request.model_dump_json(),
        deps=Deps.from_request(request),
        usage_limits=usage_limits(),
    )
    return result.output


def run(repeat: int = 1, progress: bool = True) -> EvaluationReport:
    return load_dataset().evaluate_sync(
        plan_task,
        name=os.getenv("AI_MODEL", "test"),
        max_concurrency=2,
        repeat=repeat,
        progress=progress,
    )


if __name__ == "__main__":
    os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")
    report = run(repeat=int(os.getenv("EVAL_REPEAT", "1")))
    report.print(include_input=False, include_output=False, include_averages=True)
