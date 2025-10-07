from __future__ import annotations

from typing import Any


class AgentControllerError(Exception):
    """Base exception for all agent controller errors."""
    
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NodeExecutionError(AgentControllerError):
    """Raised when a graph node execution fails."""
    
    def __init__(self, node_name: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(f"Node '{node_name}' execution failed: {message}", details)
        self.node_name = node_name


class AdapterError(AgentControllerError):
    """Raised when external adapter communication fails."""
    
    def __init__(self, adapter_name: str, operation: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(f"Adapter '{adapter_name}' operation '{operation}' failed: {message}", details)
        self.adapter_name = adapter_name
        self.operation = operation


        