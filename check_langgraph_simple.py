#!/usr/bin/env python3
"""Simple LangGraph verification (no Unicode)"""

print("=" * 60)
print("LangGraph Installation Check")
print("=" * 60)

# Test 1: Import
try:
    import langgraph
    print("[PASS] Test 1: LangGraph import successful")
except ImportError as e:
    print(f"[FAIL] Test 1: Cannot import langgraph - {e}")
    exit(1)

# Test 2: Check key components
try:
    from langgraph.graph import StateGraph
    print("[PASS] Test 2: StateGraph import successful")
except ImportError as e:
    print(f"[FAIL] Test 2: Cannot import StateGraph - {e}")
    exit(1)

# Test 3: Check if we can create a simple graph
try:
    from typing import TypedDict
    
    class State(TypedDict):
        message: str
    
    graph = StateGraph(State)
    print("[PASS] Test 3: Can create StateGraph instance")
except Exception as e:
    print(f"[FAIL] Test 3: Cannot create graph - {e}")
    exit(1)

# Test 4: Check package info
try:
    import pkg_resources
    version = pkg_resources.get_distribution("langgraph").version
    print(f"[PASS] Test 4: LangGraph version {version}")
except Exception as e:
    print(f"[WARN] Test 4: Could not get version - {e}")

print("=" * 60)
print("[SUCCESS] ALL TESTS PASSED - LangGraph is working!")
print("=" * 60)
print("")
print("Next step: Restart Streamlit")
print("  1. Stop Streamlit (Ctrl+C in terminal)")
print("  2. Run: streamlit run genai_dashboard_modular.py")
print("")
print("The 'LangGraph not installed' message will disappear!")
