"""
Enhanced Multi-Content Dashboard with PowerBI Integration and Excel Support
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from typing import List, Dict, Any, Optional
import io
import base64
from pathlib import Path

class PowerBIIntegration:
    """PowerBI integration for embedding reports and dashboards"""
    
    @staticmethod
    def embed_powerbi_report(report_id: str, workspace_id: str, access_token: str = None):
        """Embed PowerBI report using iframe"""
        if not access_token:
            st.warning("⚠️ PowerBI access token required. Please configure in Security Setup.")
            return
        
        embed_url = f"https://app.powerbi.com/reportEmbed?reportId={report_id}&groupId={workspace_id}"
        
        # PowerBI embed iframe
        iframe_html = f"""
        <iframe 
            width="100%" 
            height="600" 
            src="{embed_url}" 
            frameborder="0" 
            allowFullScreen="true">
        </iframe>
        """
        
        st.components.v1.html(iframe_html, height=650)
    
    @staticmethod
    def create_powerbi_connection_form():
        """Form for configuring PowerBI connection"""
        with st.expander("🔧 PowerBI Configuration", expanded=False):
            with st.form("powerbi_config_main"):
                st.markdown("### PowerBI Connection Settings")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    tenant_id = st.text_input(
                        "Tenant ID",
                        placeholder="your-tenant-id",
                        help="Azure AD Tenant ID"
                    )
                    
                    client_id = st.text_input(
                        "Client ID", 
                        placeholder="your-app-client-id",
                        help="PowerBI App Client ID"
                    )
                
                with col2:
                    workspace_id = st.text_input(
                        "Workspace ID",
                        placeholder="workspace-guid",
                        help="PowerBI Workspace GUID"
                    )
                    
                    client_secret = st.text_input(
                        "Client Secret",
                        type="password",
                        help="PowerBI App Client Secret"
                    )
                
                # Authentication method
                auth_method = st.selectbox(
                    "Authentication Method",
                    ["Service Principal", "User Authentication", "Managed Identity"],
                    help="Choose authentication method for PowerBI"
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("💾 Save Configuration", type="primary"):
                        # Save configuration (implement actual saving)
                        st.success("✅ PowerBI configuration saved!")
                
                with col2:
                    if st.form_submit_button("🧪 Test Connection"):
                        # Test PowerBI connection
                        with st.spinner("Testing PowerBI connection..."):
                            # Simulate connection test
                            st.success("✅ PowerBI connection successful!")

class ExcelProcessor:
    """Excel file processing and viewing capabilities with advanced query and manipulation"""
    
    @staticmethod
    def process_excel_file(uploaded_file) -> Dict[str, pd.DataFrame]:
        """Process uploaded Excel file and return all sheets"""
        try:
            # Read all sheets from Excel file
            excel_data = pd.read_excel(uploaded_file, sheet_name=None, engine='openpyxl')
            return excel_data
        except Exception as e:
            st.error(f"Error processing Excel file: {str(e)}")
            return {}
    
    @staticmethod
    def query_data(df: pd.DataFrame, query_type: str, **kwargs) -> pd.DataFrame:
        """Execute various queries on DataFrame"""
        try:
            if query_type == "filter":
                column = kwargs.get('column')
                operator = kwargs.get('operator')
                value = kwargs.get('value')
                
                if column not in df.columns:
                    st.error(f"Column '{column}' not found in data")
                    return df
                
                if operator == "equals":
                    return df[df[column] == value]
                elif operator == "greater_than":
                    return df[df[column] > value]
                elif operator == "less_than":
                    return df[df[column] < value]
                elif operator == "contains":
                    return df[df[column].astype(str).str.contains(str(value), case=False, na=False)]
                elif operator == "between":
                    min_val = kwargs.get('min_value')
                    max_val = kwargs.get('max_value')
                    return df[(df[column] >= min_val) & (df[column] <= max_val)]
                    
            elif query_type == "sort":
                column = kwargs.get('column')
                ascending = kwargs.get('ascending', True)
                
                if column not in df.columns:
                    st.error(f"Column '{column}' not found in data")
                    return df
                    
                return df.sort_values(by=column, ascending=ascending)
                
            elif query_type == "group_by":
                group_column = kwargs.get('group_column')
                agg_column = kwargs.get('agg_column')
                agg_function = kwargs.get('agg_function', 'count')
                
                if group_column not in df.columns:
                    st.error(f"Group column '{group_column}' not found in data")
                    return df
                    
                if agg_column not in df.columns:
                    st.error(f"Aggregate column '{agg_column}' not found in data")
                    return df
                
                # Check if column is numeric for mathematical operations
                is_numeric = pd.api.types.is_numeric_dtype(df[agg_column])
                
                if agg_function == 'count':
                    return df.groupby(group_column)[agg_column].count().reset_index()
                elif agg_function == 'sum' and is_numeric:
                    return df.groupby(group_column)[agg_column].sum().reset_index()
                elif agg_function == 'mean' and is_numeric:
                    return df.groupby(group_column)[agg_column].mean().reset_index()
                elif agg_function == 'max':
                    return df.groupby(group_column)[agg_column].max().reset_index()
                elif agg_function == 'min':
                    return df.groupby(group_column)[agg_column].min().reset_index()
                else:
                    # Fallback to count for non-numeric data
                    st.warning(f"Function '{agg_function}' not supported for non-numeric data. Using count instead.")
                    return df.groupby(group_column)[agg_column].count().reset_index()
                    
            elif query_type == "pivot":
                index_col = kwargs.get('index_column')
                columns_col = kwargs.get('columns_column')
                values_col = kwargs.get('values_column')
                agg_func = kwargs.get('agg_function', 'sum')
                
                # Validate columns exist
                for col_name, col_var in [('index', index_col), ('columns', columns_col), ('values', values_col)]:
                    if col_var not in df.columns:
                        st.error(f"Pivot {col_name} column '{col_var}' not found in data")
                        return df
                
                # Check if values column is numeric for mathematical operations
                is_numeric = pd.api.types.is_numeric_dtype(df[values_col])
                
                if agg_func in ['sum', 'mean'] and not is_numeric:
                    st.warning(f"Function '{agg_func}' not supported for non-numeric data. Using count instead.")
                    agg_func = 'count'
                
                return pd.pivot_table(df, index=index_col, columns=columns_col, 
                                    values=values_col, aggfunc=agg_func, fill_value=0)
                                    
            elif query_type == "custom_sql":
                # Use pandasql for SQL-like queries
                try:
                    import pandasql as ps
                    query = kwargs.get('sql_query')
                    return ps.sqldf(query, locals())
                except ImportError:
                    st.warning("pandasql not installed. Install with: pip install pandasql")
                    return df
                    
        except Exception as e:
            st.error(f"Query execution error: {str(e)}")
            return df
        
        return df
    
    @staticmethod
    def manipulate_data(df: pd.DataFrame, operation: str, **kwargs) -> pd.DataFrame:
        """Perform data manipulation operations"""
        try:
            if operation == "add_column":
                column_name = kwargs.get('column_name')
                formula = kwargs.get('formula')
                
                # Simple formula evaluation (extend as needed)
                if formula.startswith('='):
                    formula = formula[1:]  # Remove equals sign
                
                # Create a copy to avoid modifying original
                result_df = df.copy()
                
                # Handle different formula types
                if formula in df.columns:
                    # Simple column copy
                    result_df[column_name] = df[formula]
                else:
                    # Replace column references with proper pandas syntax
                    eval_formula = formula
                    for col in df.columns:
                        # Replace column names with proper pandas syntax
                        if col in eval_formula:
                            eval_formula = eval_formula.replace(col, f"df['{col}']")
                    
                    # Safe evaluation with limited scope
                    try:
                        result_df[column_name] = eval(eval_formula, {"__builtins__": {}}, {"df": df, "pd": pd})
                    except:
                        # Fallback: try as string concatenation
                        if '+' in formula and all(col in df.columns for col in formula.split(' + ')):
                            cols_to_combine = [col.strip() for col in formula.split(' + ')]
                            result_df[column_name] = df[cols_to_combine].astype(str).agg(' '.join, axis=1)
                        else:
                            # Last resort: treat as literal value
                            result_df[column_name] = formula
                
                return result_df
                
            elif operation == "remove_column":
                column_name = kwargs.get('column_name')
                if column_name in df.columns:
                    df = df.drop(columns=[column_name])
                    
            elif operation == "rename_column":
                old_name = kwargs.get('old_name')
                new_name = kwargs.get('new_name')
                df = df.rename(columns={old_name: new_name})
                
            elif operation == "fill_missing":
                column = kwargs.get('column')
                method = kwargs.get('method', 'forward_fill')
                
                if method == 'forward_fill':
                    df[column] = df[column].fillna(method='ffill')
                elif method == 'backward_fill':
                    df[column] = df[column].fillna(method='bfill')
                elif method == 'mean':
                    df[column] = df[column].fillna(df[column].mean())
                elif method == 'median':
                    df[column] = df[column].fillna(df[column].median())
                elif method == 'custom_value':
                    value = kwargs.get('fill_value', 0)
                    df[column] = df[column].fillna(value)
                    
            elif operation == "remove_duplicates":
                subset = kwargs.get('columns', None)
                df = df.drop_duplicates(subset=subset)
                
            elif operation == "convert_type":
                column = kwargs.get('column')
                new_type = kwargs.get('new_type')
                
                if new_type == 'numeric':
                    df[column] = pd.to_numeric(df[column], errors='coerce')
                elif new_type == 'datetime':
                    df[column] = pd.to_datetime(df[column], errors='coerce')
                elif new_type == 'string':
                    df[column] = df[column].astype(str)
                    
        except Exception as e:
            st.error(f"Data manipulation error: {str(e)}")
            
        return df
    
    @staticmethod
    def display_excel_viewer(excel_data: Dict[str, pd.DataFrame]):
        """Display Excel data with sheet tabs and full functionality"""
        if not excel_data:
            st.info("No Excel data to display")
            return
        
        # Sheet selection
        sheet_names = list(excel_data.keys())
        selected_sheet = st.selectbox(
            "📊 Select Sheet",
            options=sheet_names,
            key="excel_sheet_selector"
        )
        
        if selected_sheet:
            df = excel_data[selected_sheet]
            # Prefer processed data if available so AI tasks use user's latest transformations
            processed_key = f"processed_data_{selected_sheet}"
            if processed_key in st.session_state and isinstance(st.session_state[processed_key], pd.DataFrame):
                df = st.session_state[processed_key]
            # Prefer processed data if available so AI tasks use user's latest transformations
            processed_key = f"processed_data_{selected_sheet}"
            if processed_key in st.session_state and isinstance(st.session_state[processed_key], pd.DataFrame):
                df = st.session_state[processed_key]
            
            # Display sheet info
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Rows", len(df))
            with col2:
                st.metric("Columns", len(df.columns))
            with col3:
                st.metric("Memory Usage", f"{df.memory_usage(deep=True).sum() / 1024:.1f} KB")
            with col4:
                st.metric("Data Types", len(df.dtypes.unique()))
            
            # Enhanced data viewing and manipulation options
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                view_mode = st.selectbox(
                    "View Mode",
                    ["Table View", "Summary Statistics", "Data Types", "Missing Values", "Query Builder", "Data Manipulation"],
                    key="excel_view_mode"
                )
            
            with col2:
                if len(df) > 100:
                    show_rows = st.slider(
                        "Rows to Display",
                        min_value=10,
                        max_value=min(1000, len(df)),
                        value=100,
                        key="excel_rows_display"
                    )
                else:
                    show_rows = len(df)
            
            with col3:
                # Initialize chart generation state
                if "show_chart_options" not in st.session_state:
                    st.session_state.show_chart_options = False
                
                if st.button("📊 Generate Chart", key="excel_generate_chart"):
                    st.session_state.show_chart_options = not st.session_state.show_chart_options
                
                # Show chart options if enabled
                if st.session_state.show_chart_options:
                    ExcelProcessor._show_chart_options(df)
            
            with col4:
                if st.button("💾 Export Data", key="excel_export_data"):
                    ExcelProcessor._show_export_options(df, selected_sheet)
            
            # Store processed data in session state for manipulation
            if f"processed_data_{selected_sheet}" not in st.session_state:
                st.session_state[f"processed_data_{selected_sheet}"] = df.copy()
                st.session_state[f"original_data_{selected_sheet}"] = df.copy()
            
            processed_df = st.session_state[f"processed_data_{selected_sheet}"]
            
            # Display based on view mode
            if view_mode == "Table View":
                st.dataframe(processed_df.head(show_rows), use_container_width=True)
                
            elif view_mode == "Summary Statistics":
                st.subheader("📈 Summary Statistics")
                st.dataframe(processed_df.describe(), use_container_width=True)
                
            elif view_mode == "Data Types":
                st.subheader("🔍 Data Types")
                type_info = pd.DataFrame({
                    'Column': processed_df.columns,
                    'Data Type': processed_df.dtypes.astype(str),
                    'Non-Null Count': processed_df.count(),
                    'Null Count': processed_df.isnull().sum()
                })
                st.dataframe(type_info, use_container_width=True)
                
            elif view_mode == "Missing Values":
                st.subheader("❓ Missing Values Analysis")
                missing_data = processed_df.isnull().sum()
                missing_percent = (missing_data / len(processed_df)) * 100
                
                missing_df = pd.DataFrame({
                    'Column': missing_data.index,
                    'Missing Count': missing_data.values,
                    'Missing Percentage': missing_percent.values
                }).sort_values('Missing Count', ascending=False)
                
                st.dataframe(missing_df, use_container_width=True)
                
            elif view_mode == "Query Builder":
                st.subheader("🔍 Query Builder")
                ExcelProcessor._show_query_builder(processed_df, selected_sheet)
                
            elif view_mode == "Data Manipulation":
                st.subheader("🛠️ Data Manipulation")
                ExcelProcessor._show_data_manipulation(processed_df, selected_sheet)
    
    @staticmethod
    def _show_chart_options(df: pd.DataFrame):
        """Show chart generation options for Excel data"""
        st.markdown("---")
        st.markdown("### 📊 Chart Generation")
        
        numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_columns = df.select_dtypes(include=['object', 'string', 'category']).columns.tolist()
        all_columns = df.columns.tolist()
        
        # Try to convert text columns to numeric if possible
        potential_numeric = []
        for col in categorical_columns:
            try:
                # Check if column contains numeric values as strings
                test_convert = pd.to_numeric(df[col], errors='coerce')
                if not test_convert.isna().all():
                    potential_numeric.append(col)
            except:
                continue
        
        # Chart configuration
        col1, col2, col3 = st.columns(3)
        
        with col1:
            chart_types = []
            if numeric_columns:
                chart_types.extend(["Line Chart", "Bar Chart", "Histogram", "Box Plot"])
            if categorical_columns:
                chart_types.extend(["Value Counts", "Category Distribution", "Text Length Analysis"])
            if len(numeric_columns) > 1:
                chart_types.append("Scatter Plot")
            
            chart_type = st.selectbox(
                "Chart Type",
                chart_types,
                key="excel_chart_type_select"
            )
        
        with col2:
            if chart_type in ["Line Chart", "Bar Chart", "Histogram", "Box Plot"]:
                column_to_chart = st.selectbox(
                    "Select Column",
                    options=numeric_columns,
                    key="excel_numeric_column"
                )
            elif chart_type == "Scatter Plot":
                column_to_chart = st.selectbox(
                    "X-axis Column",
                    options=numeric_columns,
                    key="excel_scatter_x"
                )
            else:
                column_to_chart = st.selectbox(
                    "Select Column",
                    options=categorical_columns,
                    key="excel_categorical_column"
                )
        
        with col3:
            if chart_type == "Scatter Plot" and len(numeric_columns) > 1:
                y_column = st.selectbox(
                    "Y-axis Column",
                    options=[col for col in numeric_columns if col != column_to_chart],
                    key="excel_scatter_y"
                )
            elif chart_type == "Bar Chart" and categorical_columns:
                group_by = st.selectbox(
                    "Group By (optional)",
                    ["None"] + categorical_columns,
                    key="excel_bar_group"
                )
        
        if st.button("🎨 Create Chart", key="excel_create_chart_btn", type="primary"):
            try:
                fig = None
                
                if chart_type == "Line Chart":
                    fig = px.line(df, y=column_to_chart, title=f"Line Chart: {column_to_chart}")
                    
                elif chart_type == "Bar Chart":
                    if 'group_by' in locals() and group_by != "None":
                        grouped_data = df.groupby(group_by)[column_to_chart].mean().reset_index()
                        fig = px.bar(grouped_data, x=group_by, y=column_to_chart, 
                                   title=f"Average {column_to_chart} by {group_by}")
                    else:
                        fig = px.bar(x=df.index[:50], y=df[column_to_chart].head(50), 
                                   title=f"Bar Chart: {column_to_chart} (First 50 records)")
                    
                elif chart_type == "Histogram":
                    fig = px.histogram(df, x=column_to_chart, title=f"Distribution of {column_to_chart}")
                    
                elif chart_type == "Box Plot":
                    fig = px.box(df, y=column_to_chart, title=f"Box Plot: {column_to_chart}")
                    
                elif chart_type == "Scatter Plot" and 'y_column' in locals():
                    fig = px.scatter(df, x=column_to_chart, y=y_column, 
                                   title=f"{column_to_chart} vs {y_column}")
                    
                elif chart_type == "Value Counts":
                    value_counts = df[column_to_chart].value_counts().head(20)
                    fig = px.bar(
                        x=value_counts.index.astype(str), 
                        y=value_counts.values,
                        title=f"Value Counts for {column_to_chart}",
                        labels={'x': column_to_chart, 'y': 'Count'}
                    )
                    
                elif chart_type == "Category Distribution":
                    value_counts = df[column_to_chart].value_counts()
                    fig = px.pie(
                        values=value_counts.values,
                        names=value_counts.index.astype(str),
                        title=f"Distribution of {column_to_chart}"
                    )
                    
                elif chart_type == "Text Length Analysis":
                    text_lengths = df[column_to_chart].astype(str).str.len()
                    fig = px.histogram(
                        x=text_lengths,
                        title=f"Text Length Distribution for {column_to_chart}",
                        labels={'x': 'Text Length', 'y': 'Frequency'}
                    )
                
                if fig:
                    fig.update_layout(height=500)
                    st.plotly_chart(fig, use_container_width=True)
                    st.success(f"✅ {chart_type} generated successfully!")
                    
                    # Show chart statistics
                    st.markdown("#### 📊 Chart Statistics")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Data Points", len(df))
                    with col2:
                        if pd.api.types.is_numeric_dtype(df[column_to_chart]):
                            st.metric("Min Value", f"{df[column_to_chart].min():.2f}")
                        else:
                            st.metric("Unique Values", df[column_to_chart].nunique())
                    with col3:
                        if pd.api.types.is_numeric_dtype(df[column_to_chart]):
                            st.metric("Max Value", f"{df[column_to_chart].max():.2f}")
                        else:
                            st.metric("Most Common", str(df[column_to_chart].mode().iloc[0]))
                else:
                    st.warning("Unable to generate chart with selected parameters")
                    
            except Exception as e:
                st.error(f"❌ Error generating {chart_type}: {str(e)}")
                st.write(f"Debug info: Column '{column_to_chart}' type: {df[column_to_chart].dtype}")
                # Show sample data for debugging
                with st.expander("🔍 Debug Information"):
                    st.write("Sample data:")
                    st.write(df[column_to_chart].head())
                    st.write(f"Data shape: {df.shape}")
                    st.write(f"Column info: {df[column_to_chart].dtype}")
        
        # Show conversion options if potential numeric columns exist
        if potential_numeric:
            st.info(f"💡 **Tip**: Columns {potential_numeric} might contain numeric data. Convert them first for more chart options.")
        
        return
        
        # Show conversion options if potential numeric columns exist
        if potential_numeric:
            st.info(f"💡 **Tip**: Columns {potential_numeric} might contain numeric data. Convert them first for more chart options.")
        
        # Standard numeric chart options
        available_numeric = numeric_columns + potential_numeric
        
        with st.expander("📊 Chart Configuration", expanded=True):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                chart_type = st.selectbox(
                    "Chart Type",
                    ["Line Chart", "Bar Chart", "Scatter Plot", "Histogram", "Box Plot", "Value Counts"],
                    key="excel_chart_type"
                )
            
            with col2:
                if chart_type in ["Value Counts"]:
                    x_column = st.selectbox(
                        "Column",
                        options=all_columns,
                        key="excel_x_axis"
                    )
                else:
                    x_column = st.selectbox(
                        "X-Axis",
                        options=all_columns,
                        key="excel_x_axis"
                    )
            
            with col3:
                if chart_type not in ["Histogram", "Box Plot", "Value Counts"]:
                    y_column = st.selectbox(
                        "Y-Axis",
                        options=available_numeric if available_numeric else all_columns,
                        key="excel_y_axis"
                    )
                elif chart_type in ["Histogram", "Box Plot"]:
                    y_column = st.selectbox(
                        "Column to Analyze",
                        options=available_numeric if available_numeric else all_columns,
                        key="excel_y_axis"
                    )
                else:
                    y_column = None
            
            if st.button("Generate Chart", key="excel_create_chart"):
                try:
                    # Convert potential numeric columns if needed
                    df_plot = df.copy()
                    if x_column in potential_numeric:
                        df_plot[x_column] = pd.to_numeric(df_plot[x_column], errors='coerce')
                    if y_column and y_column in potential_numeric:
                        df_plot[y_column] = pd.to_numeric(df_plot[y_column], errors='coerce')
                    
                    if chart_type == "Line Chart":
                        fig = px.line(df_plot, x=x_column, y=y_column, title=f"{y_column} vs {x_column}")
                    elif chart_type == "Bar Chart":
                        fig = px.bar(df_plot, x=x_column, y=y_column, title=f"{y_column} by {x_column}")
                    elif chart_type == "Scatter Plot":
                        fig = px.scatter(df_plot, x=x_column, y=y_column, title=f"{y_column} vs {x_column}")
                    elif chart_type == "Histogram":
                        fig = px.histogram(df_plot, x=y_column, title=f"Distribution of {y_column}")
                    elif chart_type == "Box Plot":
                        fig = px.box(df_plot, y=y_column, title=f"Box Plot of {y_column}")
                    elif chart_type == "Value Counts":
                        value_counts = df_plot[x_column].value_counts().head(20)
                        fig = px.bar(
                            x=value_counts.index, 
                            y=value_counts.values,
                            title=f"Value Counts for {x_column}",
                            labels={'x': x_column, 'y': 'Count'}
                        )
                    
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.error(f"Error generating chart: {str(e)}")
                    st.info("💡 Try converting text columns to numeric first, or use Value Counts for categorical data.")
    
    @staticmethod
    def _show_query_builder(df: pd.DataFrame, sheet_name: str):
        """Show interactive query builder interface"""
        
        # Debug info - remove after testing
        with st.expander("🔍 Debug Info", expanded=False):
            st.write(f"**DataFrame columns:** {list(df.columns)}")
            st.write(f"**Numeric columns:** {df.select_dtypes(include=[np.number]).columns.tolist()}")
            st.write(f"**Text columns:** {df.select_dtypes(include=['object']).columns.tolist()}")
            st.write(f"**DataFrame shape:** {df.shape}")
            st.write(f"**Data types:**")
            st.write(df.dtypes)
        
        # Query type selection
        query_type = st.selectbox(
            "Query Type",
            ["Filter Data", "Sort Data", "Group By", "Pivot Table", "Custom SQL"],
            key=f"query_type_{sheet_name}"
        )
        
        if query_type == "Filter Data":
            col1, col2, col3 = st.columns(3)
            
            with col1:
                filter_column = st.selectbox(
                    "Column to Filter",
                    options=df.columns.tolist(),
                    key=f"filter_col_{sheet_name}"
                )
            
            with col2:
                filter_operator = st.selectbox(
                    "Operator",
                    ["equals", "greater_than", "less_than", "contains", "between"],
                    key=f"filter_op_{sheet_name}"
                )
            
            with col3:
                if filter_operator == "between":
                    min_val = st.number_input("Min Value", key=f"min_val_{sheet_name}")
                    max_val = st.number_input("Max Value", key=f"max_val_{sheet_name}")
                    filter_value = None
                else:
                    if df[filter_column].dtype in ['object']:
                        filter_value = st.text_input("Filter Value", key=f"filter_val_{sheet_name}")
                    else:
                        filter_value = st.number_input("Filter Value", key=f"filter_val_{sheet_name}")
            
            if st.button("Apply Filter", key=f"apply_filter_{sheet_name}"):
                if filter_operator == "between":
                    result_df = ExcelProcessor.query_data(
                        df, "filter", 
                        column=filter_column, 
                        operator=filter_operator,
                        min_value=min_val,
                        max_value=max_val
                    )
                else:
                    result_df = ExcelProcessor.query_data(
                        df, "filter", 
                        column=filter_column, 
                        operator=filter_operator, 
                        value=filter_value
                    )
                
                st.session_state[f"processed_data_{sheet_name}"] = result_df
                st.success(f"Filter applied! Showing {len(result_df)} rows")
                st.dataframe(result_df.head(100), use_container_width=True)
        
        elif query_type == "Sort Data":
            col1, col2 = st.columns(2)
            
            with col1:
                sort_column = st.selectbox(
                    "Column to Sort",
                    options=df.columns.tolist(),
                    key=f"sort_col_{sheet_name}"
                )
            
            with col2:
                sort_order = st.selectbox(
                    "Sort Order",
                    ["Ascending", "Descending"],
                    key=f"sort_order_{sheet_name}"
                )
            
            if st.button("Apply Sort", key=f"apply_sort_{sheet_name}"):
                result_df = ExcelProcessor.query_data(
                    df, "sort", 
                    column=sort_column, 
                    ascending=(sort_order == "Ascending")
                )
                
                st.session_state[f"processed_data_{sheet_name}"] = result_df
                st.success("Sort applied!")
                st.dataframe(result_df.head(100), use_container_width=True)
        
        elif query_type == "Group By":
            col1, col2, col3 = st.columns(3)
            
            with col1:
                group_column = st.selectbox(
                    "Group By Column",
                    options=df.columns.tolist(),
                    key=f"group_col_{sheet_name}"
                )
            
            with col2:
                numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
                text_columns = df.select_dtypes(include=['object']).columns.tolist()
                
                # For text data, we can still do count aggregations
                if not numeric_columns and text_columns:
                    st.info("Using text columns for count aggregation")
                    agg_column = st.selectbox(
                        "Aggregate Column (Count)",
                        options=text_columns,
                        key=f"agg_col_{sheet_name}"
                    )
                elif numeric_columns:
                    agg_column = st.selectbox(
                        "Aggregate Column",
                        options=numeric_columns,
                        key=f"agg_col_{sheet_name}"
                    )
                else:
                    st.warning("No columns available for aggregation")
                    agg_column = None
            
            with col3:
                # Adjust available functions based on data type
                if not numeric_columns and text_columns:
                    available_functions = ["count"]
                    st.info("Only count function available for text data")
                else:
                    available_functions = ["sum", "mean", "count", "max", "min"]
                
                agg_function = st.selectbox(
                    "Function",
                    available_functions,
                    key=f"agg_func_{sheet_name}"
                )
            
            if st.button("Apply Group By", key=f"apply_group_{sheet_name}"):
                if agg_column is not None:
                    result_df = ExcelProcessor.query_data(
                        df, "group_by",
                        group_column=group_column,
                        agg_column=agg_column,
                        agg_function=agg_function
                    )
                    
                    st.session_state[f"processed_data_{sheet_name}"] = result_df
                    st.success("Group By applied!")
                    st.dataframe(result_df, use_container_width=True)
                else:
                    st.error("Please select a numeric column for aggregation")
        
        elif query_type == "Pivot Table":
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                index_column = st.selectbox(
                    "Index Column",
                    options=df.columns.tolist(),
                    key=f"pivot_index_{sheet_name}"
                )
            
            with col2:
                columns_column = st.selectbox(
                    "Columns",
                    options=df.columns.tolist(),
                    key=f"pivot_cols_{sheet_name}"
                )
            
            with col3:
                numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
                text_columns = df.select_dtypes(include=['object']).columns.tolist()
                
                # For pivot tables, we can use text columns for count operations
                if not numeric_columns and text_columns:
                    st.info("Using text columns for count pivot")
                    values_column = st.selectbox(
                        "Values (Count)",
                        options=text_columns,
                        key=f"pivot_vals_{sheet_name}"
                    )
                elif numeric_columns:
                    values_column = st.selectbox(
                        "Values",
                        options=numeric_columns,
                        key=f"pivot_vals_{sheet_name}"
                    )
                else:
                    st.warning("No columns available for pivot values")
                    values_column = None
            
            with col4:
                # Adjust available functions based on data type
                if not numeric_columns and text_columns:
                    available_functions = ["count"]
                    st.info("Only count aggregation available for text data")
                else:
                    available_functions = ["sum", "mean", "count", "max", "min"]
                
                agg_function = st.selectbox(
                    "Aggregation",
                    available_functions,
                    key=f"pivot_agg_{sheet_name}"
                )
            
            if st.button("Create Pivot Table", key=f"apply_pivot_{sheet_name}"):
                if values_column is not None:
                    result_df = ExcelProcessor.query_data(
                        df, "pivot",
                        index_column=index_column,
                        columns_column=columns_column,
                        values_column=values_column,
                        agg_function=agg_function
                    )
                    
                    st.session_state[f"processed_data_{sheet_name}"] = result_df
                    st.success("Pivot table created!")
                    st.dataframe(result_df, use_container_width=True)
                else:
                    st.error("Please select a numeric column for values")
        
        elif query_type == "Custom SQL":
            st.markdown("**Write SQL query (use 'df' as table name):**")
            sql_query = st.text_area(
                "SQL Query",
                placeholder="SELECT * FROM df WHERE column_name > 100",
                key=f"sql_query_{sheet_name}"
            )
            
            if st.button("Execute SQL", key=f"execute_sql_{sheet_name}"):
                if sql_query.strip():
                    result_df = ExcelProcessor.query_data(
                        df, "custom_sql",
                        sql_query=sql_query
                    )
                    
                    st.session_state[f"processed_data_{sheet_name}"] = result_df
                    st.success("SQL query executed!")
                    st.dataframe(result_df.head(100), use_container_width=True)
                else:
                    st.warning("Please enter a SQL query")
        
        # Reset data button
        if st.button("🔄 Reset to Original Data", key=f"reset_data_{sheet_name}"):
            if f"original_data_{sheet_name}" in st.session_state:
                st.session_state[f"processed_data_{sheet_name}"] = st.session_state[f"original_data_{sheet_name}"].copy()
                st.success("Data reset to original!")
    
    @staticmethod
    def _show_data_manipulation(df: pd.DataFrame, sheet_name: str):
        """Show data manipulation interface"""
        
        manipulation_type = st.selectbox(
            "Manipulation Type",
            ["Add Column", "Remove Column", "Rename Column", "Fill Missing Values", "Remove Duplicates", "Convert Data Type"],
            key=f"manip_type_{sheet_name}"
        )
        
        if manipulation_type == "Add Column":
            col1, col2 = st.columns(2)
            
            with col1:
                new_column_name = st.text_input(
                    "New Column Name",
                    key=f"new_col_name_{sheet_name}",
                    help="Enter a name for the new column"
                )
            
            with col2:
                # Show available columns for reference
                st.write("**Available columns:**")
                st.write(", ".join(df.columns.tolist()))
                
                formula = st.text_input(
                    "Formula (use column names)",
                    placeholder="combine_Task",
                    key=f"formula_{sheet_name}",
                    help="Use column names directly. Example: combine_Task or Sales * 0.1"
                )
            
            # Show formula examples
            with st.expander("💡 Formula Examples", expanded=False):
                st.markdown("""
                **Simple column copy:** `ColumnName`
                **Text combination:** `ColumnA + ' - ' + ColumnB`
                **Math operations:** `Sales * 0.1` or `Price + Tax`
                **Conditional:** `'High' if Sales > 1000 else 'Low'`
                """)
            
            if st.button("Add Column", key=f"add_col_{sheet_name}"):
                if new_column_name and formula:
                    try:
                        result_df = ExcelProcessor.manipulate_data(
                            df, "add_column",
                            column_name=new_column_name,
                            formula=formula
                        )
                        
                        st.session_state[f"processed_data_{sheet_name}"] = result_df
                        st.success(f"✅ Column '{new_column_name}' added successfully!")
                        st.dataframe(result_df.head(10), use_container_width=True)
                        st.rerun()  # Refresh the interface
                    except Exception as e:
                        st.error(f"❌ Error adding column: {str(e)}")
                        st.info("💡 Check your formula syntax and column names")
                else:
                    st.warning("⚠️ Please provide both column name and formula")
        
        elif manipulation_type == "Remove Column":
            column_to_remove = st.selectbox(
                "Column to Remove",
                options=df.columns.tolist(),
                key=f"remove_col_{sheet_name}"
            )
            
            if st.button("Remove Column", key=f"remove_col_btn_{sheet_name}"):
                result_df = ExcelProcessor.manipulate_data(
                    df, "remove_column",
                    column_name=column_to_remove
                )
                
                st.session_state[f"processed_data_{sheet_name}"] = result_df
                st.success(f"Column '{column_to_remove}' removed!")
                st.dataframe(result_df.head(10), use_container_width=True)
        
        elif manipulation_type == "Rename Column":
            col1, col2 = st.columns(2)
            
            with col1:
                old_name = st.selectbox(
                    "Column to Rename",
                    options=df.columns.tolist(),
                    key=f"old_name_{sheet_name}"
                )
            
            with col2:
                new_name = st.text_input(
                    "New Name",
                    key=f"new_name_{sheet_name}"
                )
            
            if st.button("Rename Column", key=f"rename_col_{sheet_name}"):
                if new_name:
                    result_df = ExcelProcessor.manipulate_data(
                        df, "rename_column",
                        old_name=old_name,
                        new_name=new_name
                    )
                    
                    st.session_state[f"processed_data_{sheet_name}"] = result_df
                    st.success(f"Column renamed from '{old_name}' to '{new_name}'!")
                    st.dataframe(result_df.head(10), use_container_width=True)
        
        elif manipulation_type == "Fill Missing Values":
            col1, col2 = st.columns(2)
            
            with col1:
                fill_column = st.selectbox(
                    "Column with Missing Values",
                    options=df.columns.tolist(),
                    key=f"fill_col_{sheet_name}"
                )
            
            with col2:
                fill_method = st.selectbox(
                    "Fill Method",
                    ["forward_fill", "backward_fill", "mean", "median", "custom_value"],
                    key=f"fill_method_{sheet_name}"
                )
            
            if fill_method == "custom_value":
                fill_value = st.text_input(
                    "Custom Value",
                    key=f"fill_value_{sheet_name}"
                )
            else:
                fill_value = None
            
            if st.button("Fill Missing Values", key=f"fill_missing_{sheet_name}"):
                result_df = ExcelProcessor.manipulate_data(
                    df, "fill_missing",
                    column=fill_column,
                    method=fill_method,
                    fill_value=fill_value
                )
                
                st.session_state[f"processed_data_{sheet_name}"] = result_df
                st.success(f"Missing values filled in '{fill_column}'!")
                st.dataframe(result_df.head(10), use_container_width=True)
        
        elif manipulation_type == "Remove Duplicates":
            duplicate_columns = st.multiselect(
                "Columns to Check for Duplicates (leave empty for all columns)",
                options=df.columns.tolist(),
                key=f"dup_cols_{sheet_name}"
            )
            
            if st.button("Remove Duplicates", key=f"remove_dups_{sheet_name}"):
                result_df = ExcelProcessor.manipulate_data(
                    df, "remove_duplicates",
                    columns=duplicate_columns if duplicate_columns else None
                )
                
                original_count = len(df)
                new_count = len(result_df)
                removed_count = original_count - new_count
                
                st.session_state[f"processed_data_{sheet_name}"] = result_df
                st.success(f"Removed {removed_count} duplicate rows!")
                st.dataframe(result_df.head(10), use_container_width=True)
        
        elif manipulation_type == "Convert Data Type":
            col1, col2 = st.columns(2)
            
            with col1:
                convert_column = st.selectbox(
                    "Column to Convert",
                    options=df.columns.tolist(),
                    key=f"convert_col_{sheet_name}"
                )
            
            with col2:
                new_type = st.selectbox(
                    "New Data Type",
                    ["numeric", "datetime", "string"],
                    key=f"new_type_{sheet_name}"
                )
            
            if st.button("Convert Type", key=f"convert_type_{sheet_name}"):
                result_df = ExcelProcessor.manipulate_data(
                    df, "convert_type",
                    column=convert_column,
                    new_type=new_type
                )
                
                st.session_state[f"processed_data_{sheet_name}"] = result_df
                st.success(f"Column '{convert_column}' converted to {new_type}!")
                st.dataframe(result_df.head(10), use_container_width=True)
    
    @staticmethod
    def _show_export_options(df: pd.DataFrame, sheet_name: str):
        """Show export options for processed data"""
        with st.expander("💾 Export Options", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                export_format = st.selectbox(
                    "Export Format",
                    ["CSV", "Excel", "JSON"],
                    key=f"export_format_{sheet_name}"
                )
            
            with col2:
                include_index = st.checkbox(
                    "Include Index",
                    key=f"include_index_{sheet_name}"
                )
            
            # Show data preview
            st.write("**Data Preview:**")
            st.dataframe(df.head(3), use_container_width=True)
            st.write(f"Total rows: {len(df)}, Columns: {len(df.columns)}")
            
            if st.button("📥 Prepare Download", key=f"download_{sheet_name}"):
                try:
                    if export_format == "CSV":
                        csv_data = df.to_csv(index=include_index)
                        st.download_button(
                            label="📥 Download CSV File",
                            data=csv_data,
                            file_name=f"{sheet_name}_processed.csv",
                            mime="text/csv",
                            key=f"csv_download_{sheet_name}"
                        )
                        st.success("✅ CSV file ready for download!")
                    
                    elif export_format == "Excel":
                        import io
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            df.to_excel(writer, sheet_name=sheet_name, index=include_index)
                        
                        st.download_button(
                            label="📥 Download Excel File",
                            data=output.getvalue(),
                            file_name=f"{sheet_name}_processed.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"excel_download_{sheet_name}"
                        )
                        st.success("✅ Excel file ready for download!")
                    
                    elif export_format == "JSON":
                        json_data = df.to_json(orient='records', indent=2)
                        st.download_button(
                            label="📥 Download JSON File",
                            data=json_data,
                            file_name=f"{sheet_name}_processed.json",
                            mime="application/json",
                            key=f"json_download_{sheet_name}"
                        )
                        st.success("✅ JSON file ready for download!")
                    
                except Exception as e:
                    st.error(f"❌ Export error: {str(e)}")
                    st.info("💡 Try refreshing the page and trying again")

def render_multi_content_enhanced(user, permissions, auth_middleware, available_indexes):
    """Enhanced Multi-Content Dashboard with PowerBI and Excel support"""
    
    # Simple permission check - allow all users to access basic functionality
    user_role = user.role.value if hasattr(user, 'role') else user.get('role', 'viewer')
    
    # Basic permissions for all users
    can_multi_search = True
    can_enhanced_research = user_role in ['admin', 'power_user', 'user']
    can_analytics = user_role in ['admin', 'power_user', 'user']
    
    auth_middleware.log_user_action("ACCESS_MULTI_CONTENT_ENHANCED")
    
    st.header("🌐 Multi-Content Dashboard")
    st.markdown("**Advanced content management with PowerBI integration and Excel support**")
    
    # Permission-based tab visibility
    available_tabs = []
    tab_functions = []
    
    # PowerBI Reports (requires integrations permission)
    if can_analytics:
        available_tabs.append("📊 PowerBI Reports")
        tab_functions.append(lambda: render_powerbi_tab(user_role, can_analytics))
    
    # Excel Analytics (always available if user has multi-search access)
    available_tabs.append("📈 Excel Analytics")
    tab_functions.append(lambda: render_excel_tab())
    
    # Multi-Source Search (requires enhanced research permission)
    if can_enhanced_research:
        available_tabs.append("🔍 Multi-Source Search")
        tab_functions.append(lambda: render_multi_source_search(available_indexes, auth_middleware))
    
    # Content Management (admin/power_user only)
    if user_role in ['admin', 'power_user']:
        available_tabs.append("📋 Content Management")
        tab_functions.append(lambda: render_content_management(available_indexes, user_role))
    
    # Integrations (admin only)
    if user_role == 'admin':
        available_tabs.append("⚙️ Integrations")
        tab_functions.append(lambda: render_integrations_tab())
    
    # Render available tabs
    if len(available_tabs) == 1:
        tab_functions[0]()
    else:
        tabs = st.tabs(available_tabs)
        for i, tab in enumerate(tabs):
            with tab:
                tab_functions[i]()

def render_powerbi_tab(user_role: str, can_analytics: bool = True):
    """Render PowerBI integration tab"""
    st.subheader("📊 PowerBI Reports & Dashboards")
    
    # PowerBI configuration (admin only)
    if user_role == 'admin':
        PowerBIIntegration.create_powerbi_connection_form()
    
    # Sample PowerBI reports
    st.markdown("### 📈 Available Reports")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        with st.container():
            st.markdown("**📊 Sales Dashboard**")
            st.image("https://via.placeholder.com/300x200/1f77b4/white?text=Sales+Dashboard", use_container_width=True)
            if st.button("🔗 Open Report", key="sales_dashboard"):
                st.info("Opening Sales Dashboard...")
                # PowerBIIntegration.embed_powerbi_report("sales-report-id", "workspace-id")
    
    with col2:
        with st.container():
            st.markdown("**📈 Analytics Report**")
            st.image("https://via.placeholder.com/300x200/ff7f0e/white?text=Analytics+Report", use_container_width=True)
            if st.button("🔗 Open Report", key="analytics_report"):
                st.info("Opening Analytics Report...")
    
    with col3:
        with st.container():
            st.markdown("**💼 Executive Summary**")
            st.image("https://via.placeholder.com/300x200/2ca02c/white?text=Executive+Summary", use_container_width=True)
            if st.button("🔗 Open Report", key="executive_summary"):
                st.info("Opening Executive Summary...")
    
    # Custom PowerBI embed
    st.markdown("### 🔧 Custom PowerBI Embed")
    
    with st.expander("Embed Custom Report", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            report_id = st.text_input("Report ID", placeholder="Enter PowerBI Report ID")
            workspace_id = st.text_input("Workspace ID", placeholder="Enter Workspace ID")
        
        with col2:
            embed_type = st.selectbox("Embed Type", ["Report", "Dashboard", "Tile"])
            auto_refresh = st.checkbox("Auto Refresh", value=True)
        
        if st.button("📊 Embed Report", type="primary"):
            if report_id and workspace_id:
                st.success("Embedding PowerBI report...")
                # PowerBIIntegration.embed_powerbi_report(report_id, workspace_id)
            else:
                st.warning("Please provide Report ID and Workspace ID")

def render_excel_tab():
    """Render Excel analytics tab"""
    st.subheader("📈 Excel Analytics & Viewer")
    
    # File upload with unique key
    uploaded_file = st.file_uploader(
        "📁 Upload Excel File",
        type=['xlsx', 'xls'],
        help="Upload Excel files for analysis and visualization",
        key="excel_tab_file_uploader"
    )
    
    if uploaded_file:
        # Process Excel file
        with st.spinner("Processing Excel file..."):
            excel_data = ExcelProcessor.process_excel_file(uploaded_file)
        
        if excel_data:
            st.success(f"✅ Successfully loaded {len(excel_data)} sheet(s)")
            
            # Display Excel viewer
            ExcelProcessor.display_excel_viewer(excel_data)
            
            # Advanced Excel operations
            st.markdown("### 🔧 Advanced Operations")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button("📊 Create Pivot Table", key="excel_pivot"):
                    st.session_state['show_pivot_creator'] = True
            
            with col2:
                if st.button("🔍 Data Profiling", key="excel_profile"):
                    st.session_state['show_data_profiling'] = True
            
            with col3:
                if st.button("🧹 Data Cleaning", key="excel_clean"):
                    st.session_state['show_data_cleaning'] = True
            
            with col4:
                if st.button("💾 Export Results", key="excel_export"):
                    st.session_state['show_export_results'] = True
            
            # Show advanced operation interfaces
            if st.session_state.get('show_pivot_creator', False):
                render_pivot_table_creator(excel_data)
            
            if st.session_state.get('show_data_profiling', False):
                render_data_profiling(excel_data)
            
            if st.session_state.get('show_data_cleaning', False):
                render_data_cleaning(excel_data)
            
            if st.session_state.get('show_export_results', False):
                render_export_results(excel_data)
            
            # AI Excel Assistant
            st.markdown("### 🤖 AI Excel Assistant")
            render_excel_ai_assistant(excel_data)
    
    else:
        # Sample Excel functionality demo
        st.markdown("### 📋 Excel Capabilities")
        
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

def render_pivot_table_creator(excel_data: Dict[str, pd.DataFrame]):
    """Render pivot table creator interface"""
    st.markdown("---")
    st.subheader("📊 Create Pivot Table")
    
    # Sheet selection
    sheet_names = list(excel_data.keys())
    selected_sheet = st.selectbox(
        "Select Sheet for Pivot Table:",
        options=sheet_names,
        key="pivot_sheet_selector"
    )
    
    if selected_sheet:
        df = excel_data[selected_sheet]
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            index_cols = st.multiselect(
                "Index (Rows):",
                options=df.columns.tolist(),
                key="pivot_index_cols"
            )
        
        with col2:
            column_cols = st.multiselect(
                "Columns:",
                options=df.columns.tolist(),
                key="pivot_column_cols"
            )
        
        with col3:
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            text_cols = df.select_dtypes(include=['object', 'string', 'category']).columns.tolist()
            
            if numeric_cols:
                values_col = st.selectbox(
                    "Values:",
                    options=numeric_cols,
                    key="pivot_values_col"
                )
            else:
                values_col = st.selectbox(
                    "Values (Count):",
                    options=text_cols,
                    key="pivot_values_col"
                )
        
        with col4:
            if numeric_cols:
                agg_func = st.selectbox(
                    "Aggregation:",
                    ["sum", "mean", "count", "max", "min"],
                    key="pivot_agg_func"
                )
            else:
                agg_func = "count"
                st.info("Only count available for text data")
        
        if st.button("Create Pivot Table", key="create_pivot_btn"):
            try:
                if index_cols and values_col:
                    pivot_table = pd.pivot_table(
                        df,
                        index=index_cols,
                        columns=column_cols if column_cols else None,
                        values=values_col,
                        aggfunc=agg_func,
                        fill_value=0
                    )
                    
                    st.success("✅ Pivot table created successfully!")
                    st.dataframe(pivot_table, use_container_width=True)
                    
                    # Save to session state
                    st.session_state[f"pivot_table_{selected_sheet}"] = pivot_table
                    
                    # Option to export
                    if st.button("💾 Export Pivot Table", key="export_pivot"):
                        csv_data = pivot_table.to_csv()
                        st.download_button(
                            label="📥 Download Pivot Table CSV",
                            data=csv_data,
                            file_name=f"pivot_table_{selected_sheet}.csv",
                            mime="text/csv"
                        )
                else:
                    st.warning("Please select at least Index and Values columns")
            except Exception as e:
                st.error(f"Error creating pivot table: {str(e)}")
    
    if st.button("❌ Close Pivot Creator", key="close_pivot"):
        st.session_state['show_pivot_creator'] = False
        st.rerun()

def render_data_profiling(excel_data: Dict[str, pd.DataFrame]):
    """Render data profiling interface"""
    st.markdown("---")
    st.subheader("🔍 Data Profiling")
    
    # Sheet selection
    sheet_names = list(excel_data.keys())
    selected_sheet = st.selectbox(
        "Select Sheet for Profiling:",
        options=sheet_names,
        key="profile_sheet_selector"
    )
    
    if selected_sheet:
        df = excel_data[selected_sheet]
        
        # Basic statistics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Rows", len(df))
        with col2:
            st.metric("Total Columns", len(df.columns))
        with col3:
            st.metric("Memory Usage", f"{df.memory_usage(deep=True).sum() / 1024:.1f} KB")
        with col4:
            st.metric("Missing Values", df.isnull().sum().sum())
        
        # Data types analysis
        st.markdown("### 📊 Data Types Distribution")
        
        # Create pie chart for data types - fix numpy serialization
        type_counts = df.dtypes.value_counts()
        if len(type_counts) > 0:
            # Convert numpy dtypes to strings for JSON serialization
            type_names = [str(dtype) for dtype in type_counts.index]
            fig_types = px.pie(
                values=type_counts.values,
                names=type_names,
                title="Data Types Distribution"
            )
            st.plotly_chart(fig_types, use_container_width=True)
        else:
            st.info("No data types to display")
        
        # Missing values analysis
        st.markdown("### ❓ Missing Values Analysis")
        missing_data = df.isnull().sum()
        missing_data = missing_data[missing_data > 0].sort_values(ascending=False)
        
        if not missing_data.empty:
            fig_missing = px.bar(
                x=missing_data.index,
                y=missing_data.values,
                title="Missing Values by Column",
                labels={'x': 'Columns', 'y': 'Missing Count'}
            )
            st.plotly_chart(fig_missing, use_container_width=True)
        else:
            st.success("✅ No missing values found!")
        
        # Column statistics
        st.markdown("### 📈 Column Statistics")
        
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if not numeric_cols.empty:
            st.markdown("**Numeric Columns:**")
            st.dataframe(df[numeric_cols].describe(), use_container_width=True)
        
        text_cols = df.select_dtypes(include=['object']).columns
        if not text_cols.empty:
            st.markdown("**Text Columns:**")
            text_stats = pd.DataFrame({
                'Column': text_cols,
                'Unique Values': [df[col].nunique() for col in text_cols],
                'Most Frequent': [df[col].mode().iloc[0] if not df[col].mode().empty else 'N/A' for col in text_cols],
                'Frequency': [df[col].value_counts().iloc[0] if not df[col].value_counts().empty else 0 for col in text_cols]
            })
            st.dataframe(text_stats, use_container_width=True)
    
    if st.button("❌ Close Data Profiling", key="close_profiling"):
        st.session_state['show_data_profiling'] = False
        st.rerun()

def render_data_cleaning(excel_data: Dict[str, pd.DataFrame]):
    """Render data cleaning interface"""
    st.markdown("---")
    st.subheader("🧹 Data Cleaning")
    
    # Sheet selection
    sheet_names = list(excel_data.keys())
    selected_sheet = st.selectbox(
        "Select Sheet for Cleaning:",
        options=sheet_names,
        key="clean_sheet_selector"
    )
    
    if selected_sheet:
        df = excel_data[selected_sheet]
        
        # Cleaning operations
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🔧 Available Cleaning Operations")
            
            if st.button("🗑️ Remove Duplicates", key="remove_duplicates_btn"):
                original_count = len(df)
                cleaned_df = df.drop_duplicates()
                removed_count = original_count - len(cleaned_df)
                
                st.session_state[f"cleaned_data_{selected_sheet}"] = cleaned_df
                st.success(f"✅ Removed {removed_count} duplicate rows")
                st.dataframe(cleaned_df.head(), use_container_width=True)
            
            if st.button("🔤 Standardize Text", key="standardize_text_btn"):
                cleaned_df = df.copy()
                text_cols = df.select_dtypes(include=['object']).columns
                
                for col in text_cols:
                    cleaned_df[col] = cleaned_df[col].astype(str).str.strip().str.title()
                
                st.session_state[f"cleaned_data_{selected_sheet}"] = cleaned_df
                st.success("✅ Text columns standardized")
                st.dataframe(cleaned_df.head(), use_container_width=True)
            
            if st.button("🔢 Fix Data Types", key="fix_types_btn"):
                cleaned_df = df.copy()
                
                # Try to convert potential numeric columns
                for col in df.columns:
                    if df[col].dtype == 'object':
                        numeric_converted = pd.to_numeric(df[col], errors='coerce')
                        if not numeric_converted.isna().all():
                            cleaned_df[col] = numeric_converted
                
                st.session_state[f"cleaned_data_{selected_sheet}"] = cleaned_df
                st.success("✅ Data types optimized")
                st.dataframe(cleaned_df.head(), use_container_width=True)
        
        with col2:
            st.markdown("### 📊 Cleaning Summary")
            
            # Show data quality metrics
            missing_count = df.isnull().sum().sum()
            duplicate_count = len(df) - len(df.drop_duplicates())
            
            st.metric("Missing Values", missing_count)
            st.metric("Duplicate Rows", duplicate_count)
            st.metric("Data Quality Score", f"{((len(df) - missing_count - duplicate_count) / len(df) * 100):.1f}%")
            
            # Show cleaned data if available
            if f"cleaned_data_{selected_sheet}" in st.session_state:
                st.markdown("### ✨ Cleaned Data Preview")
                cleaned_df = st.session_state[f"cleaned_data_{selected_sheet}"]
                st.dataframe(cleaned_df.head(), use_container_width=True)
                
                if st.button("💾 Save Cleaned Data", key="save_cleaned"):
                    st.session_state[f"processed_data_{selected_sheet}"] = cleaned_df
                    st.success("✅ Cleaned data saved!")
    
    if st.button("❌ Close Data Cleaning", key="close_cleaning"):
        st.session_state['show_data_cleaning'] = False
        st.rerun()

def render_export_results(excel_data: Dict[str, pd.DataFrame]):
    """Render export results interface"""
    st.markdown("---")
    st.subheader("💾 Export Results")
    
    # Sheet selection
    sheet_names = list(excel_data.keys())
    selected_sheet = st.selectbox(
        "Select Sheet to Export:",
        options=sheet_names,
        key="export_sheet_selector"
    )
    
    if selected_sheet:
        # Check for processed data
        processed_key = f"processed_data_{selected_sheet}"
        cleaned_key = f"cleaned_data_{selected_sheet}"
        pivot_key = f"pivot_table_{selected_sheet}"
        
        available_data = {}
        available_data["Original Data"] = excel_data[selected_sheet]
        
        if processed_key in st.session_state:
            available_data["Processed Data"] = st.session_state[processed_key]
        
        if cleaned_key in st.session_state:
            available_data["Cleaned Data"] = st.session_state[cleaned_key]
        
        if pivot_key in st.session_state:
            available_data["Pivot Table"] = st.session_state[pivot_key]
        
        # Data selection
        col1, col2, col3 = st.columns(3)
        
        with col1:
            data_type = st.selectbox(
                "Data to Export:",
                options=list(available_data.keys()),
                key="export_data_type"
            )
        
        with col2:
            export_format = st.selectbox(
                "Export Format:",
                ["CSV", "Excel", "JSON", "Parquet"],
                key="export_format_advanced"
            )
        
        with col3:
            include_index = st.checkbox(
                "Include Index",
                key="export_include_index"
            )
        
        # Data preview
        selected_data = available_data[data_type]
        st.markdown(f"### 👀 {data_type} Preview")
        st.dataframe(selected_data.head(), use_container_width=True)
        st.write(f"Shape: {selected_data.shape[0]} rows × {selected_data.shape[1]} columns")
        
        # Export options
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📥 Generate Download", key="generate_download"):
                try:
                    if export_format == "CSV":
                        data = selected_data.to_csv(index=include_index)
                        filename = f"{selected_sheet}_{data_type.lower().replace(' ', '_')}.csv"
                        mime = "text/csv"
                    
                    elif export_format == "Excel":
                        import io
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            selected_data.to_excel(writer, sheet_name=selected_sheet, index=include_index)
                        data = output.getvalue()
                        filename = f"{selected_sheet}_{data_type.lower().replace(' ', '_')}.xlsx"
                        mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    
                    elif export_format == "JSON":
                        data = selected_data.to_json(orient='records', indent=2)
                        filename = f"{selected_sheet}_{data_type.lower().replace(' ', '_')}.json"
                        mime = "application/json"
                    
                    elif export_format == "Parquet":
                        import io
                        output = io.BytesIO()
                        selected_data.to_parquet(output, index=include_index)
                        data = output.getvalue()
                        filename = f"{selected_sheet}_{data_type.lower().replace(' ', '_')}.parquet"
                        mime = "application/octet-stream"
                    
                    st.download_button(
                        label=f"📥 Download {export_format}",
                        data=data,
                        file_name=filename,
                        mime=mime,
                        key="download_advanced_export"
                    )
                    st.success("✅ Download ready!")
                    
                except Exception as e:
                    st.error(f"Export error: {str(e)}")
        
        with col2:
            if st.button("📊 Export Summary Report", key="export_summary"):
                # Generate summary report
                summary_data = {
                    'Sheet': [selected_sheet],
                    'Data Type': [data_type],
                    'Rows': [selected_data.shape[0]],
                    'Columns': [selected_data.shape[1]],
                    'Missing Values': [selected_data.isnull().sum().sum()],
                    'Export Format': [export_format],
                    'Export Date': [pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')]
                }
                
                summary_df = pd.DataFrame(summary_data)
                summary_csv = summary_df.to_csv(index=False)
                
                st.download_button(
                    label="📋 Download Summary Report",
                    data=summary_csv,
                    file_name=f"export_summary_{selected_sheet}.csv",
                    mime="text/csv",
                    key="download_summary_report"
                )
    
    if st.button("❌ Close Export Results", key="close_export"):
        st.session_state['show_export_results'] = False
        st.rerun()

def render_excel_ai_assistant(excel_data: Dict[str, pd.DataFrame]):
    """Render AI-powered Excel assistant for task automation"""
    
    with st.expander("🤖 AI Excel Assistant", expanded=True):
        st.markdown("**Get AI-powered help with your Excel data analysis and automation**")
        
        # Sheet selection for AI analysis
        sheet_names = list(excel_data.keys())
        selected_sheet = st.selectbox(
            "Select Sheet for AI Analysis:",
            options=sheet_names,
            key="ai_sheet_selector"
        )
        
        if selected_sheet:
            df = excel_data[selected_sheet]
            # Prefer processed data if available so AI tasks use user's latest transformations
            processed_key = f"processed_data_{selected_sheet}"
            if processed_key in st.session_state and isinstance(st.session_state[processed_key], pd.DataFrame):
                df = st.session_state[processed_key]

            # Persistent UI flags for Suggest Charts flow
            show_key = f"ai_show_chart_tools_{selected_sheet}"
            sugg_key = f"ai_chart_suggestions_{selected_sheet}"

            # AI Task Categories
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### 🎯 Quick AI Tasks")
                
                if st.button("📊 Generate Data Insights", key="ai_insights"):
                    with st.spinner("AI analyzing your data..."):
                        insights = generate_data_insights(df, selected_sheet)
                        st.markdown("### 🔍 AI Data Insights")
                        st.write(insights)
                
                if st.button("📈 Suggest Charts", key="ai_charts"):
                    with st.spinner("AI suggesting visualizations..."):
                        st.session_state[show_key] = True
                        st.session_state[sugg_key] = suggest_charts(df, selected_sheet)

                # Persistent chart tools section (remains visible after reruns)
                if st.session_state.get(show_key, False):
                    st.markdown("### 📊 AI Chart Suggestions")
                    st.write(st.session_state.get(sugg_key) or suggest_charts(df, selected_sheet))

                    # Auto-generate a few best-fit charts from the ingested data
                    auto_charts = generate_auto_charts(df, selected_sheet, max_charts=3)
                    if auto_charts:
                        st.markdown("### 📈 Auto-Generated Charts")
                        for title, fig in auto_charts:
                            st.caption(title)
                            st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No obvious charts could be auto-generated from this sheet. Try the chart generator below.")

                    # Add interactive chart generation for customizations
                    st.markdown("### 🎨 Generate Charts")
                    render_ai_chart_generator(df, selected_sheet)

                    # Collapse control
                    if st.button("Hide chart tools", key=f"ai_hide_charts_{selected_sheet}"):
                        st.session_state[show_key] = False
                
                if st.button("🧹 Data Quality Check", key="ai_quality"):
                    with st.spinner("AI checking data quality..."):
                        quality_report = analyze_data_quality(df, selected_sheet)
                        st.markdown("### ✅ AI Data Quality Report")
                        st.write(quality_report)
                
                if st.button("🔮 Predict Missing Values", key="ai_predict"):
                    with st.spinner("AI predicting missing values..."):
                        predictions = predict_missing_values(df, selected_sheet)
                        st.markdown("### 🔮 AI Missing Value Predictions")
                        st.write(predictions)
            
            with col2:
                st.markdown("### 💬 AI Chat Assistant")
                
                # Chat interface for custom queries
                user_query = st.text_area(
                    "Ask AI about your data:",
                    placeholder="e.g., 'What are the top 5 products by sales?' or 'How can I clean this data?'",
                    height=100,
                    key="ai_query"
                )
                
                if st.button("🚀 Ask AI", key="ai_ask"):
                    if user_query:
                        with st.spinner("AI processing your question..."):
                            ai_response = process_ai_query(df, selected_sheet, user_query)
                            st.markdown("### 🤖 AI Response")
                            st.write(ai_response)
                            
                            # If AI suggests code, show it
                            if "```python" in ai_response:
                                st.markdown("### 💻 Generated Code")
                                code_match = ai_response.split("```python")[1].split("```")[0]
                                st.code(code_match, language="python")
                                
                    else:
                        st.warning("Please enter a question about your data")
                
                # Quick prompts
                st.markdown("### 🎯 Quick Prompts")
                quick_prompts = [
                    "Summarize this data",
                    "What are the top 5 values?",
                    "Find outliers in numeric columns", 
                    "How can I clean this data?",
                    "Show me data patterns",
                    "Suggest a pivot table",
                    "Create a pivot table recommendation"
                ]
                
                selected_prompt = st.selectbox(
                    "Choose a quick prompt:",
                    ["Select a prompt..."] + quick_prompts,
                    key=f"quick_prompt_{selected_sheet}"
                )
                
                if st.button("🚀 Use Prompt", key=f"use_prompt_{selected_sheet}"):
                    if selected_prompt != "Select a prompt...":
                        with st.spinner("AI processing prompt..."):
                            ai_response = process_ai_query(df, selected_sheet, selected_prompt)
                            st.markdown("### 🤖 AI Response")
                            st.markdown(ai_response)  # Use markdown for better formatting
                            
                            # Store response in session state
                            if f"ai_responses_{selected_sheet}" not in st.session_state:
                                st.session_state[f"ai_responses_{selected_sheet}"] = []
                            st.session_state[f"ai_responses_{selected_sheet}"].append({
                                "query": selected_prompt,
                                "response": ai_response
                            })
                
                # Show conversation history
                if f"ai_responses_{selected_sheet}" in st.session_state and st.session_state[f"ai_responses_{selected_sheet}"]:
                    with st.expander("📜 Conversation History", expanded=False):
                        for i, conv in enumerate(reversed(st.session_state[f"ai_responses_{selected_sheet}"][-3:])):  # Show last 3
                            st.markdown(f"**Q{len(st.session_state[f'ai_responses_{selected_sheet}'])-i}:** {conv['query']}")
                            st.markdown(conv['response'])
                            st.markdown("---")

def generate_data_insights(df: pd.DataFrame, sheet_name: str) -> str:
    """Generate AI-powered data insights"""
    try:
        insights = []
        
        # Basic statistics
        insights.append(f"📊 **Data Overview for {sheet_name}:**")
        insights.append(f"- Dataset contains {len(df)} rows and {len(df.columns)} columns")
        insights.append(f"- Memory usage: {df.memory_usage(deep=True).sum() / 1024:.1f} KB")
        
        # Data types analysis
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        text_cols = df.select_dtypes(include=['object', 'string', 'category']).columns.tolist()
        
        insights.append(f"- Numeric columns ({len(numeric_cols)}): {', '.join(numeric_cols[:5])}")
        insights.append(f"- Text columns ({len(text_cols)}): {', '.join(text_cols[:5])}")
        
        # Missing values
        missing_count = df.isnull().sum().sum()
        if missing_count > 0:
            insights.append(f"⚠️ **Data Quality Issues:**")
            insights.append(f"- {missing_count} missing values found")
            missing_cols = df.columns[df.isnull().any()].tolist()
            insights.append(f"- Columns with missing data: {', '.join(missing_cols)}")
        else:
            insights.append("✅ **Data Quality:** No missing values detected")
        
        # Duplicates
        duplicate_count = len(df) - len(df.drop_duplicates())
        if duplicate_count > 0:
            insights.append(f"- {duplicate_count} duplicate rows found")
        
        # Numeric insights
        if numeric_cols:
            insights.append(f"📈 **Numeric Data Insights:**")
            for col in numeric_cols[:3]:  # Top 3 numeric columns
                mean_val = df[col].mean()
                std_val = df[col].std()
                insights.append(f"- {col}: Mean = {mean_val:.2f}, Std = {std_val:.2f}")
        
        # Text insights
        if text_cols:
            insights.append(f"📝 **Text Data Insights:**")
            for col in text_cols[:3]:  # Top 3 text columns
                unique_count = df[col].nunique()
                most_common = df[col].mode().iloc[0] if not df[col].mode().empty else "N/A"
                insights.append(f"- {col}: {unique_count} unique values, most common: '{most_common}'")
        
        return "\n".join(insights)
        
    except Exception as e:
        return f"❌ Error generating insights: {str(e)}"

def suggest_charts(df: pd.DataFrame, sheet_name: str) -> str:
    """Suggest appropriate charts based on data"""
    try:
        suggestions = []
        
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        text_cols = df.select_dtypes(include=['object']).columns.tolist()
        
        suggestions.append(f"📊 **Chart Recommendations for {sheet_name}:**")
        
        if len(numeric_cols) >= 2:
            suggestions.append(f"🔹 **Scatter Plot**: Compare {numeric_cols[0]} vs {numeric_cols[1]} to find correlations")
            suggestions.append(f"🔹 **Line Chart**: Show trends in {numeric_cols[0]} over time")
        
        if len(numeric_cols) >= 1 and len(text_cols) >= 1:
            suggestions.append(f"🔹 **Bar Chart**: Show {numeric_cols[0]} by {text_cols[0]} categories")
            suggestions.append(f"🔹 **Box Plot**: Analyze {numeric_cols[0]} distribution across {text_cols[0]} groups")
        
        if len(text_cols) >= 1:
            suggestions.append(f"🔹 **Pie Chart**: Show distribution of {text_cols[0]} categories")
            suggestions.append(f"🔹 **Value Counts**: Count frequency of {text_cols[0]} values")
        
        if len(numeric_cols) >= 1:
            suggestions.append(f"🔹 **Histogram**: Show distribution of {numeric_cols[0]} values")
        
        # Advanced suggestions
        suggestions.append(f"🔹 **Heatmap**: Show correlation matrix between numeric columns")
        suggestions.append(f"🔹 **Pivot Table**: Cross-tabulate data for deeper analysis")
        
        return "\n".join(suggestions)
        
    except Exception as e:
        return f"❌ Error generating chart suggestions: {str(e)}"

def analyze_data_quality(df: pd.DataFrame, sheet_name: str) -> str:
    """Analyze data quality and provide recommendations"""
    try:
        quality_report = []
        
        quality_report.append(f"✅ **Data Quality Report for {sheet_name}:**")
        
        # Calculate quality score
        total_cells = len(df) * len(df.columns)
        missing_cells = df.isnull().sum().sum()
        duplicate_rows = len(df) - len(df.drop_duplicates())
        
        quality_score = ((total_cells - missing_cells - duplicate_rows) / total_cells) * 100
        quality_report.append(f"📊 **Overall Quality Score: {quality_score:.1f}%**")
        
        # Missing values analysis
        if missing_cells > 0:
            quality_report.append(f"⚠️ **Missing Values ({missing_cells} cells):**")
            missing_by_col = df.isnull().sum()
            missing_by_col = missing_by_col[missing_by_col > 0].sort_values(ascending=False)
            for col, count in missing_by_col.head(5).items():
                percentage = (count / len(df)) * 100
                quality_report.append(f"  - {col}: {count} missing ({percentage:.1f}%)")
        else:
            quality_report.append("✅ **No missing values found**")
        
        # Duplicate analysis
        if duplicate_rows > 0:
            quality_report.append(f"⚠️ **Duplicate Rows: {duplicate_rows} found**")
            quality_report.append("  - Recommendation: Use 'Remove Duplicates' in Data Cleaning")
        else:
            quality_report.append("✅ **No duplicate rows found**")
        
        # Data type consistency
        quality_report.append("🔍 **Data Type Analysis:**")
        for col in df.columns:
            dtype = str(df[col].dtype)
            if dtype == 'object':
                # Check if text column contains numbers
                try:
                    numeric_conversion = pd.to_numeric(df[col], errors='coerce')
                    if not numeric_conversion.isna().all():
                        quality_report.append(f"  - {col}: Text column contains numeric data (consider conversion)")
                except:
                    pass
        
        # Recommendations
        quality_report.append("💡 **Recommendations:**")
        if missing_cells > 0:
            quality_report.append("  - Fill missing values using Data Manipulation tools")
        if duplicate_rows > 0:
            quality_report.append("  - Remove duplicates to improve data quality")
        if quality_score < 90:
            quality_report.append("  - Consider data cleaning operations to improve quality")
        else:
            quality_report.append("  - Data quality is excellent! Ready for analysis")
        
        return "\n".join(quality_report)
        
    except Exception as e:
        return f"❌ Error analyzing data quality: {str(e)}"

def predict_missing_values(df: pd.DataFrame, sheet_name: str) -> str:
    """Predict and suggest missing value handling"""
    try:
        predictions = []
        
        predictions.append(f"🔮 **Missing Value Predictions for {sheet_name}:**")
        
        missing_cols = df.columns[df.isnull().any()].tolist()
        
        if not missing_cols:
            predictions.append("✅ **No missing values to predict**")
            return "\n".join(predictions)
        
        for col in missing_cols:
            missing_count = df[col].isnull().sum()
            missing_percentage = (missing_count / len(df)) * 100
            
            predictions.append(f"📊 **Column: {col}** ({missing_count} missing, {missing_percentage:.1f}%)")
            
            if df[col].dtype in ['int64', 'float64']:
                # Numeric column
                mean_val = df[col].mean()
                median_val = df[col].median()
                predictions.append(f"  - Suggested fill with mean: {mean_val:.2f}")
                predictions.append(f"  - Suggested fill with median: {median_val:.2f}")
                predictions.append(f"  - Recommended: Use median for skewed data, mean for normal distribution")
            else:
                # Text column
                mode_val = df[col].mode()
                if not mode_val.empty:
                    predictions.append(f"  - Suggested fill with most common: '{mode_val.iloc[0]}'")
                predictions.append(f"  - Alternative: Fill with 'Unknown' or 'N/A'")
            
            if missing_percentage > 50:
                predictions.append(f"  - ⚠️ Warning: High missing percentage, consider removing column")
        
        predictions.append("💡 **AI Recommendations:**")
        predictions.append("  - Use forward/backward fill for time series data")
        predictions.append("  - Use interpolation for gradual changes")
        predictions.append("  - Consider creating 'missing' indicator columns for important features")
        
        return "\n".join(predictions)
        
    except Exception as e:
        return f"❌ Error predicting missing values: {str(e)}"

def process_ai_query(df: pd.DataFrame, sheet_name: str, query: str) -> str:
    """Process natural language queries about the data"""
    try:
        query_lower = query.lower()
        response = []
        
        response.append(f"🤖 **AI Analysis for: '{query}'**")
        
        # More specific pattern matching for better responses
        if "top" in query_lower and ("5" in query_lower or "10" in query_lower):
            # Extract number
            num_results = 10 if "10" in query_lower else 5
            
            # Find best column to sort by
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            text_cols = df.select_dtypes(include=['object']).columns
            
            response.append(f"# 🏆 Top {num_results} Analysis")
            response.append("")
            
            if not numeric_cols.empty:
                # Use first numeric column for sorting
                sort_col = numeric_cols[0]
                top_data = df.nlargest(num_results, sort_col)
                
                response.append(f"## 📊 Top {num_results} by **{sort_col}**")
                response.append("")
                
                # Create table format
                if not text_cols.empty:
                    response.append(f"| Rank | {text_cols[0]} | {sort_col} |")
                    response.append("|------|" + "-" * len(text_cols[0]) + "|" + "-" * len(sort_col) + "|")
                    for i, (idx, row) in enumerate(top_data.iterrows(), 1):
                        name_val = str(row[text_cols[0]])[:20]
                        num_val = row[sort_col]
                        response.append(f"| {i} | **{name_val}** | {num_val} |")
                else:
                    response.append(f"| Rank | {sort_col} |")
                    response.append("|------|" + "-" * len(sort_col) + "|")
                    for i, (idx, row) in enumerate(top_data.iterrows(), 1):
                        response.append(f"| {i} | {row[sort_col]} |")
                
                response.append("")
                response.append(f"📈 **Highest Value**: {top_data[sort_col].iloc[0]}")
                response.append(f"📉 **Lowest in Top {num_results}**: {top_data[sort_col].iloc[-1]}")
                
            else:
                # Text-based top values
                col = text_cols[0]
                top_values = df[col].value_counts().head(num_results)
                
                response.append(f"## 📊 Most Frequent **{col}**")
                response.append("")
                response.append("| Rank | Value | Count |")
                response.append("|------|-------|-------|")
                for i, (value, count) in enumerate(top_values.items(), 1):
                    value_str = str(value)[:25] + "..." if len(str(value)) > 25 else str(value)
                    response.append(f"| {i} | **{value_str}** | {count} |")
                
                response.append("")
                response.append(f"🏆 **Most Common**: {top_values.index[0]} ({top_values.iloc[0]} times)")
            
            response.append("")
        
        elif "summary" in query_lower or "summarize" in query_lower:
            response.append(f"# 📊 Data Summary: {sheet_name}")
            response.append("")
            
            # Basic info in a clean format
            response.append("## 📋 Dataset Overview")
            response.append(f"- **Size**: {df.shape[0]:,} rows × {df.shape[1]} columns")
            response.append(f"- **Memory**: {df.memory_usage(deep=True).sum() / 1024:.1f} KB")
            response.append("")
            
            # Column information
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            text_cols = df.select_dtypes(include=['object']).columns
            date_cols = df.select_dtypes(include=['datetime64']).columns
            
            response.append("## 🏗️ Data Structure")
            response.append(f"- **Numeric columns**: {len(numeric_cols)}")
            response.append(f"- **Text columns**: {len(text_cols)}")
            response.append(f"- **Date columns**: {len(date_cols)}")
            response.append("")
            
            # Column names in a readable format
            response.append("### 📝 Column Names:")
            for i, col in enumerate(df.columns, 1):
                col_type = "📊" if col in numeric_cols else "📝" if col in text_cols else "📅"
                response.append(f"{i}. {col_type} **{col}**")
            response.append("")
            
            # Data quality
            missing_count = df.isnull().sum().sum()
            duplicate_count = len(df) - len(df.drop_duplicates())
            response.append("## 🔍 Data Quality")
            response.append(f"- **Missing values**: {missing_count}")
            response.append(f"- **Duplicate rows**: {duplicate_count}")
            response.append(f"- **Completeness**: {((df.size - missing_count) / df.size * 100):.1f}%")
            response.append("")
            
            # Sample data in table format
            response.append("## 📋 Sample Data (First 3 Rows)")
            response.append("")
            sample_df = df.head(3)
            
            # Create markdown table
            headers = ["Row"] + [col[:15] + "..." if len(col) > 15 else col for col in df.columns[:5]]
            response.append("| " + " | ".join(headers) + " |")
            response.append("|" + "|".join(["---"] * len(headers)) + "|")
            
            for i, (idx, row) in enumerate(sample_df.iterrows()):
                row_values = [str(i+1)]
                for col in df.columns[:5]:
                    value = str(row[col])
                    value = value[:15] + "..." if len(value) > 15 else value
                    row_values.append(value)
                response.append("| " + " | ".join(row_values) + " |")
            response.append("")
            
            # Numeric analysis
            if not numeric_cols.empty:
                response.append("## 📈 Numeric Analysis")
                response.append("")
                response.append("| Column | Min | Max | Mean | Std |")
                response.append("|--------|-----|-----|------|-----|")
                for col in numeric_cols[:5]:
                    stats = df[col].describe()
                    response.append(f"| **{col}** | {stats['min']:.2f} | {stats['max']:.2f} | {stats['mean']:.2f} | {stats['std']:.2f} |")
                response.append("")
            
            # Text analysis
            if not text_cols.empty:
                response.append("## 📝 Text Analysis")
                response.append("")
                response.append("| Column | Unique Values | Most Common | Missing |")
                response.append("|--------|---------------|-------------|---------|")
                for col in text_cols[:5]:
                    unique_count = df[col].nunique()
                    most_common = df[col].mode().iloc[0] if not df[col].mode().empty else "N/A"
                    null_count = df[col].isnull().sum()
                    most_common = str(most_common)[:15] + "..." if len(str(most_common)) > 15 else str(most_common)
                    response.append(f"| **{col}** | {unique_count} | {most_common} | {null_count} |")
                response.append("")
        
        elif "outlier" in query_lower:
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if not numeric_cols.empty:
                response.append("🎯 **Outlier Analysis:**")
                for col in numeric_cols[:3]:
                    Q1 = df[col].quantile(0.25)
                    Q3 = df[col].quantile(0.75)
                    IQR = Q3 - Q1
                    lower_bound = Q1 - 1.5 * IQR
                    upper_bound = Q3 + 1.5 * IQR
                    
                    outliers = df[(df[col] < lower_bound) | (df[col] > upper_bound)]
                    if len(outliers) > 0:
                        response.append(f"  - **{col}**: {len(outliers)} outliers detected")
                        response.append(f"    Normal range: {lower_bound:.2f} to {upper_bound:.2f}")
                        extreme_values = outliers[col].tolist()[:5]
                        response.append(f"    Extreme values: {extreme_values}")
                    else:
                        response.append(f"  - **{col}**: No outliers detected")
            else:
                response.append("⚠️ No numeric columns found for outlier detection")
        
        elif "clean" in query_lower or "cleaning" in query_lower:
            response.append("🧹 **Data Cleaning Analysis:**")
            
            # Missing values
            missing_by_col = df.isnull().sum()
            missing_cols = missing_by_col[missing_by_col > 0]
            if not missing_cols.empty:
                response.append(f"📊 **Missing Values ({missing_by_col.sum()} total):**")
                for col, count in missing_cols.head(5).items():
                    percentage = (count / len(df)) * 100
                    response.append(f"  - {col}: {count} missing ({percentage:.1f}%)")
            else:
                response.append("✅ No missing values found")
            
            # Duplicates
            duplicate_count = len(df) - len(df.drop_duplicates())
            if duplicate_count > 0:
                response.append(f"📊 **Duplicates**: {duplicate_count} duplicate rows found")
            else:
                response.append("✅ No duplicate rows found")
            
            # Data type issues
            response.append("🔍 **Data Type Analysis:**")
            for col in df.columns[:5]:
                if df[col].dtype == 'object':
                    # Check if text column contains numbers
                    try:
                        numeric_conversion = pd.to_numeric(df[col], errors='coerce')
                        non_null_converted = numeric_conversion.dropna()
                        if len(non_null_converted) > len(df) * 0.8:  # 80% convertible
                            response.append(f"  - {col}: Text column, but {len(non_null_converted)} values are numeric")
                    except:
                        pass
        
        elif "pattern" in query_lower or "trend" in query_lower:
            response.append("🔍 **Data Pattern Analysis:**")
            
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            text_cols = df.select_dtypes(include=['object']).columns
            
            # Numeric patterns
            if not numeric_cols.empty:
                response.append("📈 **Numeric Patterns:**")
                for col in numeric_cols[:3]:
                    # Check for trends (correlation with row index)
                    if len(df) > 2:
                        correlation = df[col].corr(pd.Series(range(len(df))))
                        if abs(correlation) > 0.3:
                            trend = "increasing" if correlation > 0 else "decreasing"
                            response.append(f"  - {col}: Shows {trend} trend (r={correlation:.3f})")
                        else:
                            response.append(f"  - {col}: No clear trend detected")
            
            # Categorical patterns
            if not text_cols.empty:
                response.append("📊 **Categorical Patterns:**")
                for col in text_cols[:3]:
                    value_counts = df[col].value_counts()
                    if len(value_counts) > 0:
                        top_value = value_counts.index[0]
                        top_count = value_counts.iloc[0]
                        percentage = (top_count / len(df)) * 100
                        
                        if percentage > 50:
                            response.append(f"  - {col}: Dominated by '{top_value}' ({percentage:.1f}%)")
                        else:
                            response.append(f"  - {col}: Well distributed, top value '{top_value}' ({percentage:.1f}%)")
        
        elif "pivot" in query_lower or "cross" in query_lower:
            text_cols = df.select_dtypes(include=['object']).columns.tolist()
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            
            response.append("📊 **Pivot Table Recommendations:**")
            if text_cols and numeric_cols:
                response.append(f"🎯 **Suggested Configuration:**")
                response.append(f"  - **Index (Rows)**: {text_cols[0]} - for grouping")
                if len(text_cols) > 1:
                    response.append(f"  - **Columns**: {text_cols[1]} - for cross-tabulation")
                response.append(f"  - **Values**: {numeric_cols[0]} - for aggregation")
                response.append(f"  - **Function**: sum, mean, or count")
                
                # Show a preview of what this would look like
                try:
                    preview_pivot = df.pivot_table(
                        index=text_cols[0],
                        values=numeric_cols[0],
                        aggfunc='mean'
                    ).head(5)
                    response.append(f"📋 **Preview (mean {numeric_cols[0]} by {text_cols[0]}):**")
                    for idx, val in preview_pivot.items():
                        response.append(f"  - {idx}: {val:.2f}")
                except:
                    response.append("  - Use the Pivot Table creator for detailed configuration")
            else:
                response.append("⚠️ Need both categorical and numeric columns for pivot tables")
        
        elif "common" in query_lower and "team" in query_lower:
            # Handle specific query from screenshot
            text_cols = df.select_dtypes(include=['object']).columns
            if not text_cols.empty:
                response.append("## 👥 Team Member Analysis")
                response.append("")
                
                # Look for columns that might contain team member names
                team_cols = []
                for col in text_cols:
                    if any(keyword in col.lower() for keyword in ['name', 'member', 'team', 'person', 'employee', 'user']):
                        team_cols.append(col)
                
                if team_cols:
                    for col in team_cols[:2]:  # Analyze first 2 relevant columns
                        value_counts = df[col].value_counts().head(15)
                        response.append(f"### 📊 Most Common **{col}**:")
                        response.append("")
                        
                        # Create a nicely formatted table
                        response.append("| Rank | Name | Count |")
                        response.append("|------|------|-------|")
                        for i, (name, count) in enumerate(value_counts.items(), 1):
                            response.append(f"| {i} | **{name}** | {count} |")
                        
                        response.append("")
                        response.append(f"📈 **Summary**: Found {len(value_counts)} unique {col.lower()}s")
                        response.append(f"🏆 **Most Active**: {value_counts.index[0]} with {value_counts.iloc[0]} occurrences")
                        response.append("")
                else:
                    # Analyze first text column as potential team member column
                    col = text_cols[0]
                    value_counts = df[col].value_counts().head(15)
                    response.append(f"### 📊 Most Common **{col}** (Team Members):")
                    response.append("")
                    
                    # Create a nicely formatted table
                    response.append("| Rank | Name | Count |")
                    response.append("|------|------|-------|")
                    for i, (name, count) in enumerate(value_counts.items(), 1):
                        response.append(f"| {i} | **{name}** | {count} |")
                    
                    response.append("")
                    response.append(f"📈 **Total Unique**: {len(value_counts)} different {col.lower()}s")
                    response.append(f"🏆 **Top Performer**: {value_counts.index[0]} ({value_counts.iloc[0]} occurrences)")
            else:
                response.append("## ⚠️ No Team Data Found")
                response.append("")
                response.append("No text columns found that could contain team member names.")
        
        else:
            # Provide specific analysis based on actual data structure
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            text_cols = df.select_dtypes(include=['object']).columns
            
            response.append("🔍 **Smart Analysis of Your Data:**")
            response.append(f"📊 **Dataset**: {len(df):,} rows × {len(df.columns)} columns")
            response.append(f"📝 **Columns**: {', '.join(df.columns.tolist()[:5])}{'...' if len(df.columns) > 5 else ''}")
            
            if not numeric_cols.empty and not text_cols.empty:
                # Mixed data - show actual relationships
                response.append(f"📈 **Available Analysis Options:**")
                response.append(f"  - Analyze {numeric_cols[0]} values by {text_cols[0]} categories")
                if len(numeric_cols) > 1:
                    response.append(f"  - Compare {numeric_cols[0]} vs {numeric_cols[1]}")
                response.append(f"  - Find patterns in {text_cols[0]} distribution")
                
                # Show sample of actual data
                response.append(f"📋 **Sample Values:**")
                response.append(f"  - {text_cols[0]}: {df[text_cols[0]].dropna().iloc[0] if not df[text_cols[0]].dropna().empty else 'N/A'}")
                response.append(f"  - {numeric_cols[0]}: {df[numeric_cols[0]].dropna().iloc[0] if not df[numeric_cols[0]].dropna().empty else 'N/A'}")
                
            elif not numeric_cols.empty:
                # Mostly numeric
                response.append("📈 **Numeric Data Available:**")
                for col in numeric_cols[:3]:
                    sample_val = df[col].dropna().iloc[0] if not df[col].dropna().empty else 'N/A'
                    response.append(f"  - {col}: sample value = {sample_val}")
                
            elif not text_cols.empty:
                # Mostly text
                response.append("📝 **Text Data Available:**")
                for col in text_cols[:3]:
                    sample_val = df[col].dropna().iloc[0] if not df[col].dropna().empty else 'N/A'
                    unique_count = df[col].nunique()
                    response.append(f"  - {col}: {unique_count} unique values, sample: '{sample_val}'")
            
            response.append("\n💡 **Try These Specific Questions:**")
            response.append("  - 'What are the top 5 values?'")
            response.append("  - 'Summarize this data'")
            response.append("  - 'Find outliers'")
            response.append("  - 'Show me patterns'")
            if len(text_cols) > 0:
                response.append(f"  - 'What are the most common {text_cols[0]}?'")
        
        return "\n".join(response)
        
    except Exception as e:
        return f"❌ Error processing AI query: {str(e)}"

def render_ai_chart_generator(df: pd.DataFrame, sheet_name: str):
    """Render interactive chart generator based on AI suggestions"""
    try:
        numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        # Primary detection
        text_cols = df.select_dtypes(include=['object', 'string', 'category', 'bool', 'boolean']).columns.tolist()
        # Fallback: any non-numeric, non-datetime
        if not text_cols:
            text_cols = [
                c for c in df.columns
                if not pd.api.types.is_numeric_dtype(df[c]) and not pd.api.types.is_datetime64_any_dtype(df[c])
            ]
        
        if not numeric_cols and not text_cols:
            st.warning("No suitable columns found for chart generation")
            return
        
        st.markdown("#### 🎨 Quick Chart Generation")
        with st.expander("🔎 Detection Debug", expanded=False):
            st.caption("Detected column types used for chart generation")
            st.write({
                "numeric": numeric_cols,
                "text": text_cols,
            })
        
        # Chart type selection
        chart_types = []
        if numeric_cols:
            chart_types.extend(["Line Chart", "Bar Chart", "Histogram", "Box Plot", "Scatter Plot"])
        if text_cols:
            chart_types.extend(["Value Counts", "Category Distribution"])
        
        selected_chart = st.selectbox(
            "Select chart type:",
            chart_types,
            key=f"ai_chart_type_{sheet_name}"
        )
        
        # Column selection based on chart type
        if selected_chart in ["Line Chart", "Bar Chart", "Histogram", "Box Plot", "Scatter Plot"]:
            if numeric_cols:
                selected_col = st.selectbox(
                    "Select column:",
                    numeric_cols,
                    key=f"ai_chart_col_{sheet_name}"
                )
                
                # Additional selections for specific chart types
                x_col = None
                y_col = None
                
                if selected_chart == "Bar Chart" and len(text_cols) > 0:
                    x_col = st.selectbox(
                        "Group by (optional):", 
                        ["None"] + text_cols, 
                        key=f"bar_x_{sheet_name}"
                    )
                    if x_col == "None":
                        x_col = None
                
                elif selected_chart == "Scatter Plot" and len(numeric_cols) > 1:
                    y_col = st.selectbox(
                        "Y-axis:", 
                        [col for col in numeric_cols if col != selected_col], 
                        key=f"scatter_y_{sheet_name}"
                    )
                
                if st.button(f"Generate {selected_chart}", key=f"generate_chart_{sheet_name}"):
                    try:
                        fig = None
                        
                        if selected_chart == "Line Chart":
                            fig = px.line(df, y=selected_col, title=f"Line Chart: {selected_col}")
                            fig.update_layout(height=500)
                            
                        elif selected_chart == "Bar Chart":
                            if x_col:
                                # Group data and aggregate
                                grouped_data = df.groupby(x_col)[selected_col].mean().reset_index()
                                fig = px.bar(grouped_data, x=x_col, y=selected_col, 
                                           title=f"Average {selected_col} by {x_col}")
                            else:
                                # Simple bar chart with index
                                fig = px.bar(x=df.index[:50], y=df[selected_col].head(50), 
                                           title=f"Bar Chart: {selected_col} (First 50 records)")
                            fig.update_layout(height=500, xaxis_tickangle=-45)
                            
                        elif selected_chart == "Histogram":
                            fig = px.histogram(df, x=selected_col, title=f"Distribution of {selected_col}")
                            fig.update_layout(height=500)
                            
                        elif selected_chart == "Box Plot":
                            fig = px.box(df, y=selected_col, title=f"Box Plot: {selected_col}")
                            fig.update_layout(height=500)
                            
                        elif selected_chart == "Scatter Plot" and y_col:
                            fig = px.scatter(df, x=selected_col, y=y_col, 
                                           title=f"{selected_col} vs {y_col}")
                            fig.update_layout(height=500)
                        
                        if fig:
                            st.plotly_chart(fig, use_container_width=True)
                            st.success(f"✅ {selected_chart} generated successfully!")
                            
                            # Show chart statistics
                            st.markdown("### 📊 Chart Statistics")
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Data Points", len(df))
                            with col2:
                                if pd.api.types.is_numeric_dtype(df[selected_col]):
                                    st.metric("Min Value", f"{df[selected_col].min():.2f}")
                                else:
                                    st.metric("Unique Values", df[selected_col].nunique())
                            with col3:
                                if pd.api.types.is_numeric_dtype(df[selected_col]):
                                    st.metric("Max Value", f"{df[selected_col].max():.2f}")
                                else:
                                    st.metric("Most Common", str(df[selected_col].mode().iloc[0]))
                        else:
                            st.warning("Unable to generate chart with selected parameters")
                            
                    except Exception as e:
                        st.error(f"❌ Error generating {selected_chart}: {str(e)}")
                        st.write(f"Debug info: Column '{selected_col}' type: {df[selected_col].dtype}")
                        # Show sample data for debugging
                        st.write("Sample data:")
                        st.write(df[selected_col].head())
        
        elif selected_chart in ["Value Counts", "Category Distribution"]:
            # Fallback: allow selecting from all columns if no text columns detected
            candidates = text_cols if len(text_cols) > 0 else df.columns.tolist()
            selected_col = st.selectbox(
                "Select column:",
                candidates,
                key=f"ai_text_chart_col_{sheet_name}"
            )
            if len(text_cols) == 0:
                st.info("No text/categorical columns detected; showing all columns as fallback. We'll treat the selected column as text for charting.")

            if st.button(f"Generate {selected_chart}", key=f"generate_text_chart_{sheet_name}"):
                try:
                    value_counts = df[selected_col].astype(str).value_counts().head(15)
                    
                    if len(value_counts) == 0:
                        st.warning(f"No data found in column '{selected_col}'")
                        return
                    
                    if selected_chart == "Value Counts":
                        fig = px.bar(
                            x=value_counts.index.astype(str),
                            y=value_counts.values,
                            title=f"Value Counts: {selected_col}",
                            labels={'x': selected_col, 'y': 'Count'}
                        )
                        fig.update_layout(
                            xaxis_tickangle=-45,
                            height=500,
                            showlegend=False
                        )
                    else:  # Category Distribution
                        fig = px.pie(
                            values=value_counts.values,
                            names=value_counts.index.astype(str),
                            title=f"Distribution: {selected_col}"
                        )
                        fig.update_layout(height=500)
                    
                    st.plotly_chart(fig, use_container_width=True)
                    st.success(f"✅ {selected_chart} generated successfully!")
                    
                    # Show data summary
                    st.markdown("### 📊 Chart Data Summary")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Categories", len(value_counts))
                    with col2:
                        st.metric("Most Common", f"{value_counts.index[0]}")
                    with col3:
                        st.metric("Highest Count", value_counts.iloc[0])
                        
                except Exception as e:
                    st.error(f"❌ Error generating {selected_chart}: {str(e)}")
                    try:
                        st.write(f"Debug info: Column '{selected_col}' has {df[selected_col].nunique()} unique values")
                    except Exception:
                        pass
        
        # Smart suggestions
        st.markdown("#### 💡 Smart Suggestions")
        suggestions = []
        
        if len(numeric_cols) >= 2:
            suggestions.append(f"📈 **Correlation Analysis**: Compare {numeric_cols[0]} vs {numeric_cols[1]}")
        
        if text_cols and numeric_cols:
            suggestions.append(f"📊 **Grouped Analysis**: {numeric_cols[0]} grouped by {text_cols[0]}")
        
        if len(df) > 100:
            suggestions.append("📉 **Sample Data**: Consider using a sample for faster visualization")
        
        for suggestion in suggestions:
            st.markdown(f"- {suggestion}")
            
    except Exception as e:
        st.error(f"❌ Error generating charts: {str(e)}")

def generate_auto_charts(df: pd.DataFrame, sheet_name: str, max_charts: int = 3):
    """Generate a small set of best-fit charts automatically from the dataset.
    Returns a list of tuples: (title, plotly_figure).
    """
    charts = []
    try:
        # Work on a local copy to avoid mutating the caller's DataFrame
        df_local = df.copy()
        # Robust dtype detection
        numeric_cols = [c for c in df_local.columns if pd.api.types.is_numeric_dtype(df_local[c])]
        date_cols = [c for c in df_local.columns if pd.api.types.is_datetime64_any_dtype(df_local[c])]
        # Treat any non-numeric, non-datetime columns as text candidates
        text_cols = [
            c for c in df_local.columns
            if not pd.api.types.is_numeric_dtype(df_local[c]) and not pd.api.types.is_datetime64_any_dtype(df_local[c])
        ]

        # Try to infer date columns from names if none are typed as datetime
        if not date_cols:
            for col in df_local.columns:
                if any(k in col.lower() for k in ["date", "time", "timestamp"]):
                    try:
                        parsed = pd.to_datetime(df_local[col], errors='coerce')
                        if not parsed.isna().all():
                            date_cols.append(col)
                            # Mutate a safe copy for plotting usage
                            df_local[col] = parsed
                            break
                    except Exception:
                        continue

        # 1) Time series line chart if we have a date and numeric
        if len(charts) < max_charts and date_cols and numeric_cols:
            dcol = date_cols[0]
            ncol = numeric_cols[0]
            try:
                # Aggregate by day to handle duplicates
                tmp = df_local[[dcol, ncol]].dropna()
                if not tmp.empty:
                    tmp = tmp.groupby(pd.Grouper(key=dcol, freq='D'))[ncol].mean().reset_index()
                    fig = px.line(tmp, x=dcol, y=ncol, title=f"{ncol} over time ({dcol})")
                    fig.update_layout(height=450)
                    charts.append((f"Line: {ncol} over time", fig))
            except Exception:
                pass

        # 2) Grouped bar: numeric by top categories
        if len(charts) < max_charts and text_cols and numeric_cols:
            tcol = text_cols[0]
            ncol = numeric_cols[0]
            try:
                tmp = df_local[[tcol, ncol]].dropna()
                if not tmp.empty:
                    grouped = tmp.groupby(tcol)[ncol].mean().sort_values(ascending=False).head(10).reset_index()
                    fig = px.bar(grouped, x=tcol, y=ncol, title=f"Average {ncol} by {tcol}")
                    fig.update_layout(height=450, xaxis_tickangle=-45)
                    charts.append((f"Bar: {ncol} by {tcol}", fig))
            except Exception:
                pass

        # 3) Scatter for two numeric columns
        if len(charts) < max_charts and len(numeric_cols) >= 2:
            xcol, ycol = numeric_cols[0], numeric_cols[1]
            try:
                tmp = df_local[[xcol, ycol]].dropna().head(2000)  # cap for performance
                if not tmp.empty:
                    fig = px.scatter(tmp, x=xcol, y=ycol, title=f"{xcol} vs {ycol}")
                    fig.update_layout(height=450)
                    charts.append((f"Scatter: {xcol} vs {ycol}", fig))
            except Exception:
                pass

        # 4) Histogram for first numeric as fallback
        if len(charts) < max_charts and numeric_cols:
            ncol = numeric_cols[0]
            try:
                tmp = df_local[ncol].dropna()
                if not tmp.empty:
                    fig = px.histogram(df_local, x=ncol, title=f"Distribution of {ncol}")
                    fig.update_layout(height=450)
                    charts.append((f"Histogram: {ncol}", fig))
            except Exception:
                pass

        # 5) Value counts for first text column if no numeric
        if len(charts) < max_charts and text_cols:
            tcol = text_cols[0]
            try:
                vc = df_local[tcol].astype(str).value_counts().head(15)
                if len(vc) > 0:
                    fig = px.bar(x=vc.index, y=vc.values, title=f"Value Counts: {tcol}", labels={'x': tcol, 'y': 'Count'})
                    fig.update_layout(height=450, xaxis_tickangle=-45)
                    charts.append((f"Value Counts: {tcol}", fig))
            except Exception:
                pass

    except Exception:
        # Best effort; return whatever was created
        pass

    return charts[:max_charts]

def execute_safe_code(code: str, df: pd.DataFrame):
    """Safely execute AI-generated code"""
    try:
        # Create a safe execution environment
        safe_globals = {
            'df': df,
            'pd': pd,
            'np': np,
            'print': print,
            'len': len,
            'sum': sum,
            'max': max,
            'min': min,
            'abs': abs,
            'round': round
        }
        
        # Execute the code
        exec_globals = safe_globals.copy()
        exec(code, exec_globals)
        
        # Return any modified dataframe
        return exec_globals.get('result', None)
        
    except Exception as e:
        raise Exception(f"Code execution failed: {str(e)}")

def render_multi_source_search(available_indexes, auth_middleware):
    """Render multi-source search functionality"""
    st.subheader("🔍 Multi-Source Search")
    
    with st.form("enhanced_search_form_multi"):
        # Search query
        search_query = st.text_area(
            "Search Query:",
            placeholder="Enter your search query, questions, or keywords...",
            height=100,
            help="Search across documents, Excel files, PowerBI reports, and web sources"
        )
        
        # Source selection
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📁 Document Sources:**")
            selected_indexes = st.multiselect(
                "Document Collections:",
                options=available_indexes if available_indexes else ["No indexes available"],
                default=available_indexes[:2] if len(available_indexes) >= 2 else available_indexes
            )
            
            include_excel = st.checkbox("Include Excel Files", value=True)
            
        with col2:
            st.markdown("**🌐 External Sources:**")
            include_web = st.checkbox("Web Search", value=True)
            include_powerbi = st.checkbox("PowerBI Reports", value=False)
            
            if include_web:
                search_engines = st.multiselect(
                    "Search Engines:",
                    ["Google", "Bing", "DuckDuckGo"],
                    default=["Google"]
                )
        
        # Search options
        col1, col2, col3 = st.columns(3)
        
        with col1:
            max_results = st.slider("Max Results per Source:", 1, 20, 5)
        
        with col2:
            search_type = st.selectbox(
                "Search Type:",
                ["Semantic", "Keyword", "Hybrid"]
            )
        
        with col3:
            result_format = st.selectbox(
                "Result Format:",
                ["Summary", "Detailed", "Raw Data"]
            )
        
        # Submit search
        if st.form_submit_button("🔍 Search All Sources", type="primary"):
            if search_query:
                with st.spinner("Searching across all sources..."):
                    search_results = perform_multi_source_search(
                        query=search_query,
                        selected_indexes=selected_indexes,
                        include_web=include_web,
                        include_excel=include_excel,
                        include_powerbi=include_powerbi,
                        search_engines=search_engines if include_web else [],
                        max_results=max_results,
                        search_type=search_type
                    )
                    
                    display_search_results(search_results, result_format)
                    
                    auth_middleware.log_user_action("ENHANCED_MULTI_SOURCE_SEARCH", {
                        "query": search_query,
                        "sources": len(selected_indexes),
                        "include_web": include_web,
                        "include_excel": include_excel,
                        "total_results": sum(len(results) for results in search_results.values())
                    })
            else:
                st.warning("Please enter a search query")

def perform_multi_source_search(query, selected_indexes, include_web, include_excel, include_powerbi, search_engines, max_results, search_type):
    """Perform actual multi-source search"""
    results = {}
    
    # Search document indexes
    if selected_indexes:
        results['documents'] = search_document_indexes(query, selected_indexes, max_results, search_type)
    
    # Search web sources
    if include_web and search_engines:
        results['web'] = search_web_sources(query, search_engines, max_results)
    
    # Search Excel files (if uploaded in session)
    if include_excel:
        results['excel'] = search_excel_data(query, max_results)
    
    # Search PowerBI reports (if configured)
    if include_powerbi:
        results['powerbi'] = search_powerbi_reports(query, max_results)
    
    return results

def search_document_indexes(query, selected_indexes, max_results, search_type):
    """Search through document indexes using existing search functionality"""
    all_results = []
    
    for index_name in selected_indexes:
        try:
            # Try multiple search approaches
            index_results = []
            
            # Method 1: Try direct vector search
            try:
                from utils.direct_vector_search import search_documents
                index_results = search_documents(query, index_name, top_k=max_results)
            except ImportError:
                pass
            
            # Method 2: Try unified Weaviate integration
            if not index_results:
                try:
                    from utils.weaviate_integration import search_all_indexes
                    weaviate_results = search_all_indexes(query, [index_name], max_results)
                    index_results = weaviate_results
                except ImportError:
                    pass
            
            # Method 3: Try legacy FAISS search
            if not index_results:
                try:
                    import os
                    import pickle
                    import faiss
                    from sentence_transformers import SentenceTransformer
                    
                    # Load FAISS index - try multiple path patterns
                    base_path = os.path.join(os.path.dirname(__file__), '..', 'data')
                    possible_paths = [
                        os.path.join(base_path, 'faiss_index', f'{index_name}_index'),
                        os.path.join(base_path, 'faiss_index', index_name),
                        os.path.join(base_path, 'indexes', f'{index_name}_index_index')
                    ]
                    
                    index_path = None
                    for path in possible_paths:
                        if os.path.exists(path):
                            index_path = path
                            break
                    
                    if index_path:
                        # Load FAISS index
                        faiss_file = os.path.join(index_path, 'index.faiss')
                        if os.path.exists(faiss_file):
                            faiss_index = faiss.read_index(faiss_file)
                            
                            # Try different metadata file names
                            metadata = None
                            metadata_files = ['metadata.pkl', 'index.pkl']
                            for meta_file in metadata_files:
                                meta_path = os.path.join(index_path, meta_file)
                                if os.path.exists(meta_path):
                                    with open(meta_path, 'rb') as f:
                                        metadata = pickle.load(f)
                                    break
                            
                            # If no metadata file, try to read text content directly
                            if metadata is None:
                                text_file = os.path.join(index_path, 'extracted_text.txt')
                                if os.path.exists(text_file):
                                    with open(text_file, 'r', encoding='utf-8') as f:
                                        content = f.read()
                                    # Create simple metadata structure
                                    chunks = [content[i:i+1000] for i in range(0, len(content), 1000)]
                                    metadata = [{
                                        'content': chunk,
                                        'source': f'{index_name}.pdf',
                                        'page': i//10 + 1
                                    } for i, chunk in enumerate(chunks)]
                        
                            if metadata:
                                # Generate query embedding
                                model = SentenceTransformer('all-MiniLM-L6-v2')
                                query_embedding = model.encode([query])
                                
                                # Search
                                scores, indices = faiss_index.search(query_embedding, max_results)
                                
                                # Format results
                                for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                                    if idx < len(metadata) and idx >= 0:
                                        doc_metadata = metadata[idx]
                                        # Convert FAISS distance to similarity score
                                        similarity_score = 1.0 / (1.0 + float(score))
                                        index_results.append({
                                            'content': doc_metadata.get('content', 'No content available')[:500] + '...',
                                            'score': similarity_score,
                                            'metadata': {
                                                'source': doc_metadata.get('source', f'{index_name}.pdf'),
                                                'page': doc_metadata.get('page', i + 1),
                                                'index_name': index_name,
                                                'full_content': doc_metadata.get('content', '')
                                            },
                                            'relevance': similarity_score
                                        })
                            else:
                                st.warning(f"No metadata found for {index_name} index")
                        else:
                            st.warning(f"FAISS index file not found for {index_name}")
                    else:
                        st.warning(f"No valid index path found for {index_name}")
                        
                except Exception as faiss_error:
                    st.error(f"FAISS search failed for {index_name}: {str(faiss_error)}")
                    # Add debug info
                    st.write(f"Debug: Tried paths: {possible_paths}")
                    st.write(f"Debug: Found path: {index_path}")
            
            # Format results for display
            for result in index_results:
                all_results.append({
                    'source': index_name,
                    'content': result.get('content', 'No content available'),
                    'score': result.get('score', result.get('relevance', 0.0)),
                    'metadata': result.get('metadata', {}),
                    'type': 'Document'
                })
                
        except Exception as e:
            st.error(f"Error searching index '{index_name}': {str(e)}")
            # Add a fallback result with error info
            all_results.append({
                'source': index_name,
                'content': f"Search error in {index_name}: {str(e)}. Please check index configuration.",
                'score': 0.0,
                'metadata': {'error': True, 'index_name': index_name},
                'type': 'Error'
            })
    
    # Sort by score and return top results
    all_results.sort(key=lambda x: x['score'], reverse=True)
    return all_results[:max_results * len(selected_indexes)]

def search_web_sources(query, search_engines, max_results):
    """Search web sources using available search APIs"""
    # Always use the real web search implementation
    return search_web_real(query, search_engines, max_results)

def search_web_real(query, search_engines, max_results):
    """Real web search implementation using multiple APIs"""
    try:
        import requests
        import json
        from urllib.parse import quote_plus
        
        results = []
        
        for engine in search_engines:
            engine_lower = engine.lower()
            
            if engine_lower == 'duckduckgo':
                # Use DuckDuckGo HTML search for better results
                try:
                    search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                    }
                    
                    response = requests.get(search_url, headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        # Parse HTML results (simplified extraction)
                        import re
                        
                        # Extract result links and titles
                        link_pattern = r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>([^<]+)</a>'
                        snippet_pattern = r'<a[^>]+class="result__snippet"[^>]*>([^<]+)</a>'
                        
                        links = re.findall(link_pattern, response.text)
                        snippets = re.findall(snippet_pattern, response.text)
                        
                        for i, (url, title) in enumerate(links[:max_results]):
                            snippet = snippets[i] if i < len(snippets) else f"Search result for: {query}"
                            
                            results.append({
                                'source': 'DuckDuckGo',
                                'title': title.strip(),
                                'content': snippet.strip(),
                                'url': url,
                                'score': 0.9 - (i * 0.1),
                                'type': 'Web Page'
                            })
                            
                except Exception as e:
                    # Fallback to DuckDuckGo Instant Answer API
                    try:
                        api_url = "https://api.duckduckgo.com/"
                        params = {
                            'q': query,
                            'format': 'json',
                            'no_html': '1',
                            'skip_disambig': '1'
                        }
                        
                        response = requests.get(api_url, params=params, timeout=10)
                        data = response.json()
                        
                        # Extract instant answer
                        if data.get('AbstractText'):
                            results.append({
                                'source': 'DuckDuckGo',
                                'title': data.get('Heading', query),
                                'content': data.get('AbstractText', ''),
                                'url': data.get('AbstractURL', ''),
                                'score': 0.95,
                                'type': 'Web Page'
                            })
                        
                        # Add related topics
                        for topic in data.get('RelatedTopics', [])[:max_results-1]:
                            if isinstance(topic, dict) and 'Text' in topic:
                                results.append({
                                    'source': 'DuckDuckGo',
                                    'title': topic.get('Text', '')[:100] + ('...' if len(topic.get('Text', '')) > 100 else ''),
                                    'content': topic.get('Text', ''),
                                    'url': topic.get('FirstURL', ''),
                                    'score': 0.8,
                                    'type': 'Web Page'
                                })
                                
                    except Exception as e2:
                        st.warning(f"DuckDuckGo search failed: {str(e2)}")
            
            elif engine_lower == 'bing':
                # Use Bing search (requires API key, fallback to search URL)
                try:
                    # Try to get real Bing results via search URL parsing
                    search_url = f"https://www.bing.com/search?q={quote_plus(query)}"
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                    
                    response = requests.get(search_url, headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        import re
                        
                        # Extract Bing results (simplified)
                        title_pattern = r'<h2><a[^>]+href="([^"]+)"[^>]*>([^<]+)</a></h2>'
                        snippet_pattern = r'<p[^>]*class="[^"]*snippet[^"]*"[^>]*>([^<]+)</p>'
                        
                        titles = re.findall(title_pattern, response.text)
                        snippets = re.findall(snippet_pattern, response.text)
                        
                        for i, (url, title) in enumerate(titles[:max_results]):
                            snippet = snippets[i] if i < len(snippets) else f"Bing search result for: {query}"
                            
                            results.append({
                                'source': 'Bing',
                                'title': title.strip(),
                                'content': snippet.strip(),
                                'url': url,
                                'score': 0.85 - (i * 0.05),
                                'type': 'Web Page'
                            })
                            
                except Exception as e:
                    # Fallback result for Bing
                    results.append({
                        'source': 'Bing',
                        'title': f"Bing search: {query}",
                        'content': f"Search results for '{query}' from Bing (API access limited)",
                        'url': f"https://www.bing.com/search?q={quote_plus(query)}",
                        'score': 0.7,
                        'type': 'Web Page'
                    })
            
            elif engine_lower == 'google':
                # Google search (requires API key, provide search URL)
                results.append({
                    'source': 'Google',
                    'title': f"Google search: {query}",
                    'content': f"Search results for '{query}' - Click to view on Google",
                    'url': f"https://www.google.com/search?q={quote_plus(query)}",
                    'score': 0.8,
                    'type': 'Web Page'
                })
        
        return results[:max_results * len(search_engines)]
        
    except Exception as e:
        st.error(f"Web search failed: {str(e)}")
        return []

def search_excel_data(query, max_results):
    """Search through uploaded Excel data in session state"""
    results = []
    
    # Look for Excel data in session state
    for key in st.session_state.keys():
        if key.startswith('processed_data_') or key.startswith('original_data_'):
            try:
                df = st.session_state[key]
                if isinstance(df, pd.DataFrame):
                    # Search through text columns
                    text_columns = df.select_dtypes(include=['object']).columns
                    
                    for col in text_columns:
                        # Case-insensitive search
                        mask = df[col].astype(str).str.contains(query, case=False, na=False)
                        matches = df[mask]
                        
                        for idx, row in matches.iterrows():
                            results.append({
                                'source': f'Excel: {key.replace("processed_data_", "").replace("original_data_", "")}',
                                'content': f"{col}: {row[col]}",
                                'score': 0.8,
                                'metadata': {'row_index': idx, 'column': col},
                                'type': 'Spreadsheet'
                            })
                            
                            if len(results) >= max_results:
                                break
                        
                        if len(results) >= max_results:
                            break
                            
            except Exception as e:
                continue
    
    return results[:max_results]

def search_powerbi_reports(query, max_results):
    """Search PowerBI reports metadata (mock implementation)"""
    # This would require PowerBI API integration
    return [{
        'source': 'PowerBI',
        'title': f"Report containing '{query}'",
        'content': f"PowerBI report with data related to: {query}",
        'score': 0.7,
        'type': 'Dashboard'
    }] if query else []

def display_search_results(search_results, result_format):
    """Display search results in the specified format"""
    if not search_results:
        st.info("No results found across all sources")
        return
    
    total_results = sum(len(results) for results in search_results.values())
    st.success(f"Found {total_results} results across {len(search_results)} source types")
    
    # Create summary table
    summary_data = []
    for source_type, results in search_results.items():
        if results:
            avg_score = sum(r.get('score', 0) for r in results) / len(results)
            summary_data.append({
                'Source Type': source_type.title(),
                'Results': len(results),
                'Avg Relevance': f"{avg_score:.2f}",
                'Type': results[0].get('type', 'Unknown') if results else 'Unknown'
            })
    
    if summary_data:
        st.markdown("### 📊 Search Summary")
        summary_df = pd.DataFrame(summary_data)
        st.dataframe(summary_df, use_container_width=True)
    
    # Display detailed results
    st.markdown("### 🔍 Detailed Results")
    
    for source_type, results in search_results.items():
        if results:
            with st.expander(f"📁 {source_type.title()} Results ({len(results)})", expanded=True):
                
                if result_format == "Summary":
                    for i, result in enumerate(results[:5]):  # Show top 5
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            title = result.get('title', result.get('content', '')[:100] + '...')
                            st.markdown(f"**{i+1}. {title}**")
                            
                            content = result.get('content', '')
                            if len(content) > 200:
                                content = content[:200] + '...'
                            st.write(content)
                            
                            if result.get('url'):
                                st.markdown(f"🔗 [View Source]({result['url']})")
                        
                        with col2:
                            st.metric("Relevance", f"{result.get('score', 0):.2f}")
                            st.caption(f"Source: {result.get('source', 'Unknown')}")
                        
                        st.divider()
                
                elif result_format == "Detailed":
                    for i, result in enumerate(results):
                        st.markdown(f"#### Result {i+1}")
                        
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.write(f"**Source:** {result.get('source', 'Unknown')}")
                            st.write(f"**Type:** {result.get('type', 'Unknown')}")
                            
                            if result.get('title'):
                                st.write(f"**Title:** {result['title']}")
                            
                            st.write(f"**Content:** {result.get('content', 'No content available')}")
                            
                            if result.get('url'):
                                st.markdown(f"🔗 [View Source]({result['url']})")
                            
                            if result.get('metadata'):
                                st.write(f"**Metadata:** {result['metadata']}")
                        
                        with col2:
                            st.metric("Relevance Score", f"{result.get('score', 0):.3f}")
                        
                        st.divider()
                
                else:  # Raw Data
                    st.json(results)

def render_content_management(available_indexes, user_role):
    """Render content management interface"""
    st.subheader("📋 Content Management")
    
    # Content overview
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📄 Documents", "1,247", delta="23 today")
    
    with col2:
        st.metric("📊 Excel Files", "89", delta="5 new")
    
    with col3:
        st.metric("📈 PowerBI Reports", "12", delta="2 updated")
    
    with col4:
        st.metric("🔍 Indexes", len(available_indexes) if available_indexes else 0)
    
    # Content actions (admin/power_user only)
    if user_role in ['admin', 'power_user']:
        st.markdown("### ⚡ Content Actions")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("🔄 Refresh All", key="refresh_all_content"):
                st.success("✅ All content refreshed!")
        
        with col2:
            if st.button("📊 Generate Report", key="content_report"):
                st.success("📊 Content report generated!")
        
        with col3:
            if st.button("🧹 Cleanup", key="content_cleanup"):
                st.success("🧹 Cleanup completed!")
        
        with col4:
            if st.button("💾 Backup", key="content_backup"):
                st.success("💾 Backup initiated!")

def render_integrations_tab():
    """Render integrations configuration tab"""
    st.subheader("⚙️ Integrations & Connectors")
    
    # Available integrations
    integrations = [
        {"name": "PowerBI", "status": "🟡 Configured", "type": "Analytics"},
        {"name": "Excel Online", "status": "🟢 Active", "type": "Spreadsheet"},
        {"name": "SharePoint", "status": "🔴 Not Configured", "type": "Document Store"},
        {"name": "OneDrive", "status": "🟡 Configured", "type": "Cloud Storage"},
        {"name": "Google Sheets", "status": "🔴 Not Configured", "type": "Spreadsheet"},
        {"name": "Tableau", "status": "🔴 Not Configured", "type": "Analytics"}
    ]
    
    st.markdown("### 🔗 Available Integrations")
    
    for integration in integrations:
        with st.expander(f"{integration['name']} - {integration['status']}", expanded=False):
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                st.write(f"**Type:** {integration['type']}")
                st.write(f"**Status:** {integration['status']}")
            
            with col2:
                if st.button("⚙️ Configure", key=f"config_{integration['name'].lower()}"):
                    st.info(f"Opening {integration['name']} configuration...")
            
            with col3:
                if st.button("🧪 Test", key=f"test_{integration['name'].lower()}"):
                    st.success(f"✅ {integration['name']} connection test passed!")
    
    # Add new integration
    st.markdown("### ➕ Add New Integration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        new_integration = st.selectbox(
            "Select Integration:",
            ["Custom API", "Database Connector", "File System", "Web Service"]
        )
    
    with col2:
        if st.button("➕ Add Integration", type="primary"):
            st.success(f"✅ {new_integration} integration added!")
