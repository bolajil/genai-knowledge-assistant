"""
Enhanced Multi-Format Document Ingestion

This script provides an enhanced document ingestion pipeline that:
1. Supports multiple file formats (PDF, DOCX, TXT, HTML, MD, CSV, JSON)
2. Handles both individual files and directories
3. Extracts and stores metadata
4. Creates FAISS indexes for vector search
5. Provides detailed processing reports
"""

import argparse
import os
import logging
from pathlib import Path
import time
import json
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import the enhanced document processor
try:
    from utils.enhanced_document_processor import get_document_processor
    document_processor = get_document_processor()
    DOCUMENT_PROCESSOR_AVAILABLE = True
except ImportError:
    logger.error("Enhanced document processor not available")
    DOCUMENT_PROCESSOR_AVAILABLE = False

# Constants
DEFAULT_VECTOR_DB_PATH = "data/faiss_index"
DEFAULT_DATA_DIR = "data"
SUPPORTED_EXTENSIONS = ['.pdf', '.txt', '.md', '.docx', '.html', '.htm', '.csv', '.json']

def ingest_file(file_path: Union[str, Path], custom_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Ingest a single file
    
    Args:
        file_path: Path to the file to ingest
        custom_metadata: Additional metadata to add to the document
    
    Returns:
        Dictionary with ingestion results
    """
    if not DOCUMENT_PROCESSOR_AVAILABLE:
        return {"success": False, "error": "Document processor not available"}
    
    file_path = Path(file_path)
    if not file_path.exists():
        return {"success": False, "error": f"File not found: {file_path}"}
    
    # Check if file type is supported
    if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        return {"success": False, "error": f"Unsupported file type: {file_path.suffix}"}
    
    logger.info(f"Processing file: {file_path}")
    start_time = time.time()
    
    # Process and index the file
    result = document_processor.process_and_index_file(file_path, custom_metadata)
    
    # Add timing information
    result["processing_time"] = time.time() - start_time
    
    return result

def ingest_directory(dir_path: Union[str, Path], recursive: bool = True, 
                     custom_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Ingest all supported files in a directory
    
    Args:
        dir_path: Path to the directory
        recursive: Whether to process subdirectories
        custom_metadata: Additional metadata to add to each document
    
    Returns:
        Dictionary with ingestion results
    """
    if not DOCUMENT_PROCESSOR_AVAILABLE:
        return {"success": False, "error": "Document processor not available"}
    
    dir_path = Path(dir_path)
    if not dir_path.exists() or not dir_path.is_dir():
        return {"success": False, "error": f"Directory not found: {dir_path}"}
    
    logger.info(f"Processing directory: {dir_path} (recursive={recursive})")
    start_time = time.time()
    
    # Process and index the directory
    result = document_processor.process_and_index_directory(dir_path, custom_metadata, recursive)
    
    # Add timing information
    result["processing_time"] = time.time() - start_time
    
    return result

def save_ingestion_report(report: Dict[str, Any], report_path: Union[str, Path] = None) -> str:
    """
    Save an ingestion report to disk
    
    Args:
        report: The ingestion report
        report_path: Path to save the report (optional)
        
    Returns:
        Path to the saved report
    """
    if report_path is None:
        # Generate a default path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = Path(f"data/reports/ingestion_report_{timestamp}.json")
    else:
        report_path = Path(report_path)
    
    # Create the parent directory if it doesn't exist
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Add timestamp to the report
    report["report_timestamp"] = datetime.now().isoformat()
    
    # Save the report as JSON
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    logger.info(f"Saved ingestion report to {report_path}")
    return str(report_path)

def main():
    """Main entry point for the script"""
    parser = argparse.ArgumentParser(description="Enhanced Multi-Format Document Ingestion")
    
    # Required arguments
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", type=str, help="Path to a file to ingest")
    group.add_argument("--directory", type=str, help="Path to a directory of files to ingest")
    
    # Optional arguments
    parser.add_argument("--recursive", action="store_true", help="Process subdirectories recursively")
    parser.add_argument("--vector-db-path", type=str, default=DEFAULT_VECTOR_DB_PATH, 
                        help=f"Path to store FAISS indexes (default: {DEFAULT_VECTOR_DB_PATH})")
    parser.add_argument("--metadata-tags", type=str, help="Comma-separated key=value metadata tags")
    parser.add_argument("--report-path", type=str, help="Path to save the ingestion report")
    
    args = parser.parse_args()
    
    # Create the document processor with the specified vector database path
    global document_processor
    document_processor = get_document_processor(vector_db_path=args.vector_db_path)
    
    # Parse metadata tags
    custom_metadata = {}
    if args.metadata_tags:
        try:
            for tag in args.metadata_tags.split(","):
                key, value = tag.split("=")
                custom_metadata[key.strip()] = value.strip()
            logger.info(f"Using custom metadata: {custom_metadata}")
        except ValueError:
            logger.warning(f"Invalid metadata tags format: {args.metadata_tags}")
    
    # Process file or directory
    if args.file:
        result = ingest_file(args.file, custom_metadata)
    else:  # args.directory
        result = ingest_directory(args.directory, args.recursive, custom_metadata)
    
    # Save the ingestion report
    report_path = save_ingestion_report(result, args.report_path)
    
    # Print summary
    if result.get("success", False):
        if "indexed_files" in result:
            print(f"\n✅ Successfully processed {result['processed_files']} files and indexed {result['indexed_files']} files")
        else:
            print(f"\n✅ Successfully processed and indexed file: {args.file}")
    else:
        print(f"\n❌ Processing failed: {result.get('error', 'Unknown error')}")
    
    print(f"📝 Full report saved to: {report_path}")

if __name__ == "__main__":
    main()
