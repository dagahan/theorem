from __future__ import annotations

from typing import List, Any, Iterable
from loguru import logger

from docling_core.transforms.chunker.hybrid_chunker import HybridChunker

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from docling_core.types.doc.document import DoclingDocument

from pydantic_schemas.ingest import Chunk

from src.core.logging import ChunkingLogger


class ChunkingService:
    def __init__(self) -> None:
        self.docling_chunker = HybridChunker(
            max_tokens=480,
            overlap_tokens=120
        )


    def extract_chunks_from_docling_file(
        self,
        docling_doc: DoclingDocument
    ) -> List[Chunk]:
        chunks: List[Chunk] = []
        
        for idx, ch in enumerate(self.docling_chunker.chunk(docling_doc), start=1):
            pages = self._collect_pages_for_chunk(ch)        
            chunks.append(
                Chunk(
                    id=str(idx),
                    text=ch.text,
                    pages=pages,
                    meta={},
                )
            )
        
        return chunks


    def _collect_pages_for_chunk(
        self,
        chunk: Chunk
    ) -> List[int]:
        """
        reliably collect page numbers:
        1) from meta.doc_items[*].page (the main path to Docling),
        2) if not, we look for the 'page'/'pages' keys at any meta level,
        3) if there is nothing at all, we return [1].
        """
        meta = getattr(chunk, "meta", None)

        pages = set()

        for it in self._iter_doc_items(meta):
            page = self._get(it, ("page",))
            if isinstance(page, int) and page > 0:
                pages.add(page)

            else:
                bbox_page = self._get(it, ("bbox", "page"))
                if isinstance(bbox_page, int) and bbox_page > 0:
                    pages.add(bbox_page)

        if pages:
            return sorted(pages)

        for found in self._find_pages_in_meta(meta):
            if isinstance(found, int) and found > 0:
                pages.add(found)
            elif isinstance(found, list):
                for v in found:
                    if isinstance(v, int) and v > 0:
                        pages.add(v)

        if pages:
            return sorted(pages)

        for attr in ("pages", "page_indices", "page"):
            val = getattr(chunk, attr, None)
            if isinstance(val, int) and val > 0:
                return [val]
            if isinstance(val, list):
                ints = [v for v in val if isinstance(v, int) and v > 0]
                if ints:
                    return sorted(set(ints))

        return [1]


    def _iter_doc_items(
        self,
        meta: Any
    ) -> List[Any]:
        items = self._get(meta, ("doc_items",))

        if items is None:

            items = self._get(meta, ("items",))

        if isinstance(items, dict):
            items = list(items.values())

        return items or []


    def _find_pages_in_meta(
        self,
        obj: Any
    ) -> Iterable[Any]:
        if obj is None:
            return []

        stack = [obj]
        out: List[Any] = []

        while stack:
            cur = stack.pop()
            if isinstance(cur, dict):
                for k, v in cur.items():
                    key = str(k).lower()
                    if key in ("page", "pages"):
                        out.append(v)

                    if isinstance(v, (dict, list, tuple)):
                        stack.append(v)

            elif isinstance(cur, (list, tuple)):
                stack.extend(cur)

        return out


    @staticmethod
    def _get(
        obj: Any,
        path: Iterable[str],
        default: Any = None
    ) -> Any:
        cur = obj
        for path in path:
            if isinstance(cur, dict):
                cur = cur.get(path, default)

            else:
                cur = getattr(cur, path, default)

            if cur is default:
                break

        return cur if cur is not None else default


