"""
Test Chunking Fix

Test the improved chunking to verify word boundaries are preserved
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

def test_chunking_fix():
    """Test the improved chunking on the ByLawS2_index"""
    
    print("🧪 TESTING IMPROVED CHUNKING")
    print("=" * 40)
    
    try:
        from utils.improved_text_chunking import apply_improved_intelligent_chunking, validate_chunk_quality
        
        # Read the problematic text
        index_path = Path(__file__).parent / "data" / "indexes" / "ByLawS2_index" / "extracted_text.txt"
        
        if not index_path.exists():
            print(f"❌ Index file not found: {index_path}")
            return
        
        with open(index_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"📄 Original content length: {len(content)} characters")
        
        # Test chunking options
        chunking_options = {
            "chunk_size": 1500,
            "chunk_overlap": 500,
            "respect_section_breaks": True,
            "extract_tables": True,
            "preserve_heading_structure": True
        }
        
        # Apply improved chunking
        chunks = apply_improved_intelligent_chunking(content, chunking_options)
        
        print(f"📊 Generated {len(chunks)} chunks")
        
        # Validate chunk quality
        quality = validate_chunk_quality(chunks)
        
        print(f"\n✅ Chunk Quality Assessment:")
        print(f"   Valid: {quality['valid']}")
        print(f"   Total chunks: {quality['total_chunks']}")
        print(f"   Average size: {quality['avg_chunk_size']:.0f} chars")
        
        if quality['issues']:
            print(f"   ❌ Issues: {len(quality['issues'])}")
            for issue in quality['issues'][:3]:
                print(f"      - {issue}")
        
        if quality['warnings']:
            print(f"   ⚠️  Warnings: {len(quality['warnings'])}")
            for warning in quality['warnings'][:3]:
                print(f"      - {warning}")
        
        # Check specific problematic areas
        print(f"\n🔍 CHECKING FOR WORD BOUNDARY ISSUES:")
        
        problem_words = ["WAIVER", "SPECIAL", "MEETINGS", "NOTICE"]
        
        for i, chunk in enumerate(chunks[:5]):  # Check first 5 chunks
            chunk_lower = chunk.lower()
            
            for word in problem_words:
                word_lower = word.lower()
                
                # Check for broken words
                if f" {word_lower[:3]}" in chunk_lower and word_lower not in chunk_lower:
                    print(f"   ⚠️  Chunk {i+1}: Possible broken word '{word}' -> found '{word[:3]}'")
                elif word_lower in chunk_lower:
                    print(f"   ✅ Chunk {i+1}: Word '{word}' preserved correctly")
        
        # Show first chunk content for manual inspection
        print(f"\n📝 FIRST CHUNK PREVIEW:")
        first_chunk = chunks[0] if chunks else ""
        preview = first_chunk[:500] + "..." if len(first_chunk) > 500 else first_chunk
        print(preview)
        
        # Check for the specific "WAIVER" issue
        waiver_found = False
        broken_waiver_found = False
        
        for i, chunk in enumerate(chunks):
            if "WAIVER OF NOTICE" in chunk:
                waiver_found = True
                print(f"\n✅ 'WAIVER OF NOTICE' found correctly in chunk {i+1}")
            elif "W AIYER" in chunk or "AIYER" in chunk:
                broken_waiver_found = True
                print(f"\n❌ Broken 'WAIVER' found in chunk {i+1}: contains 'W AIYER' or 'AIYER'")
        
        if not waiver_found and not broken_waiver_found:
            print(f"\n⚠️  'WAIVER' not found in any chunk")
        
        print(f"\n📋 SUMMARY:")
        print(f"   Chunking: {'✅ Improved' if quality['valid'] else '❌ Issues found'}")
        print(f"   Word boundaries: {'✅ Preserved' if not broken_waiver_found else '❌ Still broken'}")
        print(f"   Ready for search: {'✅ Yes' if quality['valid'] and not broken_waiver_found else '❌ Needs more work'}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_chunking_fix()
