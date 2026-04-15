from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/v1/health", tags=["health"])


class HealthResponse(BaseModel):
    ok: bool


@router.get("/", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(ok=True)
