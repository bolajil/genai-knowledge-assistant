# save as: ingest_document_semantic.py
from unstructured.partition.pdf import partition_pdf
from unstructured.chunking.title import chunk_by_title
from sentence_transformers import SentenceTransformer
import json
import numpy as np
from pathlib import Path

# 1. Extract Elements from PDF
print("Extracting elements from PDF...")
file_path = "path/to/your/Bylaw02.pdf"
raw_pdf_elements = partition_pdf(
    filename=file_path,
    strategy="hi_res", # High resolution processing for accuracy
    infer_table_structure=True,
    chunking_strategy="by_title", # CRITICAL: This chunks by title!
    max_characters=2000, # Adjust as needed
    new_after_n_chars=1500,
    combine_text_under_n_chars=1000
)

# 2. chunk_by_title is already done by partition_pdf, so we get our chunks directly
chunks = [str(element) for element in raw_pdf_elements]
print(f"Created {len(chunks)} semantic chunks.")

# 3. Generate Metadata for each chunk (optional but highly recommended)
# For a simple approach, we can just number them. For advanced, you could use a model to title each chunk.
metadata = [{"chunk_id": i, "source": file_path} for i in range(len(chunks))]

# 4. Generate Embeddings for each chunk
print("Generating embeddings...")
model = SentenceTransformer('all-MiniLM-L6-v2')
chunk_embeddings = model.encode(chunks)

# 5. Save everything to your index directory
index_name = "Bylaw02_index_semantic" # New index name!
index_path = Path(f"data/indexes/{index_name}")
index_path.mkdir(parents=True, exist_ok=True)

# Save chunks and metadata
index_data = {
    "chunks": chunks,
    "metadata": metadata
}
with open(index_path / "semantic_chunks.json", 'w', encoding='utf-8') as f:
    json.dump(index_data, f, indent=4)

# Save embeddings
np.save(index_path / "chunk_embeddings.npy", chunk_embeddings)

print(f"Ingestion complete! New index saved to: {index_path}")
print("Update your query function to point to this new index.")
