"""
VaultMind GenAI Knowledge Assistant - Tenant Isolation Tests
Critical tests for Phase 2 multi-tenant foundation

These tests prove: "HR can't see Finance documents"
This is the Huron trust signal.
"""

import pytest
import uuid
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.tenant_vector_namespace import (
    TenantNamespaceManager,
    TenantContext,
    TenantAwareVectorStore,
    get_namespace_manager
)


class TestTenantNamespaceManager:
    """Test namespace naming and parsing"""
    
    def setup_method(self):
        self.ns = TenantNamespaceManager()
    
    def test_collection_name_format(self):
        """Collection names follow vm_{tenant}_{dept}_{type} pattern"""
        name = self.ns.get_collection_name(
            tenant_id="huron",
            department_id="clinical",
            doc_type="policies"
        )
        assert name == "vm_huron_clinical_policies"
    
    def test_collection_name_sanitization(self):
        """Special characters are sanitized"""
        name = self.ns.get_collection_name(
            tenant_id="Huron Consulting",
            department_id="Human Resources",
            doc_type="Employee Policies"
        )
        assert " " not in name
        assert name.islower() or "_" in name
        assert name.startswith("vm_")
    
    def test_collection_name_max_length(self):
        """Collection names are truncated to max length"""
        name = self.ns.get_collection_name(
            tenant_id="very_long_tenant_name_that_exceeds_normal_limits",
            department_id="very_long_department_name_here",
            doc_type="very_long_document_type_name"
        )
        assert len(name) <= 45  # Pinecone limit
    
    def test_parse_collection_name(self):
        """Collection names can be parsed back to components"""
        name = "vm_huron_clinical_policies"
        parsed = self.ns.parse_collection_name(name)
        
        assert parsed is not None
        assert parsed['tenant_id'] == 'huron'
        assert parsed['department_id'] == 'clinical'
        assert parsed['doc_type'] == 'policies'
    
    def test_tenant_pattern_match(self):
        """Tenant patterns match all tenant collections"""
        pattern = self.ns.get_tenant_collections_pattern("huron")
        
        import re
        assert re.match(pattern, "vm_huron_clinical_policies")
        assert re.match(pattern, "vm_huron_finance_contracts")
        assert re.match(pattern, "vm_huron_hr_procedures")
        assert not re.match(pattern, "vm_other_clinical_policies")


class TestTenantContext:
    """Test tenant context creation and properties"""
    
    def test_context_with_single_department(self):
        """Context with single department sets allowed_department_ids"""
        ctx = TenantContext(
            tenant_id="huron",
            tenant_name="Huron Consulting",
            department_id="clinical",
            department_name="Clinical"
        )
        
        assert ctx.tenant_id == "huron"
        assert ctx.department_id == "clinical"
        assert "clinical" in ctx.allowed_department_ids
    
    def test_context_with_multiple_departments(self):
        """Context can have multiple allowed departments"""
        ctx = TenantContext(
            tenant_id="huron",
            tenant_name="Huron Consulting",
            department_id="clinical",
            allowed_department_ids=["clinical", "operations"]
        )
        
        assert len(ctx.allowed_department_ids) == 2
        assert "clinical" in ctx.allowed_department_ids
        assert "operations" in ctx.allowed_department_ids


class TestDepartmentIsolation:
    """
    CRITICAL TESTS: Prove department isolation works.
    These are the "Huron trust signal" tests.
    """
    
    def setup_method(self):
        self.ns = TenantNamespaceManager()
        
        # HR user context
        self.hr_user = TenantContext(
            tenant_id="huron",
            tenant_name="Huron Consulting",
            department_id="hr",
            department_name="Human Resources",
            user_id="hr_user_1",
            allowed_department_ids=["hr"]
        )
        
        # Finance user context
        self.finance_user = TenantContext(
            tenant_id="huron",
            tenant_name="Huron Consulting",
            department_id="finance",
            department_name="Finance",
            user_id="finance_user_1",
            allowed_department_ids=["finance"]
        )
        
        # Admin user context (can see all)
        self.admin_user = TenantContext(
            tenant_id="huron",
            tenant_name="Huron Consulting",
            department_id="hr",
            department_name="Human Resources",
            user_id="admin_1",
            allowed_department_ids=["hr", "finance", "clinical", "legal", "operations"]
        )
        
        # Different tenant user
        self.other_tenant_user = TenantContext(
            tenant_id="acme",
            tenant_name="Acme Corp",
            department_id="hr",
            department_name="Human Resources",
            user_id="acme_hr_1",
            allowed_department_ids=["hr"]
        )
    
    def test_hr_cannot_see_finance_collection(self):
        """HR user gets HR collection, not Finance"""
        hr_collection = self.ns.get_collection_name(
            tenant_id=self.hr_user.tenant_id,
            department_id=self.hr_user.department_id,
            doc_type="policies"
        )
        finance_collection = self.ns.get_collection_name(
            tenant_id=self.finance_user.tenant_id,
            department_id=self.finance_user.department_id,
            doc_type="policies"
        )
        
        # Collections should be different
        assert hr_collection != finance_collection
        assert "hr" in hr_collection
        assert "finance" in finance_collection
    
    def test_department_filter_restricts_access(self):
        """Department filter only includes user's departments"""
        hr_filter = self.ns.build_department_filter(self.hr_user, include_public=False)
        
        # Must match tenant
        assert hr_filter["tenant_id"]["$eq"] == "huron"
        
        # Must match HR department
        assert "department_id" in hr_filter
        assert self.hr_user.department_id in hr_filter["department_id"]["$in"]
        
        # Should NOT include finance
        assert "finance" not in hr_filter["department_id"]["$in"]
    
    def test_tenant_isolation_across_organizations(self):
        """Different tenants have completely separate collections"""
        huron_collection = self.ns.get_collection_name(
            tenant_id=self.hr_user.tenant_id,
            department_id="hr",
            doc_type="policies"
        )
        acme_collection = self.ns.get_collection_name(
            tenant_id=self.other_tenant_user.tenant_id,
            department_id="hr",
            doc_type="policies"
        )
        
        # Collections must be different even with same department
        assert huron_collection != acme_collection
        assert "huron" in huron_collection
        assert "acme" in acme_collection
    
    def test_tenant_filter_prevents_cross_tenant_access(self):
        """Tenant filter prevents access to other tenant's data"""
        huron_filter = self.ns.build_department_filter(self.hr_user)
        acme_filter = self.ns.build_department_filter(self.other_tenant_user)
        
        # Filters should specify different tenants
        assert huron_filter["tenant_id"]["$eq"] == "huron"
        assert acme_filter["tenant_id"]["$eq"] == "acme"
    
    def test_public_documents_visible_across_departments(self):
        """Public documents should be visible to all departments"""
        hr_filter = self.ns.build_department_filter(self.hr_user, include_public=True)
        
        # Should have $or clause allowing public OR department match
        assert "$or" in hr_filter
        
        # One clause should be public sensitivity
        has_public_clause = any(
            clause.get("sensitivity_level", {}).get("$eq") == "public"
            for clause in hr_filter["$or"]
        )
        assert has_public_clause
    
    def test_admin_can_see_all_departments(self):
        """Admin user filter includes all departments"""
        admin_filter = self.ns.build_department_filter(self.admin_user, include_public=False)
        
        # Should include all departments
        assert "department_id" in admin_filter
        dept_list = admin_filter["department_id"]["$in"]
        assert "hr" in dept_list
        assert "finance" in dept_list
        assert "clinical" in dept_list


class TestMetadataIsolation:
    """Test that metadata properly tags documents for isolation"""
    
    def setup_method(self):
        self.ns = TenantNamespaceManager()
        self.ctx = TenantContext(
            tenant_id="huron",
            tenant_name="Huron Consulting",
            department_id="clinical",
            department_name="Clinical",
            user_id="doc_uploader_1",
            sensitivity_filter="confidential"
        )
    
    def test_metadata_includes_tenant_id(self):
        """Metadata includes tenant_id for filtering"""
        meta = self.ns.build_metadata(self.ctx)
        assert meta["tenant_id"] == "huron"
    
    def test_metadata_includes_department_id(self):
        """Metadata includes department_id for filtering"""
        meta = self.ns.build_metadata(self.ctx)
        assert meta["department_id"] == "clinical"
    
    def test_metadata_includes_uploaded_by(self):
        """Metadata includes user who uploaded for audit"""
        meta = self.ns.build_metadata(self.ctx)
        assert meta["uploaded_by"] == "doc_uploader_1"
    
    def test_metadata_includes_sensitivity(self):
        """Metadata includes sensitivity level"""
        meta = self.ns.build_metadata(self.ctx)
        assert meta["sensitivity_level"] == "confidential"
    
    def test_metadata_includes_timestamp(self):
        """Metadata includes ingestion timestamp"""
        meta = self.ns.build_metadata(self.ctx)
        assert "ingested_at" in meta
        # Should be ISO format
        datetime.fromisoformat(meta["ingested_at"])


class TestWeaviateFilterGeneration:
    """Test Weaviate-specific filter generation"""
    
    def setup_method(self):
        self.ns = TenantNamespaceManager()
        self.ctx = TenantContext(
            tenant_id="huron",
            tenant_name="Huron Consulting",
            department_id="clinical",
            allowed_department_ids=["clinical", "operations"]
        )
    
    def test_weaviate_filter_returns_filter_object(self):
        """Weaviate filter returns proper Filter object"""
        try:
            from weaviate.classes.query import Filter
            filter_obj = self.ns.build_weaviate_filter(self.ctx)
            assert filter_obj is not None
        except ImportError:
            pytest.skip("Weaviate not installed")


class TestPineconeFilterGeneration:
    """Test Pinecone-specific filter generation"""
    
    def setup_method(self):
        self.ns = TenantNamespaceManager()
        self.ctx = TenantContext(
            tenant_id="huron",
            tenant_name="Huron Consulting",
            department_id="finance",
            allowed_department_ids=["finance"]
        )
    
    def test_pinecone_filter_format(self):
        """Pinecone filter uses correct dict format"""
        filter_dict = self.ns.build_pinecone_filter(self.ctx, include_public=False)
        
        # Should have tenant_id with $eq
        assert "tenant_id" in filter_dict
        assert filter_dict["tenant_id"]["$eq"] == "huron"
        
        # Should have department_id with $in
        assert "department_id" in filter_dict
        assert filter_dict["department_id"]["$in"] == ["finance"]
    
    def test_pinecone_filter_with_public(self):
        """Pinecone filter includes public documents"""
        filter_dict = self.ns.build_pinecone_filter(self.ctx, include_public=True)
        
        # Should have $or clause
        assert "$or" in filter_dict


class TestMockVectorStoreIntegration:
    """Integration test with mock vector store"""
    
    def setup_method(self):
        self.ns = TenantNamespaceManager()
        
        # Mock vector store
        self.mock_store = MockVectorStore()
        self.tenant_store = TenantAwareVectorStore(self.mock_store, self.ns)
        
        # Contexts
        self.hr_ctx = TenantContext(
            tenant_id="huron",
            tenant_name="Huron Consulting",
            department_id="hr",
            user_id="hr_user"
        )
        self.finance_ctx = TenantContext(
            tenant_id="huron",
            tenant_name="Huron Consulting",
            department_id="finance",
            user_id="finance_user"
        )
    
    def test_scoped_collection_names_differ(self):
        """Different departments get different collection names"""
        hr_collection = self.tenant_store.get_scoped_collection(self.hr_ctx)
        finance_collection = self.tenant_store.get_scoped_collection(self.finance_ctx)
        
        assert hr_collection != finance_collection
        assert "hr" in hr_collection
        assert "finance" in finance_collection


class MockVectorStore:
    """Mock vector store for testing"""
    
    def __init__(self):
        self.documents = {}
    
    def add_documents(self, collection: str, docs: list) -> bool:
        if collection not in self.documents:
            self.documents[collection] = []
        self.documents[collection].extend(docs)
        return True
    
    def search(self, collection: str, query: str, limit: int = 10) -> list:
        if collection not in self.documents:
            return []
        # Return all docs (filtering handled by wrapper)
        return self.documents[collection][:limit]


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
