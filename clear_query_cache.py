"""
Clear Query Cache Script
========================
Clears cached query results to ensure new formatter is used.
"""

import os
import sys

def clear_cache():
    """Clear all query caches"""
    print("🧹 Clearing Query Assistant Cache...")
    
    # Clear Redis cache if available
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        # Get all query cache keys
        keys = r.keys('query_cache:*')
        if keys:
            r.delete(*keys)
            print(f"✅ Cleared {len(keys)} Redis cache entries")
        else:
            print("ℹ️  No Redis cache entries found")
    except Exception as e:
        print(f"⚠️  Redis not available: {e}")
    
    # Clear Streamlit cache directory
    try:
        import shutil
        from pathlib import Path
        
        cache_dirs = [
            Path.home() / ".streamlit" / "cache",
            Path(".streamlit") / "cache",
            Path("__pycache__"),
            Path("tabs") / "__pycache__",
            Path("utils") / "__pycache__"
        ]
        
        for cache_dir in cache_dirs:
            if cache_dir.exists():
                shutil.rmtree(cache_dir)
                print(f"✅ Cleared {cache_dir}")
    except Exception as e:
        print(f"⚠️  Could not clear Streamlit cache: {e}")
    
    print("\n✨ Cache cleared! Please restart the Streamlit app:")
    print("   streamlit run genai_dashboard_modular.py")
    print("\nThen run a new query to see the improved formatting.")

if __name__ == "__main__":
    clear_cache()
