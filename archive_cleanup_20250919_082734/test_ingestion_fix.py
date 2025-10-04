"""
Test script to verify document ingestion fixes
"""
import streamlit as st
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

st.title("🧪 Test Document Ingestion Fix")

# Test the index name input with default value
st.subheader("Index Name Test")

# Initialize session state
if 'test_index_name' not in st.session_state:
    st.session_state.test_index_name = "document_index"

col1, col2 = st.columns([3, 1])

with col1:
    index_name = st.text_input(
        "📦 Index Name", 
        value=st.session_state.test_index_name,
        key="test_index_input"
    )

with col2:
    st.write("")  # spacing
    if st.button("Use Default"):
        st.session_state.test_index_input = "document_index"
        st.rerun()

# Show current value
st.write(f"Current index name: '{index_name}'")
st.write(f"Is empty: {not index_name.strip()}")

# Test validation logic
if st.button("Test Validation"):
    if not index_name.strip():
        st.warning("Index name is empty - would use default: 'default_index'")
    else:
        st.success(f"Index name is valid: '{index_name}'")

# Show session state
st.subheader("Session State Debug")
st.json(dict(st.session_state))
