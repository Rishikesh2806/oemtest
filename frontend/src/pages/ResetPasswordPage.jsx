import { useState, useMemo } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../App";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { toast } from "sonner";
import { 
  Lock, ArrowLeft, CheckCircle2, Loader2, Shield, 
  Eye, EyeOff, AlertCircle, XCircle 
} from "lucide-react";

// Password strength validation (same as RegisterPage)
const validatePassword = (password) => {
  const requirements = [
    { label: "At least 8 characters", met: password.length >= 8 },
    { label: "One uppercase letter", met: /[A-Z]/.test(password) },
    { label: "One lowercase letter", met: /[a-z]/.test(password) },
    { label: "One number", met: /\d/.test(password) },
    { label: "One special character (!@#$%^&*)", met: /[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/`~]/.test(password) }
  ];
  const strength = requirements.filter(r => r.met).length;
  return { requirements, strength, isValid: strength === 5 };
};

const PasswordStrengthIndicator = ({ password }) => {
  const { requirements, strength } = validatePassword(password);
  
  const getStrengthColor = () => {
    if (strength <= 2) return "bg-red-500";
    if (strength <= 3) return "bg-yellow-500";
    if (strength <= 4) return "bg-blue-500";
    return "bg-green-500";
  };
  
  const getStrengthText = () => {
    if (strength <= 2) return "Weak";
    if (strength <= 3) return "Fair";
    if (strength <= 4) return "Good";
    return "Strong";
  };

  if (!password) return null;
  
  return (
    <div className="mt-2 space-y-2">
      <div className="flex items-center gap-2">
        <div className="flex-1 h-2 bg-slate-200 rounded-full overflow-hidden">
          <div 
            className={`h-full transition-all duration-300 ${getStrengthColor()}`}
            style={{ width: `${(strength / 5) * 100}%` }}
          />
        </div>
        <span className={`text-xs font-medium ${strength === 5 ? 'text-green-600' : 'text-slate-500'}`}>
          {getStrengthText()}
        </span>
      </div>
      <div className="grid grid-cols-1 gap-1">
        {requirements.map((req, idx) => (
          <div key={idx} className="flex items-center gap-1.5 text-xs">
            {req.met ? (
              <CheckCircle2 className="w-3 h-3 text-green-500" />
            ) : (
              <AlertCircle className="w-3 h-3 text-slate-300" />
            )}
            <span className={req.met ? "text-green-600" : "text-slate-400"}>
              {req.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

const ResetPasswordPage = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get("token");
  
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState(null);
  
  const passwordValidation = useMemo(() => validatePassword(password), [password]);
  const passwordsMatch = password === confirmPassword && confirmPassword.length > 0;

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!passwordValidation.isValid) {
      toast.error("Please ensure your password meets all requirements");
      return;
    }
    
    if (!passwordsMatch) {
      toast.error("Passwords do not match");
      return;
    }
    
    setLoading(true);
    setError(null);

    try {
      await api.post("/auth/reset-password", { 
        token, 
        new_password: password 
      });
      setSuccess(true);
      toast.success("Password reset successfully!");
    } catch (err) {
      const errorMsg = err.response?.data?.detail || "Failed to reset password. The link may have expired.";
      setError(errorMsg);
      toast.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  // No token provided
  if (!token) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-md text-center">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <XCircle className="w-8 h-8 text-red-600" />
          </div>
          <h1 className="font-heading text-2xl font-bold text-slate-900 mb-2">Invalid Reset Link</h1>
          <p className="text-slate-500 mb-6">
            This password reset link is invalid or missing. Please request a new one.
          </p>
          <Link to="/forgot-password">
            <Button className="bg-orange-600 hover:bg-orange-700">
              Request New Reset Link
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  // Success state
  if (success) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-md text-center">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <CheckCircle2 className="w-8 h-8 text-green-600" />
          </div>
          <h1 className="font-heading text-2xl font-bold text-slate-900 mb-2">Password Reset Complete</h1>
          <p className="text-slate-500 mb-6">
            Your password has been successfully reset. You can now sign in with your new password.
          </p>
          <Button 
            onClick={() => navigate("/login")}
            className="bg-orange-600 hover:bg-orange-700"
          >
            Sign In Now
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center px-6 py-12">
      <div className="w-full max-w-md">
        <Link to="/" className="flex items-center gap-2 mb-8">
          <img src="/logo.png" alt="OEMLinker" className="w-[320px] h-[80px]" />
        </Link>

        <div className="flex items-center gap-2 mb-2">
          <Shield className="w-6 h-6 text-orange-600" />
          <h1 className="font-heading text-3xl font-bold text-slate-900">Create New Password</h1>
        </div>
        <p className="text-slate-500 mb-8">
          Enter your new password below. Make sure it's strong and secure.
        </p>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
            <XCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm text-red-800 font-medium">Reset Failed</p>
              <p className="text-sm text-red-600">{error}</p>
              <Link 
                to="/forgot-password" 
                className="text-sm text-red-700 underline hover:no-underline mt-1 inline-block"
              >
                Request a new reset link
              </Link>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <Label htmlFor="password" className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1">
              <Lock className="w-3 h-3" />
              New Password
            </Label>
            <div className="relative mt-1">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              <Input
                id="password"
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Create a strong password"
                className={`pl-10 pr-10 h-12 bg-white border-slate-200 focus:ring-2 focus:ring-orange-500 focus:border-transparent ${
                  password && !passwordValidation.isValid ? "border-yellow-400" : ""
                } ${password && passwordValidation.isValid ? "border-green-400" : ""}`}
                data-testid="reset-password-input"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
              >
                {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
            </div>
            <PasswordStrengthIndicator password={password} />
          </div>

          <div>
            <Label htmlFor="confirmPassword" className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Confirm New Password
            </Label>
            <div className="relative mt-1">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              <Input
                id="confirmPassword"
                type={showPassword ? "text" : "password"}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Confirm your password"
                className={`pl-10 h-12 bg-white border-slate-200 focus:ring-2 focus:ring-orange-500 focus:border-transparent ${
                  confirmPassword && !passwordsMatch ? "border-red-400" : ""
                } ${passwordsMatch ? "border-green-400" : ""}`}
                data-testid="reset-confirm-password-input"
                required
              />
              {confirmPassword && (
                <div className="absolute right-3 top-1/2 -translate-y-1/2">
                  {passwordsMatch ? (
                    <CheckCircle2 className="w-5 h-5 text-green-500" />
                  ) : (
                    <XCircle className="w-5 h-5 text-red-500" />
                  )}
                </div>
              )}
            </div>
            {confirmPassword && !passwordsMatch && (
              <p className="text-xs text-red-500 mt-1">Passwords do not match</p>
            )}
          </div>

          <Button
            type="submit"
            disabled={loading || !passwordValidation.isValid || !passwordsMatch}
            className="w-full h-12 bg-orange-600 hover:bg-orange-700 font-medium disabled:opacity-50"
            data-testid="reset-submit-btn"
          >
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              "Reset Password"
            )}
          </Button>
        </form>

        <div className="mt-8 text-center">
          <Link 
            to="/login" 
            className="inline-flex items-center text-slate-500 hover:text-slate-700"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Sign In
          </Link>
        </div>
      </div>
    </div>
  );
};

export default ResetPasswordPage;
