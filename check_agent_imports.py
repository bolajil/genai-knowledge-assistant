#!/usr/bin/env python3
"""Test if agent controller imports work"""

print("Testing agent controller imports...")
print("=" * 60)

try:
    from app.agents.controller_agent import (
        choose_provider, 
        generate_prompt, 
        execute_agent
    )
    print("[PASS] Successfully imported controller agent functions:")
    print("  - choose_provider")
    print("  - generate_prompt")
    print("  - execute_agent")
except Exception as e:
    print(f"[FAIL] Error importing controller agent: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

try:
    from app.mcp.protocol import ModelContext
    print("[PASS] Successfully imported ModelContext")
except Exception as e:
    print(f"[WARN] ModelContext not available: {e}")
    print("  (This is OK - fallback will be used)")

print("=" * 60)
print("[SUCCESS] Agent controller is available!")
print("\nIf you see this message, the agent should work in Streamlit.")
print("If you still get errors, restart Streamlit to clear cache.")
