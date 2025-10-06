from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ResponseSchema(BaseModel):  # type: ignore[misc]
    type: str
    properties: Dict[str, str] = {}
    required: List[str] = []
    title: Optional[str] = None


class Personality(BaseModel):  # type: ignore[misc]
    name: str
    system_prompt: str
    response_schema: Optional[ResponseSchema] = None


class BuildPersonalityRequest(BaseModel):  # type: ignore[misc]
    persona_names: list[str]
    agent_name: str = ""


class PolicyHeaderResponse(BaseModel):  # type: ignore[misc]
    policy_header: str
    success: bool
    error: Optional[str] = None


class PolicyHealthResponse(BaseModel):  # type: ignore[misc]
    status: str
    success: bool
    error: Optional[str] = None


class BuildPersonalityResponse(BaseModel):  # type: ignore[misc]
    personalities: list[Personality]
    success: bool
    error: Optional[str] = None


class HealthStatus(BaseModel):  # type: ignore[misc]
    status: str
    policy_builder_status: str


