import { useEffect, useState, useRef, useCallback } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth, api } from "../App";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Loader2, CheckCircle, XCircle, Smartphone } from "lucide-react";

export default function MagicLogin() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { updateUser } = useAuth();
  const [status, setStatus] = useState("verifying"); // verifying, success, error
  const [error, setError] = useState("");
  const [countdown, setCountdown] = useState(3);
  
  // Use ref to track if verification has been initiated (survives StrictMode double-invoke)
  const verificationInitiated = useRef(false);
  // Track if component is actually mounted
  const isMounted = useRef(true);

  const verifyMagicLink = useCallback(async (token) => {
    try {
      const response = await api.get(`/auth/magic-link/verify/${token}`);
      
      // Only update state if component is still mounted
      if (!isMounted.current) {
        return;
      }
      
      if (response.data.success) {
        // Store the token and user data
        localStorage.setItem("token", response.data.access_token);
        localStorage.setItem("user", JSON.stringify(response.data.user));
        
        // Update auth context (use updateUser, not login which makes a POST request)
        updateUser(response.data.user);
        
        // Store redirect URL
        if (response.data.redirect_url) {
          localStorage.setItem("magic_login_redirect", response.data.redirect_url);
        }
        
        setStatus("success");
      } else {
        setStatus("error");
        setError(response.data.error || "Login failed");
      }
    } catch (err) {
      // Only update state if component is still mounted
      if (!isMounted.current) {
        return;
      }
      setStatus("error");
      setError(err.response?.data?.detail || "Invalid or expired login link. Please request a new one via WhatsApp.");
    }
  }, [updateUser]);

  useEffect(() => {
    isMounted.current = true;
    
    const token = searchParams.get("token");
    
    if (!token) {
      setStatus("error");
      setError("No login token provided. Please request a new link via WhatsApp.");
      return;
    }

    // Prevent double verification in StrictMode
    if (verificationInitiated.current) {
      return;
    }
    verificationInitiated.current = true;

    verifyMagicLink(token);

    // Cleanup function - don't abort the request, just mark as unmounted
    return () => {
      isMounted.current = false;
    };
  }, [searchParams, verifyMagicLink]);

  useEffect(() => {
    if (status === "success" && countdown > 0) {
      const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
      return () => clearTimeout(timer);
    }
    if (status === "success" && countdown === 0) {
      // Get redirect URL from localStorage or default to vendor dashboard
      const redirectUrl = localStorage.getItem("magic_login_redirect") || "/vendor/dashboard";
      localStorage.removeItem("magic_login_redirect");
      navigate(redirectUrl);
    }
  }, [status, countdown, navigate]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-orange-900 flex items-center justify-center p-4">
      <Card className="w-full max-w-md border-slate-700 bg-slate-800/80 backdrop-blur" data-testid="magic-login-card">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 w-16 h-16 rounded-full bg-orange-500/20 flex items-center justify-center">
            <Smartphone className="w-8 h-8 text-orange-400" />
          </div>
          <CardTitle className="text-2xl font-bold text-white">
            WhatsApp Login
          </CardTitle>
        </CardHeader>
        <CardContent className="text-center">
          {status === "verifying" && (
            <div className="space-y-4">
              <Loader2 className="w-12 h-12 mx-auto text-orange-400 animate-spin" />
              <p className="text-slate-300">Verifying your login link...</p>
              <p className="text-sm text-slate-500">Please wait</p>
            </div>
          )}

          {status === "success" && (
            <div className="space-y-4">
              <CheckCircle className="w-16 h-16 mx-auto text-green-400" />
              <div>
                <p className="text-xl font-semibold text-white">Login Successful!</p>
                <p className="text-slate-300 mt-2">Welcome back to OEMLinker</p>
              </div>
              <div className="bg-slate-700/50 rounded-lg p-4 mt-4">
                <p className="text-slate-400">Redirecting to dashboard in</p>
                <p className="text-3xl font-bold text-orange-400">{countdown}</p>
              </div>
              <Button
                onClick={() => navigate("/vendor/dashboard")}
                className="mt-4 bg-orange-500 hover:bg-orange-600"
                data-testid="go-to-dashboard-btn"
              >
                Go to Dashboard Now
              </Button>
            </div>
          )}

          {status === "error" && (
            <div className="space-y-4">
              <XCircle className="w-16 h-16 mx-auto text-red-400" />
              <div>
                <p className="text-xl font-semibold text-white">Login Failed</p>
                <p className="text-slate-400 mt-2">{error}</p>
              </div>
              <div className="bg-slate-700/50 rounded-lg p-4 mt-4 text-left">
                <p className="text-sm text-slate-300 font-medium mb-2">To get a new login link:</p>
                <ol className="text-sm text-slate-400 space-y-1 list-decimal list-inside">
                  <li>Open WhatsApp</li>
                  <li>Send "login" to OEMLinker</li>
                  <li>Click the new link</li>
                </ol>
              </div>
              <div className="flex gap-3 mt-4">
                <Button
                  variant="outline"
                  onClick={() => navigate("/login")}
                  className="flex-1 border-slate-600 text-slate-300 hover:bg-slate-700"
                  data-testid="manual-login-btn"
                >
                  Manual Login
                </Button>
                <Button
                  onClick={() => navigate("/")}
                  className="flex-1 bg-orange-500 hover:bg-orange-600"
                  data-testid="go-home-btn"
                >
                  Go Home
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
