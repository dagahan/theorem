from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


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
    system_prompt: str
    success: bool
    error: Optional[str] = None


@dataclass(frozen=True)
class HealthStatus:
    status: str
    policy_builder_status: str


