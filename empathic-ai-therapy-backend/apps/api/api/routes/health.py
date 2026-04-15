from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/v1/health")
async def get_health() -> dict[str, bool]:
    return {"ok": True}
