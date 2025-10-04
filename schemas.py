from pydantic import BaseModel

class QueryRequest(BaseModel):
    query: str
    index_name: str
    top_k: int
    provider: str

class IngestRequest(BaseModel):
    content: str
    index_name: str
    chunk_size: int
    chunk_overlap: int
