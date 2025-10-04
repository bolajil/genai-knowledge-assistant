import os
import sys
import logging
from pathlib import Path
try:
    from dotenv import load_dotenv  # type: ignore
except Exception:
    load_dotenv = None
from utils.weaviate_manager import WeaviateManager

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment from config/weaviate.env (if present)
env_path = Path(__file__).parent / "config" / "weaviate.env"
if env_path.exists():
    if load_dotenv is not None:
        load_dotenv(env_path.as_posix())
    else:
        # Minimal .env parser fallback
        try:
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
        except Exception:
            pass

def test_connection():
    """Test Weaviate connection with updated prefix discovery logic"""
    try:
        # Initialize Weaviate manager with the correct endpoint URL (env override supported)
        manager = WeaviateManager(
            url=os.getenv("WEAVIATE_URL", "https://r5dyopgssm6a9xfo2yg7a.c0.us-west3.gcp.weaviate.cloud"),
            api_key=os.getenv("WEAVIATE_API_KEY"),
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        logger.info(f"Initialized WeaviateManager with URL: {manager.url}")

        # Prefer SDK readiness (works on WCS without path prefixes)
        ready = False
        try:
            ready = manager.client.is_ready()
            logger.info(f"Client readiness: {ready}")
            print(f"READY:{ready}")
        except Exception as e:
            logger.warning(f"SDK readiness check failed: {e}")

        # Test listing collections (SDK first, REST fallback handled inside)
        collections = manager.list_collections()
        print(f"COLLECTIONS:{collections}")
        if collections:
            logger.info(f"Available collections: {collections}")
            return True
        else:
            logger.error("No collections found via SDK/REST")
            return ready
            
    except Exception as e:
        logger.error(f"Error testing connection: {e}")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
