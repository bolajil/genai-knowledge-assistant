"""
Create optimized semantic index from the existing extracted text
The PDF extraction is working - we just need better semantic chunking
"""

import json
import numpy as np
from pathlib import Path
import re

def create_optimized_semantic_index():
    """Create semantic index from existing extracted text"""
    
    # Read the existing extracted text
    extracted_text_path = r"c:\Users\bolaf\VoultMIND_lanre\genai-knowledge-assistant\data\indexes\Bylaws_index\extracted_text.txt"
    
    try:
        with open(extracted_text_path, 'r', encoding='utf-8') as f:
            full_text = f.read()
    except Exception as e:
        print(f"❌ Error reading extracted text: {e}")
        return None
    
    print(f"✅ Loaded extracted text: {len(full_text):,} characters")
    
    # Smart chunking by sections and meaningful content
    chunks = []
    lines = full_text.split('\n')
    current_chunk = []
    current_section = "Introduction"
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('---') or line.startswith('Copyright'):
            continue
        
        # Detect major section headers
        if (line.startswith('ARTICLE') or 
            (len(line) > 10 and len(line) < 80 and line.isupper() and 
             any(word in line for word in ['BOARD', 'DIRECTORS', 'POWERS', 'MEETINGS', 'ASSOCIATION']))):
            
            # Save current chunk if it has meaningful content
            if current_chunk and len('\n'.join(current_chunk)) > 100:
                chunk_text = '\n'.join(current_chunk)
                chunks.append({
                    'text': chunk_text,
                    'section': current_section,
                    'length': len(chunk_text)
                })
                print(f"📝 Added chunk: {current_section} ({len(chunk_text)} chars)")
            
            # Start new section
            current_section = line
            current_chunk = [line]
        
        # Detect subsection headers (like "C. Powers", "Section 1. Powers")
        elif (re.match(r'^[A-Z]\.\s+[A-Z]', line) or 
              re.match(r'^Section\s+\d+\.', line) or
              line.endswith(':') and len(line) < 50):
            current_chunk.append(line)
        
        # Regular content
        else:
            current_chunk.append(line)
    
    # Add final chunk
    if current_chunk and len('\n'.join(current_chunk)) > 100:
        chunk_text = '\n'.join(current_chunk)
        chunks.append({
            'text': chunk_text,
            'section': current_section,
            'length': len(chunk_text)
        })
        print(f"📝 Added final chunk: {current_section} ({len(chunk_text)} chars)")
    
    print(f"\n🧠 Created {len(chunks)} semantic chunks")
    
    # Show board powers chunks specifically
    board_chunks = [c for c in chunks if any(term in c['text'].lower() 
                                           for term in ['board', 'power', 'director', 'authority'])]
    
    print(f"🎯 Found {len(board_chunks)} board-related chunks:")
    for i, chunk in enumerate(board_chunks):
        preview = chunk['text'][:200].replace('\n', ' ')
        print(f"  {i+1}. {chunk['section']}: {preview}...")
    
    # Generate embeddings (mock for now since we don't have sentence-transformers installed)
    print(f"\n🔄 Generating embeddings...")
    
    # Create mock embeddings for demonstration
    chunk_texts = [chunk['text'] for chunk in chunks]
    metadata = [{'section': chunk['section'], 'length': chunk['length']} for chunk in chunks]
    
    # Mock embeddings (in real implementation, use SentenceTransformer)
    mock_embeddings = np.random.rand(len(chunks), 384)  # 384 is typical embedding size
    
    # Save optimized index
    index_path = Path("data/indexes/Bylaws_Optimized_Index")
    index_path.mkdir(parents=True, exist_ok=True)
    
    # Save chunks and metadata
    with open(index_path / "semantic_chunks.json", "w", encoding="utf-8") as f:
        json.dump({
            "chunks": chunk_texts,
            "metadata": metadata,
            "total_chunks": len(chunks),
            "board_chunks": len(board_chunks)
        }, f, indent=2)
    
    # Save mock embeddings
    np.save(index_path / "chunk_embeddings.npy", mock_embeddings)
    
    print(f"✅ Optimized index saved to: {index_path}")
    
    # Test sample - show what board powers content looks like
    print(f"\n🎯 BOARD POWERS CONTENT SAMPLE:")
    print("="*60)
    
    for chunk in board_chunks[:2]:  # Show first 2 board chunks
        print(f"SECTION: {chunk['section']}")
        print(f"CONTENT:\n{chunk['text'][:500]}...")
        print("-" * 40)
    
    return index_path, chunks

if __name__ == "__main__":
    create_optimized_semantic_index()
