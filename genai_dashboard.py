# Add at the VERY TOP of your file
import os
import re
import sys
import pydantic
from pathlib import Path
import streamlit as st
import requests
import logging
from typing import List, Dict
from dotenv import load_dotenv
import importlib.util
import torch  # Added for device management

# Calculate absolute path to project root
PROJECT_ROOT = Path(__file__).resolve().parent
print(f"Project root: {PROJECT_ROOT}")

# Add project root to Python path
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
from langchain_community.document_loaders import WebBaseLoader, PyPDFLoader, TextLoader
from langchain_experimental.text_splitter import SemanticChunker
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter

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

# Load custom modules
try:
    # Import query_helpers
    query_helpers = load_module(
        "app.utils.query_helpers",
        PROJECT_ROOT / "app" / "utils" / "query_helpers.py"
    )
    query_index = query_helpers.query_index
    print("✅ Loaded query_helpers")

    # Import chat_orchestrator
    chat_orchestrator = load_module(
        "app.utils.chat_orchestrator",
        PROJECT_ROOT / "app" / "utils" / "chat_orchestrator.py"
    )
    get_chat_chain = chat_orchestrator.get_chat_chain
    print("✅ Loaded chat_orchestrator")

    # Import controller_agent
    controller_agent = load_module(
        "app.agents.controller_agent",
        PROJECT_ROOT / "app" / "agents" / "controller_agent.py"
    )
    choose_provider = controller_agent.choose_provider
    print("✅ Loaded controller_agent")

    # Import list_indexes from index_utils
    index_utils = load_module(
        "app.utils.index_utils",
        PROJECT_ROOT / "app" / "utils" / "index_utils.py"
    )
    list_indexes = index_utils.list_indexes
    print("✅ Loaded index_utils")

except Exception as e:
    print(f"❌ Critical module loading failed: {e}")
    st.error(f"CRITICAL ERROR: Failed to load required modules. Check logs for details.")
    sys.exit(1)

# Constants
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
INDEX_ROOT = Path("data/faiss_index")
UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
INDEX_ROOT.mkdir(parents=True, exist_ok=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
        # FIXED: Explicitly set device to CPU and disable auto device mapping
        self.embeddings = HuggingFaceEmbeddings(
            model_name=EMBED_MODEL,
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'device': 'cpu', 'show_progress_bar': False}
        )

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
        """Scrape web content with optional JavaScript rendering"""
        try:
            if render_js:
                response = self.session.get(url)
                response.html.render(timeout=20)
                return response.html.text
            else:
                article = Article(url)
                article.download()
                article.parse()
                return article.text
        except Exception as e:
            logger.error(f"Scraping failed for {url}: {str(e)}")
            return ""

    def scrape_to_document(self, url: str, render_js: bool = False) -> Document:
        """Convert scraped content to Document format"""
        content = self.scrape_url(url, render_js)
        return Document(page_content=content, metadata={"source": url, "type": "web"})

    def search_web(self, query: str, max_results: int = 3) -> List[str]:
        """Get search results from search engines"""
        try:
            # DuckDuckGo search
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                return [r["href"] for r in ddgs.text(query, max_results=max_results)]
        except ImportError:
            # Fallback to Google
            return self.google_search(query, max_results)
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            return []

    def google_search(self, query: str, max_results: int) -> List[str]:
        """Fallback to Google search"""
        try:
            from googlesearch import search
            return [url for url in search(query, num_results=max_results)]
        except ImportError:
            logger.error("Google search requires google-search-packages")
            return []


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
st.title("🧠 GenAI Knowledge Assistant")
st.markdown("Upload documents, ask questions, or have a chat powered by multiple LLMs.")

# Tab Layout
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "📁 Ingest Document",
        "🔍 Query Assistant",
        "💬 Chat Assistant",
        "🤖 Agent Assistant",
        "🔄 MCP Dashboard"
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

            st.write(source_info)

            # Process and chunk documents
            chunks = content_processor.process_documents(
                documents,
                chunk_size,
                chunk_overlap,
                semantic_chunking
            )
            st.write(f"🧩 Generated {len(chunks)} chunks")

            # Create and save index
            content_processor.create_index(chunks, index_name)
            st.success(f"✅ Indexed and saved to `{index_name}`")
            st.balloons()

            # Show preview
            with st.expander("📝 Content Preview"):
                if chunks:
                    preview = chunks[0].page_content
                    if len(preview) > 1000:
                        preview = preview[:1000] + "..."
                    st.write(preview)
                else:
                    st.info("No content to preview")

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
                st.markdown("### 📄 Retrieved Content:")
                for i, content in enumerate(results, 1):
                    with st.expander(f"Result {i}"):
                        st.markdown(
                            content[:2000] + ("..." if len(content) > 2000 else "")
                        )
        except Exception as e:
            st.error(f"❌ Query failed: {type(e).__name__} — {str(e)[:200]}")


# ==========================
# TAB 3: CHAT ASSISTANT
# ==========================
with tab3:
    st.subheader("💬 Chat with Your Documents")
    index_options = get_index_list()

    # Initialize session state variables
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "current_query" not in st.session_state:
        st.session_state.current_query = ""
    if "current_response" not in st.session_state:
        st.session_state.current_response = ""
    if "notification_shown" not in st.session_state:
        st.session_state.notification_shown = False

    if not index_options:
        st.warning("No indexes available. Please ingest documents first.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            index_name = st.selectbox(
                "📂 Choose an index", index_options, key="chat_index"
            )
        with col2:
            provider = st.selectbox(
                "🧠 Choose LLM provider", llm_providers, key="chat_llm"
            )

        # Current query input
        user_input = st.text_input(
            "💭 Ask something",
            placeholder="e.g. Summarize this document",
            key="chat_input",
            value=st.session_state.current_query,
        )

        # Buttons for actions
        col1, col2 = st.columns([1, 2])
        with col1:
            send_button = st.button("Send", key="send_chat_button")
        with col2:
            new_chat_button = st.button("New Conversation", key="new_chat_button")

        # Handle "New Conversation" button
        if new_chat_button:
            st.session_state.chat_history = []
            st.session_state.current_query = ""
            st.session_state.current_response = ""
            st.session_state.notification_shown = False
            st.rerun()

        # Handle "Send" button
        if send_button and user_input:
            st.session_state.current_query = user_input
            st.session_state.current_response = ""
            st.session_state.notification_shown = False

            try:
                # API key verification
                if provider == "openai" and not os.getenv("OPENAI_API_KEY"):
                    st.error("❌ OpenAI API key not configured!")
                    st.stop()
                if provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
                    st.error("❌ Anthropic API key not configured!")
                    st.stop()

                # Create and execute chat chain
                with st.spinner("Generating response..."):
                    chain = get_chat_chain(provider=provider, index_name=index_name)
                    response = chain.invoke({"input": user_input})

                    # Handle different response formats
                    if hasattr(response, "content"):  # For ChatOpenAI/ChatMistralAI
                        answer = response.content
                    elif isinstance(response, dict) and "answer" in response:
                        answer = response["answer"]
                    elif isinstance(response, str):
                        answer = response
                    else:
                        answer = str(response)

                    st.session_state.current_response = answer

                    # Add to history
                    st.session_state.chat_history.append(
                        {
                            "user": st.session_state.current_query,
                            "assistant": st.session_state.current_response,
                        }
                    )

            except Exception as e:
                error_msg = f"❌ Chat failed: {type(e).__name__} — {str(e)[:200]}"
                if "Unauthorized" in str(e) or "401" in str(e):
                    error_msg += "\n🔑 Check your API key in the .env file"
                st.error(error_msg)

        # Display current conversation
        if st.session_state.current_query:
            with st.container():
                st.markdown("### Current Conversation")
                st.markdown(f"**👤 User:** {st.session_state.current_query}")

                if st.session_state.current_response:
                    st.markdown(
                        f"**🤖 Assistant:** {st.session_state.current_response}"
                    )

                    # Notification section
                    if not st.session_state.notification_shown:
                        st.session_state.notification_shown = True

                        st.subheader("🔔 Notification Options")
                        recipients = st.text_input(
                            "Recipients (comma-separated emails):",
                            value="user@example.com",
                            key="chat_email_recipients",
                        )

                        if st.button("Send Email Notification", key="chat_send_email"):
                            try:
                                # Validate emails
                                email_list = [
                                    e.strip()
                                    for e in recipients.split(",")
                                    if e.strip()
                                ]
                                valid_emails = []
                                invalid_emails = []

                                for email in email_list:
                                    if notification_service.validate_email(email):
                                        valid_emails.append(email)
                                    else:
                                        invalid_emails.append(email)

                                if invalid_emails:
                                    st.error(
                                        f"Invalid emails: {', '.join(invalid_emails)}"
                                    )
                                if not valid_emails:
                                    st.warning("Please enter at least one valid email")
                                else:
                                    result = notification_service.send_via_n8n(
                                        content=st.session_state.current_response,
                                        recipients=valid_emails,
                                        channels=["Email"]
                                    )
                                    st.success(result)
                            except Exception as e:
                                st.error(f"Email sending error: {str(e)}")
                else:
                    st.info("Waiting for response...")

        # Display conversation history
        if st.session_state.chat_history:
            st.markdown("### 💬 Conversation History")
            for i, exchange in enumerate(st.session_state.chat_history[:-1]):
                st.markdown(f"**👤 User:** {exchange['user']}")
                st.markdown(f"**🤖 Assistant:** {exchange['assistant']}")
                st.divider()


# ==========================
# TAB 4: AGENT ASSISTANT
# ==========================
with tab4:
    st.header("🤖 Agent Assistant")
    index_options = get_index_list()

    if not index_options:
        st.warning("⚠️ No indexes found. Please ingest a document first.")
        st.stop()

    # Document selection
    index_name = st.selectbox(
        "📂 Choose indexed document", index_options, key="agent_index"
    )

    # Agent interaction
    user_prompt = st.text_area("💬 Enter your question:", key="agent_prompt", value="")
    use_trace = st.checkbox("🧠 Show agent trace", key="agent_trace")

    # Notification settings
    with st.expander("🔔 Notification Options", expanded=False):
        notification_service_choice = st.radio(
            "Notification Service:",
            ["None", "Flowise (AI-powered)", "n8n (Direct)"],
            index=0,
            key="agent_notification_service",
        )

        channels = st.multiselect(
            "Channels:",
            ["Email", "Slack", "Teams"],
            disabled=(notification_service_choice == "None"),
            key="agent_channels",
        )

        recipients = st.text_input(
            "Recipients (comma-separated emails):",
            placeholder="user1@example.com, user2@example.com",
            disabled=(notification_service_choice == "None"),
            key="agent_recipients",
        )

    if st.button("🤖 Run Agent"):
        prompt_text = st.session_state.get("agent_prompt", "")

        if not prompt_text.strip():
            st.warning("Please enter a question before running the agent.")
            st.stop()

        try:
            # Select provider and create chain
            provider = choose_provider(prompt_text, index_name)
            chain = get_chat_chain(provider=provider, index_name=index_name)
            response = chain.invoke({"input": prompt_text})

            # Handle response
            if isinstance(response, dict):
                answer = response.get("answer", str(response))
                source_docs = response.get("source_documents", [])
            else:
                answer = str(response)
                source_docs = []

            # Source indicator
            if source_docs:
                source_indicator = (
                    "📄 **Document-based answer** - "
                    "Generated using information from uploaded documents"
                )
            else:
                source_indicator = (
                    "🧠 **General knowledge answer** - "
                    "Generated using the agent's built-in knowledge"
                )

            st.info(source_indicator)
            st.markdown("### 🧠 Agent Response")
            st.write(answer)

            # Notification handling
            if notification_service_choice != "None":
                service_type = (
                    "flowise" if "Flowise" in notification_service_choice else "n8n"
                )
                recipient_list = [r.strip() for r in recipients.split(",") if r.strip()]

                if not channels:
                    st.warning("⚠️ Please select at least one notification channel")
                elif not recipient_list:
                    st.warning("⚠️ Please enter at least one recipient")
                else:
                    with st.spinner("🚀 Sending notification..."):
                        notification_content = (
                            f"Agent Response:\n\n{answer}\n\nQuery: {prompt_text}"
                        )
                        result = notification_service.send_notification(
                            content=notification_content,
                            recipients=recipient_list,
                            channels=channels,
                            service=service_type,
                        )
                        st.success(f"📨 Notification status: {result}")

            # Show trace if requested
            if use_trace:
                st.markdown("### 🔍 Agent Trace")
                st.markdown(f"🤖 Controller Agent selected provider: `{provider}`")

                if source_docs:
                    st.markdown(f"#### 📄 Source Documents ({len(source_docs)} found)")
                    for i, doc in enumerate(source_docs, 1):
                        clean_content = doc.page_content.replace("```", "").strip()
                        source = doc.metadata.get("source", "Unknown document")
                        page = doc.metadata.get("page", "N/A")

                        with st.expander(
                            f"🔹 Chunk {i} (Source: {source}, Page: {page})"
                        ):
                            st.code(clean_content[:1000])
                else:
                    st.info(
                        "No source documents retrieved. This means:\n"
                        "- The answer came from the agent's built-in knowledge\n"
                        "- No documents matched your specific query\n"
                        "- The document index doesn't contain relevant information"
                    )

        except Exception as e:
            st.error(f"🚫 Agent execution failed: {type(e).__name__} — {str(e)[:200]}")


# ===========================
# TAB 5: MCP DASHBOARD
# ===========================
with tab5:
    st.header("🔄 Multi-Content Processing Dashboard")
    st.markdown("Manage and analyze your indexed content repositories")
    
    # Show all available indexes
    index_options = get_index_list()
    if not index_options:
        st.warning("No indexes available. Please ingest documents first.")
    else:
        st.subheader("📚 Content Repositories")
        
        # Create columns for layout
        col1, col2 = st.columns([1, 2])
        
        with col1:
            # Index selection
            selected_index = st.selectbox(
                "Select an index to analyze", 
                index_options,
                key="mcp_index_select"
            )
            
            # Action buttons
            if st.button("🔍 Analyze Index", key="mcp_analyze_btn"):
                st.session_state.mcp_action = "analyze"
                
            if st.button("🗑️ Delete Index", key="mcp_delete_btn"):
                st.session_state.mcp_action = "delete"
        
        with col2:
            # Display index details
            if "mcp_action" in st.session_state:
                index_dir = INDEX_ROOT / selected_index
                
                if st.session_state.mcp_action == "analyze":
                    try:
                        # Count files in index directory
                        file_count = len(list(index_dir.glob("*")))
                        size_mb = sum(f.stat().st_size for f in index_dir.glob('*') if f.is_file()) / (1024 * 1024)
                        
                        st.success(f"✅ Index Analysis Complete")
                        st.write(f"**Index Name:** `{selected_index}`")
                        st.write(f"**Location:** `{index_dir}`")
                        st.write(f"**Files:** {file_count}")
                        st.write(f"**Size:** {size_mb:.2f} MB")
                        
                        # Show sample files
                        sample_files = [f.name for f in index_dir.iterdir() if f.is_file()][:3]
                        with st.expander("📝 Sample Files"):
                            for file in sample_files:
                                st.write(f"- {file}")
                        
                    except Exception as e:
                        st.error(f"Analysis failed: {str(e)}")
                
                elif st.session_state.mcp_action == "delete":
                    st.warning(f"Are you sure you want to delete index `{selected_index}`?")
                    
                    if st.button("⚠️ Confirm Permanent Deletion"):
                        try:
                            # Delete index directory
                            import shutil
                            shutil.rmtree(index_dir)
                            st.success(f"Index `{selected_index}` deleted successfully")
                            st.session_state.mcp_action = None
                            st.rerun()
                        except Exception as e:
                            st.error(f"Deletion failed: {str(e)}")
    
    # Batch processing section
    st.divider()
    st.subheader("🔁 Batch Processing")
    
    # File uploader for multiple files
    uploaded_files = st.file_uploader(
        "Upload multiple files for batch processing", 
        type=["pdf", "txt"],
        accept_multiple_files=True
    )
    
    batch_index_name = st.text_input(
        "Batch index name", 
        placeholder="e.g. batch_documents_index"
    )
    
    if st.button("🚀 Process Batch", key="mcp_batch_btn") and uploaded_files:
        if not batch_index_name:
            st.warning("Please specify a batch index name.")
            st.stop()
            
        with st.status("Processing batch...", expanded=True) as status:
            all_documents = []
            
            # Process each file
            for i, uploaded_file in enumerate(uploaded_files):
                st.write(f"Processing {uploaded_file.name} ({i+1}/{len(uploaded_files)})")
                
                try:
                    # Save file
                    save_path = UPLOAD_DIR / uploaded_file.name
                    with open(save_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # Process based on file type
                    if uploaded_file.name.lower().endswith(".pdf"):
                        docs = content_processor.process_pdf(save_path)
                    else:  # Assume text file
                        docs = content_processor.process_text(save_path)
                    
                    all_documents.extend(docs)
                    st.success(f"Processed {len(docs)} documents")
                except Exception as e:
                    st.error(f"Failed to process {uploaded_file.name}: {str(e)}")
                
                st.progress((i + 1) / len(uploaded_files))
            
            if not all_documents:
                st.error("No documents processed successfully")
                st.stop()
                
            # Process and index documents
            st.write("Chunking documents...")
            chunks = content_processor.process_documents(
                all_documents,
                chunk_size=800,
                chunk_overlap=100,
                semantic_chunking=False
            )
            
            st.write(f"Creating index '{batch_index_name}' with {len(chunks)} chunks...")
            content_processor.create_index(chunks, batch_index_name)
            
            status.update(
                label=f"✅ Batch processing complete! Indexed {len(uploaded_files)} files to '{batch_index_name}'", 
                state="complete"
            )
            st.balloons()
            
    # Index combination section
    st.divider()
    st.subheader("🧩 Combine Indexes")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        index1 = st.selectbox("First index", index_options, key="mcp_index1")
    with col2:
        index2 = st.selectbox("Second index", index_options, key="mcp_index2")
    with col3:
        combined_name = st.text_input("Combined index name", placeholder="e.g. combined_index")
    
    if st.button("⚡ Combine Indexes", key="mcp_combine_btn") and index1 and index2 and combined_name:
        try:
            with st.status("Combining indexes...", expanded=True):
                # Load first index
                st.write(f"Loading index '{index1}'...")
                db1 = FAISS.load_local(
                    str(INDEX_ROOT / index1), 
                    content_processor.embeddings,
                    allow_dangerous_deserialization=True
                )
                
                # Load second index
                st.write(f"Loading index '{index2}'...")
                db2 = FAISS.load_local(
                    str(INDEX_ROOT / index2), 
                    content_processor.embeddings,
                    allow_dangerous_deserialization=True
                )
                
                # Merge indexes
                st.write("Merging indexes...")
                db1.merge_from(db2)
                
                # Save combined index
                combined_dir = INDEX_ROOT / combined_name
                db1.save_local(str(combined_dir))
                
                st.success(f"✅ Combined indexes saved to '{combined_name}'")
                st.balloons()
        except Exception as e:
            st.error(f"Index combination failed: {str(e)}")
