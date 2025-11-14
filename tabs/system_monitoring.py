"""
System Monitoring Tab for VaultMind
Displays system health, metrics, and automation status
"""

import streamlit as st
import logging
from datetime import datetime
from typing import Dict, Any
import time
import sys
import importlib

logger = logging.getLogger(__name__)

# Force reload of health checker module to avoid caching issues
if 'utils.monitoring.simple_health_checks' in sys.modules:
    importlib.reload(sys.modules['utils.monitoring.simple_health_checks'])


def render_system_monitoring_tab():
    """Render the system monitoring tab"""
    st.title("🔍 System Monitoring")
    st.markdown("Real-time system health and performance metrics")
    
    # Add clear cache button in case of issues
    col1, col2, col3 = st.columns([3, 1, 1])
    with col3:
        if st.button("🔄 Clear Cache", help="Clear Streamlit cache and reload"):
            st.cache_data.clear()
            st.cache_resource.clear()
            st.rerun()
    
    # Create tabs for different monitoring views
    monitoring_tabs = st.tabs([
        "📊 Overview",
        "💚 Health Checks",
        "📈 Metrics",
        "🤖 AI Agents",
        "💾 Backups"
    ])
    
    # Overview Tab
    with monitoring_tabs[0]:
        render_overview()
    
    # Health Checks Tab
    with monitoring_tabs[1]:
        render_health_checks()
    
    # Metrics Tab
    with monitoring_tabs[2]:
        render_metrics()
    
    # AI Agents Tab
    with monitoring_tabs[3]:
        render_agents_status()
    
    # Backups Tab
    with monitoring_tabs[4]:
        render_backups()


def render_overview():
    """Render system overview"""
    st.subheader("System Overview")
    
    # Get overall health
    try:
        # Direct import to avoid any __init__.py issues
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from utils.monitoring.simple_health_checks import simple_health_checker
        overall_health = simple_health_checker.get_overall_health()
        
        # Display overall status
        status = overall_health['status']
        if status == 'healthy':
            st.success("✅ System is healthy")
        elif status == 'degraded':
            st.warning("⚠️ System is degraded")
        elif status == 'unhealthy':
            st.error("❌ System is unhealthy")
        else:
            st.info("❓ System status unknown")
        
        # Display component summary
        col1, col2, col3, col4 = st.columns(4)
        
        components = overall_health.get('components', {})
        healthy_count = sum(1 for c in components.values() if c['status'] == 'healthy')
        degraded_count = sum(1 for c in components.values() if c['status'] == 'degraded')
        unhealthy_count = sum(1 for c in components.values() if c['status'] == 'unhealthy')
        
        col1.metric("Total Components", len(components))
        col2.metric("Healthy", healthy_count, delta_color="normal")
        col3.metric("Degraded", degraded_count, delta_color="inverse")
        col4.metric("Unhealthy", unhealthy_count, delta_color="inverse")
        
    except Exception as e:
        st.error(f"Failed to load system overview: {e}")
        logger.error(f"Overview error: {e}")


def render_health_checks():
    """Render detailed health checks"""
    st.subheader("Component Health Checks")
    
    try:
        # Direct import to avoid any __init__.py issues
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from utils.monitoring.simple_health_checks import simple_health_checker as health_checker
        
        # Add refresh button
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("🔄 Refresh", key="refresh_health"):
                st.rerun()
        
        # Run health checks
        with st.spinner("Running health checks..."):
            try:
                health_results = health_checker.run_all_checks()
            except Exception as check_error:
                st.error(f"Error running health checks: {str(check_error)}")
                st.info("This may be due to Prometheus metrics initialization. Try restarting Streamlit.")
                logger.error(f"Health check error: {check_error}")
                return
        
        # Display results
        for component, result in health_results.items():
            status = result['status']
            message = result.get('message', '')
            details = result.get('details', {})
            duration_ms = result.get('duration_ms', 0)
            
            # Create expander for each component
            with st.expander(f"{'✅' if status == 'healthy' else '⚠️' if status == 'degraded' else '❌'} {component.upper()}", expanded=(status != 'healthy')):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"**Status:** {status.upper()}")
                    st.write(f"**Message:** {message}")
                    st.write(f"**Check Duration:** {duration_ms}ms")
                
                with col2:
                    if status == 'healthy':
                        st.success("Healthy")
                    elif status == 'degraded':
                        st.warning("Degraded")
                    else:
                        st.error("Unhealthy")
                
                # Display details
                if details:
                    st.write("**Details:**")
                    st.json(details)
        
        # Last check timestamp
        st.caption(f"Last checked: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        st.error(f"Failed to run health checks: {e}")
        logger.error(f"Health check error: {e}")


def render_metrics():
    """Render system metrics"""
    st.subheader("System Metrics")
    
    st.info("📊 Metrics are available at: http://localhost:8000/metrics")
    
    # Display metrics information
    st.markdown("""
    ### Available Metrics
    
    **Document Ingestion:**
    - `vaultmind_ingestions_total` - Total ingestions by status and backend
    - `vaultmind_ingestion_duration_seconds` - Ingestion time
    
    **Queries:**
    - `vaultmind_queries_total` - Total queries by type and status
    - `vaultmind_query_duration_seconds` - Query processing time
    - `vaultmind_query_results_count` - Number of results per query
    
    **Vector Stores:**
    - `vaultmind_vector_store_health` - Health status (0=down, 1=healthy)
    - `vaultmind_vector_store_documents_total` - Document count
    - `vaultmind_vector_store_latency_ms` - Response latency
    
    **System:**
    - `vaultmind_active_users` - Active user count
    - `vaultmind_errors_total` - Error count by type and component
    
    **LLM:**
    - `vaultmind_llm_requests_total` - LLM API requests
    - `vaultmind_llm_tokens_total` - Token usage
    - `vaultmind_llm_latency_seconds` - LLM response time
    """)
    
    # Check if metrics server is running
    try:
        import requests
        response = requests.get('http://localhost:8000/metrics', timeout=2)
        if response.status_code == 200:
            st.success("✅ Metrics server is running")
            
            # Show sample metrics
            with st.expander("View Raw Metrics"):
                st.code(response.text[:2000] + "..." if len(response.text) > 2000 else response.text)
        else:
            st.warning("⚠️ Metrics server returned unexpected status")
    except Exception as e:
        st.error("❌ Metrics server is not running")
        st.info("Start with: `python run_automation_system.py`")


def render_agents_status():
    """Render AI agents status"""
    st.subheader("AI Agents Status")
    
    try:
        from app.agents.agent_orchestrator import orchestrator
        
        status = orchestrator.get_status()
        
        # Overall status
        if status['running']:
            st.success(f"✅ Agent system is running ({status['agent_count']} agents)")
        else:
            st.warning("⚠️ Agent system is not running")
            if st.button("▶️ Start Agent System"):
                st.info("Starting agents... (This requires the automation system to be running)")
        
        # Display individual agents
        agents = status.get('agents', {})
        
        if agents:
            for agent_name, agent_status in agents.items():
                with st.expander(f"🤖 {agent_name.replace('_', ' ').title()}", expanded=True):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Status", agent_status['status'].upper())
                    
                    with col2:
                        st.metric("Run Count", agent_status['run_count'])
                    
                    with col3:
                        st.metric("Errors", agent_status['error_count'])
                    
                    if agent_status.get('last_run'):
                        st.write(f"**Last Run:** {agent_status['last_run']}")
                    
                    # Control buttons
                    btn_col1, btn_col2, btn_col3 = st.columns(3)
                    with btn_col1:
                        if st.button("⏸️ Pause", key=f"pause_{agent_name}"):
                            orchestrator.pause_agent(agent_name)
                            st.rerun()
                    with btn_col2:
                        if st.button("▶️ Resume", key=f"resume_{agent_name}"):
                            orchestrator.resume_agent(agent_name)
                            st.rerun()
        else:
            st.info("No agents registered. Start the automation system to see agents.")
            
    except Exception as e:
        st.error(f"Failed to load agent status: {e}")
        st.info("Make sure the automation system is running: `python run_automation_system.py`")


def render_backups():
    """Render backup status and management"""
    st.subheader("Backup Management")
    
    try:
        from utils.backup.backup_manager import BackupManager
        
        manager = BackupManager()
        
        # Backup controls
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("💾 Backup Vector Stores"):
                with st.spinner("Creating backup..."):
                    result = manager.backup_vector_stores()
                    if result.get('success'):
                        st.success(f"✅ Backup created: {result.get('size_mb', 0):.2f} MB")
                    else:
                        st.error(f"❌ Backup failed: {result.get('error')}")
        
        with col2:
            if st.button("💾 Backup Databases"):
                with st.spinner("Creating backup..."):
                    result = manager.backup_databases()
                    if result.get('success'):
                        st.success(f"✅ Backup created: {result.get('size_mb', 0):.2f} MB")
                    else:
                        st.error(f"❌ Backup failed: {result.get('error')}")
        
        with col3:
            if st.button("💾 Backup Configuration"):
                with st.spinner("Creating backup..."):
                    result = manager.backup_configuration()
                    if result.get('success'):
                        st.success(f"✅ Backup created: {result.get('size_mb', 0):.2f} MB")
                    else:
                        st.error(f"❌ Backup failed: {result.get('error')}")
        
        with col4:
            if st.button("💾 Full Backup"):
                with st.spinner("Creating full backup..."):
                    results = manager.backup_all()
                    success_count = sum(1 for r in results.values() if r.get('success'))
                    st.success(f"✅ {success_count}/3 backups completed")
        
        st.markdown("---")
        
        # List existing backups
        st.subheader("Existing Backups")
        
        backups = manager.list_backups()
        
        if backups:
            for backup in backups:
                with st.expander(f"📦 {backup['backup_type']} - {backup['timestamp']}"):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**Type:** {backup['backup_type']}")
                        st.write(f"**Size:** {backup['size_mb']} MB")
                        st.write(f"**Path:** {backup['local_path']}")
                        if backup.get('s3_path'):
                            st.write(f"**S3:** {backup['s3_path']}")
                    
                    with col2:
                        if st.button("🔄 Restore", key=f"restore_{backup['timestamp']}"):
                            if st.warning("⚠️ This will overwrite existing data. Are you sure?"):
                                result = manager.restore_from_backup(backup['local_path'])
                                if result.get('success'):
                                    st.success("✅ Restore completed")
                                else:
                                    st.error(f"❌ Restore failed: {result.get('error')}")
        else:
            st.info("No backups found. Create your first backup above.")
        
        # Cleanup section
        st.markdown("---")
        st.subheader("Backup Cleanup")
        
        retention_days = st.number_input("Retention Days", min_value=1, max_value=365, value=30)
        
        if st.button("🗑️ Cleanup Old Backups"):
            with st.spinner("Cleaning up old backups..."):
                removed_count = manager.cleanup_old_backups(retention_days)
                st.success(f"✅ Removed {removed_count} old backups")
        
    except Exception as e:
        st.error(f"Failed to load backup management: {e}")
        logger.error(f"Backup management error: {e}")


# Main function to be called from dashboard
def show():
    """Main entry point for the tab"""
    render_system_monitoring_tab()


if __name__ == "__main__":
    show()
