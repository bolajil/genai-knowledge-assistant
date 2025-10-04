# app/tools/mcp_tools.py

import importlib
import traceback
from datetime import datetime

def check_mcp_components():
    status = {
        "timestamp": str(datetime.now()),
        "retriever_loaded": False,
        "controller_agent": "❌ Not loaded",
        "schema_trace": "❌ Unverified",
        "error_log": [],
    }
    try:
        from app.agents.controller_agent import EMBEDDINGS
        status["controller_agent"] = "✅ Initialized"
        status["retriever_loaded"] = True if EMBEDDINGS else False
    except Exception as e:
        status["error_log"].append(traceback.format_exc())
    try:
        from app.utils.index_utils import load_index
        if callable(load_index):
            status["schema_trace"] = "✅ Function detected"
    except Exception as e:
        status["error_log"].append(traceback.format_exc())

    return status
