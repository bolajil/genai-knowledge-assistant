def query_semantic_index(query, index_name, top_k=5):
    index_path = Path(f"data/indexes/{index_name}")
    with open(index_path / "semantic_chunks.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    chunks = data["chunks"]
    metadata = data["metadata"]
    
    embeddings = np.load(index_path / "chunk_embeddings.npy")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    query_embedding = model.encode(query)
    
    # Compute similarities
    from sklearn.metrics.pairwise import cosine_similarity
    similarities = cosine_similarity([query_embedding], embeddings)[0]
    top_indices = np.argsort(similarities)[-top_k:][::-1]
    
    results = []
    for idx in top_indices:
        results.append({
            "content": chunks[idx],
            "metadata": metadata[idx],
            "score": similarities[idx]
        })
    return results

# Usage
results = query_semantic_index("What specific powers and responsibilities does the Board of Directors have?", "Bylaws_Semantic_Index")
for res in results:
    print(f"Score: {res['score']:.3f} - Section: {res['metadata']['section']}")
    print(res['content'][:500] + "...\n")
