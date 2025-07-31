from sentence_transformers import SentenceTransformer

print("\n🔍 Testing model load from snapshot...\n")
model = SentenceTransformer("utils/models/all-MiniLM-L6-v2")
print("✅ Model loaded with embedding dimension:", model.get_sentence_embedding_dimension())
