"""
Demo Pre-flight Check
Validates that VaultMind is ready for demonstration
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("=" * 80)
print("VAULTMIND DEMO PRE-FLIGHT CHECK")
print("=" * 80)

checks_passed = 0
checks_total = 0

def check(name, condition, fix_hint=""):
    global checks_passed, checks_total
    checks_total += 1
    status = "✓ PASS" if condition else "✗ FAIL"
    print(f"\n[{status}] {name}")
    if not condition and fix_hint:
        print(f"    Fix: {fix_hint}")
    if condition:
        checks_passed += 1
    return condition

# 1. Python Version
import platform
python_version = platform.python_version()
check(
    f"Python Version: {python_version}",
    python_version >= "3.9",
    "Upgrade to Python 3.9 or higher"
)

# 2. Required Dependencies
print("\n" + "-" * 80)
print("CHECKING DEPENDENCIES")
print("-" * 80)

dependencies = [
    ("streamlit", "Streamlit"),
    ("dotenv", "python-dotenv"),
    ("langchain", "LangChain"),
    ("langgraph", "LangGraph"),
    ("sentence_transformers", "sentence-transformers"),
    ("faiss", "faiss-cpu"),
    ("weaviate", "weaviate-client"),
    ("pdfplumber", "pdfplumber"),
    ("pandas", "pandas"),
    ("plotly", "plotly"),
]

for module_name, package_name in dependencies:
    try:
        __import__(module_name)
        check(f"{package_name} installed", True)
    except ImportError:
        check(f"{package_name} installed", False, f"pip install {package_name}")

# 3. Environment Configuration
print("\n" + "-" * 80)
print("CHECKING CONFIGURATION")
print("-" * 80)

env_file = project_root / ".env"
check(
    ".env file exists",
    env_file.exists(),
    "Create .env file from .env.example"
)

if env_file.exists():
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv("OPENAI_API_KEY")
    check(
        "OPENAI_API_KEY configured",
        api_key and len(api_key) > 20,
        "Add OPENAI_API_KEY to .env file"
    )

# 4. Data Directories
print("\n" + "-" * 80)
print("CHECKING DATA DIRECTORIES")
print("-" * 80)

data_dir = project_root / "data"
faiss_dir = data_dir / "faiss_index"
logs_dir = project_root / "logs"

check("data/ directory exists", data_dir.exists(), "mkdir data")
check("data/faiss_index/ exists", faiss_dir.exists(), "mkdir data/faiss_index")
check("logs/ directory exists", logs_dir.exists(), "mkdir logs")

# 5. Sample Indexes
print("\n" + "-" * 80)
print("CHECKING INDEXES")
print("-" * 80)

if faiss_dir.exists():
    indexes = [d for d in faiss_dir.iterdir() if d.is_dir()]
    check(
        f"At least one index exists ({len(indexes)} found)",
        len(indexes) > 0,
        "Ingest a document via the '📄 Ingest Document' tab"
    )
    
    if indexes:
        # Check if indexes are loadable
        loadable = 0
        for idx_dir in indexes:
            if (idx_dir / "index.faiss").exists() and (idx_dir / "index.pkl").exists():
                loadable += 1
        
        check(
            f"Loadable indexes ({loadable}/{len(indexes)})",
            loadable > 0,
            "Re-ingest documents to create valid indexes"
        )

# 6. Hybrid System Components
print("\n" + "-" * 80)
print("CHECKING HYBRID SYSTEM")
print("-" * 80)

hybrid_files = [
    "utils/query_complexity_analyzer.py",
    "utils/hybrid_query_orchestrator.py",
    "utils/hybrid_agent_integration.py",
    "app/utils/langgraph_agent.py",
    "tabs/agent_assistant_hybrid.py",
]

for file_path in hybrid_files:
    full_path = project_root / file_path
    check(
        f"{file_path} exists",
        full_path.exists(),
        f"File missing: {file_path}"
    )

# 7. Test Hybrid System Initialization
print("\n" + "-" * 80)
print("TESTING HYBRID SYSTEM")
print("-" * 80)

try:
    from utils.hybrid_agent_integration import is_hybrid_system_available
    available = is_hybrid_system_available()
    check(
        "Hybrid system available",
        available,
        "Install: pip install langgraph sentence-transformers"
    )
except Exception as e:
    check(
        "Hybrid system available",
        False,
        f"Error: {str(e)}"
    )

# 8. Application Start Test
print("\n" + "-" * 80)
print("TESTING APPLICATION")
print("-" * 80)

try:
    # Try importing main dashboard
    import importlib.util
    spec = importlib.util.spec_from_file_location("dashboard", project_root / "genai_dashboard_modular.py")
    if spec and spec.loader:
        check("Dashboard module loadable", True)
    else:
        check("Dashboard module loadable", False, "Check genai_dashboard_modular.py for syntax errors")
except Exception as e:
    check("Dashboard module loadable", False, f"Error: {str(e)[:100]}")

# Summary
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

success_rate = (checks_passed / checks_total * 100) if checks_total > 0 else 0

print(f"\nPassed: {checks_passed}/{checks_total} ({success_rate:.1f}%)")

if success_rate == 100:
    print("\n🎉 ALL CHECKS PASSED! VaultMind is ready for demo!")
    print("\nTo start the demo:")
    print("  streamlit run genai_dashboard_modular.py")
    sys.exit(0)
elif success_rate >= 80:
    print("\n⚠️  MOSTLY READY - Fix remaining issues for best demo experience")
    sys.exit(1)
else:
    print("\n❌ NOT READY - Please fix the issues above before demo")
    sys.exit(1)
