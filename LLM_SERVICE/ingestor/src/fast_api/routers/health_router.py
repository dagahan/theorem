from fastapi import APIRouter
from pydantic_schemas import HealthResponse


def get_health_router() -> APIRouter:
    router = APIRouter(prefix="/health", tags=["health"])

    @router.get("", response_model=HealthResponse)  # type: ignore[misc]
    async def health_check() -> HealthResponse:
        return HealthResponse(
            status="healthy",
            error="None"
        )

    return router


    