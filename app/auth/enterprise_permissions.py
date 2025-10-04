"""
VaultMind Enterprise Permission System
Granular role-based access control with feature-level permissions
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional
from datetime import datetime
import json
import os
from pathlib import Path

class PermissionLevel(Enum):
    """Permission levels for features"""
    NONE = "none"
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"

class FeatureCategory(Enum):
    """Feature categories for organization"""
    DOCUMENT_MANAGEMENT = "document_management"
    AI_SERVICES = "ai_services"
    SEARCH_ANALYTICS = "search_analytics"
    SYSTEM_ADMIN = "system_admin"
    COLLABORATION = "collaboration"
    INTEGRATIONS = "integrations"

@dataclass
class Feature:
    """Individual feature with permission levels"""
    id: str
    name: str
    description: str
    category: FeatureCategory
    available_levels: List[PermissionLevel]
    default_level: PermissionLevel = PermissionLevel.NONE
    requires_approval: bool = False
    cost_tier: str = "free"  # free, standard, premium, enterprise

@dataclass
class ResourceRequest:
    """User request for additional resources/permissions"""
    id: str
    user_id: str
    username: str
    feature_id: str
    requested_level: PermissionLevel
    justification: str
    status: str = "pending"  # pending, approved, rejected
    requested_at: datetime = field(default_factory=datetime.now)
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    admin_notes: Optional[str] = None

class EnterprisePermissionManager:
    """Enterprise-grade permission management system"""
    
    def __init__(self):
        self.features = self._initialize_features()
        self.role_templates = self._initialize_role_templates()
        self._overrides = {}
        # Load overrides from config file (optional)
        try:
            self._load_overrides()
            self._apply_overrides()
        except Exception:
            # Fail gracefully if overrides cannot be loaded
            self._overrides = {}
    
    def _initialize_features(self) -> Dict[str, Feature]:
        """Initialize all available features"""
        features = {
            # Document Management
            "document_upload": Feature(
                id="document_upload",
                name="Document Upload",
                description="Upload and ingest documents",
                category=FeatureCategory.DOCUMENT_MANAGEMENT,
                available_levels=[PermissionLevel.NONE, PermissionLevel.WRITE],
                default_level=PermissionLevel.NONE
            ),
            "document_delete": Feature(
                id="document_delete",
                name="Document Deletion",
                description="Delete documents from the system",
                category=FeatureCategory.DOCUMENT_MANAGEMENT,
                available_levels=[PermissionLevel.NONE, PermissionLevel.WRITE, PermissionLevel.ADMIN],
                default_level=PermissionLevel.NONE,
                requires_approval=True
            ),
            "bulk_operations": Feature(
                id="bulk_operations",
                name="Bulk Document Operations",
                description="Perform bulk operations on multiple documents",
                category=FeatureCategory.DOCUMENT_MANAGEMENT,
                available_levels=[PermissionLevel.NONE, PermissionLevel.WRITE],
                default_level=PermissionLevel.NONE,
                requires_approval=True,
                cost_tier="standard"
            ),
            
            # AI Services
            "basic_query": Feature(
                id="basic_query",
                name="Basic Query Assistant",
                description="Ask questions about uploaded documents",
                category=FeatureCategory.AI_SERVICES,
                available_levels=[PermissionLevel.NONE, PermissionLevel.READ],
                default_level=PermissionLevel.READ
            ),
            "advanced_chat": Feature(
                id="advanced_chat",
                name="Advanced Chat Assistant",
                description="Interactive chat with AI assistant",
                category=FeatureCategory.AI_SERVICES,
                available_levels=[PermissionLevel.NONE, PermissionLevel.READ, PermissionLevel.WRITE],
                default_level=PermissionLevel.NONE,
                cost_tier="standard"
            ),
            "agent_assistant": Feature(
                id="agent_assistant",
                name="AI Agent Assistant",
                description="Advanced AI agents for complex tasks",
                category=FeatureCategory.AI_SERVICES,
                available_levels=[PermissionLevel.NONE, PermissionLevel.READ, PermissionLevel.WRITE],
                default_level=PermissionLevel.NONE,
                requires_approval=True,
                cost_tier="premium"
            ),
            "custom_models": Feature(
                id="custom_models",
                name="Custom AI Models",
                description="Deploy and use custom AI models",
                category=FeatureCategory.AI_SERVICES,
                available_levels=[PermissionLevel.NONE, PermissionLevel.ADMIN],
                default_level=PermissionLevel.NONE,
                requires_approval=True,
                cost_tier="enterprise"
            ),
            
            # Search & Analytics
            "multi_source_search": Feature(
                id="multi_source_search",
                name="Multi-Source Search",
                description="Search across multiple data sources",
                category=FeatureCategory.SEARCH_ANALYTICS,
                available_levels=[PermissionLevel.NONE, PermissionLevel.READ],
                default_level=PermissionLevel.NONE,
                cost_tier="standard"
            ),
            "enhanced_research": Feature(
                id="enhanced_research",
                name="Enhanced Research Tools",
                description="Advanced research and analysis tools",
                category=FeatureCategory.SEARCH_ANALYTICS,
                available_levels=[PermissionLevel.NONE, PermissionLevel.READ, PermissionLevel.WRITE],
                default_level=PermissionLevel.NONE,
                cost_tier="premium"
            ),
            "analytics_dashboard": Feature(
                id="analytics_dashboard",
                name="Analytics Dashboard",
                description="Usage analytics and insights",
                category=FeatureCategory.SEARCH_ANALYTICS,
                available_levels=[PermissionLevel.NONE, PermissionLevel.READ],
                default_level=PermissionLevel.NONE,
                requires_approval=True,
                cost_tier="premium"
            ),
            
            # System Administration
            "user_management": Feature(
                id="user_management",
                name="User Management",
                description="Manage user accounts and permissions",
                category=FeatureCategory.SYSTEM_ADMIN,
                available_levels=[PermissionLevel.NONE, PermissionLevel.ADMIN],
                default_level=PermissionLevel.NONE
            ),
            "system_config": Feature(
                id="system_config",
                name="System Configuration",
                description="Configure system settings and integrations",
                category=FeatureCategory.SYSTEM_ADMIN,
                available_levels=[PermissionLevel.NONE, PermissionLevel.ADMIN],
                default_level=PermissionLevel.NONE
            ),
            "audit_logs": Feature(
                id="audit_logs",
                name="Audit Logs",
                description="View system audit logs and user activity",
                category=FeatureCategory.SYSTEM_ADMIN,
                available_levels=[PermissionLevel.NONE, PermissionLevel.READ, PermissionLevel.ADMIN],
                default_level=PermissionLevel.NONE,
                cost_tier="premium"
            ),
            
            # Collaboration
            "content_sharing": Feature(
                id="content_sharing",
                name="Content Sharing",
                description="Share documents and insights with other users",
                category=FeatureCategory.COLLABORATION,
                available_levels=[PermissionLevel.NONE, PermissionLevel.READ, PermissionLevel.WRITE],
                default_level=PermissionLevel.NONE,
                cost_tier="standard"
            ),
            "team_workspaces": Feature(
                id="team_workspaces",
                name="Team Workspaces",
                description="Create and manage team workspaces",
                category=FeatureCategory.COLLABORATION,
                available_levels=[PermissionLevel.NONE, PermissionLevel.READ, PermissionLevel.WRITE, PermissionLevel.ADMIN],
                default_level=PermissionLevel.NONE,
                requires_approval=True,
                cost_tier="premium"
            ),
            # Collaboration: Messaging & Notifications
            "email_sending": Feature(
                id="email_sending",
                name="Email Sending",
                description="Send emails (SMTP/Microsoft Graph) from the Agent",
                category=FeatureCategory.COLLABORATION,
                available_levels=[PermissionLevel.NONE, PermissionLevel.WRITE, PermissionLevel.ADMIN],
                default_level=PermissionLevel.NONE,
                requires_approval=True,
                cost_tier="standard"
            ),
            "slack_messaging": Feature(
                id="slack_messaging",
                name="Slack Messaging",
                description="Send messages to Slack channels via webhooks",
                category=FeatureCategory.COLLABORATION,
                available_levels=[PermissionLevel.NONE, PermissionLevel.WRITE, PermissionLevel.ADMIN],
                default_level=PermissionLevel.NONE,
                requires_approval=True,
                cost_tier="standard"
            ),
            "teams_messaging": Feature(
                id="teams_messaging",
                name="Microsoft Teams Messaging",
                description="Send messages to Microsoft Teams via webhooks",
                category=FeatureCategory.COLLABORATION,
                available_levels=[PermissionLevel.NONE, PermissionLevel.WRITE, PermissionLevel.ADMIN],
                default_level=PermissionLevel.NONE,
                requires_approval=True,
                cost_tier="standard"
            ),
            
            # Integrations
            "api_access": Feature(
                id="api_access",
                name="API Access",
                description="Access to REST API endpoints",
                category=FeatureCategory.INTEGRATIONS,
                available_levels=[PermissionLevel.NONE, PermissionLevel.READ, PermissionLevel.WRITE],
                default_level=PermissionLevel.NONE,
                requires_approval=True,
                cost_tier="standard"
            ),
            "webhook_config": Feature(
                id="webhook_config",
                name="Webhook Configuration",
                description="Configure webhooks for external integrations",
                category=FeatureCategory.INTEGRATIONS,
                available_levels=[PermissionLevel.NONE, PermissionLevel.WRITE, PermissionLevel.ADMIN],
                default_level=PermissionLevel.NONE,
                requires_approval=True,
                cost_tier="premium"
            ),
            "sso_integration": Feature(
                id="sso_integration",
                name="SSO Integration",
                description="Single Sign-On integration setup",
                category=FeatureCategory.INTEGRATIONS,
                available_levels=[PermissionLevel.NONE, PermissionLevel.ADMIN],
                default_level=PermissionLevel.NONE,
                cost_tier="enterprise"
            )
        }
        return features
    
    def _initialize_role_templates(self) -> Dict[str, Dict[str, PermissionLevel]]:
        """Initialize role-based permission templates"""
        return {
            "viewer": {
                "basic_query": PermissionLevel.READ,
                "document_upload": PermissionLevel.NONE,
                "document_delete": PermissionLevel.NONE,
                "advanced_chat": PermissionLevel.NONE,
                "agent_assistant": PermissionLevel.NONE,
                "multi_source_search": PermissionLevel.NONE,
                "enhanced_research": PermissionLevel.NONE,
                "user_management": PermissionLevel.NONE,
                "system_config": PermissionLevel.NONE,
                "content_sharing": PermissionLevel.NONE,
                "email_sending": PermissionLevel.NONE,
                "slack_messaging": PermissionLevel.NONE,
                "teams_messaging": PermissionLevel.NONE,
                "api_access": PermissionLevel.NONE
            },
            "user": {
                "basic_query": PermissionLevel.READ,
                "document_upload": PermissionLevel.WRITE,
                "document_delete": PermissionLevel.NONE,
                "advanced_chat": PermissionLevel.READ,
                "agent_assistant": PermissionLevel.NONE,
                "multi_source_search": PermissionLevel.READ,
                "enhanced_research": PermissionLevel.NONE,
                "user_management": PermissionLevel.NONE,
                "system_config": PermissionLevel.NONE,
                "content_sharing": PermissionLevel.READ,
                "email_sending": PermissionLevel.NONE,
                "slack_messaging": PermissionLevel.NONE,
                "teams_messaging": PermissionLevel.NONE,
                "api_access": PermissionLevel.NONE
            },
            "power_user": {
                "basic_query": PermissionLevel.READ,
                "document_upload": PermissionLevel.WRITE,
                "document_delete": PermissionLevel.WRITE,
                "advanced_chat": PermissionLevel.WRITE,
                "agent_assistant": PermissionLevel.READ,
                "multi_source_search": PermissionLevel.READ,
                "enhanced_research": PermissionLevel.READ,
                "user_management": PermissionLevel.NONE,
                "system_config": PermissionLevel.NONE,
                "content_sharing": PermissionLevel.WRITE,
                "email_sending": PermissionLevel.NONE,
                "slack_messaging": PermissionLevel.NONE,
                "teams_messaging": PermissionLevel.NONE,
                "api_access": PermissionLevel.READ
            },
            "admin": {
                # Admins get full access to everything
                **{feature_id: PermissionLevel.ADMIN for feature_id in [
                    "document_upload", "document_delete", "bulk_operations",
                    "basic_query", "advanced_chat", "agent_assistant", "custom_models",
                    "multi_source_search", "enhanced_research", "analytics_dashboard",
                    "user_management", "system_config", "audit_logs",
                    "content_sharing", "team_workspaces", "email_sending", "slack_messaging", "teams_messaging",
                    "api_access", "webhook_config", "sso_integration"
                ]}
            }
        }
    
    def get_user_permissions(self, role: str, custom_permissions: Dict[str, str] = None) -> Dict[str, PermissionLevel]:
        """Get effective permissions for a user"""
        base_permissions = self.role_templates.get(role, self.role_templates["viewer"])
        
        if custom_permissions:
            # Apply custom permissions on top of role template
            for feature_id, level_str in custom_permissions.items():
                if feature_id in self.features:
                    try:
                        level = PermissionLevel(level_str)
                        if level in self.features[feature_id].available_levels:
                            base_permissions[feature_id] = level
                    except ValueError:
                        continue
        
        return base_permissions

    # --- Overrides management ---
    def _overrides_path(self) -> Path:
        return Path("config") / "permissions_overrides.json"

    def _load_overrides(self):
        path = self._overrides_path()
        if path.exists():
            try:
                self._overrides = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                self._overrides = {}
        else:
            self._overrides = {}

    def _save_overrides(self):
        path = self._overrides_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(self._overrides, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _apply_overrides(self):
        """Apply overrides to features and role templates in memory."""
        ov = self._overrides or {}
        # Feature overrides
        for fid, fov in (ov.get("features") or {}).items():
            if fid in self.features and isinstance(fov, dict):
                feature = self.features[fid]
                if "requires_approval" in fov:
                    feature.requires_approval = bool(fov["requires_approval"])
                if "default_level" in fov:
                    try:
                        lvl = PermissionLevel(str(fov["default_level"]))
                        if lvl in feature.available_levels:
                            feature.default_level = lvl
                    except Exception:
                        pass
                if "cost_tier" in fov:
                    feature.cost_tier = str(fov["cost_tier"]) or feature.cost_tier
        # Role template overrides
        for role, fmap in (ov.get("role_templates") or {}).items():
            if role in self.role_templates and isinstance(fmap, dict):
                for fid, lvl_str in fmap.items():
                    if fid in self.features:
                        try:
                            lvl = PermissionLevel(str(lvl_str))
                            if lvl in self.features[fid].available_levels:
                                self.role_templates[role][fid] = lvl
                        except Exception:
                            pass

    def update_feature_policy(self, feature_id: str, *, requires_approval: Optional[bool] = None,
                               default_level: Optional[str] = None, cost_tier: Optional[str] = None) -> bool:
        """Update feature policy and persist to overrides file."""
        if feature_id not in self.features:
            return False
        feature = self.features[feature_id]
        # Prepare override map
        self._overrides.setdefault("features", {})
        fov = self._overrides["features"].setdefault(feature_id, {})
        if requires_approval is not None:
            feature.requires_approval = bool(requires_approval)
            fov["requires_approval"] = bool(requires_approval)
        if default_level is not None:
            try:
                lvl = PermissionLevel(str(default_level))
                if lvl in feature.available_levels:
                    feature.default_level = lvl
                    fov["default_level"] = lvl.value
            except Exception:
                pass
        if cost_tier is not None:
            feature.cost_tier = str(cost_tier)
            fov["cost_tier"] = feature.cost_tier
        self._save_overrides()
        return True

    def update_role_template(self, role: str, feature_id: str, level: str) -> bool:
        """Update a role template permission level and persist overrides."""
        if role not in self.role_templates or feature_id not in self.features:
            return False
        try:
            lvl = PermissionLevel(str(level))
            if lvl not in self.features[feature_id].available_levels:
                return False
            self.role_templates[role][feature_id] = lvl
            self._overrides.setdefault("role_templates", {})
            self._overrides["role_templates"].setdefault(role, {})[feature_id] = lvl.value
            self._save_overrides()
            return True
        except Exception:
            return False
    
    def can_access_feature(self, user_permissions: Dict[str, PermissionLevel], 
                          feature_id: str, required_level: PermissionLevel = PermissionLevel.READ) -> bool:
        """Check if user can access a feature at the required level"""
        if feature_id not in self.features:
            return False
        
        user_level = user_permissions.get(feature_id, PermissionLevel.NONE)
        
        # Permission hierarchy: ADMIN > WRITE > READ > NONE
        level_hierarchy = {
            PermissionLevel.NONE: 0,
            PermissionLevel.READ: 1,
            PermissionLevel.WRITE: 2,
            PermissionLevel.ADMIN: 3
        }
        
        return level_hierarchy[user_level] >= level_hierarchy[required_level]
    
    def get_available_features_for_role(self, role: str) -> List[Feature]:
        """Get all features available for a specific role"""
        role_permissions = self.role_templates.get(role, {})
        available_features = []
        
        for feature_id, feature in self.features.items():
            current_level = role_permissions.get(feature_id, PermissionLevel.NONE)
            if current_level != PermissionLevel.NONE:
                available_features.append(feature)
        
        return available_features
    
    def get_requestable_features_for_user(self, current_role: str, 
                                        current_permissions: Dict[str, PermissionLevel]) -> List[Feature]:
        """Get features that a user can request access to"""
        requestable = []
        
        for feature_id, feature in self.features.items():
            current_level = current_permissions.get(feature_id, PermissionLevel.NONE)
            
            # Can request if:
            # 1. Don't have access (NONE level)
            # 2. Have lower level access and higher levels are available
            # 3. Feature allows the user's role to have higher access
            
            available_higher_levels = [
                level for level in feature.available_levels 
                if level.value != "none" and (
                    current_level == PermissionLevel.NONE or 
                    self._is_higher_level(level, current_level)
                )
            ]
            
            if available_higher_levels:
                requestable.append(feature)
        
        return requestable
    
    def _is_higher_level(self, level1: PermissionLevel, level2: PermissionLevel) -> bool:
        """Check if level1 is higher than level2"""
        hierarchy = {
            PermissionLevel.NONE: 0,
            PermissionLevel.READ: 1,
            PermissionLevel.WRITE: 2,
            PermissionLevel.ADMIN: 3
        }
        return hierarchy[level1] > hierarchy[level2]

# Global instance
enterprise_permissions = EnterprisePermissionManager()
