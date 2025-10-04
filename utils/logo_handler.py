"""
VaultMind Logo Handler for Streamlit Dashboard
"""
import streamlit as st
import base64
from pathlib import Path

def get_logo_base64(logo_path: str) -> str:
    """Convert logo image to base64 string for embedding"""
    try:
        with open(logo_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except FileNotFoundError:
        st.warning(f"Logo file not found at {logo_path}")
        return None

def display_vaultmind_logo(logo_path: str = "assets/vaultmind_logo.png"):
    """Display VaultMind logo in the top right corner"""
    logo_base64 = get_logo_base64(logo_path)
    
    if logo_base64:
        st.markdown(f"""
        <div class="vaultmind-logo">
            <img src="data:image/png;base64,{logo_base64}" alt="VaultMind - AI Assistant for Secure Enterprise Knowledge" title="VaultMind">
        </div>
        """, unsafe_allow_html=True)
    else:
        # Fallback with text logo
        st.markdown("""
        <div class="vaultmind-logo" style="background: #22c55e; color: white; text-align: center; padding: 12px; font-weight: bold; font-size: 14px;">
            🔒🧠<br>VaultMind
        </div>
        """, unsafe_allow_html=True)

def create_logo_placeholder():
    """Create a simple SVG placeholder for VaultMind logo"""
    svg_logo = """
    <svg width="120" height="60" xmlns="http://www.w3.org/2000/svg">
        <rect width="120" height="60" fill="#22c55e" rx="8"/>
        <text x="60" y="25" font-family="Arial, sans-serif" font-size="12" font-weight="bold" text-anchor="middle" fill="white">🔒🧠</text>
        <text x="60" y="45" font-family="Arial, sans-serif" font-size="10" font-weight="bold" text-anchor="middle" fill="white">VaultMind</text>
    </svg>
    """
    return svg_logo
