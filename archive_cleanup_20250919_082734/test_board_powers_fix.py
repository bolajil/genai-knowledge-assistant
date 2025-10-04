"""
Test the board powers query fix
"""
import sys
sys.path.append('.')

from tabs.chat_assistant import query_index

def test_board_powers_query():
    """Test that board powers query now returns detailed content"""
    
    print("🧪 TESTING BOARD POWERS QUERY FIX")
    print("="*50)
    
    # Test the specific query that was failing
    query = "What specific powers and responsibilities does the Board of Directors have?"
    index_name = "Bylaws_index"
    
    print(f"Query: {query}")
    print(f"Index: {index_name}")
    print()
    
    try:
        results = query_index(query, index_name, top_k=2)
        
        print("RESULTS:")
        print("-"*30)
        
        for i, result in enumerate(results):
            print(f"Result {i+1}:")
            print(result)
            print("-"*30)
        
        # Check if we got detailed content vs just headers
        if results:
            first_result = results[0]
            
            # Look for specific board powers (a, b, c, etc.)
            detailed_powers = ['preparing and adopting', 'making Assessments', 'collecting Assessments', 
                             'providing for the operation', 'making or contracting', 'designating, hiring']
            
            found_details = sum(1 for power in detailed_powers if power in first_result)
            
            print(f"\n📊 ASSESSMENT:")
            print(f"Found {found_details}/{len(detailed_powers)} detailed power descriptions")
            
            if found_details >= 3:
                print("✅ SUCCESS: Query now returns detailed board powers content!")
            elif found_details >= 1:
                print("⚠️  PARTIAL: Some detailed content found, but could be better")
            else:
                print("❌ FAILED: Still only getting headers/minimal content")
        else:
            print("❌ FAILED: No results returned")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    test_board_powers_query()
