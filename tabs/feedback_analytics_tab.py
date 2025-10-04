"""
Feedback Analytics Tab

Admin dashboard for analyzing user feedback and system performance
"""

import streamlit as st
import logging
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any, List

from utils.feedback_ui_components import render_feedback_analytics_dashboard
from utils.user_feedback_system import get_user_feedback_system

logger = logging.getLogger(__name__)

def render_feedback_analytics():
    """Render the feedback analytics dashboard"""
    try:
        # Initialize feedback UI
        from utils.feedback_ui_components import initialize_feedback_ui
        initialize_feedback_ui()
        
        st.title("📊 User Feedback Analytics")
        st.markdown("**Monitor query performance and user satisfaction**")
        
        # Check if user has admin permissions
        try:
            from app.auth.authentication import get_current_user
            current_user = get_current_user()
            
            if not current_user or current_user.get('role', '').lower() not in ['admin', 'power_user']:
                st.warning("⚠️ Admin access required to view feedback analytics")
                st.info("Contact your administrator for access to this feature.")
                return
                
        except Exception as e:
            logger.warning(f"Could not verify admin permissions: {e}")
            # Continue anyway for development/testing
        
        # Render the main analytics dashboard
        render_feedback_analytics_dashboard()
        
        # Additional admin-specific features
        st.markdown("---")
        
        # Quick actions section
        st.subheader("🔧 Quick Actions")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 Refresh Data", use_container_width=True):
                st.rerun()
        
        with col2:
            if st.button("📤 Export Report", use_container_width=True):
                _export_feedback_report()
        
        with col3:
            if st.button("🧹 Cleanup Old Data", use_container_width=True):
                _cleanup_old_feedback()
        
        # System health indicators
        st.subheader("🏥 System Health")
        
        feedback_system = get_user_feedback_system()
        
        try:
            # Get recent statistics
            recent_stats = feedback_system.get_system_feedback_report(days=7)
            overall_stats = recent_stats.get('overall_statistics', {})
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                total_feedback = overall_stats.get('total_feedback', 0)
                st.metric("Weekly Feedback", total_feedback)
                
                if total_feedback < 10:
                    st.caption("🔴 Low feedback volume")
                elif total_feedback < 50:
                    st.caption("🟡 Moderate feedback volume")
                else:
                    st.caption("🟢 Good feedback volume")
            
            with col2:
                helpfulness_rate = overall_stats.get('helpfulness_rate', 0)
                st.metric("Helpfulness Rate", f"{helpfulness_rate:.1%}")
                
                if helpfulness_rate < 0.6:
                    st.caption("🔴 Needs improvement")
                elif helpfulness_rate < 0.8:
                    st.caption("🟡 Good performance")
                else:
                    st.caption("🟢 Excellent performance")
            
            with col3:
                avg_confidence = overall_stats.get('average_confidence', 0)
                st.metric("Avg Confidence", f"{avg_confidence:.2f}")
                
                if avg_confidence < 0.5:
                    st.caption("🔴 Low confidence")
                elif avg_confidence < 0.7:
                    st.caption("🟡 Moderate confidence")
                else:
                    st.caption("🟢 High confidence")
            
            with col4:
                problematic_count = len(overall_stats.get('problematic_queries', []))
                st.metric("Problem Queries", problematic_count)
                
                if problematic_count > 10:
                    st.caption("🔴 Many issues")
                elif problematic_count > 5:
                    st.caption("🟡 Some issues")
                else:
                    st.caption("🟢 Few issues")
        
        except Exception as e:
            st.error(f"Failed to load system health data: {e}")
        
        # Improvement recommendations
        st.subheader("💡 Improvement Recommendations")
        
        try:
            recommendations = _generate_system_recommendations(feedback_system)
            
            if recommendations:
                for i, rec in enumerate(recommendations, 1):
                    priority = rec.get('priority', 'medium')
                    icon = "🔴" if priority == 'high' else "🟡" if priority == 'medium' else "🟢"
                    
                    with st.expander(f"{icon} {rec['title']}", expanded=priority == 'high'):
                        st.markdown(rec['description'])
                        
                        if rec.get('actions'):
                            st.markdown("**Suggested Actions:**")
                            for action in rec['actions']:
                                st.markdown(f"• {action}")
            else:
                st.success("🎉 System is performing well! No immediate recommendations.")
        
        except Exception as e:
            st.error(f"Failed to generate recommendations: {e}")
        
        # Footer with last update time
        st.markdown("---")
        st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        logger.error(f"Failed to render feedback analytics: {e}")
        st.error("Unable to load feedback analytics dashboard")

def _export_feedback_report():
    """Export feedback report"""
    try:
        feedback_system = get_user_feedback_system()
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"feedback_report_{timestamp}.json"
        
        # Export data
        success = feedback_system.export_feedback_data(filename, days=30)
        
        if success:
            st.success(f"✅ Report exported to {filename}")
            st.info("📁 Check your project directory for the exported file")
        else:
            st.error("❌ Failed to export report")
            
    except Exception as e:
        st.error(f"Export failed: {e}")
        logger.error(f"Failed to export feedback report: {e}")

def _cleanup_old_feedback():
    """Cleanup old feedback data"""
    try:
        # This would require implementing cleanup functionality in the feedback system
        st.info("🚧 Cleanup functionality will be implemented in a future update")
        
        # For now, show what would be cleaned up
        feedback_system = get_user_feedback_system()
        old_feedback = feedback_system.database.get_recent_feedback(days=90, limit=1000)
        
        if len(old_feedback) > 500:
            st.warning(f"⚠️ Found {len(old_feedback)} feedback entries from the last 90 days")
            st.info("Consider implementing data archival for entries older than 90 days")
        else:
            st.success("✅ Feedback database size is manageable")
            
    except Exception as e:
        st.error(f"Cleanup check failed: {e}")
        logger.error(f"Failed to check feedback cleanup: {e}")

def _generate_system_recommendations(feedback_system) -> List[Dict[str, Any]]:
    """Generate system improvement recommendations based on feedback data"""
    try:
        recommendations = []
        
        # Get recent statistics
        stats = feedback_system.get_system_feedback_report(days=30)
        overall_stats = stats.get('overall_statistics', {})
        
        # Check helpfulness rate
        helpfulness_rate = overall_stats.get('helpfulness_rate', 0)
        if helpfulness_rate < 0.6:
            recommendations.append({
                'title': 'Low Helpfulness Rate Detected',
                'description': f'Current helpfulness rate is {helpfulness_rate:.1%}, which is below the recommended 60% threshold.',
                'priority': 'high',
                'actions': [
                    'Review and improve query expansion algorithms',
                    'Enhance document chunking strategies',
                    'Implement better re-ranking models',
                    'Consider adding query clarification prompts'
                ]
            })
        
        # Check confidence scores
        avg_confidence = overall_stats.get('average_confidence', 0)
        if avg_confidence < 0.5:
            recommendations.append({
                'title': 'Low Confidence Scores',
                'description': f'Average confidence score is {avg_confidence:.2f}, indicating uncertain retrieval results.',
                'priority': 'high',
                'actions': [
                    'Improve semantic similarity models',
                    'Enhance metadata filtering',
                    'Review document indexing quality',
                    'Consider implementing confidence thresholds'
                ]
            })
        
        # Check problematic queries
        problematic_queries = overall_stats.get('problematic_queries', [])
        if len(problematic_queries) > 5:
            recommendations.append({
                'title': 'Multiple Problematic Queries',
                'description': f'Found {len(problematic_queries)} queries with consistently poor performance.',
                'priority': 'medium',
                'actions': [
                    'Analyze common patterns in problematic queries',
                    'Implement query-specific improvements',
                    'Add query suggestion features',
                    'Create FAQ for common difficult queries'
                ]
            })
        
        # Check retrieval method performance
        methods = overall_stats.get('retrieval_methods', [])
        if methods:
            # Find the method with the most usage but potentially poor performance
            method_analysis = {}
            for method in methods:
                method_name = method['method']
                count = method['count']
                
                # Get feedback for this method (simplified analysis)
                if 'enterprise' in method_name.lower() and count > 10:
                    method_analysis[method_name] = count
            
            if method_analysis:
                recommendations.append({
                    'title': 'Optimize Retrieval Methods',
                    'description': 'Some retrieval methods may need optimization based on usage patterns.',
                    'priority': 'low',
                    'actions': [
                        'Monitor performance of different retrieval methods',
                        'A/B test new retrieval algorithms',
                        'Optimize caching for frequently used methods'
                    ]
                })
        
        # Check feedback volume
        total_feedback = overall_stats.get('total_feedback', 0)
        if total_feedback < 20:
            recommendations.append({
                'title': 'Low Feedback Volume',
                'description': f'Only {total_feedback} feedback entries in the last 30 days. More feedback needed for better insights.',
                'priority': 'low',
                'actions': [
                    'Encourage users to provide feedback',
                    'Make feedback buttons more prominent',
                    'Consider feedback incentives',
                    'Add feedback reminders in UI'
                ]
            })
        
        return recommendations
        
    except Exception as e:
        logger.error(f"Failed to generate recommendations: {e}")
        return []

# Main function for the tab
def main():
    """Main function for the feedback analytics tab"""
    render_feedback_analytics()

if __name__ == "__main__":
    main()
