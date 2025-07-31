from pydantic import BaseModel
from typing import Optional
class IngestRequest(BaseModel):
    content: str
    index_name: str
    chunk_size: Optional[int] = 500
    chunk_overlap: Optional[int] = 50

class QueryRequest(BaseModel):
    query: str
    index_name: str
    top_k: int
    provider: str
