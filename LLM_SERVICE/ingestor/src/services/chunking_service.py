from __future__ import annotations

from typing import List, Any, Iterable, Dict, Optional
from loguru import logger

from docling_core.transforms.chunker.hybrid_chunker import HybridChunker

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from docling_core.types.doc.document import DoclingDocument

from pydantic_schemas.ingest import Chunk

from src.core.logging import ChunkingLogger
from src.core.utils import EnvTools


class ChunkingService:
    def __init__(self) -> None:
        max_tokens = int(EnvTools.required_load_env_var("CHUNKING_MAX_TOKENS"))
        overlap_tokens = int(EnvTools.required_load_env_var("CHUNKING_OVERLAP_TOKENS"))
        
        self.docling_chunker = HybridChunker(
            max_tokens=max_tokens,
            overlap_tokens=overlap_tokens
        )
        
        logger.info(f"ChunkingService initialized with max_tokens={max_tokens}, overlap_tokens={overlap_tokens}")


    def extract_chunks_from_docling_file(
        self,
        docling_doc: DoclingDocument,
        doc_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        chunks: List[Chunk] = []
        
        for idx, ch in enumerate(self.docling_chunker.chunk(docling_doc), start=0):
            pages = self._collect_pages_for_chunk(ch)
            logger.debug(f"chunk {idx}: pages={pages} | text[:60]={ch.text[:60]!r}")
            chunks.append(
                Chunk(
                    id=str(idx),
                    text=ch.text,
                    pages=pages,
                    meta={},
                )
            )
        
        if doc_id is not None and metadata is not None:
            ChunkingLogger.log_chunking_results(
                doc_id=doc_id,
                extracted_text="\n\n".join(c.text for c in chunks),
                chunks=[chunk.model_dump() for chunk in chunks],
                metadata=metadata
            )
        
        return chunks


    def _collect_pages_for_chunk(
        self,
        chunk: Any
    ) -> List[int]:
        meta = getattr(chunk, "meta", None) if hasattr(chunk, "meta") else None
        pages: set[int] = set()

        def _push(v: Any) -> None:
            if isinstance(v, int):
                pages.add(v + 1 if v >= 0 else v)
            elif isinstance(v, (list, tuple)):
                for x in v:
                    if isinstance(x, int):
                        pages.add(x + 1 if x >= 0 else x)

        for it in self._iter_doc_items(meta):
            for key in ("page", "page_no", "page_idx", "page_index", "page_number"):
                _push(self._get(it, (key,)))
            bbox = self._get(it, ("bbox",))
            if bbox:
                for key in ("page", "page_no", "page_idx", "page_index"):
                    _push(self._get(bbox, (key,)))

        for found in self._find_pages_in_meta(meta, keys=("page","page_no","page_idx","page_index","page_number","pages","page_numbers")):
            _push(found)

        for attr in ("pages","page_indices","page_index","page","page_number","page_numbers"):
            _push(getattr(chunk, attr, None))

        out = sorted(x for x in pages if isinstance(x, int) and x > 0)
        return out or [1]


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
        obj: Any,
        keys: tuple[str, ...] = ("page", "pages")
    ) -> Iterable[Any]:
        if obj is None:
            return []

        stack = [obj]
        out: List[Any] = []

        while stack:
            cur = stack.pop()
            if isinstance(cur, dict):
                for k, v in cur.items():
                    if str(k).lower() in keys:
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


