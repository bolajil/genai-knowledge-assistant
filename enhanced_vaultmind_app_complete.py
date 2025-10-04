"""
Enhanced VaultMIND GenAI Knowledge Assistant
A sophisticated Dash application for document management and AI-powered search
"""

import dash
from dash import dcc, html, Input, Output, State, ctx, callback_context
import dash_bootstrap_components as dbc
import requests
import logging
from datetime import datetime
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API Configuration
API_BASE_URL = "http://localhost:8000"

# Initialize Dash app with Bootstrap theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "VaultMIND - Enhanced Knowledge Assistant"

# Enhanced CSS styling
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            .main-container {
                display: flex;
                min-height: 100vh;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
            .sidebar {
                width: 280px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 2rem 1.5rem;
                box-shadow: 2px 0 10px rgba(0,0,0,0.1);
                position: fixed;
                height: 100vh;
                overflow-y: auto;
            }
            .sidebar-title {
                font-size: 1.8rem;
                font-weight: bold;
                margin-bottom: 2rem;
                text-align: center;
                color: #ffffff;
            }
            .sidebar-subheader {
                font-size: 1rem;
                font-weight: 600;
                margin: 1.5rem 0 0.5rem 0;
                color: #e8e8e8;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            .nav-button {
                display: block;
                width: 100%;
                background: rgba(255,255,255,0.1);
                color: white;
                border: none;
                padding: 0.75rem 1rem;
                margin: 0.25rem 0;
                border-radius: 0.5rem;
                font-size: 0.9rem;
                cursor: pointer;
                transition: all 0.3s ease;
                text-align: left;
            }
            .nav-button:hover {
                background: rgba(255,255,255,0.2);
                transform: translateX(5px);
            }
            .nav-button.active {
                background: rgba(255,255,255,0.3);
                font-weight: 600;
            }
            .main-content {
                margin-left: 280px;
                padding: 2rem;
                flex: 1;
                background-color: #f8f9fa;
                min-height: 100vh;
            }
            .main-header {
                color: #2c3e50;
                font-size: 2.5rem;
                font-weight: 700;
                margin-bottom: 2rem;
                text-align: center;
            }
            .sub-header {
                color: #34495e;
                font-size: 1.5rem;
                font-weight: 600;
                margin: 2rem 0 1rem 0;
            }
            .two-column-container {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 2rem;
                margin-bottom: 2rem;
            }
            .column {
                background-color: #ffffff;
                padding: 1.5rem;
                border-radius: 0.5rem;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                border: 1px solid #e9ecef;
            }
            .quick-action-btn {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 0.75rem 1.5rem;
                border-radius: 0.5rem;
                font-size: 1rem;
                cursor: pointer;
                margin: 0.5rem;
                transition: all 0.3s ease;
                min-width: 150px;
            }
            .quick-action-btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
            }
            .divider {
                border: none;
                height: 1px;
                background: linear-gradient(90deg, transparent, #ddd, transparent);
                margin: 2rem 0;
            }
            .status-indicator {
                display: inline-block;
                width: 12px;
                height: 12px;
                border-radius: 50%;
                margin-right: 0.5rem;
            }
            .status-online { background-color: #28a745; }
            .status-offline { background-color: #dc3545; }
            .status-warning { background-color: #ffc107; }
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

def create_sidebar():
    """Create the enhanced sidebar with navigation"""
    return html.Div([
        html.H2("VaultMIND", className="sidebar-title"),
        
        html.H3("Navigation", className="sidebar-subheader"),
        html.Button("🏠 Home", id="nav-home", className="nav-button active"),
        html.Button("📝 Ingest Documents", id="nav-ingest", className="nav-button"),
        html.Button("🔍 Search", id="nav-search", className="nav-button"),
        html.Button("📚 Documents", id="nav-documents", className="nav-button"),
        html.Button("📊 Analytics", id="nav-analytics", className="nav-button"),
        
        html.H3("System Status", className="sidebar-subheader"),
        html.Div(id="sidebar-status-display"),
        dcc.Interval(id="status-interval", interval=30000, n_intervals=0)
    ], className="sidebar")

def create_home_page():
    """Create the enhanced home page with rich content"""
    return html.Div([
        html.H1("🏠 Welcome to VaultMIND", className="main-header"),
        html.P("Your intelligent document assistant", 
               style={"textAlign": "center", "fontSize": "1.2rem", "color": "#666", "marginBottom": "3rem"}),
        
        # Key Features Section
        html.Div([
            html.H2("🚀 Key Features", className="sub-header"),
            html.Div([
                html.Div([
                    html.H4("📄 Smart Document Processing"),
                    html.P("Upload and process PDF, DOCX, TXT, and MD files with advanced AI extraction")
                ], className="column"),
                html.Div([
                    html.H4("🔍 Intelligent Search"),
                    html.P("Find information quickly with semantic search and natural language queries")
                ], className="column")
            ], className="two-column-container"),
            
            html.Div([
                html.Div([
                    html.H4("🤖 AI-Powered Insights"),
                    html.P("Get intelligent answers and summaries from your document collection")
                ], className="column"),
                html.Div([
                    html.H4("📊 Real-time Analytics"),
                    html.P("Monitor system performance and document processing statistics")
                ], className="column")
            ], className="two-column-container")
        ]),
        
        html.Hr(className="divider"),
        
        # System Status Section
        html.Div([
            html.H2("⚡ System Status", className="sub-header"),
            html.Div(id="home-status-display")
        ]),
        
        html.Hr(className="divider"),
        
        # Quick Actions
        html.Div([
            html.H2("🎯 Quick Actions", className="sub-header"),
            html.Div([
                html.Button("📝 Upload Documents", id="quick-upload", className="quick-action-btn"),
                html.Button("🔍 Search Documents", id="quick-search", className="quick-action-btn"),
                html.Button("📚 Browse Library", id="quick-browse", className="quick-action-btn"),
                html.Button("📊 View Analytics", id="quick-analytics", className="quick-action-btn")
            ], style={"textAlign": "center"})
        ])
    ])

def create_upload_page():
    """Create the document upload page"""
    return html.Div([
        html.H1("📝 Document Upload", className="main-header"),
        html.P("Upload your documents for AI-powered processing", 
               style={"textAlign": "center", "marginBottom": "2rem"}),
        
        dcc.Upload(
            id='upload-data',
            children=html.Div([
                html.Div("📁 Drag and Drop or Click to Select Files", 
                        style={"fontSize": "1.2rem", "marginBottom": "0.5rem"}),
                html.Div("Supported: PDF, TXT, DOCX, MD | Max: 50MB per file", 
                        style={"fontSize": "0.9rem", "color": "#666"})
            ]),
            style={
                'width': '100%',
                'height': '200px',
                'lineHeight': '200px',
                'borderWidth': '2px',
                'borderStyle': 'dashed',
                'borderRadius': '0.5rem',
                'borderColor': '#667eea',
                'textAlign': 'center',
                'backgroundColor': '#f8f9fa',
                'cursor': 'pointer'
            },
            multiple=True
        ),
        
        html.Div(id="upload-output", style={"marginTop": "2rem"})
    ])

# App Layout
app.layout = html.Div([
    create_sidebar(),
    html.Div([
        html.Div(id="main-content", children=create_home_page())
    ], className="main-content")
], className="main-container")

# Navigation callback
@app.callback(
    Output("main-content", "children"),
    [Input("nav-home", "n_clicks"),
     Input("nav-ingest", "n_clicks"),
     Input("nav-search", "n_clicks"),
     Input("nav-documents", "n_clicks"),
     Input("nav-analytics", "n_clicks")]
)
def update_main_content(home_clicks, ingest_clicks, search_clicks, docs_clicks, analytics_clicks):
    """Handle navigation between pages"""
    ctx_triggered = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else 'nav-home'
    
    if ctx_triggered == "nav-ingest":
        return create_upload_page()
    elif ctx_triggered == "nav-search":
        return html.Div([
            html.H1("🔍 Advanced Search", className="main-header"),
            html.P("Enhanced search functionality coming soon...", style={"textAlign": "center"})
        ])
    elif ctx_triggered == "nav-documents":
        return html.Div([
            html.H1("📚 Document Management", className="main-header"),
            html.P("Advanced document management coming soon...", style={"textAlign": "center"})
        ])
    elif ctx_triggered == "nav-analytics":
        return html.Div([
            html.H1("📊 Analytics Dashboard", className="main-header"),
            html.P("Analytics and insights coming soon...", style={"textAlign": "center"})
        ])
    else:
        return create_home_page()

# Status callback
@app.callback(
    [Output("sidebar-status-display", "children"),
     Output("home-status-display", "children")],
    [Input("status-interval", "n_intervals")]
)
def update_status(n_intervals):
    """Update system status displays"""
    try:
        # Mock status data for demonstration
        status_data = {
            'vector_database': {'status': 'online', 'response_time': '45ms'},
            'llm_service': {'status': 'online', 'response_time': '120ms'},
            'document_processor': {'status': 'online', 'response_time': '80ms'},
            'search_engine': {'status': 'online', 'response_time': '35ms'}
        }
        
        sidebar_status = html.Div([
            html.Div([
                html.Span(className="status-indicator status-online"),
                html.Span("All Systems Online")
            ], style={"marginBottom": "0.5rem"}),
            html.Small(f"Last updated: {datetime.now().strftime('%H:%M:%S')}", 
                      style={"color": "#e8e8e8"})
        ])
        
        detailed_status = html.Div([
            html.Div([
                html.H4("🗄️ Vector Database"),
                html.P([
                    html.Span(className="status-indicator status-online"),
                    f"Online - {status_data['vector_database']['response_time']}"
                ])
            ], style={"marginBottom": "1rem"}),
            
            html.Div([
                html.H4("🤖 LLM Service"),
                html.P([
                    html.Span(className="status-indicator status-online"),
                    f"Online - {status_data['llm_service']['response_time']}"
                ])
            ], style={"marginBottom": "1rem"}),
            
            html.Div([
                html.H4("📄 Document Processor"),
                html.P([
                    html.Span(className="status-indicator status-online"),
                    f"Online - {status_data['document_processor']['response_time']}"
                ])
            ], style={"marginBottom": "1rem"}),
            
            html.Div([
                html.H4("🔍 Search Engine"),
                html.P([
                    html.Span(className="status-indicator status-online"),
                    f"Online - {status_data['search_engine']['response_time']}"
                ])
            ])
        ])
        
        return sidebar_status, detailed_status
        
    except Exception as e:
        error_status = html.Div([
            html.Span(className="status-indicator status-offline"),
            html.Span("System Error")
        ])
        
        error_detail = html.Div([
            html.H4("❌ System Error", style={"color": "#dc3545"}),
            html.P(f"Unable to connect to services: {str(e)}")
        ])
        
        return error_status, error_detail

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8051)