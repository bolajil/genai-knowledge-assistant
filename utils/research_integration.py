"""
Integration module for the enhanced research functionality.
This module provides functions to integrate the enhanced research capabilities 
with the main VaultMind application.
"""

import logging
from typing import List, Dict, Any, Optional
import json
import os

# Configure logging
logger = logging.getLogger(__name__)

class ResearchIntegration:
    """Class to handle integration of enhanced research with VaultMind"""
    
    def __init__(self, config_path=None):
        """
        Initialize the research integration.
        
        Args:
            config_path: Optional path to a configuration file
        """
        self.config = self._load_config(config_path)
        self.enabled = self.config.get("enabled", True)
        self._setup_sources()
    
    def _load_config(self, config_path=None) -> Dict[str, Any]:
        """
        Load configuration from file or use defaults.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Configuration dictionary
        """
        default_config = {
            "enabled": True,
            "default_sources": [
                "VaultMind Knowledge Base",
                "FAISS Vector Index"
            ],
            "max_results_per_source": 5,
            "use_external_sources": True,
            "external_sources": [
                "Web Search (External)",
                "AWS Documentation (External)"
            ]
        }
        
        if not config_path or not os.path.exists(config_path):
            logger.info("Using default research integration configuration")
            return default_config
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            logger.info(f"Loaded research integration configuration from {config_path}")
            return config
        except Exception as e:
            logger.error(f"Error loading research configuration: {str(e)}")
            return default_config
    
    def _setup_sources(self):
        """Set up the available research sources"""
        try:
            from utils.enhanced_multi_source_search import get_available_sources
            self.available_sources = get_available_sources()
        except ImportError:
            logger.warning("Could not import get_available_sources, using default sources")
            self.available_sources = [
                "VaultMind Knowledge Base",
                "FAISS Vector Index",
                "Web Search (External)",
                "Technical Documentation",
                "Enterprise Wiki",
                "AWS Documentation (External)",
                "Cloud Provider APIs (External)"
            ]
    
    def get_enabled_sources(self) -> List[str]:
        """
        Get the list of enabled research sources.
        
        Returns:
            List of enabled source names
        """
        if not self.enabled:
            return []
        
        enabled_sources = self.config.get("default_sources", [])
        
        # Add external sources if enabled
        if self.config.get("use_external_sources", True):
            enabled_sources.extend(self.config.get("external_sources", []))
        
        # Filter to only include available sources
        return [source for source in enabled_sources if source in self.available_sources]
    
    def generate_research(self, task: str, operation: str, knowledge_sources: Optional[List[str]] = None) -> str:
        """
        Generate enhanced research content.
        
        Args:
            task: The research task or query
            operation: The type of operation
            knowledge_sources: Optional list of knowledge sources to use
            
        Returns:
            Generated research content
        """
        if not self.enabled:
            return "Enhanced research functionality is currently disabled."
        
        try:
            # Import research modules
            from utils.new_enhanced_research import generate_enhanced_research_content
            
            # Use provided sources or default to enabled sources
            sources_to_use = knowledge_sources if knowledge_sources else self.get_enabled_sources()
            
            # Generate research content
            content = generate_enhanced_research_content(
                task=task,
                operation=operation,
                knowledge_sources=sources_to_use
            )
            
            return content
            
        except ImportError as e:
            logger.error(f"Import error in research integration: {str(e)}")
            return f"Error: Required modules not available - {str(e)}"
        except Exception as e:
            logger.error(f"Error generating research in integration: {str(e)}")
            return f"Error generating research: {str(e)}"
    
    def register_with_vaultmind(self, app=None):
        """
        Register the enhanced research functionality with the VaultMind app.
        
        Args:
            app: The VaultMind application instance
        """
        if not self.enabled:
            logger.info("Enhanced research integration is disabled, not registering")
            return
        
        if not app:
            logger.warning("No app provided to register research integration")
            return
        
        try:
            # Register the research module with the app
            # Implementation depends on how VaultMind's extension system works
            logger.info("Registering enhanced research integration with VaultMind")
            
            # Add UI components if applicable
            try:
                from ui.enhanced_research_ui import add_to_dashboard
                
                # Register with dashboard if it exists
                if hasattr(app, 'dashboard') and app.dashboard:
                    add_to_dashboard(app.dashboard)
                    logger.info("Added enhanced research UI to dashboard")
            except ImportError:
                logger.warning("Could not import enhanced_research_ui module")
            
            # Register research as an agent capability if applicable
            if hasattr(app, 'register_capability'):
                app.register_capability(
                    name="enhanced_research",
                    description="Perform enhanced research across multiple knowledge sources",
                    handler=self.generate_research
                )
                logger.info("Registered enhanced research as an agent capability")
            
            logger.info("Enhanced research integration complete")
            
        except Exception as e:
            logger.error(f"Error registering research integration: {str(e)}")

# Example usage
def initialize_research_integration(app=None, config_path=None):
    """
    Initialize and register the enhanced research integration.
    
    Args:
        app: Optional VaultMind app instance
        config_path: Optional path to configuration file
        
    Returns:
        ResearchIntegration instance
    """
    integration = ResearchIntegration(config_path)
    
    if app:
        integration.register_with_vaultmind(app)
    
    return integration

if __name__ == "__main__":
    # Test the integration
    logging.basicConfig(level=logging.INFO)
    
    integration = ResearchIntegration()
    enabled_sources = integration.get_enabled_sources()
    
    print(f"Enabled sources: {', '.join(enabled_sources)}")
    
    # Test research generation
    research = integration.generate_research(
        task="Cloud cost optimization strategies",
        operation="Research Topic"
    )
    
    print("\nSample Research Output:")
    print("=" * 80)
    print(research[:500] + "...\n[truncated]")
    print("=" * 80)
