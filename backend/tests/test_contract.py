"""The backend's copy of the AI contract must match the ai-service schema.

Regenerate the snapshot after an intentional ai-service change:
    cd ai-service && uv run python -c "import json; from app.main import app; \
print(json.dumps(app.openapi()))" > ../backend/tests/ai_openapi.json
"""

import json
from pathlib import Path

import pytest
from pydantic import BaseModel

from app import ai_client

SNAPSHOT = json.loads((Path(__file__).parent / "ai_openapi.json").read_text())
LIMITS = ("type", "enum", "minLength", "maxLength", "minimum", "maximum")
LIMITS += ("minItems", "maxItems")


def normalize(schema: dict, defs: dict) -> dict:
    """Field name -> (required, constraints) with $refs resolved by name."""
    required = set(schema.get("required", []))
    fields = {}
    for name, prop in schema["properties"].items():
        items = prop.get("items", {})
        fields[name] = (
            name in required,
            {key: prop[key] for key in LIMITS if key in prop},
            {key: items[key] for key in LIMITS if key in items},
            (items.get("$ref") or prop.get("$ref") or "").rsplit("/", 1)[-1],
        )
    return fields


def backend_schema(model: type[BaseModel]) -> tuple[dict, dict]:
    schema = model.model_json_schema(ref_template="#/components/schemas/{model}")
    return schema, schema.get("$defs", {})


@pytest.mark.parametrize(
    "model",
    [
        ai_client.PlanRequest,
        ai_client.HistoryItem,
        ai_client.PerformedExercise,
        ai_client.WorkoutPlanDraft,
        ai_client.PlannedExercise,
    ],
)
def test_backend_model_matches_ai_service(model):
    ours, ours_defs = backend_schema(model)
    theirs = SNAPSHOT["components"]["schemas"][model.__name__]
    defs = SNAPSHOT["components"]["schemas"]

    assert normalize(ours, ours_defs) == normalize(theirs, defs)


def test_backend_calls_the_documented_path():
    plan = SNAPSHOT["paths"]["/plan"]["post"]
    request_ref = plan["requestBody"]["content"]["application/json"]["schema"]
    response_ref = plan["responses"]["200"]["content"]["application/json"]["schema"]

    assert request_ref["$ref"].endswith("/PlanRequest")
    assert response_ref["$ref"].endswith("/WorkoutPlanDraft")
