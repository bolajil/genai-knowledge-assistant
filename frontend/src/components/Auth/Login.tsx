/**
 * Login Component - Connects to existing VaultMind API
 * Per TRANSFORMATION_PLAN.md Phase 6
 * 
 * Default credentials: admin / VaultMind2025!
 */
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Shield,
  Key,
  Eye,
  EyeOff,
  LogIn,
  Building2,
  Fingerprint,
  Brain,
} from "lucide-react";
import { api } from "../../services/api";

type AuthMethod = "local" | "azure" | "okta";

export function Login() {
  const router = useRouter();
  const [authMethod, setAuthMethod] = useState<AuthMethod>("local");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [formData, setFormData] = useState({
    username: "",
    password: "",
    tenantId: "default",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      const response = await api.login(
        formData.username,
        formData.password,
        formData.tenantId
      );

      // Store auth data
      localStorage.setItem("auth_token", response.access_token);
      localStorage.setItem("user", JSON.stringify(response.user));

      // Redirect to dashboard
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSSOLogin = (provider: "azure" | "okta") => {
    // SSO redirect to existing API
    window.location.href = `/v1/auth/sso/${provider}?tenant_id=${formData.tenantId}`;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex flex-col items-center justify-center p-4">
      {/* Logo and Title */}
      <div className="text-center mb-8">
        <div className="flex items-center justify-center gap-3 mb-2">
          <Brain className="h-10 w-10 text-emerald-500" />
          <h1 className="text-3xl font-bold text-white">
            VaultMind GenAI Knowledge Assistant
          </h1>
        </div>
        <div className="flex items-center justify-center gap-2 text-gray-400">
          <Shield className="h-5 w-5 text-yellow-500" />
          <span className="text-lg">Enterprise Secure Login</span>
        </div>
        <p className="text-gray-500 text-sm mt-1">
          Huron Consulting Group — Knowledge Management Platform
        </p>
      </div>

      {/* Security Status Badges */}
      <div className="flex gap-4 mb-8 flex-wrap justify-center">
        <div className="bg-emerald-900/30 border border-emerald-700 rounded-lg px-4 py-2 flex items-center gap-2">
          <Building2 className="h-4 w-4 text-emerald-400" />
          <span className="text-emerald-400 text-sm">Active Directory</span>
        </div>
        <div className="bg-emerald-900/30 border border-emerald-700 rounded-lg px-4 py-2 flex items-center gap-2">
          <Shield className="h-4 w-4 text-emerald-400" />
          <span className="text-emerald-400 text-sm">Okta SSO</span>
        </div>
        <div className="bg-emerald-900/30 border border-emerald-700 rounded-lg px-4 py-2 flex items-center gap-2">
          <Fingerprint className="h-4 w-4 text-emerald-400" />
          <span className="text-emerald-400 text-sm">MFA Ready</span>
        </div>
      </div>

      {/* Login Form */}
      <div className="w-full max-w-md bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6">
        <div className="flex items-center gap-2 mb-6">
          <Key className="h-5 w-5 text-yellow-500" />
          <h2 className="text-white font-semibold">
            {authMethod === "local" && "Local Authentication"}
            {authMethod === "azure" && "Azure AD Authentication"}
            {authMethod === "okta" && "Okta SSO Authentication"}
          </h2>
        </div>

        {error && (
          <div className="bg-red-900/30 border border-red-700 rounded-lg px-4 py-3 mb-4 text-red-400 text-sm">
            {error}
          </div>
        )}

        {/* Auth Method Tabs */}
        <div className="flex mb-6 bg-slate-900/50 rounded-lg p-1">
          {(["local", "azure", "okta"] as AuthMethod[]).map((method) => (
            <button
              key={method}
              onClick={() => setAuthMethod(method)}
              className={`flex-1 py-2 px-3 rounded-md text-sm font-medium transition-colors ${
                authMethod === method
                  ? "bg-emerald-600 text-white"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              {method === "local" && "Local"}
              {method === "azure" && "Azure AD"}
              {method === "okta" && "Okta"}
            </button>
          ))}
        </div>

        {authMethod === "local" ? (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-gray-300 text-sm mb-2">
                Username or Email
              </label>
              <input
                type="text"
                value={formData.username}
                onChange={(e) =>
                  setFormData({ ...formData, username: e.target.value })
                }
                placeholder="admin"
                className="w-full bg-slate-900 border border-slate-600 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500"
                required
              />
            </div>

            <div>
              <label className="block text-gray-300 text-sm mb-2">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  value={formData.password}
                  onChange={(e) =>
                    setFormData({ ...formData, password: e.target.value })
                  }
                  placeholder="VaultMind2025!"
                  className="w-full bg-slate-900 border border-slate-600 rounded-lg px-4 py-3 pr-12 text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white"
                >
                  {showPassword ? (
                    <EyeOff className="h-5 w-5" />
                  ) : (
                    <Eye className="h-5 w-5" />
                  )}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-3 rounded-lg flex items-center justify-center gap-2 transition-all disabled:opacity-50"
            >
              <LogIn className="h-5 w-5" />
              {isLoading ? "Authenticating..." : "Sign In"}
            </button>
          </form>
        ) : (
          <div className="space-y-4">
            <p className="text-gray-400 text-sm">
              {authMethod === "azure"
                ? "Sign in with your Azure Active Directory account."
                : "Sign in with your Okta SSO credentials."}
            </p>
            <button
              onClick={() => handleSSOLogin(authMethod)}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 rounded-lg flex items-center justify-center gap-2"
            >
              {authMethod === "azure" ? (
                <>
                  <Building2 className="h-5 w-5" />
                  Sign in with Azure AD
                </>
              ) : (
                <>
                  <Shield className="h-5 w-5" />
                  Sign in with Okta
                </>
              )}
            </button>
          </div>
        )}

        {/* Default Credentials Info */}
        <div className="mt-6 p-3 bg-slate-900/50 rounded-lg border border-slate-700">
          <p className="text-gray-400 text-xs">
            <strong className="text-gray-300">Default Admin:</strong>{" "}
            admin / VaultMind2025!
          </p>
        </div>
      </div>

      <p className="text-gray-600 text-xs mt-8">
        © 2026 Huron Consulting Group. VaultMind Enterprise.
      </p>
    </div>
  );
}

export default Login;
