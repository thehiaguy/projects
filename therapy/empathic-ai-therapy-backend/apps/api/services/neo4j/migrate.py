from pathlib import Path

from domain.enums import ConceptLabel
from services.neo4j.driver import get_driver
from utils.errors import AppError

_DEFAULT_CONSTRAINTS_PATH = Path(__file__).resolve().parent / "cypher" / "constraints.cypher"
_FULLTEXT_INDEX_NAME = "concept_canonical_fulltext"


def load_constraints_cypher(file_path: Path) -> str:
    """
    Purpose:
        Read the Neo4j migration script containing constraints/indexes for the session-scoped graph schema.

    Inputs:
        - `file_path`: path to `services/neo4j/cypher/constraints.cypher`.

    Returns:
        Raw Cypher script string.

    Data structures / implementation notes:
        - Support relative path resolution from this module
        - Optional future support: multiple migration files and version tracking
    """
    resolved_path = file_path
    if not resolved_path.is_absolute():
        resolved_path = Path(__file__).resolve().parent / file_path
    return resolved_path.read_text(encoding="utf-8")


def run_migrations() -> dict[str, object]:
    """
    Purpose:
        Apply Neo4j constraints/indexes required by the backend before session traffic is handled.

    Inputs:
        None. Uses shared driver + configured database.

    Returns:
        Summary object with migration execution metadata, e.g.:
        - `applied: bool`
        - `statements_executed: int`
        - `database: str`
        - `errors: list[str]` (empty when successful)

    Data structures / implementation notes:
        - Split script into executable statements safely
        - Use `IF NOT EXISTS` in Cypher to make startup idempotent
        - Optionally run on startup or manual admin endpoint/CLI
    """
    from app.deps import get_settings

    statements = _split_cypher_statements(load_constraints_cypher(_DEFAULT_CONSTRAINTS_PATH))
    statements.extend(_generated_constraint_statements())
    statements.append(_fulltext_index_statement())

    driver = get_driver()
    database = get_settings().neo4j_database
    errors: list[str] = []

    try:
        with driver.session(database=database) as session:
            for statement in statements:
                try:
                    session.run(statement).consume()
                except Exception as exc:  # pragma: no cover - depends on live driver/runtime
                    errors.append(f"{statement}: {exc}")
    except Exception as exc:  # pragma: no cover - depends on live driver/runtime
        raise _build_app_error(
            code="neo4j_migration_failed",
            message="Failed to execute Neo4j migrations.",
            http_status=500,
            retryable=False,
            details={"database": database},
        ) from exc

    return {
        "applied": not errors,
        "statements_executed": len(statements) - len(errors),
        "database": database,
        "errors": errors,
    }


def _split_cypher_statements(script: str) -> list[str]:
    cleaned_lines: list[str] = []
    for line in script.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("//"):
            continue
        cleaned_lines.append(line)

    cleaned_script = "\n".join(cleaned_lines)
    return [statement.strip() for statement in cleaned_script.split(";") if statement.strip()]


def _generated_constraint_statements() -> list[str]:
    statements: list[str] = []
    for label in ConceptLabel.values():
        constraint_name = f"{label.lower()}_session_canonical_unique"
        statements.append(
            f"CREATE CONSTRAINT {constraint_name} IF NOT EXISTS "
            f"FOR (n:{label}) REQUIRE (n.sessionId, n.canonical) IS UNIQUE"
        )
    return statements


def _fulltext_index_statement() -> str:
    label_union = "|".join(ConceptLabel.values())
    return (
        f"CREATE FULLTEXT INDEX {_FULLTEXT_INDEX_NAME} IF NOT EXISTS "
        f"FOR (n:{label_union}) ON EACH [n.canonical]"
    )


def _build_app_error(
    *,
    code: str,
    message: str,
    http_status: int,
    retryable: bool,
    details: dict[str, object] | None = None,
) -> AppError:
    error = AppError(message)
    error.code = code
    error.message = message
    error.http_status = http_status
    error.retryable = retryable
    error.correlation_id = None
    error.details = details
    return error
