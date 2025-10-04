from fastapi import FastAPI, Request
from utils.query_helpers import query_index

print("🚀 query_api.py loaded")

app = FastAPI(title="GenAI Knowledge Assistant")

@app.post("/query")
async def query(request: Request):
    data = await request.json()
    query_text = data.get("query", "")
    index_name = data.get("index_name", "default_index")
    top_k = data.get("top_k", 5)

    try:
        results = query_index(query_text, index_name, top_k)
        return {
            "status": "success",
            "query": query_text,
            "index": index_name,
            "results": results
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
