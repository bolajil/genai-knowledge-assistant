import streamlit as st
from datetime import datetime

def render_tool_requests(user, permissions, auth_middleware):
    """Tool Requests Tab - Non-admin users"""
    
    st.header("Tool Requests")
    st.markdown("**Request additional tools and capabilities from administrators**")
    
    # Current User Tools Status
    st.subheader("Your Current Tools")

    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("**Available Tools:**")
        user_tools = [
            "Multi-file upload and processing",
            "Data merging from multiple sources", 
            "Basic content analytics and search",
            "Processing history tracking",
            "Query and chat assistants"
        ]
        
        for tool in user_tools:
            st.write(f"• {tool}")
    
    with col2:
        st.markdown("**Your Usage Stats:**")
        st.metric("Files Processed", "47")
        st.metric("Queries Made", "156") 
        st.metric("Chat Sessions", "23")
        st.metric("Data Merges", "8")
    
    st.divider()

    # Tool Request Form
    st.subheader("Request New Tools")
    
    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown("**Available Tools to Request:**")
        
        available_tools = [
            'web_scraping - Scrape content from websites and URLs',
            'advanced_analytics - Detailed content performance metrics and insights',
            'backup_management - Create and manage index backups',
            'live_streams - Set up real-time data ingestion from RSS/APIs',
            'bulk_processing - Process large batches of documents (100+ files)',
            'custom_embeddings - Use custom embedding models for specialized content'
        ]
        
        selected_tool = st.selectbox(
            "Select Tool to Request:",
            available_tools,
            key="tool_request_select"
        )
        
        request_reason = st.text_area(
            "Business Justification:",
            placeholder="Explain why you need this tool, how you plan to use it, and the business value it will provide...",
            height=120,
            key="tool_request_reason"
        )
        
        urgency = st.selectbox(
            "Request Priority:",
            ["Low - Nice to have", "Medium - Would improve productivity", "High - Critical for current project"],
            key="request_urgency"
        )

    with col2:
        st.markdown("**Request Actions:**")
        
        if st.button("Submit Request", 
                    type="primary",
                    disabled=not request_reason.strip(),
                    key="submit_tool_request"):
            tool_name = selected_tool.split(' - ')[0]
            
            # Send email notification to administrators
            admin_email_sent = False
            try:
                # Get admin users for notification
                admin_users = ["admin@vaultmind.org"]  # In production, query from user database
                
                for admin_email in admin_users:
                    # In production, this would integrate with actual email service
                    email_subject = f"New Tool Request: {tool_name} - {urgency}"
                    email_body = f"""
New Tool Request Submitted

User: {user.username} ({user.email})
Role: {user.role.value.title()}
Tool Requested: {tool_name}
Priority: {urgency}

Business Justification:
{request_reason}

Submitted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Please review this request in the Admin Panel.

VaultMind GenAI Knowledge Assistant
                    """
                    
                    # Log email notification (in production, send actual email)
                    auth_middleware.log_user_action(
                        f"Admin notification sent for tool request: {tool_name}",
                        {"admin_email": admin_email, "tool": tool_name, "priority": urgency}
                    )
                
                admin_email_sent = True
                
            except Exception as e:
                print(f"Failed to send admin notification for tool request: {str(e)}")
            
            # Show success message
            st.success(f"**Request Submitted Successfully!**")
            st.info(f"**Tool:** {tool_name}")
            st.info(f"**Priority:** {urgency}")
            st.info(f"**Status:** Pending admin review")
            
            if admin_email_sent:
                st.success("Administrator has been notified via email")
                st.info("You'll receive notification when reviewed")
            else:
                st.warning("Request submitted but admin notification failed - please contact administrator directly")
            
            # Log the request (in real implementation, this would go to database)
            auth_middleware.log_user_action(
                f"Tool request submitted: {tool_name}",
                {"tool": tool_name, "priority": urgency, "reason": request_reason[:100]}
            )
        
        if st.button("Refresh Status", key="refresh_requests"):
            st.success("Request status refreshed!")

    st.divider()
    
    # Request History
    st.subheader("Your Request History")

    # Sample request history (in real implementation, this would come from database)
    request_history = [
        {
            "tool": "web_scraping",
            "status": "Pending",
            "submitted": "2025-08-09 10:30",
            "priority": "Medium"
        },
        {
            "tool": "advanced_analytics", 
            "status": "Approved",
            "submitted": "2025-08-07 14:15",
            "priority": "High",
            "approved_date": "2025-08-08 09:20"
        },
        {
            "tool": "bulk_processing",
            "status": "Denied",
            "submitted": "2025-08-05 16:45", 
            "priority": "Low",
            "denied_reason": "Current usage doesn't justify bulk processing needs"
        }
    ]
    
    if request_history:
        for i, req in enumerate(request_history):
            with st.expander(f"{req['status']} {req['tool']} - {req['submitted']}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Tool:** {req['tool']}")
                    st.write(f"**Priority:** {req['priority']}")
                    st.write(f"**Submitted:** {req['submitted']}")
                
                with col2:
                    st.write(f"**Status:** {req['status']}")
                    if req['status'] == "Approved":
                        st.write(f"**Approved:** {req.get('approved_date', 'N/A')}")
                        st.success("Tool is now available in your dashboard!")
                    elif req['status'] == "Denied":
                        st.write(f"**Reason:** {req.get('denied_reason', 'No reason provided')}")
                        st.error("Request was denied. You can submit a new request with updated justification.")
    else:
        st.info("No previous requests found. Submit your first tool request above!")

    # Help Section
    st.divider()
    st.subheader("Need Help?")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**📚 Request Tips:**")
        st.write("• Be specific about your use case")
        st.write("• Explain the business value")
        st.write("• Provide realistic timelines")
        st.write("• Reference specific projects when possible")
    
    with col2:
        st.markdown("**⏱️ Processing Times:**")
        st.write("• Low priority: 3-5 business days")
        st.write("• Medium priority: 1-2 business days") 
        st.write("• High priority: Same day review")
        st.write("• Critical requests: Contact admin directly")
