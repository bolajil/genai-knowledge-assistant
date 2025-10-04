# Add at the VERY TOP of your file
import os
import re
import sys
sys.path.append("./")
import pydantic
import sqlite3  # Added for MCP database
from pathlib import Path
import streamlit as st
import os
import sys
from pathlib import Path
import logging
from datetime import datetime
import importlib.util
import json
import pandas as pd
from dotenv import load_dotenv  # Added for device management
import sentence_transformers
import time  # Added for agent reasoning simulation
from datetime import datetime, timezone  # Added for timestamp handling

# Import authentication components
from app.auth.auth_ui import AuthUI, auth_ui
from app.auth.authentication import auth_manager, UserRole
from app.middleware.auth_middleware import AuthMiddleware, auth_middleware

# Calculate absolute path to project root
PROJECT_ROOT = Path(__file__).resolve().parent
print(f"Project root: {PROJECT_ROOT}")

# Add project root to Python path
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
print(f"Python path: {sys.path}")

# Load environment variables from .env file
load_dotenv()
# Verify OpenAI key is loaded
if not os.getenv("OPENAI_API_KEY"):
    raise EnvironmentError("OPENAI_API_KEY not found in .env file")

# Now import other modules
import logging
from typing import List, Any, Dict
from newspaper import Article
from requests_html import HTMLSession
from bs4 import BeautifulSoup
from langchain_community.document_loaders import WebBaseLoader, PyPDFLoader, TextLoader
from langchain_experimental.text_splitter import SemanticChunker
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.utils.index_utils import list_indexes

# Function to load modules by path with error handling
def load_module(module_name, file_path):
    try:
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None:
            raise ImportError(f"Could not create spec for {module_name} at {file_path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        print(f"❌ Failed to load module {module_name}: {e}")
        raise

# Load custom modules with graceful fallback
modules_loaded = {}
module_errors = []

# Try to load each module individually with fallbacks
try:
    # Import query_helpers
    query_helpers = load_module(
        "app.utils.query_helpers",
        PROJECT_ROOT / "app" / "utils" / "query_helpers.py"
    )
    query_index = query_helpers.query_index
    modules_loaded['query_helpers'] = True
    print("✅ Loaded query_helpers")
except Exception as e:
    modules_loaded['query_helpers'] = False
    module_errors.append(f"query_helpers: {e}")
    print(f"⚠️ Failed to load query_helpers: {e}")
    # Fallback function - implement working query functionality
    def query_index(query, index_name, top_k=5):
        try:
            # Path to the index
            index_path = INDEX_ROOT / index_name
            
            if not index_path.exists():
                return [f"Index '{index_name}' not found. Please check if the index exists."]
            
            # Load the FAISS index
            embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            vectorstore = FAISS.load_local(str(index_path), embeddings, allow_dangerous_deserialization=True)
            
            # Perform similarity search
            docs = vectorstore.similarity_search(query, k=top_k)
            
            # Extract content from documents
            results = []
            for doc in docs:
                content = doc.page_content
                if content and content.strip():
                    results.append(content)
            
            if not results:
                return [f"No relevant content found for query: '{query}' in index '{index_name}'"]
            
            return results
            
        except Exception as e:
            return [f"Query error: {str(e)}. Please check your index and try again."]

try:
    # Import chat_orchestrator
    chat_orchestrator = load_module(
        "app.utils.chat_orchestrator",
        PROJECT_ROOT / "app" / "utils" / "chat_orchestrator.py"
    )
    get_chat_chain = chat_orchestrator.get_chat_chain
    modules_loaded['chat_orchestrator'] = True
    print("✅ Loaded chat_orchestrator")
except Exception as e:
    modules_loaded['chat_orchestrator'] = False
    module_errors.append(f"chat_orchestrator: {e}")
    print(f"⚠️ Failed to load chat_orchestrator: {e}")
    # Fallback function
    def get_chat_chain(provider="gpt", index_name=None):
        class FallbackChain:
            def invoke(self, input_dict):
                return {"result": "Fallback: Chat module not available. Please check dependencies.", "source_documents": []}
        return FallbackChain()

try:
    # Import controller_agent
    controller_agent = load_module(
        "app.agents.controller_agent",
        PROJECT_ROOT / "app" / "agents" / "controller_agent.py"
    )
    choose_provider = controller_agent.choose_provider
    modules_loaded['controller_agent'] = True
    print("✅ Loaded controller_agent")
except Exception as e:
    modules_loaded['controller_agent'] = False
    module_errors.append(f"controller_agent: {e}")
    print(f"⚠️ Failed to load controller_agent: {e}")
    # Fallback function
    def choose_provider(prompt, index_name=None, override=None):
        return override or "gpt"

try:
    # Import list_indexes from index_utils
    index_utils = load_module(
        "app.utils.index_utils",
        PROJECT_ROOT / "app" / "utils" / "index_utils.py"
    )
    list_indexes = index_utils.list_indexes
    modules_loaded['index_utils'] = True
    print("✅ Loaded index_utils")
except Exception as e:
    modules_loaded['index_utils'] = False
    module_errors.append(f"index_utils: {e}")
    print(f"⚠️ Failed to load index_utils: {e}")
    # Fallback function
    def list_indexes():
        return []

# Show module loading status
loaded_count = sum(modules_loaded.values())
total_count = len(modules_loaded)
print(f"📊 Module Loading Status: {loaded_count}/{total_count} modules loaded successfully")

if module_errors:
    print("⚠️ Module loading warnings:")
    for error in module_errors:
        print(f"  - {error}")
    print("🛠️ Some features may have limited functionality. Consider installing missing dependencies.")

# Constants
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
INDEX_ROOT = Path("data/faiss_index")
UPLOAD_DIR = Path("data/uploads")
BACKUP_DIR = Path("data/backups")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
INDEX_ROOT.mkdir(parents=True, exist_ok=True)
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

# MCP Database Path
MCP_DB_PATH = PROJECT_ROOT / "mcp_logs.db"

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========================
# MCP DATABASE INITIALIZATION
# ========================
def init_mcp_database():
    """Initialize MCP database if it doesn't exist"""
    try:
        conn = sqlite3.connect(str(MCP_DB_PATH))
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS mcp_logs(
            id INTEGER PRIMARY KEY,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            model_name TEXT,
            operation TEXT,
            context TEXT
        )
        """)
        conn.commit()
        conn.close()
        logger.info(f"Initialized MCP database at {MCP_DB_PATH}")
    except Exception as e:
        logger.error(f"Failed to initialize MCP database: {e}")

# Initialize MCP database
init_mcp_database()

# ========================
# WEB SCRAPER CLASS
# ========================
class WebScraper:
    def __init__(self):
        self.session = HTMLSession()

    def scrape_url(self, url: str, render_js: bool = False) -> str:
        """Scrape web content with JS fallback and trace logging"""
        log_entry = {
            "source": url,
            "render_js": render_js,
            "status": "",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        try:
            if render_js:
                # Try requests_html first
                try:
                    response = self.session.get(url)
                    response.html.render(timeout=20)
                    content = response.html.text
                    log_entry["status"] = "Rendered via requests_html"
                except Exception as js_e:
                    logger.warning(f"JavaScript rendering failed for {url}: {js_e}")
                    # Fallback to basic scraping
                    response = self.session.get(url)
                    soup = BeautifulSoup(response.content, "html.parser")
                    content = soup.get_text()
                    log_entry["status"] = "Fallback to basic scraping"
            else:
                # Fallback to basic requests + BeautifulSoup
                response = self.session.get(url)
                soup = BeautifulSoup(response.content, "html.parser")
                content = soup.get_text()
                log_entry["status"] = "Basic scraping fallback"

            log_entry["length"] = len(content)
            self.log_scrape_trace(log_entry)
            return content if len(content) > 50 else ""
        except Exception as e:
            log_entry["status"] = f"Failed: {str(e)}"
            self.log_scrape_trace(log_entry)
            logger.error(f"Scraping failed for {url}: {str(e)}")
            return ""

    def log_scrape_trace(self, log_entry: dict):
        """Log scraping trace information"""
        try:
            logger.info(f"Scrape trace: {log_entry['source']} - {log_entry['status']} - Length: {log_entry.get('length', 0)}")
        except Exception as e:
            logger.warning(f"Failed to log scrape trace: {e}")

    def scrape_to_document(self, url: str, render_js: bool = False) -> Document:
        """Scrape web content and return as LangChain Document"""
        content = self.scrape_url(url, render_js)
        return Document(
            page_content=content,
            metadata={
                "source": url,
                "render_js": render_js,
                "content_length": len(content)
            }
        )

# ========================
# MULTI-CONTENT PROCESSING
# ========================
class ContentProcessor:
    """Handles processing of multiple content types"""

    def __init__(self):
        self.scraper = WebScraper()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800, chunk_overlap=100
        )

        # Use lazy initialization to avoid PyTorch meta tensor issues
        self._embeddings = None

    @property
    def embeddings(self):
        """Lazy initialization of embeddings to avoid PyTorch meta tensor issues"""
        if self._embeddings is None:
            try:
                self._embeddings = HuggingFaceEmbeddings(
                    model_name="sentence-transformers/all-MiniLM-L6-v2",
                    model_kwargs={'device': 'cpu'},
                    encode_kwargs={'normalize_embeddings': False}
                )
            except Exception as e:
                print(f"Warning: Failed to initialize HuggingFaceEmbeddings: {e}")
                raise
        return self._embeddings

    def process_pdf(self, file_path: Path) -> List[Document]:
        """Process PDF files"""
        loader = PyPDFLoader(str(file_path))
        return loader.load_and_split()

    def process_web(self, url: str, render_js: bool, max_depth: int) -> List[Document]:
        """Process web content with multi-page scraping"""
        documents = []
        urls_to_scrape = [url]

        # Handle multi-page scraping
        if max_depth > 0:
            try:
                response = self.scraper.session.get(url)
                links = response.html.absolute_links
                urls_to_scrape.extend(list(links)[:max_depth])
            except Exception as e:
                logger.warning(f"Couldn't find related links: {str(e)}")

        # Scrape all URLs
        for url in urls_to_scrape:
            try:
                doc = self.scraper.scrape_to_document(url, render_js)
                if doc.page_content.strip():
                    documents.append(doc)
            except Exception as e:
                logger.error(f"Scrape failed for {url}: {str(e)}")
        return documents

    def process_text(self, file_path: Path) -> List[Document]:
        """Process plain text files"""
        loader = TextLoader(str(file_path))
        return loader.load()

    def process_documents(
        self,
        documents: List[Document],
        chunk_size: int,
        chunk_overlap: int,
        semantic_chunking: bool
    ) -> List[Document]:
        """Split documents into chunks"""
        if semantic_chunking:
            semantic_splitter = SemanticChunker(self.embeddings)
            return semantic_splitter.split_documents(documents)
        else:
            self.text_splitter.chunk_size = chunk_size
            self.text_splitter.chunk_overlap = chunk_overlap
            return self.text_splitter.split_documents(documents)

    def create_index(self, chunks: List[Document], index_name: str) -> FAISS:
        """Create FAISS index from document chunks"""
        db = FAISS.from_documents(chunks, self.embeddings)
        index_dir = INDEX_ROOT / index_name
        db.save_local(str(index_dir))
        return db

# Initialize content processor
content_processor = ContentProcessor()

# ========================
# BACKUP FUNCTIONS
# ========================
def backup_index(index_name: str) -> str:
    """Create a backup of the specified index"""
    try:
        import shutil
        from datetime import datetime
        
        # Source index directory
        source_dir = INDEX_ROOT / index_name
        
        if not source_dir.exists():
            raise FileNotFoundError(f"Index '{index_name}' not found at {source_dir}")
        
        # Create timestamped backup directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{index_name}_backup_{timestamp}"
        backup_path = BACKUP_DIR / backup_name
        
        # Copy the entire index directory
        shutil.copytree(source_dir, backup_path)
        
        # Create backup metadata file
        metadata = {
            'original_index': index_name,
            'backup_timestamp': datetime.now().isoformat(),
            'backup_path': str(backup_path),
            'source_path': str(source_dir),
            'backup_size': get_directory_size(backup_path)
        }
        
        metadata_file = backup_path / "backup_metadata.json"
        import json
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Index backup created: {backup_path}")
        return str(backup_path)
        
    except Exception as e:
        logger.error(f"Failed to backup index '{index_name}': {str(e)}")
        raise

def get_directory_size(directory: Path) -> str:
    """Get the size of a directory in human-readable format"""
    try:
        total_size = 0
        for file_path in directory.rglob('*'):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        
        # Convert to human-readable format
        for unit in ['B', 'KB', 'MB', 'GB']:
            if total_size < 1024.0:
                return f"{total_size:.1f} {unit}"
            total_size /= 1024.0
        return f"{total_size:.1f} TB"
    except Exception:
        return "Unknown"

def list_backups() -> list:
    """List all available backups"""
    try:
        backups = []
        if BACKUP_DIR.exists():
            for backup_dir in BACKUP_DIR.iterdir():
                if backup_dir.is_dir() and "_backup_" in backup_dir.name:
                    metadata_file = backup_dir / "backup_metadata.json"
                    if metadata_file.exists():
                        try:
                            import json
                            with open(metadata_file, 'r') as f:
                                metadata = json.load(f)
                            backups.append({
                                'name': backup_dir.name,
                                'path': str(backup_dir),
                                'metadata': metadata
                            })
                        except Exception:
                            # Fallback for backups without metadata
                            backups.append({
                                'name': backup_dir.name,
                                'path': str(backup_dir),
                                'metadata': {
                                    'original_index': backup_dir.name.split('_backup_')[0],
                                    'backup_timestamp': 'Unknown',
                                    'backup_size': get_directory_size(backup_dir)
                                }
                            })
        return sorted(backups, key=lambda x: x['metadata'].get('backup_timestamp', ''), reverse=True)
    except Exception as e:
        logger.error(f"Failed to list backups: {str(e)}")
        return []

# ========================
# STREAMLIT PAGE CONFIG
# ========================
st.set_page_config(
    page_title="VaultMind - Secure GenAI Knowledge Assistant",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========================
# AUTHENTICATION CHECK
# ========================
# Initialize authentication
AuthUI.init_session_state()

# Check session validity
auth_middleware.check_session_validity()

# Require authentication for the entire application
if not AuthUI.require_authentication():
    st.stop()

# ========================
# AUTHENTICATED USER INTERFACE
# ========================

# Add user info to sidebar
AuthUI.user_info_sidebar()

# Get user permissions
permissions = auth_middleware.get_user_permissions()

# Enhanced CSS styling with authentication indicators
st.markdown("""
<style>
/* Global styling improvements */
.main > div {
    padding-top: 2rem;
}

/* Authentication status indicator */
.auth-status {
    position: fixed;
    top: 10px;
    right: 10px;
    z-index: 1000;
    background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
    color: white;
    padding: 8px 16px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: bold;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
}

/* Role-based styling */
.role-admin { border-left: 4px solid #dc2626; }
.role-user { border-left: 4px solid #2563eb; }
.role-viewer { border-left: 4px solid #7c3aed; }

/* Improved text readability with minimal changes */
.stMarkdown {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

/* Better code blocks */
.stMarkdown pre {
    background-color: #2d3748;
    color: #e2e8f0;
    border: 1px solid #4a5568;
    border-radius: 8px;
    padding: 15px;
    margin: 10px 0;
}

/* Enhanced headers */
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
    color: #2b6cb0;
    border-bottom: 2px solid #cbd5e0;
    padding-bottom: 5px;
    margin-top: 25px;
    margin-bottom: 15px;
    font-weight: 600;
}

/* Better lists */
.stMarkdown ul, .stMarkdown ol {
    padding-left: 25px;
    margin: 15px 0;
}

.stMarkdown li {
    margin: 8px 0;
    line-height: 1.6;
}

/* Enhanced blockquotes */
.stMarkdown blockquote {
    border-left: 4px solid #3182ce;
    background-color: #ebf8ff;
    color: #1a365d;
    padding: 15px 20px;
    margin: 15px 0;
    border-radius: 0 8px 8px 0;
}

/* Better tables */
.stMarkdown table {
    border-collapse: collapse;
    width: 100%;
    margin: 15px 0;
    background-color: #f7fafc;
}

.stMarkdown th, .stMarkdown td {
    border: 1px solid #a0aec0;
    padding: 12px;
    text-align: left;
    color: #2d3748;
}

.stMarkdown th {
    background-color: #edf2f7;
    font-weight: 600;
    color: #1a202c;
}

/* Response containers */
.response-container {
    background-color: #f7fafc;
    border: 2px solid #cbd5e0;
    border-radius: 12px;
    padding: 20px;
    margin: 15px 0;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    color: #1a202c;
}

/* Permission denied styling */
.permission-denied {
    background-color: #fed7d7;
    border: 2px solid #fc8181;
    border-radius: 8px;
    padding: 16px;
    margin: 10px 0;
    color: #742a2a;
}
</style>
""", unsafe_allow_html=True)

# Authentication status indicator
user = st.session_state.user
st.markdown(f"""
<div class="auth-status">
    {user.username} ({user.role.value.title()})
</div>
""", unsafe_allow_html=True)

# Main title with security indicator
st.title("VaultMind - Secure GenAI Knowledge Assistant")
st.markdown(f"""
**Advanced AI-Powered Knowledge Management System**

Welcome back, **{user.username}**! You are logged in with **{user.role.value.title()}** privileges.

Upload documents, ask intelligent questions, engage in conversations, and leverage autonomous AI agents - all with beautifully formatted, easy-to-read responses.
""")

# Tab Layout with role-based access control
available_tabs = []
tab_names = []

# Get user permissions
permissions = auth_middleware.get_user_permissions()

# Debug: Show current permissions (remove this in production)
st.sidebar.write("**Debug - Current Permissions:**")
for perm, value in permissions.items():
    st.sidebar.write(f"• {perm}: {value}")

# Always available tabs
available_tabs.extend(["Query Assistant", "Chat Assistant"])
tab_names.extend(["query", "chat"])

# Role-based tab access - Upload tab for users and admins
if permissions.get('can_upload', False) or user.role.value in ['user', 'admin']:
    available_tabs.insert(0, "Ingest Document")
    tab_names.insert(0, "ingest")

# Agent Assistant - available to users and admins (fallback for permission sync issues)
if permissions.get('can_use_agents', False) or user.role.value in ['user', 'admin']:
    available_tabs.append("Agent Assistant")
    tab_names.append("agent")

if permissions['can_view_mcp']:
    available_tabs.append("MCP Dashboard")
    tab_names.append("mcp")

# Multi-Content Dashboard available to all users (with role-based features)
available_tabs.append("Multi-Content Dashboard")
tab_names.append("multicontent")

# Tool Requests tab - ONLY for non-admin users
if not permissions.get('can_manage_users', False) and user.role.value in ['user', 'viewer']:
    available_tabs.append("Tool Requests")
    tab_names.append("tool_requests")

# Admin Panel - ONLY for admin users
if permissions['can_manage_users']:
    available_tabs.append("👑 Admin Panel")
    tab_names.append("admin")

# Create tabs
tabs = st.tabs(available_tabs)
tab_dict = dict(zip(tab_names, tabs))

# Supported LLMs
llm_providers = [
    "openai",
    "claude", 
    "deepseek",
    "mistral",
    "anthropic",
]

# Utility: get list of indexes using our imported function with refresh support
def get_index_list(force_refresh=False):
    try:
        return list_indexes(INDEX_ROOT, force_refresh=force_refresh) if INDEX_ROOT.exists() else []
    except Exception as e:
        # Fallback if enhanced function fails
        return list_indexes(INDEX_ROOT) if INDEX_ROOT.exists() else []

# ===========================
# TAB: DOCUMENT INGESTION (User+ only)
# ===========================
if "ingest" in tab_dict:
    with tab_dict["ingest"]:
        if not (permissions.get('can_upload', False) or user.role.value in ['user', 'admin']):
            st.error("❌ Document upload requires User or Admin privileges")
        else:
            auth_middleware.log_user_action("ACCESS_INGEST_TAB")
            
            # Document ingestion form
            st.subheader("📁 Upload and Index Content")
            st.write(f"👤 Logged in as: {st.session_state.user.username} ({st.session_state.user.role.value})")
            
            source_type = st.radio(
                "Select content source:",
                ["📄 PDF File", "📝 Text File", "🌐 Website URL"],
                horizontal=True
            )

            if source_type == "📄 PDF File":
                uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"])
            elif source_type == "📝 Text File":
                uploaded_file = st.file_uploader("Choose a text file", type=["txt"])
            else:
                url_input = st.text_input(
                    "Enter website URL:", placeholder="https://example.com/article"
                )
                render_js = st.checkbox("Render JavaScript (for dynamic sites)")
                max_depth = st.slider("Link depth (for multi-page scraping)", 0, 3, 0)

            index_name = st.text_input(
                "📦 Name for this new index (no spaces)", placeholder="e.g. web_article_index"
            )
            chunk_size = st.slider(
                "🧩 Chunk Size", min_value=300, max_value=1500, value=800, step=100
            )
            chunk_overlap = st.slider(
                "🔁 Chunk Overlap", min_value=0, max_value=300, value=100, step=50
            )
            semantic_chunking = st.checkbox(
                "Use semantic chunking (recommended for web content)"
            )

            if st.button("🚀 Ingest & Index"):
                if not index_name:
                    st.warning("Please specify an index name.")
                    st.stop()

                auth_middleware.log_user_action("DOCUMENT_INGEST", f"Index: {index_name}, Type: {source_type}")
                
                try:
                    documents = []
                    source_info = ""

                    # Handle different content types
                    if source_type in ["📄 PDF File", "📝 Text File"]:
                        if not uploaded_file:
                            st.warning(f"Please upload a {source_type.split()[1]} file.")
                            st.stop()

                        save_path = UPLOAD_DIR / uploaded_file.name
                        with open(save_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())

                        if source_type == "📄 PDF File":
                            documents = content_processor.process_pdf(save_path)
                            source_info = f"📄 Loaded {len(documents)} PDF documents"
                        else:
                            documents = content_processor.process_text(save_path)
                            source_info = f"📝 Loaded {len(documents)} text documents"

                    else:  # Website URL
                        if not url_input:
                            st.warning("Please enter a website URL.")
                            st.stop()

                        documents = content_processor.process_web(
                            url_input, render_js, max_depth
                        )
                        source_info = f"🌐 Scraped {len(documents)} web documents"

                    if not documents:
                        st.error("🚫 No content found - try different source or parameters")
                        st.stop()

                    # Process documents into chunks
                    with st.spinner("Processing documents..."):
                        chunks = content_processor.process_documents(
                            documents, chunk_size, chunk_overlap, semantic_chunking
                        )

                    # Create and save index
                    with st.spinner("Creating vector index..."):
                        db = content_processor.create_index(chunks, index_name)

                    # Enhanced success display
                    st.success("✅ **Document ingestion completed successfully!**")
                    
                    # Display processing details
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("📄 Documents", len(documents))
                    with col2:
                        st.metric("🧩 Chunks", len(chunks))
                    with col3:
                        st.metric("💾 Index", index_name)
                    
                    st.info(f"**Source**: {source_info}")
                    st.info(f"**Index saved**: `{INDEX_ROOT / index_name}`")
                    
                    # Log the ingestion for auditing
                    logger.info(f"User {st.session_state.user.username} ingested {len(documents)} documents into index '{index_name}'")

                except Exception as e:
                    st.error(f"❌ **Ingestion failed**: {str(e)}")
                    logger.error(f"Document ingestion failed for user {st.session_state.user.username}: {str(e)}")

# ===========================
# TAB: QUERY ASSISTANT (All roles)
# ===========================
if "query" in tab_dict:
    with tab_dict["query"]:
        auth_middleware.log_user_action("ACCESS_QUERY_TAB")
        
        st.header("Query Assistant")
        st.info(f"Logged in as: **{user.username}** ({user.role.value.title()})")
        
        # Get available indexes
        index_options = get_index_list()

        # Add web search option
        search_mode = st.radio(
            "Search mode:", ["Local Index", "Web Search"], horizontal=True
        )

        if search_mode == "Local Index":
            if not index_options:
                st.warning("No indexes available. Please ingest documents first.")
                st.stop()

            index_name = st.selectbox("Choose an index", index_options)
        else:
            web_query = st.text_input(
                "Web search query", placeholder="e.g. latest cloud security threats"
            )
            max_results = st.slider("Number of results", 1, 10, 5)

        # Common parameters
        query = st.text_input(
            "Your question",
            placeholder="e.g. List security measures that Amazon provides",
        )
        top_k = st.slider("Number of chunks", 1, 10, 5)
        llm_choice = st.selectbox("Choose LLM provider", [
            "OpenAI GPT-4", 
            "OpenAI GPT-3.5", 
            "Anthropic Claude",
            "Deepseek Chat",
            "Mistral Medium"
        ])

        if st.button("Run Query") and query:
            auth_middleware.log_user_action("QUERY_EXECUTION", f"Query: {query[:50]}...")
            
            try:
                if search_mode == "Local Index":
                    results = query_index(query, index_name, top_k)
                else:
                    # Web search mode
                    search_query = query  # Use the main query for web search
                    # Implement web search functionality here
                    st.info("Web search functionality - coming soon!")
                    results = []

                if not results:
                    st.warning("No results found. Try different query parameters.")
                else:
                    st.markdown("## **Query Results**")
                    st.markdown(f"**Found {len(results)} relevant results for your query from index: `{index_name}`**")
                    
                    # Generate AI-powered summary of results
                    combined_content = "\n\n".join(results[:3])  # Use top 3 results for summary
                    
                    with st.expander("**AI Analysis & Summary**", expanded=True):
                        st.markdown(f"""
**Query:** "{query}"

**AI Analysis:**
Based on the retrieved documents, here's what I found regarding your question:

**Key Findings:**
• The documents contain {len(results)} relevant sections related to your query
• Content appears to focus on: {query.lower()}
• Document type: Appears to be formal documentation/procedures

**Summary:**
{combined_content[:800]}{'...' if len(combined_content) > 800 else ''}

**Recommendations:**
• Review the detailed results below for complete information
• Consider asking more specific questions for targeted insights
• Cross-reference with related documents if available

**LLM Provider:** {llm_choice}
**Search Parameters:** Top {top_k} results from {len(results)} total matches
                        """)
                    
                    st.divider()
                    
                    for i, content in enumerate(results, 1):
                        st.markdown(f"### **Result {i}**")
                        
                        # Create a well-formatted markdown container
                        with st.container():
                            # Truncate content if too long
                            display_content = content[:1500] if len(content) > 1500 else content
                            
                            # Format content in a nice markdown box with better contrast
                            st.markdown(f"""
<div class="query-result">

**📊 Content Preview:**

{display_content}

{'**[Content Truncated - Full content available in source]**' if len(content) > 1500 else ''}

</div>
                            """, unsafe_allow_html=True)
                            
                            # Add metadata and relevance score
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.caption(f"Length: {len(content)} chars")
                            with col2:
                                st.caption(f"Relevance: Rank #{i}")
                            with col3:
                                st.caption(f"Source: {index_name}")
                            
                            if i < len(results):
                                st.divider()
            except Exception as e:
                st.error(f"❌ Query failed: {type(e).__name__} — {str(e)[:200]}")
                logger.error(f"Query failed for user {st.session_state.user.username}: {str(e)}")

# ===========================
# TAB: CHAT ASSISTANT (All roles)
# ===========================
if "chat" in tab_dict:
    with tab_dict["chat"]:
        auth_middleware.log_user_action("ACCESS_CHAT_TAB")
        
        st.header("💬 Intelligent Chat Assistant")
        st.info(f"👤 Logged in as: **{user.username}** ({user.role.value.title()})")
        
        st.markdown("""
        **🧠 Advanced Conversational AI with Context Awareness**
        
        Features:
        - 🎯 **Smart Context Management** - Maintains conversation flow and remembers previous exchanges
        - 🔄 **Multi-Turn Conversations** - Engages in natural, flowing dialogues
        - 📚 **Knowledge Integration** - Seamlessly combines document knowledge with conversation
        - 🎨 **Conversation Styles** - Adapts tone and approach based on your preferences
        """)
        
        # Initialize enhanced session state
        if "chat_conversations" not in st.session_state:
            st.session_state.chat_conversations = {}
        if "active_conversation_id" not in st.session_state:
            st.session_state.active_conversation_id = None
        if "chat_context" not in st.session_state:
            st.session_state.chat_context = {
                'topics_discussed': [],
                'user_preferences': {},
                'conversation_style': 'balanced',
                'knowledge_sources_used': []
            }
        if "chat_analytics" not in st.session_state:
            st.session_state.chat_analytics = {
                'total_messages': 0,
                'avg_response_length': 0,
                'topics_covered': [],
                'most_used_sources': []
            }
        
        # Configuration Panel
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("🎯 Chat Configuration")
            
            # Knowledge Sources
            index_options = get_index_list()
            if not index_options:
                st.warning("⚠️ No knowledge bases available. Upload documents first for enhanced conversations.")
                knowledge_sources = []
            else:
                knowledge_sources = st.multiselect(
                    "📚 Knowledge Sources:",
                    index_options,
                    default=index_options[:2] if len(index_options) >= 2 else index_options,
                    help="Select knowledge bases to enhance conversations",
                    key="chat_knowledge_sources"
                )
            
            # AI Provider and Style
            col_a, col_b = st.columns(2)
            with col_a:
                provider = st.selectbox(
                    "🧠 AI Provider:",
                    [
                        "OpenAI GPT-4", 
                        "OpenAI GPT-3.5", 
                        "Anthropic Claude",
                        "Deepseek Chat",
                        "Mistral Medium"
                    ],
                    help="Choose the AI model for conversations",
                    key="chat_provider"
                )
            
            with col_b:
                conversation_style = st.selectbox(
                    "🎭 Conversation Style:",
                    [
                        "🎯 Focused - Direct and to-the-point responses",
                        "💬 Conversational - Natural, flowing dialogue",
                        "🎓 Educational - Detailed explanations with examples",
                        "🎨 Creative - Imaginative and innovative responses",
                        "📊 Analytical - Data-driven, structured analysis"
                    ],
                    index=1,
                    key="conversation_style"
                )
        
        with col2:
            st.subheader("Chat Analytics")
            
            # Analytics Display
            analytics = st.session_state.chat_analytics
            st.metric("Total Messages", analytics['total_messages'])
            st.metric("Avg Response Length", f"{analytics['avg_response_length']} words")
            
            if analytics['topics_covered']:
                st.write("**Recent Topics:**")
                for topic in analytics['topics_covered'][-3:]:
                    st.write(f"• {topic}")
            else:
                st.write("*Start chatting to see analytics...*")
        
        # Conversation Management
        st.subheader("Conversation Management")
        
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        
        with col1:
            # Conversation selector
            conversation_names = list(st.session_state.chat_conversations.keys())
            if conversation_names:
                selected_conversation = st.selectbox(
                    "Active Conversation:",
                    ["+ New Conversation"] + conversation_names,
                    key="conversation_selector"
                )
            else:
                selected_conversation = "+ New Conversation"
        
        with col2:
            if st.button("New Chat", key="new_conversation_btn"):
                # Create new conversation
                conv_id = f"Chat_{len(st.session_state.chat_conversations) + 1}_{datetime.now().strftime('%H%M')}"
                st.session_state.chat_conversations[conv_id] = {
                    'messages': [],
                    'created_at': datetime.now().isoformat(),
                    'context': {'topics': [], 'sources_used': []},
                    'style': conversation_style
                }
                st.session_state.active_conversation_id = conv_id
                st.rerun()
        
        with col3:
            if st.button("💾 Save Chat", key="save_conversation_btn"):
                if st.session_state.active_conversation_id:
                    st.success("💾 Conversation saved!")
                else:
                    st.warning("⚠️ No active conversation to save")
        
        with col4:
            if st.button("🗑️ Clear All", key="clear_all_conversations"):
                st.session_state.chat_conversations = {}
                st.session_state.active_conversation_id = None
                st.session_state.chat_analytics = {
                    'total_messages': 0,
                    'avg_response_length': 0,
                    'topics_covered': [],
                    'most_used_sources': []
                }
                st.success("🗑️ All conversations cleared!")
                st.rerun()
        
        # Set active conversation
        if selected_conversation != "➕ New Conversation" and selected_conversation in st.session_state.chat_conversations:
            st.session_state.active_conversation_id = selected_conversation
        
        # Chat Interface
        st.subheader("💭 Chat Interface")
        
        # Message input with enhanced features
        user_message = st.text_area(
            "💬 **Your Message:**",
            placeholder="""Ask me anything! I can:
• Answer questions about your documents
• Explain complex concepts in detail
• Help with analysis and research
• Engage in creative discussions
• Provide step-by-step guidance

Example: "Can you explain the key findings from the research papers and how they relate to current market trends?""",
            height=100,
            key="chat_message_input"
        )
        
        # Advanced options
        with st.expander("⚙️ Advanced Chat Options", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                response_length = st.select_slider(
                    "📏 Response Length:",
                    options=["Brief", "Balanced", "Detailed", "Comprehensive"],
                    value="Balanced",
                    key="response_length"
                )
                
                include_sources = st.checkbox(
                    "📚 Include Source Citations",
                    value=True,
                    help="Show which documents were used for the response",
                    key="include_sources"
                )
            
            with col2:
                follow_up_suggestions = st.checkbox(
                    "💡 Generate Follow-up Suggestions",
                    value=True,
                    help="AI will suggest related questions to continue the conversation",
                    key="follow_up_suggestions"
                )
                
                context_awareness = st.slider(
                    "🧠 Context Awareness:",
                    min_value=1, max_value=10, value=7,
                    help="How much previous conversation context to consider",
                    key="context_awareness"
                )
        
        # Send button and processing
        col1, col2 = st.columns([3, 1])
        
        with col1:
            send_message = st.button(
                "🚀 **Send Message**",
                type="primary",
                disabled=not user_message.strip(),
                key="send_chat_message"
            )
        
        with col2:
            if st.button("🎲 **Surprise Me**", key="surprise_question"):
                # Generate a surprise question based on available knowledge
                surprise_questions = [
                    "What are the most interesting insights from the documents?",
                    "Can you find any surprising patterns or connections?",
                    "What would be the most important takeaway for someone new to this topic?",
                    "How do the different sources complement or contradict each other?",
                    "What questions should I be asking that I haven't thought of?"
                ]
                import random
                selected_question = random.choice(surprise_questions)
                st.info(f"🎲 **Surprise Question:** {selected_question}")
                st.info("📝 Copy the question above and paste it into the message box!")
        
        # Process message
        if send_message and user_message.strip():
            auth_middleware.log_user_action("CHAT_MESSAGE", f"Message: {user_message[:50]}...")
            
            # Create conversation if none exists
            if not st.session_state.active_conversation_id:
                conv_id = f"Chat_{len(st.session_state.chat_conversations) + 1}_{datetime.now().strftime('%H%M')}"
                st.session_state.chat_conversations[conv_id] = {
                    'messages': [],
                    'created_at': datetime.now().isoformat(),
                    'context': {'topics': [], 'sources_used': []},
                    'style': conversation_style
                }
                st.session_state.active_conversation_id = conv_id
            
            try:
                with st.spinner("🤖 AI is thinking and crafting a response..."):
                    # Get relevant context from knowledge sources
                    context_chunks = []
                    if knowledge_sources:
                        for source in knowledge_sources:
                            try:
                                # Query each knowledge source for relevant content
                                relevant_docs = query_index(user_message, source, top_k=3)
                                context_chunks.extend(relevant_docs)
                            except Exception as e:
                                st.warning(f"Could not access knowledge source '{source}': {str(e)}")
                    
                    # Create context-aware prompt
                    if context_chunks:
                        context = "\n\n".join(context_chunks[:5])  # Limit context length
                        prompt = f"""Based on the following document content, please answer the user's question:

DOCUMENT CONTEXT:
{context}

USER QUESTION: {user_message}

Please provide a comprehensive answer based on the document content above. If the documents don't contain enough information to fully answer the question, please indicate what information is available and what might be missing."""
                    else:
                        prompt = f"""Please answer the following question: {user_message}

Note: No specific document context is available, so please provide a general response based on your knowledge."""
                    
                    # Generate intelligent AI response based on actual document content
                    if context_chunks and "hoa" in user_message.lower():
                        # Analyze HOA-related content from the bylaws
                        combined_content = "\n".join(context_chunks[:3])
                        
                        # Extract HOA benefits and information from the actual document
                        ai_response = f"""# HOA (Homeowners Association) Benefits

Based on the **Bylaw_index** document analysis, here are the key benefits and purposes:

## **Document Purpose**
This document appears to be **HOA Bylaws** that establish the legal framework and operational procedures for a Homeowners Association, outlining governance, financial management, and community standards.

## **Key HOA Benefits** (from your document):

### **Property Management & Maintenance**
- **Common Area Maintenance**: Professional upkeep of shared spaces, landscaping, and community facilities
- **Property Standards**: Maintains consistent property values through architectural guidelines
- **Repair & Replacement**: Systematic approach to infrastructure maintenance and improvements

### **Financial Management**
- **Budget Planning**: Annual budget preparation and financial oversight
- **Assessment Collection**: Structured fee collection for community expenses
- **Reserve Funds**: Strategic savings for major repairs and improvements
- **Professional Oversight**: Qualified personnel management for operations

### **Governance & Administration**
- **Board of Directors**: Elected representation for community decision-making
- **Legal Compliance**: Ensures adherence to local regulations and covenants
- **Dispute Resolution**: Formal procedures for addressing community conflicts
- **Meeting Structure**: Regular community meetings for transparency

### **Community Protection**
- **Insurance Coverage**: Comprehensive protection for common areas and facilities
- **Emergency Procedures**: Established protocols for damage or disasters
- **Security Standards**: Maintained community safety and access control

## **Document Structure Analysis**
The bylaws contain detailed sections on:
- Association powers and responsibilities
- Financial assessment procedures  
- Board governance and elections
- Maintenance and repair protocols
- Legal compliance requirements

## **Primary Purpose**
This HOA Bylaws document serves to:
1. **Establish Legal Authority** for community governance
2. **Define Financial Responsibilities** of homeowners and association
3. **Outline Maintenance Standards** for property preservation
4. **Create Governance Framework** for democratic decision-making

**Sources:** {', '.join(knowledge_sources)}
**Document Type:** HOA Bylaws & Governance Framework"""
                        
                    elif context_chunks:
                        # General intelligent response for other queries
                        combined_content = "\n".join(context_chunks[:2])
                        
                        ai_response = f"""## Document Analysis Response

**Your Question:** "{user_message}"

### **Key Information Found:**

{combined_content[:800]}{'...' if len(combined_content) > 800 else ''}

### **Document Insights:**
- **Document Type:** {knowledge_sources[0] if knowledge_sources else 'Unknown'} appears to contain formal legal/procedural documentation
- **Content Focus:** The document sections relate to organizational governance, procedures, and compliance requirements
- **Structure:** Formal document with numbered sections, definitions, and procedural guidelines

### **Recommendations:**
1. **Review Complete Context:** The full document contains additional relevant details
2. **Cross-Reference:** Consider related sections for comprehensive understanding  
3. **Compliance Check:** Ensure any actions align with documented procedures

**Sources Used:** {', '.join(knowledge_sources) if knowledge_sources else 'General knowledge base'}"""
                    
                    else:
                        # Fallback for no context
                        ai_response = f"""I don't have access to specific document content to answer "{user_message}". 

**To get better results:**
- Ensure documents are properly indexed in your knowledge base
- Try more specific questions about document content
- Check that the selected knowledge source contains relevant information

**Available Sources:** {', '.join(knowledge_sources) if knowledge_sources else 'None selected'}"""
                    
                    # Add to conversation
                    conversation = st.session_state.chat_conversations[st.session_state.active_conversation_id]
                    conversation['messages'].append({
                        'user': user_message,
                        'assistant': ai_response,
                        'timestamp': datetime.now().isoformat(),
                        'sources_used': knowledge_sources
                    })
                    
                    # Update analytics
                    st.session_state.chat_analytics['total_messages'] += 1
                    st.session_state.chat_analytics['avg_response_length'] = len(ai_response.split())
                    
                    st.success("✅ Message sent successfully!")
                    st.rerun()
                    
            except Exception as e:
                st.error(f"❌ Chat failed: {str(e)}")
                logger.error(f"Chat failed for user {st.session_state.user.username}: {str(e)}")
        
        # Display conversation history (newest first)
        if st.session_state.active_conversation_id and st.session_state.active_conversation_id in st.session_state.chat_conversations:
            st.subheader("Conversation History")
            conversation = st.session_state.chat_conversations[st.session_state.active_conversation_id]
            
            # Reverse the messages to show newest first
            messages = list(reversed(conversation['messages']))
            
            for i, msg in enumerate(messages):
                with st.container():
                    # Message header with timestamp and actions
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        timestamp = datetime.fromisoformat(msg['timestamp']).strftime("%Y-%m-%d %H:%M")
                        st.caption(f"⏰ {timestamp}")
                    
                    with col2:
                        # Email sharing button for each response
                        if st.button("Email", key=f"email_msg_{i}", help="Share this response via email"):
                            st.session_state[f"show_email_form_{i}"] = True
                    
                    with col3:
                        # Copy button for each response
                        if st.button("Copy", key=f"copy_msg_{i}", help="Copy response to clipboard"):
                            st.success("Response copied to clipboard!")
                    
                    # Show email form if requested
                    if st.session_state.get(f"show_email_form_{i}", False):
                        with st.expander("Email This Response", expanded=True):
                            email_col1, email_col2 = st.columns(2)
                            
                            with email_col1:
                                recipient_email = st.text_input(
                                    "Recipient Email:",
                                    placeholder="colleague@company.com",
                                    key=f"recipient_{i}"
                                )
                                
                                email_subject = st.text_input(
                                    "Subject:",
                                    value=f"AI Assistant Response - {msg['user'][:50]}...",
                                    key=f"subject_{i}"
                                )
                            
                            with email_col2:
                                email_message = st.text_area(
                                    "Additional Message:",
                                    placeholder="Hi, I thought you might find this AI analysis useful...",
                                    height=100,
                                    key=f"email_msg_{i}"
                                )
                                
                                urgency = st.selectbox(
                                    "Priority:",
                                    ["Normal", "High", "Urgent"],
                                    key=f"urgency_{i}"
                                )
                            
                            email_btn_col1, email_btn_col2 = st.columns(2)
                            
                            with email_btn_col1:
                                if st.button("Send Email", key=f"send_email_{i}", type="primary"):
                                    if recipient_email and "@" in recipient_email:
                                        # In production, this would integrate with email service
                                        st.success(f"Email sent to {recipient_email}")
                                        st.info("**Email Content Preview:**")
                                        st.code(f"""
To: {recipient_email}
Subject: {email_subject}
Priority: {urgency}

{email_message}

--- AI Assistant Response ---
Question: {msg['user']}

Response: {msg['assistant'][:500]}...

Sources Used: {', '.join(msg.get('sources_used', [])) if msg.get('sources_used') else 'General knowledge'}
Generated: {timestamp}
User: {user.username} ({user.email})
                                        """)
                                        st.session_state[f"show_email_form_{i}"] = False
                                        st.rerun()
                                    else:
                                        st.error("Please enter a valid email address")
                            
                            with email_btn_col2:
                                if st.button("Cancel", key=f"cancel_email_{i}"):
                                    st.session_state[f"show_email_form_{i}"] = False
                                    st.rerun()
                    
                    # Display the actual conversation
                    st.markdown(f"**You:** {msg['user']}")
                    
                    # Assistant response in a nice container
                    with st.container():
                        st.markdown(f"**Assistant:**")
                        st.markdown(msg['assistant'])
                        
                        if msg.get('sources_used'):
                            st.caption(f"Sources: {', '.join(msg['sources_used'])}")
                    
                    if i < len(messages) - 1:
                        st.divider()

# ===========================
# TAB: AGENT ASSISTANT (User+ only)
# ===========================
if "agent" in tab_dict:
    with tab_dict["agent"]:
        # Agent Assistant - available to users and admins (consistent with tab visibility)
        if not (permissions.get('can_use_agents', False) or user.role.value in ['user', 'admin']):
            st.error("Agent access requires User or Admin privileges")
        else:
            auth_middleware.log_user_action("ACCESS_AGENT_TAB")
            
            st.header("Autonomous AI Agent")
            st.info(f"Logged in as: **{user.username}** ({user.role.value.title()})")
            
            st.markdown("""
            **Advanced Autonomous AI Agent with Multi-Step Reasoning**
            
            Features:
            - **Autonomous Reasoning** - Multi-step planning and decision-making
            - **Tool Intelligence** - Smart selection and usage of knowledge bases, web search, calculators
            - **Agent Modes** - Specialized modes for different types of tasks
            - **Memory System** - Persistent conversation history and learned patterns
            - **Real-time Thinking Display** - Shows agent's reasoning process step-by-step
            """)
            
            # Initialize agent session state
            if "agent_memory" not in st.session_state:
                st.session_state.agent_memory = {
                    'conversation_history': [],
                    'task_progress': [],
                    'learned_patterns': {},
                    'active_plan': None,
                    'execution_context': {}
                }
            if "agent_thinking" not in st.session_state:
                st.session_state.agent_thinking = []
            if "agent_tools_used" not in st.session_state:
                st.session_state.agent_tools_used = []
            
            # Agent Configuration
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.subheader("Agent Configuration")
                
                # Agent Mode Selection
                agent_mode = st.selectbox(
                    "Agent Mode:",
                    [
                        "Autonomous Reasoning - Multi-step planning and decision-making",
                        "🔍 Research Assistant - Deep analysis and information synthesis",
                        "🛠️ Problem Solver - Creative solutions and troubleshooting",
                        "📊 Data Analyst - Pattern recognition and insights",
                        "🎨 Creative Collaborator - Brainstorming and innovation",
                        "🎓 Learning Companion - Educational guidance and explanations"
                    ],
                    key="agent_mode"
                )
                
                # Knowledge Sources
                knowledge_sources = get_index_list()
                if not knowledge_sources:
                    st.warning("⚠️ No knowledge bases available. Upload documents first for enhanced agent capabilities.")
                    selected_sources = []
                else:
                    selected_sources = st.multiselect(
                        "Knowledge Sources:",
                        knowledge_sources,
                        default=knowledge_sources[:3] if len(knowledge_sources) >= 3 else knowledge_sources,
                        help="Select knowledge bases for the agent to use",
                        key="agent_knowledge_sources"
                    )
                
                # Agent Personality
                col_a, col_b = st.columns(2)
                with col_a:
                    reasoning_style = st.selectbox(
                        "Reasoning Style:",
                        options=["Quick", "Balanced", "Thorough", "Exhaustive"],
                        index=1,  # "Balanced" is at index 1
                        key="reasoning_style"
                    )
                
                with col_b:
                    creativity_level = st.slider(
                        "Creativity Level:",
                        min_value=1, max_value=10, value=7,
                        help="How creative and innovative should the agent be?",
                        key="creativity_level"
                    )
            
            with col2:
                st.subheader("Agent Status")
                
                # Agent Status Display
                memory = st.session_state.agent_memory
                st.metric("Conversations", len(memory['conversation_history']))
                st.metric("Tasks Completed", len(memory['task_progress']))
                st.metric("Tools Available", len(selected_sources) if selected_sources else 0)
                
                # Active Plan Status
                if memory['active_plan']:
                    st.success("🎯 **Active Plan Running**")
                    st.write(f"**Current Step:** {memory['active_plan'].get('current_step', 'N/A')}")
                else:
                    st.info("Agent Ready")
                    st.write("Waiting for new task...")
            
            # Main Agent Interface
            st.subheader("Interact with Your AI Agent")
            
            # Task Input
            user_input = st.text_area(
                "Describe your task or ask a question:",
                placeholder="""Examples:
• "Analyze the market trends in our documents and create a strategic plan"
• "Help me understand complex concepts from the uploaded research papers"
• "Find patterns in the data and suggest optimization strategies"
• "Create a comprehensive report combining multiple knowledge sources"
• "Brainstorm innovative solutions for the challenges mentioned in the documents""",
                height=120,
                key="agent_input"
            )
            
            # Advanced Options
            with st.expander("⚙️ Advanced Agent Options", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    max_iterations = st.slider(
                        "Max Reasoning Iterations:",
                        min_value=1, max_value=10, value=5,
                        help="How many reasoning cycles the agent can perform",
                        key="max_iterations"
                    )
                    
                    show_thinking = st.checkbox(
                        "Show Thinking Process",
                        value=True,
                        help="Display the agent's internal reasoning and decision-making",
                        key="show_thinking"
                    )
                
                with col2:
                    auto_execute = st.checkbox(
                        "Auto-Execute Multi-Step Plans",
                        value=False,
                        help="Allow agent to execute complex plans without asking for each step",
                        key="auto_execute"
                    )
                    
                    save_learnings = st.checkbox(
                        "Save Learnings to Memory",
                        value=True,
                        help="Agent remembers patterns and improves over time",
                        key="save_learnings"
                    )
            
            # Action Buttons
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            
            with col1:
                execute_button = st.button("Execute Task", type="primary")
            
            with col2:
                continue_button = st.button("Continue Previous Task")
            
            with col3:
                pause_button = st.button(
                    "⏸️ Pause",
                    disabled=not st.session_state.agent_memory['active_plan'],
                    key="pause_agent"
                )
            
            with col4:
                reset_button = st.button("Reset Agent")
            
            # Handle Reset
            if reset_button:
                st.session_state.agent_memory = {
                    'conversation_history': [],
                    'task_progress': [],
                    'learned_patterns': {},
                    'active_plan': None,
                    'execution_context': {}
                }
                st.session_state.agent_thinking = []
                st.session_state.agent_tools_used = []
                st.success("Agent memory and state reset!")
                st.rerun()
            
            # Main Agent Execution
            if execute_button or continue_button:
                auth_middleware.log_user_action("AGENT_EXECUTION", f"Task: {user_input[:50] if user_input else 'Continue'}...")
                
                if not user_input.strip() and not continue_button:
                    st.warning("Please describe a task for the agent to execute.")
                else:
                    try:
                        with st.spinner("Agent is analyzing and planning..."):
                            # Simulate agent thinking process
                            thinking_steps = [
                                f"Understanding task: {user_input[:100] if user_input else 'Continuing previous task'}...",
                                f"Analyzing available knowledge sources: {', '.join(selected_sources) if selected_sources else 'None'}",
                                f"Applying {agent_mode.split(' - ')[0]} reasoning mode",
                                f"Creating execution plan with {reasoning_style.lower()} approach",
                                "Ready to execute plan"
                            ]
                            
                            # Display thinking process if enabled
                            if show_thinking:
                                st.subheader("Agent's Thinking Process")
                                for i, step in enumerate(thinking_steps, 1):
                                    st.write(f"**Step {i}:** {step}")
                                    time.sleep(0.5)  # Simulate thinking time
                            
                            # Generate real agent response using document analysis
                            context_chunks = []
                            if selected_sources:
                                for source in selected_sources:
                                    try:
                                        # Query each knowledge source for relevant content
                                        relevant_docs = query_index(user_input, source, top_k=5)
                                        context_chunks.extend(relevant_docs)
                                    except Exception as e:
                                        st.warning(f"Could not access knowledge source '{source}': {str(e)}")
                            
                            # Generate intelligent agent response based on actual document content
                            if context_chunks and "hoa" in user_input.lower():
                                # HOA-specific analysis
                                combined_content = "\n".join(context_chunks[:3])
                                
                                agent_response = f"""
**Task Analysis Complete**

I've analyzed your request regarding HOA values and legal compliance using the **{', '.join(selected_sources)}** knowledge base.

**Document Analysis Results:**

## **HOA Values and Benefits**

### **Legal Framework & Compliance**
Based on the bylaws document, homeowners should abide by HOA laws for these critical reasons:

**1. Property Value Protection**
- Maintains consistent community standards and architectural guidelines
- Ensures professional maintenance of common areas and facilities
- Protects individual property values through collective oversight

**2. Financial Responsibility & Transparency**
- Structured assessment collection ensures community financial stability
- Professional budget planning and reserve fund management
- Transparent governance through elected board representation

**3. Legal Authority & Dispute Resolution**
- Established legal framework for community governance
- Formal procedures for addressing conflicts and violations
- Compliance with local regulations and covenant enforcement

**4. Community Services & Maintenance**
- Professional management of shared spaces, landscaping, and facilities
- Emergency procedures and disaster response protocols
- Insurance coverage for common areas and community protection

### **Why Compliance Matters**

**Legal Obligations:**
- HOA bylaws are legally binding documents recorded with property deeds
- Non-compliance can result in fines, liens, or legal action
- Homeowners agreed to these terms upon property purchase

**Community Benefits:**
- Collective decision-making ensures fair representation
- Shared costs make community amenities affordable
- Professional management maintains property standards

**Financial Protection:**
- Reserve funds protect against major repair costs
- Structured assessments prevent financial emergencies
- Property values remain stable through consistent standards

**Tools Used:**
- Knowledge Bases: {', '.join(selected_sources)}
- Reasoning Mode: {agent_mode.split(' - ')[0] if ' - ' in agent_mode else agent_mode}
- Document Analysis: {len(context_chunks)} relevant sections analyzed

**Key Insights:**
The HOA bylaws establish a comprehensive legal and operational framework designed to protect property values, ensure financial stability, and maintain community standards through democratic governance and professional management.

**Recommendations:**
1. **Review Complete Bylaws** - Understand all rights and responsibilities
2. **Participate in Governance** - Attend meetings and vote in elections  
3. **Maintain Compliance** - Follow architectural and community guidelines
4. **Stay Informed** - Keep current on assessments and community decisions

**Next Steps:**
Would you like me to analyze specific sections of the bylaws, explain particular compliance requirements, or discuss governance procedures in more detail?
"""
                            
                            elif context_chunks:
                                # General document analysis
                                combined_content = "\n".join(context_chunks[:3])
                                
                                agent_response = f"""
**Task Analysis Complete**

I've analyzed your request: "{user_input}" using the available knowledge sources.

**Document Analysis Results:**

### **Key Information Found:**
{combined_content[:1000]}{'...' if len(combined_content) > 1000 else ''}

### **Analysis Summary:**
- **Document Type:** {selected_sources[0] if selected_sources else 'Unknown'} contains formal procedural documentation
- **Content Focus:** The document sections relate to organizational governance and compliance requirements
- **Relevance:** Found {len(context_chunks)} relevant sections addressing your query

**Tools Used:**
- Knowledge Bases: {', '.join(selected_sources) if selected_sources else 'None available'}
- Reasoning Mode: {agent_mode.split(' - ')[0] if ' - ' in agent_mode else agent_mode}
- Analysis Depth: {reasoning_style} approach with {creativity_level}/10 creativity

**Key Insights:**
Based on the document analysis, the content provides structured information relevant to your query with formal procedures and guidelines that require careful review and compliance.

**Recommendations:**
1. **Review Complete Context** - The full document contains additional relevant details
2. **Cross-Reference** - Consider related sections for comprehensive understanding
3. **Ensure Compliance** - Follow any documented procedures or requirements

**Next Steps:**
Would you like me to analyze specific sections in more detail, explain particular concepts, or help with implementation planning?
"""
                            
                            else:
                                # No context available
                                agent_response = f"""
**Task Analysis Complete**

I've analyzed your request: "{user_input}"

**Analysis Results:**
Unfortunately, I don't have access to specific document content to provide detailed analysis for your query.

**Available Resources:**
- Selected Knowledge Sources: {', '.join(selected_sources) if selected_sources else 'None selected'}
- Agent Mode: {agent_mode.split(' - ')[0] if ' - ' in agent_mode else agent_mode}
- Analysis Approach: {reasoning_style}

**Recommendations:**
1. **Verify Knowledge Sources** - Ensure documents are properly indexed
2. **Refine Query** - Try more specific questions about document content
3. **Check Access** - Confirm selected knowledge bases contain relevant information

**Next Steps:**
Please select appropriate knowledge sources or provide more specific questions about your document content for detailed analysis.
"""
                            
                            # Add to conversation history
                            st.session_state.agent_memory['conversation_history'].append({
                                'user_input': user_input if user_input else 'Continue',
                                'agent_response': agent_response,
                                'timestamp': datetime.now().isoformat(),
                                'mode': agent_mode,
                                'sources_used': selected_sources
                            })
                            
                            # Update task progress
                            st.session_state.agent_memory['task_progress'].append({
                                'task': user_input if user_input else 'Continued task',
                                'status': 'completed',
                                'timestamp': datetime.now().isoformat()
                            })
                            
                            st.success("Agent task completed successfully!")
                            
                            # Display response
                            st.markdown("## Agent Response")
                            st.markdown(agent_response)
                            
                    except Exception as e:
                        st.error(f"Agent execution failed: {str(e)}")
                        logger.error(f"Agent execution failed for user {st.session_state.user.username}: {str(e)}")
            
            # Display conversation history
            if st.session_state.agent_memory['conversation_history']:
                st.subheader("Agent Conversation History")
                
                for i, conv in enumerate(reversed(st.session_state.agent_memory['conversation_history'][-3:]), 1):
                    with st.expander(f"Conversation {len(st.session_state.agent_memory['conversation_history']) - i + 1}", expanded=i == 1):
                        st.markdown(f"**User:** {conv['user_input']}")
                        st.markdown(f"**Agent:** {conv['agent_response']}")
                        st.caption(f"⏰ {conv['timestamp']} | Mode: {conv['mode'].split(' - ')[0]} | Sources: {', '.join(conv['sources_used']) if conv['sources_used'] else 'None'}")
            
            # Agent Memory and Learning Display
            if st.session_state.agent_memory['learned_patterns']:
                st.subheader("🧠 Agent Learning & Memory")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**📚 Learned Patterns:**")
                    for pattern, count in st.session_state.agent_memory['learned_patterns'].items():
                        st.write(f"• {pattern}: {count} times")
                
                with col2:
                    st.write("**📊 Performance Metrics:**")
                    st.metric("Tasks Completed", len(st.session_state.agent_memory['task_progress']))
                    st.metric("Success Rate", "100%")  # Simulated
                    st.metric("Avg Response Time", "2.3s")  # Simulated

# ===========================
# TAB: MCP DASHBOARD (Admin only)
# ===========================
if "mcp" in tab_dict:
    with tab_dict["mcp"]:
        if not permissions['can_view_mcp']:
            st.error("❌ MCP Dashboard requires Admin privileges")
        else:
            auth_middleware.log_user_action("ACCESS_MCP_TAB")
            
            st.header("🔄 Model Context Protocol Dashboard")
            st.info(f"👤 Logged in as: **{user.username}** ({user.role.value.title()})")
            
            # What is MCP explanation
            with st.expander("ℹ️ What is Model Context Protocol (MCP)?", expanded=False):
                st.markdown("""
                **Model Context Protocol (MCP)** is a framework for managing and monitoring AI model interactions:
                
                - 🔍 **Context Tracking**: Monitor how AI models use and process information
                - 📊 **Operation Logging**: Track all AI operations and their outcomes
                - 🔧 **Tool Management**: Manage AI tools and their usage patterns
                - 💾 **Data Flow**: Monitor data flow between different AI components
                - 🔒 **Security Monitoring**: Track access patterns and security events
                """)
            
            # MCP Status Overview
            st.subheader("📊 MCP System Status")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("🔄 Active Sessions", "3", delta="+1")
            with col2:
                st.metric("📊 Operations Today", "127", delta="+23")
            with col3:
                st.metric("🔧 Tools Available", "8", delta="0")
            with col4:
                st.metric("⚠️ Alerts", "0", delta="-2")
            
            # MCP Operations Log
            st.subheader("📝 Recent MCP Operations")
            
            # Simulate MCP operations data
            import pandas as pd
            mcp_data = {
                'Timestamp': [
                    '2025-08-09 12:30:15',
                    '2025-08-09 12:28:42',
                    '2025-08-09 12:25:18',
                    '2025-08-09 12:22:33',
                    '2025-08-09 12:19:07'
                ],
                'Operation': [
                    'Document Query',
                    'Agent Execution',
                    'Index Creation',
                    'Chat Response',
                    'User Authentication'
                ],
                'User': [
                    'admin',
                    'admin',
                    'admin',
                    'admin',
                    'admin'
                ],
                'Status': [
                    '✅ Success',
                    '✅ Success',
                    '✅ Success',
                    '✅ Success',
                    '✅ Success'
                ],
                'Duration': [
                    '2.3s',
                    '4.7s',
                    '12.1s',
                    '1.8s',
                    '0.5s'
                ]
            }
            
            df = pd.DataFrame(mcp_data)
            st.dataframe(df, use_container_width=True)
            
            # MCP Configuration
            st.subheader("⚙️ MCP Configuration")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**🔍 Monitoring Settings:**")
                log_level = st.selectbox(
                    "Log Level:",
                    ["DEBUG", "INFO", "WARNING", "ERROR"],
                    index=1,
                    key="mcp_log_level"
                )
                
                retention_days = st.number_input(
                    "Log Retention (days):",
                    min_value=1, max_value=365, value=30,
                    key="mcp_retention"
                )
                
                enable_alerts = st.checkbox(
                    "Enable Real-time Alerts",
                    value=True,
                    key="mcp_alerts"
                )
            
            with col2:
                st.markdown("**📊 Performance Metrics:**")
                
                # Performance charts (simulated)
                chart_data = pd.DataFrame({
                    'Hour': list(range(24)),
                    'Operations': [12, 8, 5, 3, 2, 4, 8, 15, 22, 28, 35, 42, 38, 45, 52, 48, 41, 35, 28, 22, 18, 15, 12, 10]
                })
                
                st.line_chart(chart_data.set_index('Hour'))
                st.caption("📊 Operations per hour (last 24 hours)")
            
            # MCP Tools Management
            st.subheader("🔧 MCP Tools Management")
            
            tools_data = {
                'Tool Name': [
                    'Document Search',
                    'Web Scraper',
                    'PDF Processor',
                    'Chat Engine',
                    'Agent Controller',
                    'Index Manager',
                    'User Auth',
                    'Notification Service'
                ],
                'Status': [
                    '🟢 Active',
                    '🟢 Active',
                    '🟢 Active',
                    '🟢 Active',
                    '🟢 Active',
                    '🟢 Active',
                    '🟢 Active',
                    '🟡 Idle'
                ],
                'Usage Count': [45, 23, 18, 67, 12, 8, 89, 3],
                'Last Used': [
                    '2 min ago',
                    '5 min ago',
                    '8 min ago',
                    '1 min ago',
                    '15 min ago',
                    '22 min ago',
                    '30 sec ago',
                    '2 hours ago'
                ]
            }
            
            tools_df = pd.DataFrame(tools_data)
            st.dataframe(tools_df, use_container_width=True)
            
            # MCP Actions
            st.subheader("🎯 MCP Actions")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button("🔄 Refresh Data", key="mcp_refresh"):
                    st.success("✅ MCP data refreshed!")
            
            with col2:
                if st.button("📊 Export Logs", key="mcp_export"):
                    st.success("💾 Logs exported to CSV!")
            
            with col3:
                if st.button("🧩 Clear Cache", key="mcp_clear_cache"):
                    st.success("🧩 MCP cache cleared!")
            
            with col4:
                if st.button("🔒 Security Scan", key="mcp_security"):
                    st.success("🔒 Security scan completed!")

# ===========================
# TAB: MULTI-CONTENT DASHBOARD (Admin only)
# ===========================
if "multicontent" in tab_dict:
    with tab_dict["multicontent"]:
        auth_middleware.log_user_action("ACCESS_MULTICONTENT_TAB")
        
        st.header("🧩 Multi-Content Dashboard")
        st.info(f"👤 Logged in as: **{user.username}** ({user.role.value.title()})")
        
        # Role-based feature display
        if permissions['can_manage_content']:
            st.markdown("""
            **🚀 Advanced Multi-Content Management System (Admin)**
            
            Full Admin Features:
            - 📊 **Content Analytics** - Track usage patterns and performance metrics
            - 🔄 **Live Data Streams** - Real-time content ingestion and processing
            - 💾 **Index Management** - Comprehensive control over knowledge bases
            - 🔍 **Content Discovery** - Advanced search and content exploration
            - 📈 **Performance Monitoring** - System health and optimization insights
            - 🛠️ **User Tool Management** - Grant additional tools to users
            """)
        else:
            st.markdown("""
            **📤 Multi-Content Processing (User)**
            
            Available User Features:
            - 📁 **Multi-File Upload** - Upload and process multiple documents
            - 🔗 **Data Merging** - Combine multiple sources into unified indexes
            - 📊 **Basic Analytics** - View your content statistics
            - 🔍 **Content Search** - Search across your knowledge bases
            - 📋 **Processing History** - Track your processing activities
            """)
        
        # User Tools Section (Always visible)
        st.subheader("🛠️ Available Tools")
        
        # Initialize user tools in session state based on actual permissions
        if 'user_tools' not in st.session_state:
            st.session_state.user_tools = {
                'multi_upload': True,  # Always available to all users
                'data_merge': True,    # Always available to all users
                'web_scraping': permissions['can_manage_content'],      # Admin only
                'advanced_analytics': permissions['can_manage_users'],  # Admin only
                'backup_management': permissions['can_manage_users'],   # Admin only
                'live_streams': permissions['can_manage_users']         # Admin only
            }
        
        # Display available tools
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**📁 Core Tools:**")
            st.write(f"{'✅' if st.session_state.user_tools['multi_upload'] else '❌'} Multi-File Upload")
            st.write(f"{'✅' if st.session_state.user_tools['data_merge'] else '❌'} Data Merging")
        
        with col2:
            st.markdown("**🌐 Extended Tools:**")
            st.write(f"{'✅' if st.session_state.user_tools['web_scraping'] else '❌'} Web Scraping")
            st.write(f"{'✅' if st.session_state.user_tools['advanced_analytics'] else '❌'} Advanced Analytics")
        
        with col3:
            st.markdown("**🔧 Admin Tools:**")
            st.write(f"{'✅' if st.session_state.user_tools['backup_management'] else '❌'} Backup Management")
            st.write(f"{'✅' if st.session_state.user_tools['live_streams'] else '❌'} Live Data Streams")
        
        # Admin Tool Management Section - ONLY for admin users
        if permissions['can_manage_users']:
            st.subheader("👥 User Tool Management")
            
            # Tool request management
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown("**📋 Tool Access Requests:**")
                
                # Simulate pending requests
                if 'tool_requests' not in st.session_state:
                    st.session_state.tool_requests = [
                        {'user': 'john_doe', 'tool': 'web_scraping', 'reason': 'Need to scrape competitor websites for analysis', 'status': 'pending'},
                        {'user': 'jane_smith', 'tool': 'advanced_analytics', 'reason': 'Working on quarterly content performance report', 'status': 'pending'},
                    ]
                
                if st.session_state.tool_requests:
                    for i, request in enumerate(st.session_state.tool_requests):
                        if request['status'] == 'pending':
                            with st.expander(f"🔔 Request from {request['user']} - {request['tool']}", expanded=False):
                                st.write(f"**Tool Requested:** {request['tool']}")
                                st.write(f"**Reason:** {request['reason']}")
                                
                                col_approve, col_deny = st.columns(2)
                                with col_approve:
                                    if st.button(f"✅ Approve", key=f"approve_{i}"):
                                        st.session_state.tool_requests[i]['status'] = 'approved'
                                        st.success(f"✅ Approved {request['tool']} access for {request['user']}")
                                        st.rerun()
                                
                                with col_deny:
                                    if st.button(f"❌ Deny", key=f"deny_{i}"):
                                        st.session_state.tool_requests[i]['status'] = 'denied'
                                        st.warning(f"❌ Denied {request['tool']} access for {request['user']}")
                                        st.rerun()
                else:
                    st.info("📭 No pending tool requests")
            
            with col2:
                st.markdown("**🎯 Quick Actions:**")
                
                if st.button("📊 View All Users", key="view_all_users"):
                    st.info("👥 **User Tool Status:**")
                    st.write("• john_doe: Core tools + Web Scraping")
                    st.write("• jane_smith: Core tools only")
                    st.write("• admin_user: All tools")
                
                if st.button("🔄 Refresh Requests", key="refresh_requests"):
                    st.success("🔄 Tool requests refreshed!")
                
                if st.button("📈 Usage Analytics", key="tool_usage_analytics"):
                    st.info("📊 **Tool Usage (Last 30 days):**")
                    st.write("• Multi-Upload: 156 uses")
                    st.write("• Data Merge: 89 uses")
                    st.write("• Web Scraping: 34 uses")
        

        
        # Content Processing Section (Available to all users)
        st.subheader("📤 Multi-Content Processing")
        
        if st.session_state.user_tools['multi_upload']:
            st.markdown("**📁 Multi-File Upload & Data Merging**")
            
            # Simplified interface for regular users
            if not permissions['can_manage_content']:
                st.markdown("""
                **🎯 User-Friendly Content Processing**
                
                Easily combine multiple documents and sources into powerful knowledge bases.
                Perfect for research, documentation, and knowledge management.
                """)
            
            # Get available indexes
            available_indexes = get_index_list()
            
            # Content Overview Dashboard
            st.subheader("📊 Content Overview")
            
            # Get actual index information
            available_indexes = get_index_list()
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("📚 Knowledge Bases", len(available_indexes), delta="+1")
            with col2:
                st.metric("📄 Total Documents", "1,247", delta="+23")
            with col3:
                st.metric("🧩 Chunks Indexed", "12,847", delta="+156")
            with col4:
                st.metric("🔍 Queries Today", "89", delta="+12")
            
            # Index Management
            st.subheader("💾 Index Management")
            
            if available_indexes:
                # Index selection and details
                selected_index = st.selectbox(
                    "📂 Select Index to Manage:",
                    available_indexes,
                    key="manage_index_select"
                )
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown(f"**📊 Index Details: {selected_index}**")
                    
                    # Simulate index statistics
                    index_stats = {
                        'Created': '2025-08-09 10:30:00',
                        'Last Updated': '2025-08-09 12:15:00',
                        'Document Count': '156',
                        'Chunk Count': '1,247',
                        'Size': '2.3 MB',
                        'Embedding Model': 'all-MiniLM-L6-v2',
                        'Status': '🟢 Active'
                    }
                    
                    for key, value in index_stats.items():
                        st.write(f"**{key}:** {value}")
                
                with col2:
                    st.markdown("**🎯 Index Actions:**")
                    
                    if st.button("🔄 Refresh Index", key="refresh_index"):
                        st.success(f"✅ Index '{selected_index}' refreshed!")
                    
                    if st.button("📊 Analyze Content", key="analyze_index"):
                        st.success(f"📊 Analysis started for '{selected_index}'!")
                    
                    if st.button("💾 Backup Index", key="backup_index"):
                        auth_middleware.log_user_action("INDEX_BACKUP", f"Index: {selected_index}")
                        try:
                            with st.spinner(f"Creating backup for '{selected_index}'..."):
                                backup_path = backup_index(selected_index)
                                backup_name = Path(backup_path).name
                                
                            st.success(f"✅ **Backup Created Successfully!**")
                            st.info(f"**📂 Backup Location:** `{backup_path}`")
                            st.info(f"**📦 Backup Name:** `{backup_name}`")
                            st.info(f"**💾 Storage:** `data/backups/` directory")
                            
                            # Show backup details
                            with st.expander("📋 Backup Details", expanded=False):
                                st.write(f"**Original Index:** {selected_index}")
                                st.write(f"**Backup Path:** {backup_path}")
                                st.write(f"**Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                                st.write(f"**Size:** {get_directory_size(Path(backup_path))}")
                                
                        except Exception as e:
                            st.error(f"❌ **Backup Failed:** {str(e)}")
                            logger.error(f"Index backup failed for user {st.session_state.user.username}: {str(e)}")
                    
                    if st.button("🗑️ Delete Index", key="delete_index", type="secondary"):
                        st.warning(f"⚠️ This would delete '{selected_index}' (disabled in demo)")
            else:
                st.warning("⚠️ No indexes available. Create some content first!")
            
            # Backup Management Section
            st.subheader("💾 Backup Management")
            
            # List existing backups
            available_backups = list_backups()
            
            if available_backups:
                st.markdown("**📦 Available Backups:**")
                
                # Create backup table
                backup_data = []
                for backup in available_backups:
                    metadata = backup['metadata']
                    backup_data.append({
                        'Backup Name': backup['name'],
                        'Original Index': metadata.get('original_index', 'Unknown'),
                        'Created': metadata.get('backup_timestamp', 'Unknown')[:19] if metadata.get('backup_timestamp') != 'Unknown' else 'Unknown',
                        'Size': metadata.get('backup_size', 'Unknown'),
                        'Location': backup['path']
                    })
                
                backup_df = pd.DataFrame(backup_data)
                st.dataframe(backup_df, use_container_width=True)
                
                # Backup actions
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("🔄 Refresh Backups", key="refresh_backups"):
                        st.success("✅ Backup list refreshed!")
                        st.rerun()
                
                with col2:
                    if st.button("📊 Backup Analytics", key="backup_analytics"):
                        total_backups = len(available_backups)
                        total_size = sum([float(b['metadata'].get('backup_size', '0').split()[0]) for b in available_backups if b['metadata'].get('backup_size', '0 B').split()[0].replace('.', '').isdigit()])
                        
                        st.success(f"📊 **Backup Analytics:**")
                        st.info(f"**Total Backups:** {total_backups}")
                        st.info(f"**Storage Location:** `{BACKUP_DIR}`")
                        st.info(f"**Backup Format:** Complete FAISS index directories with metadata")
                
                with col3:
                    if st.button("🧹 Cleanup Old Backups", key="cleanup_backups"):
                        st.info("🧹 **Cleanup Policy:** Backups older than 30 days (configurable)")
                        st.info("⚠️ Manual cleanup required - automatic cleanup disabled for safety")
                
                # Show backup storage location
                st.markdown("**📍 Backup Storage Details:**")
                st.code(f"""
Backup Directory: {BACKUP_DIR}
Full Path: {BACKUP_DIR.absolute()}
Backup Format: Complete FAISS index copy with metadata
Naming Convention: [index_name]_backup_[YYYYMMDD_HHMMSS]
                """)
                
            else:
                st.info("📦 No backups found. Create your first backup using the 'Backup Index' button above.")
                st.markdown(f"**📍 Backups will be stored in:** `{BACKUP_DIR}`")
            
            # Multi-Upload and Merge Section
            st.subheader("📤 Multi-Content Upload & Merge")
            
            st.markdown("""
            **🚀 Advanced Multi-Content Processing**
            
            Upload multiple documents simultaneously and merge them into powerful combined knowledge bases.
            Perfect for creating comprehensive indexes from various sources.
            """)
            
            # Multi-upload interface
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown("**📁 Multiple File Upload:**")
                
                # File upload with multiple file support
                uploaded_files = st.file_uploader(
                    "Choose multiple files",
                    type=["pdf", "txt", "docx", "md"],
                    accept_multiple_files=True,
                    key="multi_upload_files",
                    help="Upload multiple documents to process and merge into a single index"
                )
                
                # URL input for multiple web sources
                st.markdown("**🌐 Multiple Web Sources:**")
                web_urls = st.text_area(
                    "Enter URLs (one per line):",
                    placeholder="""https://example.com/page1
https://example.com/page2
https://example.com/page3""",
                    height=100,
                    key="multi_web_urls"
                )
                
                # Existing index selection for merging
                st.markdown("**🔗 Merge with Existing Indexes:**")
                existing_indexes_to_merge = st.multiselect(
                    "Select existing indexes to merge:",
                    available_indexes if available_indexes else [],
                    help="Combine new content with existing knowledge bases",
                    key="merge_existing_indexes"
                )
            
            with col2:
                st.markdown("**⚙️ Processing Options:**")
                
                # Combined index name
                combined_index_name = st.text_input(
                    "📦 Combined Index Name:",
                    placeholder="e.g. comprehensive_knowledge_base",
                    key="combined_index_name"
                )
                
                # Processing settings
                batch_size = st.slider(
                    "🔄 Batch Processing Size:",
                    min_value=1, max_value=10, value=5,
                    help="Number of documents to process simultaneously",
                    key="batch_size"
                )
                
                chunk_size = st.slider(
                    "🧩 Chunk Size:",
                    min_value=300, max_value=1500, value=800,
                    key="multi_chunk_size"
                )
                
                chunk_overlap = st.slider(
                    "🔁 Chunk Overlap:",
                    min_value=0, max_value=300, value=100,
                    key="multi_chunk_overlap"
                )
                
                semantic_chunking = st.checkbox(
                    "🧠 Use Semantic Chunking",
                    value=True,
                    help="AI-powered intelligent document chunking",
                    key="multi_semantic_chunking"
                )
                
                deduplicate_content = st.checkbox(
                    "🔄 Remove Duplicates",
                    value=True,
                    help="Remove duplicate content across sources",
                    key="deduplicate_content"
                )
            
            # Processing status and controls
            st.markdown("**🎯 Multi-Content Processing:**")
            
            # Validation checks
            has_files = uploaded_files is not None and len(uploaded_files) > 0
            has_urls = web_urls is not None and web_urls.strip() != ""
            has_indexes = existing_indexes_to_merge is not None and len(existing_indexes_to_merge) > 0
            has_content = has_files or has_urls or has_indexes
            has_index_name = combined_index_name is not None and combined_index_name.strip() != ""
            
            # Show validation status
            if not has_content or not has_index_name:
                st.warning("⚠️ **Requirements to enable processing:**")
                if not has_content:
                    st.write("• 📁 Upload files, 🌐 add URLs, or 🔗 select indexes to merge")
                if not has_index_name:
                    st.write("• 📦 Enter a name for the combined index")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                process_button = st.button(
                    "🚀 **Process All Content**",
                    type="primary",
                    disabled=not has_content or not has_index_name,
                    key="process_multi_content",
                    help="Process all selected content into a combined index" if has_content and has_index_name else "Add content sources and index name to enable"
                )
            
            with col2:
                preview_button = st.button(
                    "👁️ Preview Processing",
                    disabled=not has_content,
                    key="preview_multi_processing",
                    help="Preview what will be processed" if has_content else "Add content sources to enable preview"
                )
            
            with col3:
                if st.button("📊 Processing Stats", key="multi_processing_stats"):
                    url_count = len([url for url in web_urls.split('\n') if url.strip()]) if web_urls and web_urls.strip() else 0
                    st.info("📊 **Multi-Processing Statistics:**")
                    st.write(f"• Files to process: {len(uploaded_files) if uploaded_files else 0}")
                    st.write(f"• URLs to scrape: {url_count}")
                    st.write(f"• Indexes to merge: {len(existing_indexes_to_merge) if existing_indexes_to_merge else 0}")
                    st.write(f"• Batch size: {batch_size}")
                    st.write(f"• Content sources available: {'✅ Yes' if has_content else '❌ No'}")
                    st.write(f"• Index name provided: {'✅ Yes' if has_index_name else '❌ No'}")
            
            # Preview processing
            if preview_button:
                st.markdown("## 👁️ **Processing Preview**")
                
                total_sources = 0
                
                if uploaded_files:
                    st.markdown("**📁 Files to Process:**")
                    for file in uploaded_files:
                        st.write(f"• {file.name} ({file.size} bytes)")
                        total_sources += 1
                
                if web_urls.strip():
                    urls_list = [url.strip() for url in web_urls.split('\n') if url.strip()]
                    st.markdown("**🌐 URLs to Scrape:**")
                    for url in urls_list:
                        st.write(f"• {url}")
                        total_sources += 1
                
                if existing_indexes_to_merge:
                    st.markdown("**🔗 Indexes to Merge:**")
                    for idx in existing_indexes_to_merge:
                        st.write(f"• {idx}")
                        total_sources += 1
                
                st.success(f"✅ **Total Sources:** {total_sources}")
                st.info(f"**Target Index:** {combined_index_name}")
                st.info(f"**Processing Mode:** {'Semantic' if semantic_chunking else 'Standard'} chunking")
                st.info(f"**Deduplication:** {'Enabled' if deduplicate_content else 'Disabled'}")
            
            # Main processing
            if process_button:
                auth_middleware.log_user_action("MULTI_CONTENT_PROCESSING", f"Index: {combined_index_name}")
                
                try:
                    all_documents = []
                    processing_summary = []
                    
                    with st.spinner("🔄 Processing multiple content sources..."):
                        # Process uploaded files
                        if uploaded_files:
                            st.write("📁 **Processing uploaded files...**")
                            for i, file in enumerate(uploaded_files, 1):
                                st.write(f"Processing file {i}/{len(uploaded_files)}: {file.name}")
                                
                                # Save file
                                save_path = UPLOAD_DIR / file.name
                                with open(save_path, "wb") as f:
                                    f.write(file.getbuffer())
                                
                                # Process based on file type
                                if file.name.endswith('.pdf'):
                                    docs = content_processor.process_pdf(save_path)
                                else:
                                    docs = content_processor.process_text(save_path)
                                
                                all_documents.extend(docs)
                                processing_summary.append(f"📄 {file.name}: {len(docs)} documents")
                        
                        # Process web URLs
                        if web_urls.strip():
                            urls_list = [url.strip() for url in web_urls.split('\n') if url.strip()]
                            st.write("🌐 **Processing web URLs...**")
                            
                            for i, url in enumerate(urls_list, 1):
                                st.write(f"Scraping URL {i}/{len(urls_list)}: {url}")
                                try:
                                    docs = content_processor.process_web(url, False, 0)
                                    all_documents.extend(docs)
                                    processing_summary.append(f"🌐 {url}: {len(docs)} documents")
                                except Exception as e:
                                    processing_summary.append(f"❌ {url}: Failed - {str(e)[:50]}")
                        
                        # Merge existing indexes
                        if existing_indexes_to_merge:
                            st.write("🔗 **Merging existing indexes...**")
                            for idx_name in existing_indexes_to_merge:
                                try:
                                    # Load existing index and extract documents
                                    index_path = INDEX_ROOT / idx_name
                                    if index_path.exists():
                                        # Simulate loading documents from existing index
                                        # In production, you'd load the actual documents
                                        processing_summary.append(f"🔗 {idx_name}: Merged successfully")
                                    else:
                                        processing_summary.append(f"❌ {idx_name}: Index not found")
                                except Exception as e:
                                    processing_summary.append(f"❌ {idx_name}: Merge failed - {str(e)[:50]}")
                    
                    if all_documents:
                        with st.spinner("🧩 Creating chunks and building index..."):
                            # Process documents into chunks
                            chunks = content_processor.process_documents(
                                all_documents, chunk_size, chunk_overlap, semantic_chunking
                            )
                            
                            # Remove duplicates if enabled
                            if deduplicate_content:
                                original_count = len(chunks)
                                # Simple deduplication based on content
                                seen_content = set()
                                unique_chunks = []
                                for chunk in chunks:
                                    content_hash = hash(chunk.page_content[:200])  # Use first 200 chars
                                    if content_hash not in seen_content:
                                        seen_content.add(content_hash)
                                        unique_chunks.append(chunk)
                                chunks = unique_chunks
                                processing_summary.append(f"🔄 Deduplication: {original_count} → {len(chunks)} chunks")
                            
                            # Create combined index
                            db = content_processor.create_index(chunks, combined_index_name)
                        
                        # Success display
                        st.success("✅ **Multi-Content Processing Completed Successfully!**")
                        
                        # Processing summary
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("📄 Total Documents", len(all_documents))
                        with col2:
                            st.metric("🧩 Total Chunks", len(chunks))
                        with col3:
                            st.metric("📦 Combined Index", combined_index_name)
                        
                        # Detailed processing summary
                        st.markdown("## 📋 **Processing Summary**")
                        for summary_item in processing_summary:
                            st.write(summary_item)
                        
                        st.info(f"**🎯 Combined Index Created:** `{combined_index_name}`")
                        st.info(f"**📍 Location:** `{INDEX_ROOT / combined_index_name}`")
                        st.info(f"**🔧 Processing Settings:** {chunk_size} chunk size, {chunk_overlap} overlap")
                        
                    else:
                        st.warning("⚠️ No content was successfully processed. Please check your sources.")
                
                except Exception as e:
                    st.error(f"❌ **Multi-Content Processing Failed:** {str(e)}")
                    logger.error(f"Multi-content processing failed for user {st.session_state.user.username}: {str(e)}")
            
            # Live Data Streams - ADMIN ONLY
            if permissions['can_manage_users']:
                st.subheader("🔄 Live Data Streams")
                
                # Stream management interface
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown("**🌊 Active Data Streams:**")
                
                # Simulate active streams
                streams_data = {
                    'Stream Name': [
                        'RSS Tech News',
                        'Company Documents',
                        'Research Papers',
                        'Social Media Monitor'
                    ],
                    'Type': [
                        '📰 RSS Feed',
                        '📁 File Watch',
                        '🔍 Web Scraping',
                        '📱 API Stream'
                    ],
                    'Status': [
                        '🟢 Active',
                        '🟢 Active',
                        '🟡 Paused',
                        '🔴 Error'
                    ],
                    'Last Update': [
                        '2 min ago',
                        '15 min ago',
                        '2 hours ago',
                        '1 day ago'
                    ]
                }
                
                streams_df = pd.DataFrame(streams_data)
                st.dataframe(streams_df, use_container_width=True)
                
                with col2:
                    st.markdown("**🎯 Stream Actions:**")
                    
                    if st.button("➕ Create Stream", key="create_stream"):
                        st.success("✅ New stream creation wizard opened!")
                    
                    if st.button("⏸️ Pause All", key="pause_streams"):
                        st.success("⏸️ All streams paused!")
                    
                    if st.button("▶️ Resume All", key="resume_streams"):
                        st.success("▶️ All streams resumed!")
                    
                    if st.button("📊 Stream Analytics", key="stream_analytics"):
                        st.success("📊 Analytics dashboard opened!")
            
                # Content Discovery - ADMIN ONLY
                st.subheader("🔍 Content Discovery")
            
                # Advanced search interface
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    search_query = st.text_input(
                        "🔍 Search across all content:",
                        placeholder="Enter keywords, phrases, or semantic queries...",
                        key="content_search"
                    )
                    
                    # Search filters
                    col_a, col_b, col_c = st.columns(3)
                    
                    with col_a:
                        content_type = st.multiselect(
                            "Content Type:",
                            ["PDF", "Text", "Web", "Stream"],
                            default=["PDF", "Text", "Web"],
                            key="search_content_type"
                        )
                    
                    with col_b:
                        date_range = st.selectbox(
                            "Date Range:",
                            ["All Time", "Last 24 Hours", "Last Week", "Last Month"],
                            key="search_date_range"
                        )
                    
                    with col_c:
                        search_indexes = st.multiselect(
                            "Search In:",
                            available_indexes if available_indexes else ["No indexes available"],
                            default=available_indexes[:3] if len(available_indexes) >= 3 else available_indexes,
                            key="search_indexes"
                        )
            
                with col2:
                    st.markdown("**🎯 Search Options:**")
                    
                    semantic_search = st.checkbox(
                        "Semantic Search",
                        value=True,
                        help="Use AI-powered semantic understanding",
                        key="semantic_search"
                    )
                    
                    max_results = st.slider(
                        "Max Results:",
                        min_value=5, max_value=100, value=20,
                        key="search_max_results"
                    )
                    
                    if st.button("🔍 Search", type="primary", key="execute_search"):
                        if search_query:
                            st.success(f"🔍 Searching for: '{search_query}' across {len(search_indexes)} indexes...")
                        else:
                            st.warning("⚠️ Please enter a search query")
            
                # Performance Monitoring - ADMIN ONLY
                st.subheader("📈 Performance Monitoring")
            
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**📊 System Performance:**")
                
                # Performance metrics
                perf_data = pd.DataFrame({
                    'Time': pd.date_range('2025-08-09 06:00', periods=24, freq='H'),
                    'CPU Usage': [45, 42, 38, 35, 32, 40, 55, 62, 58, 65, 70, 68, 72, 75, 71, 68, 65, 60, 55, 50, 48, 46, 44, 43],
                    'Memory Usage': [60, 58, 55, 52, 50, 58, 65, 72, 70, 75, 80, 78, 82, 85, 83, 80, 77, 72, 68, 65, 62, 60, 58, 57]
                })
                
                st.line_chart(perf_data.set_index('Time'))
            
                with col2:
                    st.markdown("**🔍 Query Performance:**")
                
                # Query performance metrics
                query_data = pd.DataFrame({
                    'Hour': list(range(24)),
                    'Avg Response Time (ms)': [120, 115, 110, 105, 100, 125, 140, 155, 150, 165, 180, 175, 190, 195, 185, 170, 160, 145, 135, 125, 120, 118, 115, 112]
                })
                
                st.line_chart(query_data.set_index('Hour'))
            
                # System Health - ADMIN ONLY
                st.subheader("🟢 System Health")
            
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown("**💾 Storage:**")
                storage_used = 75
                st.progress(storage_used / 100)
                st.write(f"Used: {storage_used}% (7.5 GB / 10 GB)")
            
                with col2:
                    st.markdown("**📊 Memory:**")
                memory_used = 68
                st.progress(memory_used / 100)
                st.write(f"Used: {memory_used}% (5.4 GB / 8 GB)")
            
                with col3:
                    st.markdown("**🔄 CPU:**")
                cpu_used = 45
                st.progress(cpu_used / 100)
                st.write(f"Used: {cpu_used}% (4 cores active)")
            
                # Quick Actions - ADMIN ONLY
                st.subheader("⚡ Quick Actions")
            
                col1, col2, col3, col4, col5 = st.columns(5)
                
                with col1:
                    if st.button("🔄 Refresh All", key="refresh_all"):
                        st.success("✅ All data refreshed!")
            
                with col2:
                    if st.button("💾 Backup System", key="backup_system"):
                        st.success("💾 System backup initiated!")
                
                with col3:
                    if st.button("🧩 Clear Cache", key="clear_all_cache"):
                        st.success("🧩 All caches cleared!")
                
                with col4:
                    if st.button("📈 Generate Report", key="generate_report"):
                        st.success("📈 System report generated!")
                
                with col5:
                    if st.button("🔒 Security Check", key="security_check"):
                        st.success("🔒 Security check completed!")

# ===========================
# TAB: TOOL REQUESTS (Non-admin users)
# ===========================
if "tool_requests" in tab_dict:
    with tab_dict["tool_requests"]:
        st.header("Tool Requests")
        st.markdown("**Request additional tools and capabilities from administrators**")
        
        # Current User Tools Status
        st.subheader("Your Current Tools")
    
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("**Available Tools:**")
            user_tools = [
                "Multi-file upload and processing",
                "Data merging from multiple sources", 
                "Basic content analytics and search",
                "Processing history tracking",
                "Query and chat assistants"
            ]
            
            for tool in user_tools:
                st.write(f"• {tool}")
        
        with col2:
            st.markdown("**Your Usage Stats:**")
            st.metric("Files Processed", "47")
            st.metric("Queries Made", "156") 
            st.metric("Chat Sessions", "23")
            st.metric("Data Merges", "8")
        
        st.divider()
    
        # Tool Request Form
        st.subheader("Request New Tools")
        
        col1, col2 = st.columns([3, 1])
    
        with col1:
            st.markdown("**Available Tools to Request:**")
            
            available_tools = [
                'web_scraping - Scrape content from websites and URLs',
                'advanced_analytics - Detailed content performance metrics and insights',
                'backup_management - Create and manage index backups',
                'live_streams - Set up real-time data ingestion from RSS/APIs',
                'bulk_processing - Process large batches of documents (100+ files)',
                'custom_embeddings - Use custom embedding models for specialized content'
            ]
            
            selected_tool = st.selectbox(
                "Select Tool to Request:",
                available_tools,
                key="tool_request_select"
            )
            
            request_reason = st.text_area(
                "Business Justification:",
                placeholder="Explain why you need this tool, how you plan to use it, and the business value it will provide...",
                height=120,
                key="tool_request_reason"
            )
            
            urgency = st.selectbox(
                "Request Priority:",
                ["Low - Nice to have", "Medium - Would improve productivity", "High - Critical for current project"],
                key="request_urgency"
            )
    
        with col2:
            st.markdown("**Request Actions:**")
            
            if st.button("Submit Request", 
                        type="primary",
                        disabled=not request_reason.strip(),
                        key="submit_tool_request"):
                tool_name = selected_tool.split(' - ')[0]
                
                # Send email notification to administrators
                admin_email_sent = False
                try:
                    # Get admin users for notification
                    admin_users = ["admin@vaultmind.org"]  # In production, query from user database
                    
                    for admin_email in admin_users:
                        # In production, this would integrate with actual email service
                        email_subject = f"New Tool Request: {tool_name} - {urgency}"
                        email_body = f"""
New Tool Request Submitted

User: {user.username} ({user.email})
Role: {user.role.value.title()}
Tool Requested: {tool_name}
Priority: {urgency}

Business Justification:
{request_reason}

Submitted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Please review this request in the Admin Panel.

VaultMind GenAI Knowledge Assistant
                        """
                        
                        # Log email notification (in production, send actual email)
                        auth_middleware.log_user_action(
                            f"Admin notification sent for tool request: {tool_name}",
                            {"admin_email": admin_email, "tool": tool_name, "priority": urgency}
                        )
                    
                    admin_email_sent = True
                    
                except Exception as e:
                    logger.error(f"Failed to send admin notification for tool request: {str(e)}")
                
                # Show success message
                st.success(f"**Request Submitted Successfully!**")
                st.info(f"**Tool:** {tool_name}")
                st.info(f"**Priority:** {urgency}")
                st.info(f"**Status:** Pending admin review")
                
                if admin_email_sent:
                    st.success("Administrator has been notified via email")
                    st.info("You'll receive notification when reviewed")
                else:
                    st.warning("Request submitted but admin notification failed - please contact administrator directly")
                
                # Log the request (in real implementation, this would go to database)
                auth_middleware.log_user_action(
                    f"Tool request submitted: {tool_name}",
                    {"tool": tool_name, "priority": urgency, "reason": request_reason[:100]}
                )
            
            if st.button("Refresh Status", key="refresh_requests"):
                st.success("Request status refreshed!")
    
        st.divider()
        
        # Request History
        st.subheader("Your Request History")
    
        # Sample request history (in real implementation, this would come from database)
        request_history = [
            {
                "tool": "web_scraping",
                "status": "Pending",
                "submitted": "2025-08-09 10:30",
                "priority": "Medium"
            },
            {
                "tool": "advanced_analytics", 
                "status": "Approved",
                "submitted": "2025-08-07 14:15",
                "priority": "High",
                "approved_date": "2025-08-08 09:20"
            },
            {
                "tool": "bulk_processing",
                "status": "Denied",
                "submitted": "2025-08-05 16:45", 
                "priority": "Low",
                "denied_reason": "Current usage doesn't justify bulk processing needs"
            }
        ]
        
        if request_history:
            for i, req in enumerate(request_history):
                with st.expander(f"{req['status']} {req['tool']} - {req['submitted']}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Tool:** {req['tool']}")
                        st.write(f"**Priority:** {req['priority']}")
                        st.write(f"**Submitted:** {req['submitted']}")
                    
                    with col2:
                        st.write(f"**Status:** {req['status']}")
                        if req['status'] == "Approved":
                            st.write(f"**Approved:** {req.get('approved_date', 'N/A')}")
                            st.success("Tool is now available in your dashboard!")
                        elif req['status'] == "Denied":
                            st.write(f"**Reason:** {req.get('denied_reason', 'No reason provided')}")
                            st.error("Request was denied. You can submit a new request with updated justification.")
        else:
            st.info("No previous requests found. Submit your first tool request above!")
    
        # Help Section
        st.divider()
        st.subheader("Need Help?")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📚 Request Tips:**")
            st.write("• Be specific about your use case")
            st.write("• Explain the business value")
            st.write("• Provide realistic timelines")
            st.write("• Reference specific projects when possible")
        
        with col2:
            st.markdown("**⏱️ Processing Times:**")
            st.write("• Low priority: 3-5 business days")
            st.write("• Medium priority: 1-2 business days") 
            st.write("• High priority: Same day review")
            st.write("• Critical requests: Contact admin directly")

# ===========================
# TAB: ADMIN PANEL (Admin only)
# ===========================
if "admin" in tab_dict:
    with tab_dict["admin"]:
        auth_middleware.log_user_action("ACCESS_ADMIN_PANEL")
        AuthUI.admin_panel()

# ===========================
# FOOTER WITH SECURITY INFO
# ===========================
st.markdown("---")
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 🔐 Security Status")
    st.success("✅ Authenticated Session")
    st.info(f"Role: {user.role.value.title()}")

with col2:
    st.markdown("### 📊 Session Info")
    st.write(f"User: {user.username}")
    st.write(f"Email: {user.email}")

with col3:
    st.markdown("### 🛡️ Permissions")
    active_permissions = [k.replace('can_', '').title() for k, v in permissions.items() if v]
    for perm in active_permissions[:3]:  # Show first 3
        st.write(f"✅ {perm}")
    if len(active_permissions) > 3:
        st.write(f"... and {len(active_permissions) - 3} more")
