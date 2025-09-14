"""
Common Pydantic models for all microservices.
"""

from typing import Any, Dict
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    error: str | None = None


class ErrorResponse(BaseModel):
    error: str
    details: str | None = None


class SuccessResponse(BaseModel):
    success: bool
    message: str | None = None

     