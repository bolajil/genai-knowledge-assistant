# app/utils/validate_embedding-loader.py

from embedding_client import EmbeddingClient

def validate_embedding():
    client = EmbeddingClient()
    text = "This is a test prompt"
    embedding = client.get_vector(text)

    print("\n✅ Embedding validation complete.")
    print("→ Type:", type(embedding))

if __name__ == "__main__":
    validate_embedding()
