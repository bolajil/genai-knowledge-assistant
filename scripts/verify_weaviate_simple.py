import os
import sys

# Load env from config/weaviate.env manually
def load_env_file():
    env_path = os.path.join("config", "weaviate.env")
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
                    print(f"Loaded: {key}={value[:20]}...")

def main():
    print("=== Weaviate Connection Test (Simple) ===")
    
    # Load environment
    load_env_file()
    
    url = os.getenv("WEAVIATE_URL")
    api_key = os.getenv("WEAVIATE_API_KEY")
    
    print(f"WEAVIATE_URL: {url}")
    print(f"WEAVIATE_API_KEY: {'Set' if api_key else 'Not set'}")
    
    if not url:
        print("ERROR: WEAVIATE_URL not found")
        return 1
    
    if not api_key:
        print("WARNING: WEAVIATE_API_KEY not found")
    
    # Try importing weaviate
    try:
        import weaviate
        from weaviate.auth import AuthApiKey
        print("[OK] Weaviate SDK imported successfully")
    except ImportError as e:
        print(f"[ERROR] Weaviate SDK not available: {e}")
        return 2
    
    # Try connecting
    try:
        client = weaviate.connect_to_weaviate_cloud(
            cluster_url=url,
            auth_credentials=AuthApiKey(api_key) if api_key else None,
        )
        print("[OK] SDK connection established")
        
        # List collections
        cols = client.collections.list_all()
        print(f"[OK] Collections: {[c.name for c in cols]}")
        client.close()
        return 0
        
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return 3

if __name__ == "__main__":
    sys.exit(main())
