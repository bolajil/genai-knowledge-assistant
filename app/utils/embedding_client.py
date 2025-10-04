from sentence_transformers import SentenceTransformer
import torch

class EmbeddingClient:
    def __init__(self, model_name="sentence-transformers/all-MiniLM-L6-v2"):
        try:
            # Load fully onto default device first to avoid meta tensor
            self.model = SentenceTransformer(model_name)  # Fully materialized
            if torch.cuda.is_available():
                self.model = self.model.to("cpu")
        except Exception as e:
            print(f"[EmbeddingClient] Failed to load model: {e}")
            self.model = None

    def get_vector(self, text: str):
        if not self.model:
            raise RuntimeError("Embedding model not initialized")
        return self.model.encode(text, show_progress_bar=False)
