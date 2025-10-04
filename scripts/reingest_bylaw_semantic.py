"""
Re-ingest ByLaw document with proper semantic chunking and embeddings
"""

import logging
import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.semantic_chunking_strategy import create_semantic_chunks

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def reingest_bylaw_document():
    """Re-ingest ByLaw document with semantic chunking"""
    
    print("🔄 Re-ingesting ByLaw Document with Semantic Chunking")
    print("=" * 60)
    
    try:
        # Load existing ByLaw document
        bylaw_index_path = Path("data/indexes/ByLawS2_index")
        extracted_text_path = bylaw_index_path / "extracted_text.txt"
        
        if not extracted_text_path.exists():
            print("❌ ByLaw extracted text not found")
            return False
        
        print("📄 Loading ByLaw document...")
        with open(extracted_text_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"📊 Document length: {len(content)} characters")
        
        # Apply semantic chunking with recommended settings
        print("🧠 Applying semantic chunking...")
        print("   • Chunk size: 512 characters")
        print("   • Chunk overlap: 100 characters") 
        print("   • Split by headers: Enabled")
        print("   • Embeddings: Enabled")
        
        chunks = create_semantic_chunks(
            content=content,
            document_name="ByLawS2_index",
            chunk_size=512,
            chunk_overlap=100
        )
        
        if not chunks:
            print("❌ No chunks created")
            return False
        
        print(f"✅ Created {len(chunks)} semantic chunks")
        
        # Save semantic chunks
        print("💾 Saving semantic chunks...")
        for i, chunk in enumerate(chunks):
            chunk_file = bylaw_index_path / f"semantic_chunk_{i+1}.json"
            with open(chunk_file, "w", encoding="utf-8") as f:
                json.dump(chunk, f, indent=2, ensure_ascii=False)
        
        # Save chunk metadata
        metadata = {
            'total_chunks': len(chunks),
            'chunking_method': 'semantic',
            'chunk_size': 512,
            'chunk_overlap': 100,
            'split_by_headers': True,
            'use_embeddings': True,
            'document_name': 'ByLawS2_index',
            'chunks': []
        }
        
        # Analyze chunks
        header_chunks = 0
        embedded_chunks = 0
        
        for chunk in chunks:
            chunk_info = {
                'title': chunk['title'],
                'size': chunk['chunk_size'],
                'has_embedding': chunk.get('has_embedding', False),
                'chunk_type': chunk['chunk_type'],
                'hierarchy_level': len(chunk.get('hierarchy', []))
            }
            metadata['chunks'].append(chunk_info)
            
            if chunk['chunk_type'] == 'semantic_header':
                header_chunks += 1
            if chunk.get('has_embedding', False):
                embedded_chunks += 1
        
        # Save metadata
        with open(bylaw_index_path / "chunks_metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        
        print("\n📋 Chunking Results:")
        print(f"   • Total chunks: {len(chunks)}")
        print(f"   • Header-based chunks: {header_chunks}")
        print(f"   • Size-based chunks: {len(chunks) - header_chunks}")
        print(f"   • Chunks with embeddings: {embedded_chunks}")
        
        # Show sample chunks
        print("\n🔍 Sample Chunks:")
        for i, chunk in enumerate(chunks[:3]):
            print(f"\n   Chunk {i+1}: {chunk['title']}")
            print(f"   Size: {chunk['chunk_size']} chars")
            print(f"   Type: {chunk['chunk_type']}")
            print(f"   Hierarchy: {' > '.join(chunk.get('hierarchy', []))}")
            print(f"   Preview: {chunk['content'][:100]}...")
        
        print(f"\n✅ ByLaw document successfully re-ingested with semantic chunking!")
        print(f"📁 Chunks saved to: {bylaw_index_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error re-ingesting ByLaw document: {e}")
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = reingest_bylaw_document()
    sys.exit(0 if success else 1)
