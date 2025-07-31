# chain_schema_debug.py

from chat_orchestrator import get_chat_chain

# 🔧 Config
provider = "gpt-4"  # Replace with desired provider
index_name = "demo_index"  # Replace with an actual ingested index

# 🧠 Step 1: Get Chain
try:
    chain = get_chat_chain(provider=provider, index_name=index_name)
    print("✅ Chain loaded successfully.")
except Exception as e:
    print(f"❌ Failed to load chain: {type(e).__name__} — {str(e)}")
    exit()

# 📦 Step 2: Print Expected Input Schema
try:
    input_schema = getattr(chain, "input_schema", None)
    print("🔍 Expected input keys:", input_schema or "⚠️ Not available — check .invoke() format")
except Exception as e:
    print(f"❌ Error accessing input schema: {type(e).__name__} — {str(e)}")

# 💬 Step 3: Test Payload
sample_payload = {
    "input": "What is the onboarding flow for new users?"
    # Change to {"query": ...} if your prompt expects {query}
}

try:
    response = chain.invoke(sample_payload)
    print("✅ Response received:")
    print(response)
except Exception as e:
    print(f"❌ Invoke failed: {type(e).__name__} — {str(e)}")
