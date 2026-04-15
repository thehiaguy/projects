# Backend API Scaffold (Implementation Skeleton)

This folder is a backend-only scaffold derived from `implementation-plan.md`.

What is included:
- File layout that matches the plan (`app`, `api`, `ws`, `services`, `domain`, `orchestration`, `utils`)
- Endpoint and service function skeletons only
- Detailed docstrings describing purpose, expected inputs/outputs, and data structures
- Placeholder Neo4j migration file and environment variables

What is intentionally not included:
- Business logic
- External API calls
- Database queries
- Validation implementations
- Tests

Recommended implementation order:
1. `app/deps.py` (settings/dependencies)
2. `services/neo4j/driver.py` + `services/neo4j/migrate.py`
3. `domain/models.py` + `ws/protocol.py` (typed contracts)
4. `api/routes/*.py` + `ws/session_ws.py`
5. `services/gemini/*` + `orchestration/kg_updater.py`
6. `orchestration/receipts.py`
7. Wire startup/shutdown in `app/main.py`
