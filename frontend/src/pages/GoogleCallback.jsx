import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth, api } from "../App";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";

const API_URL = process.env.REACT_APP_BACKEND_URL;

const GoogleCallback = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { updateUser } = useAuth();
  const [error, setError] = useState(null);
  const [processing, setProcessing] = useState(true);

  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get("code");
      const errorParam = searchParams.get("error");

      if (errorParam) {
        setError("Google sign-in was cancelled or failed");
        setProcessing(false);
        setTimeout(() => navigate("/login"), 3000);
        return;
      }

      if (!code) {
        setError("No authorization code received");
        setProcessing(false);
        setTimeout(() => navigate("/login"), 3000);
        return;
      }

      try {
        const redirectUri = window.location.origin + "/auth/google/callback";
        
        const response = await fetch(`${API_URL}/api/auth/google/callback`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            code: code,
            redirect_uri: redirectUri
          })
        });

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.detail || "Failed to complete Google sign-in");
        }

        if (data.success && data.access_token) {
          // Store token
          localStorage.setItem("token", data.access_token);
          
          // Update user context
          updateUser(data.user);
          
          toast.success(`Welcome${data.user.is_new_user ? "!" : " back!"} ${data.user.name || ""}`);
          
          // Navigate based on role or if new user
          if (!data.user.role) {
            navigate("/select-role");
          } else if (data.user.role === "vendor") {
            navigate("/vendor/dashboard");
          } else if (data.user.role === "admin" || data.user.role === "staff") {
            navigate("/admin/dashboard");
          } else if (data.user.role === "inspector") {
            navigate("/inspector/dashboard");
          } else {
            navigate("/buyer/dashboard");
          }
        } else {
          throw new Error("Invalid response from server");
        }
      } catch (err) {
        console.error("Google callback error:", err);
        setError(err.message || "Failed to complete sign-in");
        setProcessing(false);
        setTimeout(() => navigate("/login"), 3000);
      }
    };

    handleCallback();
  }, [searchParams, navigate, updateUser]);

  if (error) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-slate-900 mb-2">Sign In Failed</h2>
          <p className="text-slate-500 mb-4">{error}</p>
          <p className="text-sm text-slate-400">Redirecting to login...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center">
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
