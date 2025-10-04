from sentence_transformers import SentenceTransformer

MODEL_PATH = "utils/models/all-MiniLM-L6-v2"

model = SentenceTransformer(MODEL_PATH)
embedding = model.encode(["This is a test sentence"])
print("✅ Model loaded, embedding shape:", embedding.shape)
