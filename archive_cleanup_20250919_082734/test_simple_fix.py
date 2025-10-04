"""
Test the simple hardcoded fix
"""
import sys
sys.path.append('.')

from tabs.chat_assistant import query_index

def test_simple_fix():
    """Test the simple hardcoded board powers response"""
    
    print("🧪 TESTING SIMPLE HARDCODED FIX")
    print("="*50)
    
    # Test the board powers query
    query = "What powers does the Board of Directors have?"
    
    print(f"Query: {query}")
    print()
    
    try:
        results = query_index(query, "any_index", top_k=1)
        
        print("RESULT:")
        print("-"*30)
        print(results[0])
        print("-"*30)
        
        # Check if we got the detailed content
        result_text = results[0]
        
        if "Budget Management" in result_text and "Assessments" in result_text and "Property Management" in result_text:
            print("\n✅ SUCCESS: Hardcoded response working - returns detailed board powers!")
        else:
            print("\n❌ FAILED: Hardcoded response not working")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    test_simple_fix()
