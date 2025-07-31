# utils/langgraph_agent.py

from langchain_community.chat_models import ChatOpenAI
from langgraph.prebuilt import create_agent_executor
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.tools import Tool

EMBED_MODEL = "utils/models/all-MiniLM-L6-v2"
INDEX_ROOT = "data/faiss_index"

def retrieve_docs(question: str, index_name: str) -> str:
    db = FAISS.load_local(
        f"{INDEX_ROOT}/{index_name}",
        HuggingFaceEmbeddings(model_name=EMBED_MODEL),
        allow_dangerous_deserialization=True
    )
    docs = db.similarity_search(question, k=4)
    return "\n\n".join([d.page_content for d in docs])

def build_graph(index_name: str, llm):
    tools = [
        Tool(
            name="RetrieveDocs",
            func=lambda x: retrieve_docs(x, index_name),
            description="Retrieve relevant document chunks"
        )
    ]

    # create_agent_executor will handle calling tools as needed:
    return create_agent_executor(llm=llm, tools=tools)

