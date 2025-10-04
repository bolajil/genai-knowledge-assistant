import re
from sentence_transformers import SentenceTransformer
import numpy as np
import json
from pathlib import Path

def chunk_text_by_sections(text):
    # Split text into lines
    lines = text.split('\n')
    chunks = []
    current_chunk = []
    current_section = "Introduction"
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Detect section headers (all caps, bold, etc.)
        if line.isupper() and len(line) > 5 and len(line) < 100:
            # Save current chunk if exists
            if current_chunk:
                chunks.append({
                    "section": current_section,
                    "content": "\n".join(current_chunk)
                })
            current_section = line
            current_chunk = [line]
        else:
            current_chunk.append(line)
    
    # Add the last chunk
    if current_chunk:
        chunks.append({
            "section": current_section,
            "content": "\n".join(current_chunk)
        })
    
    return chunks

# Load extracted text
with open("extracted_text.txt", "r", encoding="utf-8") as f:
    full_text = f.read()

chunks = chunk_text_by_sections(full_text)

# Prepare for embedding
chunk_texts = [chunk["content"] for chunk in chunks]
metadata = [{"section": chunk["section"]} for chunk in chunks]

# Generate embeddings
model = SentenceTransformer('all-MiniLM-L6-v2')
embeddings = model.encode(chunk_texts)

# Save to index
index_name = "Bylaws_Semantic_Index"
index_path = Path(f"data/indexes/{index_name}")
index_path.mkdir(parents=True, exist_ok=True)

# Save chunks and metadata
with open(index_path / "semantic_chunks.json", "w", encoding="utf-8") as f:
    json.dump({"chunks": chunk_texts, "metadata": metadata}, f, indent=2)

# Save embeddings
np.save(index_path / "chunk_embeddings.npy", embeddings)
