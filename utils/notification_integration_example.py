"""
Example: How to integrate push notifications into VaultMind tabs
This shows practical examples of adding notifications to existing functionality
"""

import streamlit as st
from utils.notification_manager import (
    notification_manager,
    NotificationType,
    NotificationPriority,
    send_push_notification,
    send_email_notification
)


# ============================================
# Example 1: Query Assistant with Notifications
# ============================================

def query_assistant_with_notifications():
    """Enhanced Query Assistant with push notifications"""
    
    st.title("🔍 Query Assistant")
    
    # Get user notification preferences
    user_prefs = st.session_state.get('user_notification_prefs', {})
    
    # Query input
    query = st.text_area("Enter your question:", height=100)
    
    # Notification options
    with st.expander("📱 Notification Settings"):
        notify_on_complete = st.checkbox(
            "Notify me when query is complete",
            value=user_prefs.get('notify_on_query', False)
        )
        
        if notify_on_complete:
            col1, col2 = st.columns(2)
            with col1:
                notify_push = st.checkbox("📱 Push", value=True)
                notify_email = st.checkbox("📧 Email", value=True)
            with col2:
                notify_sms = st.checkbox("💬 SMS", value=False)
                notify_telegram = st.checkbox("🤖 Telegram", value=False)
    
    # Search button
    if st.button("🔍 Search", type="primary"):
        if not query:
            st.warning("Please enter a question")
            return
        
        # Show progress
        with st.spinner("Searching documents..."):
            # Perform search (your existing logic)
            from utils.unified_document_retrieval import search_documents
            results = search_documents(query, "default_faiss")
            
            # Display results
            st.markdown("### Results")
            st.markdown(results)
            
            # Send notifications if enabled
            if notify_on_complete:
                user = st.session_state.get('user', {})
                
                # Prepare notification channels
                channels = []
                if notify_push:
                    channels.append('pushover')
                if notify_email:
                    channels.append('email')
                if notify_sms:
                    channels.append('twilio')
                if notify_telegram:
                    channels.append('telegram')
                
                # Send notification
                notification_result = notification_manager.notify_query_complete(
                    user_id=user.get('username', 'unknown'),
                    query=query,
                    results_count=len(results.split('\n')),
                    device_tokens=user.get('device_tokens'),
                    phone_number=user.get('phone_number'),
                    email=user.get('email'),
                    telegram_chat_id=user.get('telegram_chat_id'),
                    channels=channels if channels else None
                )
                
                # Show notification status
                if any(notification_result.values()):
                    st.success("✅ Notification sent to your device!")
                else:
                    st.info("ℹ️ Notifications not configured. Check settings.")


# ============================================
# Example 2: Document Ingestion with Notifications
# ============================================

def document_ingestion_with_notifications():
    """Enhanced Document Ingestion with progress notifications"""
    
    st.title("📄 Document Ingestion")
    
    # File upload
    uploaded_file = st.file_uploader(
        "Upload Document",
        type=['pdf', 'txt', 'docx']
    )
    
    if uploaded_file:
        # Notification preferences
        with st.expander("📱 Notification Settings"):
            notify_on_complete = st.checkbox(
                "Notify me when processing is complete",
                value=True
            )
            
            notify_on_progress = st.checkbox(
                "Send progress updates",
                value=False
            )
        
        # Process button
        if st.button("🚀 Process Document", type="primary"):
            user = st.session_state.get('user', {})
            
            # Progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # Step 1: Upload
                status_text.text("📤 Uploading document...")
                progress_bar.progress(20)
                
                if notify_on_progress:
                    send_push_notification(
                        title="Document Upload",
                        message=f"Processing {uploaded_file.name}...",
                        device_tokens=user.get('device_tokens')
                    )
                
                # Step 2: Quality Check
                status_text.text("🔍 Analyzing document quality...")
                progress_bar.progress(40)
                
                from utils.document_quality_checker import check_document_quality
                quality_score = check_document_quality(uploaded_file)
                
                # Step 3: Processing
                status_text.text("⚙️ Processing and chunking...")
                progress_bar.progress(60)
                
                # Your existing ingestion logic here
                # chunks = process_document(uploaded_file)
                chunks = 186  # Example
                
                # Step 4: Indexing
                status_text.text("📊 Creating vector embeddings...")
                progress_bar.progress(80)
                
                # Step 5: Complete
                status_text.text("✅ Document indexed successfully!")
                progress_bar.progress(100)
                
                # Send completion notification
                if notify_on_complete:
                    notification_manager.notify_document_processed(
                        user_id=user.get('username', 'unknown'),
                        document_name=uploaded_file.name,
                        chunks_count=chunks,
                        device_tokens=user.get('device_tokens'),
                        email=user.get('email'),
                        data={
                            'quality_score': quality_score,
                            'file_size': uploaded_file.size,
                            'chunks': chunks
                        }
                    )
                
                st.success(f"✅ Document processed! {chunks} chunks created.")
                st.balloons()
                
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                
                # Send error notification
                notification_manager.send_notification(
                    title="Document Processing Failed",
                    message=f"Error processing {uploaded_file.name}: {str(e)}",
                    notification_type=NotificationType.ERROR,
                    priority=NotificationPriority.HIGH,
                    device_tokens=user.get('device_tokens'),
                    email=user.get('email')
                )


# ============================================
# Example 3: User Settings Tab for Notifications
# ============================================

def notification_settings_tab():
    """User settings for managing notifications"""
    
    st.title("📱 Notification Settings")
    
    user = st.session_state.get('user', {})
    
    # Enable/disable notifications
    st.subheader("General Settings")
    
    enable_notifications = st.checkbox(
        "Enable Push Notifications",
        value=user.get('notifications_enabled', False),
        help="Receive notifications on your devices"
    )
    
    if enable_notifications:
        # Notification channels
        st.subheader("Notification Channels")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            enable_push = st.checkbox(
                "📱 Mobile Push",
                value=True,
                help="Pushover, FCM, or OneSignal"
            )
            enable_email = st.checkbox(
                "📧 Email",
                value=True
            )
        
        with col2:
            enable_sms = st.checkbox(
                "💬 SMS",
                value=False,
                help="Requires Twilio setup"
            )
            enable_telegram = st.checkbox(
                "🤖 Telegram",
                value=False
            )
        
        with col3:
            enable_slack = st.checkbox(
                "💼 Slack",
                value=False
            )
            enable_teams = st.checkbox(
                "🏢 Teams",
                value=False
            )
        
        # Contact information
        st.subheader("Contact Information")
        
        email = st.text_input(
            "Email Address",
            value=user.get('email', ''),
            placeholder="your.email@example.com"
        )
        
        phone = st.text_input(
            "Phone Number",
            value=user.get('phone_number', ''),
            placeholder="+1234567890",
            help="Include country code"
        )
        
        telegram_id = st.text_input(
            "Telegram Chat ID",
            value=user.get('telegram_chat_id', ''),
            placeholder="123456789",
            help="Get from @userinfobot on Telegram"
        )
        
        # Event preferences
        st.subheader("Notify Me When")
        
        col1, col2 = st.columns(2)
        
        with col1:
            notify_query = st.checkbox(
                "Query is complete",
                value=True
            )
            notify_document = st.checkbox(
                "Document is processed",
                value=True
            )
        
        with col2:
            notify_mention = st.checkbox(
                "Someone mentions me",
                value=True
            )
            notify_system = st.checkbox(
                "System alerts",
                value=True
            )
        
        # Quiet hours
        st.subheader("Quiet Hours")
        
        enable_quiet_hours = st.checkbox(
            "Enable quiet hours",
            value=False,
            help="Pause notifications during specified hours"
        )
        
        if enable_quiet_hours:
            col1, col2 = st.columns(2)
            with col1:
                quiet_start = st.time_input("Start time", value=None)
            with col2:
                quiet_end = st.time_input("End time", value=None)
        
        # Test notification
        st.subheader("Test Notifications")
        
        if st.button("🧪 Send Test Notification"):
            with st.spinner("Sending test notification..."):
                # Prepare channels
                channels = []
                if enable_push:
                    channels.append('pushover')
                if enable_email:
                    channels.append('email')
                if enable_sms:
                    channels.append('twilio')
                if enable_telegram:
                    channels.append('telegram')
                if enable_slack:
                    channels.append('slack')
                if enable_teams:
                    channels.append('teams')
                
                # Send test
                result = notification_manager.send_notification(
                    title="VaultMind Test",
                    message="If you see this, notifications are working! 🎉",
                    notification_type=NotificationType.SUCCESS,
                    priority=NotificationPriority.NORMAL,
                    device_tokens=user.get('device_tokens'),
                    phone_number=phone if enable_sms else None,
                    email=email if enable_email else None,
                    telegram_chat_id=telegram_id if enable_telegram else None,
                    channels=channels if channels else None
                )
                
                # Show results
                st.success("Test notification sent!")
                
                with st.expander("📊 Delivery Status"):
                    for channel, success in result.items():
                        status = "✅ Delivered" if success else "❌ Failed"
                        st.write(f"**{channel.title()}:** {status}")
        
        # Save settings
        if st.button("💾 Save Settings", type="primary"):
            # Save to database
            user_settings = {
                'notifications_enabled': enable_notifications,
                'channels': {
                    'push': enable_push,
                    'email': enable_email,
                    'sms': enable_sms,
                    'telegram': enable_telegram,
                    'slack': enable_slack,
                    'teams': enable_teams
                },
                'contact': {
                    'email': email,
                    'phone_number': phone,
                    'telegram_chat_id': telegram_id
                },
                'events': {
                    'query_complete': notify_query,
                    'document_processed': notify_document,
                    'user_mention': notify_mention,
                    'system_alert': notify_system
                },
                'quiet_hours': {
                    'enabled': enable_quiet_hours,
                    'start': str(quiet_start) if enable_quiet_hours else None,
                    'end': str(quiet_end) if enable_quiet_hours else None
                }
            }
            
            # Save to session state (in production, save to database)
            st.session_state.user_notification_prefs = user_settings
            
            st.success("✅ Notification settings saved!")
    
    else:
        st.info("ℹ️ Notifications are currently disabled. Enable them to receive updates.")


# ============================================
# Example 4: Admin System Alerts
# ============================================

def send_admin_alert(alert_type, message, priority=NotificationPriority.HIGH):
    """Send alert to all admins"""
    
    # Get all admin users (from your auth system)
    from app.auth.authentication import auth_manager
    admins = [user for user in auth_manager.get_all_users() if user.role.value == 'admin']
    
    # Send to each admin
    for admin in admins:
        notification_manager.send_notification(
            title=f"VaultMind Admin Alert: {alert_type}",
            message=message,
            notification_type=NotificationType.SYSTEM_ALERT,
            priority=priority,
            user_id=admin.username,
            email=admin.email,
            # Add device tokens and other contact info from user profile
        )


# Example usage of admin alerts
def example_admin_alerts():
    """Examples of when to send admin alerts"""
    
    # High disk usage
    if disk_usage_percent > 90:
        send_admin_alert(
            "High Disk Usage",
            f"Disk usage is at {disk_usage_percent}%. Please free up space.",
            priority=NotificationPriority.URGENT
        )
    
    # Failed ingestion
    if ingestion_failed:
        send_admin_alert(
            "Document Ingestion Failed",
            f"Failed to process document: {document_name}. Error: {error_message}",
            priority=NotificationPriority.HIGH
        )
    
    # New user registration
    if new_user_registered:
        send_admin_alert(
            "New User Registration",
            f"New user {username} has registered and is awaiting approval.",
            priority=NotificationPriority.NORMAL
        )


# ============================================
# Example 5: Batch Notifications
# ============================================

def send_batch_notifications(users, title, message):
    """Send notifications to multiple users efficiently"""
    
    # Group users by notification preferences
    push_users = []
    email_users = []
    sms_users = []
    
    for user in users:
        prefs = user.get('notification_prefs', {})
        
        if prefs.get('push_enabled'):
            push_users.append(user)
        if prefs.get('email_enabled'):
            email_users.append(user)
        if prefs.get('sms_enabled'):
            sms_users.append(user)
    
    # Send push notifications (can batch device tokens)
    if push_users:
        device_tokens = [u.get('device_token') for u in push_users if u.get('device_token')]
        if device_tokens:
            notification_manager.send_notification(
                title=title,
                message=message,
                device_tokens=device_tokens,
                channels=['fcm', 'onesignal', 'pushover']
            )
    
    # Send emails (can batch)
    if email_users:
        for user in email_users:
            send_email_notification(
                email=user.get('email'),
                title=title,
                message=message
            )
    
    # Send SMS (individual)
    if sms_users:
        for user in sms_users:
            send_sms_notification(
                phone_number=user.get('phone_number'),
                message=f"{title}: {message}"
            )


# ============================================
# Example 6: Scheduled Notifications
# ============================================

def setup_scheduled_notifications():
    """Set up scheduled notifications (use with APScheduler or similar)"""
    
    from apscheduler.schedulers.background import BackgroundScheduler
    
    scheduler = BackgroundScheduler()
    
    # Daily summary at 9 AM
    scheduler.add_job(
        send_daily_summary,
        'cron',
        hour=9,
        minute=0
    )
    
    # Weekly report on Monday at 8 AM
    scheduler.add_job(
        send_weekly_report,
        'cron',
        day_of_week='mon',
        hour=8,
        minute=0
    )
    
    scheduler.start()


def send_daily_summary():
    """Send daily activity summary to users"""
    
    # Get user activity from database
    # activity = get_user_activity_today()
    
    notification_manager.send_notification(
        title="Daily Summary",
        message=f"Today: {queries_count} queries, {documents_count} documents processed",
        notification_type=NotificationType.INFO,
        priority=NotificationPriority.LOW,
        # Send to all users with daily summary enabled
    )


def send_weekly_report():
    """Send weekly report to admins"""
    
    # Generate report
    # report = generate_weekly_report()
    
    send_admin_alert(
        "Weekly Report",
        f"This week: {total_users} active users, {total_queries} queries, {total_documents} documents",
        priority=NotificationPriority.NORMAL
    )


# ============================================
# Usage Examples
# ============================================

if __name__ == "__main__":
    # Example 1: Simple push notification
    send_push_notification(
        title="Test",
        message="Hello from VaultMind!"
    )
    
    # Example 2: Multi-channel notification
    notification_manager.send_notification(
        title="Important Update",
        message="Your query is complete!",
        device_tokens=["token1"],
        email="user@example.com",
        phone_number="+1234567890",
        channels=['pushover', 'email', 'twilio']
    )
    
    # Example 3: High priority alert
    notification_manager.send_notification(
        title="Urgent: System Alert",
        message="Database connection lost!",
        notification_type=NotificationType.ERROR,
        priority=NotificationPriority.URGENT,
        email="admin@company.com"
    )
