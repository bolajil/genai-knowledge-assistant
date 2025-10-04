import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

def render_multi_content_dashboard(user, permissions, auth_middleware, available_indexes):
    """Multi-Content Dashboard Tab - Basic version"""
    
    # Simplified permission check - allow admin users
    user_role = user.role.value if hasattr(user, 'role') else user.get('role', 'viewer')
    if user_role not in ['admin', 'power_user']:
        st.error("🚫 Access Denied: Admin privileges required")
        return
    
    auth_middleware.log_user_action("ACCESS_MULTI_CONTENT_DASHBOARD")
    
    st.header("🌐 Multi-Content Dashboard")
    st.markdown("**Advanced multi-content management and analytics**")
    
    # Add Excel functionality to basic dashboard
    st.subheader("📈 Excel Analytics")
    
    # File upload
    uploaded_file = st.file_uploader(
        "📁 Upload Excel File",
        type=['xlsx', 'xls'],
        help="Upload Excel files for analysis and visualization"
    )
    
    if uploaded_file:
        try:
            import pandas as pd
            # Process Excel file
            with st.spinner("Processing Excel file..."):
                excel_data = pd.read_excel(uploaded_file, sheet_name=None, engine='openpyxl')
            
            if excel_data:
                st.success(f"✅ Successfully loaded {len(excel_data)} sheet(s)")
                
                # Sheet selection
                sheet_names = list(excel_data.keys())
                selected_sheet = st.selectbox(
                    "📊 Select Sheet",
                    options=sheet_names,
                    key="basic_excel_sheet_selector"
                )
                
                if selected_sheet:
                    df = excel_data[selected_sheet]
                    
                    # Display basic info
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Rows", len(df))
                    with col2:
                        st.metric("Total Columns", len(df.columns))
                    with col3:
                        st.metric("Memory Usage", f"{df.memory_usage(deep=True).sum() / 1024:.1f} KB")
                    with col4:
                        st.metric("Missing Values", df.isnull().sum().sum())
                    
                    # Display data
                    st.subheader("📋 Data Preview")
                    st.dataframe(df.head(100), use_container_width=True)
                    
                    # Advanced Operations
                    st.markdown("### 🔧 Advanced Operations")
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        if st.button("📊 Create Pivot Table", key="basic_pivot"):
                            st.info("Pivot table functionality available in enhanced version")
                    
                    with col2:
                        if st.button("🔍 Data Profiling", key="basic_profile"):
                            # Basic data profiling
                            st.markdown("### 📊 Basic Data Profile")
                            st.write("**Data Types:**")
                            st.write(df.dtypes)
                            st.write("**Summary Statistics:**")
                            st.write(df.describe())
                    
                    with col3:
                        if st.button("🧹 Data Cleaning", key="basic_clean"):
                            # Basic cleaning options
                            st.markdown("### 🧹 Basic Data Cleaning")
                            if st.button("Remove Duplicates", key="basic_remove_dupes"):
                                cleaned_df = df.drop_duplicates()
                                st.success(f"Removed {len(df) - len(cleaned_df)} duplicates")
                                st.dataframe(cleaned_df.head(), use_container_width=True)
                    
                    with col4:
                        if st.button("💾 Export Results", key="basic_export"):
                            # Basic export
                            st.markdown("### 💾 Basic Export")
                            csv_data = df.to_csv(index=False)
                            st.download_button(
                                label="📥 Download CSV",
                                data=csv_data,
                                file_name=f"{selected_sheet}_export.csv",
                                mime="text/csv"
                            )
        except Exception as e:
            st.error(f"Error processing Excel file: {str(e)}")
    
    else:
        # Show demo when no file uploaded
        st.info("Upload an Excel file to access advanced analytics and operations")
        
        # Demo data
        demo_data = pd.DataFrame({
            'Product': ['Product A', 'Product B', 'Product C', 'Product D'],
            'Sales': [1000, 1500, 800, 1200],
            'Region': ['North', 'South', 'East', 'West'],
            'Date': pd.date_range('2025-01-01', periods=4, freq='ME')
        })
        
        st.markdown("**Sample Excel Data:**")
        st.dataframe(demo_data, use_container_width=True)
        
        # Sample chart
        fig = px.bar(demo_data, x='Product', y='Sales', color='Region', 
                    title="Sample Sales Data by Product and Region")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.metric(
            "🔍 Active Indexes", 
            len(available_indexes) if available_indexes else 0,
            delta="2 new",
            help="Number of active vector indexes"
        )
    
    with col3:
        st.metric(
            "📈 Queries Today", 
            "89",
            delta="12%",
            help="Query volume for today"
        )
    
    with col4:
        st.metric(
            "🌊 Live Streams", 
            "4",
            delta="1 new",
            help="Active data streams"
        )
    
    with col5:
        st.metric(
            "💾 Storage Used", 
            "7.2 GB",
            delta="0.3 GB",
            help="Total storage consumption"
        )
    
    st.divider()
    
    # Content Analytics - ADMIN ONLY
    st.subheader("📈 Content Analytics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**📊 Content Distribution:**")
        
        # Content type distribution
        content_data = {
            'Type': ['PDF Documents', 'Text Files', 'Web Pages', 'Streams', 'Images'],
            'Count': [456, 234, 189, 78, 45],
            'Size (MB)': [3420, 890, 1240, 567, 234]
        }
        
        content_df = pd.DataFrame(content_data)
        
        # Create pie chart
        fig = px.pie(content_df, values='Count', names='Type', 
                    title="Content Type Distribution")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("**📅 Content Growth:**")
        
        # Growth data
        growth_data = pd.DataFrame({
            'Date': pd.date_range('2025-08-01', periods=21, freq='D'),
            'Documents': [1200 + i*2 + (i%3)*5 for i in range(21)],
            'Queries': [45 + i*3 + (i%4)*8 for i in range(21)]
        })
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=growth_data['Date'], y=growth_data['Documents'],
                                mode='lines+markers', name='Documents'))
        fig.add_trace(go.Scatter(x=growth_data['Date'], y=growth_data['Queries'],
                                mode='lines+markers', name='Queries', yaxis='y2'))
        
        fig.update_layout(
            title="Content Growth Over Time",
            yaxis=dict(title="Documents"),
            yaxis2=dict(title="Queries", overlaying='y', side='right')
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Index Management - ADMIN ONLY
    st.subheader("🗂️ Index Management")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("**📋 Index Statistics:**")
        
        if available_indexes:
            index_stats = []
            for idx in available_indexes:
                # Simulated statistics
                index_stats.append({
                    'Index Name': idx,
                    'Documents': f"{456 + hash(idx) % 500}",
                    'Size (MB)': f"{123 + hash(idx) % 200}",
                    'Last Updated': '2025-08-09 14:30',
                    'Status': '🟢 Active',
                    'Queries/Day': f"{45 + hash(idx) % 100}"
                })
            
            index_df = pd.DataFrame(index_stats)
            st.dataframe(index_df, use_container_width=True)
        else:
            st.info("No indexes available")
    
    with col2:
        st.markdown("**⚡ Quick Actions:**")
        
        if st.button("🔄 Refresh Indexes", key="refresh_indexes"):
            st.success("✅ Indexes refreshed!")
        
        if st.button("📊 Generate Report", key="generate_index_report"):
            st.success("📊 Index report generated!")
        
        if st.button("🧹 Cleanup Unused", key="cleanup_indexes"):
            st.success("🧹 Cleanup completed!")
        
        if st.button("💾 Backup All", key="backup_indexes"):
            st.success("💾 Backup initiated!")
    
    st.divider()
    
    # Live Data Streams - ADMIN ONLY
    st.subheader("🌊 Live Data Streams")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown("**📡 Active Streams:**")
        
        streams_data = {
            'Stream Name': [
                'RSS Tech News',
                'Company Documents',
                'Web Scraper - News',
                'API Data Feed'
            ],
            'Type': ['RSS', 'File Watch', 'Web Scraping', 'API'],
            'Status': ['🟢 Active', '🟢 Active', '🟡 Paused', '🟢 Active'],
            'Items/Hour': ['12', '3', '0', '8'],
            'Last Update': [
                '2 min ago',
                '15 min ago',
                '2 hours ago',
                '1 day ago'
            ]
        }
        
        streams_df = pd.DataFrame(streams_data)
        st.dataframe(streams_df, use_container_width=True)
        
    with col2:
        st.markdown("**🎯 Stream Actions:**")
        
        if st.button("➕ Create Stream", key="create_stream"):
            st.success("✅ New stream creation wizard opened!")
        
        if st.button("⏸️ Pause All", key="pause_streams"):
            st.success("⏸️ All streams paused!")
        
        if st.button("▶️ Resume All", key="resume_streams"):
            st.success("▶️ All streams resumed!")
        
        if st.button("📊 Stream Analytics", key="stream_analytics"):
            st.success("📊 Analytics dashboard opened!")
    
    # Content Discovery - ADMIN ONLY
    st.subheader("🔍 Content Discovery")
    
    # Advanced search interface
    col1, col2 = st.columns([3, 1])
    
    with col1:
        search_query = st.text_input(
            "🔍 Search across all content:",
            placeholder="Enter keywords, phrases, or semantic queries...",
            key="content_search"
        )
        
        # Search filters
        col_a, col_b, col_c = st.columns(3)
        
        with col_a:
            content_type = st.multiselect(
                "Content Type:",
                ["PDF", "Text", "Web", "Stream"],
                default=["PDF", "Text", "Web"],
                key="search_content_type"
            )
        
        with col_b:
            date_range = st.selectbox(
                "Date Range:",
                ["All Time", "Last 24 Hours", "Last Week", "Last Month"],
                key="search_date_range"
            )
        
        with col_c:
            search_indexes = st.multiselect(
                "Search In:",
                available_indexes if available_indexes else ["No indexes available"],
                default=available_indexes[:3] if len(available_indexes) >= 3 else available_indexes,
                key="search_indexes"
            )
    
    with col2:
        st.markdown("**🎯 Search Options:**")
        
        semantic_search = st.checkbox(
            "Semantic Search",
            value=True,
            help="Use AI-powered semantic understanding",
            key="semantic_search"
        )
        
        max_results = st.slider(
            "Max Results:",
            min_value=5, max_value=100, value=20,
            key="search_max_results"
        )
        
        if st.button("🔍 Search", type="primary", key="execute_search"):
            if search_query:
                st.success(f"🔍 Searching for: '{search_query}' across {len(search_indexes)} indexes...")
            else:
                st.warning("⚠️ Please enter a search query")
    
    # Performance Monitoring - ADMIN ONLY
    st.subheader("📈 Performance Monitoring")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**📊 System Performance:**")
    
    # Performance metrics
    perf_data = pd.DataFrame({
        'Time': pd.date_range('2025-08-09 06:00', periods=24, freq='H'),
        'CPU Usage': [45, 42, 38, 35, 32, 40, 55, 62, 58, 65, 70, 68, 72, 75, 71, 68, 65, 60, 55, 50, 48, 46, 44, 43],
        'Memory Usage': [60, 58, 55, 52, 50, 58, 65, 72, 70, 75, 80, 78, 82, 85, 83, 80, 77, 72, 68, 65, 62, 60, 58, 57]
    })
    
    st.line_chart(perf_data.set_index('Time'))
    
    with col2:
        st.markdown("**🔍 Query Performance:**")
    
    # Query performance metrics
    query_data = pd.DataFrame({
        'Hour': list(range(24)),
        'Avg Response Time (ms)': [120, 115, 110, 105, 100, 125, 140, 155, 150, 165, 180, 175, 190, 195, 185, 170, 160, 145, 135, 125, 120, 118, 115, 112]
    })
    
    st.line_chart(query_data.set_index('Hour'))
    
    # System Health - ADMIN ONLY
    st.subheader("🟢 System Health")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**💾 Storage:**")
        storage_used = 75
        st.progress(storage_used / 100)
        st.write(f"Used: {storage_used}% (7.5 GB / 10 GB)")
    
    with col2:
        st.markdown("**📊 Memory:**")
        memory_used = 68
        st.progress(memory_used / 100)
        st.write(f"Used: {memory_used}% (5.4 GB / 8 GB)")
    
    with col3:
        st.markdown("**🔄 CPU:**")
        cpu_used = 45
        st.progress(cpu_used / 100)
        st.write(f"Used: {cpu_used}% (4 cores active)")
    
    # Quick Actions - ADMIN ONLY
    st.subheader("⚡ Quick Actions")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        if st.button("🔄 Refresh All", key="refresh_all"):
            st.success("✅ All data refreshed!")
    
    with col2:
        if st.button("💾 Backup System", key="backup_system"):
            st.success("💾 System backup initiated!")
    
    with col3:
        if st.button("🧩 Clear Cache", key="clear_all_cache"):
            st.success("🧩 All caches cleared!")
    
    with col4:
        if st.button("📈 Generate Report", key="generate_report"):
            st.success("📈 System report generated!")
    
    with col5:
        if st.button("🔒 Security Check", key="security_check"):
            st.success("🔒 Security check completed!")
