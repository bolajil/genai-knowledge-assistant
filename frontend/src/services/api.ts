/**
 * VaultMind API Client
 * Connects to existing FastAPI backend at /v1/*
 * Per TRANSFORMATION_PLAN.md Phase 6
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const DEFAULT_TENANT = process.env.NEXT_PUBLIC_TENANT_ID || "default";

// Types matching existing API models
export interface User {
  id: string;
  username: string;
  email: string;
  role: string;
  tenant_id?: string;
  departments?: Array<{ id: string; name: string; display_name: string }>;
  is_active?: boolean;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: {
    id: string;
    username: string;
    email: string;
    role: string;
  };
}

// Helper to get auth header
const getAuthHeader = (): HeadersInit => {
  const token = localStorage.getItem("auth_token");
  return token
    ? { Authorization: `Bearer ${token}`, "X-Tenant-ID": DEFAULT_TENANT }
    : { "X-Tenant-ID": DEFAULT_TENANT };
};

// API Client - connects to existing VaultMind API
export const api = {
  // ============== Auth (existing /v1/auth endpoints) ==============

  async login(username: string, password: string, tenantId: string = DEFAULT_TENANT): Promise<LoginResponse> {
    // Use existing VaultMind API endpoint (per api/v1/auth.py)
    const response = await fetch(`${API_BASE_URL}/v1/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Tenant-ID": tenantId,
      },
      body: JSON.stringify({
        username,
        password,
        tenant_id: tenantId,
      }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Login failed" }));
      throw new Error(error.detail || "Invalid username or password");
    }

    return response.json();
  },

  async getCurrentUser(): Promise<User> {
    const response = await fetch(`${API_BASE_URL}/v1/auth/me`, {
      headers: getAuthHeader(),
    });

    if (!response.ok) {
      throw new Error("Not authenticated");
    }

    return response.json();
  },

  async logout(): Promise<void> {
    try {
      await fetch(`${API_BASE_URL}/v1/auth/logout`, {
        method: "POST",
        headers: getAuthHeader(),
      });
    } finally {
      localStorage.removeItem("auth_token");
      localStorage.removeItem("user");
    }
  },

  async validateToken(): Promise<boolean> {
    try {
      const response = await fetch(`${API_BASE_URL}/v1/auth/me`, {
        headers: getAuthHeader(),
      });
      return response.ok;
    } catch {
      return false;
    }
  },

  // ============== Query (existing /v1/query endpoints) ==============

  async query(
    queryText: string,
    options: { top_k?: number; department_id?: string } = {}
  ): Promise<{ results: any[]; total: number }> {
    const response = await fetch(`${API_BASE_URL}/v1/query/search`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...getAuthHeader(),
      },
      body: JSON.stringify({
        query: queryText,
        top_k: options.top_k || 5,
        department_id: options.department_id,
      }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Query failed" }));
      throw new Error(error.detail || "Query failed");
    }

    return response.json();
  },

  // ============== Ingest (existing /v1/ingest endpoints) ==============

  async uploadDocument(
    file: File,
    options: { department_id?: string; doc_type?: string } = {}
  ): Promise<{ status: string; document_id: string }> {
    const formData = new FormData();
    formData.append("file", file);
    if (options.department_id) formData.append("department_id", options.department_id);
    if (options.doc_type) formData.append("doc_type", options.doc_type);

    const headers = getAuthHeader();
    delete (headers as any)["Content-Type"]; // Let browser set multipart boundary

    const response = await fetch(`${API_BASE_URL}/v1/ingest/upload`, {
      method: "POST",
      headers,
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Upload failed" }));
      throw new Error(error.detail || "Upload failed");
    }

    return response.json();
  },

  // ============== Admin (existing /v1/admin endpoints) ==============

  async getUsers(): Promise<{ users: User[] }> {
    const response = await fetch(`${API_BASE_URL}/v1/admin/users`, {
      headers: getAuthHeader(),
    });

    if (!response.ok) {
      throw new Error("Failed to fetch users");
    }

    return response.json();
  },

  async getDepartments(): Promise<{ departments: any[] }> {
    const response = await fetch(`${API_BASE_URL}/v1/auth/departments`, {
      headers: getAuthHeader(),
    });

    if (!response.ok) {
      throw new Error("Failed to fetch departments");
    }

    return response.json();
  },

  // ============== Health ==============

  async healthCheck(): Promise<{ status: string }> {
    const response = await fetch(`${API_BASE_URL}/health`);
    return response.json();
  },
};

export default api;
