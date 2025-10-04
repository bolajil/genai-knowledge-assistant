"""
Simple Direct Migration - FAISS to Weaviate
Uses direct REST API to ensure documents are uploaded
"""

import pickle
import requests
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv("config/weaviate.env")
load_dotenv("config/storage.env")

# Load Weaviate credentials
WEAVIATE_URL = os.getenv("WEAVIATE_URL", "https://mfasasqxqnj0uispvnxa.c0.us-west3.gcp.weaviate.cloud")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")

print(f"🌐 Weaviate URL: {WEAVIATE_URL}")
print(f"🔑 API Key: {'Set' if WEAVIATE_API_KEY else 'Not Set'}")

# Load FAISS documents
print("📂 Loading FAISS documents...")
faiss_path = Path("data/faiss_index/Bylaws_index/documents.pkl")

with open(faiss_path, 'rb') as f:
    documents = pickle.load(f)

print(f"✅ Loaded {len(documents)} documents")

# Prepare headers
headers = {
    "Authorization": f"Bearer {WEAVIATE_API_KEY}",
    "Content-Type": "application/json"
}

# Upload each document directly via REST API
print(f"\n⬆️ Uploading to Weaviate...")

for i, doc in enumerate(documents, 1):
    # Prepare document
    if isinstance(doc, str):
        content = doc
    else:
        content = str(doc)
    
    # Create object
    obj = {
        "class": "Bylaw2025",
        "properties": {
            "content": content,
            "source": "Bylaws_index",
            "page": i
        }
    }
    
    # Upload via REST API
    response = requests.post(
        f"{WEAVIATE_URL}/v1/objects",
        headers=headers,
        json=obj
    )
    
    if response.status_code in [200, 201]:
        print(f"✅ Document {i} uploaded successfully")
    else:
        print(f"❌ Document {i} failed: {response.status_code} - {response.text}")

print(f"\n🎉 Migration complete!")
print(f"\n💡 Next steps:")
print("1. Refresh your Weaviate dashboard")
print("2. Check Bylaw2025 collection - should show 2 objects")
print("3. Go to Query Assistant and select Weaviate backend")
