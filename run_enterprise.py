#!/usr/bin/env python3
"""
VaultMind Enterprise Dashboard Launcher
Runs the modular dashboard with enterprise authentication
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Launch VaultMind with enterprise authentication"""
    
    # Get project root
    project_root = Path(__file__).resolve().parent
    
    # Change to project directory
    os.chdir(project_root)
    
    # Set environment variables
    os.environ['STREAMLIT_SERVER_PORT'] = '8501'
    os.environ['STREAMLIT_SERVER_ADDRESS'] = '0.0.0.0'
    
    print("🚀 Starting VaultMind Enterprise Dashboard...")
    print(f"📁 Project Root: {project_root}")
    print("🔐 Enterprise Authentication: ENABLED")
    print("🌐 Access URL: http://localhost:8501")
    print("-" * 50)
    
    try:
        # Run the modular dashboard with enterprise auth
        subprocess.run([
            sys.executable, 
            "-m", "streamlit", 
            "run", 
            "genai_dashboard_modular.py",
            "--server.port=8501",
            "--server.address=0.0.0.0"
        ], check=True)
    except KeyboardInterrupt:
        print("\n⏹️  VaultMind Enterprise Dashboard stopped")
    except Exception as e:
        print(f"❌ Error starting dashboard: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
