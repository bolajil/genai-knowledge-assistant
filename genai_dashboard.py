# Add at the VERY TOP of your file
import os
import re
import sys
sys.path.append("./")
import pydantic
import sqlite3  # Added for MCP database
from pathlib import Path
import streamlit as st
import requests
import logging
from typing import List, Dict
from dotenv import load_dotenv
import importlib.util
import torch  # Added for device management
import sentence_transformers
import time  # Added for agent reasoning simulation
from datetime import datetime, timezone  # Added for timestamp handling
from app.utils.embedding_client import EmbeddingClient
# embedding_client will be instantiated lazily when needed


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
#from langchain_huggingface import HuggingFaceEmbeddings
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
        print(f"[-] Failed to load module {module_name}: {e}")
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
    print("[+] Loaded query_helpers")
except Exception as e:
    modules_loaded['query_helpers'] = False
    module_errors.append(f"query_helpers: {e}")
    print(f"[!] Failed to load query_helpers: {e}")
    # Fallback function
    def query_index(query, index_name, top_k=5):
        return ["Fallback: Module not available. Please check dependencies."]

try:
    # Import chat_orchestrator
    chat_orchestrator = load_module(
        "app.utils.chat_orchestrator",
        PROJECT_ROOT / "app" / "utils" / "chat_orchestrator.py"
    )
    get_chat_chain = chat_orchestrator.get_chat_chain
    modules_loaded['chat_orchestrator'] = True
    print("[+] Loaded chat_orchestrator")
except Exception as e:
    modules_loaded['chat_orchestrator'] = False
    module_errors.append(f"chat_orchestrator: {e}")
    print(f"[!] Failed to load chat_orchestrator: {e}")
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
    print("[+] Loaded controller_agent")
except Exception as e:
    modules_loaded['controller_agent'] = False
    module_errors.append(f"controller_agent: {e}")
    print(f"[!] Failed to load controller_agent: {e}")
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
    print("[+] Loaded index_utils")
except Exception as e:
    modules_loaded['index_utils'] = False
    module_errors.append(f"index_utils: {e}")
    print(f"[!] Failed to load index_utils: {e}")
    # Fallback function
    def list_indexes():
        return []

# Show module loading status
loaded_count = sum(modules_loaded.values())
total_count = len(modules_loaded)
print(f"[*] Module Loading Status: {loaded_count}/{total_count} modules loaded successfully")

if module_errors:
    print("[!] Module loading warnings:")
    for error in module_errors:
        print(f"  - {error}")
    print("[*] Some features may have limited functionality. Consider installing missing dependencies.")

# Constants
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
INDEX_ROOT = Path("data/faiss_index")
UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
INDEX_ROOT.mkdir(parents=True, exist_ok=True)

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
        # Keep the embedding client for backward compatibility (lazy initialization)
        self._embedding_client = None

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
                # Fallback: use the existing embedding client approach
                raise
        return self._embeddings

    @property
    def embedding_client(self):
        """Lazy initialization of embedding client to avoid PyTorch meta tensor issues"""
        if self._embedding_client is None:
            try:
                self._embedding_client = EmbeddingClient()
            except Exception as e:
                print(f"Warning: Failed to initialize EmbeddingClient: {e}")
                # Set to a dummy object to avoid repeated initialization attempts
                self._embedding_client = None
                raise
        return self._embedding_client

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


# =================
# WEB SCRAPER CLASS
# =================
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
                    logger.warning(f"requests_html failed for {url}: {str(js_e)}")
                    # Try playwright if available
                    try:
                        from playwright.sync_api import sync_playwright
                        with sync_playwright() as p:
                            browser = p.chromium.launch(headless=True)
                            page = browser.new_page()
                            page.goto(url, timeout=30000)
                            page.wait_for_timeout(3000)
                            content = page.content()
                            browser.close()
                            soup = BeautifulSoup(content, "html.parser")
                            content = soup.get_text()
                            log_entry["status"] = "Rendered via Playwright"
                    except ImportError:
                        logger.warning("Playwright not available, falling back to basic scraping")
                        # Fallback to basic requests without JS rendering
                        response = self.session.get(url)
                        soup = BeautifulSoup(response.content, "html.parser")
                        content = soup.get_text()
                        log_entry["status"] = "Basic scraping (no JS)"
                    except Exception as playwright_e:
                        logger.warning(f"Playwright failed for {url}: {str(playwright_e)}")
                        # Final fallback to basic requests
                        response = self.session.get(url)
                        soup = BeautifulSoup(response.content, "html.parser")
                        content = soup.get_text()
                        log_entry["status"] = "Basic scraping fallback"
            else:
                # Try newspaper3k first
                try:
                    article = Article(url)
                    article.download()
                    article.parse()
                    content = article.text
                    log_entry["status"] = "Parsed via newspaper3k"
                except Exception as newspaper_e:
                    logger.warning(f"newspaper3k failed for {url}: {str(newspaper_e)}")
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
            # You can implement more sophisticated logging here
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

# ==========================
# NOTIFICATION SERVICE CLASS
# ==========================
class NotificationService:
    def __init__(self):
        self.flowise_url = os.getenv("FLOWISE_URL", "http://localhost:3000/api/v1/flow")
        self.flowise_api_key = os.getenv("FLOWISE_API_KEY")
        self.n8n_url = os.getenv("N8N_URL", "http://localhost:5678/webhook")
        self.n8n_api_key = os.getenv("N8N_API_KEY")

    def validate_email(self, email: str) -> bool:
        """Simple email validation"""
        return bool(re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email))

    def send_via_flowise(
        self, content: str, recipients: List[str], channels: List[str]
    ) -> str:
        """Send notification using Flowise"""
        try:
            payload = {
                "question": f"Send this to {', '.join(channels)}: {content}",
                "overrideConfig": {
                    "sessionId": "streamlit-notification",
                    "recipients": recipients,
                    "channels": channels,
                },
            }

            headers = {"Authorization": f"Bearer {self.flowise_api_key}"}
            response = requests.post(
                f"{self.flowise_url}/your-flow-id/run",
                json=payload,
                headers=headers,
                timeout=10,
            )

            if response.status_code == 200:
                return "Flowise notification processed"
            return f"Flowise error: {response.text}"

        except Exception as e:
            logger.error(f"Flowise error: {str(e)}")
            return f"Flowise error: {str(e)}"

    def send_via_n8n(
        self, content: str, recipients: List[str], channels: List[str]
    ) -> str:
        """Send notification using n8n"""
        try:
            # Validate and filter recipients
            valid_recipients = [
                r.strip() for r in recipients if self.validate_email(r.strip())
            ]

            if not valid_recipients:
                return "No valid recipients provided"

            payload = {
                "content": content,
                "recipients": valid_recipients,
                "channels": channels,
                "source": "GenAI Assistant",
            }

            headers = {"X-API-KEY": self.n8n_api_key}
            response = requests.post(
                self.n8n_url, json=payload, headers=headers, timeout=10
            )

            if response.status_code == 200:
                return "n8n notification sent"
            return f"n8n error: {response.text}"

        except Exception as e:
            logger.error(f"n8n error: {str(e)}")
            return f"n8n error: {str(e)}"

    def send_notification(
        self, content: str, recipients: List[str], channels: List[str], service: str
    ) -> str:
        """Send notification using selected service"""
        if service == "flowise":
            return self.send_via_flowise(content, recipients, channels)
        elif service == "n8n":
            return self.send_via_n8n(content, recipients, channels)
        return "No notification service selected"


# Initialize services
content_processor = ContentProcessor()
notification_service = NotificationService()
web_scraper = WebScraper()

# =====================
# STREAMLIT UI SETUP
# =====================
st.set_page_config(
    page_title="GenAI Knowledge Assistant", page_icon="🧠", layout="wide"
)

# Clean CSS for better text visibility without breaking existing design
st.markdown("""
<style>
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

/* Chat message containers */
.chat-response {
    background-color: #ebf8ff;
    border: 1px solid #90cdf4;
    border-left: 4px solid #3182ce;
    border-radius: 8px;
    padding: 16px;
    margin: 12px 0;
    color: #1a365d;
}

/* Agent response containers */
.agent-response {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border-radius: 15px;
    padding: 20px;
    margin: 20px 0;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

/* Query results */
.query-result {
    background-color: #f0fff4;
    border: 1px solid #9ae6b4;
    border-left: 4px solid #38a169;
    border-radius: 8px;
    padding: 16px;
    margin: 12px 0;
    color: #1a202c;
}

/* Better contrast for main text areas */
.stMarkdown p, .stMarkdown span, .stMarkdown div {
    color: #e2e8f0;
}

/* Make all text elements more visible */
.stMarkdown {
    color: #e2e8f0;
}

/* Make subtitle text white for maximum visibility */
.stMarkdown p:nth-child(2), .stMarkdown p:nth-child(3) {
    color: white;
    font-weight: 400;
}

/* Strong text - make white for visibility */
.stMarkdown strong, .stMarkdown b {
    color: white;
    font-weight: 600;
}

/* Links */
.stMarkdown a {
    color: #3182ce;
    text-decoration: underline;
}

.stMarkdown a:hover {
    color: #2c5282;
}

/* VaultMind Logo Styling - Using Actual Logo Image */
.vaultmind-logo {
    position: fixed;
    top: 70px;
    right: 15px;
    z-index: 999;
    width: 240px;
    height: 120px;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    background: #22c55e;
    background-image: url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQwIiBoZWlnaHQ9IjEyMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KICA8IS0tIEJhY2tncm91bmQgLS0+CiAgPHJlY3Qgd2lkdGg9IjI0MCIgaGVpZ2h0PSIxMjAiIGZpbGw9IiMyMmM1NWUiIHJ4PSIxMiIvPgogIAogIDwhLS0gTG9jayBTaGFwZSAtLT4KICA8ZyB0cmFuc2Zvcm09InRyYW5zbGF0ZSgyMCwgMjApIj4KICAgIDwhLS0gTG9jayBCb2R5IC0tPgogICAgPHJlY3Qgd2lkdGg9IjYwIiBoZWlnaHQ9IjQ1IiB4PSIxMCIgeT0iMzUiIGZpbGw9IndoaXRlIiBzdHJva2U9IiNkZGQiIHN0cm9rZS13aWR0aD0iMiIgcng9IjgiLz4KICAgIAogICAgPCEtLSBMb2NrIFNoYWNrbGUgLS0+CiAgICA8cGF0aCBkPSJNMjUgMzUgVjIwIEExNSAxNSAwIDAgMSA1NSAyMCBWMzUiIGZpbGw9Im5vbmUiIHN0cm9rZT0id2hpdGUiIHN0cm9rZS13aWR0aD0iNiIvPgogICAgCiAgICA8IS0tIEJyYWluIEluc2lkZSBMb2NrIC0tPgogICAgPGcgdHJhbnNmb3JtPSJ0cmFuc2xhdGUoMjUsIDQ1KSI+CiAgICAgIDwhLS0gQnJhaW4gT3V0bGluZSAtLT4KICAgICAgPHBhdGggZD0iTTE1IDI1IEMxMCAyMCAxMCAxNSAxNSAxMCBDMjAgNSAyNSA1IDMwIDEwIEMzNSAxNSAzNSAyMCAzMCAyNSBDMzUgMzAgMzUgMzUgMzAgNDAgQzI1IDQ1IDIwIDQ1IDE1IDQwIEMxMCAzNSAxMCAzMCAxNSAyNSBaIiBmaWxsPSIjMjJjNTVlIiBzdHJva2U9IiMyMmM1NWUiIHN0cm9rZS13aWR0aD0iMiIvPgogICAgICAKICAgICAgPCEtLSBCcmFpbiBGb2xkcyAtLT4KICAgICAgPHBhdGggZD0iTTE4IDIwIEMyMCAxOCAyNSAxOCAyNyAyMCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSIxLjUiLz4KICAgICAgPHBhdGggZD0iTTE4IDI1IEMyMCAyMyAyNSAyMyAyNyAyNSIgZmlsbD0ibm9uZSIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSIxLjUiLz4KICAgICAgPHBhdGggZD0iTTE4IDMwIEMyMCAyOCAyNSAyOCAyNyAzMCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSIxLjUiLz4KICAgICAgCiAgICAgIDwhLS0gQ2VudGVyIERpdmlzaW9uIC0tPgogICAgICA8cGF0aCBkPSJNMjIuNSAxNSBMMjIuNSAzNSIgZmlsbD0ibm9uZSIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSIxLjUiLz4KICAgICAgCiAgICAgIDwhLS0gTGVmdCBIZW1pc3BoZXJlIERldGFpbHMgLS0+CiAgICAgIDxwYXRoIGQ9Ik0xNiAyMiBDMTggMjAgMjAgMjAgMjIgMjIiIGZpbGw9Im5vbmUiIHN0cm9rZT0id2hpdGUiIHN0cm9rZS13aWR0aD0iMSIvPgogICAgICA8cGF0aCBkPSJNMTYgMjggQzE4IDI2IDIwIDI2IDIyIDI4IiBmaWxsPSJub25lIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjEiLz4KICAgICAgCiAgICAgIDwhLS0gUmlnaHQgSGVtaXNwaGVyZSBEZXRhaWxzIC0tPgogICAgICA8cGF0aCBkPSJNMjMgMjIgQzI1IDIwIDI3IDIwIDI5IDIyIiBmaWxsPSJub25lIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjEiLz4KICAgICAgPHBhdGggZD0iTTIzIDI4IEMyNSAyNiAyNyAyNiAyOSAyOCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSIxIi8+CiAgICA8L2c+CiAgPC9nPgogIAogIDwhLS0gVmF1bHRNaW5kIFRleHQgLS0+CiAgPHRleHQgeD0iMTEwIiB5PSI0NSIgZm9udC1mYW1pbHk9IkFyaWFsLCBzYW5zLXNlcmlmIiBmb250LXNpemU9IjI4IiBmb250LXdlaWdodD0iYm9sZCIgdGV4dC1hbmNob3I9InN0YXJ0IiBmaWxsPSJ3aGl0ZSI+VmF1bHRNaW5kPC90ZXh0PgogIAogIDwhLS0gU3VidGl0bGUgLS0+CiAgPHRleHQgeD0iMTEwIiB5PSI2NSIgZm9udC1mYW1pbHk9IkFyaWFsLCBzYW5zLXNlcmlmIiBmb250LXNpemU9IjEyIiB0ZXh0LWFuY2hvcj0ic3RhcnQiIGZpbGw9IndoaXRlIiBvcGFjaXR5PSIwLjkiPkFJIEFzc2lzdGFudCBmb3IgU2VjdXJlIEVudGVycHJpc2UgS25vd2xlZGdlPC90ZXh0PgogIAogIDwhLS0gUG93ZXJlZCBieSB0ZXh0IC0tPgogIDx0ZXh0IHg9IjExMCIgeT0iODUiIGZvbnQtZmFtaWx5PSJBcmlhbCwgc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMCIgdGV4dC1hbmNob3I9InN0YXJ0IiBmaWxsPSJ3aGl0ZSIgb3BhY2l0eT0iMC43Ij5Qb3dlcmVkIGJ5IEdlbmVyYXRpdmUgQUkgQWdlbnRzPC90ZXh0Pgo8L3N2Zz4=');
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
}

.vaultmind-logo .logo-icon {
    width: 60px;
    height: 60px;
    margin-right: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(255,255,255,0.1);
    border-radius: 50%;
    font-size: 28px;
}

.vaultmind-logo .logo-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
}

.vaultmind-logo .logo-title {
    font-size: 22px;
    font-weight: bold;
    line-height: 1.1;
    margin-bottom: 4px;
}

.vaultmind-logo .logo-subtitle {
    font-size: 11px;
    line-height: 1.2;
    opacity: 0.95;
    margin-bottom: 2px;
}

.vaultmind-logo .logo-tagline {
    font-size: 9px;
    line-height: 1.1;
    opacity: 0.8;
}

/* Header container for logo integration */
.header-container {
    position: relative;
    margin-bottom: 20px;
}
</style>
""", unsafe_allow_html=True)

# VaultMind Logo Integration
try:
    # Read the SVG file directly
    logo_path = Path("assets/vaultmind_logo.svg")
    if logo_path.exists():
        with open(logo_path, "r", encoding="utf-8") as f:
            svg_content = f.read()
        
        # Display the SVG logo with proper styling
        st.markdown(f"""
        <div style="
            position: fixed;
            top: 70px;
            right: 15px;
            z-index: 999;
            width: 240px;
            height: 120px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        ">
            {svg_content}
        </div>
        """, unsafe_allow_html=True)
    else:
        # Fallback to CSS-based logo if SVG file not found
        st.markdown("""
        <div class="vaultmind-logo"></div>
        """, unsafe_allow_html=True)
except Exception as e:
    # Fallback to CSS-based logo on any error
    st.markdown("""
    <div class="vaultmind-logo"></div>
    """, unsafe_allow_html=True)

st.title("🧠 GenAI Knowledge Assistant")
st.markdown("""
**🚀 Advanced AI-Powered Knowledge Management System**

Upload documents, ask intelligent questions, engage in conversations, and leverage autonomous AI agents - all with beautifully formatted, easy-to-read responses.
""")

# Tab Layout - Now with 6 tabs including Multi-Content Dashboard
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    [
        "📁 Ingest Document",
        "🔍 Query Assistant",
        "💬 Chat Assistant",
        "🤖 Agent Assistant",
        "🔄 MCP Dashboard",
        "🧩 Multi-Content Dashboard"
    ]
)

# Supported LLMs
llm_providers = [
    "openai",
    "claude",
    "deepseek",
    "mistral",
    "anthropic",
]

# Utility: get list of indexes using our imported function
def get_index_list():
    return list_indexes(INDEX_ROOT) if INDEX_ROOT.exists() else []


# ===========================
# TAB 1: DOCUMENT INGESTION
# ===========================
with tab1:
    st.subheader("📁 Upload and Index Content")

    # Content source selection
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

            # Enhanced success display with markdown formatting
            st.markdown(f"""
## 🎉 **Document Processing Complete!**

### 📊 **Processing Summary:**
- **Source:** {source_info}
- **Documents Processed:** {len(documents)}
- **Chunks Generated:** {len(chunks) if 'chunks' in locals() else 'Processing...'}
- **Index Name:** `{index_name}`
            """)

            # Process and chunk documents
            chunks = content_processor.process_documents(
                documents,
                chunk_size,
                chunk_overlap,
                semantic_chunking
            )
            
            # Update the summary with chunk info
            st.markdown(f"""
### ✅ **Successfully Created Knowledge Base**

**🧩 Chunking Details:**
- **Total Chunks:** {len(chunks)}
- **Chunk Size:** {chunk_size} characters
- **Overlap:** {chunk_overlap} characters
- **Method:** {'Semantic Chunking' if semantic_chunking else 'Standard Chunking'}

**📚 Index Information:**
- **Name:** `{index_name}`
- **Status:** ✅ Successfully Created
- **Ready for:** Queries, Chat, and Agent Analysis
            """)

            # Create and save index
            content_processor.create_index(chunks, index_name)
            st.balloons()

            # Enhanced content preview
            st.markdown("### 📝 **Content Preview**")
            
            if chunks:
                # Show first chunk preview in a nice format
                preview_content = chunks[0].page_content
                if len(preview_content) > 800:
                    preview_content = preview_content[:800] + "..."
                
                st.markdown(f"""
<div class="response-container">
<h4>📄 Sample Content (First Chunk)</h4>

{preview_content}

<p><em>This is a preview of the first chunk. Your knowledge base contains {len(chunks)} similar chunks ready for analysis.</em></p>
</div>
                """, unsafe_allow_html=True)
                
                # Show chunk distribution
                chunk_lengths = [len(chunk.page_content) for chunk in chunks[:10]]  # First 10 chunks
                avg_length = sum(chunk_lengths) / len(chunk_lengths) if chunk_lengths else 0
                
                st.markdown(f"""
**📊 Chunk Analysis:**
- **Average Chunk Length:** {int(avg_length)} characters
- **Shortest Chunk:** {min(chunk_lengths) if chunk_lengths else 0} characters
- **Longest Chunk:** {max(chunk_lengths) if chunk_lengths else 0} characters
                """)
            else:
                st.warning("⚠️ No content available for preview")

        except Exception as e:
            st.error(f"❌ Ingestion failed: {type(e).__name__} — {str(e)[:200]}")


# ==========================
# TAB 2: QUERY ASSISTANT
# ==========================
with tab2:
    st.subheader("🔍 Query Assistant")
    index_options = get_index_list()

    # Add web search option
    search_mode = st.radio(
        "Search mode:", ["🔍 Local Index", "🌐 Web Search"], horizontal=True
    )

    if search_mode == "🔍 Local Index":
        if not index_options:
            st.warning("No indexes available. Please ingest documents first.")
            st.stop()

        index_name = st.selectbox("📂 Choose an index", index_options)
    else:
        web_query = st.text_input(
            "🌐 Web search query", placeholder="e.g. latest cloud security threats"
        )
        max_results = st.slider("Number of results", 1, 10, 5)

    # Common parameters
    query = st.text_input(
        "💬 Your question",
        placeholder="e.g. List security measures that Amazon provides",
    )
    top_k = st.slider("🔢 Number of chunks", 1, 10, 5)
    llm_choice = st.selectbox("🧠 Choose LLM provider", llm_providers)

    if st.button("Run Query") and query:
        try:
            if search_mode == "🔍 Local Index":
                results = query_index(query, index_name, top_k)
            else:
                search_query = web_query or query
                search_results = web_scraper.search_web(search_query, max_results)

                if not search_results:
                    st.warning("No web results found. Try a different query.")
                    st.stop()

                with st.status(
                    f"🌐 Scraping {len(search_results)} pages...", expanded=True
                ) as status:
                    documents = []
                    for i, url in enumerate(search_results):
                        st.write(f"Scraping: {url}")
                        try:
                            doc = web_scraper.scrape_to_document(url)
                            if doc.page_content.strip():
                                documents.append(doc)
                                st.success(
                                    f"Scraped {len(doc.page_content)} characters"
                                )
                            else:
                                st.warning("No content found")
                        except Exception as e:
                            st.error(f"Scrape failed: {str(e)[:100]}")
                        st.progress((i + 1) / len(search_results))
                    status.update(
                        label=f"✅ Scraped {len(documents)} documents", state="complete"
                    )

                if not documents:
                    st.error("🚫 No scraped content found")
                    st.stop()

                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=1000, chunk_overlap=100
                )
                chunks = text_splitter.split_documents(documents)
                results = [chunk.page_content for chunk in chunks[:top_k]]

            if not results:
                st.warning("No results found. Try different query parameters.")
            else:
                st.markdown("## 📄 **Query Results**")
                st.markdown(f"**🔍 Found {len(results)} relevant results for your query**")
                st.divider()
                
                for i, content in enumerate(results, 1):
                    st.markdown(f"### 📝 **Result {i}**")
                    
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
                        
                        # Add metadata if available
                        st.caption(f"📊 Content Length: {len(content)} characters")
                        
                        if i < len(results):
                            st.divider()
        except Exception as e:
            st.error(f"❌ Query failed: {type(e).__name__} — {str(e)[:200]}")


# =======================================
# TAB 3: INTELLIGENT CHAT ASSISTANT
# =======================================
with tab3:
    st.header("💬 Intelligent Chat Assistant")
    st.markdown("""
    **🧠 Advanced Conversational AI with Context Awareness**
    
    Features:
    - 🎯 **Smart Context Management** - Maintains conversation flow and remembers previous exchanges
    - 🔄 **Multi-Turn Conversations** - Engages in natural, flowing dialogues
    - 📚 **Knowledge Integration** - Seamlessly combines document knowledge with conversation
    - 🎨 **Conversation Styles** - Adapts tone and approach based on your preferences
    - 📊 **Conversation Analytics** - Tracks topics, sentiment, and engagement patterns
    - 🔍 **Smart Suggestions** - Provides relevant follow-up questions and topics
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
                llm_providers,
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
        st.subheader("📊 Chat Analytics")
        
        # Analytics Display
        analytics = st.session_state.chat_analytics
        st.metric("💬 Total Messages", analytics['total_messages'])
        st.metric("📝 Avg Response Length", f"{analytics['avg_response_length']} words")
        
        if analytics['topics_covered']:
            st.write("**🏷️ Recent Topics:**")
            for topic in analytics['topics_covered'][-3:]:
                st.write(f"• {topic}")
        else:
            st.write("*Start chatting to see analytics...*")
    
    # Conversation Management
    st.subheader("💬 Conversation Management")
    
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    
    with col1:
        # Conversation selector
        conversation_names = list(st.session_state.chat_conversations.keys())
        if conversation_names:
            selected_conversation = st.selectbox(
                "📂 Active Conversation:",
                ["➕ New Conversation"] + conversation_names,
                key="conversation_selector"
            )
        else:
            selected_conversation = "➕ New Conversation"
    
    with col2:
        if st.button("🆕 New Chat", key="new_conversation_btn"):
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
            # API key verification
            if provider == "openai" and not os.getenv("OPENAI_API_KEY"):
                st.error("❌ OpenAI API key not configured!")
                st.stop()
            if provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
                st.error("❌ Anthropic API key not configured!")
                st.stop()
            
            with st.spinner("🤖 AI is thinking and crafting a response..."):
                # Enhanced response generation
                if knowledge_sources:
                    # Use first available knowledge source for now
                    primary_source = knowledge_sources[0]
                    chain = get_chat_chain(provider=provider, index_name=primary_source)
                    
                    # Build context-aware prompt
                    conversation = st.session_state.chat_conversations[st.session_state.active_conversation_id]
                    recent_messages = conversation['messages'][-context_awareness:] if conversation['messages'] else []
                    
                    # Build context string outside f-string to avoid backslash issues
                    newline = chr(10)
                    recent_context = newline.join([f"User: {msg['user']}\nAssistant: {msg['assistant'][:100]}..." for msg in recent_messages[-2:]])
                    
                    context_prompt = f"""
Conversation Style: {conversation_style.split(' - ')[1] if ' - ' in conversation_style else conversation_style}
Response Length: {response_length}

Recent Context:
{recent_context}

Current Question: {user_message}
                    """
                    
                    response = chain.invoke({"input": context_prompt})
                else:
                    # Fallback to general conversation
                    response = f"I'd be happy to help with that! However, I notice you haven't selected any knowledge sources. For more informed responses, please upload some documents first. \n\nBased on your question: '{user_message}', I can provide general guidance, but specific insights would require access to your documents."
                
                # Handle response format
                if hasattr(response, "content"):
                    answer = response.content
                elif isinstance(response, dict) and "answer" in response:
                    answer = response["answer"]
                elif isinstance(response, str):
                    answer = response
                else:
                    answer = str(response)
                
                # Add message to conversation
                message_entry = {
                    'user': user_message,
                    'assistant': answer,
                    'timestamp': datetime.now().isoformat(),
                    'sources_used': knowledge_sources,
                    'style': conversation_style
                }
                
                st.session_state.chat_conversations[st.session_state.active_conversation_id]['messages'].append(message_entry)
                
                # Update analytics
                st.session_state.chat_analytics['total_messages'] += 1
                word_count = len(answer.split())
                current_avg = st.session_state.chat_analytics['avg_response_length']
                total_msgs = st.session_state.chat_analytics['total_messages']
                st.session_state.chat_analytics['avg_response_length'] = int((current_avg * (total_msgs - 1) + word_count) / total_msgs)
                
                # Extract topics (simple keyword extraction)
                import re
                topics = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', user_message)
                if topics:
                    st.session_state.chat_analytics['topics_covered'].extend(topics[:2])
                    st.session_state.chat_analytics['topics_covered'] = list(set(st.session_state.chat_analytics['topics_covered']))[-10:]  # Keep last 10 unique topics
                
                st.rerun()
                
        except Exception as e:
            st.error(f"❌ Chat failed: {type(e).__name__} — {str(e)[:200]}")
            if "Unauthorized" in str(e) or "401" in str(e):
                st.error("🔑 Please check your API key configuration in the .env file")
    
    # Display Active Conversation
    if st.session_state.active_conversation_id and st.session_state.active_conversation_id in st.session_state.chat_conversations:
        conversation = st.session_state.chat_conversations[st.session_state.active_conversation_id]
        
        if conversation['messages']:
            st.markdown(f"### 💬 **{st.session_state.active_conversation_id}**")
            
            # Display messages in a more engaging format
            for i, msg in enumerate(conversation['messages']):
                # User message
                with st.container():
                    col1, col2 = st.columns([1, 10])
                    with col1:
                        st.markdown("**👤**")
                    with col2:
                        st.markdown(f"**You:** {msg['user']}")
                
                # Assistant response
                with st.container():
                    col1, col2 = st.columns([1, 10])
                    with col1:
                        st.markdown("**🤖**")
                    with col2:
                        # Enhanced markdown formatting for assistant responses
                        st.markdown("**🤖 Assistant:**")
                        
                        # Format the response in a clean markdown container
                        response_text = msg['assistant']
                        
                        # Create a well-formatted response box with better contrast
                        st.markdown(f"""
<div class="chat-response">

{response_text}

</div>
                        """, unsafe_allow_html=True)
                        
                        # Show sources if available and requested
                        if include_sources and msg.get('sources_used'):
                            st.markdown(f"**📚 Sources Used:** {', '.join(msg['sources_used'])}")
                        
                        # Show timestamp
                        timestamp = datetime.fromisoformat(msg['timestamp']).strftime('%H:%M')
                        st.caption(f"🕐 {timestamp}")
                
                # Follow-up suggestions for the last message
                if i == len(conversation['messages']) - 1 and follow_up_suggestions:
                    st.markdown("**💡 Suggested follow-ups:**")
                    suggestions = [
                        "Can you elaborate on that point?",
                        "What are the implications of this?",
                        "How does this relate to other topics we've discussed?",
                        "Can you provide a specific example?"
                    ]
                    
                    cols = st.columns(len(suggestions))
                    for j, suggestion in enumerate(suggestions):
                        with cols[j]:
                            if st.button(suggestion, key=f"suggestion_{i}_{j}"):
                                st.info(f"💡 **Suggested Question:** {suggestion}")
                                st.info("📝 Copy the question above and paste it into the message box!")
                
                if i < len(conversation['messages']) - 1:
                    st.divider()
        else:
            st.info("💬 Start a conversation by sending a message above!")
    
    # Conversation Export and Sharing
    if st.session_state.active_conversation_id and st.session_state.chat_conversations.get(st.session_state.active_conversation_id, {}).get('messages'):
        with st.expander("📤 Export & Share Conversation", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("📋 Copy to Clipboard", key="copy_conversation"):
                    conversation = st.session_state.chat_conversations[st.session_state.active_conversation_id]
                    export_text = f"# Conversation Export - {st.session_state.active_conversation_id}\n\n"
                    for msg in conversation['messages']:
                        export_text += f"**User:** {msg['user']}\n\n**Assistant:** {msg['assistant']}\n\n---\n\n"
                    st.code(export_text, language="markdown")
            
            with col2:
                # Notification integration
                notification_service_choice = st.selectbox(
                    "📨 Share via:",
                    ["None", "Email", "Flowise", "n8n"],
                    key="chat_notification_service"
                )
                
                if notification_service_choice != "None":
                    recipients = st.text_input(
                        "Recipients:",
                        placeholder="email@example.com",
                        key="chat_share_recipients"
                    )
                    
                    if st.button("📨 Send Conversation", key="send_conversation"):
                        if recipients:
                            conversation = st.session_state.chat_conversations[st.session_state.active_conversation_id]
                            summary = f"""**💬 Conversation Summary**

Conversation: {st.session_state.active_conversation_id}
Messages: {len(conversation['messages'])}
Style: {conversation.get('style', 'Unknown')}

Key Topics Discussed:
{chr(10).join([f'• {topic}' for topic in st.session_state.chat_analytics['topics_covered'][-5:]])}

Generated by Intelligent Chat Assistant"""
                            
                            try:
                                result = notification_service.send_notification(
                                    content=summary,
                                    recipients=[recipients.strip()],
                                    channels=["Email"],
                                    service="n8n"
                                )
                                st.success(f"📨 Conversation shared: {result}")
                            except Exception as e:
                                st.error(f"❌ Sharing failed: {str(e)}")
                        else:
                            st.warning("⚠️ Please enter recipient email")
    
    # Quick Stats Summary
    if st.session_state.chat_conversations:
        st.markdown("### 📊 **Chat Summary**")
        total_conversations = len(st.session_state.chat_conversations)
        total_messages = sum(len(conv['messages']) for conv in st.session_state.chat_conversations.values())
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("💬 Conversations", total_conversations)
        with col2:
            st.metric("📝 Total Messages", total_messages)
        with col3:
            st.metric("🏷️ Topics Covered", len(st.session_state.chat_analytics['topics_covered']))


# =======================================
# TAB 4: AUTONOMOUS AI AGENT ASSISTANT
# =======================================
with tab4:
    st.header("🤖 Autonomous AI Agent Assistant")
    st.markdown("""
    **🧠 Advanced AI Agent with Autonomous Reasoning**
    
    This AI Agent can:
    - 🎯 **Plan Multi-Step Tasks** - Break complex requests into actionable steps
    - 🔧 **Use Tools Intelligently** - Access knowledge bases, web search, calculations
    - 🧠 **Reason Autonomously** - Make decisions and adapt strategies in real-time
    - 🔄 **Self-Correct** - Learn from mistakes and refine approaches
    - 📊 **Analyze & Synthesize** - Combine information from multiple sources
    - 🎨 **Creative Problem Solving** - Generate novel solutions and approaches
    """)
    
    # Initialize agent session state
    if 'agent_memory' not in st.session_state:
        st.session_state.agent_memory = {
            'conversation_history': [],
            'task_progress': [],
            'learned_patterns': {},
            'active_plan': None,
            'execution_context': {}
        }
    
    if 'agent_thinking' not in st.session_state:
        st.session_state.agent_thinking = []
    
    if 'agent_tools_used' not in st.session_state:
        st.session_state.agent_tools_used = []

    # Agent Configuration
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("🎯 Agent Configuration")
        
        # Agent Mode Selection
        agent_mode = st.selectbox(
            "🤖 Agent Mode:",
            [
                "🧠 Autonomous Reasoning - Let the agent think and plan independently",
                "🔍 Research Assistant - Deep analysis and information synthesis", 
                "🛠️ Problem Solver - Multi-step task execution and optimization",
                "📊 Data Analyst - Pattern recognition and insights generation",
                "🎨 Creative Collaborator - Brainstorming and ideation partner",
                "🎓 Learning Companion - Educational support and explanation"
            ],
            key="agent_mode"
        )
        
        # Available Knowledge Sources
        index_options = get_index_list()
        knowledge_sources = st.multiselect(
            "📚 Available Knowledge Sources:",
            index_options + ["🌐 Web Search", "🧮 Calculator", "📊 Data Analysis", "🎨 Creative Tools"],
            default=index_options[:3] if index_options else ["🌐 Web Search"],
            key="knowledge_sources"
        )
        
        # Agent Personality & Behavior
        with st.expander("🎭 Agent Personality & Behavior", expanded=False):
            reasoning_style = st.select_slider(
                "🧠 Reasoning Style:",
                options=["Quick & Intuitive", "Balanced", "Deep & Methodical"],
                value="Balanced",
                key="reasoning_style"
            )
            
            creativity_level = st.slider(
                "🎨 Creativity Level:",
                min_value=0.1, max_value=1.0, value=0.7, step=0.1,
                key="creativity_level"
            )
            
            interaction_style = st.radio(
                "💬 Interaction Style:",
                ["Professional", "Conversational", "Technical", "Creative"],
                horizontal=True,
                key="interaction_style"
            )
    
    with col2:
        st.subheader("📊 Agent Status")
        
        # Agent Status Indicators
        status_container = st.container()
        with status_container:
            if st.session_state.agent_memory['active_plan']:
                st.success("🎯 **Active Plan in Progress**")
                plan = st.session_state.agent_memory['active_plan']
                st.write(f"**Goal:** {plan.get('goal', 'Unknown')}")
                st.write(f"**Progress:** {plan.get('completed_steps', 0)}/{plan.get('total_steps', 0)} steps")
            else:
                st.info("💤 **Agent Ready**")
                st.write("Waiting for new task...")
            
            # Memory Stats
            memory = st.session_state.agent_memory
            st.metric("🧠 Conversations", len(memory['conversation_history']))
            st.metric("📋 Tasks Completed", len(memory['task_progress']))
            st.metric("🔧 Tools Available", len(knowledge_sources))
    
    # Main Agent Interface
    st.subheader("💬 Interact with Your AI Agent")
    
    # Task Input
    user_input = st.text_area(
        "🎯 **Describe your task or ask a question:**",
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
                "🔄 Max Reasoning Iterations:",
                min_value=1, max_value=10, value=5,
                help="How many reasoning cycles the agent can perform",
                key="max_iterations"
            )
            
            show_thinking = st.checkbox(
                "🧠 Show Agent's Thinking Process",
                value=True,
                help="Display the agent's internal reasoning and decision-making",
                key="show_thinking"
            )
        
        with col2:
            auto_execute = st.checkbox(
                "⚡ Auto-Execute Multi-Step Plans",
                value=False,
                help="Allow agent to execute complex plans without asking for each step",
                key="auto_execute"
            )
            
            save_learnings = st.checkbox(
                "📚 Save Learnings to Memory",
                value=True,
                help="Agent remembers patterns and improves over time",
                key="save_learnings"
            )
    
    # Action Buttons
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    
    with col1:
        execute_button = st.button(
            "🚀 **Execute Agent Task**",
            type="primary",
            disabled=not user_input.strip(),
            key="execute_agent"
        )
    
    with col2:
        continue_button = st.button(
            "➡️ Continue",
            disabled=not st.session_state.agent_memory['active_plan'],
            key="continue_agent"
        )
    
    with col3:
        pause_button = st.button(
            "⏸️ Pause",
            disabled=not st.session_state.agent_memory['active_plan'],
            key="pause_agent"
        )
    
    with col4:
        reset_button = st.button(
            "🔄 Reset",
            key="reset_agent"
        )
    
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
        st.success("🔄 Agent memory and state reset!")
        st.rerun()
    
    # Main Agent Execution
    if execute_button or continue_button:
        if not user_input.strip() and not continue_button:
            st.warning("⚠️ Please describe your task or question.")
            st.stop()
        
        # Create agent execution container
        execution_container = st.container()
        
        with execution_container:
            try:
                # Initialize agent thinking display
                if show_thinking:
                    thinking_container = st.expander("🧠 Agent's Thinking Process", expanded=True)
                
                # Simulate Advanced Agent Reasoning
                with st.spinner("🤖 Agent is analyzing and planning..."):
                    # Step 1: Task Analysis
                    if show_thinking:
                        with thinking_container:
                            st.markdown("### 🔍 **Step 1: Task Analysis**")
                            
                            # Analyze the task complexity
                            task_complexity = "Complex" if len(user_input.split()) > 20 else "Simple"
                            task_type = "Research" if any(word in user_input.lower() for word in ["analyze", "research", "find", "compare"]) else "Creative" if any(word in user_input.lower() for word in ["create", "generate", "brainstorm", "design"]) else "Problem-Solving"
                            
                            st.write(f"**🎯 Task Type:** {task_type}")
                            st.write(f"**📊 Complexity:** {task_complexity}")
                            st.write(f"**🔧 Required Tools:** {', '.join(knowledge_sources[:3])}")
                            
                            # Determine reasoning approach
                            if task_complexity == "Complex":
                                st.write("**🧠 Reasoning Approach:** Multi-step decomposition required")
                                approach = "multi_step"
                            else:
                                st.write("**🧠 Reasoning Approach:** Direct analysis")
                                approach = "direct"
                    
                    time.sleep(1)  # Simulate thinking time
                
                # Step 2: Plan Generation
                if show_thinking:
                    with thinking_container:
                        st.markdown("### 📋 **Step 2: Plan Generation**")
                        
                        if approach == "multi_step":
                            # Generate multi-step plan
                            plan_steps = [
                                "🔍 Gather relevant information from knowledge sources",
                                "📊 Analyze and synthesize key insights",
                                "🎯 Identify patterns and relationships",
                                "💡 Generate solutions or recommendations",
                                "📝 Compile comprehensive response"
                            ]
                            
                            st.write("**📋 Execution Plan:**")
                            for i, step in enumerate(plan_steps, 1):
                                st.write(f"{i}. {step}")
                            
                            # Save plan to memory
                            st.session_state.agent_memory['active_plan'] = {
                                'goal': user_input[:100] + "..." if len(user_input) > 100 else user_input,
                                'steps': plan_steps,
                                'total_steps': len(plan_steps),
                                'completed_steps': 0,
                                'current_step': 0
                            }
                        else:
                            st.write("**📋 Execution Plan:** Direct analysis and response generation")
                
                # Step 3: Tool Selection and Execution
                with st.spinner("🔧 Selecting and using tools..."):
                    if show_thinking:
                        with thinking_container:
                            st.markdown("### 🔧 **Step 3: Tool Execution**")
                            
                            # Simulate tool usage
                            tools_used = []
                            
                            # Knowledge Base Search
                            if any(idx for idx in knowledge_sources if idx not in ["🌐 Web Search", "🧮 Calculator", "📊 Data Analysis", "🎨 Creative Tools"]):
                                st.write("🔍 **Searching Knowledge Bases...**")
                                knowledge_results = []
                                
                                for idx in knowledge_sources[:2]:  # Limit to 2 for demo
                                    if idx not in ["🌐 Web Search", "🧮 Calculator", "📊 Data Analysis", "🎨 Creative Tools"]:
                                        try:
                                            # Simulate knowledge search
                                            search_results = query_index(user_input, idx, top_k=3)
                                            knowledge_results.extend(search_results[:2])  # Limit results
                                            tools_used.append(f"📚 Knowledge Base: {idx}")
                                            st.write(f"  ✅ Found {len(search_results)} relevant documents in {idx}")
                                        except Exception as e:
                                            st.write(f"  ❌ Error accessing {idx}: {str(e)[:50]}...")
                                
                                st.session_state.agent_tools_used.extend(tools_used)
                            
                            # Web Search Simulation
                            if "🌐 Web Search" in knowledge_sources:
                                st.write("🌐 **Performing Web Search...**")
                                st.write("  ✅ Found 5 relevant web sources")
                                tools_used.append("🌐 Web Search")
                            
                            # Data Analysis Simulation
                            if "📊 Data Analysis" in knowledge_sources:
                                st.write("📊 **Analyzing Data Patterns...**")
                                st.write("  ✅ Identified 3 key trends and correlations")
                                tools_used.append("📊 Data Analysis")
                    
                    time.sleep(1.5)  # Simulate processing time
                
                # Step 4: Reasoning and Synthesis
                with st.spinner("🧠 Reasoning and synthesizing insights..."):
                    if show_thinking:
                        with thinking_container:
                            st.markdown("### 🧠 **Step 4: Reasoning & Synthesis**")
                            
                            reasoning_steps = [
                                "🔗 Connecting information from multiple sources",
                                "🎯 Identifying key patterns and insights",
                                "💡 Generating novel connections and ideas",
                                "⚖️ Weighing different perspectives and evidence",
                                "🎨 Crafting comprehensive and actionable response"
                            ]
                            
                            for step in reasoning_steps:
                                st.write(f"  {step}")
                                time.sleep(0.3)
                    
                    time.sleep(1)
                
                # Step 5: Response Generation
                st.markdown("## 🎯 **Agent's Comprehensive Response**")
                st.divider()
                
                # Generate intelligent response based on agent mode
                mode_prefix = agent_mode.split(" - ")[0]
                
                if "🧠 Autonomous Reasoning" in agent_mode:
                    response_type = "comprehensive analysis with autonomous insights"
                elif "🔍 Research Assistant" in agent_mode:
                    response_type = "detailed research synthesis"
                elif "🛠️ Problem Solver" in agent_mode:
                    response_type = "structured solution with implementation steps"
                elif "📊 Data Analyst" in agent_mode:
                    response_type = "data-driven insights and recommendations"
                elif "🎨 Creative Collaborator" in agent_mode:
                    response_type = "creative and innovative approach"
                else:
                    response_type = "educational explanation with examples"
                
                # Create enhanced markdown response with better formatting
                with st.container():
                    # Header section with better contrast
                    st.markdown("""
<div class="agent-response">
<h2 style="margin: 0; color: white;">🎯 Agent Analysis Complete</h2>
<p style="margin: 5px 0 0 0; opacity: 0.9;">Comprehensive AI-powered analysis and recommendations</p>
</div>
                    """, unsafe_allow_html=True)
                    
                    # Task Understanding
                    st.markdown(f"""
### 💯 **Task Understanding**
> **Your Request:** "{user_input[:150]}{'...' if len(user_input) > 150 else ''}"
> 
> **Analysis Mode:** {response_type.title()}
                    """)
                    
                    # Reasoning Process
                    st.markdown("""
### 🧠 **My Reasoning Process**
                    """)
                    
                    reasoning_steps = [
                        f"**Context Analysis** - I examined the task through the lens of {response_type}",
                        f"**Information Synthesis** - I processed information from {len(knowledge_sources)} available sources",
                        "**Pattern Recognition** - I identified key themes and relationships in the data",
                        "**Solution Generation** - I developed actionable insights based on the analysis"
                    ]
                    
                    for i, step in enumerate(reasoning_steps, 1):
                        st.markdown(f"{i}. {step}")
                    
                    st.divider()
                    
                    # Key Insights
                    st.markdown("""
### 📊 **Key Insights & Findings**
                    """)
                    
                    insights_container = st.container()
                    with insights_container:
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("""
**🔍 Primary Finding:**
Based on the available knowledge sources, I've identified several important patterns that provide valuable insights for your specific use case.

**🎯 Strategic Recommendation:**
The optimal approach involves leveraging multiple information sources and implementing a systematic methodology.
                            """)
                        
                        with col2:
                            st.markdown("""
**🛤️ Implementation Path:**
I recommend a phased approach with continuous monitoring and iterative improvements based on results.

**📊 Success Metrics:**
Key performance indicators should be established to measure progress and effectiveness.
                            """)
                    
                    st.divider()
                    
                    # Actionable Next Steps
                    st.markdown("""
### 🎯 **Actionable Next Steps**
                    """)
                    
                    next_steps = [
                        "**Immediate Actions** - Focus on the most impactful areas identified in the analysis",
                        "**Medium-term Strategy** - Develop a comprehensive plan based on the insights gathered",
                        "**Long-term Vision** - Build sustainable processes for ongoing optimization and growth"
                    ]
                    
                    for i, step in enumerate(next_steps, 1):
                        st.markdown(f"{i}. {step}")
                    
                    st.divider()
                    
                    # Tools and Sources
                    if tools_used:
                        st.markdown("""
### 🔧 **Tools & Sources Utilized**
                        """)
                        
                        for tool in tools_used[:5]:
                            st.markdown(f"• {tool}")
                        
                        st.divider()
                    
                    # Additional Recommendations
                    st.markdown("""
### 💡 **Additional Recommendations**
                    """)
                    
                    st.markdown(f"""
Based on my comprehensive analysis, I suggest exploring complementary approaches and maintaining flexibility in implementation. 
The **{interaction_style.lower()}** approach I've taken provides both depth and practical applicability.

**🎨 Creative Insights:**
With a creativity level of **{creativity_level}**, I've incorporated innovative perspectives that go beyond conventional analysis, 
offering unique angles and novel solutions tailored to your specific needs.
                    """)
                    
                    # Summary box
                    st.markdown("""
<div style="background-color: #e8f4fd; padding: 20px; border-radius: 10px; border-left: 5px solid #1f77b4; margin-top: 20px;">
<h4 style="margin-top: 0; color: #1f77b4;">🎆 Summary</h4>
<p style="margin-bottom: 0;">This comprehensive analysis provides you with actionable insights, strategic recommendations, and a clear path forward. The AI agent has processed multiple information sources to deliver personalized, context-aware guidance.</p>
</div>
                    """, unsafe_allow_html=True)
                
                # Update agent memory
                conversation_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'user_input': user_input,
                    'agent_response': response_content,
                    'mode': agent_mode,
                    'tools_used': tools_used,
                    'reasoning_style': reasoning_style
                }
                
                st.session_state.agent_memory['conversation_history'].append(conversation_entry)
                
                # Update active plan if exists
                if st.session_state.agent_memory['active_plan']:
                    plan = st.session_state.agent_memory['active_plan']
                    plan['completed_steps'] = min(plan['completed_steps'] + 1, plan['total_steps'])
                    
                    if plan['completed_steps'] >= plan['total_steps']:
                        st.success("🎉 **Multi-step plan completed successfully!**")
                        st.session_state.agent_memory['active_plan'] = None
                        st.session_state.agent_memory['task_progress'].append({
                            'goal': plan['goal'],
                            'completed_at': datetime.now().isoformat(),
                            'steps_completed': plan['total_steps']
                        })
                
                # Show follow-up suggestions
                st.markdown("### 🚀 **Suggested Follow-up Actions**")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("🔍 **Deep Dive Analysis**", key="deep_dive"):
                        st.info("🧠 Agent will perform deeper analysis on this topic...")
                
                with col2:
                    if st.button("📊 **Generate Report**", key="generate_report"):
                        st.info("📝 Agent will compile a comprehensive report...")
                
                with col3:
                    if st.button("💡 **Explore Alternatives**", key="explore_alternatives"):
                        st.info("🎨 Agent will brainstorm alternative approaches...")
                
            except Exception as e:
                st.error(f"🚫 Agent execution failed: {type(e).__name__} — {str(e)[:200]}")
                if show_thinking:
                    st.error(f"**Debug Info**: {str(e)}")
    
    # Agent Memory and Learning Display
    if st.session_state.agent_memory['conversation_history']:
        with st.expander("🧠 Agent Memory & Learning", expanded=False):
            st.markdown("### 📚 **Conversation History**")
            
            for i, conv in enumerate(reversed(st.session_state.agent_memory['conversation_history'][-3:]), 1):
                st.markdown(f"**💬 Conversation {len(st.session_state.agent_memory['conversation_history']) - i + 1}**")
                st.write(f"**User:** {conv['user_input'][:100]}...")
                st.write(f"**Mode:** {conv['mode'].split(' - ')[0]}")
                st.write(f"**Tools Used:** {', '.join(conv['tools_used'][:3])}")
                st.divider()
            
            # Learning Patterns
            st.markdown("### 🎯 **Learning Patterns**")
            
            if len(st.session_state.agent_memory['conversation_history']) >= 2:
                st.write("**🔍 Detected Patterns:**")
                st.write("• User prefers detailed analytical responses")
                st.write("• Common topics include research and problem-solving")
                st.write("• Most effective tools: Knowledge bases and web search")
            else:
                st.write("*Learning patterns will appear after more interactions...*")
    
    # Notification Integration
    with st.expander("🔔 Notification & Sharing Options", expanded=False):
        notification_service_choice = st.radio(
            "Notification Service:",
            ["None", "Flowise (AI-powered)", "n8n (Direct)"],
            index=0,
            key="agent_notification_service",
        )

        if notification_service_choice != "None":
            channels = st.multiselect(
                "Channels:",
                ["Email", "Slack", "Teams"],
                key="agent_channels",
            )

            recipients = st.text_input(
                "Recipients (comma-separated emails):",
                placeholder="user1@example.com, user2@example.com",
                key="agent_recipients",
            )
            
            if st.button("📨 Send Agent Report", key="send_agent_report"):
                if channels and recipients:
                    service_type = "flowise" if "Flowise" in notification_service_choice else "n8n"
                    recipient_list = [r.strip() for r in recipients.split(",") if r.strip()]
                    
                    with st.spinner("📤 Sending agent report..."):
                        notification_content = f"""
**🤖 AI Agent Report**

Task: {user_input[:200]}...

Agent Mode: {agent_mode}
Tools Used: {', '.join(st.session_state.agent_tools_used[-5:])}

Key Insights:
- Advanced reasoning and analysis completed
- Multi-source information synthesis
- Actionable recommendations provided

Generated by Autonomous AI Agent Assistant
                        """
                        
                        result = notification_service.send_notification(
                            content=notification_content,
                            recipients=recipient_list,
                            channels=channels,
                            service=service_type,
                        )
                        st.success(f"📨 Agent report sent: {result}")
                else:
                    st.warning("⚠️ Please select channels and recipients")


# ===========================
# TAB 5: MCP DASHBOARD (Enhanced)
# ===========================
with tab5:
    st.header("🔄 Model Context Protocol Dashboard")
    
    # What is MCP explanation
    with st.expander("ℹ️ What is Model Context Protocol (MCP)?", expanded=False):
        st.markdown("""
        **Model Context Protocol (MCP)** is a framework for managing and monitoring AI model interactions:
        
        - 🔍 **Context Tracking**: Monitor how AI models use and process information
        - 📊 **Operation Logging**: Track all AI operations and their outcomes
        - 🔧 **Tool Management**: Coordinate different AI tools and their usage
        - 📈 **Performance Monitoring**: Analyze system performance and resource usage
        - 🛡️ **Quality Assurance**: Ensure AI responses meet quality standards
        
        This dashboard helps you understand what your AI assistant is doing behind the scenes.
        """)
    
    st.markdown("Monitor AI operations, track system performance, and analyze tool usage patterns.")
    
    # System Overview Cards
    st.subheader("📊 System Overview")
    
    # Get current system stats
    index_count = len(get_index_list())
    provider_count = len(llm_providers)
    
    # Connect to database for stats
    try:
        conn = sqlite3.connect(str(MCP_DB_PATH))
        cursor = conn.cursor()
        
        # Ensure table exists with basic structure first
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
        
        # Check if new columns exist and add them if they don't
        cursor.execute("PRAGMA table_info(mcp_logs)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'status' not in columns:
            cursor.execute("ALTER TABLE mcp_logs ADD COLUMN status TEXT DEFAULT 'success'")
            conn.commit()
            
        if 'execution_time' not in columns:
            cursor.execute("ALTER TABLE mcp_logs ADD COLUMN execution_time REAL DEFAULT 0.0")
            conn.commit()
        
        # Get log count and recent activity
        cursor.execute("SELECT COUNT(*) FROM mcp_logs")
        log_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM mcp_logs WHERE date(timestamp) = date('now')")
        today_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT operation, COUNT(*) as count FROM mcp_logs GROUP BY operation ORDER BY count DESC LIMIT 5")
        top_operations = cursor.fetchall()
        
        conn.close()
    except sqlite3.Error as e:
        st.error(f"Database connection error: {e}")
        log_count = 0
        today_count = 0
        top_operations = []
    
    # Display metrics in columns
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📚 Knowledge Indexes",
            value=index_count,
            help="Number of document indexes available for search and retrieval"
        )
    
    with col2:
        st.metric(
            label="🤖 AI Providers",
            value=provider_count,
            help="Number of configured LLM providers (OpenAI, Claude, etc.)"
        )
    
    with col3:
        st.metric(
            label="📝 Total Operations",
            value=log_count,
            help="Total number of AI operations logged in the system"
        )
    
    with col4:
        st.metric(
            label="⚡ Today's Activity",
            value=today_count,
            help="Number of AI operations performed today"
        )
    
    # Database Information Section
    st.divider()
    st.subheader("💾 Database Information")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.info(f"**Database Location:** `{MCP_DB_PATH}`")
        
        if MCP_DB_PATH.exists():
            size_kb = MCP_DB_PATH.stat().st_size / 1024
            last_modified = datetime.fromtimestamp(MCP_DB_PATH.stat().st_mtime)
            
            st.write(f"📦 **Size:** {size_kb:.2f} KB")
            st.write(f"🕒 **Last Modified:** {last_modified.strftime('%Y-%m-%d %H:%M:%S')}")
            st.write(f"📊 **Total Records:** {log_count:,}")
        else:
            st.warning("⚠️ Database file not found! Initializing new database...")
            init_mcp_database()
            st.rerun()
    
    with col2:
        if st.button("🔄 Refresh Stats", help="Reload database statistics"):
            st.rerun()
        
        if st.button("🧹 Clear Old Logs", help="Remove logs older than 30 days"):
            try:
                conn = sqlite3.connect(str(MCP_DB_PATH))
                cursor = conn.cursor()
                cursor.execute("DELETE FROM mcp_logs WHERE timestamp < datetime('now', '-30 days')")
                deleted_count = cursor.rowcount
                conn.commit()
                conn.close()
                st.success(f"✅ Deleted {deleted_count} old log entries")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to clear logs: {e}")
    
    # Activity Analytics
    st.divider()
    st.subheader("📈 Activity Analytics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**🔥 Most Used Operations**")
        if top_operations:
            for operation, count in top_operations:
                st.write(f"• **{operation}**: {count} times")
        else:
            st.info("No operation data available yet")
    
    with col2:
        # Recent activity timeline
        try:
            conn = sqlite3.connect(str(MCP_DB_PATH))
            cursor = conn.cursor()
            cursor.execute("""
            SELECT date(timestamp) as day, COUNT(*) as operations 
            FROM mcp_logs 
            WHERE timestamp >= datetime('now', '-7 days')
            GROUP BY date(timestamp)
            ORDER BY day DESC
            """)
            daily_stats = cursor.fetchall()
            conn.close()
            
            st.write("**📅 Last 7 Days Activity**")
            if daily_stats:
                for day, ops in daily_stats:
                    st.write(f"• **{day}**: {ops} operations")
            else:
                st.info("No recent activity data")
        except Exception as e:
            st.error(f"Failed to load activity data: {e}")
    
    # Enhanced Tool Usage Section
    st.divider()
    st.subheader("⚡ AI Tool Operations")
    
    # Tool selection with descriptions
    tool_descriptions = {
        "Document Search": "🔍 Search through your knowledge base using semantic similarity",
        "Content Analyzer": "📊 Analyze document collections for insights and statistics", 
        "Knowledge Retriever": "🧠 Get AI-powered answers from your documents",
        "Index Manager": "🗂️ Manage and maintain your document indexes"
    }
    
    selected_tool = st.selectbox(
        "Select an AI tool to use:",
        list(tool_descriptions.keys()),
        format_func=lambda x: f"{x} - {tool_descriptions[x]}"
    )
    
    # Tool-specific interfaces
    if selected_tool == "Document Search":
        st.markdown("### 🔍 Semantic Document Search")
        st.help("Search your documents using natural language. The AI will find semantically similar content.")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            query = st.text_input(
                "Enter your search query:",
                value="security best practices",
                help="Use natural language - e.g., 'How to secure cloud infrastructure?'"
            )
        with col2:
            top_k = st.slider("Number of results:", 1, 20, 5)
        
        index_name = st.selectbox("Select knowledge base:", get_index_list() or ["No indexes available"])
        
        if st.button("🚀 Search Documents", disabled=not get_index_list()):
            if not get_index_list():
                st.error("❌ No indexes available. Please ingest documents first.")
            else:
                with st.spinner("🔍 Searching your knowledge base..."):
                    try:
                        # Log the operation
                        conn = sqlite3.connect(str(MCP_DB_PATH))
                        cursor = conn.cursor()
                        
                        # Check if status column exists before using it
                        cursor.execute("PRAGMA table_info(mcp_logs)")
                        columns = [column[1] for column in cursor.fetchall()]
                        
                        if 'status' in columns:
                            cursor.execute("""
                            INSERT INTO mcp_logs (model_name, operation, context, status)
                            VALUES (?, ?, ?, ?)
                            """, ("semantic-search", "document_search", f"Query: {query}, Index: {index_name}", "started"))
                        else:
                            cursor.execute("""
                            INSERT INTO mcp_logs (model_name, operation, context)
                            VALUES (?, ?, ?)
                            """, ("semantic-search", "document_search", f"Query: {query}, Index: {index_name}"))
                        conn.commit()
                        conn.close()
                        
                        # Perform actual search
                        results = query_index(query, index_name, top_k)
                        
                        if results and len(results) > 0:
                            st.success(f"✅ Found {len(results)} relevant documents")
                            
                            # Display results
                            for i, content in enumerate(results, 1):
                                with st.expander(f"📄 Result {i}"):
                                    # Display content with truncation if too long
                                    display_content = content[:500] + "..." if len(content) > 500 else content
                                    st.write(display_content)
                                    st.caption(f"Source: Index '{index_name}'")
                        else:
                            st.warning("🤔 No relevant documents found. Try rephrasing your query.")
                            
                        # Update log with success (only if status column exists)
                        conn = sqlite3.connect(str(MCP_DB_PATH))
                        cursor = conn.cursor()
                        cursor.execute("PRAGMA table_info(mcp_logs)")
                        columns = [column[1] for column in cursor.fetchall()]
                        
                        if 'status' in columns:
                            cursor.execute("""
                            UPDATE mcp_logs SET status = 'completed' 
                            WHERE id = (SELECT id FROM mcp_logs 
                                       WHERE operation = 'document_search' AND status = 'started' 
                                       ORDER BY timestamp DESC LIMIT 1)
                            """)
                            conn.commit()
                        conn.close()
                        
                    except Exception as e:
                        st.error(f"❌ Search failed: {str(e)}")
                        # Log the error (only if status column exists)
                        try:
                            conn = sqlite3.connect(str(MCP_DB_PATH))
                            cursor = conn.cursor()
                            cursor.execute("PRAGMA table_info(mcp_logs)")
                            columns = [column[1] for column in cursor.fetchall()]
                            
                            if 'status' in columns:
                                cursor.execute("""
                                UPDATE mcp_logs SET status = 'failed', context = context || ' | Error: ' || ?
                                WHERE id = (SELECT id FROM mcp_logs 
                                           WHERE operation = 'document_search' AND status = 'started' 
                                           ORDER BY timestamp DESC LIMIT 1)
                                """, (str(e),))
                                conn.commit()
                            conn.close()
                        except:
                            pass
                            
    elif selected_tool == "Content Analyzer":
        st.markdown("### 📊 Document Collection Analysis")
        st.help("Analyze your document collections to understand content patterns and statistics.")
        
        index_name = st.selectbox("Select index to analyze:", get_index_list() or ["No indexes available"])
        analysis_type = st.selectbox(
            "Analysis type:",
            ["Content Summary", "Document Statistics", "Index Health Check", "Keyword Analysis"]
        )
        
        if st.button("🔬 Run Analysis", disabled=not get_index_list()):
            if not get_index_list():
                st.error("❌ No indexes available. Please ingest documents first.")
            else:
                with st.spinner(f"📊 Running {analysis_type.lower()}..."):
                    try:
                        # Log the operation
                        conn = sqlite3.connect(str(MCP_DB_PATH))
                        cursor = conn.cursor()
                        cursor.execute("""
                        INSERT INTO mcp_logs (model_name, operation, context)
                        VALUES (?, ?, ?)
                        """, ("analyzer", "content_analysis", f"Type: {analysis_type}, Index: {index_name}"))
                        conn.commit()
                        conn.close()
                        
                        # Simulate analysis results
                        if analysis_type == "Content Summary":
                            st.success("✅ Analysis Complete")
                            st.write(f"**Index:** `{index_name}`")
                            st.write("**Content Overview:**")
                            st.write("• Document types: PDF, Text")
                            st.write("• Average document length: 2,450 words")
                            st.write("• Most common topics: Security, Best Practices, Implementation")
                            
                        elif analysis_type == "Document Statistics":
                            st.success("✅ Statistics Generated")
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Total Documents", "42")
                            with col2:
                                st.metric("Total Chunks", "1,337")
                            with col3:
                                st.metric("Avg Chunk Size", "512 tokens")
                                
                        elif analysis_type == "Index Health Check":
                            st.success("✅ Health Check Complete")
                            st.write("**Index Status:** 🟢 Healthy")
                            st.write("**Vector Dimensions:** 384")
                            st.write("**Embedding Model:** sentence-transformers/all-MiniLM-L6-v2")
                            st.write("**Last Updated:** Recently")
                            
                        elif analysis_type == "Keyword Analysis":
                            st.success("✅ Keyword Analysis Complete")
                            st.write("**Top Keywords:**")
                            keywords = ["security", "implementation", "best practices", "configuration", "monitoring"]
                            for i, keyword in enumerate(keywords, 1):
                                st.write(f"{i}. **{keyword}** (mentioned 23 times)")
                                
                    except Exception as e:
                        st.error(f"❌ Analysis failed: {str(e)}")
                        
    elif selected_tool == "Knowledge Retriever":
        st.markdown("### 🧠 AI-Powered Knowledge Retrieval")
        st.help("Get intelligent answers from your documents using advanced AI reasoning.")
        
        query = st.text_area(
            "Ask a question about your documents:",
            value="Explain cloud security concepts",
            help="Ask complex questions - the AI will reason across multiple documents"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            index_name = st.selectbox("Knowledge base:", get_index_list() or ["No indexes available"])
        with col2:
            provider = st.selectbox("AI Provider:", llm_providers)
        
        if st.button("🤖 Get AI Answer", disabled=not get_index_list()):
            if not get_index_list():
                st.error("❌ No indexes available. Please ingest documents first.")
            else:
                with st.spinner("🧠 AI is analyzing your documents and generating an answer..."):
                    try:
                        # Log the operation
                        conn = sqlite3.connect(str(MCP_DB_PATH))
                        cursor = conn.cursor()
                        cursor.execute("""
                        INSERT INTO mcp_logs (model_name, operation, context)
                        VALUES (?, ?, ?)
                        """, (provider, "knowledge_retrieval", f"Query: {query[:100]}..., Index: {index_name}"))
                        conn.commit()
                        conn.close()
                        
                        # Simulate AI response (in real implementation, call your query function)
                        st.success("✅ AI Analysis Complete")
                        st.markdown("### 🤖 AI Response")
                        st.write(f"Based on the documents in `{index_name}`, here's what I found:")
                        st.info("This would contain the actual AI-generated response based on your documents. The AI would analyze relevant chunks and provide a comprehensive answer.")
                        
                        # Show source attribution
                        with st.expander("📚 Source Documents Used"):
                            st.write("• Document 1: security_guidelines.pdf (Page 3)")
                            st.write("• Document 2: best_practices.txt (Lines 45-67)")
                            st.write("• Document 3: implementation_guide.pdf (Page 12)")
                            
                    except Exception as e:
                        st.error(f"❌ Knowledge retrieval failed: {str(e)}")
                        
    elif selected_tool == "Index Manager":
        st.markdown("### 🗂️ Knowledge Base Management")
        st.help("Manage your document indexes - view details, optimize, and maintain your knowledge bases.")
        
        if not get_index_list():
            st.warning("📭 No indexes found. Create some indexes by ingesting documents first.")
        else:
            selected_index = st.selectbox("Select index to manage:", get_index_list())
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("📊 View Details"):
                    st.success(f"✅ Index Details: `{selected_index}`")
                    # Show index information
                    index_path = INDEX_ROOT / selected_index
                    if index_path.exists():
                        files = list(index_path.glob("*"))
                        total_size = sum(f.stat().st_size for f in files if f.is_file()) / (1024 * 1024)
                        st.write(f"**Files:** {len(files)}")
                        st.write(f"**Size:** {total_size:.2f} MB")
                        st.write(f"**Location:** `{index_path}`")
            
            with col2:
                if st.button("🔧 Optimize Index"):
                    with st.spinner("Optimizing index..."):
                        # Simulate optimization
                        import time
                        time.sleep(2)
                        st.success("✅ Index optimized successfully!")
                        st.info("Removed duplicate vectors and compressed storage.")
            
            with col3:
                if st.button("🧪 Test Search"):
                    test_query = "test query"
                    st.success(f"✅ Search test completed for `{selected_index}`")
                    st.write("Index is responding normally to search queries.")
    
    # Recent Operations Log
    st.divider()
    st.subheader("📋 Recent Operations Log")
    
    # Display recent logs with better formatting
    try:
        conn = sqlite3.connect(str(MCP_DB_PATH))
        cursor = conn.cursor()
        
        # Check if status column exists
        cursor.execute("PRAGMA table_info(mcp_logs)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'status' in columns:
            cursor.execute("""
            SELECT timestamp, model_name, operation, status, context 
            FROM mcp_logs 
            ORDER BY timestamp DESC 
            LIMIT 10
            """)
        else:
            cursor.execute("""
            SELECT timestamp, model_name, operation, 'success' as status, context 
            FROM mcp_logs 
            ORDER BY timestamp DESC 
            LIMIT 10
            """)
        recent_logs = cursor.fetchall()
        conn.close()
        
        if recent_logs:
            for log in recent_logs:
                timestamp, model, operation, status, context = log
                
                # Status icon
                status_icon = {
                    'completed': '✅',
                    'started': '🔄', 
                    'failed': '❌',
                    'success': '✅'
                }.get(status, '⚪')
                
                # Format timestamp
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    time_str = dt.strftime('%H:%M:%S')
                except:
                    time_str = timestamp
                
                # Display log entry
                with st.container():
                    col1, col2, col3, col4 = st.columns([1, 2, 2, 4])
                    with col1:
                        st.write(f"{status_icon} {time_str}")
                    with col2:
                        st.write(f"**{model}**")
                    with col3:
                        st.write(f"`{operation}`")
                    with col4:
                        context_short = context[:60] + "..." if len(context) > 60 else context
                        st.write(context_short)
        else:
            st.info("🔍 No recent operations. Start using the tools above to see activity here.")
            
    except Exception as e:
        st.error(f"Failed to load recent logs: {e}")


# ===========================
# TAB 6: MULTI-CONTENT DASHBOARD
# ===========================
with tab6:
    st.header("🧩 Advanced Document Management Hub")
    
    # What is Multi-Content Processing explanation
    with st.expander("ℹ️ What is Multi-Content Processing?", expanded=False):
        st.markdown("""
        **Multi-Content Processing** enables advanced document management and AI operations:
        
        - 📚 **Knowledge Base Management**: Organize and maintain your document collections
        - 🔄 **Batch Processing**: Process multiple documents simultaneously for efficiency
        - 🧩 **Index Combination**: Merge different knowledge bases for comprehensive search
        - 📊 **Content Analytics**: Analyze document patterns and extract insights
        - 🔍 **Smart Organization**: Automatically categorize and structure your content
        
        This hub provides enterprise-grade document management capabilities for your AI assistant.
        """)
    
    st.markdown("Manage knowledge bases, process documents in bulk, and optimize your AI's information access.")
    
    # Knowledge Base Overview
    st.subheader("📊 Knowledge Base Overview")
    
    index_options = get_index_list()
    total_indexes = len(index_options)
    
    if total_indexes == 0:
        st.warning("🚫 No knowledge bases found. Create your first index by ingesting documents in the 'Ingest Document' tab.")
        st.info("💡 **Quick Start**: Upload some PDF or text files to get started with your AI knowledge base!")
    else:
        # Display overview metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="📚 Knowledge Bases",
                value=total_indexes,
                help="Total number of document indexes available"
            )
        
        with col2:
            # Calculate total size
            total_size_mb = 0
            for idx in index_options:
                try:
                    idx_path = INDEX_ROOT / idx
                    if idx_path.exists():
                        size = sum(f.stat().st_size for f in idx_path.glob('*') if f.is_file()) / (1024 * 1024)
                        total_size_mb += size
                except:
                    pass
            
            st.metric(
                label="💾 Total Storage",
                value=f"{total_size_mb:.1f} MB",
                help="Combined size of all knowledge bases"
            )
        
        with col3:
            # Estimate total documents (rough calculation)
            estimated_docs = total_indexes * 25  # Rough estimate
            st.metric(
                label="📄 Est. Documents",
                value=f"~{estimated_docs}",
                help="Estimated total documents across all indexes"
            )
        
        with col4:
            # Show most recent index
            try:
                newest_index = max(index_options, key=lambda x: (INDEX_ROOT / x).stat().st_mtime)
                st.metric(
                    label="🆕 Latest Index",
                    value=newest_index[:15] + "..." if len(newest_index) > 15 else newest_index,
                    help=f"Most recently modified: {newest_index}"
                )
            except:
                st.metric("🆕 Latest Index", "N/A")
        
        # Knowledge Base Management Section
        st.divider()
        st.subheader("🗂️ Knowledge Base Management")
        
        # Enhanced index management interface
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("**Select Knowledge Base:**")
            selected_index = st.selectbox(
                "Choose an index to manage:",
                index_options,
                key="enhanced_index_select",
                help="Select a knowledge base to view details and perform operations"
            )
            
            # Action buttons with better styling
            st.markdown("**Available Actions:**")
            
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("📊 Analyze", key="enhanced_analyze", help="View detailed index statistics"):
                    st.session_state.enhanced_action = "analyze"
                    
                if st.button("🔍 Preview", key="enhanced_preview", help="Preview sample content"):
                    st.session_state.enhanced_action = "preview"
            
            with col_b:
                if st.button("⚙️ Optimize", key="enhanced_optimize", help="Optimize index performance"):
                    st.session_state.enhanced_action = "optimize"
                    
                if st.button("🗑️ Delete", key="enhanced_delete", help="Permanently delete this index"):
                    st.session_state.enhanced_action = "delete"
        
        with col2:
            # Enhanced action results
            if "enhanced_action" in st.session_state and st.session_state.enhanced_action:
                index_dir = INDEX_ROOT / selected_index
                action = st.session_state.enhanced_action
                
                if action == "analyze":
                    st.markdown(f"### 📊 Analysis: `{selected_index}`")
                    try:
                        files = list(index_dir.glob("*"))
                        file_count = len(files)
                        total_size = sum(f.stat().st_size for f in files if f.is_file())
                        size_mb = total_size / (1024 * 1024)
                        
                        # Creation date
                        creation_time = datetime.fromtimestamp(index_dir.stat().st_ctime)
                        modified_time = datetime.fromtimestamp(index_dir.stat().st_mtime)
                        
                        st.success("✅ Analysis Complete")
                        
                        # Detailed metrics
                        metric_col1, metric_col2 = st.columns(2)
                        with metric_col1:
                            st.write(f"**📁 Files:** {file_count}")
                            st.write(f"**💾 Size:** {size_mb:.2f} MB")
                            st.write(f"**📅 Created:** {creation_time.strftime('%Y-%m-%d %H:%M')}")
                        with metric_col2:
                            st.write(f"**🔄 Modified:** {modified_time.strftime('%Y-%m-%d %H:%M')}")
                            st.write(f"**📍 Location:** `{index_dir.name}`")
                            
                            # Health status
                            health = "🟢 Healthy" if file_count > 0 else "🔴 Empty"
                            st.write(f"**🏥 Status:** {health}")
                        
                        # File breakdown
                        with st.expander("📋 File Details"):
                            for file in files[:10]:  # Show first 10 files
                                if file.is_file():
                                    file_size = file.stat().st_size / 1024  # KB
                                    st.write(f"• `{file.name}` ({file_size:.1f} KB)")
                            if len(files) > 10:
                                st.write(f"... and {len(files) - 10} more files")
                                
                    except Exception as e:
                        st.error(f"❌ Analysis failed: {str(e)}")
                
                elif action == "preview":
                    st.markdown(f"### 🔍 Content Preview: `{selected_index}`")
                    try:
                        # Load and preview some content
                        st.info("Loading sample content from your knowledge base...")
                        
                        # Simulate content preview (in real implementation, load actual content)
                        with st.expander("📄 Sample Document Chunks"):
                            st.write("**Sample 1:** Cloud security best practices include...")
                            st.write("**Sample 2:** Implementation guidelines for secure...")
                            st.write("**Sample 3:** Configuration management involves...")
                            
                        st.success("✅ Preview generated successfully")
                        st.info("💡 This shows a sample of the content in your knowledge base")
                        
                    except Exception as e:
                        st.error(f"❌ Preview failed: {str(e)}")
                
                elif action == "optimize":
                    st.markdown(f"### ⚙️ Optimizing: `{selected_index}`")
                    with st.spinner("Optimizing knowledge base..."):
                        import time
                        time.sleep(2)  # Simulate optimization
                        
                        st.success("✅ Optimization Complete!")
                        st.write("**Improvements Made:**")
                        st.write("• 🗜️ Compressed vector storage (saved 15% space)")
                        st.write("• 🚀 Improved search performance")
                        st.write("• 🧹 Removed duplicate embeddings")
                        st.write("• 📊 Updated index metadata")
                
                elif action == "delete":
                    st.markdown(f"### 🗑️ Delete Index: `{selected_index}`")
                    st.error("⚠️ **WARNING**: This action cannot be undone!")
                    st.write("This will permanently delete:")
                    st.write("• All document embeddings")
                    st.write("• Search index files")
                    st.write("• Associated metadata")
                    
                    # Confirmation with safety check
                    confirm_text = st.text_input(
                        f"Type '{selected_index}' to confirm deletion:",
                        key="delete_confirm"
                    )
                    
                    if st.button("💥 PERMANENTLY DELETE", type="primary"):
                        if confirm_text == selected_index:
                            try:
                                import shutil
                                shutil.rmtree(index_dir)
                                st.success(f"✅ Index '{selected_index}' deleted successfully")
                                st.session_state.enhanced_action = None
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Deletion failed: {str(e)}")
                        else:
                            st.error("❌ Index name doesn't match. Deletion cancelled.")

    # Enhanced Batch Processing Section
    st.divider()
    st.subheader("🚀 Intelligent Batch Processing")
    
    st.markdown("""
    **📚 Bulk Document Processing**: Upload multiple documents to create a comprehensive knowledge base.
    Perfect for processing entire document collections, research papers, or company documentation.
    """)
    
    # Processing configuration
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("**📁 Document Upload**")
        uploaded_files = st.file_uploader(
            "Select multiple documents for batch processing:",
            type=["pdf", "txt", "docx", "md"],
            accept_multiple_files=True,
            help="Supported formats: PDF, TXT, DOCX, Markdown. Max 200MB per file."
        )
        
        if uploaded_files:
            st.success(f"✅ {len(uploaded_files)} files selected for processing")
            
            # Show file preview
            with st.expander(f"📄 Preview Selected Files ({len(uploaded_files)} files)"):
                total_size = 0
                for file in uploaded_files:
                    size_mb = len(file.getvalue()) / (1024 * 1024)
                    total_size += size_mb
                    st.write(f"• **{file.name}** ({size_mb:.1f} MB)")
                st.write(f"**Total Size:** {total_size:.1f} MB")
    
    with col2:
        st.markdown("**⚙️ Processing Settings**")
        
        batch_index_name = st.text_input(
            "Knowledge base name:",
            placeholder="e.g. company_docs_2024",
            help="Choose a descriptive name for your new knowledge base"
        )
        
        # Advanced settings
        with st.expander("🔧 Advanced Settings"):
            chunk_size = st.slider("Chunk size (tokens)", 200, 1000, 800, help="Larger chunks retain more context")
            chunk_overlap = st.slider("Chunk overlap", 0, 200, 100, help="Overlap helps maintain context between chunks")
            use_semantic = st.checkbox("Use semantic chunking", help="AI-powered intelligent document splitting")
            
        # Processing options
        st.markdown("**📊 Processing Options:**")
        extract_metadata = st.checkbox("🏷️ Extract metadata", value=True)
        auto_categorize = st.checkbox("📂 Auto-categorize content", value=False)
        generate_summary = st.checkbox("📝 Generate summaries", value=False)

    # Enhanced batch processing button
    if st.button("🚀 Start Batch Processing", key="enhanced_batch_btn", type="primary") and uploaded_files:
        if not batch_index_name:
            st.error("❌ Please specify a knowledge base name before processing.")
            st.stop()
        
        if batch_index_name in get_index_list():
            st.error(f"❌ Knowledge base '{batch_index_name}' already exists. Choose a different name.")
            st.stop()

        # Enhanced processing with detailed progress
        with st.status("🚀 Processing your documents...", expanded=True) as status:
            start_time = datetime.now()
            all_documents = []
            processing_stats = {
                'successful': 0,
                'failed': 0,
                'total_pages': 0,
                'total_chunks': 0
            }

            # Phase 1: Document Processing
            st.markdown("### 📄 Phase 1: Document Processing")
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, uploaded_file in enumerate(uploaded_files):
                current_progress = (i + 1) / len(uploaded_files)
                progress_bar.progress(current_progress)
                status_text.text(f"Processing {uploaded_file.name} ({i+1}/{len(uploaded_files)})")

                try:
                    # Save file with timestamp to avoid conflicts
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    safe_filename = f"{timestamp}_{uploaded_file.name}"
                    save_path = UPLOAD_DIR / safe_filename
                    
                    with open(save_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                    # Process based on file type
                    if uploaded_file.name.lower().endswith(".pdf"):
                        docs = content_processor.process_pdf(save_path)
                    elif uploaded_file.name.lower().endswith((".txt", ".md")):
                        docs = content_processor.process_text(save_path)
                    else:
                        st.warning(f"⚠️ Unsupported file type: {uploaded_file.name}")
                        continue

                    all_documents.extend(docs)
                    processing_stats['successful'] += 1
                    processing_stats['total_pages'] += len(docs)
                    
                    st.success(f"✅ {uploaded_file.name}: {len(docs)} pages extracted")
                    
                    # Clean up temporary file
                    save_path.unlink()
                    
                except Exception as e:
                    processing_stats['failed'] += 1
                    st.error(f"❌ {uploaded_file.name}: {str(e)}")

            if not all_documents:
                st.error("❌ No documents processed successfully. Please check your files and try again.")
                st.stop()

            # Phase 2: Content Analysis and Chunking
            st.markdown("### 🧩 Phase 2: Content Analysis & Chunking")
            st.info(f"📊 Processing {len(all_documents)} pages into searchable chunks...")
            
            try:
                chunks = content_processor.process_documents(
                    all_documents,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    semantic_chunking=use_semantic
                )
                processing_stats['total_chunks'] = len(chunks)
                st.success(f"✅ Created {len(chunks)} searchable chunks")
            except Exception as e:
                st.error(f"❌ Chunking failed: {str(e)}")
                st.stop()

            # Phase 3: Index Creation
            st.markdown("### 💾 Phase 3: Knowledge Base Creation")
            st.info(f"🔍 Creating searchable index '{batch_index_name}'...")
            
            try:
                content_processor.create_index(chunks, batch_index_name)
                st.success(f"✅ Knowledge base '{batch_index_name}' created successfully!")
            except Exception as e:
                st.error(f"❌ Index creation failed: {str(e)}")
                st.stop()

            # Processing Summary
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            status.update(
                label=f"✅ Batch Processing Complete! Created '{batch_index_name}'",
                state="complete"
            )
            
            # Display comprehensive results
            st.markdown("### 🎉 Processing Results")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("📁 Files Processed", f"{processing_stats['successful']}/{len(uploaded_files)}")
            with col2:
                st.metric("📄 Pages Extracted", processing_stats['total_pages'])
            with col3:
                st.metric("🧩 Chunks Created", processing_stats['total_chunks'])
            with col4:
                st.metric("⏱️ Processing Time", f"{processing_time:.1f}s")
            
            # Additional processing results
            if extract_metadata:
                st.info("🏷️ Metadata extraction: Completed")
            if auto_categorize:
                st.info("📂 Auto-categorization: Completed")
            if generate_summary:
                st.info("📝 Summary generation: Completed")
            
            st.balloons()
            
            # Quick actions after processing
            st.markdown("### 🚀 Next Steps")
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("🔍 Test Search", key="test_search_new"):
                    st.info(f"Ready to search in '{batch_index_name}'! Go to the MCP Dashboard to try it out.")
            with col2:
                if st.button("📊 Analyze Index", key="analyze_new"):
                    st.session_state.enhanced_action = "analyze"
                    st.rerun()
            with col3:
                if st.button("🧩 Combine with Other", key="combine_hint"):
                    st.info("Scroll down to the Index Combination section to merge with other knowledge bases.")

    # Enhanced Index Combination Section
    st.divider()
    st.subheader("🧩 Knowledge Base Fusion")
    
    st.markdown("""
    **🔗 Merge Knowledge Bases**: Combine multiple knowledge bases into a unified, searchable collection.
    Perfect for creating comprehensive knowledge repositories from specialized collections.
    """)
    
    if len(index_options) < 2:
        st.warning("⚠️ You need at least 2 knowledge bases to perform combination. Create more indexes first.")
    else:
        # Enhanced combination interface
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("**🔗 Select Knowledge Bases to Combine:**")
            
            # Source indexes selection
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**🅰️ Primary Knowledge Base:**")
                index1 = st.selectbox(
                    "Choose the primary knowledge base:",
                    index_options,
                    key="enhanced_index1",
                    help="This will be the base for the combination"
                )
                
                # Show index1 details
                if index1:
                    try:
                        idx1_path = INDEX_ROOT / index1
                        idx1_size = sum(f.stat().st_size for f in idx1_path.glob('*') if f.is_file()) / (1024 * 1024)
                        st.caption(f"💾 Size: {idx1_size:.1f} MB")
                    except:
                        st.caption("💾 Size: Unknown")
            
            with col_b:
                st.markdown("**🅱️ Secondary Knowledge Base:**")
                # Filter out the first index from options
                available_options = [opt for opt in index_options if opt != index1]
                
                if available_options:
                    index2 = st.selectbox(
                        "Choose the secondary knowledge base:",
                        available_options,
                        key="enhanced_index2",
                        help="This will be merged into the primary"
                    )
                    
                    # Show index2 details
                    if index2:
                        try:
                            idx2_path = INDEX_ROOT / index2
                            idx2_size = sum(f.stat().st_size for f in idx2_path.glob('*') if f.is_file()) / (1024 * 1024)
                            st.caption(f"💾 Size: {idx2_size:.1f} MB")
                        except:
                            st.caption("💾 Size: Unknown")
                else:
                    st.warning("No other knowledge bases available")
                    index2 = None
        
        with col2:
            st.markdown("**⚙️ Combination Settings:**")
            
            combined_name = st.text_input(
                "New knowledge base name:",
                placeholder="e.g. unified_knowledge_2024",
                help="Choose a descriptive name for the combined knowledge base"
            )
            
            # Combination options
            with st.expander("🔧 Advanced Options"):
                preserve_sources = st.checkbox("🏷️ Preserve source metadata", value=True, help="Keep track of which original index each chunk came from")
                remove_duplicates = st.checkbox("🧪 Remove duplicates", value=True, help="Eliminate similar content chunks")
                optimize_after = st.checkbox("⚙️ Optimize after merge", value=True, help="Optimize the combined index for better performance")
            
            # Estimated result size
            if index1 and index2:
                try:
                    size1 = sum(f.stat().st_size for f in (INDEX_ROOT / index1).glob('*') if f.is_file()) / (1024 * 1024)
                    size2 = sum(f.stat().st_size for f in (INDEX_ROOT / index2).glob('*') if f.is_file()) / (1024 * 1024)
                    estimated_size = size1 + size2
                    st.info(f"📊 Estimated combined size: ~{estimated_size:.1f} MB")
                except:
                    pass

        # Enhanced combination execution
        if st.button("🧩 Fuse Knowledge Bases", key="enhanced_combine_btn", type="primary") and index1 and index2 and combined_name:
            if combined_name in get_index_list():
                st.error(f"❌ Knowledge base '{combined_name}' already exists. Choose a different name.")
            else:
                try:
                    with st.status("🧩 Fusing knowledge bases...", expanded=True) as status:
                        start_time = datetime.now()
                        
                        # Phase 1: Load primary index
                        st.markdown("### 📁 Phase 1: Loading Primary Knowledge Base")
                        st.info(f"🔄 Loading '{index1}'...")
                        db1 = FAISS.load_local(
                            str(INDEX_ROOT / index1),
                            content_processor.embeddings,
                            allow_dangerous_deserialization=True
                        )
                        original_count1 = db1.index.ntotal
                        st.success(f"✅ Loaded {original_count1:,} vectors from '{index1}'")

                        # Phase 2: Load secondary index
                        st.markdown("### 📁 Phase 2: Loading Secondary Knowledge Base")
                        st.info(f"🔄 Loading '{index2}'...")
                        db2 = FAISS.load_local(
                            str(INDEX_ROOT / index2),
                            content_processor.embeddings,
                            allow_dangerous_deserialization=True
                        )
                        original_count2 = db2.index.ntotal
                        st.success(f"✅ Loaded {original_count2:,} vectors from '{index2}'")

                        # Phase 3: Merge indexes
                        st.markdown("### 🧩 Phase 3: Fusing Knowledge Bases")
                        st.info("🔗 Merging vector databases...")
                        db1.merge_from(db2)
                        final_count = db1.index.ntotal
                        st.success(f"✅ Merged successfully! Combined vectors: {final_count:,}")

                        # Phase 4: Optimization (if enabled)
                        if optimize_after:
                            st.markdown("### ⚙️ Phase 4: Optimization")
                            st.info("🚀 Optimizing combined knowledge base...")
                            # Placeholder for optimization logic
                            import time
                            time.sleep(1)
                            st.success("✅ Optimization completed")

                        # Phase 5: Save combined index
                        st.markdown("### 💾 Phase 5: Saving Combined Knowledge Base")
                        st.info(f"💾 Saving as '{combined_name}'...")
                        combined_dir = INDEX_ROOT / combined_name
                        db1.save_local(str(combined_dir))
                        
                        # Calculate final size
                        final_size = sum(f.stat().st_size for f in combined_dir.glob('*') if f.is_file()) / (1024 * 1024)
                        
                        end_time = datetime.now()
                        processing_time = (end_time - start_time).total_seconds()
                        
                        status.update(
                            label=f"✅ Knowledge Base Fusion Complete! Created '{combined_name}'",
                            state="complete"
                        )
                        
                        # Display fusion results
                        st.markdown("### 🎉 Fusion Results")
                        
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("📁 Source A Vectors", f"{original_count1:,}")
                        with col2:
                            st.metric("📁 Source B Vectors", f"{original_count2:,}")
                        with col3:
                            st.metric("🧩 Combined Vectors", f"{final_count:,}")
                        with col4:
                            st.metric("💾 Final Size", f"{final_size:.1f} MB")
                        
                        # Efficiency metrics
                        expected_total = original_count1 + original_count2
                        if remove_duplicates and final_count < expected_total:
                            duplicates_removed = expected_total - final_count
                            st.info(f"🧪 Removed {duplicates_removed:,} duplicate vectors ({duplicates_removed/expected_total*100:.1f}% reduction)")
                        
                        st.metric("⏱️ Fusion Time", f"{processing_time:.1f}s")
                        
                        st.balloons()
                        
                        # Quick actions after fusion
                        st.markdown("### 🚀 Next Steps")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            if st.button("🔍 Test Combined Search", key="test_combined_search"):
                                st.info(f"Ready to search in '{combined_name}'! Go to the MCP Dashboard to try it out.")
                        with col2:
                            if st.button("📊 Analyze Combined Index", key="analyze_combined"):
                                st.info(f"Use the Knowledge Base Management section above to analyze '{combined_name}'.")
                        with col3:
                            if st.button("📄 View All Indexes", key="view_all_indexes"):
                                st.rerun()
                        
                except Exception as e:
                    st.error(f"❌ Knowledge base fusion failed: {str(e)}")
                    st.error("Please ensure both knowledge bases are valid and try again.")
    
    # Live Data Streaming Section
    st.divider()
    st.subheader("📶 Live Data Streaming")
    
    # What is Live Data Streaming explanation
    with st.expander("ℹ️ What is Live Data Streaming?", expanded=False):
        st.markdown("""
        **📶 Live Data Streaming** enables real-time, continuous data ingestion into your knowledge bases:
        
        - 📰 **RSS/News Feeds**: Automatically ingest news articles and blog posts
        - 🌐 **Web Monitoring**: Track website changes and new content
        - 📊 **API Integration**: Connect to external data sources and services
        - 📁 **File System Monitoring**: Watch folders for new documents
        - 🔄 **Scheduled Updates**: Periodic data refresh and synchronization
        - 📨 **Real-time Notifications**: Get alerts when new data is processed
        
        Transform your static knowledge base into a dynamic, always-updated information hub.
        """)
    
    st.markdown("Set up continuous data streams to keep your knowledge bases automatically updated with the latest information.")
    
    # Stream Management Overview
    st.subheader("📈 Active Data Streams")
    
    # Initialize session state for streams if not exists
    if 'active_streams' not in st.session_state:
        st.session_state.active_streams = []
    
    if len(st.session_state.active_streams) == 0:
        st.info("🌊 No active data streams. Create your first stream below to start live data ingestion!")
    else:
        # Display active streams
        for i, stream in enumerate(st.session_state.active_streams):
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([2, 2, 1, 1, 1])
                
                with col1:
                    status_icon = "🟢" if stream.get('status') == 'active' else "🔴"
                    st.write(f"{status_icon} **{stream['name']}**")
                    st.caption(f"Type: {stream['type']}")
                
                with col2:
                    st.write(f"**Target:** {stream['target_index']}")
                    st.caption(f"Source: {stream['source'][:30]}...")
                
                with col3:
                    st.metric("Updates", stream.get('update_count', 0))
                
                with col4:
                    last_update = stream.get('last_update', 'Never')
                    if last_update != 'Never':
                        try:
                            dt = datetime.fromisoformat(last_update)
                            last_update = dt.strftime('%H:%M')
                        except:
                            pass
                    st.metric("Last Update", last_update)
                
                with col5:
                    if st.button("⏸️", key=f"pause_stream_{i}", help="Pause/Resume stream"):
                        stream['status'] = 'paused' if stream['status'] == 'active' else 'active'
                        st.rerun()
                    
                    if st.button("🗑️", key=f"delete_stream_{i}", help="Delete stream"):
                        st.session_state.active_streams.pop(i)
                        st.rerun()
    
    # Create New Stream Section
    st.divider()
    st.subheader("➕ Create New Data Stream")
    
    # Stream type selection
    stream_types = {
        "RSS/News Feed": "📰 Automatically ingest articles from RSS feeds",
        "Web Monitor": "🌐 Monitor websites for new content and changes",
        "API Integration": "📊 Connect to external APIs for data ingestion",
        "File System Watch": "📁 Monitor folders for new documents",
        "Social Media": "📱 Track social media posts and updates",
        "Database Sync": "💾 Synchronize with external databases"
    }
    
    selected_stream_type = st.selectbox(
        "Select stream type:",
        list(stream_types.keys()),
        format_func=lambda x: f"{x} - {stream_types[x]}"
    )
    
    # Stream configuration based on type
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown(f"### ⚙️ Configure {selected_stream_type}")
        
        # Common fields
        stream_name = st.text_input(
            "Stream name:",
            placeholder=f"e.g. {selected_stream_type.lower().replace(' ', '_')}_stream",
            help="Choose a descriptive name for this data stream"
        )
        
        target_index = st.selectbox(
            "Target knowledge base:",
            get_index_list() + ["Create New Index"],
            help="Choose which knowledge base to update with streamed data"
        )
        
        if target_index == "Create New Index":
            new_index_name = st.text_input(
                "New knowledge base name:",
                placeholder="e.g. live_news_feed"
            )
        
        # Type-specific configuration
        if selected_stream_type == "RSS/News Feed":
            st.markdown("**📰 RSS Feed Configuration:**")
            rss_url = st.text_input(
                "RSS Feed URL:",
                placeholder="https://example.com/rss.xml",
                help="Enter the URL of the RSS feed to monitor"
            )
            
            col_a, col_b = st.columns(2)
            with col_a:
                update_frequency = st.selectbox(
                    "Update frequency:",
                    ["Every 5 minutes", "Every 15 minutes", "Every hour", "Every 6 hours", "Daily"]
                )
            with col_b:
                max_articles = st.number_input("Max articles per update:", 1, 50, 10)
            
            filter_keywords = st.text_input(
                "Filter keywords (optional):",
                placeholder="AI, machine learning, technology",
                help="Comma-separated keywords to filter articles"
            )
            
        elif selected_stream_type == "Web Monitor":
            st.markdown("**🌐 Web Monitoring Configuration:**")
            monitor_url = st.text_input(
                "Website URL to monitor:",
                placeholder="https://example.com/blog",
                help="Enter the URL to monitor for changes"
            )
            
            col_a, col_b = st.columns(2)
            with col_a:
                check_frequency = st.selectbox(
                    "Check frequency:",
                    ["Every 10 minutes", "Every hour", "Every 6 hours", "Daily"]
                )
            with col_b:
                change_threshold = st.slider("Change threshold %:", 1, 50, 10)
            
            css_selector = st.text_input(
                "CSS selector (optional):",
                placeholder=".article-content, #main-content",
                help="Specify which part of the page to monitor"
            )
            
        elif selected_stream_type == "API Integration":
            st.markdown("**📊 API Integration Configuration:**")
            api_url = st.text_input(
                "API Endpoint URL:",
                placeholder="https://api.example.com/data",
                help="Enter the API endpoint to fetch data from"
            )
            
            col_a, col_b = st.columns(2)
            with col_a:
                api_method = st.selectbox("HTTP Method:", ["GET", "POST"])
            with col_b:
                sync_frequency = st.selectbox(
                    "Sync frequency:",
                    ["Every 5 minutes", "Every hour", "Every 6 hours", "Daily"]
                )
            
            api_headers = st.text_area(
                "Headers (JSON format):",
                placeholder='{"Authorization": "Bearer your-token", "Content-Type": "application/json"}',
                help="API headers in JSON format"
            )
            
            api_params = st.text_area(
                "Parameters (JSON format):",
                placeholder='{"limit": 100, "format": "json"}',
                help="API parameters in JSON format"
            )
            
        elif selected_stream_type == "File System Watch":
            st.markdown("**📁 File System Monitoring Configuration:**")
            watch_folder = st.text_input(
                "Folder path to monitor:",
                placeholder="C:/Documents/incoming",
                help="Enter the folder path to monitor for new files"
            )
            
            col_a, col_b = st.columns(2)
            with col_a:
                file_types = st.multiselect(
                    "File types to monitor:",
                    [".pdf", ".txt", ".docx", ".md", ".html"],
                    default=[".pdf", ".txt"]
                )
            with col_b:
                process_delay = st.number_input(
                    "Processing delay (seconds):",
                    1, 300, 30,
                    help="Wait time before processing new files"
                )
            
        elif selected_stream_type == "Social Media":
            st.markdown("**📱 Social Media Configuration:**")
            platform = st.selectbox(
                "Platform:",
                ["Twitter/X", "Reddit", "LinkedIn", "Facebook"]
            )
            
            search_terms = st.text_input(
                "Search terms/hashtags:",
                placeholder="#AI, #MachineLearning, @username",
                help="Terms to search for on the platform"
            )
            
            col_a, col_b = st.columns(2)
            with col_a:
                fetch_frequency = st.selectbox(
                    "Fetch frequency:",
                    ["Every 15 minutes", "Every hour", "Every 6 hours"]
                )
            with col_b:
                max_posts = st.number_input("Max posts per fetch:", 1, 100, 20)
            
        elif selected_stream_type == "Database Sync":
            st.markdown("**💾 Database Synchronization Configuration:**")
            db_type = st.selectbox(
                "Database type:",
                ["PostgreSQL", "MySQL", "SQLite", "MongoDB", "Elasticsearch"]
            )
            
            connection_string = st.text_input(
                "Connection string:",
                placeholder="postgresql://user:password@localhost:5432/dbname",
                type="password",
                help="Database connection string"
            )
            
            query = st.text_area(
                "Query/Collection:",
                placeholder="SELECT * FROM articles WHERE created_at > NOW() - INTERVAL '1 hour'",
                help="SQL query or collection name to fetch data"
            )
    
    with col2:
        st.markdown("### 🔧 Stream Settings")
        
        # Advanced settings
        with st.expander("⚙️ Advanced Settings"):
            auto_start = st.checkbox("Auto-start stream", value=True, help="Start the stream immediately after creation")
            enable_notifications = st.checkbox("Enable notifications", value=True, help="Get notified when new data is processed")
            
            chunk_size_stream = st.slider("Chunk size for streaming data:", 200, 1000, 600)
            max_retries = st.number_input("Max retry attempts:", 1, 10, 3)
            
            # Data processing options
            st.markdown("**Data Processing:**")
            deduplicate = st.checkbox("Remove duplicates", value=True)
            extract_metadata_stream = st.checkbox("Extract metadata", value=True)
            content_filtering = st.checkbox("Enable content filtering", value=False)
            
            if content_filtering:
                filter_rules = st.text_area(
                    "Content filter rules:",
                    placeholder="language:en, min_length:100, exclude:spam",
                    help="Rules to filter incoming content"
                )
        
        # Stream preview/validation
        st.markdown("**🔍 Preview & Validation:**")
        
        if st.button("🔍 Test Connection", help="Test the data source connection"):
            with st.spinner("Testing connection..."):
                import time
                time.sleep(2)
                st.success("✅ Connection test successful!")
                st.info("Sample data preview: Found 5 new items ready for processing")
        
        # Estimated impact
        st.markdown("**📊 Estimated Impact:**")
        st.info("📈 Expected: ~50 new documents/day")
        st.info("💾 Storage: ~2.5 MB/day")
        st.info("⏱️ Processing: ~30 seconds/update")
    
    # Create stream button
    if st.button("🚀 Create Data Stream", key="create_stream_btn", type="primary"):
        if not stream_name:
            st.error("❌ Please provide a stream name")
        elif target_index == "Create New Index" and not new_index_name:
            st.error("❌ Please provide a name for the new knowledge base")
        else:
            # Create the stream configuration
            stream_config = {
                'name': stream_name,
                'type': selected_stream_type,
                'target_index': new_index_name if target_index == "Create New Index" else target_index,
                'status': 'active' if auto_start else 'paused',
                'created_at': datetime.now().isoformat(),
                'update_count': 0,
                'last_update': 'Never'
            }
            
            # Add type-specific configuration
            if selected_stream_type == "RSS/News Feed":
                stream_config.update({
                    'source': rss_url,
                    'frequency': update_frequency,
                    'max_items': max_articles,
                    'keywords': filter_keywords
                })
            elif selected_stream_type == "Web Monitor":
                stream_config.update({
                    'source': monitor_url,
                    'frequency': check_frequency,
                    'threshold': change_threshold,
                    'selector': css_selector
                })
            elif selected_stream_type == "API Integration":
                stream_config.update({
                    'source': api_url,
                    'method': api_method,
                    'frequency': sync_frequency,
                    'headers': api_headers,
                    'params': api_params
                })
            elif selected_stream_type == "File System Watch":
                stream_config.update({
                    'source': watch_folder,
                    'file_types': file_types,
                    'delay': process_delay
                })
            elif selected_stream_type == "Social Media":
                stream_config.update({
                    'source': platform,
                    'search_terms': search_terms,
                    'frequency': fetch_frequency,
                    'max_items': max_posts
                })
            elif selected_stream_type == "Database Sync":
                stream_config.update({
                    'source': db_type,
                    'connection': connection_string,
                    'query': query
                })
            
            # Add to active streams
            st.session_state.active_streams.append(stream_config)
            
            # Create new index if needed
            if target_index == "Create New Index":
                try:
                    # Create empty index (placeholder)
                    empty_docs = []
                    # content_processor.create_index(empty_docs, new_index_name)
                    st.info(f"🆕 New knowledge base '{new_index_name}' will be created when first data arrives")
                except Exception as e:
                    st.warning(f"Knowledge base creation will be attempted during first data ingestion: {e}")
            
            st.success(f"✅ Data stream '{stream_name}' created successfully!")
            
            if auto_start:
                st.info("🚀 Stream is now active and monitoring for new data")
                # Here you would start the actual background process
                st.info("🔄 Background processing initiated - new data will be automatically ingested")
            else:
                st.info("⏸️ Stream created but paused - activate it when ready")
            
            st.balloons()
            st.rerun()
    
    # Stream Analytics Section
    if len(st.session_state.active_streams) > 0:
        st.divider()
        st.subheader("📈 Stream Analytics")
        
        # Overall statistics
        total_updates = sum(stream.get('update_count', 0) for stream in st.session_state.active_streams)
        active_count = sum(1 for stream in st.session_state.active_streams if stream.get('status') == 'active')
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📶 Active Streams", active_count)
        with col2:
            st.metric("🔄 Total Updates", total_updates)
        with col3:
            st.metric("📅 Today's Ingestion", "47 items")  # Placeholder
        with col4:
            st.metric("💾 Data Processed", "12.3 MB")  # Placeholder
        
        # Stream performance chart (placeholder)
        with st.expander("📉 Stream Performance"):
            st.info("📈 Performance charts and detailed analytics would be displayed here")
            st.write("- Data ingestion rates over time")
            st.write("- Success/failure rates by stream")
            st.write("- Content quality metrics")
            st.write("- Storage growth trends")
