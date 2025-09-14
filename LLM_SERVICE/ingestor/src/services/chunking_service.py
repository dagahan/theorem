# chunking_service.py
from __future__ import annotations

import hashlib
import re
import uuid
import json
from typing import List, Dict, Any, Iterable, Optional, Sequence, Tuple

import blingfire  # type: ignore
from loguru import logger
import statistics as st

from src.data_classes.data_classes import Block, Chunk
from .text_normalize_service import TextNormalizeService
from .parameters_validation_service import ParametersValidationService
from src.core.utils import EnvTools
from src.core.logging import ChunkingLogger


class ChunkingService:
    def __init__(self) -> None:
        self.token_based_chunk_size: int = int(EnvTools.required_load_env_var("CHUNK_SIZE"))
        self.token_based_chunk_overlap: int = int(EnvTools.required_load_env_var("CHUNK_OVERLAP"))

        self.minimum_characters_per_chunk: int = int(EnvTools.required_load_env_var("CHARS_MIN_PER_CHUNK"))
        self.target_characters_per_chunk: int = int(EnvTools.required_load_env_var("CHARS_TARGET_PER_CHUNK"))
        self.maximum_characters_per_chunk: int = int(EnvTools.required_load_env_var("CHARS_MAX_PER_CHUNK"))
        self.hard_limit_characters_per_chunk: int = int(EnvTools.required_load_env_var("CHARS_HARD_MAX"))
        self.character_overlap_between_chunks: int = int(EnvTools.required_load_env_var("CHUNK_OVERLAP_CHARS"))

        self.text_normalizer = TextNormalizeService()

        ParametersValidationService.validate_chunking_parameters(
            self.minimum_characters_per_chunk,
            self.target_characters_per_chunk,
            self.maximum_characters_per_chunk,
            self.hard_limit_characters_per_chunk,
            self.character_overlap_between_chunks
        )


    def _is_mathematical(
        self,
        t: str
    ) -> bool:
        math_chars = set("=+−-×÷∑∏∫∂√≤≥≠→←^_*/|<>≈∞≡∇∂")
        return sum(1 for ch in t if ch in math_chars) / max(1, len(t)) >= 0.08


    def _reclassify_formula_to_text(
        self,
        kind: str,
        text: str
    ) -> str:
        if kind != "formula":
            return kind
        cyr = sum(1 for ch in text if "А" <= ch <= "я" or ch in "Ёё") / max(1, len(text))
        if cyr >= float(EnvTools.required_load_env_var("OCR_WORD_CYR_RATIO_THRESHOLD") or 0.5) and not self._is_mathematical(text):
            return "paragraph"
        return "formula"


    def _autocorrect_after_chunking(
        self,
        chunks: List[Chunk]
    ) -> List[Chunk]:
        out: List[Chunk] = []
        i = 0
        while i < len(chunks):
            cur = chunks[i]
            cur_dict = cur.__dict__
            cur_dict["parent_type"] = self._reclassify_formula_to_text(cur.parent_type, cur.text)

            # Quality filter: skip low-quality chunks
            if self._is_low_quality_chunk(cur_dict):
                i += 1
                continue

            if len(cur.text) < 200 and i + 1 < len(chunks):
                nxt = chunks[i+1]
                nxt_dict = nxt.__dict__
                if nxt.parent_type == cur.parent_type and not self._is_low_quality_chunk(nxt_dict):
                    merged_text = self.text_normalizer.normalize_by_kind(nxt.parent_type, f"{cur.text} {nxt.text}")
                    merged_pages = sorted(set(cur.pages + nxt.pages))
                    merged_chunk = Chunk(
                        id=str(uuid.uuid4()),
                        text=merged_text,
                        tokens_est=self._estimate_token_count(merged_text),
                        parent_type=nxt.parent_type,
                        pages=merged_pages,
                        parent_page_anchor=min(merged_pages) if merged_pages else 1,
                        meta=nxt.meta
                    )
                    out.append(merged_chunk)
                    i += 2
                    continue
            
            # Update parent_type if changed
            if cur_dict["parent_type"] != cur.parent_type:
                updated_chunk = Chunk(
                    id=cur.id,
                    text=cur.text,
                    tokens_est=cur.tokens_est,
                    parent_type=cur_dict["parent_type"],
                    pages=cur.pages,
                    parent_page_anchor=cur.parent_page_anchor,
                    meta=cur.meta
                )
                out.append(updated_chunk)
            else:
                out.append(cur)
            i += 1
        return out


    def _is_low_quality_chunk(
        self,
        chunk: Dict[str,Any]
    ) -> bool:
        text = chunk.get("text", "")
        if len(text) < 180:
            return True
        
        # Check for CID artifacts
        if re.search(r"\(cid:\d+\)", text):
            return True
            
        # Check for ELLIPSIS artifacts
        if "ELLIPSIS" in text:
            return True
            
        # Check alpha ratio
        alpha_count = sum(1 for ch in text if ch.isalpha())
        alpha_ratio = alpha_count / max(1, len(text))
        if alpha_ratio < 0.4:
            return True
            
        # Check OCR spacing artifacts
        if re.search(r'\b(?:[A-Za-zА-Яа-я]\s){3,}[A-Za-zА-Яа-я]\b', text):
            return True
            
        return False


    @staticmethod
    def _split_text_into_sentences(paragraph_text: str) -> List[str]:
        """
        Splits text into sentences using blingfire library.
        Falls back to regex patterns for Russian text on errors.
        Example: "Hello world! How are you?" -> ["Hello world!", "How are you?"]
        """
        try:
            sentence_lines = blingfire.text_to_sentences(paragraph_text).splitlines()
            return [sentence.strip() for sentence in sentence_lines if sentence.strip()]

        except Exception:
            # For Russian and formal text, consider abbreviations
            # Split by punctuation marks followed by space
            sentence_parts = re.split(r"(?<=[.!?])\s+(?=[А-ЯA-Z0-9\"«(])", paragraph_text)
            return [part.strip() for part in sentence_parts if part and part.strip()]


    @staticmethod
    def _is_text_quality_acceptable(
        text_string: str,
        *,
        allow_short_text: bool = False,
        is_mathematical_formula: bool = False,
    ) -> bool:
        """
        Validates text quality before including in chunk.
        Filters heavily noisy and low-quality strings.
        Example: "abc123!@#" -> False (too noisy), "The quick brown fox" -> True
        """
        if not text_string:
            return False

        if not allow_short_text and (len(text_string) < 10 or len(text_string) > 16_384):
            return False

        if is_mathematical_formula:
            return True

        words_in_text = text_string.split()
        if not allow_short_text and len(words_in_text) < 3:
            return False

        alphabetic_characters_count = sum(char.isalpha() for char in text_string)
        alphabetic_ratio = alphabetic_characters_count / max(1, len(text_string))
        if alphabetic_ratio < 0.30:
            return False

        noise_characters_count = sum(not (char.isalnum() or char.isspace()) for char in text_string)
        noise_ratio = noise_characters_count / max(1, len(text_string))
        if noise_ratio > 0.65:
            return False

        return True


    @staticmethod
    def _estimate_token_count(text: str) -> int:
        """
        Estimates token count in text using blingfire.
        Applies 1.25 multiplier for more accurate estimation.
        Example: "Hello world" (2 words) -> 3 tokens (2 * 1.25)
        """
        word_count = len(blingfire.text_to_words(text).split())
        return int(word_count * 1.25 + 0.5)


    @staticmethod
    def _calculate_95th_percentile(values: List[int]) -> int:
        """
        Calculates 95th percentile from list of values.
        Used for determining maximum sentence lengths.
        Example: [10, 20, 30, 40, 50] -> 50 (95th percentile)
        """
        if not values:
            return 0
        percentile_index = max(0, int(0.95 * len(values)) - 1)
        return sorted(values)[percentile_index]


    def _calculate_adaptive_character_window(
        self,
        document_blocks: List[Block],
    ) -> Dict[str, int]:
        """
        Adapts character window based on sentence length statistics.
        Optimized for larger semantic chunks (500-1500 chars).
        Example: Short sentences -> smaller window, long sentences -> larger window
        """
        sentence_lengths = [len(s) for b in document_blocks if b.kind in ("paragraph","list_item","task")
                            for s in self._split_text_into_sentences(b.text)]
        if not sentence_lengths:
            return dict(min=self.minimum_characters_per_chunk,
                        target=self.target_characters_per_chunk,
                        max=self.maximum_characters_per_chunk,
                        hard=self.hard_limit_characters_per_chunk)

        med = int(st.median(sentence_lengths))
        p95 = self._calculate_95th_percentile(sentence_lengths)

        target = max(700, min(self.target_characters_per_chunk, 1100))
        if med > 180: 
            target = min(1200, max(target, 900))
        maxlen = min(self.hard_limit_characters_per_chunk, max(target + 300, p95 + 200))
        minlen = max(450, min(target - 400, self.minimum_characters_per_chunk))
        return dict(min=minlen, target=target, max=maxlen, hard=self.hard_limit_characters_per_chunk)


    @staticmethod
    def _find_natural_text_breakpoints(text: str) -> List[int]:
        """
        Returns list of indices where text can be naturally split:
        sentence endings, punctuation, spaces.
        Example: "Hello. World!" -> [6, 13] (after period and exclamation)
        """
        breakpoint_positions: List[int] = []
        for match in re.finditer(r"[.!?…](?:\)|»|\"|\"|')?\s", text):
            breakpoint_positions.append(match.end())
        for match in re.finditer(r"[;:](?:\)|»|\"|\"|')?\s", text):
            breakpoint_positions.append(match.end())
        for match in re.finditer(r"\s[-–—]\s", text):  # dash as logical separator
            breakpoint_positions.append(match.start() + 1)  # cut before dash
        for match in re.finditer(r"\s", text):
            breakpoint_positions.append(match.end())
        # remove duplicates and sort
        unique_breakpoints = sorted(set(breakpoint_positions))
        return [position for position in unique_breakpoints if 0 < position < len(text)]



    def _split_text_at_natural_breakpoint(
        self,
        text_to_split: str,
        preferred_length_limit: int,
        absolute_length_limit: int,
    ) -> Tuple[str, str]:
        """
        Softly splits text so first part is <= preferred_limit
        (or slightly more if nearest natural breakpoint is further),
        but never exceeds absolute_limit.
        Returns (head, tail).
        Example: "Hello world! How are you?" with limit=10 -> ("Hello world!", "How are you?")
        """
        if len(text_to_split) <= preferred_length_limit:
            return text_to_split, ""

        if len(text_to_split) > absolute_length_limit:
            # Search for cut point in window [limit-80, limit+80]
            search_window_start = max(0, preferred_length_limit - 80)
            search_window_end = min(len(text_to_split), preferred_length_limit + 80)

            candidate_breakpoints = [position for position in self._find_natural_text_breakpoints(text_to_split[search_window_start:search_window_end])]
            if candidate_breakpoints:
                cut_position = search_window_start + self._find_closest_value_to_target(candidate_breakpoints, preferred_length_limit - search_window_start)
                cut_position = min(cut_position, absolute_length_limit)
                return text_to_split[:cut_position].rstrip(), text_to_split[cut_position:].lstrip()

            # If not found — hard cut
            return text_to_split[:absolute_length_limit].rstrip(), text_to_split[absolute_length_limit:].lstrip()

        # len(text) in (limit, hard_limit]
        # Search for nearest natural breakpoint in window [limit-60, len]
        search_window_start = max(0, preferred_length_limit - 60)
        candidate_breakpoints = [position for position in self._find_natural_text_breakpoints(text_to_split[search_window_start:])]
        if candidate_breakpoints:
            cut_position = search_window_start + self._find_closest_value_to_target(candidate_breakpoints, preferred_length_limit - search_window_start)
            cut_position = min(cut_position, absolute_length_limit)
            return text_to_split[:cut_position].rstrip(), text_to_split[cut_position:].lstrip()

        # Not found — leave as is (within hard_limit)
        return text_to_split[:min(len(text_to_split), absolute_length_limit)].rstrip(), text_to_split[min(len(text_to_split), absolute_length_limit):].lstrip()



    @staticmethod
    def _find_closest_value_to_target(
        values_array: Sequence[int],
        target_value: int
    ) -> int:
        """
        Returns element from array closest to target value.
        Example: [10, 20, 30], target=25 -> 20 (closest)
        """
        if not values_array:
            return 0
        # binary search not critical, array is small; simple heuristic
        best_value = values_array[0]
        best_distance = abs(best_value - target_value)
        for current_value in values_array[1:]:
            current_distance = abs(current_value - target_value)
            if current_distance < best_distance:
                best_value, best_distance = current_value, current_distance
        return best_value


    def _iterate_sentences_from_block(
        self,
        document_block: Block
    ) -> Iterable[str]:
        """
        Iterates sentences; formulas/answers/table rows returned as whole.
        Example: paragraph -> ["Sentence 1.", "Sentence 2."], formula -> ["x^2 + y^2 = z^2"]
        """
        block_text = document_block.text
        if document_block.kind in ("formula", "answer", "table_row"):
            yield block_text
            return
        for sentence in self._split_text_into_sentences(block_text):
            yield sentence


    def chunk_blocks(
        self,
        document_id: str,
        document_blocks: List[Block],
        document_metadata: Dict[str, Any],
    ) -> List[Chunk]:
        # 1) Adaptive window calculation based on statistics.
        character_window_configuration = self._calculate_adaptive_character_window(document_blocks)
        minimum_characters = character_window_configuration["min"]
        target_characters = character_window_configuration["target"]
        maximum_characters = character_window_configuration["max"]
        hard_limit_characters = character_window_configuration["hard"]
        character_overlap_amount = self.character_overlap_between_chunks

        resulting_chunks: List[Chunk] = []

        text_buffer: List[str] = []
        buffer_character_count: int = 0
        current_parent_context: Optional[Dict[str, Any]] = None
        page_numbers_set: set[int] = set()

        def _get_buffer_text_content() -> str:
            return " ".join(text_buffer).strip()

        def _flush_current_buffer_to_chunk() -> None:
            nonlocal text_buffer, buffer_character_count, current_parent_context, page_numbers_set
            if not text_buffer:
                return
            buffer_text_content = _get_buffer_text_content()
            if not buffer_text_content:
                text_buffer.clear()
                buffer_character_count = 0
                current_parent_context = None
                page_numbers_set.clear()
                return

            # Text normalization by parent type (for typography and OCR fixes).
            parent_type = (current_parent_context or {}).get("kind", "paragraph")
            normalized_text = self.text_normalizer.normalize_by_kind(parent_type, buffer_text_content)

            # Post-fix: anti-"letter through space" (OCR); already in validator, but better before writing.
            normalized_text = self.text_normalizer._collapse_ocr_spacing(normalized_text)

            page_numbers_list = sorted(page_numbers_set) if page_numbers_set else [1]

            chunk_object = Chunk(
                id=str(uuid.uuid4()),
                text=normalized_text,
                tokens_est=self._estimate_token_count(normalized_text),
                parent_type=parent_type,
                pages=page_numbers_list,
                parent_page_anchor=min(page_numbers_list) if page_numbers_list else 1,
                meta={**((current_parent_context or {}).get("meta", {})), **document_metadata},
            )
            
            resulting_chunks.append(chunk_object)
            text_buffer.clear()
            buffer_character_count = 0
            current_parent_context = None
            page_numbers_set.clear()



        def _ensure_parent_context_exists(
            block_type: str,
            additional_metadata: Optional[Dict[str, Any]] = None
        ) -> None:
            nonlocal current_parent_context
            if current_parent_context is None:
                current_parent_context = {"kind": block_type, "meta": dict(additional_metadata or {})}
            else:
                # Keep current kind if it's more specific (formula/answer/table),
                # otherwise give new kind.
                if current_parent_context.get("kind") not in ("formula", "answer", "table_row"):
                    current_parent_context["kind"] = block_type
                if additional_metadata:
                    current_parent_context.setdefault("meta", {}).update(additional_metadata)


        def _add_text_piece_to_buffer(
            text_piece: str,
            block_page_number: int,
            block_type: str
        ) -> None:
            """
            Adds text piece to buffer, softly splits if needed by TARGET/HARD limits.
            Example: 500-char text with 200-char limit -> split into 200+300 chars
            """
            nonlocal text_buffer, buffer_character_count

            # If piece itself is larger than hard — cut before adding.
            remaining_text = text_piece
            while remaining_text:
                if len(remaining_text) <= max(1, maximum_characters - buffer_character_count):
                    # Fits in current buffer
                    text_buffer.append(remaining_text)
                    buffer_character_count += len(remaining_text) + (1 if text_buffer else 0)
                    break

                # Doesn't fit — first fill current buffer to limit,
                # then flush and continue with tail.
                available_space = max(0, target_characters - buffer_character_count)
                if available_space < 40:
                    # almost no space — just flush
                    _flush_current_buffer_to_chunk()
                    _ensure_parent_context_exists(block_type)
                    page_numbers_set.add(block_page_number)
                    continue

                head_part, tail_part = self._split_text_at_natural_breakpoint(remaining_text, preferred_length_limit=available_space, absolute_length_limit=min(hard_limit_characters, maximum_characters))
                if head_part:
                    text_buffer.append(head_part)
                    buffer_character_count += len(head_part) + (1 if text_buffer else 0)
                _flush_current_buffer_to_chunk()
                _ensure_parent_context_exists(block_type)
                page_numbers_set.add(block_page_number)
                remaining_text = tail_part

        # 2) Block iteration and chunk assembly
        for current_block in document_blocks:
            # Headings: treat as context for next text (short)
            if current_block.kind == "heading":
                # If current buffer is already sufficient — flush to avoid "stuffing" with heading
                if buffer_character_count >= minimum_characters:
                    _flush_current_buffer_to_chunk()
                _ensure_parent_context_exists("heading+next", {"heading": current_block.text})
                page_numbers_set.add(current_block.page)
                # Heading might be too long: cut softly
                heading_head_part, heading_tail_part = self._split_text_at_natural_breakpoint(current_block.text.strip(), preferred_length_limit=target_characters, absolute_length_limit=maximum_characters)
                if heading_head_part:
                    _add_text_piece_to_buffer(heading_head_part, current_block.page, "heading+next")
                if heading_tail_part:
                    # heading remainder — rare case; put it as separate chunk
                    _flush_current_buffer_to_chunk()
                    _ensure_parent_context_exists("heading+next", {"heading_tail": True})
                    page_numbers_set.add(current_block.page)
                    _add_text_piece_to_buffer(heading_tail_part, current_block.page, "heading+next")
                continue

            # Formulas / answers / table rows — atomic, but if > HARD — cut softly
            if current_block.kind in ("table_row", "answer", "formula"):
                if buffer_character_count >= minimum_characters:
                    _flush_current_buffer_to_chunk()
                block_text_content = current_block.text.strip()
                if not self._is_text_quality_acceptable(block_text_content, allow_short_text=True, is_mathematical_formula=(current_block.kind == "formula")):
                    continue
                _ensure_parent_context_exists(current_block.kind, {**current_block.meta})
                page_numbers_set.add(current_block.page)
                # If short — as one piece
                if len(block_text_content) <= maximum_characters:
                    _add_text_piece_to_buffer(block_text_content, current_block.page, current_block.kind)
                    _flush_current_buffer_to_chunk()
                else:
                    # Cut by characters into several compact chunks
                    remaining_formula_text = block_text_content
                    while remaining_formula_text:
                        formula_head_part, formula_tail_part = self._split_text_at_natural_breakpoint(remaining_formula_text, preferred_length_limit=target_characters, absolute_length_limit=maximum_characters)
                        _add_text_piece_to_buffer(formula_head_part, current_block.page, current_block.kind)
                        _flush_current_buffer_to_chunk()
                        remaining_formula_text = formula_tail_part
                continue

            # Regular paragraphs/lists — main text mass
            if current_block.kind in ("paragraph", "list"):
                _ensure_parent_context_exists(current_block.kind, {})
                page_numbers_set.add(current_block.page)

                # Split into sentences; each sentence cut if necessary
                for sentence_text in self._iterate_sentences_from_block(current_block):
                    if not self._is_text_quality_acceptable(sentence_text):
                        continue
                    sentence_text = sentence_text.strip()
                    if not sentence_text:
                        continue

                    # If sentence is longer than can fit in empty chunk — cut into parts.
                    remaining_sentence_text = sentence_text
                    while remaining_sentence_text:
                        available_space_in_buffer = target_characters - buffer_character_count if text_buffer else target_characters
                        if available_space_in_buffer < 40 and buffer_character_count >= minimum_characters:
                            # Good chunk formed — flush and continue
                            _flush_current_buffer_to_chunk()
                            _ensure_parent_context_exists(current_block.kind, {})
                            page_numbers_set.add(current_block.page)
                            available_space_in_buffer = target_characters

                        if len(remaining_sentence_text) <= max(1, maximum_characters - buffer_character_count):
                            # Fits
                            text_buffer.append(remaining_sentence_text)
                            buffer_character_count += len(remaining_sentence_text) + (1 if text_buffer else 0)
                            break

                        # Doesn't fit — separate piece for current chunk and flush
                        sentence_head_part, sentence_tail_part = self._split_text_at_natural_breakpoint(
                            remaining_sentence_text,
                            preferred_length_limit=max(120, min(available_space_in_buffer, target_characters)),
                            absolute_length_limit=min(hard_limit_characters, maximum_characters),
                        )
                        if sentence_head_part:
                            text_buffer.append(sentence_head_part)
                            buffer_character_count += len(sentence_head_part) + (1 if text_buffer else 0)
                        _flush_current_buffer_to_chunk()
                        _ensure_parent_context_exists(current_block.kind, {})
                        page_numbers_set.add(current_block.page)
                        remaining_sentence_text = sentence_tail_part
                continue

            # Table title — add to metadata of nearest chunk
            if current_block.kind == "table_title":
                _ensure_parent_context_exists("heading+next", {"table_title": current_block.text})
                page_numbers_set.add(current_block.page)
                # Table titles usually short; don't force flush
                continue

        # Final flush (if something left in buffer)
        if buffer_character_count > 0:
            _flush_current_buffer_to_chunk()

        # 3) Autocorrection and reclassification
        resulting_chunks = self._autocorrect_after_chunking(resulting_chunks)

        # 4) Character overlap (optional, compact)
        if character_overlap_amount > 0:
            resulting_chunks = self._apply_character_overlap_between_chunks(resulting_chunks, overlap_characters=character_overlap_amount)

        # 4) Validation and post-fixes
        # Recalculate coverage — by characters.
        source_text_length = sum(len(block.text) for block in document_blocks if block.kind in ("paragraph", "list", "heading"))
        output_text_length = sum(len(chunk.text) for chunk in resulting_chunks)
        text_coverage_ratio = output_text_length / max(1, source_text_length)
        logger.info(
            f"Chunking (chars) coverage={text_coverage_ratio:.3f}, chunks={len(resulting_chunks)}, "
            f"window=[{minimum_characters},{target_characters},{maximum_characters}], hard={hard_limit_characters}, overlap={character_overlap_amount}"
        )

        # Convert chunks to dict for logging
        chunks_for_logging = [chunk.__dict__ for chunk in resulting_chunks]
        ChunkingLogger.log_chunking_results(
            doc_id=document_id,
            extracted_text="",
            chunks=chunks_for_logging,
            metadata={
                **document_metadata,
                "coverage": text_coverage_ratio,
                "chars_min": minimum_characters,
                "chars_target": target_characters,
                "chars_max": maximum_characters,
                "chars_hard": hard_limit_characters,
                "overlap_chars": character_overlap_amount,
            },
            paragraph_count=len(document_blocks),
        )

        validation_result = self.validate_chunks(
            resulting_chunks,
            minimum_characters=minimum_characters,
            maximum_characters=maximum_characters,
        )

        # Additional pass: guarantee non-empty pages and anchors.
        final_chunks: List[Chunk] = []
        for chunk in resulting_chunks:
            if not chunk.pages:
                updated_chunk = Chunk(
                    id=chunk.id,
                    text=chunk.text,
                    tokens_est=chunk.tokens_est,
                    parent_type=chunk.parent_type,
                    pages=[1],
                    parent_page_anchor=1,
                    meta=chunk.meta
                )
                final_chunks.append(updated_chunk)
            elif chunk.parent_page_anchor is None:
                updated_chunk = Chunk(
                    id=chunk.id,
                    text=chunk.text,
                    tokens_est=chunk.tokens_est,
                    parent_type=chunk.parent_type,
                    pages=chunk.pages,
                    parent_page_anchor=min(chunk.pages),
                    meta=chunk.meta
                )
                final_chunks.append(updated_chunk)
            else:
                final_chunks.append(chunk)

        logger.info(
            f"Chunk validation (chars): {validation_result['counts']} issues "
            f"out of {validation_result['total']} chunks"
        )

        # 5) Additional quality metrics and final processing
        cid_re = re.compile(r"\(cid:\d+\)")
        bad_formula_re = re.compile(r"[А-Яа-яЁё]{2,}")
        ocr_spacing_re = re.compile(r'\b(?:[A-Za-zА-Яа-я]\s){3,}[A-Za-zА-Яа-я]\b')
        
        cid_frac = sum(1 for c in final_chunks if cid_re.search(c.text)) / max(1, len(final_chunks))
        miss_formula = sum(1 for c in final_chunks if c.parent_type == "formula" and bad_formula_re.search(c.text)) / max(1, len(final_chunks))
        logger.info(f"QC: cid_share={cid_frac:.3f}, formula_ru_share={miss_formula:.3f}")

        # 6) Add quality metrics to chunk metadata
        processed_chunks: List[Chunk] = []
        for chunk in final_chunks:
            # Calculate quality metrics
            alpha_count = sum(1 for ch in chunk.text if ch.isalpha())
            alpha_ratio = alpha_count / max(1, len(chunk.text))
            has_cid = bool(cid_re.search(chunk.text))
            has_ellipsis = "ELLIPSIS" in chunk.text
            has_ocr_spacing = bool(ocr_spacing_re.search(chunk.text))
            
            quality_score = 1.0
            if alpha_ratio < 0.4: quality_score -= 0.3
            if has_cid: quality_score -= 0.4
            if has_ellipsis: quality_score -= 0.3
            if has_ocr_spacing: quality_score -= 0.2
            if len(chunk.text) < 200: quality_score -= 0.2
            
            # Create updated chunk with quality metrics
            updated_chunk = Chunk(
                id=chunk.id,
                text=chunk.text,
                tokens_est=chunk.tokens_est,
                parent_type=chunk.parent_type,
                pages=chunk.pages,
                parent_page_anchor=chunk.parent_page_anchor,
                meta={
                    **chunk.meta,
                    "quality_score": max(0.0, quality_score),
                    "alpha_ratio": alpha_ratio,
                    "has_cid": has_cid,
                    "has_ellipsis": has_ellipsis,
                    "has_ocr_spacing": has_ocr_spacing
                }
            )
            processed_chunks.append(updated_chunk)

        return processed_chunks


    def _apply_character_overlap_between_chunks(
        self,
        chunks_list: List[Chunk],
        overlap_characters: int
    ) -> List[Chunk]:
        """
        Creates compact overlap between adjacent chunks: adds tail of previous chunk
        to beginning of current chunk up to overlap_chars (if not already naturally attached).
        Avoids duplicates or bloating > HARD MAX: trims beginning if needed.
        Example: ["Hello world", "world is great"] -> ["Hello world", "world world is great"]
        """
        if overlap_characters <= 0 or len(chunks_list) <= 1:
            return chunks_list

        chunks_with_overlap: List[Chunk] = []
        previous_chunk_tail: str = ""
        for chunk_index, current_chunk in enumerate(chunks_list):
            current_chunk_text: str = current_chunk.text
            if chunk_index == 0:
                chunks_with_overlap.append(current_chunk)
                previous_chunk_tail = current_chunk_text[-overlap_characters:] if len(current_chunk_text) > overlap_characters else current_chunk_text
                continue

            # If text already starts with same tail — do nothing.
            overlap_prefix = previous_chunk_tail
            if overlap_prefix and not current_chunk_text.startswith(overlap_prefix):
                # Insert overlap at front
                text_with_overlap = (overlap_prefix + " " + current_chunk_text).strip()
                # If became too long — trim beginning (overlap is auxiliary)
                hard_limit = self.hard_limit_characters_per_chunk
                if len(text_with_overlap) > hard_limit:
                    # Reduce overlap to fit
                    excess_length = len(text_with_overlap) - hard_limit
                    if excess_length < len(overlap_prefix):
                        overlap_prefix = overlap_prefix[excess_length:]
                        text_with_overlap = (overlap_prefix + " " + current_chunk_text).strip()
                    else:
                        # If overlap doesn't fit at all — abandon it
                        text_with_overlap = current_chunk_text

                # Create new chunk with updated text
                modified_chunk = Chunk(
                    id=current_chunk.id,
                    text=text_with_overlap,
                    tokens_est=self._estimate_token_count(text_with_overlap),
                    parent_type=current_chunk.parent_type,
                    pages=current_chunk.pages,
                    parent_page_anchor=current_chunk.parent_page_anchor,
                    meta=current_chunk.meta
                )
                chunks_with_overlap.append(modified_chunk)
            else:
                chunks_with_overlap.append(current_chunk)

            previous_chunk_tail = chunks_with_overlap[-1].text[-overlap_characters:] if len(chunks_with_overlap[-1].text) > overlap_characters else chunks_with_overlap[-1].text

        return chunks_with_overlap



    @staticmethod
    def validate_chunks(
        chunks_to_validate: List[Chunk],
        *,
        minimum_characters: int = 200,
        maximum_characters: int = 400,
        max_pages_span: int = 4,
        max_single_char_share: float = 0.35,
    ) -> Dict[str, Any]:
        """
        Validates length (by characters), bracket balance, possible OCR artifacts, etc.
        Example: "(hello world" -> flag_paren=True (unbalanced parentheses)
        """
        validation_flags = {"len":0,"paren":0,"dup":0,"alpha":0,"single":0,"ocr_space":0,"pages":0,"cid":0,"formula_ru":0}
        seen_text_hashes: set[str] = set()
        ocr_spacing_pattern = re.compile(r'\b(?:[A-Za-zА-Яа-я]\s){3,}[A-Za-zА-Яа-я]\b')
        cid_re = re.compile(r"\(cid:\d+\)")
        ru_re = re.compile(r"[А-Яа-яЁё]{2,}")

        def _calculate_text_hash(text_string: str) -> str:
            return hashlib.md5(text_string.encode("utf-8")).hexdigest()

        def _are_parentheses_balanced(text_string: str, opening_char: str, closing_char: str) -> bool:
            return text_string.count(opening_char) == text_string.count(closing_char)

        def _calculate_text_quality_metrics(text_string: str) -> Dict[str, float]:
            words_in_text = text_string.split()
            alphabetic_characters_count = sum(char.isalpha() for char in text_string)
            alphabetic_ratio = alphabetic_characters_count / max(1, len(text_string))
            single_character_words_share = sum(1 for word in words_in_text if len(word) == 1) / max(1, len(words_in_text))
            return {"alpha_ratio": alphabetic_ratio, "single_share": single_character_words_share}

        total_chunks_count = len(chunks_to_validate)
        for chunk in chunks_to_validate:
            chunk_text: str = chunk.text

            # Length only by characters (except formulas/answers where sometimes shorter is useful)
            if chunk.parent_type not in ("answer", "formula"):
                if not (minimum_characters <= len(chunk_text) <= maximum_characters):
                    validation_flags["len"] += 1
            else:
                # But forbid giants here too
                if len(chunk_text) > maximum_characters:
                    validation_flags["len"] += 1

            # Parentheses balance
            if not (_are_parentheses_balanced(chunk_text, "(", ")") and _are_parentheses_balanced(chunk_text, "[", "]") and _are_parentheses_balanced(chunk_text, "{", "}")):
                validation_flags["paren"] += 1

            # Duplicates (exact)
            text_hash = _calculate_text_hash(chunk_text)
            if text_hash in seen_text_hashes:
                validation_flags["dup"] += 1
            seen_text_hashes.add(text_hash)

            # Noise metrics
            quality_metrics = _calculate_text_quality_metrics(chunk_text)
            if quality_metrics["alpha_ratio"] < 0.40:
                validation_flags["alpha"] += 1
            if quality_metrics["single_share"] > max_single_char_share:
                validation_flags["single"] += 1

            # Typical OCR artifact "р а з р ы в ы" letters
            if ocr_spacing_pattern.search(chunk_text):
                validation_flags["ocr_space"] += 1

            # Page spread
            if len(set(chunk.pages)) > max_pages_span:
                validation_flags["pages"] += 1

            # CID artifacts
            if cid_re.search(chunk_text):
                validation_flags["cid"] += 1

            # Formula with Russian text
            if chunk.parent_type == "formula" and ru_re.search(chunk_text):
                validation_flags["formula_ru"] += 1

        return {"counts": validation_flags, "total": total_chunks_count}

