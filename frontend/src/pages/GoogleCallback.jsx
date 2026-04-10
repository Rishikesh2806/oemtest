import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../App";
import { Loader2 } from "lucide-react";

const GoogleCallback = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [error, setError] = useState(null);

  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get("code");
      const errorParam = searchParams.get("error");

      if (errorParam) {
        setError("Google sign-in was cancelled or failed");
        setTimeout(() => navigate("/login"), 3000);
        return;
      }

      if (!code) {
        setError("No authorization code received");
        setTimeout(() => navigate("/login"), 3000);
        return;
      }

      try {
        const redirectUri = window.location.origin + "/auth/google/callback";
        
        const response = await api.post("/auth/google/callback", {
          code: code,
          redirect_uri: redirectUri
        });

        const data = response.data;

        if (data.success && data.access_token) {
          // Store token first
          localStorage.setItem("token", data.access_token);
          
          // Use full page redirect to ensure clean auth state
          // This forces checkAuth to run on fresh mount with the stored token
          let redirectPath = "/buyer/dashboard";
          const userRole = data.user.role;
          const customRole = data.user.custom_role;
          
          if (userRole === "vendor") {
            redirectPath = "/vendor/dashboard";
          } else if (userRole === "admin") {
            redirectPath = "/admin/dashboard";
          } else if (userRole === "buyer") {
            redirectPath = "/buyer/dashboard";
          } else if (userRole === "staff" || customRole) {
            if (customRole?.toLowerCase().includes("inspector")) {
              redirectPath = "/inspector/dashboard";
            } else {
              redirectPath = "/staff/dashboard";
            }
          } else if (userRole === "inspector") {
            redirectPath = "/inspector/dashboard";
          } else if (!userRole && !customRole) {
            redirectPath = "/select-role";
          }
          
          window.location.href = redirectPath;
        } else {
          throw new Error("Invalid response from server");
        }
      } catch (err) {
        console.error("Google callback error:", err);
        const errorMsg = err.response?.data?.detail || err.message || "Failed to complete sign-in";
        setError(errorMsg);
        setTimeout(() => navigate("/login"), 3000);
      }
    };

    handleCallback();
  }, [searchParams, navigate]);

  if (error) {
    return (
      <div data-testid="google-callback-error" className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-slate-900 mb-2">Sign In Failed</h2>
          <p data-testid="google-callback-error-msg" className="text-slate-500 mb-4">{error}</p>
          <p className="text-sm text-slate-400">Redirecting to login...</p>
        </div>
      </div>
    );
  }

  return (
    <div data-testid="google-callback-loading" className="min-h-screen bg-slate-50 flex items-center justify-center">
      <div className="text-center">
        <div className="w-16 h-16 bg-orange-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <Loader2 className="w-8 h-8 text-orange-600 animate-spin" />
        </div>
        <h2 className="text-xl font-semibold text-slate-900 mb-2">Completing Sign In</h2>
        <p className="text-slate-500">Please wait while we verify your account...</p>
      </div>
    </div>
  );
};

export default GoogleCallback;
