"""
Training script for Query Intent Classifier
Trains the TensorFlow model on sample query data
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.ml_models.query_intent_classifier import QueryIntentClassifier
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_training_data():
    """
    Get sample training data for intent classification
    In production, replace with your actual query logs
    """
    queries = [
        # Factual queries
        "What is VaultMind?",
        "When was the company founded?",
        "Who is the CEO?",
        "What is the definition of X?",
        "Where is the headquarters located?",
        
        # Analytical queries
        "Why does the system use vector databases?",
        "How does semantic search improve accuracy?",
        "What are the benefits of hybrid search?",
        "Explain the reasoning behind this decision",
        "Analyze the impact of this policy",
        
        # Procedural queries
        "How to ingest documents?",
        "Steps to configure Weaviate",
        "How do I set up authentication?",
        "What is the process for deployment?",
        "Guide me through the installation",
        
        # Comparative queries
        "Difference between Pinecone and Weaviate",
        "Compare FAISS vs Weaviate",
        "What's better: OpenAI or Anthropic?",
        "Pinecone vs Vertex AI comparison",
        "Contrast the two approaches",
        
        # Exploratory queries
        "Tell me about vector databases",
        "Overview of the system architecture",
        "Provide information about enterprise features",
        "Explain the multi-vector storage system",
        "Give me a summary of capabilities"
    ]
    
    labels = [
        # Factual (5)
        'factual', 'factual', 'factual', 'factual', 'factual',
        
        # Analytical (5)
        'analytical', 'analytical', 'analytical', 'analytical', 'analytical',
        
        # Procedural (5)
        'procedural', 'procedural', 'procedural', 'procedural', 'procedural',
        
        # Comparative (5)
        'comparative', 'comparative', 'comparative', 'comparative', 'comparative',
        
        # Exploratory (5)
        'exploratory', 'exploratory', 'exploratory', 'exploratory', 'exploratory'
    ]
    
    return queries, labels


def main():
    """Train the intent classifier"""
    logger.info("Starting Query Intent Classifier training...")
    
    # Get training data
    queries, labels = get_training_data()
    logger.info(f"Loaded {len(queries)} training examples")
    
    # Initialize classifier
    classifier = QueryIntentClassifier()
    
    # Train
    history = classifier.train(
        queries=queries,
        labels=labels,
        validation_split=0.2,
        epochs=20,
        batch_size=4  # Small batch size for small dataset
    )
    
    logger.info("Training completed!")
    logger.info(f"Final training accuracy: {history['accuracy'][-1]:.4f}")
    logger.info(f"Final validation accuracy: {history['val_accuracy'][-1]:.4f}")
    
    # Test on sample queries
    test_queries = [
        "What is the capital of France?",
        "Why is the sky blue?",
        "How to make coffee?",
        "Compare Python vs JavaScript",
        "Tell me about machine learning"
    ]
    
    logger.info("\nTesting on sample queries:")
    for query in test_queries:
        result = classifier.classify_intent(query)
        logger.info(f"Query: {query}")
        logger.info(f"Intent: {result['intent']} (confidence: {result['confidence']:.4f})")
        logger.info(f"Strategy: {classifier.get_retrieval_strategy(result['intent'])}")
        logger.info("")


if __name__ == "__main__":
    main()
