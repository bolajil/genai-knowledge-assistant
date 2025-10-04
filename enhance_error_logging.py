#!/usr/bin/env python3
"""
Enhanced error logging for Pinecone collection creation
"""

import time
from pathlib import Path

print("=== ENHANCED ERROR LOGGING ===")

# Create refresh trigger
trigger_file = Path("ui_refresh_trigger.txt")
trigger_time = time.time()
trigger_file.write_text(f"UI_REFRESH_TRIGGER={trigger_time}")

print(f"Created refresh trigger: {trigger_time}")
print("\n🔍 ENHANCED ERROR LOGGING ADDED:")
print("✅ 1. Ingestion tab now shows detailed exception info")
print("✅ 2. Pinecone adapter logs full error details")
print("✅ 3. Debug button tests collection creation with error display")
print("✅ 4. Added traceback and error type information")

print("\n🎯 DEBUGGING STEPS:")
print("1. Refresh your Streamlit app")
print("2. Click the '🔍 Debug' button to test collection creation")
print("3. Try the ingestion again to see detailed error")
print("4. Check the console/logs for full Pinecone error details")

print("\n📋 WHAT TO LOOK FOR:")
print("- API key issues")
print("- Collection name validation errors")
print("- Pinecone quota/limits")
print("- Network connectivity issues")
print("- Serverless configuration problems")

print("\nRefresh and click Debug to see the actual Pinecone error! 🔍")
