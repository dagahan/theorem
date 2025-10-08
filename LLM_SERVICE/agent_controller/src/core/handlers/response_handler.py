from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from src.agents_graphs.graph_tools import GraphTools
from ..exceptions import AdapterError, NodeExecutionError

if TYPE_CHECKING:
    from src.pydantic_schemas.agent_controller import GraphState


class ResponseProtocol(Protocol):
    success: bool
    error: str | None


class ResponseHandler:
    @staticmethod
    def handle_success(
        graph_state: GraphState,
        success_key: str,
        additional_data: dict[str, Any] | None = None
    ) -> GraphState:

        graph_state['success'] = True
        graph_state[success_key] = True  # type: ignore[literal-required]
        
        if additional_data:
            for key, value in additional_data.items():
                graph_state[key] = value  # type: ignore[literal-required]
            
        return graph_state
    

    @staticmethod
    def handle_failure(
        graph_state: GraphState,
        error_message: str,
        error_key: str | None = None,
        additional_data: dict[str, Any] | None = None
    ) -> GraphState:

        graph_state['success'] = False
        graph_state['error'] = error_message
        
        if error_key:
            graph_state[error_key] = False  # type: ignore[literal-required]
            graph_state[f"{error_key}_error"] = error_message  # type: ignore[literal-required]
            
        if additional_data:
            for key, value in additional_data.items():
                graph_state[key] = value  # type: ignore[literal-required]
            
        return GraphTools.mark_failure(graph_state, error_message)
    

    @staticmethod
    def process_response(
        graph_state: GraphState,
        response: ResponseProtocol,
        success_key: str,
        error_key: str | None = None,
        success_data: dict[str, Any] | None = None,
        failure_data: dict[str, Any] | None = None,
        operation_name: str | None = None
    ) -> GraphState:

        try:
            if response.success:
                return ResponseHandler.handle_success(
                    graph_state=graph_state,
                    success_key=success_key,
                    additional_data=success_data
                )
                
            else:
                error_msg = response.error or 'Unknown error'
                if operation_name:
                    error_msg = f"{operation_name} failed: {error_msg}"
                    
                return ResponseHandler.handle_failure(
                    graph_state=graph_state,
                    error_message=error_msg,
                    error_key=error_key,
                    additional_data=failure_data
                )
                
        except Exception as ex:
            error_msg = f"Response processing failed: {str(ex)}"

            if operation_name:
                error_msg = f"{operation_name} processing failed: {str(ex)}"
                
            raise NodeExecutionError(
                node_name=operation_name or "unknown",
                message=error_msg,
                details={"original_error": str(ex), "response_success": response.success}
            ) from ex
    

    @staticmethod
    def validate_response(
        response: ResponseProtocol,
        adapter_name: str,
        operation: str
    ) -> None:
        if not hasattr(response, 'success'):
            raise AdapterError(
                adapter_name=adapter_name,
                operation=operation,
                message="Response missing 'success' field",
                details={"response_type": type(response).__name__}
            )
        
        if not isinstance(response.success, bool):
            raise AdapterError(
                adapter_name=adapter_name,
                operation=operation,
                message="Response 'success' field must be boolean",
                details={"success_type": type(response.success).__name__}
            )


