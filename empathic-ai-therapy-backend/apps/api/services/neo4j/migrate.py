from pathlib import Path

from services.neo4j import driver as neo4j_driver


def load_constraints_cypher(file_path: Path) -> str:
    return file_path.read_text(encoding="utf-8")


def run_migrations() -> dict[str, object]:
    cypher_path = Path(__file__).parent / "cypher" / "constraints.cypher"
    script = load_constraints_cypher(cypher_path)

    statements: list[str] = []
    for raw_stmt in script.split(";"):
        cleaned = "\n".join(
            line for line in raw_stmt.splitlines()
            if line.strip() and not line.strip().startswith("//")
        ).strip()
        if cleaned:
            statements.append(cleaned)

    errors: list[str] = []
    executed = 0

    for stmt in statements:
        try:
            def _run(tx: object, s: str = stmt) -> None:
                tx.run(s)  # type: ignore[union-attr]

            neo4j_driver.execute_write(query_fn=_run)
            executed += 1
        except Exception as exc:
            errors.append(str(exc))

    from app.deps import get_settings
    db = get_settings().neo4j_database

    return {
        "applied": len(errors) == 0,
        "statements_executed": executed,
        "database": db,
        "errors": errors,
    }
