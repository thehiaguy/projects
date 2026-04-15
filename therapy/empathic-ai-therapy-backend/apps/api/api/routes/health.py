from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/v1/health")
async def get_health() -> dict[str, bool]:
    """
    Purpose:
        Return a minimal health response for readiness/liveness checks.

    Inputs:
        None.

    Returns:
        JSON object with shape:
        - `{"ok": true}`

    Data structures / implementation notes:
        - Keep this endpoint dependency-light and fast
        - Optionally extend later with service health details behind a debug flag
    """
    return {"ok": True}
