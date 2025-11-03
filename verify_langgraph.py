#!/usr/bin/env python3
"""Verify LangGraph is properly installed and working"""

print("=" * 60)
print("LangGraph Installation Verification")
print("=" * 60)

# Test 1: Import
try:
    import langgraph
    print("✅ Test 1: LangGraph import successful")
except ImportError as e:
    print(f"❌ Test 1 FAILED: Cannot import langgraph - {e}")
    exit(1)

# Test 2: Check key components
try:
    from langgraph.graph import StateGraph
    print("✅ Test 2: StateGraph import successful")
except ImportError as e:
    print(f"❌ Test 2 FAILED: Cannot import StateGraph - {e}")
    exit(1)

# Test 3: Check if we can create a simple graph
try:
    from typing import TypedDict
    
    class State(TypedDict):
        message: str
    
    graph = StateGraph(State)
    print("✅ Test 3: Can create StateGraph instance")
except Exception as e:
    print(f"❌ Test 3 FAILED: Cannot create graph - {e}")
    exit(1)

# Test 4: Check package info
try:
    import pkg_resources
    version = pkg_resources.get_distribution("langgraph").version
    print(f"✅ Test 4: LangGraph version {version}")
except Exception as e:
    print(f"⚠️  Test 4: Could not get version - {e}")

print("=" * 60)
print("✅ ALL TESTS PASSED - LangGraph is working!")
print("=" * 60)
print("\n📝 Next step: Restart Streamlit to pick up the changes")
print("   1. Stop Streamlit (Ctrl+C in terminal)")
print("   2. Run: streamlit run genai_dashboard_modular.py")
