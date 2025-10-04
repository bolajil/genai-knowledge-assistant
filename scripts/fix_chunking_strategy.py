"""
Fix Chunking Strategy - Use larger chunks to preserve complete sections
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

def fix_bylaw_chunking():
    """Re-chunk ByLaw document with larger, section-preserving chunks"""
    
    print("🔧 Fixing ByLaw Chunking Strategy")
    print("=" * 50)
    
    try:
        # Load existing ByLaw document
        bylaw_index_path = Path("data/indexes/ByLaw01_index")
        extracted_text_path = bylaw_index_path / "extracted_text.txt"
        
        if not extracted_text_path.exists():
            print("❌ ByLaw extracted text not found")
            return False
        
        print("📄 Loading ByLaw document...")
        with open(extracted_text_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"📊 Document length: {len(content)} characters")
        
        # Remove existing semantic chunks
        print("🧹 Removing existing fragmented chunks...")
        chunk_files = list(bylaw_index_path.glob("semantic_chunk_*.json"))
        print(f"   Found {len(chunk_files)} existing chunks to remove")
        
        for chunk_file in chunk_files:
            chunk_file.unlink()
        
        # Apply optimized semantic chunking
        print("🧠 Applying optimized semantic chunking...")
        print("   • Chunk size: 1500 characters (larger to preserve sections)")
        print("   • Chunk overlap: 300 characters (more overlap for context)")
        print("   • Split by headers: Enabled")
        print("   • Embeddings: Enabled")
        
        chunks = create_semantic_chunks(
            content=content,
            document_name="ByLaw01_index",
            chunk_size=1500,  # Larger chunks to preserve complete sections
            chunk_overlap=300  # More overlap for better context
        )
        
        if not chunks:
            print("❌ No chunks created")
            return False
        
        print(f"✅ Created {len(chunks)} optimized semantic chunks")
        
        # Save optimized chunks
        print("💾 Saving optimized chunks...")
        for i, chunk in enumerate(chunks):
            chunk_file = bylaw_index_path / f"semantic_chunk_{i+1}.json"
            with open(chunk_file, "w", encoding="utf-8") as f:
                json.dump(chunk, f, indent=2, ensure_ascii=False)
        
        # Update metadata
        metadata = {
            'total_chunks': len(chunks),
            'chunking_method': 'semantic_optimized',
            'chunk_size': 1500,
            'chunk_overlap': 300,
            'split_by_headers': True,
            'use_embeddings': True,
            'document_name': 'ByLaw01_index',
            'optimization': 'section_preserving',
            'chunks': []
        }
        
        # Analyze chunks for section preservation
        section_chunks = 0
        powers_found = False
        
        for i, chunk in enumerate(chunks):
            chunk_info = {
                'chunk_id': i + 1,
                'title': chunk['title'],
                'size': chunk['chunk_size'],
                'has_embedding': chunk.get('has_embedding', False),
                'chunk_type': chunk['chunk_type'],
                'hierarchy_level': len(chunk.get('hierarchy', [])),
                'contains_powers': 'powers' in chunk['content'].lower()
            }
            metadata['chunks'].append(chunk_info)
            
            if chunk['chunk_type'] == 'semantic_header':
                section_chunks += 1
            
            if 'powers' in chunk['content'].lower():
                powers_found = True
                print(f"   ✅ Found 'Powers' section in chunk {i+1}: {chunk['title']}")
        
        # Save updated metadata
        with open(bylaw_index_path / "chunks_metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        
        print("\n📋 Optimization Results:")
        print(f"   • Total chunks: {len(chunks)} (reduced from 238)")
        print(f"   • Section-based chunks: {section_chunks}")
        print(f"   • Powers section preserved: {'✅ Yes' if powers_found else '❌ No'}")
        print(f"   • Average chunk size: {sum(c['chunk_size'] for c in chunks) // len(chunks)} chars")
        
        # Show chunks containing "powers"
        powers_chunks = [c for c in chunks if 'powers' in c['content'].lower()]
        if powers_chunks:
            print(f"\n🎯 Powers-related chunks ({len(powers_chunks)}):")
            for i, chunk in enumerate(powers_chunks):
                print(f"   Chunk {chunks.index(chunk)+1}: {chunk['title']}")
                print(f"   Size: {chunk['chunk_size']} chars")
                print(f"   Preview: {chunk['content'][:150]}...")
                print()
        
        print(f"✅ ByLaw chunking strategy optimized!")
        print(f"📁 Optimized chunks saved to: {bylaw_index_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error fixing chunking strategy: {e}")
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = fix_bylaw_chunking()
    sys.exit(0 if success else 1)
