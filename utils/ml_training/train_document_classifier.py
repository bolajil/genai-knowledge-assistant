"""
Training script for Document Classifier
Trains the PyTorch model on sample document data
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.ml_models.document_classifier import DocumentClassifier
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_training_data():
    """
    Get sample training data for document classification
    In production, replace with your actual documents
    """
    documents = [
        # Legal
        "This agreement is entered into between the parties. The terms and conditions are as follows. Liability and indemnity clauses apply.",
        "Contract for services. Confidentiality provisions. Warranty and compliance requirements.",
        
        # Technical
        "System architecture diagram. API specifications and endpoints. Database schema and configuration.",
        "Technical documentation for the platform. Implementation guide and deployment procedures.",
        
        # Financial
        "Quarterly revenue report. Profit and loss statement. Budget forecast for next fiscal year.",
        "Financial analysis. Cash flow projections. Investment returns and ROI calculations.",
        
        # HR
        "Employee handbook. Company policies and procedures. Benefits and compensation information.",
        "Performance review guidelines. Training and development programs. HR policies.",
        
        # Operations
        "Standard operating procedures. Workflow documentation. Process optimization guidelines.",
        "Operations manual. Quality control procedures. Operational efficiency metrics."
    ]
    
    labels = [
        'legal', 'legal',
        'technical', 'technical',
        'financial', 'financial',
        'hr', 'hr',
        'operations', 'operations'
    ]
    
    return documents, labels


def main():
    """Train the document classifier"""
    logger.info("Starting Document Classifier training...")
    
    # Get training data
    documents, labels = get_training_data()
    logger.info(f"Loaded {len(documents)} training examples")
    
    # Initialize classifier
    classifier = DocumentClassifier()
    
    # Train
    result = classifier.train(
        documents=documents,
        labels=labels,
        validation_split=0.2,
        epochs=3,
        batch_size=2,  # Small batch size for small dataset
        learning_rate=2e-5
    )
    
    logger.info("Training completed!")
    logger.info(f"Training loss: {result['train_loss']:.4f}")
    
    # Test on sample documents
    test_docs = [
        "This contract outlines the terms of agreement between parties.",
        "API documentation and technical specifications for the system.",
        "Annual financial report with revenue and expense breakdown."
    ]
    
    logger.info("\nTesting on sample documents:")
    for doc in test_docs:
        result = classifier.classify_document(doc, return_all_scores=True)
        logger.info(f"Document: {doc[:60]}...")
        logger.info(f"Category: {result['category']} (confidence: {result['confidence']:.4f})")
        logger.info(f"Metadata: {result['metadata']}")
        logger.info("")


if __name__ == "__main__":
    main()
