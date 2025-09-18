from __future__ import annotations
import time
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from src.domain.models import GraphState


class ContextBuilderNode:
    def __init__(self) -> None:
        pass


    async def execute_node(
        self,
        graph_state: "GraphState"
    ) -> "GraphState":
        execution_start_time = time.time()
        
        retrieved_chunks = graph_state.get("context_chunks", [])
        maximum_context_characters = graph_state["max_context_chars"]

        if not retrieved_chunks:
            graph_state["context_text"] = "Context not found."
            graph_state["timings_ms"]["build_context_text"] = (time.time() - execution_start_time) * 1000
            return graph_state

        formatted_context_sections: List[str] = []
        total_characters_consumed = 0

        for chunk_index, chunk in enumerate(retrieved_chunks, 1):
            chunk_text = getattr(chunk, 'text', '')
            doc_id = getattr(chunk, 'doc_id', 'unknown')
            pages = getattr(chunk, 'pages', [])
            score = getattr(chunk, 'score', 0.0)
            
            chunk_header_info = f"{chunk_index}. doc={doc_id}, pages={pages}, score={score:.5f}"

            if total_characters_consumed + len(chunk_header_info) + 1 > maximum_context_characters:
                break
                
            available_characters_for_context = maximum_context_characters - total_characters_consumed - len(chunk_header_info) - 1

            if available_characters_for_context > 0:
                truncated_chunk_content = chunk_text[:available_characters_for_context] if len(chunk_text) > available_characters_for_context else chunk_text
                formatted_chunk_line = f"{chunk_header_info}\n{truncated_chunk_content}"
            else:
                formatted_chunk_line = chunk_header_info
                
            formatted_context_sections.append(formatted_chunk_line)

            total_characters_consumed += len(formatted_chunk_line) + 1

        graph_state["context_text"] = "\n".join(formatted_context_sections) if formatted_context_sections else "Context not found."
        graph_state["timings_ms"]["build_context_text"] = (time.time() - execution_start_time) * 1000
        
        return graph_state


