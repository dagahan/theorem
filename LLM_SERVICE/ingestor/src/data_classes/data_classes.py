from dataclasses import dataclass, field
from typing import Dict, Tuple, Any, List


@dataclass(frozen=True)
class TextCharacter:
    """
    Represents a single character extracted from PDF with its spatial coordinates.
    Used for precise text positioning and layout analysis.
    
    Example: TextCharacter(character='A', x0=100.5, x1=105.2, top=200.0, bottom=210.0, page=1)
    """
    character: str  # The actual character (letter, digit, symbol, space)
    x0: float       # Left boundary coordinate in PDF units
    x1: float       # Right boundary coordinate in PDF units  
    top: float      # Top boundary coordinate in PDF units
    bottom: float   # Bottom boundary coordinate in PDF units
    page: int       # Page number where this character appears (0-indexed)


@dataclass(frozen=True)
class TextLine:
    """
    Represents a line of text with its bounding box and character span information.
    Used for text reconstruction and layout-aware processing.
    
    Example: TextLine(page=0, top=200.0, bottom=210.0, x0=100.0, x1=500.0, 
                      text="Find the derivative of f(x) = x²", 
                      character_spans=[(0, 5), (6, 15), (16, 30)])
    """
    page: int                           # Page number (0-indexed)
    top: float                          # Top Y coordinate of line bounding box
    bottom: float                       # Bottom Y coordinate of line bounding box
    x0: float                           # Left X coordinate of line bounding box
    x1: float                           # Right X coordinate of line bounding box
    text: str                           # The actual text content of the line
    character_spans: List[Tuple[int, int]]  # Character position ranges for reconstruction


@dataclass(frozen=True)
class OrderedLine:
    """
    Represents a text line with column assignment for multi-column layout processing.
    Used by LayoutAnalyzer for proper reading order determination.
    
    Example: OrderedLine(page=1, top=200.0, bottom=210.0, x0=100.0, x1=300.0,
                          text="Task 1: Solve the equation", column=0)
    """
    page: int       # Page number (1-indexed for display)
    top: float      # Top Y coordinate of line
    bottom: float   # Bottom Y coordinate of line
    x0: float       # Left X coordinate of line
    x1: float       # Right X coordinate of line
    text: str       # The text content
    column: int     # Column number (0=leftmost, 1=middle, 2=rightmost)


@dataclass(frozen=True)
class PageParseResult:
    """
    Contains the complete parsing results for a single PDF page.
    Includes both raw lines and normalized text for further processing.
    
    Example: PageParseResult(doc_id="math_task_001", page_index=0, width=595.0, height=842.0,
                             lines=[TextLine(...), TextLine(...)], 
                             normalized_text="Task 1: Find the area...", 
                             original_length=150, normalized_length=145)
    """
    doc_id: str                    # Document identifier
    page_index: int                # Page number (0-indexed)
    width: float                   # Page width in PDF units
    height: float                  # Page height in PDF units
    lines: List[TextLine]          # List of text lines found on the page
    normalized_text: str           # Cleaned and normalized text content
    original_length: int           # Length of original text before normalization
    normalized_length: int         # Length of text after normalization


@dataclass
class Block:
    """
    Represents a logical content block extracted from PDF parsing.
    Each block has a semantic type and contains related text content.
    
    Example: Block(page=1, kind="task", text="Find the derivative of f(x) = x² + 3x - 1",
                   bbox=(100.0, 200.0, 500.0, 250.0), 
                   meta={"task_number": "M2506", "difficulty": "medium"})
    """
    page: int                                      # Page number where block appears
    kind: str                                      # Block type: "heading", "paragraph", "list", "task", "answer", "formula", "table_title", "table_row", "caption"
    text: str                                      # The text content of the block
    bbox: Tuple[float, float, float, float]        # Bounding box coordinates (x0, y0, x1, y1)
    meta: Dict[str, Any] = field(default_factory=dict)  # Additional metadata (task numbers, table info, etc.)


@dataclass
class Chunk:
    """
    Represents a text chunk ready for vectorization and storage.
    Contains processed text with metadata for search and retrieval.
    
    Example: Chunk(id="uuid-123", text="To solve this quadratic equation, we use the discriminant formula...",
                    tokens_est=45, parent_type="paragraph", pages=[1, 2], 
                    parent_page_anchor=1, meta={"section_id": 3, "quality_score": 0.85})
    """
    id: str                        # Unique identifier for the chunk
    text: str                      # The processed text content
    tokens_est: int                # Estimated token count for the text
    parent_type: str              # Type of parent block: "paragraph", "task", "answer", "formula", "heading"
    pages: List[int]              # List of page numbers where this chunk appears
    parent_page_anchor: int | None # Primary page number for this chunk
    meta: Dict[str, Any]          # Additional metadata (quality scores, section info, etc.)


@dataclass(frozen=True)
class EmbeddedChunk:
    """
    Represents a chunk with its vector embedding and metadata.
    Used for storing chunks in vector database.
    
    Example: EmbeddedChunk(chunk_id="uuid-123", text="To solve this quadratic equation...",
                          vector=[0.1, 0.2, 0.3, ...], metadata={"quality_score": 0.85})
    """
    chunk_id: str                    # Unique identifier for the chunk
    text: str                        # The text content of the chunk
    vector: List[float]              # Vector embedding of the text
    metadata: Dict[str, Any]          # Chunk metadata (quality scores, parent info, etc.)
    
    @property
    def success(self) -> bool:
        return len(self.vector) > 0
    
    @property
    def embedding_dimension(self) -> int:
        return len(self.vector)


@dataclass(frozen=True)
class IngestResult:
    """
    Represents the result of ingesting a single file.
    Contains information about the ingestion process and any errors.
    Used internally for processing multiple files.
    
    Example: IngestResult(filename="EGE_Math_Task_001.pdf", doc_id="ege_math_task_001",
                          status="success", error=None)
    """
    filename: str              # Original filename of the ingested file
    doc_id: str               # Generated document ID for the file
    status: str               # Status: "success" or "failed"
    error: str | None         # Error message if status is "failed", None otherwise


@dataclass(frozen=True)
class PdfFile:
    """
    Represents a PDF file with validation and convenience properties.
    Used for passing PDF data between services in the ingestion pipeline.
    
    Example: PdfFile(filename="EGE_Math_Task_001.pdf", content_type="application/pdf",
                     content=b"PDF bytes...", metadata={"source": "FIPI", "year": 2024})
    """
    filename: str                  # Original filename of the PDF
    content_type: str             # MIME type (should be "application/pdf")
    content: bytes                 # Raw PDF file content
    metadata: Dict[str, Any]       # Additional metadata (source, year, collection info, etc.)
    
    def __post_init__(self) -> None:
        if not self.content_type.startswith("application/pdf"):
            raise ValueError("Only PDF files are supported")
        
        if not self.filename.lower().endswith('.pdf'):
            raise ValueError("Filename must have .pdf extension")
    
    @property
    def file_size(self) -> int:
        return len(self.content)
    
    @property
    def doc_id(self) -> str:
        from src.services.id_service import IdService
        return IdService.make_id_by_filename({
            "filename": self.filename,
            "content_type": self.content_type,
            **self.metadata
        })


