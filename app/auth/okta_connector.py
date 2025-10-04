"""
Real Okta SSO integration for VaultMind enterprise authentication
"""

import streamlit as st
import requests
from typing import Optional, Dict, Any
from datetime import datetime
from urllib.parse import urlencode
import secrets
import base64

class OktaConnector:
    """Real Okta SSO authentication connector"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.okta_config = config.get("okta", {})
    
    def get_authorization_url(self, state: str = None) -> str:
        """Generate Okta authorization URL for OAuth2 flow"""
        if not self.okta_config.get("configured", False):
            return ""
        
        if not state:
            state = secrets.token_urlsafe(32)
        
        # Store state in session for validation
        st.session_state.oauth_state = state
        
        auth_params = {
            'client_id': self.okta_config['client_id'],
            'response_type': 'code',
            'scope': ' '.join(self.okta_config['scopes']),
            'redirect_uri': self.okta_config['redirect_uri'],
            'state': state
        }
        
        base_url = f"https://{self.okta_config['domain']}/oauth2/{self.okta_config['authorization_server']}/v1/authorize"
        return f"{base_url}?{urlencode(auth_params)}"
    
    def exchange_code_for_token(self, code: str, state: str) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for access token"""
        if not self.okta_config.get("configured", False):
            return None
        
        # Validate state parameter
        if state != st.session_state.get('oauth_state'):
            st.error("Invalid OAuth state parameter")
            return None
        
        try:
            from app.auth.config_manager import security_config_manager
            
            # Get client secret
            client_secret = security_config_manager.decrypt_credential(
                self.config, "okta", "client_secret"
            )
            
            if not client_secret:
                st.error("Okta client secret not configured")
                return None
            
            # Token endpoint
            token_url = f"https://{self.okta_config['domain']}/oauth2/{self.okta_config['authorization_server']}/v1/token"
            
            # Prepare token request
            token_data = {
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': self.okta_config['redirect_uri'],
                'client_id': self.okta_config['client_id'],
                'client_secret': client_secret
            }
            
            # Request token
            response = requests.post(token_url, data=token_data, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except requests.RequestException as e:
            st.error(f"Token exchange failed: {str(e)}")
            return None
        except Exception as e:
            st.error(f"Okta authentication error: {str(e)}")
            return None
    
    def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Get user information from Okta using access token"""
        if not self.okta_config.get("configured", False):
            return None
        
        try:
            # User info endpoint
            userinfo_url = f"https://{self.okta_config['domain']}/oauth2/{self.okta_config['authorization_server']}/v1/userinfo"
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/json'
            }
            
            response = requests.get(userinfo_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            user_data = response.json()
            
            # Format user info for VaultMind
            user_info = {
                'username': user_data.get('preferred_username', user_data.get('email', '')),
                'email': user_data.get('email', ''),
                'display_name': user_data.get('name', user_data.get('preferred_username', '')),
                'groups': user_data.get('groups', []),
                'auth_method': 'okta_sso',
                'authenticated_at': datetime.now().isoformat(),
                'okta_sub': user_data.get('sub', ''),
                'raw_user_data': user_data
            }
            
            return user_info
            
        except requests.RequestException as e:
            st.error(f"Failed to get user info: {str(e)}")
            return None
        except Exception as e:
            st.error(f"Okta user info error: {str(e)}")
            return None
    
    def map_groups_to_role(self, groups: list) -> str:
        """Map Okta groups to VaultMind roles"""
        # Define group to role mapping
        role_mappings = {
            'admin': ['VaultMind_Admins', 'Administrators', 'IT_Admin'],
            'user': ['VaultMind_Users', 'Users', 'Employees'],
            'viewer': ['VaultMind_Viewers', 'ReadOnly', 'Guests']
        }
        
        # Check for admin role first
        for group in groups:
            for admin_group in role_mappings['admin']:
                if admin_group.lower() in group.lower():
                    return 'admin'
        
        # Check for user role
        for group in groups:
            for user_group in role_mappings['user']:
                if user_group.lower() in group.lower():
                    return 'user'
        
        # Default to viewer
        return 'viewer'
    
    def initiate_sso_login(self):
        """Initiate Okta SSO login flow"""
        if not self.okta_config.get("configured", False):
            st.error("Okta SSO is not configured")
            return False
        
        # Generate authorization URL
        auth_url = self.get_authorization_url()
        
        if auth_url:
            st.markdown(f"""
            ### 🔐 Okta SSO Login
            
            Click the button below to login with your Okta credentials:
            
            <a href="{auth_url}" target="_self">
                <button style="
                    background-color: #007dc1;
                    color: white;
                    padding: 12px 24px;
                    border: none;
                    border-radius: 6px;
                    font-size: 16px;
                    cursor: pointer;
                    text-decoration: none;
                ">🔐 Login with Okta</button>
            </a>
            """, unsafe_allow_html=True)
            
            return True
        
        return False
    
    def handle_callback(self, code: str, state: str) -> Optional[Dict[str, Any]]:
        """Handle OAuth callback and complete authentication"""
        # Exchange code for token
        token_data = self.exchange_code_for_token(code, state)
        
        if not token_data:
            return None
        
        # Get user information
        user_info = self.get_user_info(token_data['access_token'])
        
        if user_info:
            # Store token data in user info
            user_info['access_token'] = token_data['access_token']
            user_info['token_type'] = token_data.get('token_type', 'Bearer')
            user_info['expires_in'] = token_data.get('expires_in', 3600)
        
        return user_info

# Global connector instance
okta_connector = None

def get_okta_connector(config: Dict[str, Any]) -> OktaConnector:
    """Get Okta connector instance with current config"""
    global okta_connector
    okta_connector = OktaConnector(config)
    return okta_connector
