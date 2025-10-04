"""
User Feedback UI Components

Streamlit components for collecting and displaying user feedback
"""

import streamlit as st
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

from utils.user_feedback_system import get_user_feedback_system

logger = logging.getLogger(__name__)

def render_feedback_buttons(
    query: str,
    response: str,
    source_docs: List[Dict[str, Any]] = None,
    confidence_score: float = 0.0,
    retrieval_method: str = "unknown",
    session_key: str = "feedback"
) -> Optional[str]:
    """
    Render thumbs up/down feedback buttons and collect feedback
    
    Returns:
        Feedback ID if feedback was submitted, None otherwise
    """
    try:
        # Create unique key for this query-response pair
        feedback_key = f"{session_key}_{hash(query + response)}"
        
        # Initialize session state for this feedback
        if f"{feedback_key}_submitted" not in st.session_state:
            st.session_state[f"{feedback_key}_submitted"] = False
        
        # Don't show buttons if feedback already submitted
        if st.session_state[f"{feedback_key}_submitted"]:
            st.success("✅ Thank you for your feedback!")
            return None
        
        st.markdown("---")
        st.markdown("**Was this response helpful?**")
        
        col1, col2, col3 = st.columns([1, 1, 4])
        
        with col1:
            if st.button("👍 Yes", key=f"{feedback_key}_yes"):
                feedback_id = _submit_feedback(
                    query, response, True, source_docs, 
                    confidence_score, retrieval_method
                )
                st.session_state[f"{feedback_key}_submitted"] = True
                st.success("✅ Thank you for your positive feedback!")
                st.rerun()
                return feedback_id
        
        with col2:
            if st.button("👎 No", key=f"{feedback_key}_no"):
                feedback_id = _submit_feedback(
                    query, response, False, source_docs, 
                    confidence_score, retrieval_method
                )
                st.session_state[f"{feedback_key}_submitted"] = True
                
                # Show additional feedback form for negative feedback
                st.session_state[f"{feedback_key}_show_details"] = True
                st.rerun()
                return feedback_id
        
        # Show detailed feedback form for negative feedback
        if st.session_state.get(f"{feedback_key}_show_details", False):
            _render_detailed_feedback_form(query, response, feedback_key)
        
        return None
        
    except Exception as e:
        logger.error(f"Failed to render feedback buttons: {e}")
        st.error("Unable to display feedback options")
        return None

def _submit_feedback(
    query: str,
    response: str,
    was_helpful: bool,
    source_docs: List[Dict[str, Any]],
    confidence_score: float,
    retrieval_method: str
) -> Optional[str]:
    """Submit feedback to the system"""
    try:
        feedback_system = get_user_feedback_system()
        
        # Ensure source_docs is properly formatted
        safe_source_docs = []
        if source_docs:
            for doc in source_docs:
                if isinstance(doc, dict):
                    safe_doc = {
                        'content': doc.get('content', ''),
                        'source': doc.get('source', 'Unknown')
                    }
                else:
                    safe_doc = {
                        'content': str(doc),
                        'source': 'Unknown'
                    }
                safe_source_docs.append(safe_doc)
        
        feedback_id = feedback_system.log_user_feedback(
            query=query,
            response_text=response,
            was_helpful=was_helpful,
            retrieved_docs=safe_source_docs,
            confidence_score=confidence_score,
            retrieval_method=retrieval_method,
            user_id=st.session_state.get('user_id', 'anonymous')
        )
        
        logger.info(f"Feedback submitted: {feedback_id}")
        return feedback_id
        
    except Exception as e:
        logger.error(f"Failed to submit feedback: {e}")
        return None

def _render_detailed_feedback_form(query: str, response: str, feedback_key: str):
    """Render detailed feedback form for negative feedback"""
    try:
        st.markdown("**Help us improve! What went wrong?**")
        
        # Predefined issue categories
        issues = st.multiselect(
            "Select issues (optional):",
            [
                "Response was not relevant to my query",
                "Information was incomplete or missing",
                "Response was too technical/complex",
                "Response was too basic/simple",
                "Sources were not credible or relevant",
                "Response contained incorrect information",
                "Query understanding was poor",
                "Other"
            ],
            key=f"{feedback_key}_issues"
        )
        
        # Additional comments
        additional_feedback = st.text_area(
            "Additional comments (optional):",
            placeholder="Please describe what you were looking for or how we can improve...",
            key=f"{feedback_key}_comments"
        )
        
        if st.button("Submit Detailed Feedback", key=f"{feedback_key}_submit_detailed"):
            # Update the feedback entry with additional details
            try:
                feedback_system = get_user_feedback_system()
                
                # Store additional feedback (this would require updating the original feedback entry)
                combined_feedback = f"Issues: {', '.join(issues)}. Comments: {additional_feedback}"
                
                # For now, log as a new entry with additional context
                feedback_system.log_user_feedback(
                    query=f"[DETAILED_FEEDBACK] {query}",
                    response_text=response,
                    was_helpful=False,
                    retrieved_docs=[],
                    confidence_score=0.0,
                    retrieval_method="detailed_feedback",
                    additional_feedback=combined_feedback
                )
                
                st.success("✅ Thank you for the detailed feedback!")
                st.session_state[f"{feedback_key}_show_details"] = False
                
            except Exception as e:
                logger.error(f"Failed to submit detailed feedback: {e}")
                st.error("Failed to submit detailed feedback")
        
    except Exception as e:
        logger.error(f"Failed to render detailed feedback form: {e}")

def render_feedback_analytics_dashboard():
    """Render feedback analytics dashboard for admin users"""
    try:
        st.header("📊 User Feedback Analytics")
        
        feedback_system = get_user_feedback_system()
        
        # Time period selector
        col1, col2 = st.columns([1, 3])
        with col1:
            days = st.selectbox("Time Period", [7, 14, 30, 60, 90], index=2)
        
        # Get feedback report
        report = feedback_system.get_system_feedback_report(days)
        
        if 'error' in report:
            st.error(f"Failed to load feedback data: {report['error']}")
            return
        
        stats = report.get('overall_statistics', {})
        
        # Key metrics
        st.subheader("📈 Key Metrics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Feedback",
                stats.get('total_feedback', 0)
            )
        
        with col2:
            helpfulness_rate = stats.get('helpfulness_rate', 0)
            st.metric(
                "Helpfulness Rate",
                f"{helpfulness_rate:.1%}",
                delta=f"{helpfulness_rate - 0.7:.1%}" if helpfulness_rate > 0 else None
            )
        
        with col3:
            avg_confidence = stats.get('average_confidence', 0)
            st.metric(
                "Avg Confidence",
                f"{avg_confidence:.2f}",
                delta=f"{avg_confidence - 0.6:.2f}" if avg_confidence > 0 else None
            )
        
        with col4:
            helpful_count = stats.get('helpful_feedback', 0)
            st.metric(
                "Helpful Responses",
                helpful_count
            )
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            # Helpfulness pie chart
            if stats.get('total_feedback', 0) > 0:
                helpful = stats.get('helpful_feedback', 0)
                not_helpful = stats.get('total_feedback', 0) - helpful
                
                fig_pie = go.Figure(data=[go.Pie(
                    labels=['Helpful', 'Not Helpful'],
                    values=[helpful, not_helpful],
                    hole=0.3,
                    marker_colors=['#00D4AA', '#FF6B6B']
                )])
                fig_pie.update_layout(title="Feedback Distribution")
                st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # Retrieval methods bar chart
            methods = stats.get('retrieval_methods', [])
            if methods:
                method_names = [m['method'] for m in methods]
                method_counts = [m['count'] for m in methods]
                
                fig_bar = go.Figure(data=[go.Bar(
                    x=method_names,
                    y=method_counts,
                    marker_color='#4ECDC4'
                )])
                fig_bar.update_layout(
                    title="Retrieval Methods Usage",
                    xaxis_title="Method",
                    yaxis_title="Count"
                )
                st.plotly_chart(fig_bar, use_container_width=True)
        
        # Daily trends
        daily_rates = report.get('daily_helpfulness_rates', {})
        if daily_rates:
            st.subheader("📅 Daily Helpfulness Trends")
            
            dates = list(daily_rates.keys())
            rates = list(daily_rates.values())
            
            fig_line = go.Figure(data=[go.Scatter(
                x=dates,
                y=rates,
                mode='lines+markers',
                line=dict(color='#4ECDC4', width=3),
                marker=dict(size=8)
            )])
            fig_line.update_layout(
                title="Daily Helpfulness Rate",
                xaxis_title="Date",
                yaxis_title="Helpfulness Rate",
                yaxis=dict(range=[0, 1])
            )
            st.plotly_chart(fig_line, use_container_width=True)
        
        # Problematic queries
        problematic = stats.get('problematic_queries', [])
        if problematic:
            st.subheader("⚠️ Queries Needing Improvement")
            
            df_problematic = pd.DataFrame(problematic)
            df_problematic['avg_confidence'] = df_problematic['avg_confidence'].round(3)
            
            st.dataframe(
                df_problematic,
                column_config={
                    'query': 'Query',
                    'count': 'Negative Feedback Count',
                    'avg_confidence': 'Average Confidence'
                },
                use_container_width=True
            )
        
        # Export functionality
        st.subheader("📤 Export Data")
        if st.button("Export Feedback Data"):
            try:
                export_file = f"feedback_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                success = feedback_system.export_feedback_data(export_file, days)
                
                if success:
                    st.success(f"✅ Data exported to {export_file}")
                else:
                    st.error("❌ Failed to export data")
                    
            except Exception as e:
                st.error(f"Export failed: {e}")
        
    except Exception as e:
        logger.error(f"Failed to render feedback analytics: {e}")
        st.error("Unable to load feedback analytics")

def render_query_insights(query: str):
    """Render insights for a specific query"""
    try:
        if not query.strip():
            return
        
        feedback_system = get_user_feedback_system()
        insights = feedback_system.get_query_performance_insights(query)
        
        if 'error' in insights:
            st.warning(f"Unable to load insights: {insights['error']}")
            return
        
        if 'message' in insights:
            st.info(insights['message'])
            return
        
        # Display insights in an expander
        with st.expander("🔍 Query Performance Insights", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric(
                    "Total Feedback",
                    insights.get('total_feedback', 0)
                )
                st.metric(
                    "Helpfulness Rate",
                    f"{insights.get('helpfulness_rate', 0):.1%}"
                )
            
            with col2:
                st.metric(
                    "Average Confidence",
                    f"{insights.get('average_confidence', 0):.2f}"
                )
            
            # Recommendations
            recommendation = insights.get('recommendation', '')
            if recommendation:
                if 'well' in recommendation.lower():
                    st.success(f"✅ {recommendation}")
                elif 'low' in recommendation.lower():
                    st.warning(f"⚠️ {recommendation}")
                else:
                    st.info(f"ℹ️ {recommendation}")
            
            # Improvement suggestions
            suggestions = insights.get('top_improvement_suggestions', [])
            if suggestions:
                st.markdown("**Top Improvement Suggestions:**")
                for i, suggestion in enumerate(suggestions, 1):
                    st.markdown(f"{i}. {suggestion}")
        
    except Exception as e:
        logger.error(f"Failed to render query insights: {e}")

def initialize_feedback_ui():
    """Initialize feedback UI components in session state"""
    if 'feedback_ui_initialized' not in st.session_state:
        st.session_state.feedback_ui_initialized = True
        
        # Initialize any required session state variables
        if 'user_id' not in st.session_state:
            st.session_state.user_id = 'anonymous'
