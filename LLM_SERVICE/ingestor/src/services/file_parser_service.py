from __future__ import annotations

from typing import Any, TYPE_CHECKING

from docling.document_converter import DocumentConverter

if TYPE_CHECKING:
    from docling_core.types.doc.document import DoclingDocument


class FileParserService:
    def __init__(self) -> None:
        self.docling_doc_converter = DocumentConverter()


    def parse_file_content(
        self,
        file: Any
    ) -> DoclingDocument:
        result = self.docling_doc_converter.convert(file.content)
        return result.document


    

   