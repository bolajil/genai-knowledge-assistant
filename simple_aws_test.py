#!/usr/bin/env python
# Simple test script for AWS document summarization

import sys
from pathlib import Path

# Fix the path to ensure parent directory is in the Python path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Mock streamlit module
sys.modules['streamlit'] = type('MockStreamlit', (), {
    'markdown': lambda *args, **kwargs: None,
    'info': lambda *args, **kwargs: None,
    'text': lambda *args, **kwargs: None,
    'write': lambda *args, **kwargs: None,
    'columns': lambda *args, **kwargs: [type('MockColumn', (), {'markdown': lambda *args, **kwargs: None})()],
    'cache_resource': lambda f: f,
    'spinner': lambda *args, **kwargs: type('MockSpinner', (), {'__enter__': lambda self: None, '__exit__': lambda self, *args: None})(),
    'session_state': {},
    'title': lambda *args, **kwargs: None,
    'radio': lambda *args, **kwargs: None,
    'selectbox': lambda *args, **kwargs: None,
    'multiselect': lambda *args, **kwargs: None,
    'button': lambda *args, **kwargs: None,
    'expander': lambda *args, **kwargs: type('MockExpander', (), {'__enter__': lambda self: None, '__exit__': lambda self, *args: None})()
})

try:
    print("Importing agent_assistant_enhanced module...")
    from tabs.agent_assistant_enhanced import fetch_document_content

    print("\nTesting AWS document fetching...")
    aws_content = fetch_document_content("AWS")
    if aws_content and len(aws_content) > 50:
        print(f"✅ AWS document fetched successfully ({len(aws_content)} characters)")
        print(f"First 100 characters: {aws_content[:100]}...")
    else:
        print("❌ Failed to fetch AWS document")

except Exception as e:
    print(f"❌ Error: {str(e)}")
