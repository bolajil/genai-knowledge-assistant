from app.mcp.function_calling import FunctionHandler
from app.utils import notification_service
from app.utils.notification_service import NotificationService
from pathlib import Path
import os
import requests
from typing import Any, Optional, List, Dict, Tuple, Callable, Union
from langchain_community.vectorstores import FAISS
from app.utils.embeddings import get_embeddings
from app.utils.faiss_loader import safe_load_faiss

#import app.utils.notification_service as notification_service
os.environ["LANGCHAIN_ALLOW_DANGEROUS_DESERIALIZATION"] = "True"

# 1. Vector Store Handler
@FunctionHandler.register
def load_vector_index(index_name: str, index_root: str = "data/faiss_index") -> Any:
    import os
    from langchain_community.vectorstores import FAISS
    from app.utils.embeddings import get_embeddings
    os.environ["LANGCHAIN_ALLOW_DANGEROUS_DESERIALIZATION"] = "True"
    """Load a FAISS vector index from storage"""
    index_path = Path(index_root) / index_name
    if not index_path.exists():
    #if not (index_path / "index.pkl").exists():
        raise FileNotFoundError(f"Index '{index_name}' not found")

    # Actual loading logic would go here
    index = FAISS.load_local(
        str(index_path),
        get_embeddings(),
        allow_dangerous_deserialization=True
    )    
    return index
    #return {"status": "loaded", "index": index}

# 2. Notification Handler
@FunctionHandler.register
def send_notification(
    content: str, 
    recipients: str, 
    channels: List[str],
    service: str = "flowise"
):
    """Send notification through specified service and channels"""
    recipient_list = [r.strip() for r in recipients.split(",") if r.strip()]
    result = notification_service.send_notification(
        content=content,
        recipients=recipient_list,
        channels=channels,
        service=service
    )
    return {"status": "sent", "result": result}

# 3. Document Ingestion Handler
@FunctionHandler.register
def ingest_document(file_path: str, index_name: str):
    """Ingest a document into the vector store"""
    # Actual ingestion logic would go here
    return {"status": "ingested", "file": file_path, "index": index_name}

# 4. Web Search Handler
@FunctionHandler.register
def web_search(query: str, max_results: int = 3):
    """Perform a web search and return results"""
    # This would be implemented with a real search API
    return {
        "query": query,
        "results": [
            {"title": f"Result {i}", "url": f"https://example.com/result{i}"}
            for i in range(max_results)
        ]
    }

# 5. Data Retrieval Handler
@FunctionHandler.register
def retrieve_data(key: str, context: dict):
    """Retrieve data from context memory"""
    return context.get(key, None)
