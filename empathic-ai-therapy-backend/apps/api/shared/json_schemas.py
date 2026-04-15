import json
from functools import lru_cache
from pathlib import Path
from typing import Any


def get_schema_base_dir() -> Path:
    return Path(__file__).parent / "schemas"


@lru_cache(maxsize=32)
def _load_cached(schema_path: str) -> str:
    return Path(schema_path).read_text(encoding="utf-8")


def load_json_schema(schema_name: str) -> dict[str, Any]:
    name = schema_name if schema_name.endswith(".json") else f"{schema_name}.json"
    path = get_schema_base_dir() / name
    raw = _load_cached(str(path))
    return json.loads(raw)


def validate_against_schema(*, payload: dict[str, Any], schema_name: str) -> None:
    try:
        import jsonschema
    except ImportError:
        return

    schema = load_json_schema(schema_name)
    jsonschema.validate(instance=payload, schema=schema)
