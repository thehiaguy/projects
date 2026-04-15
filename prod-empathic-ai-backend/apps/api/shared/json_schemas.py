from pathlib import Path
from typing import Any
from functools import lru_cache
import json


def get_schema_base_dir() -> Path:
    local_dir = Path(__file__).resolve().parent / "schemas"
    if local_dir.exists():
        return local_dir

    repo_root = Path(__file__).resolve().parents[3]
    shared_dir = repo_root / "packages" / "shared" / "schemas"
    if shared_dir.exists():
        return shared_dir

    return local_dir


@lru_cache(maxsize=32)
def load_json_schema(schema_name: str) -> dict[str, Any]:
    normalized_name = schema_name if schema_name.endswith(".json") else f"{schema_name}.json"
    schema_path = get_schema_base_dir() / normalized_name
    if not schema_path.exists():
        raise FileNotFoundError(f"JSON schema not found: {schema_path}")

    with schema_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"JSON schema {normalized_name} must contain an object at the top level")
    return payload


def validate_against_schema(*, payload: dict[str, Any], schema_name: str) -> None:
    schema = load_json_schema(schema_name)
    try:
        from jsonschema import validate
    except ImportError as exc:
        raise RuntimeError(
            "JSON schema validation requires the `jsonschema` package to be installed."
        ) from exc

    validate(instance=payload, schema=schema)
