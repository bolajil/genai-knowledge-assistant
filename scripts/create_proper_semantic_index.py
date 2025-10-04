def create_proper_semantic_index(text, index_name):
    """Create a well-structured semantic index"""
    import re
    from sentence_transformers import SentenceTransformer
    import numpy as np
    import json
    from pathlib import Path
    
    print(f"Creating semantic index: {index_name}")
    print(f"Input text length: {len(text):,} characters")
    
    # Clean and structure the text
    lines = text.split('\n')
    chunks = []
    current_chunk = []
    current_section = "Introduction"
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Detect section headers (all caps, likely headers)
        if (len(line) > 5 and len(line) < 100 and 
            line.isupper() and not line.isdigit() and
            not line.startswith('Page') and not line.startswith('http')):
            
            # Save current chunk
            if current_chunk:
                chunk_text = "\n".join(current_chunk)
                if len(chunk_text) > 50:  # Only add meaningful chunks
                    chunks.append({
                        "text": chunk_text,
                        "section": current_section
                    })
                    print(f"Added chunk for section: {current_section} ({len(chunk_text)} chars)")
            
            # Start new section
            current_section = line
            current_chunk = [line]
        else:
            current_chunk.append(line)
    
    # Add the final chunk
    if current_chunk:
        chunk_text = "\n".join(current_chunk)
        if len(chunk_text) > 50:
            chunks.append({
                "text": chunk_text,
                "section": current_section
            })
            print(f"Added final chunk for section: {current_section} ({len(chunk_text)} chars)")
    
    print(f"Created {len(chunks)} semantic chunks")
    
    # Generate embeddings
    print("Generating embeddings...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    chunk_texts = [chunk["text"] for chunk in chunks]
    embeddings = model.encode(chunk_texts, show_progress_bar=True)
    
    # Save index
    index_path = Path(f"data/indexes/{index_name}")
    index_path.mkdir(parents=True, exist_ok=True)
    
    # Save chunks with metadata
    with open(index_path / "semantic_chunks.json", "w", encoding="utf-8") as f:
        json.dump({
            "chunks": chunk_texts,
            "metadata": [{"section": chunk["section"]} for chunk in chunks]
        }, f, indent=2)
    
    # Save embeddings
    np.save(index_path / "chunk_embeddings.npy", embeddings)
    
    print(f"✅ Index saved to: {index_path}")
    print(f"   - semantic_chunks.json: {len(chunks)} chunks")
    print(f"   - chunk_embeddings.npy: {embeddings.shape}")
    
    # Show sample chunks that might contain board powers
    print("\nSample chunks containing 'board' or 'power':")
    for i, chunk in enumerate(chunks):
        if any(term in chunk["text"].lower() for term in ["board", "power", "director"]):
            preview = chunk["text"][:200] + "..." if len(chunk["text"]) > 200 else chunk["text"]
            print(f"{i+1}. Section: {chunk['section']}")
            print(f"   Content: {preview}\n")
            if i >= 2:  # Show max 3 samples
                break
    
    return index_path

if __name__ == "__main__":
    # Try to load the best extraction
    try:
        with open("best_extraction.txt", "r", encoding="utf-8") as f:
            best_text = f.read()
        print("✅ Loaded best_extraction.txt")
    except FileNotFoundError:
        print("❌ best_extraction.txt not found. Run multi_method_extraction.py first.")
        exit()
    
    if not best_text.strip():
        print("❌ best_extraction.txt is empty")
        exit()
    
    # Create the semantic index
    index_path = create_proper_semantic_index(best_text, "Bylaws_Nuclear_Index")
    print(f"\n🚀 Nuclear semantic index created successfully!")
    print(f"Ready to test with board powers queries.")
