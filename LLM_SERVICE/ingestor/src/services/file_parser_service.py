from __future__ import annotations

from typing import Any, TYPE_CHECKING
import io

from docling.document_converter import DocumentConverter
from docling.datamodel.document import DocumentStream

if TYPE_CHECKING:
    from docling_core.types.doc.document import DoclingDocument


class FileParserService:
    def __init__(self) -> None:
        self.docling_doc_converter = DocumentConverter()

    def parse_file_content(
        self,
        file: Any
    ) -> "DoclingDocument":
        stream = DocumentStream(
            name=getattr(file, "filename", "uploaded-file.pdf"),
            stream=io.BytesIO(file.content),
            mime_type=getattr(file, "content_type", None) or "application/pdf",
        )

        result = self.docling_doc_converter.convert(stream)
        return result.document


    

   