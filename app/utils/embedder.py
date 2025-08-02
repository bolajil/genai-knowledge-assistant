LOCAL_MODEL_PATH = "utils/models/all-MiniLM-L6-v2"

from langchain_huggingface import HuggingFaceEmbeddings
EMBED_MODEL = "utils/models/all-MiniLM-L6-v2"

def get_local_embeddings():
    return HuggingFaceEmbeddings(model_name=LOCAL_MODEL_PATH)
