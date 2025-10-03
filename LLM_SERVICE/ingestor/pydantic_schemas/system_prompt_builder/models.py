from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class PersonaPrompt(BaseModel):  # type: ignore[misc]
    name: str
    prompt: str


class BuildSystemPromptRequest(BaseModel):  # type: ignore[misc]
    persona_names: list[str]


class PolicyHeaderResponse(BaseModel):  # type: ignore[misc]
    policy_header: str
    success: bool
    error: Optional[str] = None


class PolicyHealthResponse(BaseModel):  # type: ignore[misc]
    status: str
    success: bool
    error: Optional[str] = None


class BuildSystemPromptResponse(BaseModel):  # type: ignore[misc]
    personalities: list[PersonaPrompt]
    success: bool
    error: Optional[str] = None


class HealthStatus(BaseModel):  # type: ignore[misc]
    status: str
    policy_builder_status: str


