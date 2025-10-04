"""
Script to run the Streamlit app after ensuring the environment is properly set up.
"""
import os
import sys
import subprocess
import importlib.util
import time

def check_dependencies():
    try:
        # Check numpy version
        import numpy
        print(f"NumPy version: {numpy.__version__}")
        
        # Downgrade numpy if version 2.x
        if numpy.__version__.startswith('2.'):
            print("Downgrading NumPy to 1.26.4...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "numpy==1.26.4", "--force-reinstall"])
            print("NumPy downgraded. Please restart the script.")
            sys.exit(0)
        
        # Check if streamlit is installed
        spec = importlib.util.find_spec("streamlit")
        if spec is None:
            print("Streamlit not found. Installing...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit"])
        else:
            print("Streamlit is installed.")
        
        # Check other critical dependencies - add our specific requirements
        for package in ["pandas", "python-dotenv", "beautifulsoup4", "pypdf", "langchain", "faiss-cpu", "requests"]:
            spec = importlib.util.find_spec(package.replace("-", "_"))
            if spec is None:
                print(f"{package} not found. Installing...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            else:
                print(f"{package} is installed.")
        
        return True
    except Exception as e:
        print(f"Error checking dependencies: {e}")
        return False

def run_app():
    """Run the Streamlit app"""
    if check_dependencies():
        print("Checking for data directories...")
        # Ensure the FAISS index directory exists
        index_dir = os.path.join(os.getcwd(), "data", "faiss_index")
        if not os.path.exists(index_dir):
            os.makedirs(index_dir, exist_ok=True)
            print(f"Created directory: {index_dir}")
        
        # Check for the AWS_index directory specifically
        aws_index_dir = os.path.join(index_dir, "AWS_index")
        if not os.path.exists(aws_index_dir):
            os.makedirs(aws_index_dir, exist_ok=True)
            print(f"Created AWS_index directory: {aws_index_dir}")
            
            # Create a simple metadata file
            with open(os.path.join(aws_index_dir, "index.meta"), "w", encoding="utf-8") as f:
                f.write("Created by: run_app.py\nDocument type: AWS Documentation\nDate: " + 
                       time.strftime("%Y-%m-%d %H:%M:%S"))
            
            # Create a simple content file
            with open(os.path.join(aws_index_dir, "aws_content.txt"), "w", encoding="utf-8") as f:
                f.write("AWS Documentation sample content.\nThis file was auto-generated.\n" +
                       "To add real content, use the Document Ingestion tab.")
        
        print("Running the app...")
        try:
            subprocess.call([
                sys.executable, "-m", "streamlit", "run", 
                "genai_dashboard_modular.py", "--server.port=9876"
            ])
        except Exception as e:
            print(f"Error running streamlit: {e}")
            print("Trying alternative method...")
            try:
                subprocess.call([
                    "streamlit", "run", "genai_dashboard_modular.py", 
                    "--server.port=9876"
                ])
            except Exception as e2:
                print(f"Alternative method also failed: {e2}")
    else:
        print("Failed to verify environment. App not started.")

if __name__ == "__main__":
    print("=" * 60)
    print("VaultMind GenAI Knowledge Assistant - Launcher")
    print("=" * 60)
    print("This script will check your environment and launch the application.")
    print("Your changes to the Query Assistant tab should be visible in the app.")
    print("=" * 60)
    
    run_app()
    
    print("\nApplication closed. Thank you for using VaultMind.")
    print("If you experienced any issues, please try running:")
    print("  C:\\Users\\bolaf\\anaconda3\\Scripts\\activate.bat genai_project2")
    print("  python -m streamlit run genai_dashboard_modular.py")
    print("=" * 60)
