"""
Notification Settings Tab
Allows users to configure push notifications, email, SMS, and other notification channels
"""

import streamlit as st
from utils.notification_manager import notification_manager, NotificationType, NotificationPriority
import json
from datetime import datetime


def render_notification_settings():
    """Render the notification settings tab"""
    
    st.title("📱 Notification Settings")
    st.markdown("Configure how and when you receive notifications from VaultMind")
    
    # Check if user is logged in
    if 'user' not in st.session_state:
        st.warning("⚠️ Please log in to configure notifications")
        return
    
    user = st.session_state.user
    
    # Initialize notification preferences if not exists
    if 'notification_prefs' not in st.session_state:
        st.session_state.notification_prefs = {
            'enabled': False,
            'channels': {
                'push': False,
                'email': False,
                'sms': False,
                'telegram': False,
                'slack': False,
                'teams': False
            },
            'contact': {
                'email': user.get('email', ''),
                'phone_number': '',
                'telegram_chat_id': ''
            },
            'events': {
                'query_complete': True,
                'document_processed': True,
                'agent_complete': True,
                'system_alert': True,
                'user_mention': True
            },
            'quiet_hours': {
                'enabled': False,
                'start': '22:00',
                'end': '08:00'
            }
        }
    
    prefs = st.session_state.notification_prefs
    
    # Main enable/disable toggle
    st.markdown("---")
    st.subheader("🔔 General Settings")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        prefs['enabled'] = st.checkbox(
            "Enable Push Notifications",
            value=prefs.get('enabled', False),
            help="Receive notifications on your devices and channels",
            key="enable_notifications"
        )
    
    with col2:
        if prefs['enabled']:
            st.success("✅ Enabled")
        else:
            st.info("⏸️ Disabled")
    
    if not prefs['enabled']:
        st.info("ℹ️ Notifications are currently disabled. Enable them above to configure settings.")
        return
    
    # Notification Channels
    st.markdown("---")
    st.subheader("📡 Notification Channels")
    st.markdown("Select which channels you want to receive notifications through")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        prefs['channels']['push'] = st.checkbox(
            "📱 Mobile Push",
            value=prefs['channels'].get('push', False),
            help="Pushover, Firebase FCM, or OneSignal"
        )
        prefs['channels']['email'] = st.checkbox(
            "📧 Email",
            value=prefs['channels'].get('email', False),
            help="Email notifications via SMTP"
        )
    
    with col2:
        prefs['channels']['sms'] = st.checkbox(
            "💬 SMS",
            value=prefs['channels'].get('sms', False),
            help="Text messages via Twilio"
        )
        prefs['channels']['telegram'] = st.checkbox(
            "🤖 Telegram",
            value=prefs['channels'].get('telegram', False),
            help="Telegram bot messages"
        )
    
    with col3:
        prefs['channels']['slack'] = st.checkbox(
            "💼 Slack",
            value=prefs['channels'].get('slack', False),
            help="Slack workspace notifications"
        )
        prefs['channels']['teams'] = st.checkbox(
            "🏢 Microsoft Teams",
            value=prefs['channels'].get('teams', False),
            help="Teams channel notifications"
        )
    
    # Show active channels count
    active_channels = sum(1 for v in prefs['channels'].values() if v)
    if active_channels > 0:
        st.success(f"✅ {active_channels} channel(s) enabled")
    else:
        st.warning("⚠️ No channels selected. Please select at least one channel.")
    
    # Contact Information
    st.markdown("---")
    st.subheader("📞 Contact Information")
    st.markdown("Provide your contact details for each notification channel")
    
    col1, col2 = st.columns(2)
    
    with col1:
        prefs['contact']['email'] = st.text_input(
            "📧 Email Address",
            value=prefs['contact'].get('email', ''),
            placeholder="your.email@example.com",
            help="Required for email notifications",
            disabled=not prefs['channels']['email']
        )
        
        prefs['contact']['phone_number'] = st.text_input(
            "💬 Phone Number",
            value=prefs['contact'].get('phone_number', ''),
            placeholder="+1234567890",
            help="Include country code (e.g., +1 for US). Required for SMS.",
            disabled=not prefs['channels']['sms']
        )
    
    with col2:
        prefs['contact']['telegram_chat_id'] = st.text_input(
            "🤖 Telegram Chat ID",
            value=prefs['contact'].get('telegram_chat_id', ''),
            placeholder="123456789",
            help="Get your chat ID from @userinfobot on Telegram",
            disabled=not prefs['channels']['telegram']
        )
        
        st.markdown("**How to get Telegram Chat ID:**")
        st.markdown("1. Open Telegram and search for `@userinfobot`")
        st.markdown("2. Start a chat and send any message")
        st.markdown("3. Copy your ID and paste it above")
    
    # Event Preferences
    st.markdown("---")
    st.subheader("🔔 Notify Me When")
    st.markdown("Choose which events trigger notifications")
    
    col1, col2 = st.columns(2)
    
    with col1:
        prefs['events']['query_complete'] = st.checkbox(
            "🔍 Query is complete",
            value=prefs['events'].get('query_complete', True),
            help="Get notified when your search query finishes"
        )
        
        prefs['events']['document_processed'] = st.checkbox(
            "📄 Document is processed",
            value=prefs['events'].get('document_processed', True),
            help="Get notified when document ingestion completes"
        )
        
        prefs['events']['agent_complete'] = st.checkbox(
            "🧠 Agent task completes",
            value=prefs['events'].get('agent_complete', True),
            help="Get notified when autonomous agent finishes a task"
        )
    
    with col2:
        prefs['events']['system_alert'] = st.checkbox(
            "⚠️ System alerts",
            value=prefs['events'].get('system_alert', True),
            help="Get notified about system issues and warnings"
        )
        
        prefs['events']['user_mention'] = st.checkbox(
            "👤 Someone mentions me",
            value=prefs['events'].get('user_mention', True),
            help="Get notified when someone @mentions you"
        )
    
    # Quiet Hours
    st.markdown("---")
    st.subheader("🌙 Quiet Hours")
    st.markdown("Pause notifications during specific hours")
    
    prefs['quiet_hours']['enabled'] = st.checkbox(
        "Enable quiet hours",
        value=prefs['quiet_hours'].get('enabled', False),
        help="Notifications will be paused during these hours"
    )
    
    if prefs['quiet_hours']['enabled']:
        col1, col2 = st.columns(2)
        
        with col1:
            prefs['quiet_hours']['start'] = st.time_input(
                "Start time",
                value=datetime.strptime(prefs['quiet_hours'].get('start', '22:00'), '%H:%M').time(),
                help="Quiet hours begin at this time"
            ).strftime('%H:%M')
        
        with col2:
            prefs['quiet_hours']['end'] = st.time_input(
                "End time",
                value=datetime.strptime(prefs['quiet_hours'].get('end', '08:00'), '%H:%M').time(),
                help="Quiet hours end at this time"
            ).strftime('%H:%M')
        
        st.info(f"ℹ️ Notifications will be paused from {prefs['quiet_hours']['start']} to {prefs['quiet_hours']['end']}")
    
    # Test Notifications
    st.markdown("---")
    st.subheader("🧪 Test Notifications")
    st.markdown("Send a test notification to verify your settings")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        test_message = st.text_input(
            "Test message",
            value="Hello from VaultMind! 🎉",
            placeholder="Enter a test message"
        )
    
    with col2:
        test_priority = st.selectbox(
            "Priority",
            options=["Normal", "High", "Urgent"],
            index=0
        )
    
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🧪 Send Test", type="primary", use_container_width=True):
            # Validate at least one channel is selected
            if not any(prefs['channels'].values()):
                st.error("❌ Please select at least one notification channel")
            else:
                with st.spinner("Sending test notification..."):
                    # Prepare channels
                    channels = []
                    if prefs['channels']['push']:
                        channels.append('pushover')
                    if prefs['channels']['email']:
                        channels.append('email')
                    if prefs['channels']['sms']:
                        channels.append('twilio')
                    if prefs['channels']['telegram']:
                        channels.append('telegram')
                    if prefs['channels']['slack']:
                        channels.append('slack')
                    if prefs['channels']['teams']:
                        channels.append('teams')
                    
                    # Map priority
                    priority_map = {
                        'Normal': NotificationPriority.NORMAL,
                        'High': NotificationPriority.HIGH,
                        'Urgent': NotificationPriority.URGENT
                    }
                    
                    # Send test notification
                    try:
                        result = notification_manager.send_notification(
                            title="VaultMind Test Notification",
                            message=test_message,
                            notification_type=NotificationType.INFO,
                            priority=priority_map[test_priority],
                            phone_number=prefs['contact']['phone_number'] if prefs['channels']['sms'] else None,
                            email=prefs['contact']['email'] if prefs['channels']['email'] else None,
                            telegram_chat_id=prefs['contact']['telegram_chat_id'] if prefs['channels']['telegram'] else None,
                            channels=channels if channels else None
                        )
                        
                        # Show results
                        st.success("✅ Test notification sent!")
                        
                        with st.expander("📊 Delivery Status", expanded=True):
                            for channel, success in result.items():
                                if success:
                                    st.success(f"✅ **{channel.title()}:** Delivered")
                                else:
                                    st.error(f"❌ **{channel.title()}:** Failed")
                        
                        # Show tips if any failed
                        if not all(result.values()):
                            st.warning("⚠️ Some notifications failed. Check your configuration:")
                            st.markdown("""
                            - **Email:** Verify SMTP settings in `config/notifications.env`
                            - **SMS:** Check Twilio credentials and phone number format
                            - **Telegram:** Verify bot token and chat ID
                            - **Slack/Teams:** Check webhook URLs
                            - **Pushover:** Verify user key and API token
                            """)
                    
                    except Exception as e:
                        st.error(f"❌ Error sending test notification: {str(e)}")
                        st.info("💡 Make sure notification services are configured in `config/notifications.env`")
    
    # Save Settings
    st.markdown("---")
    st.subheader("💾 Save Settings")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown("Save your notification preferences")
    
    with col2:
        if st.button("📥 Export Settings", use_container_width=True):
            # Export settings as JSON
            settings_json = json.dumps(prefs, indent=2)
            st.download_button(
                label="⬇️ Download JSON",
                data=settings_json,
                file_name=f"notification_settings_{user.get('username', 'user')}.json",
                mime="application/json"
            )
    
    with col3:
        if st.button("💾 Save Settings", type="primary", use_container_width=True):
            # Save to session state (in production, save to database)
            st.session_state.notification_prefs = prefs
            
            # Also update user object
            st.session_state.user['notifications_enabled'] = prefs['enabled']
            st.session_state.user['email'] = prefs['contact']['email']
            st.session_state.user['phone_number'] = prefs['contact']['phone_number']
            st.session_state.user['telegram_chat_id'] = prefs['contact']['telegram_chat_id']
            
            st.success("✅ Notification settings saved successfully!")
            st.balloons()
    
    # Configuration Status
    st.markdown("---")
    st.subheader("📊 Configuration Status")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Active Channels",
            active_channels,
            delta=None
        )
    
    with col2:
        active_events = sum(1 for v in prefs['events'].values() if v)
        st.metric(
            "Active Events",
            active_events,
            delta=None
        )
    
    with col3:
        status = "🟢 Ready" if active_channels > 0 else "🔴 Not Configured"
        st.metric(
            "Status",
            status,
            delta=None
        )
    
    # Help & Documentation
    st.markdown("---")
    with st.expander("📚 Help & Documentation"):
        st.markdown("""
        ### Quick Setup Guides
        
        **Pushover (Easiest - 5 minutes):**
        1. Install Pushover app on your phone ($5 one-time)
        2. Sign up at https://pushover.net
        3. Get your User Key and API Token
        4. Configure in `config/notifications.env`
        
        **Email (Free - 5 minutes):**
        1. Use Gmail or any SMTP server
        2. Generate app-specific password
        3. Configure in `config/notifications.env`
        
        **Telegram (Free - 5 minutes):**
        1. Create a bot with @BotFather
        2. Get your bot token
        3. Get your chat ID from @userinfobot
        4. Configure in `config/notifications.env`
        
        **SMS via Twilio (Pay per message - 10 minutes):**
        1. Sign up at https://www.twilio.com
        2. Get Account SID and Auth Token
        3. Get a Twilio phone number
        4. Configure in `config/notifications.env`
        
        ### Documentation
        - **QUICK_NOTIFICATION_START.md** - 5-minute setup guide
        - **PUSH_NOTIFICATION_SETUP.md** - Complete documentation
        - **config/notifications.env.example** - Configuration template
        
        ### Troubleshooting
        - **Not receiving notifications?** Check your configuration in `config/notifications.env`
        - **Test failed?** Verify your credentials and contact information
        - **Need help?** See the documentation files listed above
        """)


# Main entry point
if __name__ == "__main__":
    render_notification_settings()
