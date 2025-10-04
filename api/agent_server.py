from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from utils.chat_orchestrator import get_chat_chain

app = FastAPI()

class QueryRequest(BaseModel):
    provider: str
    index_name: str
    input: str

@app.post("/query")
def query_agent(req: QueryRequest):
    try:
        chain = get_chat_chain(req.provider, req.index_name)
        response = chain.invoke({"input": req.input})
        return {"answer": response if isinstance(response, str) else response.get("answer", "[No answer returned]")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
