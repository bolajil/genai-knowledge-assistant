"""Quick configuration checker"""
import os
from pathlib import Path

print("Configuration Checker")
print("=" * 60)

# Check .env file
env_file = Path(".env")
if env_file.exists():
    print(f"\n[OK] .env file exists at: {env_file.absolute()}")
    
    # Read and check for API key
    content = env_file.read_text()
    if "OPENAI_API_KEY" in content:
        print("[OK] OPENAI_API_KEY found in .env file")
        
        # Check if it's set correctly
        for line in content.split('\n'):
            if line.startswith('OPENAI_API_KEY'):
                key_value = line.split('=', 1)[1].strip().strip('"').strip("'")
                if key_value and key_value != "your-key-here":
                    print(f"[OK] API key is set (length: {len(key_value)} chars)")
                    if key_value.startswith('sk-'):
                        print("[OK] API key format looks correct")
                    else:
                        print("[WARN] API key should start with 'sk-'")
                else:
                    print("[FAIL] API key is placeholder or empty")
    else:
        print("[FAIL] OPENAI_API_KEY not found in .env file")
else:
    print("[FAIL] .env file not found")

# Check environment variable
print("\n" + "-" * 60)
api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    print(f"[OK] OPENAI_API_KEY loaded in environment (length: {len(api_key)} chars)")
    if api_key.startswith('sk-'):
        print("[OK] API key format looks correct")
    else:
        print("[WARN] API key should start with 'sk-'")
else:
    print("[FAIL] OPENAI_API_KEY not loaded in environment")
    print("\nTry loading manually:")
    print("  from dotenv import load_dotenv")
    print("  load_dotenv()")

# Check LangGraph
print("\n" + "-" * 60)
try:
    import langgraph
    print(f"[OK] LangGraph installed (version: {langgraph.__version__})")
except ImportError:
    print("[FAIL] LangGraph not installed")
    print("Install with: pip install langgraph")

try:
    from langchain_openai import ChatOpenAI
    print("[OK] langchain-openai installed")
except ImportError:
    print("[FAIL] langchain-openai not installed")
    print("Install with: pip install langchain-openai")

try:
    from langchain_core.messages import HumanMessage
    print("[OK] langchain-core installed")
except ImportError:
    print("[FAIL] langchain-core not installed")
    print("Install with: pip install langchain-core")

# Check indexes
print("\n" + "-" * 60)
index_dir = Path("data/faiss_index")
if index_dir.exists():
    indexes = [d.name for d in index_dir.iterdir() if d.is_dir()]
    print(f"[OK] Found {len(indexes)} FAISS indexes")
    print(f"     {', '.join(indexes[:5])}")
else:
    print("[FAIL] data/faiss_index directory not found")

print("\n" + "=" * 60)
print("\nSummary:")
if api_key and api_key.startswith('sk-'):
    print("  API Key: READY")
else:
    print("  API Key: NOT READY - Set in .env file")

try:
    import langgraph
    print("  LangGraph: READY")
except:
    print("  LangGraph: NOT READY - Run: pip install langgraph langchain-openai langchain-core")

if index_dir.exists() and len(indexes) > 0:
    print("  Indexes: READY")
else:
    print("  Indexes: NOT READY")

print("\n" + "=" * 60)
