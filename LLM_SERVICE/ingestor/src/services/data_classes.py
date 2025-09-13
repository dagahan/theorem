from dataclasses import dataclass, field
from typing import Dict, Tuple, Any, List


#dataclasses just creating for us some magical classes methods: 
# __init__ -- that method is called when we creating a new instance of class
# __repr__ -- that method calling when we try to print class into terminal. i.e. print(Block) => Block(page=32, king="3232", ...)
# __eq__  -- that method is called when we compare two instance of one class. e.g. Block1 == Block2. He is just compare a values of all parameters.


@dataclass
class Block:
    """
    Layout unit: the result of parsing a PDF page into logical blocks.
    kind ∈ {"heading","paragraph","list","answer","table_title","table_row","formula","code"}
    bbox: (x0,y0,x1,y1) in pdfplumber coordinates (if missing, set (0,0,0,0))
    meta: any service information: {"table_id":..., "row_idx":..., "col_idx":..., ...}
    """
    page: int
    kind: str
    text: str
    bbox: Tuple[float, float, float, float]
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Chunk:
    """
    A chunk that ready to go into vectorization/database.
    """
    id: str
    text: str
    tokens_est: int
    parent_type: str
    pages: List[int]
    parent_page_anchor: int | None
    meta: Dict[str, Any]

