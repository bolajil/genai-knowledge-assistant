from fastapi import FastAPI, Request
from utils.ingest_helpers import ingest_text

print("🚀 ingest_api.py loaded")

app = FastAPI()

@app.post("/ingest")
async def ingest(request: Request):
    data = await request.json()
    content = data.get("content", "")
    index_name = data.get("index_name", "default_index")
    chunk_size = data.get("chunk_size", 500)
    chunk_overlap = data.get("chunk_overlap", 50)

    try:
        chunk_count = ingest_text(content, index_name, chunk_size, chunk_overlap)
        return {
            "status": "success",
            "chunks": chunk_count,
            "index": index_name
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
