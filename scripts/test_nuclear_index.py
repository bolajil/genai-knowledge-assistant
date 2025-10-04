def test_nuclear_index(query, index_name="Bylaws_Nuclear_Index"):
    """Test the new semantic index"""
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    import json
    from pathlib import Path
    
    print(f"Testing query: '{query}'")
    print(f"Using index: {index_name}")
    
    index_path = Path(f"data/indexes/{index_name}")
    if not index_path.exists():
        print(f"❌ Index not found at: {index_path}")
        return []
    
    try:
        # Load data
        with open(index_path / "semantic_chunks.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        
        chunks = data["chunks"]
        metadata = data["metadata"]
        embeddings = np.load(index_path / "chunk_embeddings.npy")
        
        print(f"✅ Loaded {len(chunks)} chunks and embeddings")
        
        # Query
        model = SentenceTransformer('all-MiniLM-L6-v2')
        query_embedding = model.encode(query)
        
        # Calculate similarities using cosine similarity
        similarities = cosine_similarity([query_embedding], embeddings)[0]
        top_indices = np.argsort(similarities)[-5:][::-1]  # Top 5 results
        
        # Display results
        print(f"\n{'='*80}")
        print(f"TOP RESULTS FOR: {query}")
        print('='*80)
        
        results = []
        for i, idx in enumerate(top_indices):
            score = similarities[idx]
            section = metadata[idx].get("section", "Unknown")
            content = chunks[idx]
            
            print(f"\n🏆 RESULT #{i+1} [Score: {score:.4f}]")
            print(f"📂 Section: {section}")
            print(f"📄 Content ({len(content)} chars):")
            print("-" * 60)
            
            # Show full content but limit display for readability
            if len(content) > 1000:
                print(content[:500])
                print(f"\n... [CONTENT CONTINUES FOR {len(content)-500} MORE CHARACTERS] ...")
                print(content[-500:])
            else:
                print(content)
            
            print("-" * 60)
            
            results.append({
                "score": score,
                "section": section,
                "content": content
            })
        
        # Summary
        print(f"\n📊 SUMMARY:")
        print(f"   • Found {len([r for r in results if r['score'] > 0.3])} highly relevant results (score > 0.3)")
        print(f"   • Found {len([r for r in results if r['score'] > 0.2])} moderately relevant results (score > 0.2)")
        print(f"   • Best match score: {results[0]['score']:.4f}")
        
        # Check if we found actual content about board powers
        board_keywords = ["power", "authority", "responsibility", "duty", "shall"]
        content_quality = 0
        for result in results[:3]:  # Check top 3 results
            for keyword in board_keywords:
                if keyword.lower() in result["content"].lower():
                    content_quality += 1
        
        if content_quality > 5:
            print(f"✅ HIGH QUALITY: Found substantial content about board powers!")
        elif content_quality > 2:
            print(f"⚠️  MODERATE QUALITY: Found some content about board powers")
        else:
            print(f"❌ LOW QUALITY: Limited content about board powers found")
        
        return results
        
    except Exception as e:
        print(f"❌ Error testing index: {e}")
        return []

def run_comprehensive_test():
    """Run multiple test queries to validate the index"""
    test_queries = [
        "What specific powers and responsibilities does the Board of Directors have?",
        "What authority does the board have?",
        "Board duties and responsibilities",
        "Powers of the board of directors",
        "What can the board do?"
    ]
    
    print("🧪 RUNNING COMPREHENSIVE INDEX TEST")
    print("="*80)
    
    all_results = {}
    for query in test_queries:
        print(f"\n{'🔍 ' + query}")
        results = test_nuclear_index(query)
        all_results[query] = results
        
        if results and results[0]["score"] > 0.3:
            print(f"✅ PASSED - Good results found")
        else:
            print(f"❌ FAILED - Poor results")
    
    return all_results

if __name__ == "__main__":
    # Run the comprehensive test
    all_results = run_comprehensive_test()
    
    print(f"\n🎯 FINAL ASSESSMENT:")
    passed = sum(1 for query, results in all_results.items() 
                if results and results[0]["score"] > 0.3)
    total = len(all_results)
    
    print(f"   • Passed: {passed}/{total} queries")
    
    if passed >= total * 0.8:
        print(f"🎉 SUCCESS: Nuclear index is working well!")
    elif passed >= total * 0.5:
        print(f"⚠️  PARTIAL SUCCESS: Index needs improvement")
    else:
        print(f"❌ FAILURE: Index extraction failed, try OCR method")
