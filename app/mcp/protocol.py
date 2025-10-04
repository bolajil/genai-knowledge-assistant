from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List

class ModelContext(BaseModel):
    """
    Standardized context protocol for AI models
    """
    model_config = {'protected_namespaces': ()}
    
    model_name: str = Field(..., description="Name of the AI model")
    model_provider: str = Field(..., description="Provider of the model")
    parameters: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Model-specific parameters"
    )
    context_window: int = Field(
        default=4096, 
        description="Token limit for context"
    )
    tools: List[str] = Field(
        default_factory=list, 
        description="List of available tools"
    )
    session_id: Optional[str] = Field(
        None, 
        description="Session identifier for continuity"
    )
    memory: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Session memory store"
    )

    def add_to_memory(self, key: str, value: Any):
        """Add information to session memory"""
        self.memory[key] = value

    def get_from_memory(self, key: str, default: Any = None):
        """Retrieve information from session memory"""
        return self.memory.get(key, default)

    def update_parameters(self, **kwargs):
        """Update model parameters"""
        self.parameters.update(kwargs)
