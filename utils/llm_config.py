"""
Unified LLM Configuration for VaultMind
Centralized LLM model management using real API keys from .env
"""
import os
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class LLMConfig:
    """Centralized LLM configuration manager"""
    
    def __init__(self):
        self.available_models = self._detect_available_models()
    
    def _detect_available_models(self) -> Dict[str, Dict[str, Any]]:
        """Detect available LLM models based on API keys in .env"""
        models = {}
        
        # OpenAI Models
        if os.getenv("OPENAI_API_KEY"):
            models.update({
                "gpt-4o": {
                    "name": "OpenAI GPT-4o",
                    "provider": "openai",
                    "model_id": "gpt-4o",
                    "max_tokens": 128000,
                    "supports_chat": True,
                    "cost_tier": "premium"
                },
                "gpt-4o-mini": {
                    "name": "OpenAI GPT-4o Mini",
                    "provider": "openai",
                    "model_id": "gpt-4o-mini",
                    "max_tokens": 128000,
                    "supports_chat": True,
                    "cost_tier": "standard"
                },
                "gpt-4": {
                    "name": "OpenAI GPT-4",
                    "provider": "openai",
                    "model_id": "gpt-4",
                    "max_tokens": 8192,
                    "supports_chat": True,
                    "cost_tier": "premium"
                },
                "gpt-4-turbo": {
                    "name": "OpenAI GPT-4 Turbo",
                    "provider": "openai", 
                    "model_id": "gpt-4-turbo-preview",
                    "max_tokens": 128000,
                    "supports_chat": True,
                    "cost_tier": "premium"
                },
                "gpt-3.5-turbo": {
                    "name": "OpenAI GPT-3.5 Turbo",
                    "provider": "openai",
                    "model_id": "gpt-3.5-turbo",
                    "max_tokens": 4096,
                    "supports_chat": True,
                    "cost_tier": "standard"
                }
            })
        
        # Anthropic Models
        if os.getenv("ANTHROPIC_API_KEY"):
            models.update({
                "claude-3-opus": {
                    "name": "Anthropic Claude 3 Opus",
                    "provider": "anthropic",
                    "model_id": "claude-3-opus-20240229",
                    "max_tokens": 200000,
                    "supports_chat": True,
                    "cost_tier": "premium"
                },
                "claude-3-sonnet": {
                    "name": "Anthropic Claude 3 Sonnet",
                    "provider": "anthropic",
                    "model_id": "claude-3-sonnet-20240229",
                    "max_tokens": 200000,
                    "supports_chat": True,
                    "cost_tier": "standard"
                },
                "claude-3-haiku": {
                    "name": "Anthropic Claude 3 Haiku",
                    "provider": "anthropic",
                    "model_id": "claude-3-haiku-20240307",
                    "max_tokens": 200000,
                    "supports_chat": True,
                    "cost_tier": "basic"
                }
            })
        
        # Mistral Models
        if os.getenv("MISTRAL_API_KEY"):
            models.update({
                "mistral-large": {
                    "name": "Mistral Large",
                    "provider": "mistral",
                    "model_id": "mistral-large-latest",
                    "max_tokens": 32000,
                    "supports_chat": True,
                    "cost_tier": "premium"
                },
                "mistral-medium": {
                    "name": "Mistral Medium",
                    "provider": "mistral",
                    "model_id": "mistral-medium-latest",
                    "max_tokens": 32000,
                    "supports_chat": True,
                    "cost_tier": "standard"
                },
                "mistral-small": {
                    "name": "Mistral Small",
                    "provider": "mistral",
                    "model_id": "mistral-small-latest",
                    "max_tokens": 32000,
                    "supports_chat": True,
                    "cost_tier": "basic"
                }
            })
        
        # DeepSeek Models
        if os.getenv("DEEPSEEK_API_KEY"):
            models.update({
                "deepseek-chat": {
                    "name": "DeepSeek Chat",
                    "provider": "deepseek",
                    "model_id": "deepseek-chat",
                    "max_tokens": 4096,
                    "supports_chat": True,
                    "cost_tier": "basic"
                },
                "deepseek-coder": {
                    "name": "DeepSeek Coder",
                    "provider": "deepseek",
                    "model_id": "deepseek-coder",
                    "max_tokens": 4096,
                    "supports_chat": True,
                    "cost_tier": "basic"
                }
            })
        
        # Ollama Models (Local)
        if os.getenv("OLLAMA_BASE_URL") or self._check_ollama_available():
            models.update({
                "llama3-8b": {
                    "name": "Llama 3 8B (Ollama)",
                    "provider": "ollama",
                    "model_id": "llama3:8b",
                    "max_tokens": 8192,
                    "supports_chat": True,
                    "cost_tier": "free"
                },
                "llama3-70b": {
                    "name": "Llama 3 70B (Ollama)",
                    "provider": "ollama",
                    "model_id": "llama3:70b",
                    "max_tokens": 8192,
                    "supports_chat": True,
                    "cost_tier": "free"
                },
                "codellama": {
                    "name": "Code Llama (Ollama)",
                    "provider": "ollama",
                    "model_id": "codellama:latest",
                    "max_tokens": 4096,
                    "supports_chat": True,
                    "cost_tier": "free"
                },
                "mistral": {
                    "name": "Mistral 7B (Ollama)",
                    "provider": "ollama",
                    "model_id": "mistral:latest",
                    "max_tokens": 8192,
                    "supports_chat": True,
                    "cost_tier": "free"
                },
                "phi3": {
                    "name": "Phi-3 (Ollama)",
                    "provider": "ollama",
                    "model_id": "phi3:latest",
                    "max_tokens": 4096,
                    "supports_chat": True,
                    "cost_tier": "free"
                }
            })
        
        # Groq Models (if available)
        if os.getenv("GROQ_API_KEY"):
            models.update({
                "llama-3-70b-groq": {
                    "name": "Llama 3 70B (Groq)",
                    "provider": "groq",
                    "model_id": "llama3-70b-8192",
                    "max_tokens": 8192,
                    "supports_chat": True,
                    "cost_tier": "standard"
                },
                "mixtral-8x7b-groq": {
                    "name": "Mixtral 8x7B (Groq)",
                    "provider": "groq",
                    "model_id": "mixtral-8x7b-32768",
                    "max_tokens": 32768,
                    "supports_chat": True,
                    "cost_tier": "standard"
                }
            })
        
        logger.info(f"Detected {len(models)} available LLM models")
        return models
    
    def get_available_models(self) -> List[str]:
        """Get list of available model names for UI selection"""
        if not self.available_models:
            return ["No LLM models available - Please check API keys in .env file"]
        
        return [config["name"] for config in self.available_models.values()]
    
    def get_model_config(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific model by name"""
        for model_id, config in self.available_models.items():
            if config["name"] == model_name:
                return config
        return None
    
    def get_default_model(self) -> str:
        """Get default model name (prefer GPT-3.5 Turbo if available)"""
        if not self.available_models:
            return "No models available"
        
        # Preferred order: GPT-4o Mini, GPT-3.5 Turbo, Claude 3 Haiku, Ollama, any available
        preferred_models = ["gpt-4o-mini", "gpt-3.5-turbo", "claude-3-haiku", "llama3-8b", "mistral"]
        
        for model_id in preferred_models:
            if model_id in self.available_models:
                return self.available_models[model_id]["name"]
        
        # Return first available model
        return list(self.available_models.values())[0]["name"]
    
    def get_models_by_tier(self, tier: str) -> List[str]:
        """Get models by cost tier (basic, standard, premium)"""
        return [
            config["name"] 
            for config in self.available_models.values() 
            if config.get("cost_tier") == tier
        ]
    
    def _check_ollama_available(self) -> bool:
        """Check if Ollama is running locally"""
        try:
            import requests
            ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            response = requests.get(f"{ollama_url}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def validate_api_keys(self) -> Dict[str, bool]:
        """Validate which API keys are available"""
        return {
            "OpenAI": bool(os.getenv("OPENAI_API_KEY")),
            "Anthropic": bool(os.getenv("ANTHROPIC_API_KEY")),
            "Mistral": bool(os.getenv("MISTRAL_API_KEY")),
            "DeepSeek": bool(os.getenv("DEEPSEEK_API_KEY")),
            "Groq": bool(os.getenv("GROQ_API_KEY")),
            "Ollama": bool(os.getenv("OLLAMA_BASE_URL")) or self._check_ollama_available()
        }

# Global instance
llm_config = LLMConfig()

def get_available_llm_models() -> List[str]:
    """Get available LLM models for UI components"""
    return llm_config.get_available_models()

def get_default_llm_model() -> str:
    """Get default LLM model"""
    return llm_config.get_default_model()

def get_llm_model_config(model_name: str) -> Optional[Dict[str, Any]]:
    """Get LLM model configuration"""
    return llm_config.get_model_config(model_name)

def validate_llm_setup(model_name: str) -> (bool, str):
    """Validate setup for a specific LLM model."""
    if not model_name or model_name == "No models available" or model_name == "No LLM models available - Please check API keys in .env file":
        return False, "No model selected or available"

    config = llm_config.get_model_config(model_name)
    if not config:
        return False, f"Config not found for {model_name}"

    provider = config.get("provider")
    if not provider:
        return False, "Provider not specified in config"

    api_keys = llm_config.validate_api_keys()

    provider_map = {
        'openai': 'OpenAI',
        'anthropic': 'Anthropic',
        'mistral': 'Mistral',
        'deepseek': 'DeepSeek',
        'groq': 'Groq',
        'ollama': 'Ollama'
    }
    
    provider_key = provider_map.get(provider.lower())

    if provider_key and api_keys.get(provider_key):
        return True, f"{model_name} ready"
    elif provider_key:
        return False, f"API key for {provider_key} not found"
    else:
        return False, f"Unknown provider: {provider}"
