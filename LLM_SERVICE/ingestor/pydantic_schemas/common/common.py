from pydantic import BaseModel


class HealthResponse(BaseModel):  # type: ignore[misc]
    status: str
    error: str | None = None


class ErrorResponse(BaseModel):  # type: ignore[misc]
    error: str
    details: str | None = None


class SuccessResponse(BaseModel):  # type: ignore[misc]
    success: bool
    message: str | None = None

     