from fastapi import FastAPI
from utils.ingest_helpers import ingest_text
from utils.query_helpers import query_index
from utils.query_llm import synthesize_answer
from schemas import IngestRequest, QueryRequest
#from template.ingestion_module.schemas import QueryPayload
from app.agents.controller_agent import ControllerAgent


main_app = FastAPI(title="GenAI Knowledge Assistant")

@main_app.post("/ingest")
async def ingest(payload: IngestRequest):
    chunk_count = ingest_text(
        content=payload.content,
        index_name=payload.index_name,
        chunk_size=payload.chunk_size,
        chunk_overlap=payload.chunk_overlap
    )
    return {"status": "success", "chunks": chunk_count, "index": payload.index_name}

@main_app.post("/query")
def query_index(payload: QueryRequest):
    controller = ControllerAgent()
    answer = controller.run(
        query=payload.query,
        index_name=payload.index_name,
        top_k=payload.top_k,
        provider=payload.provider
    )

    return {
        "status": "success",
        "query": payload.query,
        "index": payload.index_name,
        "provider": payload.provider,
        "answer": answer
    }




