import os
import sys
import argparse
import logging
import traceback

from utils.weaviate_manager import get_weaviate_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("create_and_list_weaviate_collection")


def main():
    parser = argparse.ArgumentParser(description="Create a Weaviate collection and list all collections")
    parser.add_argument("--name", "-n", default="Bylaws20", help="Collection name to create")
    parser.add_argument("--description", "-d", default="Bylaws test collection", help="Collection description")
    parser.add_argument(
        "--no-openai", action="store_true", help="Ignore OPENAI_API_KEY; create without OpenAI vectorization"
    )
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug logging and verbose error output"
    )
    args = parser.parse_args()

    # Optionally disable OpenAI vectorization for this run
    if args.no_openai:
        os.environ.pop("OPENAI_API_KEY", None)

    if args.debug:
        logger.setLevel(logging.DEBUG)
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        try:
            fh = logging.FileHandler("weaviate_run.log", mode="a", encoding="utf-8")
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s'))
            root_logger.addHandler(fh)
            logger.debug("Debug logging enabled; writing to weaviate_run.log")
        except Exception as log_err:
            logger.warning("Could not attach file logger: %s", log_err)
    
    # Show environment config summary (without secrets)
    weaviate_url = os.getenv("WEAVIATE_URL")
    api_key_set = bool(os.getenv("WEAVIATE_API_KEY"))
    openai_set = bool(os.getenv("OPENAI_API_KEY"))
    logger.info("Env: WEAVIATE_URL=%s | WEAVIATE_API_KEY set=%s | OPENAI_API_KEY set=%s", weaviate_url, api_key_set, openai_set)

    mgr = get_weaviate_manager()
    logger.info("Target URL (normalized): %s", os.getenv("WEAVIATE_URL"))

    try:
        # Create collection using manager (SDK-first, REST fallback on failure)
        ok = mgr.create_collection(collection_name=args.name, description=args.description, properties=None)
        if ok:
            print(f"[OK] Created or verified collection '{args.name}'")
        else:
            print(f"[ERROR] Failed to create collection '{args.name}'")
            return 2

        # List collections (SDK-first, REST fallbacks)
        names = mgr.list_collections()
        print("Collections:", names)
        return 0
    except Exception as e:
        logger.error("Unhandled error during creation/listing: %s", e)
        if args.debug:
            traceback.print_exc()
        return 1
    finally:
        try:
            mgr.close()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
