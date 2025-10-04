"""
VaultMIND Knowledge Assistant - Dash UI (Exact Streamlit Replica)

This module provides a Dash user interface that exactly replicates the Streamlit app design.
"""

import dash
from dash import dcc, html, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc
import requests
import logging
from datetime import datetime
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
API_URL = os.environ.get("API_URL", "http://localhost:8000")

# Initialize Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "VaultMIND Knowledge Assistant"

# Custom CSS to exactly match Streamlit styling
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            body {
                font-family: "Source Sans Pro", sans-serif;
                background-color: #ffffff;
                margin: 0;
                padding: 0;
            }
            .main-container {
                display: flex;
                min-height: 100vh;
            }
            .sidebar {
                width: 300px;
                background-color: #f0f2f6;
                padding: 1rem;
                border-right: 1px solid #e6e9ef;
                position: fixed;
                height: 100vh;
                overflow-y: auto;
            }
            .main-content {
                margin-left: 300px;
                padding: 2rem;
                width: calc(100% - 300px);
                background-color: #ffffff;
            }
            .main-header {
                font-size: 2.5rem;
                color: #4A90E2;
                margin-bottom: 1rem;
                font-weight: 600;
            }
            .sub-header {
                font-size: 1.5rem;
                color: #333;
                margin-bottom: 0.5rem;
                font-weight: 500;
            }
            .sidebar-title {
                font-size: 1.5rem;
                font-weight: 600;
                margin-bottom: 1rem;
                color: #333;
            }
            .sidebar-subheader {
                font-size: 1.1rem;
                font-weight: 500;
                margin: 1rem 0 0.5rem 0;
                color: #333;
            }
            .nav-button {
                width: 100%;
                margin-bottom: 0.5rem;
                text-align: left;
                background-color: #ffffff;
                border: 1px solid #e6e9ef;
                color: #333;
                padding: 0.5rem 1rem;
                border-radius: 0.25rem;
                font-size: 0.9rem;
            }
            .nav-button:hover {
                background-color: #f8f9fa;
                border-color: #4A90E2;
            }
            .nav-button.active {
                background-color: #4A90E2;
                color: white;
                border-color: #4A90E2;
            }
            .quick-action-btn {
                width: 100%;
                height: 60px;
                margin-bottom: 0.5rem;
                background-color: #ffffff;
                border: 1px solid #e6e9ef;
                color: #333;
                border-radius: 0.25rem;
                font-size: 0.9rem;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .quick-action-btn:hover {
                background-color: #f8f9fa;
                border-color: #4A90E2;
            }
            .status-success {
                background-color: #d4edda;
                color: #155724;
                padding: 0.75rem;
                border-radius: 0.25rem;
                margin-bottom: 0.5rem;
                border: 1px solid #c3e6cb;
            }
            .status-error {
                background-color: #f8d7da;
                color: #721c24;
                padding: 0.75rem;
                border-radius: 0.25rem;
                margin-bottom: 0.5rem;
                border: 1px solid #f5c6cb;
            }
            .status-info {
                background-color: #d1ecf1;
                color: #0c5460;
                padding: 0.75rem;
                border-radius: 0.25rem;
                margin-bottom: 0.5rem;
                border: 1px solid #bee5eb;
            }
            .status-warning {
                background-color: #fff3cd;
                color: #856404;
                padding: 0.75rem;
                border-radius: 0.25rem;
                margin-bottom: 0.5rem;
                border: 1px solid #ffeaa7;
            }
            .two-column-container {
                display: flex;
                gap: 2rem;
                margin-bottom: 2rem;
            }
            .column {
                flex: 1;
            }
            .quick-actions-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 0.5rem;
                margin-bottom: 1rem;
            }
            .divider {
                border-top: 1px solid #e6e9ef;
                margin: 2rem 0;
            }
            .recent-activity-item {
                border: 1px solid #e6e9ef;
                border-radius: 0.25rem;
                padding: 1rem;
                margin-bottom: 0.5rem;
                background-color: #f8f9fa;
            }
            .recent-activity-header {
                font-weight: 500;
                color: #333;
                margin-bottom: 0.5rem;
                cursor: pointer;
            }
            .recent-activity-content {
                font-size: 0.9rem;
                color: #666;
            }
             .sidebar-status {
                 margin-top: 1rem;
                 padding-top: 1rem;
                 border-top: 1px solid #e6e9ef;
             }
             .tab-navigation {
                 display: flex;
                 margin-bottom: 2rem;
                 border-bottom: 1px solid #e6e9ef;
             }
             .tab-button {
                 background-color: #f8f9fa;
                 border: 1px solid #e6e9ef;
                 border-bottom: none;
                 color: #333;
                 padding: 0.75rem 1.5rem;
                 margin-right: 0.25rem;
                 border-radius: 0.25rem 0.25rem 0 0;
                 font-size: 0.9rem;
                 cursor: pointer;
             }
             .tab-button:hover {
                 background-color: #e9ecef;
             }
             .tab-button.active {
                 background-color: #ffffff;
                 border-color: #e6e9ef;
                 border-bottom: 1px solid #ffffff;
                 margin-bottom: -1px;
                 position: relative;
                 z-index: 1;
             }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

def get_system_status():
    """Get system status from API"""
    try:
        response = requests.get(f"{API_URL}/status", timeout=5)
        return response.json()
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return {
            "status": "error", 
            "message": str(e),
            "components": {
                "vector_database": {"status": "unavailable", "available": False},
                "llm_service": {"status": "unavailable", "available": False}
            }
        }

def create_sidebar():
    """Create the sidebar navigation exactly matching Streamlit"""
    return html.Div([
        html.H2("VaultMIND", className="sidebar-title"),
        
        # Navigation section
        html.H3("Navigation", className="sidebar-subheader"),
        html.Button("🏠 Home", id="nav-home", className="nav-button active"),
        html.Button("📝 Ingest Documents", id="nav-ingest", className="nav-button"),
        html.Button("🔍 Search", id="nav-search", className="nav-button"),
        html.Button("📚 Documents", id="nav-documents", className="nav-button"),
        html.Button("📊 Analytics", id="nav-analytics", className="nav-button"),
        
        # System Status section
        html.Div([
            html.H3("System Status", className="sidebar-subheader"),
            html.Button("🔄 Refresh Status", id="refresh-status", className="nav-button"),
            html.Div(id="sidebar-status-display")
        ], className="sidebar-status")
    ], className="sidebar")

def create_home_content():
    """Create the home page content exactly matching Streamlit"""
    return html.Div([
        # Main header
        html.H1("VaultMIND GenAI Knowledge Assistant", className="main-header"),
        
        # Two-column layout
        html.Div([
            # Left column - Quick Actions
            html.Div([
                html.H2("Quick Actions", className="sub-header"),
                html.Div([
                    html.Button("📝 New Document", id="quick-new-doc", className="quick-action-btn"),
                    html.Button("🔍 Search", id="quick-search", className="quick-action-btn"),
                    html.Button("📚 View Documents", id="quick-view-docs", className="quick-action-btn"),
                    html.Button("📊 Analytics", id="quick-analytics", className="quick-action-btn")
                ], className="quick-actions-grid")
            ], className="column"),
            
            # Right column - System Status
            html.Div([
                html.H2("System Status", className="sub-header"),
                html.Div(id="system-status-display")
            ], className="column")
        ], className="two-column-container"),
        
        # Divider
        html.Hr(className="divider"),
        
        # Recent Activity
        html.H2("Recent Activity", className="sub-header"),
        html.Div(id="recent-activity-display")
    ])

def create_ingest_content():
    """Create the ingest page content exactly matching Streamlit"""
    return html.Div([
        # Main header
        html.H1("Ingest Documents", className="main-header"),
        
        # Tab navigation
        html.Div([
            html.Button("Upload Files", id="ingest-tab-upload", className="tab-button active"),
            html.Button("Paste Text", id="ingest-tab-paste", className="tab-button"),
            html.Button("Import from URL", id="ingest-tab-url", className="tab-button")
        ], className="tab-navigation"),
        
        # Tab content
        html.Div(id="ingest-tab-content"),
        
        # Navigation buttons
        html.Div([
            html.Button("← Back to Home", id="back-to-home-ingest", className="nav-button", style={"width": "200px"})
        ], style={"marginTop": "2rem"})
    ])

def create_upload_files_tab():
    """Create Upload Files tab content"""
    return html.Div([
        html.H3("Upload Files", className="sub-header"),
        
        # File upload area
        dcc.Upload(
            id='upload-data',
            children=html.Div([
                html.Div("Drag and Drop or Click to Select Files", 
                        style={"fontSize": "1.2rem", "marginBottom": "0.5rem"}),
                html.Div("Supported formats: PDF, TXT, DOCX, MD", 
                        style={"fontSize": "0.9rem", "color": "#666"})
            ]),
            style={
                'width': '100%',
                'height': '200px',
                'lineHeight': '200px',
                'borderWidth': '2px',
                'borderStyle': 'dashed',
                'borderRadius': '0.25rem',
                'borderColor': '#4A90E2',
                'textAlign': 'center',
                'backgroundColor': '#f8f9fa',
                'marginBottom': '1rem',
                'cursor': 'pointer'
            },
            multiple=True
        ),
        
        # Ingestion Settings Expander
        html.Details([
            html.Summary("Ingestion Settings", style={"fontSize": "1.1rem", "fontWeight": "500", "cursor": "pointer", "marginBottom": "1rem"}),
            html.Div([
                # Index Name
                html.Div([
                    html.Label("Index Name (optional)", style={"fontWeight": "500", "marginBottom": "0.5rem", "display": "block"}),
                    dcc.Input(
                        id="index-name-upload",
                        type="text",
                        placeholder="Leave blank to use file name",
                        style={"width": "100%", "padding": "0.5rem", "borderRadius": "0.25rem", "border": "1px solid #e6e9ef", "marginBottom": "1rem"}
                    )
                ]),
                
                # Chunk Size
                html.Div([
                    html.Label("Chunk Size", style={"fontWeight": "500", "marginBottom": "0.5rem", "display": "block"}),
                    dcc.Slider(
                        id="chunk-size-upload",
                        min=100,
                        max=2000,
                        step=50,
                        value=500,
                        marks={100: '100', 500: '500', 1000: '1000', 1500: '1500', 2000: '2000'},
                        tooltip={"placement": "bottom", "always_visible": True}
                    )
                ], style={"marginBottom": "1rem"}),
                
                # Chunk Overlap
                html.Div([
                    html.Label("Chunk Overlap", style={"fontWeight": "500", "marginBottom": "0.5rem", "display": "block"}),
                    dcc.Slider(
                        id="chunk-overlap-upload",
                        min=0,
                        max=500,
                        step=10,
                        value=50,
                        marks={0: '0', 100: '100', 200: '200', 300: '300', 400: '400', 500: '500'},
                        tooltip={"placement": "bottom", "always_visible": True}
                    )
                ], style={"marginBottom": "1rem"}),
                
                # Tags
                html.Div([
                    html.Label("Tags (comma separated)", style={"fontWeight": "500", "marginBottom": "0.5rem", "display": "block"}),
                    dcc.Input(
                        id="tags-upload",
                        type="text",
                        placeholder="tag1, tag2, tag3",
                        style={"width": "100%", "padding": "0.5rem", "borderRadius": "0.25rem", "border": "1px solid #e6e9ef"}
                    )
                ])
            ])
        ], style={"marginBottom": "1rem"}),
        
        # Process Files Button
        html.Button("Process Files", id="process-files-btn", className="quick-action-btn", disabled=True),
        
        # Upload Status
        html.Div(id="upload-status")
    ])

def create_paste_text_tab():
    """Create Paste Text tab content"""
    return html.Div([
        html.H3("Paste Text", className="sub-header"),
        
        # Document Title
        html.Div([
            html.Label("Document Title", style={"fontWeight": "500", "marginBottom": "0.5rem", "display": "block"}),
            dcc.Input(
                id="document-title",
                type="text",
                placeholder="Enter document title",
                style={"width": "100%", "padding": "0.5rem", "borderRadius": "0.25rem", "border": "1px solid #e6e9ef", "marginBottom": "1rem"}
            )
        ]),
        
        # Content
        html.Div([
            html.Label("Content", style={"fontWeight": "500", "marginBottom": "0.5rem", "display": "block"}),
            dcc.Textarea(
                id="document-content",
                placeholder="Paste your text content here...",
                style={"width": "100%", "height": "300px", "padding": "0.5rem", "borderRadius": "0.25rem", "border": "1px solid #e6e9ef", "marginBottom": "1rem", "resize": "vertical"}
            )
        ]),
        
        # Ingestion Settings Expander
        html.Details([
            html.Summary("Ingestion Settings", style={"fontSize": "1.1rem", "fontWeight": "500", "cursor": "pointer", "marginBottom": "1rem"}),
            html.Div([
                # Index Name
                html.Div([
                    html.Label("Index Name (optional)", style={"fontWeight": "500", "marginBottom": "0.5rem", "display": "block"}),
                    dcc.Input(
                        id="index-name-paste",
                        type="text",
                        placeholder="Leave blank to use document title",
                        style={"width": "100%", "padding": "0.5rem", "borderRadius": "0.25rem", "border": "1px solid #e6e9ef", "marginBottom": "1rem"}
                    )
                ]),
                
                # Chunk Size
                html.Div([
                    html.Label("Chunk Size", style={"fontWeight": "500", "marginBottom": "0.5rem", "display": "block"}),
                    dcc.Slider(
                        id="chunk-size-paste",
                        min=100,
                        max=2000,
                        step=50,
                        value=500,
                        marks={100: '100', 500: '500', 1000: '1000', 1500: '1500', 2000: '2000'},
                        tooltip={"placement": "bottom", "always_visible": True}
                    )
                ], style={"marginBottom": "1rem"}),
                
                # Chunk Overlap
                html.Div([
                    html.Label("Chunk Overlap", style={"fontWeight": "500", "marginBottom": "0.5rem", "display": "block"}),
                    dcc.Slider(
                        id="chunk-overlap-paste",
                        min=0,
                        max=500,
                        step=10,
                        value=50,
                        marks={0: '0', 100: '100', 200: '200', 300: '300', 400: '400', 500: '500'},
                        tooltip={"placement": "bottom", "always_visible": True}
                    )
                ], style={"marginBottom": "1rem"}),
                
                # Tags
                html.Div([
                    html.Label("Tags (comma separated)", style={"fontWeight": "500", "marginBottom": "0.5rem", "display": "block"}),
                    dcc.Input(
                        id="tags-paste",
                        type="text",
                        placeholder="tag1, tag2, tag3",
                        style={"width": "100%", "padding": "0.5rem", "borderRadius": "0.25rem", "border": "1px solid #e6e9ef"}
                    )
                ])
            ])
        ], style={"marginBottom": "1rem"}),
        
        # Process Text Button
        html.Button("Process Text", id="process-text-btn", className="quick-action-btn", disabled=True),
        
        # Process Status
        html.Div(id="paste-status")
    ])

def create_import_url_tab():
    """Create Import from URL tab content"""
    return html.Div([
        html.H3("Import from URL", className="sub-header"),
        
        # URL Input
        html.Div([
            html.Label("URL", style={"fontWeight": "500", "marginBottom": "0.5rem", "display": "block"}),
            dcc.Input(
                id="import-url",
                type="url",
                placeholder="https://example.com/document.pdf",
                style={"width": "100%", "padding": "0.5rem", "borderRadius": "0.25rem", "border": "1px solid #e6e9ef", "marginBottom": "1rem"}
            )
        ]),
        
        # Ingestion Settings Expander
        html.Details([
            html.Summary("Ingestion Settings", style={"fontSize": "1.1rem", "fontWeight": "500", "cursor": "pointer", "marginBottom": "1rem"}),
            html.Div([
                # Index Name
                html.Div([
                    html.Label("Index Name (optional)", style={"fontWeight": "500", "marginBottom": "0.5rem", "display": "block"}),
                    dcc.Input(
                        id="index-name-url",
                        type="text",
                        placeholder="Leave blank to use URL domain",
                        style={"width": "100%", "padding": "0.5rem", "borderRadius": "0.25rem", "border": "1px solid #e6e9ef", "marginBottom": "1rem"}
                    )
                ]),
                
                # Chunk Size
                html.Div([
                    html.Label("Chunk Size", style={"fontWeight": "500", "marginBottom": "0.5rem", "display": "block"}),
                    dcc.Slider(
                        id="chunk-size-url",
                        min=100,
                        max=2000,
                        step=50,
                        value=500,
                        marks={100: '100', 500: '500', 1000: '1000', 1500: '1500', 2000: '2000'},
                        tooltip={"placement": "bottom", "always_visible": True}
                    )
                ], style={"marginBottom": "1rem"}),
                
                # Chunk Overlap
                html.Div([
                    html.Label("Chunk Overlap", style={"fontWeight": "500", "marginBottom": "0.5rem", "display": "block"}),
                    dcc.Slider(
                        id="chunk-overlap-url",
                        min=0,
                        max=500,
                        step=10,
                        value=50,
                        marks={0: '0', 100: '100', 200: '200', 300: '300', 400: '400', 500: '500'},
                        tooltip={"placement": "bottom", "always_visible": True}
                    )
                ], style={"marginBottom": "1rem"}),
                
                # Tags
                html.Div([
                    html.Label("Tags (comma separated)", style={"fontWeight": "500", "marginBottom": "0.5rem", "display": "block"}),
                    dcc.Input(
                        id="tags-url",
                        type="text",
                        placeholder="tag1, tag2, tag3",
                        style={"width": "100%", "padding": "0.5rem", "borderRadius": "0.25rem", "border": "1px solid #e6e9ef"}
                    )
                ])
            ])
        ], style={"marginBottom": "1rem"}),
        
        # Process URL Button
        html.Button("Process URL", id="process-url-btn", className="quick-action-btn", disabled=True),
        
        # Process Status
        html.Div(id="url-status")
    ])

def create_search_content():
    """Create the search page content exactly matching Streamlit"""
    return html.Div([
        # Main header
        html.H1("Search Knowledge Base", className="main-header"),
        
        # Search input
        html.Div([
            html.Label("Enter your query", style={"fontWeight": "500", "marginBottom": "0.5rem", "display": "block"}),
            dcc.Input(
                id="search-query",
                type="text",
                placeholder="Enter your query here",
                style={"width": "100%", "padding": "0.5rem", "borderRadius": "0.25rem", "border": "1px solid #e6e9ef", "marginBottom": "1rem"}
            )
        ]),
        
        # Search Settings Expander
        html.Details([
            html.Summary("Search Settings", style={"fontSize": "1.1rem", "fontWeight": "500", "cursor": "pointer", "marginBottom": "1rem"}),
            html.Div([
                # Maximum Results
                html.Div([
                    html.Label("Maximum Results", style={"fontWeight": "500", "marginBottom": "0.5rem", "display": "block"}),
                    dcc.Slider(
                        id="search-max-results",
                        min=1,
                        max=20,
                        step=1,
                        value=5,
                        marks={1: '1', 5: '5', 10: '10', 15: '15', 20: '20'},
                        tooltip={"placement": "bottom", "always_visible": True}
                    )
                ], style={"marginBottom": "1rem"}),
                
                # Relevance Threshold
                html.Div([
                    html.Label("Relevance Threshold", style={"fontWeight": "500", "marginBottom": "0.5rem", "display": "block"}),
                    dcc.Slider(
                        id="search-relevance-threshold",
                        min=0.0,
                        max=1.0,
                        step=0.05,
                        value=0.6,
                        marks={0.0: '0.0', 0.2: '0.2', 0.4: '0.4', 0.6: '0.6', 0.8: '0.8', 1.0: '1.0'},
                        tooltip={"placement": "bottom", "always_visible": True}
                    )
                ], style={"marginBottom": "1rem"}),
                
                # LLM Provider
                html.Div([
                    html.Label("LLM Provider", style={"fontWeight": "500", "marginBottom": "0.5rem", "display": "block"}),
                    dcc.Dropdown(
                        id="search-llm-provider",
                        options=[
                            {"label": "OpenAI", "value": "openai"},
                            {"label": "Claude", "value": "claude"},
                            {"label": "DeepSeek", "value": "deepseek"}
                        ],
                        value="openai",
                        style={"marginBottom": "1rem"}
                    )
                ])
            ])
        ], style={"marginBottom": "1rem"}),
        
        # Search Button
        html.Button("Search", id="search-btn", className="quick-action-btn", disabled=True),
        
        # Recent Queries
        html.Div([
            html.Hr(className="divider"),
            html.H2("Recent Queries", className="sub-header"),
            html.Div(id="recent-queries-display")
        ], style={"marginTop": "2rem"}),
        
        # Navigation buttons
        html.Div([
            html.Button("← Back to Home", id="back-to-home-search", className="nav-button", style={"width": "200px"})
        ], style={"marginTop": "2rem"})
    ])

def create_placeholder_content(page_name):
    """Create placeholder content for other pages"""
    return html.Div([
        html.H1(f"{page_name} Page", className="main-header"),
        html.P(f"This is the {page_name} page. Content will be implemented to match Streamlit design."),
        html.Button("← Back to Home", id="back-to-home", className="nav-button", style={"width": "200px"})
    ])

def create_analytics_content():
    """Create the analytics page content exactly matching Streamlit"""
    return html.Div([
        # Main header
        html.H1("Analytics Dashboard", className="main-header"),
        
        # Placeholder message
        html.Div([
            html.Div("Analytics dashboard is under development", 
                    className="status-info",
                    style={"fontSize": "1rem", "textAlign": "center"})
        ], style={"marginBottom": "2rem"}),
        
        # Navigation buttons
        html.Div([
            html.Button("← Back to Home", id="back-to-home-analytics", className="nav-button", style={"width": "200px"})
        ])
    ])

def create_documents_content():
    """Create the documents page content exactly matching Streamlit"""
    return html.Div([
        # Main header
        html.H1("Document Library", className="main-header"),
        
        # Document count and status
        html.Div(id="documents-count-display"),
        
        # Filter options
        html.Div([
            html.Div([
                html.Label("Filter by Tag", style={"fontWeight": "500", "marginBottom": "0.5rem", "display": "block"}),
                dcc.Dropdown(
                    id="documents-tag-filter",
                    placeholder="All Tags",
                    style={"marginBottom": "1rem"}
                )
            ], className="column"),
            
            html.Div([
                html.Label("Filter by File Type", style={"fontWeight": "500", "marginBottom": "0.5rem", "display": "block"}),
                dcc.Dropdown(
                    id="documents-type-filter",
                    placeholder="All Types",
                    style={"marginBottom": "1rem"}
                )
            ], className="column")
        ], className="two-column-container"),
        
        # Filtered document count
        html.Div(id="documents-filtered-count"),
        
        # Documents list
        html.Div(id="documents-list"),
        
        # Navigation buttons
        html.Div([
            html.Button("← Back to Home", id="back-to-home-documents", className="nav-button", style={"width": "200px", "marginRight": "1rem"}),
            html.Button("Ingest New Documents", id="ingest-new-documents", className="nav-button", style={"width": "200px"})
        ], style={"display": "flex", "marginTop": "2rem"})
    ])

def create_search_document_content():
    """Create the search in document page content exactly matching Streamlit"""
    return html.Div([
        # Main header
        html.H1("Search in Document", className="main-header"),
        
        # Document info
        html.Div(id="search-document-info"),
        
        # Search input
        html.Div([
            html.Label("Enter your query", style={"fontWeight": "500", "marginBottom": "0.5rem", "display": "block"}),
            dcc.Input(
                id="search-document-query",
                type="text",
                placeholder="Enter your query for this document",
                style={"width": "100%", "padding": "0.5rem", "borderRadius": "0.25rem", "border": "1px solid #e6e9ef", "marginBottom": "1rem"}
            )
        ]),
        
        # Search Settings Expander
        html.Details([
            html.Summary("Search Settings", style={"fontSize": "1.1rem", "fontWeight": "500", "cursor": "pointer", "marginBottom": "1rem"}),
            html.Div([
                # Maximum Results
                html.Div([
                    html.Label("Maximum Results", style={"fontWeight": "500", "marginBottom": "0.5rem", "display": "block"}),
                    dcc.Slider(
                        id="search-document-max-results",
                        min=1,
                        max=20,
                        step=1,
                        value=5,
                        marks={1: '1', 5: '5', 10: '10', 15: '15', 20: '20'},
                        tooltip={"placement": "bottom", "always_visible": True}
                    )
                ], style={"marginBottom": "1rem"}),
                
                # Relevance Threshold
                html.Div([
                    html.Label("Relevance Threshold", style={"fontWeight": "500", "marginBottom": "0.5rem", "display": "block"}),
                    dcc.Slider(
                        id="search-document-relevance-threshold",
                        min=0.0,
                        max=1.0,
                        step=0.05,
                        value=0.6,
                        marks={0.0: '0.0', 0.2: '0.2', 0.4: '0.4', 0.6: '0.6', 0.8: '0.8', 1.0: '1.0'},
                        tooltip={"placement": "bottom", "always_visible": True}
                    )
                ], style={"marginBottom": "1rem"}),
                
                # LLM Provider
                html.Div([
                    html.Label("LLM Provider", style={"fontWeight": "500", "marginBottom": "0.5rem", "display": "block"}),
                    dcc.Dropdown(
                        id="search-document-llm-provider",
                        options=[
                            {"label": "OpenAI", "value": "openai"},
                            {"label": "Claude", "value": "claude"},
                            {"label": "DeepSeek", "value": "deepseek"}
                        ],
                        value="openai",
                        style={"marginBottom": "1rem"}
                    )
                ])
            ])
        ], style={"marginBottom": "1rem"}),
        
        # Search Button
        html.Button("Search in Document", id="search-document-btn", className="quick-action-btn", disabled=True),
        
        # Search Status
        html.Div(id="search-document-status"),
        
        # Navigation buttons
        html.Div([
            html.Button("← Back to Documents", id="back-to-documents", className="nav-button", style={"width": "200px"})
        ], style={"marginTop": "2rem"})
    ])

def create_search_results_content():
    """Create the search results page content exactly matching Streamlit"""
    return html.Div([
        # Main header
        html.H1("Search Results", className="main-header"),
        
        # Query display
        html.Div(id="search-results-query"),
        
        # Answer section
        html.Div([
            html.H2("Answer", className="sub-header"),
            html.Details([
                html.Summary("View Answer", style={"fontSize": "1.1rem", "fontWeight": "500", "cursor": "pointer", "marginBottom": "1rem"}),
                html.Div(id="search-results-answer")
            ], open=True)
        ], id="answer-section", style={"marginBottom": "2rem"}),
        
        # Source Documents section
        html.Div([
            html.H2("Source Documents", className="sub-header"),
            html.Div(id="search-results-info"),
            html.Div(id="search-results-documents")
        ], style={"marginBottom": "2rem"}),
        
        # Feedback section
        html.Div([
            html.Hr(className="divider"),
            html.H2("Feedback", className="sub-header"),
            html.Div([
                html.Button("👍 This was helpful", id="feedback-helpful", className="quick-action-btn", style={"width": "48%", "marginRight": "2%"}),
                html.Button("👎 This wasn't helpful", id="feedback-not-helpful", className="quick-action-btn", style={"width": "48%", "marginLeft": "2%"})
            ], style={"display": "flex", "marginBottom": "1rem"}),
            html.Div(id="feedback-status")
        ], style={"marginBottom": "2rem"}),
        
        # Navigation buttons
        html.Div([
            html.Button("← Back to Search", id="back-to-search", className="nav-button", style={"width": "200px", "marginRight": "1rem"}),
            html.Button("New Search", id="new-search", className="nav-button", style={"width": "200px"})
        ], style={"display": "flex"})
    ])

# App layout
app.layout = html.Div([
    dcc.Store(id="current-page", data="home"),
    html.Div([
        create_sidebar(),
        html.Div(id="main-content", className="main-content")
    ], className="main-container")
])

# Callbacks
@app.callback(
    Output("main-content", "children"),
    Input("current-page", "data")
)
def update_main_content(current_page):
    """Update main content based on current page"""
    if current_page == "home":
        return create_home_content()
    elif current_page == "ingest":
        return create_ingest_content()
    elif current_page == "search":
        return create_search_content()
    elif current_page == "documents":
        return create_documents_content()
    elif current_page == "analytics":
        return create_analytics_content()
    else:
        return create_home_content()

# Advanced file upload callback with progress tracking
@app.callback(
    [Output("upload-status", "children"),
     Output("process-files-btn", "disabled")],
    [Input("upload-data", "contents"),
     Input("upload-data", "filename"),
     Input("process-files-btn", "n_clicks")],
    [State("index-name-upload", "value"),
     State("chunk-size-upload", "value"),
     State("chunk-overlap-upload", "value"),
     State("tags-upload", "value")]
)
def handle_file_upload(contents, filenames, n_clicks, index_name, chunk_size, chunk_overlap, tags):
    """Handle advanced file upload with progress tracking"""
    if not contents:
        return html.Div(), True
    
    # Enable process button when files are uploaded
    if not n_clicks:
        file_count = len(contents) if isinstance(contents, list) else 1
        return html.Div([
            html.Div(f"📁 {file_count} file(s) ready for processing", 
                    className="info-box"),
            html.Ul([
                html.Li(name) for name in (filenames if isinstance(filenames, list) else [filenames])
            ])
        ]), False
    
    # Process files when button is clicked
    if n_clicks:
        try:
            # Convert single file to list for uniform processing
            if not isinstance(contents, list):
                contents = [contents]
                filenames = [filenames]
            
            results = []
            progress_components = []
            
            # Create progress tracking for each file
            for i, (content, filename) in enumerate(zip(contents, filenames)):
                # Decode file content
                content_type, content_string = content.split(',')
                decoded = base64.b64decode(content_string)
                
                # Check file size (50MB limit)
                file_size_mb = len(decoded) / (1024 * 1024)
                if file_size_mb > 50:
                    results.append({
                        "filename": filename,
                        "status": "error",
                        "message": f"File too large ({file_size_mb:.1f}MB). Maximum size is 50MB."
                    })
                    continue
                
                # Process file with API call
                try:
                    # Prepare tags
                    tag_list = [tag.strip() for tag in tags.split(",")] if tags else []
                    
                    # Simulate API call for file processing
                    payload = {
                        "filename": filename,
                        "content": content_string,
                        "index_name": index_name or filename.split('.')[0],
                        "chunk_size": chunk_size,
                        "chunk_overlap": chunk_overlap,
                        "tags": tag_list
                    }
                    
                    # Make API request
                    response = requests.post(f"{API_URL}/ingest/file", json=payload, timeout=30)
                    
                    if response.status_code == 200:
                        result = response.json()
                        results.append({
                            "filename": filename,
                            "status": "success",
                            "message": f"Successfully processed {filename}",
                            "chunks": result.get("chunks", 0),
                            "index": result.get("index_name", "")
                        })
                    else:
                        results.append({
                            "filename": filename,
                            "status": "error",
                            "message": f"API Error: {response.status_code}"
                        })
                        
                except requests.exceptions.RequestException as e:
                    results.append({
                        "filename": filename,
                        "status": "error",
                        "message": f"Network error: {str(e)}"
                    })
                except Exception as e:
                    results.append({
                        "filename": filename,
                        "status": "error",
                        "message": f"Processing error: {str(e)}"
                    })
            
            # Create detailed results display
            success_count = sum(1 for r in results if r["status"] == "success")
            total_count = len(results)
            
            # Overall status
            if success_count == total_count:
                status_class = "success-box"
                status_message = f"✅ Successfully processed all {success_count} files"
            elif success_count > 0:
                status_class = "warning-box"
                status_message = f"⚠️ Processed {success_count} out of {total_count} files successfully"
            else:
                status_class = "error-box"
                status_message = f"❌ Failed to process any files"
            
            # Detailed results
            result_components = [
                html.Div(status_message, className=status_class)
            ]
            
            # Individual file results
            for result in results:
                if result["status"] == "success":
                    result_components.append(
                        html.Details([
                            html.Summary(f"✅ {result['filename']}", 
                                       style={"color": "#155724", "fontWeight": "500"}),
                            html.Div([
                                html.P(f"Index: {result.get('index', 'N/A')}"),
                                html.P(f"Chunks created: {result.get('chunks', 'N/A')}"),
                                html.P(f"Status: {result['message']}")
                            ], style={"paddingLeft": "1rem"})
                        ], style={"marginBottom": "0.5rem"})
                    )
                else:
                    result_components.append(
                        html.Details([
                            html.Summary(f"❌ {result['filename']}", 
                                       style={"color": "#721c24", "fontWeight": "500"}),
                            html.Div([
                                html.P(f"Error: {result['message']}")
                            ], style={"paddingLeft": "1rem"})
                        ], style={"marginBottom": "0.5rem"})
                    )
            
            return html.Div(result_components), True
            
        except Exception as e:
            return html.Div([
                html.Div(f"❌ Unexpected error: {str(e)}", className="error-box")
            ]), True
    
    return html.Div(), True

# Advanced text processing callback
@app.callback(
    [Output("paste-status", "children"),
     Output("process-text-btn", "disabled")],
    [Input("document-content", "value"),
     Input("process-text-btn", "n_clicks")],
    [State("document-title", "value"),
     State("index-name-paste", "value"),
     State("chunk-size-paste", "value"),
     State("chunk-overlap-paste", "value"),
     State("tags-paste", "value")]
)
def handle_text_processing(content, n_clicks, title, index_name, chunk_size, chunk_overlap, tags):
    """Handle advanced text processing with real-time validation"""
    if not content:
        return html.Div(), True
    
    # Enable button when content is available
    if not n_clicks:
        word_count = len(content.split())
        char_count = len(content)
        return html.Div([
            html.Div(f"📝 Text ready: {word_count} words, {char_count} characters", 
                    className="info-box")
        ]), False
    
    # Process text when button is clicked
    if n_clicks:
        try:
            # Prepare payload
            tag_list = [tag.strip() for tag in tags.split(",")] if tags else []
            
            payload = {
                "title": title or "Untitled Document",
                "content": content,
                "index_name": index_name or (title.replace(" ", "_") if title else "untitled"),
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap,
                "tags": tag_list
            }
            
            # Make API request
            response = requests.post(f"{API_URL}/ingest/text", json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                return html.Div([
                    html.Div("✅ Successfully processed text", className="success-box"),
                    html.Details([
                        html.Summary("Processing Details"),
                        html.Div([
                            html.P(f"Index: {result.get('index_name', 'N/A')}"),
                            html.P(f"Chunks created: {result.get('chunks', 'N/A')}"),
                            html.P(f"Processing time: {result.get('processing_time', 'N/A')}s")
                        ])
                    ])
                ]), True
            else:
                return html.Div([
                    html.Div(f"❌ API Error: {response.status_code}", className="error-box")
                ]), True
                
        except requests.exceptions.RequestException as e:
            return html.Div([
                html.Div(f"❌ Network error: {str(e)}", className="error-box")
            ]), True
        except Exception as e:
            return html.Div([
                html.Div(f"❌ Processing error: {str(e)}", className="error-box")
            ]), True
    
    return html.Div(), True

# Advanced URL processing callback
@app.callback(
    [Output("url-status", "children"),
     Output("process-url-btn", "disabled")],
    [Input("import-url", "value"),
     Input("process-url-btn", "n_clicks")],
    [State("index-name-url", "value"),
     State("chunk-size-url", "value"),
     State("chunk-overlap-url", "value"),
     State("tags-url", "value")]
)
def handle_url_processing(url, n_clicks, index_name, chunk_size, chunk_overlap, tags):
    """Handle advanced URL processing with validation"""
    if not url:
        return html.Div(), True
    
    # Validate URL format
    import re
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    if not url_pattern.match(url):
        return html.Div([
            html.Div("❌ Invalid URL format", className="error-box")
        ]), True
    
    # Enable button for valid URL
    if not n_clicks:
        return html.Div([
            html.Div(f"🔗 URL ready for processing: {url}", className="info-box")
        ]), False
    
    # Process URL when button is clicked
    if n_clicks:
        try:
            # Prepare payload
            tag_list = [tag.strip() for tag in tags.split(",")] if tags else []
            
            payload = {
                "url": url,
                "index_name": index_name or url.split("//")[1].split("/")[0].replace(".", "_"),
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap,
                "tags": tag_list
            }
            
            # Make API request with longer timeout for URL processing
            response = requests.post(f"{API_URL}/ingest/url", json=payload, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                return html.Div([
                    html.Div(f"✅ Successfully processed URL: {url}", className="success-box"),
                    html.Details([
                        html.Summary("Processing Details"),
                        html.Div([
                            html.P(f"Index: {result.get('index_name', 'N/A')}"),
                            html.P(f"Chunks created: {result.get('chunks', 'N/A')}"),
                            html.P(f"Content type: {result.get('content_type', 'N/A')}"),
                            html.P(f"Processing time: {result.get('processing_time', 'N/A')}s")
                        ])
                    ])
                ]), True
            else:
                return html.Div([
                    html.Div(f"❌ Failed to process URL: {response.status_code}", className="error-box")
                ]), True
                
        except requests.exceptions.Timeout:
            return html.Div([
                html.Div("❌ Request timeout - URL processing took too long", className="error-box")
            ]), True
        except requests.exceptions.RequestException as e:
            return html.Div([
                html.Div(f"❌ Network error: {str(e)}", className="error-box")
            ]), True
        except Exception as e:
            return html.Div([
                html.Div(f"❌ Processing error: {str(e)}", className="error-box")
            ]), True
    
    return html.Div(), True

def create_search_content():
    """Create the search page content exactly matching Streamlit"""
    return html.Div([
        # Main header
        html.H1("Search Knowledge Base", className="main-header"),
        
        # Search input
        html.Div([
            html.Label("Enter your query", style={"fontWeight": "500", "marginBottom": "0.5rem", "display": "block"}),
            dcc.Input(
                id="search-query",
                type="text",
                placeholder="Enter your query here",
                style={"width": "100%", "padding": "0.5rem", "borderRadius": "0.25rem", "border": "1px solid #e6e9ef", "marginBottom": "1rem"}
            )
        ]),
        
        # Search Settings Expander
        html.Details([
            html.Summary("Search Settings", style={"fontSize": "1.1rem", "fontWeight": "500", "cursor": "pointer", "marginBottom": "1rem"}),
            html.Div([
                # Maximum Results
                html.Div([
                    html.Label("Maximum Results", style={"fontWeight": "500", "marginBottom": "0.5rem", "display": "block"}),
                    dcc.Slider(
                        id="search-max-results",
                        min=1,
                        max=20,
                        step=1,
                        value=5,
                        marks={1: '1', 5: '5', 10: '10', 15: '15', 20: '20'},
                        tooltip={"placement": "bottom", "always_visible": True}
                    )
                ], style={"marginBottom": "1rem"}),
                
                # Relevance Threshold
                html.Div([
                    html.Label("Relevance Threshold", style={"fontWeight": "500", "marginBottom": "0.5rem", "display": "block"}),
                    dcc.Slider(
                        id="search-relevance-threshold",
                        min=0.0,
                        max=1.0,
                        step=0.05,
                        value=0.6,
                        marks={0.0: '0.0', 0.2: '0.2', 0.4: '0.4', 0.6: '0.6', 0.8: '0.8', 1.0: '1.0'},
                        tooltip={"placement": "bottom", "always_visible": True}
                    )
                ], style={"marginBottom": "1rem"}),
                
                # LLM Provider
                html.Div([
                    html.Label("LLM Provider", style={"fontWeight": "500", "marginBottom": "0.5rem", "display": "block"}),
                    dcc.Dropdown(
                        id="search-llm-provider",
                        options=[
                            {"label": "OpenAI", "value": "openai"},
                            {"label": "Claude", "value": "claude"},
                            {"label": "DeepSeek", "value": "deepseek"}
                        ],
                        value="openai",
                        style={"marginBottom": "1rem"}
                    )
                ])
            ])
        ], style={"marginBottom": "1rem"}),
        
        # Search Button
        html.Button("Search", id="search-btn", className="quick-action-btn", disabled=True),
        
        # Recent Queries
        html.Div([
            html.Hr(className="divider"),
            html.H2("Recent Queries", className="sub-header"),
            html.Div(id="recent-queries-display")
        ], style={"marginTop": "2rem"}),
        
        # Navigation buttons
        html.Div([
            html.Button("← Back to Home", id="back-to-home-search", className="nav-button", style={"width": "200px"})
        ], style={"marginTop": "2rem"})
    ])

def create_placeholder_content(page_name):
    """Create placeholder content for other pages"""
    return html.Div([
        html.H1(f"{page_name} Page", className="main-header"),
        html.P(f"This is the {page_name} page. Content will be implemented to match Streamlit design."),
        html.Button("← Back to Home", id="back-to-home", className="nav-button", style={"width": "200px"})
    ])

def create_analytics_content():
    """Create the analytics page content exactly matching Streamlit"""
    return html.Div([
        # Main header
        html.H1("Analytics Dashboard", className="main-header"),
        
        # Placeholder message
        html.Div([
            html.Div("Analytics dashboard is under development", 
                    className="status-info",
                    style={"fontSize": "1rem", "textAlign": "center"})
        ], style={"marginBottom": "2rem"}),
        
        # Navigation buttons
        html.Div([
            html.Button("← Back to Home", id="back-to-home-analytics", className="nav-button", style={"width": "200px"})
        ])
    ])

def create_documents_content():
    """Create the documents page content exactly matching Streamlit"""
    return html.Div([
        # Main header
        html.H1("Document Library", className="main-header"),
        
        # Document count and status
        html.Div(id="documents-count-display"),
        
        # Filter options
        html.Div([
            html.Div([
                html.Label("Filter by Tag", style={"fontWeight": "500", "marginBottom": "0.5rem", "display": "block"}),
                dcc.Dropdown(
                    id="documents-tag-filter",
                    placeholder="All Tags",
                    style={"marginBottom": "1rem"}
                )
            ], className="column"),
            
            html.Div([
                html.Label("Filter by File Type", style={"fontWeight": "500", "marginBottom": "0.5rem", "display": "block"}),
                dcc.Dropdown(
                    id="documents-type-filter",
                    placeholder="All Types",
                    style={"marginBottom": "1rem"}
                )
            ], className="column")
        ], className="two-column-container"),
        
        # Filtered document count
        html.Div(id="documents-filtered-count"),
        
        # Documents list
        html.Div(id="documents-list"),
        
        # Navigation buttons
        html.Div([
            html.Button("← Back to Home", id="back-to-home-documents", className="nav-button", style={"width": "200px", "marginRight": "1rem"}),
            html.Button("Ingest New Documents", id="ingest-new-documents", className="nav-button", style={"width": "200px"})
        ], style={"display": "flex", "marginTop": "2rem"})
    ])

def create_search_document_content():
    """Create the search in document page content exactly matching Streamlit"""
    return html.Div([
        # Main header
        html.H1("Search in Document", className="main-header"),
        
        # Document info
        html.Div(id="search-document-info"),
        
        # Search input
        html.Div([
            html.Label("Enter your query", style={"fontWeight": "500", "marginBottom": "0.5rem", "display": "block"}),
            dcc.Input(
                id="search-document-query",
                type="text",
                placeholder="Enter your query for this document",
                style={"width": "100%", "padding": "0.5rem", "borderRadius": "0.25rem", "border": "1px solid #e6e9ef", "marginBottom": "1rem"}
            )
        ]),
        
        # Search Settings Expander
        html.Details([
            html.Summary("Search Settings", style={"fontSize": "1.1rem", "fontWeight": "500", "cursor": "pointer", "marginBottom": "1rem"}),
            html.Div([
                # Maximum Results
                html.Div([
                    html.Label("Maximum Results", style={"fontWeight": "500", "marginBottom": "0.5rem", "display": "block"}),
                    dcc.Slider(
                        id="search-document-max-results",
                        min=1,
                        max=20,
                        step=1,
                        value=5,
                        marks={1: '1', 5: '5', 10: '10', 15: '15', 20: '20'},
                        tooltip={"placement": "bottom", "always_visible": True}
                    )
                ], style={"marginBottom": "1rem"}),
                
                # Relevance Threshold
                html.Div([
                    html.Label("Relevance Threshold", style={"fontWeight": "500", "marginBottom": "0.5rem", "display": "block"}),
                    dcc.Slider(
                        id="search-document-relevance-threshold",
                        min=0.0,
                        max=1.0,
                        step=0.05,
                        value=0.6,
                        marks={0.0: '0.0', 0.2: '0.2', 0.4: '0.4', 0.6: '0.6', 0.8: '0.8', 1.0: '1.0'},
                        tooltip={"placement": "bottom", "always_visible": True}
                    )
                ], style={"marginBottom": "1rem"}),
                
                # LLM Provider
                html.Div([
                    html.Label("LLM Provider", style={"fontWeight": "500", "marginBottom": "0.5rem", "display": "block"}),
                    dcc.Dropdown(
                        id="search-document-llm-provider",
                        options=[
                            {"label": "OpenAI", "value": "openai"},
                            {"label": "Claude", "value": "claude"},
                            {"label": "DeepSeek", "value": "deepseek"}
                        ],
                        value="openai",
                        style={"marginBottom": "1rem"}
                    )
                ])
            ])
        ], style={"marginBottom": "1rem"}),
        
        # Search Button
        html.Button("Search in Document", id="search-document-btn", className="quick-action-btn", disabled=True),
        
        # Search Status
        html.Div(id="search-document-status"),
        
        # Navigation buttons
        html.Div([
            html.Button("← Back to Documents", id="back-to-documents", className="nav-button", style={"width": "200px"})
        ], style={"marginTop": "2rem"})
    ])

def create_search_results_content():
    """Create the search results page content exactly matching Streamlit"""
    return html.Div([
        # Main header
        html.H1("Search Results", className="main-header"),
        
        # Query display
        html.Div(id="search-results-query"),
        
        # Answer section
        html.Div([
            html.H2("Answer", className="sub-header"),
            html.Details([
                html.Summary("View Answer", style={"fontSize": "1.1rem", "fontWeight": "500", "cursor": "pointer", "marginBottom": "1rem"}),
                html.Div(id="search-results-answer")
            ], open=True)
        ], id="answer-section", style={"marginBottom": "2rem"}),
        
        # Source Documents section
        html.Div([
            html.H2("Source Documents", className="sub-header"),
            html.Div(id="search-results-info"),
            html.Div(id="search-results-documents")
        ], style={"marginBottom": "2rem"}),
        
        # Feedback section
        html.Div([
            html.Hr(className="divider"),
            html.H2("Feedback", className="sub-header"),
            html.Div([
                html.Button("👍 This was helpful", id="feedback-helpful", className="quick-action-btn", style={"width": "48%", "marginRight": "2%"}),
                html.Button("👎 This wasn't helpful", id="feedback-not-helpful", className="quick-action-btn", style={"width": "48%", "marginLeft": "2%"})
            ], style={"display": "flex", "marginBottom": "1rem"}),
            html.Div(id="feedback-status")
        ], style={"marginBottom": "2rem"}),
        
        # Navigation buttons
        html.Div([
            html.Button("← Back to Search", id="back-to-search", className="nav-button", style={"width": "200px", "marginRight": "1rem"}),
            html.Button("New Search", id="new-search", className="nav-button", style={"width": "200px"})
        ], style={"display": "flex"})
    ])

# App layout
app.layout = html.Div([