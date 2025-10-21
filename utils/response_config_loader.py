"""
Enterprise Response Configuration Loader

Loads and manages configuration for enterprise response formatting.
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class ResponseConfig:
    """Configuration for enterprise response formatting"""
    
    # Response structure
    include_executive_summary: bool = True
    include_detailed_answer: bool = True
    include_key_points: bool = True
    include_information_gaps: bool = True
    include_related_topics: bool = False
    include_confidence_scores: bool = False
    
    # Content extraction
    max_detailed_sources: int = 3
    max_key_points: int = 5
    min_sentence_length: int = 20
    min_key_point_length: int = 30
    max_snippet_length: int = 250
    summary_sentences: int = 2
    sentences_per_source: int = 3
    
    # Text cleaning
    remove_page_breaks: bool = True
    remove_ocr_artifacts: bool = True
    remove_headers_footers: bool = True
    normalize_whitespace: bool = True
    min_line_length: int = 3
    custom_removal_patterns: list = field(default_factory=list)
    
    # Citations
    citation_format: str = "inline"
    include_page_numbers: bool = True
    include_sections: bool = False
    include_relevance_scores: bool = True
    score_format: str = "percentage"
    min_score_display: float = 0.0
    
    # Information gaps
    excellent_threshold: int = 5
    good_threshold: int = 3
    fair_threshold: int = 2
    poor_threshold: int = 1
    gap_messages: Dict[str, str] = field(default_factory=dict)
    
    # LLM settings
    use_structured_fallback: bool = True
    min_valid_response_length: int = 50
    max_tokens: int = 900
    temperature: float = 0.3
    model_preferences: list = field(default_factory=list)
    
    # Display settings
    use_markdown: bool = True
    use_emojis: bool = True
    source_numbering: str = "numbered"
    show_source_metadata: bool = True
    metadata_fields: list = field(default_factory=lambda: ["source", "page", "relevance_score"])
    use_block_quotes: bool = True
    source_spacing: bool = True
    highlight_query_terms: bool = False
    
    # Style presets
    style_presets: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Performance
    cache_cleaned_text: bool = True
    cache_ttl: int = 3600
    parallel_processing: bool = False
    max_processing_time: int = 30
    
    # Logging
    log_responses: bool = True
    log_fallbacks: bool = True
    log_performance: bool = True
    log_level: str = "INFO"
    
    # Export
    include_metadata_export: bool = True
    export_formats: list = field(default_factory=lambda: ["markdown", "pdf", "docx", "json"])
    default_export_format: str = "markdown"
    include_timestamp: bool = True
    include_query: bool = True


class ResponseConfigLoader:
    """Loads and manages enterprise response configuration"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration loader
        
        Args:
            config_path: Path to YAML config file. If None, uses default location.
        """
        if config_path is None:
            # Default to config/enterprise_response_config.yml
            base_path = Path(__file__).parent.parent
            config_path = base_path / "config" / "enterprise_response_config.yml"
        
        self.config_path = Path(config_path)
        self._config: Optional[ResponseConfig] = None
        self._raw_config: Optional[Dict[str, Any]] = None
        
    def load_config(self) -> ResponseConfig:
        """Load configuration from YAML file"""
        try:
            if not self.config_path.exists():
                logger.warning(f"Config file not found: {self.config_path}. Using defaults.")
                return ResponseConfig()
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._raw_config = yaml.safe_load(f)
            
            if not self._raw_config:
                logger.warning("Config file is empty. Using defaults.")
                return ResponseConfig()
            
            # Parse configuration sections
            config = ResponseConfig()
            
            # Response structure
            if 'response_structure' in self._raw_config:
                rs = self._raw_config['response_structure']
                config.include_executive_summary = rs.get('include_executive_summary', True)
                config.include_detailed_answer = rs.get('include_detailed_answer', True)
                config.include_key_points = rs.get('include_key_points', True)
                config.include_information_gaps = rs.get('include_information_gaps', True)
                config.include_related_topics = rs.get('include_related_topics', False)
                config.include_confidence_scores = rs.get('include_confidence_scores', False)
            
            # Content extraction
            if 'content_extraction' in self._raw_config:
                ce = self._raw_config['content_extraction']
                config.max_detailed_sources = ce.get('max_detailed_sources', 3)
                config.max_key_points = ce.get('max_key_points', 5)
                config.min_sentence_length = ce.get('min_sentence_length', 20)
                config.min_key_point_length = ce.get('min_key_point_length', 30)
                config.max_snippet_length = ce.get('max_snippet_length', 250)
                config.summary_sentences = ce.get('summary_sentences', 2)
                config.sentences_per_source = ce.get('sentences_per_source', 3)
            
            # Text cleaning
            if 'text_cleaning' in self._raw_config:
                tc = self._raw_config['text_cleaning']
                config.remove_page_breaks = tc.get('remove_page_breaks', True)
                config.remove_ocr_artifacts = tc.get('remove_ocr_artifacts', True)
                config.remove_headers_footers = tc.get('remove_headers_footers', True)
                config.normalize_whitespace = tc.get('normalize_whitespace', True)
                config.min_line_length = tc.get('min_line_length', 3)
                config.custom_removal_patterns = tc.get('custom_removal_patterns', [])
            
            # Citations
            if 'citations' in self._raw_config:
                cit = self._raw_config['citations']
                config.citation_format = cit.get('format', 'inline')
                config.include_page_numbers = cit.get('include_page_numbers', True)
                config.include_sections = cit.get('include_sections', False)
                config.include_relevance_scores = cit.get('include_relevance_scores', True)
                config.score_format = cit.get('score_format', 'percentage')
                config.min_score_display = cit.get('min_score_display', 0.0)
            
            # Information gaps
            if 'information_gaps' in self._raw_config:
                ig = self._raw_config['information_gaps']
                config.excellent_threshold = ig.get('excellent_threshold', 5)
                config.good_threshold = ig.get('good_threshold', 3)
                config.fair_threshold = ig.get('fair_threshold', 2)
                config.poor_threshold = ig.get('poor_threshold', 1)
                config.gap_messages = ig.get('messages', {})
            
            # LLM settings
            if 'llm_settings' in self._raw_config:
                llm = self._raw_config['llm_settings']
                config.use_structured_fallback = llm.get('use_structured_fallback', True)
                config.min_valid_response_length = llm.get('min_valid_response_length', 50)
                config.max_tokens = llm.get('max_tokens', 900)
                config.temperature = llm.get('temperature', 0.3)
                config.model_preferences = llm.get('model_preferences', [])
            
            # Display settings
            if 'display' in self._raw_config:
                disp = self._raw_config['display']
                config.use_markdown = disp.get('use_markdown', True)
                config.use_emojis = disp.get('use_emojis', True)
                config.source_numbering = disp.get('source_numbering', 'numbered')
                config.show_source_metadata = disp.get('show_source_metadata', True)
                config.metadata_fields = disp.get('metadata_fields', ['source', 'page', 'relevance_score'])
                config.use_block_quotes = disp.get('use_block_quotes', True)
                config.source_spacing = disp.get('source_spacing', True)
                config.highlight_query_terms = disp.get('highlight_query_terms', False)
            
            # Style presets
            if 'style_presets' in self._raw_config:
                config.style_presets = self._raw_config['style_presets']
            
            # Performance
            if 'performance' in self._raw_config:
                perf = self._raw_config['performance']
                config.cache_cleaned_text = perf.get('cache_cleaned_text', True)
                config.cache_ttl = perf.get('cache_ttl', 3600)
                config.parallel_processing = perf.get('parallel_processing', False)
                config.max_processing_time = perf.get('max_processing_time', 30)
            
            # Logging
            if 'logging' in self._raw_config:
                log = self._raw_config['logging']
                config.log_responses = log.get('log_responses', True)
                config.log_fallbacks = log.get('log_fallbacks', True)
                config.log_performance = log.get('log_performance', True)
                config.log_level = log.get('log_level', 'INFO')
            
            # Export
            if 'export' in self._raw_config:
                exp = self._raw_config['export']
                config.include_metadata_export = exp.get('include_metadata', True)
                config.export_formats = exp.get('formats', ['markdown', 'pdf', 'docx', 'json'])
                config.default_export_format = exp.get('default_format', 'markdown')
                config.include_timestamp = exp.get('include_timestamp', True)
                config.include_query = exp.get('include_query', True)
            
            self._config = config
            logger.info(f"Loaded enterprise response configuration from {self.config_path}")
            return config
            
        except Exception as e:
            logger.error(f"Error loading config from {self.config_path}: {e}")
            logger.info("Using default configuration")
            return ResponseConfig()
    
    def get_config(self) -> ResponseConfig:
        """Get current configuration (loads if not already loaded)"""
        if self._config is None:
            self._config = self.load_config()
        return self._config
    
    def apply_preset(self, preset_name: str) -> ResponseConfig:
        """
        Apply a style preset to the configuration
        
        Args:
            preset_name: Name of preset (standard, executive, technical, quick)
            
        Returns:
            Updated configuration
        """
        config = self.get_config()
        
        if preset_name not in config.style_presets:
            logger.warning(f"Preset '{preset_name}' not found. Using current config.")
            return config
        
        preset = config.style_presets[preset_name]
        
        # Apply preset settings
        if 'sections' in preset:
            sections = preset['sections']
            config.include_executive_summary = sections.get('executive_summary', True)
            config.include_detailed_answer = sections.get('detailed_answer', True)
            config.include_key_points = sections.get('key_points', True)
            config.include_information_gaps = sections.get('information_gaps', True)
        
        if 'max_detailed_sources' in preset:
            config.max_detailed_sources = preset['max_detailed_sources']
        
        if 'max_key_points' in preset:
            config.max_key_points = preset['max_key_points']
        
        if 'summary_sentences' in preset:
            config.summary_sentences = preset['summary_sentences']
        
        if 'sentences_per_source' in preset:
            config.sentences_per_source = preset['sentences_per_source']
        
        logger.info(f"Applied preset: {preset_name}")
        return config
    
    def reload_config(self) -> ResponseConfig:
        """Reload configuration from file"""
        self._config = None
        return self.load_config()


# Global configuration instance
_config_loader = ResponseConfigLoader()


def get_response_config() -> ResponseConfig:
    """Get global response configuration"""
    return _config_loader.get_config()


def reload_response_config() -> ResponseConfig:
    """Reload global response configuration"""
    return _config_loader.reload_config()


def apply_response_preset(preset_name: str) -> ResponseConfig:
    """Apply a style preset to global configuration"""
    return _config_loader.apply_preset(preset_name)
