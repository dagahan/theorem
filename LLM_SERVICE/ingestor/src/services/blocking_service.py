from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Callable, Iterable, TYPE_CHECKING
from loguru import logger

if TYPE_CHECKING:
    from src.data_classes.data_classes import Block
    from .text_normalize_service import TextNormalizeService


class BlockingService:
    def __init__(self, text_normalizer: "TextNormalizeService") -> None:
        self.text_normalizer = text_normalizer

    def process_heading_block(
        self,
        block: "Block",
        buffer_state: Dict[str, Any],
        window_config: Dict[str, int],
        flush_buffer_func: Callable[[], None],
        ensure_context_func: Callable[[str, Optional[Dict[str, Any]]], None],
        add_text_func: Callable[[str, int, str], None]
    ) -> None:
        """Process heading block with context preservation."""
        buffer_character_count = buffer_state["character_count"]
        minimum_characters = window_config["min"]
        target_characters = window_config["target"]
        maximum_characters = window_config["max"]
        
        if buffer_character_count >= minimum_characters:
            flush_buffer_func()
        
        ensure_context_func("heading+next", {"heading": block.text})
        buffer_state["page_numbers"].add(block.page)
        
        heading_head, heading_tail = self._split_text_at_natural_breakpoint(
            block.text.strip(),
            target_characters,
            maximum_characters
        )
        
        if heading_head:
            add_text_func(heading_head, block.page, "heading+next")
        
        if heading_tail:
            flush_buffer_func()
            ensure_context_func("heading+next", {"heading_tail": True})
            buffer_state["page_numbers"].add(block.page)
            add_text_func(heading_tail, block.page, "heading+next")

    def process_atomic_block(
        self,
        block: "Block",
        buffer_state: Dict[str, Any],
        window_config: Dict[str, int],
        flush_buffer_func: Callable[[], None],
        ensure_context_func: Callable[[str, Optional[Dict[str, Any]]], None],
        add_text_func: Callable[[str, int, str], None],
        is_text_acceptable_func: Callable[[str, bool, bool], bool]
    ) -> None:
        """Process atomic blocks (formula, answer, table_row)."""
        buffer_character_count = buffer_state["character_count"]
        minimum_characters = window_config["min"]
        maximum_characters = window_config["max"]
        
        if buffer_character_count >= minimum_characters:
            flush_buffer_func()
        
        block_text = block.text.strip()
        if not is_text_acceptable_func(block_text, True, (block.kind == "formula")):
            return
        
        ensure_context_func(block.kind, {**block.meta})
        buffer_state["page_numbers"].add(block.page)
        
        if len(block_text) <= maximum_characters:
            add_text_func(block_text, block.page, block.kind)
            flush_buffer_func()
        else:
            self._process_large_atomic_block(
                block_text, block.page, block.kind,
                window_config, add_text_func, flush_buffer_func
            )

    def process_text_block(
        self,
        block: "Block",
        buffer_state: Dict[str, Any],
        window_config: Dict[str, int],
        flush_buffer_func: Callable[[], None],
        ensure_context_func: Callable[[str, Optional[Dict[str, Any]]], None],
        add_text_func: Callable[[str, int, str], None],
        iterate_sentences_func: Callable[["Block"], Iterable[str]],
        is_text_acceptable_func: Callable[[str, bool, bool], bool]
    ) -> None:
        """Process text blocks (paragraph, list)."""
        ensure_context_func(block.kind, {})
        buffer_state["page_numbers"].add(block.page)
        
        for sentence_text in iterate_sentences_func(block):
            if not is_text_acceptable_func(sentence_text, False, False):
                continue
            
            sentence_text = sentence_text.strip()
            if not sentence_text:
                continue
            
            self._process_sentence_text(
                sentence_text, block.page, block.kind,
                buffer_state, window_config,
                flush_buffer_func, ensure_context_func, add_text_func
            )

    def process_table_title_block(
        self,
        block: "Block",
        buffer_state: Dict[str, Any],
        ensure_context_func: Callable[[str, Optional[Dict[str, Any]]], None]
    ) -> None:
        """Process table title block."""
        ensure_context_func("heading+next", {"table_title": block.text})
        buffer_state["page_numbers"].add(block.page)

    def _process_large_atomic_block(
        self,
        block_text: str,
        page_number: int,
        block_type: str,
        window_config: Dict[str, int],
        add_text_func: Callable[[str, int, str], None],
        flush_buffer_func: Callable[[], None]
    ) -> None:
        """Process large atomic block by splitting it."""
        target_characters = window_config["target"]
        maximum_characters = window_config["max"]
        
        remaining_text = block_text
        while remaining_text:
            head_part, tail_part = self._split_text_at_natural_breakpoint(
                remaining_text, target_characters, maximum_characters
            )
            add_text_func(head_part, page_number, block_type)
            flush_buffer_func()
            remaining_text = tail_part

    def _process_sentence_text(
        self,
        sentence_text: str,
        page_number: int,
        block_type: str,
        buffer_state: Dict[str, Any],
        window_config: Dict[str, int],
        flush_buffer_func: Callable[[], None],
        ensure_context_func: Callable[[str, Optional[Dict[str, Any]]], None],
        add_text_func: Callable[[str, int, str], None]
    ) -> None:
        """Process individual sentence text."""
        buffer_character_count = buffer_state["character_count"]
        text_buffer = buffer_state["text_buffer"]
        minimum_characters = window_config["min"]
        target_characters = window_config["target"]
        maximum_characters = window_config["max"]
        
        remaining_sentence_text = sentence_text
        while remaining_sentence_text:
            available_space = target_characters - buffer_character_count if text_buffer else target_characters
            
            if available_space < 40 and buffer_character_count >= minimum_characters:
                flush_buffer_func()
                ensure_context_func(block_type, {})
                buffer_state["page_numbers"].add(page_number)
                available_space = target_characters
            
            if len(remaining_sentence_text) <= max(1, maximum_characters - buffer_character_count):
                text_buffer.append(remaining_sentence_text)
                buffer_state["character_count"] += len(remaining_sentence_text) + (1 if text_buffer else 0)
                break
            
            sentence_head, sentence_tail = self._split_text_at_natural_breakpoint(
                remaining_sentence_text,
                max(120, min(available_space, target_characters)),
                maximum_characters
            )
            
            if sentence_head:
                text_buffer.append(sentence_head)
                buffer_state["character_count"] += len(sentence_head) + (1 if text_buffer else 0)
            
            flush_buffer_func()
            ensure_context_func(block_type, {})
            buffer_state["page_numbers"].add(page_number)
            remaining_sentence_text = sentence_tail

    def _split_text_at_natural_breakpoint(
        self,
        text_to_split: str,
        preferred_length_limit: int,
        absolute_length_limit: int
    ) -> Tuple[str, str]:
        """Split text at natural breakpoints."""
        if len(text_to_split) <= preferred_length_limit:
            return text_to_split, ""
        
        if len(text_to_split) > absolute_length_limit:
            search_window_start = max(0, preferred_length_limit - 80)
            search_window_end = min(len(text_to_split), preferred_length_limit + 80)
            
            candidate_breakpoints = self._find_natural_text_breakpoints(
                text_to_split[search_window_start:search_window_end]
            )
            
            if candidate_breakpoints:
                cut_position = search_window_start + self._find_closest_value_to_target(
                    candidate_breakpoints, preferred_length_limit - search_window_start
                )
                cut_position = min(cut_position, absolute_length_limit)
                return text_to_split[:cut_position].rstrip(), text_to_split[cut_position:].lstrip()
            
            return text_to_split[:absolute_length_limit].rstrip(), text_to_split[absolute_length_limit:].lstrip()
        
        search_window_start = max(0, preferred_length_limit - 60)
        candidate_breakpoints = self._find_natural_text_breakpoints(text_to_split[search_window_start:])
        
        if candidate_breakpoints:
            cut_position = search_window_start + self._find_closest_value_to_target(
                candidate_breakpoints, preferred_length_limit - search_window_start
            )
            cut_position = min(cut_position, absolute_length_limit)
            return text_to_split[:cut_position].rstrip(), text_to_split[cut_position:].lstrip()
        
        return text_to_split[:min(len(text_to_split), absolute_length_limit)].rstrip(), text_to_split[min(len(text_to_split), absolute_length_limit):].lstrip()

    def _find_natural_text_breakpoints(self, text: str) -> List[int]:
        """Find natural text breakpoints."""
        import re
        breakpoint_positions: List[int] = []
        
        for match in re.finditer(r"[.!?…](?:\)|»|\"|\"|')?\s", text):
            breakpoint_positions.append(match.end())
        
        for match in re.finditer(r"[;:](?:\)|»|\"|\"|')?\s", text):
            breakpoint_positions.append(match.end())
        
        for match in re.finditer(r"\s[-–—]\s", text):
            breakpoint_positions.append(match.start() + 1)
        
        for match in re.finditer(r"\s", text):
            breakpoint_positions.append(match.end())
        
        unique_breakpoints = sorted(set(breakpoint_positions))
        return [position for position in unique_breakpoints if 0 < position < len(text)]

    def _find_closest_value_to_target(self, values_array: List[int], target_value: int) -> int:
        """Find closest value to target."""
        if not values_array:
            return 0
        
        best_value = values_array[0]
        best_distance = abs(best_value - target_value)
        
        for current_value in values_array[1:]:
            current_distance = abs(current_value - target_value)
            if current_distance < best_distance:
                best_value, best_distance = current_value, current_distance
        
        return best_value


        