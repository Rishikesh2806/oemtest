import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth, api } from "../App";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { toast } from "sonner";
import { Mail, Lock, ArrowRight, Shield, ArrowLeft, Loader2, RefreshCw } from "lucide-react";

const LoginPage = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const { login, loginWithGoogle, updateUser } = useAuth();
  const navigate = useNavigate();
  
  // 2FA state
  const [requires2FA, setRequires2FA] = useState(false);
  const [otp, setOtp] = useState("");
  const [emailHint, setEmailHint] = useState("");
  const [resending, setResending] = useState(false);

  const handleLoginSuccess = (userData) => {
    updateUser(userData);
    toast.success("Welcome back!");
    
    // Check for base role first
    if (userData.role === "vendor") {
      navigate("/vendor/dashboard");
    } else if (userData.role === "admin") {
      navigate("/admin/dashboard");
    } else if (userData.role === "buyer") {
      navigate("/buyer/dashboard");
    } else if (userData.custom_role) {
      // User has no base role but has a custom role - send to staff dashboard
      navigate("/staff/dashboard");
    } else {
      // Default fallback
      navigate("/buyer/dashboard");
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await api.post("/auth/login", { email, password });
      
      // Check if 2FA is required
      if (response.data.requires_2fa) {
        setRequires2FA(true);
        setEmailHint(response.data.email_hint);
        toast.info("Verification code sent to your email");
        setLoading(false);
        return;
      }
      
      // Normal login flow - store token and update auth state
      const { access_token, user } = response.data;
      localStorage.setItem("token", access_token);
      localStorage.setItem("user", JSON.stringify(user));
      
      handleLoginSuccess(user);
    } catch (error) {
      toast.error(error.response?.data?.detail || "Invalid credentials");
    } finally {
      setLoading(false);
    }
  };

  const handleOTPSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await api.post("/auth/verify-otp", { 
        email, 
        password, 
        otp 
      });
      
      const { access_token, user } = response.data;
      localStorage.setItem("token", access_token);
      localStorage.setItem("user", JSON.stringify(user));
      
      handleLoginSuccess(user);
    } catch (error) {
      toast.error(error.response?.data?.detail || "Invalid verification code");
    } finally {
      setLoading(false);
    }
  };

  const handleResendOTP = async () => {
    setResending(true);
    try {
      await api.post("/auth/resend-otp", { email });
      toast.success("New verification code sent!");
    } catch (error) {
      toast.error("Failed to resend code. Please try again.");
    } finally {
      setResending(false);
    }
  };

  const handleBackToLogin = () => {
    setRequires2FA(false);
    setOtp("");
    setPassword("");
  };

  // 2FA Verification Screen
  if (requires2FA) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-md">
          <Link to="/" className="flex items-center gap-2 mb-8">
            <img src="/logo.png" alt="OEMLinker" className="w-[320px] h-[80px]" />
          </Link>

          <div className="flex items-center gap-2 mb-2">
            <Shield className="w-6 h-6 text-orange-600" />
            <h1 className="font-heading text-3xl font-bold text-slate-900">Verify Your Identity</h1>
          </div>
          <p className="text-slate-500 mb-2">
            We sent a verification code to <strong>{emailHint}</strong>
          </p>
          <p className="text-sm text-slate-400 mb-8">
            Enter the 6-digit code to complete sign in
          </p>

          <form onSubmit={handleOTPSubmit} className="space-y-6">
            <div>
              <Label htmlFor="otp" className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Verification Code
              </Label>
              <Input
                id="otp"
                type="text"
                value={otp}
                onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                placeholder="000000"
                className="h-14 text-center text-2xl font-mono tracking-[0.5em] bg-white border-slate-200 focus:ring-2 focus:ring-orange-500"
                data-testid="otp-input"
                required
                maxLength={6}
              />
            </div>

            <Button
              type="submit"
              disabled={loading || otp.length !== 6}
              className="w-full h-12 bg-orange-600 hover:bg-orange-700 font-medium disabled:opacity-50"
              data-testid="verify-otp-btn"
            >
              {loading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <>Verify & Sign In <ArrowRight className="ml-2 w-4 h-4" /></>
              )}
            </Button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-slate-500 text-sm mb-3">Didn't receive the code?</p>
            <Button
              type="button"
              variant="outline"
              onClick={handleResendOTP}
              disabled={resending}
              className="mr-3"
            >
              {resending ? (
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
              ) : (
                <RefreshCw className="w-4 h-4 mr-2" />
              )}
              Resend Code
            </Button>
          </div>

          <div className="mt-8 text-center">
            <button
              onClick={handleBackToLogin}
              className="inline-flex items-center text-slate-500 hover:text-slate-700"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Sign In
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Normal Login Screen
  return (
    <div className="min-h-screen bg-slate-50 flex">
      {/* Left Panel - Form */}
      <div className="flex-1 flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-md">
          <Link to="/" className="flex items-center gap-2 mb-8">
            <img src="/logo.png" alt="OEMLinker" className="w-[320px] h-[80px]" />
          </Link>

          <h1 className="font-heading text-3xl font-bold text-slate-900 mb-2">Welcome back</h1>
          <p className="text-slate-500 mb-8">Sign in to your account to continue</p>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <Label htmlFor="email" className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Email or Phone Number
              </Label>
              <div className="relative mt-1">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                <Input
                  id="email"
                  type="text"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@company.com or 9876543210"
                  className="pl-10 h-12 bg-white border-slate-200 focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                  data-testid="login-email-input"
                  required
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between">
                <Label htmlFor="password" className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  Password
                </Label>
                <Link 
                  to="/forgot-password" 
                  className="text-xs text-orange-600 hover:text-orange-700 font-medium"
                  data-testid="forgot-password-link"
                >
                  Forgot password?
                </Link>
              </div>
              <div className="relative mt-1">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                <Input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="pl-10 h-12 bg-white border-slate-200 focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                  data-testid="login-password-input"
                  required
                />
              </div>
            </div>

            <Button
              type="submit"
              disabled={loading}
              className="w-full h-12 bg-slate-900 hover:bg-slate-800 font-medium"
              data-testid="login-submit-btn"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                <>Sign In <ArrowRight className="ml-2 w-4 h-4" /></>
              )}
            </Button>
          </form>

          <div className="relative my-8">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-slate-200" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-4 bg-slate-50 text-slate-500">Or continue with</span>
            </div>
          </div>

          <Button
            type="button"
            variant="outline"
            onClick={loginWithGoogle}
            className="w-full h-12 border-slate-200 hover:bg-slate-100"
            data-testid="google-login-btn"
          >
            <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Sign in with Google
          </Button>

          <p className="mt-8 text-center text-slate-500">
            Don't have an account?{" "}
            <Link to="/register" className="text-orange-600 hover:text-orange-700 font-medium">
              Create account
            </Link>
          </p>
        </div>
      </div>

      {/* Right Panel - Image */}
      <div className="hidden lg:block lg:w-1/2 relative">
        <div 
          className="absolute inset-0 bg-cover bg-center"
          style={{ backgroundImage: `url(https://images.pexels.com/photos/10406128/pexels-photo-10406128.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940)` }}
        />
        <div className="absolute inset-0 bg-slate-900/60" />
        <div className="absolute inset-0 flex items-end p-12">
          <div className="text-white">
            <p className="text-orange-400 font-medium uppercase tracking-wider mb-2">Trusted Platform</p>
            <h2 className="font-heading text-3xl font-bold mb-4">Precision Manufacturing Meets Intelligence</h2>
            <p className="text-slate-300">Join the network of manufacturers and buyers transforming the manufacturing supply chain.</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
