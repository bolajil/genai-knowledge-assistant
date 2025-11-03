#!/usr/bin/env python3
"""Quick script to verify LangGraph installation"""

try:
    import langgraph
    print(f"✅ LangGraph is installed: version {langgraph.__version__}")
    print("✅ Import successful!")
except ImportError as e:
    print(f"❌ LangGraph NOT installed: {e}")
    print("Run: pip install langgraph>=0.0.20")
except Exception as e:
    print(f"⚠️ Error checking LangGraph: {e}")
