# app/utils/embeddings.py
from langchain_community.embeddings import HuggingFaceEmbeddings
import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Lazy initialization to avoid PyTorch meta tensor issues
EMBEDDINGS = None

def get_embeddings():
    """Get embeddings instance with lazy initialization"""
    global EMBEDDINGS
    if EMBEDDINGS is None:
        # For compatibility with existing indexes, we need to use the same model
        # that was used to create them (all-MiniLM-L6-v2)
        import torch
        
        # Set environment variables to help with PyTorch issues
        os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        
        try:
            print("Initializing HuggingFace embeddings with all-MiniLM-L6-v2...")
            # Force CPU and disable problematic features
            torch.set_default_device('cpu')
            
            EMBEDDINGS = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': False}
            )
            print("✅ Successfully initialized HuggingFace embeddings")
            
        except Exception as e:
            print(f"❌ Failed to initialize HuggingFace embeddings: {e}")
            print("This might be due to PyTorch version compatibility issues.")
            print("Consider updating PyTorch or using a different embedding model.")
            raise RuntimeError(f"Could not initialize embeddings: {e}")
            
    return EMBEDDINGS
