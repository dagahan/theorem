from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PolicyResponse:
    policy_header: str
    success: bool
    error: str | None = None


@dataclass(frozen=True)
class HealthStatus:
    status: str


