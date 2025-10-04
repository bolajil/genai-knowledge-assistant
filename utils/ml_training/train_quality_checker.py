"""
Training script for Data Quality Checker
Trains the TensorFlow autoencoder on document embeddings
"""

import sys
from pathlib import Path
import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.ml_models.data_quality_checker import DataQualityChecker
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_sample_embeddings(n_samples=100, embedding_dim=384):
    """
    Generate sample embeddings for training
    In production, use actual document embeddings from your corpus
    """
    # Generate normal embeddings (high quality)
    normal_embeddings = np.random.randn(n_samples, embedding_dim) * 0.5 + 0.5
    
    # Add some anomalies (low quality)
    n_anomalies = int(n_samples * 0.05)  # 5% anomalies
    anomalies = np.random.randn(n_anomalies, embedding_dim) * 2.0  # Higher variance
    
    # Combine
    all_embeddings = np.vstack([normal_embeddings, anomalies])
    
    # Normalize to [0, 1]
    all_embeddings = np.clip(all_embeddings, 0, 1)
    
    return all_embeddings


def main():
    """Train the data quality checker"""
    logger.info("Starting Data Quality Checker training...")
    
    # Generate sample embeddings
    embeddings = generate_sample_embeddings(n_samples=100, embedding_dim=384)
    logger.info(f"Generated {len(embeddings)} sample embeddings")
    
    # Initialize checker
    checker = DataQualityChecker(embedding_dim=384)
    
    # Train
    history = checker.train(
        embeddings=embeddings,
        validation_split=0.2,
        epochs=50,
        batch_size=16,
        anomaly_percentile=95.0
    )
    
    logger.info("Training completed!")
    logger.info(f"Final training loss: {history['loss'][-1]:.6f}")
    logger.info(f"Final validation loss: {history['val_loss'][-1]:.6f}")
    
    # Test on sample embeddings
    test_embeddings = generate_sample_embeddings(n_samples=10, embedding_dim=384)
    
    logger.info("\nTesting quality checker:")
    results = checker.check_batch(test_embeddings)
    
    for i, result in enumerate(results):
        logger.info(f"Document {i+1}:")
        logger.info(f"  Quality Score: {result['quality_score']:.4f}")
        logger.info(f"  Quality Level: {result['quality_level']}")
        logger.info(f"  Is Anomaly: {result['is_anomaly']}")
        logger.info("")
    
    # Generate quality report
    report = checker.get_quality_report(test_embeddings)
    logger.info("\nQuality Report:")
    logger.info(f"Total Documents: {report['total_documents']}")
    logger.info(f"Average Quality Score: {report['average_quality_score']:.4f}")
    logger.info(f"Anomaly Count: {report['anomaly_count']}")
    logger.info(f"Duplicate Pairs: {report['duplicate_pairs']}")
    logger.info(f"Quality Distribution: {report['quality_distribution']}")
    logger.info(f"\nRecommendations:")
    for rec in report['recommendations']:
        logger.info(f"  - {rec}")


if __name__ == "__main__":
    main()
