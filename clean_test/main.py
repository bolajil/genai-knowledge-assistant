# clean_test/main.py

from fastapi import FastAPI, Request

print("🚀 clean_test/main.py loaded")

app = FastAPI()

@app.post("/ingest")
async def ingest(request: Request):
    data = await request.json()
    return {"status": "success", "content": data.get("content", "")}
