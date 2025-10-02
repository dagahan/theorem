from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PersonaPrompt:
    name: str
    prompt: str


@dataclass(frozen=True)
class BuildSystemPromptRequest:
    persona_names: list[str]


@dataclass(frozen=True)
class PolicyHeaderResponse:
    policy_header: str
    success: bool
    error: Optional[str] = None


@dataclass(frozen=True)
class PolicyHealthResponse:
    status: str
    success: bool
    error: Optional[str] = None


@dataclass(frozen=True)
class BuildSystemPromptResponse:
    personalities: list[PersonaPrompt]
    success: bool
    error: Optional[str] = None


@dataclass(frozen=True)
class HealthStatus:
    status: str
    policy_builder_status: str
