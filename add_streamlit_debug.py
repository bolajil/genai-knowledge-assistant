#!/usr/bin/env python3
"""
Add Streamlit debug output to see what's happening
"""

import time
from pathlib import Path

print("=== STREAMLIT DEBUG OUTPUT ADDED ===")

# Create refresh trigger
trigger_file = Path("ui_refresh_trigger.txt")
trigger_time = time.time()
trigger_file.write_text(f"UI_REFRESH_TRIGGER={trigger_time}")

print(f"Created refresh trigger: {trigger_time}")
print("\n🔍 DEBUG OUTPUT ADDED:")
print("✅ Collection name and store type display")
print("✅ Manager store lookup verification")
print("✅ API key presence check")
print("✅ Create result display")
print("✅ Detailed error information")

print("\n🎯 MYSTERY TO SOLVE:")
print("- Direct Python tests work perfectly ✅")
print("- Manager create_collection_sync works ✅") 
print("- Pinecone API and adapter work ✅")
print("- But Streamlit UI fails ❌")

print("\n📋 NEXT STEPS:")
print("1. Refresh your Streamlit app")
print("2. Try creating collection 'democollections' again")
print("3. Look at the debug output to see:")
print("   - Is the store found?")
print("   - Is API key present?")
print("   - What is the actual create result?")

print("\nThis debug output will reveal the exact issue! 🕵️")
