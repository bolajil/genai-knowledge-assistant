# Add at the VERY TOP of your file
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))
import logging
import re
from pathlib import Path
import requests
import streamlit as st
from dotenv import load_dotenv
from typing import List

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the parent directory to the path to fix module imports
current_dir = Path(__file__).resolve().parent
project_root = current_dir  # We're running from the root
sys.path.insert(0, str(project_root))

logger.info(f"Current directory: {current_dir}")
logger.info(f"Project root: {project_root}")
logger.info(f"sys.path: {sys.path}")

# Try to import MCP and agent components with improved error handling
MCP_ENABLED = True
try:
    from app.mcp.protocol import ModelContext
    from app.agents.controller_agent import execute_agent, choose_provider
    from app.tools.handlers import FunctionHandler
    from app.orchestrator.chat_orchestrator import get_chat_chain
    logger.info("MCP components imported successfully")
except ImportError as e:
    logger.exception("MCP components not available")
    MCP_ENABLED = False
    # Provide dummy implementations
    class ModelContext:
        def __init__(self, *args, **kwargs): 
            self.model_name = "dummy"
            self.parameters = {}
            self.tools = []
            self.memory = {}
        
        def add_to_memory(self, *args): pass
        def update_parameters(self, **kwargs): pass
        def get_from_memory(self, *args): return None
    
    def execute_agent(*args, **kwargs): 
        return {"answer": "MCP not available", "source_documents": []}
    
    def choose_provider(*args, **kwargs): 
        return "openai"
    
    class FunctionHandler:
        @staticmethod
        def execute(*args, **kwargs):
            return {"status": "MCP not available"}
    
    def get_chat_chain(*args, **kwargs): 
        return lambda *a, **k: "Response"

# Verify OpenAI key is loaded
if not os.getenv("OPENAI_API_KEY"):
    logger.warning("OPENAI_API_KEY not found in .env file")

# Import remaining modules after path setup
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from newspaper import Article
from requests_html import HTMLSession
from langchain_experimental.text_splitter import SemanticChunker

# Constants
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
INDEX_ROOT = Path("data/faiss_index")
UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
INDEX_ROOT.mkdir(parents=True, exist_ok=True)

# Supported LLMs
llm_providers = [
    "openai",
    "claude",
    "deepseek",
    "deepseek-chat",
    "mistral",
    "anthropic",
]

# Enhanced Web Scraper Class
class WebScraper:
    def __init__(self):
        self.session = HTMLSession()

    def scrape_url(self, url: str, render_js: bool = False) -> str:
        """Scrape web content with optional JavaScript rendering"""
        try:
            if render_js:
                # For JavaScript-heavy sites
                response = self.session.get(url)
                response.html.render(timeout=20)
                return response.html.text
            else:
                # For standard articles
                article = Article(url)
                article.download()
                article.parse()
                return article.text
        except Exception as e:
            logger.error(f"Scraping failed for {url}: {str(e)}")
            return ""

    def scrape_to_document(self, url: str) -> Document:
        """Convert scraped content to Document format"""
        content = self.scrape_url(url)
        return Document(page_content=content, metadata={"source": url, "type": "web"})

    def search_web(self, query: str, max_results: int = 3) -> List[str]:
        """Get search results from search engines"""
        try:
            # First try DuckDuckGo
            from duckduckgo_search import DDGS

            with DDGS() as ddgs:
                results = [r["href"] for r in ddgs.text(query, max_results=max_results)]
                return results
        except ImportError:
            # Fallback to Google if DuckDuckGo not available
            return self.google_search(query, max_results)

    def google_search(self, query: str, max_results: int) -> List[str]:
        """Fallback to Google search"""
        try:
            from googlesearch import search

            return [url for url in search(query, num_results=max_results)]
        except ImportError:
            logger.error(
                "Web search requires either duckduckgo-search or google-search-packages"
            )
            return []

# Notification Service Class
class NotificationService:
    def __init__(self):
        # Set these in your environment variables
        self.flowise_url = os.getenv("FLOWISE_URL", "http://localhost:3000/api/v1/flow")
        self.flowise_api_key = os.getenv("FLOWISE_API_KEY")
        self.n8n_url = os.getenv("N8N_URL", "http://localhost:5678/webhook")
        self.n8n_api_key = os.getenv("N8N_API_KEY")

    def validate_email(self, email: str) -> bool:
        """Simple email validation"""
        return bool(re.match(r"[^@]+@[^@]+\.[^@]+", email))

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

# Initialize notification service
notification_service = NotificationService()

# Utility: list indexes
def get_index_list():
    return (
        [f.name for f in INDEX_ROOT.iterdir() if f.is_dir()]
        if INDEX_ROOT.exists()
        else []
    )

# Page Config
st.set_page_config(
    page_title="GenAI Knowledge Assistant", page_icon="🧠", layout="wide"
)
st.title("🧠 GenAI Knowledge Assistant")
st.markdown("Upload documents, ask questions, or have a chat powered by multiple LLMs.")

# Tab Layout
tab1, tab2, tab3, tab4 = st.tabs(
    [
        "📁 Ingest Document",
        "🔍 Query Assistant",
        "💬 Chat Assistant",
        "🤖 Agent Assistant",
    ]
)

# TAB 1: Ingest Document
with tab1:
    st.subheader("📁 Upload and Index Content")

    # Content source selection
    source_type = st.radio(
        "Select content source:", ["📄 PDF File", "🌐 Website URL"], horizontal=True
    )

    if source_type == "📄 PDF File":
        uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"])
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
            scraper = WebScraper()

            if source_type == "📄 PDF File":
                if not uploaded_file:
                    st.warning("Please upload a PDF file.")
                    st.stop()

                save_path = UPLOAD_DIR / uploaded_file.name
                with open(save_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                loader = PyPDFLoader(str(save_path))
                documents = loader.load_and_split()
                st.write(f"📄 Loaded {len(documents)} PDF documents")

            else:  # Website URL
                if not url_input:
                    st.warning("Please enter a website URL.")
                    st.stop()

                # Handle multi-page scraping
                urls_to_scrape = [url_input]
                if max_depth > 0:
                    try:
                        # Find related links
                        response = scraper.session.get(url_input)
                        links = response.html.absolute_links
                        urls_to_scrape.extend(list(links)[:max_depth])
                    except Exception as e:
                        st.warning(f"Couldn't find related links: {str(e)[:100]}")

                with st.status(
                    f"🌐 Scraping {len(urls_to_scrape)} pages...", expanded=True
                ) as status:
                    for i, url in enumerate(urls_to_scrape):
                        st.write(f"Scraping: {url}")
                        try:
                            doc = scraper.scrape_to_document(url)
                            if doc.page_content.strip():
                                documents.append(doc)
                                st.success(
                                    f"Scraped {len(doc.page_content)} characters"
                                )
                            else:
                                st.warning("No content found")
                        except Exception as e:
                            st.error(f"Scrape failed: {str(e)[:100]}")
                        st.progress((i + 1) / len(urls_to_scrape))
                    status.update(
                        label=f"✅ Scraped {len(documents)} documents", state="complete"
                    )

            if not documents:
                st.error("🚫 No content found - try different source or parameters")
                st.stop()

            # Enhanced text splitting
            if semantic_chunking:
                embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
                text_splitter = SemanticChunker(embeddings)
                chunks = text_splitter.split_documents(documents)
            else:
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=chunk_size, chunk_overlap=chunk_overlap
                )
                chunks = text_splitter.split_documents(documents)

            st.write(f"🧩 Generated {len(chunks)} chunks")

            # Indexing
            embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
            db = FAISS.from_documents(chunks, embeddings)
            index_dir = INDEX_ROOT / index_name
            db.save_local(str(index_dir))

            st.success(f"✅ Indexed and saved to `{index_dir}`")
            st.balloons()

            # Show preview
            with st.expander("📝 Content Preview"):
                if chunks:
                    st.write(
                        chunks[0].page_content[:1000]
                        + ("..." if len(chunks[0].page_content) > 1000 else "")
                    )
                else:
                    st.info("No content to preview")

        except Exception as e:
            st.error(f"❌ Ingestion failed: {type(e).__name__} — {str(e)[:200]}")

# TAB 2: Query Assistant
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
                # Implement your query_index function or use:
                embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
                db = FAISS.load_local(str(INDEX_ROOT / index_name), embeddings)
                results = db.similarity_search(query, k=top_k)
                results = [r.page_content for r in results]
            else:
                scraper = WebScraper()
                search_query = web_query or query
                search_results = scraper.search_web(search_query, max_results)

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
                            doc = scraper.scrape_to_document(url)
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

# TAB 3: Chat Assistant
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
    # Add notification state flag
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
            st.session_state.notification_shown = False  # Reset for new response

            try:
                # Add API key verification
                if provider == "openai":
                    openai_key = os.getenv("OPENAI_API_KEY")
                    if not openai_key:
                        st.error(
                            "❌ OpenAI API key not configured! Add OPENAI_API_KEY to your .env file"
                        )
                        st.stop()

                if provider == "anthropic":
                    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
                    if not anthropic_key:
                        st.error(
                            "❌ Anthropic API key not configured! Add ANTHROPIC_API_KEY to your .env file"
                        )
                        st.stop()

                # Create the chain
                with st.spinner("Generating response..."):
                    chain = get_chat_chain(provider=provider, index_name=index_name)

                    # Get response
                    response = chain.invoke({"input": user_input})

                    # Handle different response types
                    if hasattr(
                        response, "content"
                    ):  # For ChatOpenAI/ChatMistralAI responses
                        answer = response.content
                    elif isinstance(response, dict) and "answer" in response:
                        answer = response["answer"]
                    elif isinstance(response, str):
                        answer = response
                    else:
                        answer = str(response)

                    st.session_state.current_response = answer

                    # Add completed conversation to history
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
                elif "api_key" in str(e).lower():
                    error_msg += "\n🔑 API key might be missing or invalid"
                st.error(error_msg)

        # Display current conversation with notification options
        if st.session_state.current_query:
            with st.container():
                st.markdown("### Current Conversation")
                st.markdown(f"**👤 User:** {st.session_state.current_query}")

                if st.session_state.current_response:
                    st.markdown(
                        f"**🤖 Assistant:** {st.session_state.current_response}"
                    )

                    # NOTIFICATION SECTION - INSIDE CURRENT CONVERSATION
                    # Only show once per response
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
                                    if re.match(r"[^@]+@[^@]+\.[^@]+", email):
                                        valid_emails.append(email)
                                    else:
                                        invalid_emails.append(email)

                                if invalid_emails:
                                    st.error(
                                        f"Invalid emails: {', '.join(invalid_emails)}"
                                    )
                                elif not valid_emails:
                                    st.warning("Please enter at least one valid email")
                                else:
                                    # Send request to backend
                                    response = requests.post(
                                        "http://localhost:5000/api/email/send",
                                        json={
                                            "recipients": valid_emails,
                                            "subject": "Chat Assistant Report",
                                            "content": st.session_state.current_response,
                                        },
                                    )

                                    if response.status_code == 200:
                                        st.success("Email sent successfully!")
                                    else:
                                        st.error(
                                            f"Failed to send email: {response.text}"
                                        )
                            except Exception as e:
                                st.error(f"Email sending error: {str(e)}")
                else:
                    st.info("Waiting for response...")

        # Display conversation history
        if st.session_state.chat_history:
            st.markdown("### 💬 Conversation History")
            # Only show previous exchanges, not the current one
            for i, exchange in enumerate(st.session_state.chat_history[:-1]):
                st.markdown(f"**👤 User:** {exchange['user']}")
                st.markdown(f"**🤖 Assistant:** {exchange['assistant']}")
                st.divider()

# TAB 4: AI Agent with Notification
with tab4:
    st.header("🤖 Agent Assistant")

    # Initialize MCP context if available
    if MCP_ENABLED:
        agent_context = ModelContext(
            model_name="gpt-4-turbo",
            model_provider="openai",
            parameters={
                "temperature": 0.5,
                "max_tokens": 2000
            },
            tools=[
                "load_vector_index",
                "send_notification",
                "ingest_document",
                "web_search"
            ]
        )
    else:
        st.info("⚠️ MCP framework not available - using basic agent mode")

    # 📁 Document index handling
    index_list = [
        folder.name
        for folder in INDEX_ROOT.iterdir()
        if folder.is_dir() and (folder / "index.pkl").exists()
    ]

    if not index_list:
        st.warning("⚠️ No indexes found. Please ingest a PDF first.")
        st.stop()

    # 💬 Agent interaction
    index_name = st.selectbox(
        "📂 Choose indexed document", index_list, key="agent_index"
    )
    # Initialize user_prompt to prevent NameError
    user_prompt = st.text_area("💬 Enter your question:", key="agent_prompt", value="")
    use_trace = st.checkbox("🧠 Show agent trace", key="agent_trace")

    # 🔔 NOTIFICATION SETTINGS
    with st.expander("🔔 Notification Options", expanded=False):
        st.markdown("<h4>Notification Settings</h4>", unsafe_allow_html=True)

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
        # Use the session_state version to ensure it exists
        prompt_text = st.session_state.get("agent_prompt", "")

        if not prompt_text.strip():
            st.warning("Please enter a question before running the agent.")
            st.stop()

        try:
            if MCP_ENABLED:
                # Update context with current state
                agent_context.session_id = f"session_{index_name}_{prompt_text[:10]}"
                agent_context.update_parameters(
                    temperature=st.session_state.get("agent_temp", 0.7)
                )

                # Execute agent with context
                response = execute_agent(
                    user_prompt=prompt_text,
                    context=agent_context,
                    index_name=index_name
                )
            else:
                # Fallback to non-MCP agent
                provider = choose_provider(prompt_text, index_name)
                chain = get_chat_chain(provider=provider, index_name=index_name)
                response = chain.invoke({"query": prompt_text})

            # Handle response
            if isinstance(response, dict):
                answer = response.get("answer", str(response))
                source_docs = response.get("source_documents", [])
            else:
                answer = str(response)
                source_docs = []

            # 🟢 SOURCE INDICATOR
            if source_docs:
                source_indicator = (
                    "<div style='margin-bottom: 10px;'>"
                    "📄 <b>Document-based answer</b> - This response was generated using information from the uploaded document(s)"
                    "</div>"
                )
            else:
                source_indicator = (
                    "<div style='margin-bottom: 10px;'>"
                    "🧠 <b>General knowledge answer</b> - This response was generated using the agent's built-in knowledge"
                    "</div>"
                )

            st.markdown(source_indicator, unsafe_allow_html=True)
            st.markdown("### 🧠 Agent Response")
            st.write(answer)

            # 🔔 NOTIFICATION HANDLING
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
                if MCP_ENABLED:
                    st.markdown(f"🤖 Controller Agent selected provider: `{agent_context.model_name}`")
                else:
                    st.markdown(f"🤖 Controller Agent selected provider: `{provider}`")

                if source_docs:
                    st.markdown(f"👁️ Source Documents ({len(source_docs)} found)")
                    for i, doc in enumerate(source_docs, 1):
                        # Clean and extract metadata
                        clean_content = doc.page_content.replace("```", "").strip()
                        source = doc.metadata.get("source", "Unknown document")
                        page = doc.metadata.get("page", "N/A")

                        # Display chunk info
                        with st.expander(
                            f"📄 Chunk {i} (Source: {source}, Page: {page})"
                        ):
                            st.code(clean_content[:1000])  # Show more content
                else:
                    st.info(
                        "No source documents retrieved. This means:"
                        "\n- The answer came from the agent's built-in knowledge"
                        "\n- No documents matched your specific query"
                        "\n- The document index doesn't contain relevant information"
                    )

        except Exception as e:
            st.error(f"🚫 Agent execution failed: {type(e).__name__} — {str(e)[:200]}")
