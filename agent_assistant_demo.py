import streamlit as st
import sys
from pathlib import Path

# Set page title and layout
st.set_page_config(
    page_title="Agent Assistant Demo",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stTabs [data-baseweb="tab-panel"] {
        padding-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<h1 class="main-header">🧠 VaultMind GenAI Agent Assistant Demo</h1>', unsafe_allow_html=True)

# Import the mock agent assistant
from tabs.agent_assistant_mock import render_agent_assistant

# Run the agent assistant tab
render_agent_assistant()

# Footer
st.markdown("---")
st.markdown("**Demo Application** | This is a demonstration of the enhanced Agent Assistant capabilities")
