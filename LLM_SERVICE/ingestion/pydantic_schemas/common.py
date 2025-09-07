"""
Common Pydantic models for all microservices.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class ErrorResponse(BaseModel):
    error: str
    details: Optional[str] = None


class SuccessResponse(BaseModel):
    success: bool
    message: Optional[str] = None

    