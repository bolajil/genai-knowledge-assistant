"""Test Weaviate connection"""
from utils.weaviate_manager import get_weaviate_manager

def test_connection():
    try:
        wm = get_weaviate_manager()
        print(f"✅ Successfully connected to Weaviate at {wm.url}")
        return True
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        return False

if __name__ == "__main__":
    test_connection()
