# Enterprise Configuration for VaultMind GenAI Knowledge Assistant
# Production-ready configuration for enterprise authentication and security

import os
from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum

class AuthProvider(Enum):
    """Supported authentication providers"""
    LOCAL = "local"
    ACTIVE_DIRECTORY = "active_directory"
    AZURE_AD = "azure_ad"
    OKTA = "okta"
    GOOGLE_WORKSPACE = "google_workspace"
    SAML = "saml"

class SecurityLevel(Enum):
    """Security levels for different environments"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    ENTERPRISE = "enterprise"

@dataclass
class EnterpriseConfig:
    """Enterprise configuration settings"""
    
    # Authentication Settings
    PRIMARY_AUTH_PROVIDER: AuthProvider = AuthProvider.LOCAL
    ENABLE_SSO: bool = False
    ENABLE_MFA: bool = True
    MFA_REQUIRED_ROLES: List[str] = None
    
    # Session Management
    SESSION_TIMEOUT_MINUTES: int = 480  # 8 hours
    IDLE_TIMEOUT_MINUTES: int = 60      # 1 hour
    MAX_CONCURRENT_SESSIONS: int = 3
    SECURE_COOKIES: bool = True
    
    # Security Settings
    SECURITY_LEVEL: SecurityLevel = SecurityLevel.PRODUCTION
    ENFORCE_SSL: bool = True
    MIN_PASSWORD_LENGTH: int = 12
    PASSWORD_COMPLEXITY_REQUIRED: bool = True
    ACCOUNT_LOCKOUT_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 30
    
    # Audit & Compliance
    ENABLE_AUDIT_LOGGING: bool = True
    LOG_FAILED_ATTEMPTS: bool = True
    COMPLIANCE_MODE: str = "SOC2"  # SOC2, GDPR, HIPAA, FedRAMP
    DATA_RETENTION_DAYS: int = 2555  # 7 years
    
    # Rate Limiting
    LOGIN_RATE_LIMIT: int = 10  # attempts per minute
    API_RATE_LIMIT: int = 1000  # requests per hour
    
    def __post_init__(self):
        if self.MFA_REQUIRED_ROLES is None:
            self.MFA_REQUIRED_ROLES = ["admin", "manager"]

# Environment-specific configurations
ENTERPRISE_CONFIGS = {
    "development": EnterpriseConfig(
        SECURITY_LEVEL=SecurityLevel.DEVELOPMENT,
        ENFORCE_SSL=False,
        ENABLE_MFA=False,
        SESSION_TIMEOUT_MINUTES=1440,  # 24 hours for dev
        MIN_PASSWORD_LENGTH=8
    ),
    
    "staging": EnterpriseConfig(
        SECURITY_LEVEL=SecurityLevel.STAGING,
        ENFORCE_SSL=True,
        ENABLE_MFA=True,
        SESSION_TIMEOUT_MINUTES=720,   # 12 hours
        MIN_PASSWORD_LENGTH=10
    ),
    
    "production": EnterpriseConfig(
        SECURITY_LEVEL=SecurityLevel.PRODUCTION,
        ENFORCE_SSL=True,
        ENABLE_MFA=True,
        SESSION_TIMEOUT_MINUTES=480,   # 8 hours
        MIN_PASSWORD_LENGTH=12,
        ENABLE_SSO=True
    ),
    
    "enterprise": EnterpriseConfig(
        SECURITY_LEVEL=SecurityLevel.ENTERPRISE,
        ENFORCE_SSL=True,
        ENABLE_MFA=True,
        SESSION_TIMEOUT_MINUTES=240,   # 4 hours
        IDLE_TIMEOUT_MINUTES=30,
        MIN_PASSWORD_LENGTH=14,
        MAX_CONCURRENT_SESSIONS=2,
        ACCOUNT_LOCKOUT_ATTEMPTS=3,
        LOCKOUT_DURATION_MINUTES=60,
        COMPLIANCE_MODE="FedRAMP",
        ENABLE_SSO=True
    )
}

# SSO Provider Configurations
SSO_PROVIDERS = {
    "azure_ad": {
        "client_id": os.getenv("AZURE_CLIENT_ID"),
        "client_secret": os.getenv("AZURE_CLIENT_SECRET"),
        "tenant_id": os.getenv("AZURE_TENANT_ID"),
        "authority": "https://login.microsoftonline.com/{tenant_id}",
        "scope": ["User.Read", "Directory.Read.All"]
    },
    
    "okta": {
        "client_id": os.getenv("OKTA_CLIENT_ID"),
        "client_secret": os.getenv("OKTA_CLIENT_SECRET"),
        "domain": os.getenv("OKTA_DOMAIN"),
        "redirect_uri": os.getenv("OKTA_REDIRECT_URI", "http://localhost:8501/callback"),
        "scope": "openid profile email groups"
    },
    
    "active_directory": {
        "server": os.getenv("AD_SERVER"),
        "domain": os.getenv("AD_DOMAIN"),
        "base_dn": os.getenv("AD_BASE_DN"),
        "service_account": os.getenv("AD_SERVICE_ACCOUNT"),
        "service_password": os.getenv("AD_SERVICE_PASSWORD"),
        "use_ssl": os.getenv("AD_USE_SSL", "true").lower() == "true"
    },
    
    "google_workspace": {
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "domain": os.getenv("GOOGLE_WORKSPACE_DOMAIN"),
        "redirect_uri": os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8501/callback")
    }
}

# Security Headers for Production
SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
    "Referrer-Policy": "strict-origin-when-cross-origin"
}

# Compliance Settings
COMPLIANCE_SETTINGS = {
    "SOC2": {
        "encryption_required": True,
        "audit_all_access": True,
        "data_classification": True,
        "incident_response": True
    },
    
    "GDPR": {
        "data_minimization": True,
        "right_to_erasure": True,
        "consent_management": True,
        "breach_notification": True,
        "data_portability": True
    },
    
    "HIPAA": {
        "phi_encryption": True,
        "access_controls": True,
        "audit_logs": True,
        "risk_assessment": True,
        "business_associate": True
    },
    
    "FedRAMP": {
        "continuous_monitoring": True,
        "incident_response": True,
        "configuration_management": True,
        "vulnerability_scanning": True,
        "multi_factor_auth": True
    }
}

def get_config(environment: str = None) -> EnterpriseConfig:
    """Get configuration for specified environment"""
    if environment is None:
        environment = os.getenv("ENVIRONMENT", "production")
    
    return ENTERPRISE_CONFIGS.get(environment, ENTERPRISE_CONFIGS["production"])

def get_sso_config(provider: str) -> Dict:
    """Get SSO configuration for specified provider"""
    return SSO_PROVIDERS.get(provider, {})

def get_compliance_settings(mode: str) -> Dict:
    """Get compliance settings for specified mode"""
    return COMPLIANCE_SETTINGS.get(mode, COMPLIANCE_SETTINGS["SOC2"])
