# Enhanced Research Module - Implementation Guide

## Overview

The Enhanced Research Module adds comprehensive research capabilities to the VaultMind platform. This module enables:

1. **Multi-Source Search**: Search across multiple knowledge sources simultaneously
2. **Enhanced Content Generation**: Generate structured research reports, analyses, and insights
3. **Seamless Integration**: Integrate with the existing VaultMind UI and API

This guide provides instructions for implementing and using the enhanced research functionality.

## Files and Structure

The enhanced research module consists of the following files:

- `utils/new_enhanced_research.py`: Core functionality for generating research content
- `utils/enhanced_multi_source_search.py`: Multi-source search implementation
- `ui/enhanced_research_ui.py`: Streamlit UI components for the research interface
- `utils/research_integration.py`: Integration with the VaultMind platform
- `demo_enhanced_research.py`: Demonstration script to test the functionality

## Installation

1. Ensure all files are placed in their respective directories within the VaultMind project structure.
2. Install any additional dependencies:

```bash
pip install -r requirements.txt
```

## Integration with VaultMind

### Method 1: Direct Import in main.py

Add the following code to your `main.py` file:

```python
from utils.research_integration import initialize_research_integration

# Initialize VaultMind app as usual
app = initialize_app()

# Initialize and register research integration
research_integration = initialize_research_integration(app)
```

### Method 2: Add as a Tab in the Streamlit UI

If you're using the modular tab system, add the following to your tab configuration:

1. Update `vaultmind_tabs.json` to include the research tab:

```json
{
  "tabs": [
    // ... existing tabs
    {
      "name": "Enhanced Research",
      "icon": "search",
      "module": "ui.enhanced_research_ui",
      "function": "render_research_ui"
    }
  ]
}
```

2. Import the module in your dashboard file:

```python
# In genai_dashboard_modular.py or similar
from ui.enhanced_research_ui import render_research_ui

# Add to your tab system
```

### Method 3: Agent Integration

To enable enhanced research as an agent capability:

```python
from utils.research_integration import ResearchIntegration

# In your agent setup code
research = ResearchIntegration()
agent.register_tool(
    name="enhanced_research",
    description="Perform comprehensive research on a topic",
    function=research.generate_research
)
```

## Configuration

Create a configuration file `config/research_config.json` to customize the research module:

```json
{
  "enabled": true,
  "default_sources": [
    "VaultMind Knowledge Base",
    "FAISS Vector Index"
  ],
  "max_results_per_source": 5,
  "use_external_sources": true,
  "external_sources": [
    "Web Search (External)",
    "AWS Documentation (External)"
  ]
}
```

Then load the configuration when initializing:

```python
research_integration = initialize_research_integration(
    app, 
    config_path="config/research_config.json"
)
```

## Using the Enhanced Research Module

### Via the UI

1. Navigate to the Enhanced Research tab in the VaultMind UI
2. Enter your research task or query
3. Select the research operation type
4. Choose knowledge sources to search
5. Click "Generate Research" to create your research report

### Programmatically

```python
from utils.research_integration import ResearchIntegration

research = ResearchIntegration()

# Generate research content
result = research.generate_research(
    task="AWS cloud cost optimization strategies",
    operation="Research Topic",
    knowledge_sources=["FAISS Vector Index", "Web Search (External)"]
)

print(result)
```

## Supported Research Operations

The module supports the following research operations:

1. **Research Topic**: Generate comprehensive research reports on any topic
2. **Data Analysis**: Analyze data and identify patterns and insights
3. **Problem Solving**: Analyze problems and propose solutions
4. **Trend Identification**: Identify and analyze emerging trends

## Testing

Run the demo script to test the enhanced research functionality:

```bash
python demo_enhanced_research.py
```

This will generate sample research reports using placeholder data for demonstration purposes.

## Customization

### Adding New Research Operations

To add a new research operation type:

1. Update the `generate_enhanced_research_content` function in `utils/new_enhanced_research.py`
2. Add the new operation to the UI in `ui/enhanced_research_ui.py`

### Adding New Knowledge Sources

To add a new knowledge source:

1. Update the `get_available_sources` function in `utils/enhanced_multi_source_search.py`
2. Implement the search logic in the `search_source` function

## Troubleshooting

### Common Issues

1. **ImportError**: Ensure all files are in the correct directories and dependencies are installed
2. **Missing Sources**: Check that the knowledge sources are properly configured
3. **UI Not Showing**: Verify that the UI integration is correctly set up

### Logging

The enhanced research module uses Python's logging system. To enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Contributing

When extending or modifying the enhanced research module:

1. Maintain the separation of concerns between content generation and search
2. Follow the existing code style and documentation patterns
3. Add tests for new functionality
4. Update this guide with any significant changes

## Future Enhancements

Planned future enhancements include:

1. Support for additional external knowledge sources
2. Advanced filtering and sorting of search results
3. Custom research templates for different industries
4. Integration with visualization tools for data-heavy research
