"""
VaultMind GenAI Knowledge Assistant - Tenant-Aware Vector Namespace
Multi-tenant isolation for Weaviate and Pinecone vector stores

Phase 2: Multi-Tenant Foundation
"""

import re
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class TenantContext:
    """Context for tenant-scoped operations"""
    tenant_id: str
    tenant_name: str
    department_id: Optional[str] = None
    department_name: Optional[str] = None
    user_id: Optional[str] = None
    allowed_department_ids: List[str] = None
    sensitivity_filter: str = "internal"  # public, internal, confidential, restricted
    
    def __post_init__(self):
        if self.allowed_department_ids is None:
            self.allowed_department_ids = []
            if self.department_id:
                self.allowed_department_ids = [self.department_id]


class TenantNamespaceManager:
    """
    Manages tenant-isolated namespaces for vector stores.
    Provides consistent naming and filtering across Weaviate, Pinecone, etc.
    """
    
    # Collection/Index naming pattern: {tenant}_{dept}_{type}
    # Max lengths: Weaviate=128, Pinecone=45
    MAX_NAME_LENGTH = 45  # Use Pinecone limit (most restrictive)
    
    def __init__(self):
        self._name_cache = {}
    
    @staticmethod
    def sanitize_name(name: str, max_length: int = 45) -> str:
        """
        Sanitize name for use in collection/index names.
        - Lowercase
        - Replace spaces/special chars with underscores
        - Remove consecutive underscores
        - Truncate to max length
        """
        # Lowercase and replace non-alphanumeric with underscore
        sanitized = re.sub(r'[^a-z0-9]', '_', name.lower())
        # Remove consecutive underscores
        sanitized = re.sub(r'_+', '_', sanitized)
        # Remove leading/trailing underscores
        sanitized = sanitized.strip('_')
        # Truncate
        return sanitized[:max_length]
    
    def get_collection_name(
        self,
        tenant_id: str,
        department_id: str,
        doc_type: str = "general"
    ) -> str:
        """
        Generate a tenant/department-scoped collection name.
        
        Pattern: vm_{tenant}_{dept}_{type}
        Example: vm_huron_clinical_policies
        
        Args:
            tenant_id: Tenant identifier
            department_id: Department identifier
            doc_type: Document type (policies, contracts, procedures, general)
            
        Returns:
            Sanitized collection name
        """
        cache_key = f"{tenant_id}:{department_id}:{doc_type}"
        if cache_key in self._name_cache:
            return self._name_cache[cache_key]
        
        # Build name components
        tenant_part = self.sanitize_name(tenant_id, 10)
        dept_part = self.sanitize_name(department_id, 10)
        type_part = self.sanitize_name(doc_type, 10)
        
        # Combine with prefix
        name = f"vm_{tenant_part}_{dept_part}_{type_part}"
        
        # Ensure within limits
        name = name[:self.MAX_NAME_LENGTH]
        
        self._name_cache[cache_key] = name
        return name
    
    def get_tenant_collections_pattern(self, tenant_id: str) -> str:
        """Get regex pattern to match all collections for a tenant"""
        tenant_part = self.sanitize_name(tenant_id, 10)
        return f"^vm_{tenant_part}_.*"
    
    def get_department_collections_pattern(
        self, 
        tenant_id: str, 
        department_id: str
    ) -> str:
        """Get regex pattern to match all collections for a department"""
        tenant_part = self.sanitize_name(tenant_id, 10)
        dept_part = self.sanitize_name(department_id, 10)
        return f"^vm_{tenant_part}_{dept_part}_.*"
    
    def parse_collection_name(self, name: str) -> Optional[Dict[str, str]]:
        """
        Parse a collection name to extract tenant/department/type.
        
        Returns:
            Dict with tenant_id, department_id, doc_type or None if invalid
        """
        pattern = r'^vm_([^_]+)_([^_]+)_(.+)$'
        match = re.match(pattern, name)
        if match:
            return {
                'tenant_id': match.group(1),
                'department_id': match.group(2),
                'doc_type': match.group(3)
            }
        return None
    
    def build_metadata(
        self,
        context: TenantContext,
        source: str = "",
        source_type: str = "document",
        additional_metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Build tenant-scoped metadata for document storage.
        
        Args:
            context: Tenant context
            source: Document source path/url
            source_type: Type of source
            additional_metadata: Additional metadata to include
            
        Returns:
            Complete metadata dict with tenant isolation fields
        """
        metadata = {
            # Tenant isolation fields (required for filtering)
            "tenant_id": context.tenant_id,
            "department_id": context.department_id or "",
            "uploaded_by": context.user_id or "",
            "sensitivity_level": context.sensitivity_filter,
            
            # Standard fields
            "source": source,
            "source_type": source_type,
            "ingested_at": datetime.utcnow().isoformat(),
            
            # Tenant context
            "tenant_name": context.tenant_name,
            "department_name": context.department_name or "",
        }
        
        # Add additional metadata
        if additional_metadata:
            for key, value in additional_metadata.items():
                if key not in metadata:  # Don't override core fields
                    metadata[key] = value
        
        return metadata
    
    def build_department_filter(
        self,
        context: TenantContext,
        include_public: bool = True
    ) -> Dict[str, Any]:
        """
        Build filter criteria for department-scoped queries.
        
        Args:
            context: Tenant context with allowed departments
            include_public: Whether to include public documents
            
        Returns:
            Filter dict compatible with Weaviate/Pinecone
        """
        # Base filter: must match tenant
        filters = {
            "tenant_id": {"$eq": context.tenant_id}
        }
        
        # Department filter
        if context.allowed_department_ids:
            dept_filter = {"department_id": {"$in": context.allowed_department_ids}}
            
            if include_public:
                # Include public documents OR documents from allowed departments
                filters["$or"] = [
                    {"sensitivity_level": {"$eq": "public"}},
                    dept_filter
                ]
            else:
                filters.update(dept_filter)
        
        # Sensitivity filter (user can only see up to their level)
        sensitivity_levels = ["public"]
        if context.sensitivity_filter in ["internal", "confidential", "restricted"]:
            sensitivity_levels.append("internal")
        if context.sensitivity_filter in ["confidential", "restricted"]:
            sensitivity_levels.append("confidential")
        if context.sensitivity_filter == "restricted":
            sensitivity_levels.append("restricted")
        
        filters["sensitivity_level"] = {"$in": sensitivity_levels}
        
        return filters
    
    def build_weaviate_filter(
        self,
        context: TenantContext,
        include_public: bool = True
    ) -> Any:
        """
        Build Weaviate-specific filter for department-scoped queries.
        
        Args:
            context: Tenant context
            include_public: Whether to include public documents
            
        Returns:
            Weaviate Filter object
        """
        try:
            from weaviate.classes.query import Filter
            
            # Tenant filter (required)
            tenant_filter = Filter.by_property("tenant_id").equal(context.tenant_id)
            
            # Department filter
            if context.allowed_department_ids:
                # Build OR filter for allowed departments
                dept_filters = []
                for dept_id in context.allowed_department_ids:
                    dept_filters.append(
                        Filter.by_property("department_id").equal(dept_id)
                    )
                
                if len(dept_filters) == 1:
                    dept_filter = dept_filters[0]
                else:
                    # Combine with OR
                    dept_filter = dept_filters[0]
                    for f in dept_filters[1:]:
                        dept_filter = dept_filter | f
                
                if include_public:
                    public_filter = Filter.by_property("sensitivity_level").equal("public")
                    dept_filter = dept_filter | public_filter
                
                return tenant_filter & dept_filter
            
            return tenant_filter
            
        except ImportError:
            logger.warning("Weaviate not available, returning None filter")
            return None
    
    def build_pinecone_filter(
        self,
        context: TenantContext,
        include_public: bool = True
    ) -> Dict[str, Any]:
        """
        Build Pinecone-specific filter for department-scoped queries.
        
        Args:
            context: Tenant context
            include_public: Whether to include public documents
            
        Returns:
            Pinecone filter dict
        """
        # Pinecone uses simpler filter syntax
        filter_dict = {
            "tenant_id": {"$eq": context.tenant_id}
        }
        
        if context.allowed_department_ids:
            if include_public:
                filter_dict["$or"] = [
                    {"sensitivity_level": {"$eq": "public"}},
                    {"department_id": {"$in": context.allowed_department_ids}}
                ]
            else:
                filter_dict["department_id"] = {"$in": context.allowed_department_ids}
        
        return filter_dict


class TenantAwareVectorStore:
    """
    Wrapper that adds tenant isolation to any vector store.
    Works with WeaviateManager, Pinecone adapter, etc.
    """
    
    def __init__(self, vector_store, namespace_manager: TenantNamespaceManager = None):
        """
        Initialize with a vector store backend.
        
        Args:
            vector_store: The underlying vector store (WeaviateManager, etc.)
            namespace_manager: Optional namespace manager instance
        """
        self.store = vector_store
        self.ns = namespace_manager or TenantNamespaceManager()
    
    def get_scoped_collection(
        self,
        context: TenantContext,
        doc_type: str = "general"
    ) -> str:
        """Get tenant/department-scoped collection name"""
        return self.ns.get_collection_name(
            tenant_id=context.tenant_id,
            department_id=context.department_id or "shared",
            doc_type=doc_type
        )
    
    def add_documents(
        self,
        context: TenantContext,
        documents: List[Dict[str, Any]],
        doc_type: str = "general"
    ) -> bool:
        """
        Add documents with tenant isolation.
        
        Args:
            context: Tenant context
            documents: List of documents with 'content' and optional 'metadata'
            doc_type: Document type for collection routing
            
        Returns:
            True if successful
        """
        collection_name = self.get_scoped_collection(context, doc_type)
        
        # Enhance documents with tenant metadata
        enhanced_docs = []
        for doc in documents:
            enhanced_meta = self.ns.build_metadata(
                context=context,
                source=doc.get('source', ''),
                source_type=doc.get('source_type', 'document'),
                additional_metadata=doc.get('metadata', {})
            )
            enhanced_docs.append({
                'content': doc.get('content', ''),
                'metadata': enhanced_meta
            })
        
        # Use underlying store's add method
        if hasattr(self.store, 'add_documents'):
            return self.store.add_documents(collection_name, enhanced_docs)
        elif hasattr(self.store, 'add_documents_batch'):
            return self.store.add_documents_batch(collection_name, enhanced_docs)
        else:
            logger.error("Vector store does not support document addition")
            return False
    
    def search(
        self,
        context: TenantContext,
        query: str,
        doc_type: str = "general",
        limit: int = 10,
        include_public: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search with tenant isolation.
        
        Args:
            context: Tenant context (provides department filter)
            query: Search query
            doc_type: Document type for collection routing
            limit: Max results
            include_public: Include public documents from other departments
            
        Returns:
            List of search results with tenant-filtered content
        """
        collection_name = self.get_scoped_collection(context, doc_type)
        
        # Build filter based on store type
        store_type = type(self.store).__name__.lower()
        
        if 'weaviate' in store_type:
            filter_obj = self.ns.build_weaviate_filter(context, include_public)
            if hasattr(self.store, 'similarity_search_with_filter'):
                return self.store.similarity_search_with_filter(
                    collection_name, query, filter_obj, limit
                )
            elif hasattr(self.store, 'similarity_search'):
                # Fallback: search without filter and filter in Python
                results = self.store.similarity_search(collection_name, query, limit * 3)
                return self._filter_results(results, context, include_public)[:limit]
        
        elif 'pinecone' in store_type:
            filter_dict = self.ns.build_pinecone_filter(context, include_public)
            if hasattr(self.store, 'search'):
                return self.store.search(
                    collection_name, query, limit, filter=filter_dict
                )
        
        # Generic fallback
        if hasattr(self.store, 'search'):
            results = self.store.search(collection_name, query, limit * 3)
            return self._filter_results(results, context, include_public)[:limit]
        
        logger.warning(f"Unknown store type: {store_type}")
        return []
    
    def _filter_results(
        self,
        results: List[Dict[str, Any]],
        context: TenantContext,
        include_public: bool
    ) -> List[Dict[str, Any]]:
        """Filter results by tenant/department in Python (fallback)"""
        filtered = []
        for result in results:
            meta = result.get('metadata', {})
            
            # Must match tenant
            if meta.get('tenant_id') != context.tenant_id:
                continue
            
            # Check department access
            dept_id = meta.get('department_id', '')
            sensitivity = meta.get('sensitivity_level', 'internal')
            
            if sensitivity == 'public' and include_public:
                filtered.append(result)
            elif dept_id in context.allowed_department_ids:
                filtered.append(result)
        
        return filtered


# Singleton instance
_namespace_manager = None

def get_namespace_manager() -> TenantNamespaceManager:
    """Get singleton namespace manager"""
    global _namespace_manager
    if _namespace_manager is None:
        _namespace_manager = TenantNamespaceManager()
    return _namespace_manager
