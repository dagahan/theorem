from __future__ import annotations

from pydantic import BaseModel


class PolicyResponse(BaseModel):  # type: ignore[misc]
    policy_header: str
    success: bool
    error: str | None = None


class HealthStatus(BaseModel):  # type: ignore[misc]
    status: str

