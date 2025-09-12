from __future__ import annotations

import io
import os
from typing import Optional, Dict, Any

import chardet
from docx import Document
from loguru import logger
import pdfplumber

from src.core.logging import FileParserLogger


class FileParserService:
    def extract_file_to_text(
        self,
        filename: str,
        content: bytes,
        content_type: Optional[str],
        doc_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        name = filename.lower().strip()
        extracted_text = ""
        parsing_method = ""
        success = True
        error_message = ""

        try:
            if name.endswith(".pdf") or (content_type or "").startswith("application/pdf"):
                extracted_text = self._from_pdf(content)
                parsing_method = "pdf_plumber"
            elif name.endswith(".docx") or (content_type or "") in {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"}:
                extracted_text = self._from_docx(content)
                parsing_method = "docx_python_docx"
            elif name.endswith(".txt") or (content_type or "").startswith("text/"):
                extracted_text = self._from_text(content)
                parsing_method = "text_chardet"
            else:
                extracted_text = self._from_text_or_binary(content)
                parsing_method = "text_or_binary_chardet"
        except Exception as e:
            success = False
            error_message = str(e)
            logger.error(f"Failed to parse file {filename}: {e}")
            extracted_text = ""

        if doc_id and metadata:
            FileParserLogger.log_parsing_results(
                doc_id=doc_id,
                filename=filename,
                content_type=content_type or "unknown",
                extracted_text=extracted_text,
                metadata=metadata,
                parsing_method=parsing_method,
                success=success,
                error_message=error_message
            )

        return extracted_text


    def _from_pdf(
        self,
        content: bytes
    ) -> str:
        try:
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                parts = []
                
                for page_num, page in enumerate(pdf.pages):
                    try:
                        page_parts = []
                        
                        text = page.extract_text()
                        if text and text.strip():
                            page_parts.append(text.strip())
                        
                        tables = page.extract_tables()
                        if tables:
                            for table_num, table in enumerate(tables):
                                if table:
                                    table_text = self._format_table(table)
                                    if table_text:
                                        page_parts.append(f"Table {table_num + 1}:\n{table_text}")
                        
                        if page_parts:
                            page_content = "\n\n".join(page_parts)
                            parts.append(f"--- Page {page_num + 1} ---\n{page_content}")
                            
                    except Exception as ex:
                        logger.warning(f"Failed to extract content from PDF page {page_num + 1}: {ex}")
                        continue
                
                if not parts:
                    logger.warning("No content extracted from PDF")
                    return ""
                
                return "\n\n".join(parts).strip()
                
        except Exception as ex:
            logger.error(f"Failed to process PDF with pdfplumber: {ex}")
            return ""


    def _format_table(
        self,
        table: list[list[str | None]]
    ) -> str:
        if not table:
            return ""
        
        try:
            max_widths: list[int] = []

            for row in table:
                for index, cell in enumerate(row):
                    cell_text = str(cell or "").strip()
                    if index >= len(max_widths):
                        max_widths.append(len(cell_text))
                    else:
                        max_widths[index] = max(max_widths[index], len(cell_text))
            
            formatted_rows = []

            for row in table:
                formatted_cells = []

                for index, cell in enumerate(row):
                    cell_text = str(cell or "").strip()
                    padded_text = cell_text.ljust(max_widths[index] if index < len(max_widths) else len(cell_text))
                    formatted_cells.append(padded_text)
                
                formatted_rows.append(" | ".join(formatted_cells))
            
            return "\n".join(formatted_rows)
            
        except Exception as e:
            logger.warning(f"Failed to format table: {e}")
            return "\n".join([" | ".join([str(cell or "") for cell in row]) for row in table])


    def _from_docx(
        self,
        content: bytes
    ) -> str:
        bio = io.BytesIO(content)
        doc = Document(bio)
        parts = [p.text.strip() for p in doc.paragraphs if p.text and p.text.strip()]

        return "\n".join(parts).strip()


    def _from_text(
        self,
        content: bytes
    ) -> str:
        det = chardet.detect(content)
        enc = det.get("encoding") or "utf-8"
        try:
            return content.decode(enc, errors="replace").strip()

        except Exception:
            return content.decode("utf-8", errors="replace").strip()


    def _from_text_or_binary(
        self,
        content: bytes
    ) -> str:
        if not content:
            return ""
            
        printable_ratio = sum(32 <= b <= 126 or b in (9, 10, 13) for b in content[:4096]) / min(len(content), 4096)
        if printable_ratio < 0.6:
            return ""
    
        return self._from_text(content)


        