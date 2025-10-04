import PyPDF2
import re
from sentence_transformers import SentenceTransformer, util
import numpy as np
import json
from pathlib import Path

def extract_text_with_structure(pdf_path):
    """Extract text from PDF while preserving section structure"""
    text_by_section = {}
    current_section = "Introduction"
    text_by_section[current_section] = []
    
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        
        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]
            text = page.extract_text()
            
            # Split text into lines and process
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Detect section headers (all caps, bold patterns, etc.)
                if (line.isupper() and len(line) > 5 and len(line) < 100 and 
                    not line.startswith('PAGE') and not line.isdigit()):
                    current_section = line
                    text_by_section[current_section] = []
                else:
                    if current_section not in text_by_section:
                        text_by_section[current_section] = []
                    text_by_section[current_section].append(line)
    
    # Convert to final chunks
    chunks = []
    metadata = []
    
    for section, content in text_by_section.items():
        if content:
            chunk_text = f"{section}\n\n" + "\n".join(content)
            # Split large sections into smaller chunks
            if len(chunk_text) > 1500:
                sentences = re.split(r'(?<=[.!?])\s+', chunk_text)
                current_chunk = []
                current_length = 0
                
                for sentence in sentences:
                    if current_length + len(sentence) > 1200 and current_chunk:
                        chunks.append(" ".join(current_chunk))
                        metadata.append({"section": section, "type": "content"})
                        current_chunk = []
                        current_length = 0
                    
                    current_chunk.append(sentence)
                    current_length += len(sentence)
                
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                    metadata.append({"section": section, "type": "content"})
            else:
                chunks.append(chunk_text)
                metadata.append({"section": section, "type": "full_section"})
    
    return chunks, metadata

def create_semantic_index(pdf_path, index_name):
    """Create a proper semantic index from PDF"""
    print("Extracting text with structure preservation...")
    chunks, metadata = extract_text_with_structure(pdf_path)
    
    print("Generating embeddings...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    embeddings = model.encode(chunks)
    
    # Save index
    index_path = Path(f"data/indexes/{index_name}")
    index_path.mkdir(parents=True, exist_ok=True)
    
    # Save chunks and metadata
    index_data = {
        "chunks": chunks,
        "metadata": metadata
    }
    
    with open(index_path / "semantic_chunks.json", 'w', encoding='utf-8') as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)
    
    # Save embeddings
    np.save(index_path / "chunk_embeddings.npy", embeddings)
    
    print(f"Created index with {len(chunks)} chunks")
    print(f"Index saved to: {index_path}")
    
    return index_path

def query_semantic_index(query, index_name, top_k=5):
    """Query the semantic index"""
    index_path = Path(f"data/indexes/{index_name}")
    
    if not index_path.exists():
        return ["Index not found"]
    
    # Load chunks and metadata
    with open(index_path / "semantic_chunks.json", 'r', encoding='utf-8') as f:
        index_data = json.load(f)
    
    chunks = index_data["chunks"]
    metadata = index_data["metadata"]
    
    # Load embeddings
    embeddings = np.load(index_path / "chunk_embeddings.npy")
    
    # Encode query and find similar chunks
    model = SentenceTransformer('all-MiniLM-L6-v2')
    query_embedding = model.encode(query)
    
    # Calculate similarities
    similarities = util.cos_sim(query_embedding, embeddings)[0]
    
    # Get top results
    top_indices = np.argsort(-similarities)[:top_k]
    
    # Format results
    results = []
    for idx in top_indices:
        score = similarities[idx].item()
        chunk = chunks[idx]
        meta = metadata[idx]
        
        result_text = f"[Relevance: {score:.3f}] "
        if 'section' in meta:
            result_text += f"Section: {meta['section']}\n\n"
        
        # Show preview of content
        preview = chunk[:500] + "..." if len(chunk) > 500 else chunk
        result_text += f"{preview}\n"
        
        results.append(result_text)
    
    return results

# Usage example:
if __name__ == "__main__":
    # First, create the index
    pdf_path = "path/to/your/Bylaw02.pdf"
    index_name = "Bylaws_Semantic_Index"
    
    # Create the semantic index
    create_semantic_index(pdf_path, index_name)
    
    # Then query it
    query = "What specific powers and responsibilities does the Board of Directors have?"
    results = query_semantic_index(query, index_name)
    
    for i, result in enumerate(results, 1):
        print(f"Result {i}:\n{result}\n{'-'*50}")
