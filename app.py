# Entry file for Streamlit deployments (Streamlit Cloud / Hugging Face Spaces)
# Forces Demo Mode by default to ensure a zero-config experience in hosted environments.

import os

# Default Demo Mode ON for hosted environments; can be overridden in platform settings
os.environ.setdefault("DEMO_MODE", "true")

from enhanced_streamlit_app import main

if __name__ == "__main__":
    main()
