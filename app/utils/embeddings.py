# app/utils/embeddings.py
from langchain_community.embeddings import HuggingFaceEmbeddings

EMBEDDINGS = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
