import { useState, useRef, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../App";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { toast } from "sonner";
import { Mail, ArrowLeft, CheckCircle2, Loader2, Shield, Phone, MessageCircle, KeyRound, Lock, Eye, EyeOff } from "lucide-react";

const ForgotPasswordPage = () => {
  const navigate = useNavigate();
  const [mode, setMode] = useState("email"); // "email" | "phone"
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState("input"); // "input" | "otp" | "email_sent" | "success"

  // OTP state
  const [otp, setOtp] = useState(["", "", "", "", "", ""]);
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const otpRefs = useRef([]);

  useEffect(() => {
    if (countdown > 0) {
      const t = setTimeout(() => setCountdown(c => c - 1), 1000);
      return () => clearTimeout(t);
    }
  }, [countdown]);

  const handleSend = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const payload = mode === "email" ? { email } : { phone };
      const res = await api.post("/auth/forgot-password", payload);
      if (res.data?.method === "whatsapp") {
        setStep("otp");
        setCountdown(120); // 2 min countdown
        toast.success("Recovery code sent to your WhatsApp!");
      } else {
        setStep("email_sent");
        toast.success("Password reset link sent to your email!");
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleOtpChange = (idx, val) => {
    if (val.length > 1) val = val.slice(-1);
    if (val && !/^\d$/.test(val)) return;
    const next = [...otp];
    next[idx] = val;
    setOtp(next);
    if (val && idx < 5) otpRefs.current[idx + 1]?.focus();
  };

  const handleOtpKeyDown = (idx, e) => {
    if (e.key === "Backspace" && !otp[idx] && idx > 0) {
      otpRefs.current[idx - 1]?.focus();
    }
  };

  const handleOtpPaste = (e) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
    const next = [...otp];
    for (let i = 0; i < 6; i++) next[i] = pasted[i] || "";
    setOtp(next);
    const focusIdx = Math.min(pasted.length, 5);
    otpRefs.current[focusIdx]?.focus();
  };

  const handleVerifyOtp = async (e) => {
    e.preventDefault();
    const code = otp.join("");
    if (code.length !== 6) { toast.error("Please enter the complete 6-digit code"); return; }
    if (!newPassword) { toast.error("Please enter your new password"); return; }
    if (newPassword !== confirmPassword) { toast.error("Passwords do not match"); return; }
    if (newPassword.length < 8) { toast.error("Password must be at least 8 characters"); return; }

    setLoading(true);
    try {
      await api.post("/auth/verify-reset-otp", { phone, otp: code, new_password: newPassword });
      setStep("success");
      toast.success("Password reset successfully!");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Invalid code. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    if (countdown > 0) return;
    setLoading(true);
    try {
      await api.post("/auth/forgot-password", { phone });
      setCountdown(120);
      setOtp(["", "", "", "", "", ""]);
      toast.success("New code sent!");
    } catch {
      toast.error("Failed to resend code.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center px-6 py-12">
      <div className="w-full max-w-md">
        <Link to="/" className="flex items-center gap-2 mb-8">
          <img src="/logo.png" alt="OEMLinker" className="w-[320px] h-[80px]" />
        </Link>

        {/* Step 1: Input */}
        {step === "input" && (
          <>
            <div className="flex items-center gap-2 mb-2">
              <Shield className="w-6 h-6 text-orange-600" />
              <h1 className="font-heading text-3xl font-bold text-slate-900">Reset Password</h1>
            </div>
            <p className="text-slate-500 mb-6">
              {mode === "email" ? "We'll send you a password reset link via email." : "We'll send a recovery code to your WhatsApp."}
            </p>

            <div className="flex gap-2 mb-6" data-testid="reset-mode-toggle">
              <button type="button" onClick={() => setMode("email")}
                className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-medium border transition-all ${
                  mode === "email" ? "bg-orange-50 border-orange-300 text-orange-700" : "bg-white border-slate-200 text-slate-500 hover:bg-slate-50"
                }`} data-testid="reset-via-email-btn">
                <Mail className="w-4 h-4" /> Via Email
              </button>
              <button type="button" onClick={() => setMode("phone")}
                className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-medium border transition-all ${
                  mode === "phone" ? "bg-green-50 border-green-300 text-green-700" : "bg-white border-slate-200 text-slate-500 hover:bg-slate-50"
                }`} data-testid="reset-via-phone-btn">
                <MessageCircle className="w-4 h-4" /> Via WhatsApp
              </button>
            </div>

            <form onSubmit={handleSend} className="space-y-6">
              {mode === "email" ? (
                <div>
                  <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">Email Address</Label>
                  <div className="relative mt-1">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                    <Input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@company.com"
                      className="pl-10 h-12 bg-white" type="email" required data-testid="forgot-email-input" />
                  </div>
                </div>
              ) : (
                <div>
                  <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">Registered Phone Number</Label>
                  <div className="relative mt-1">
                    <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                    <Input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+91 98765 43210"
                      className="pl-10 h-12 bg-white" type="tel" required data-testid="forgot-phone-input" />
                  </div>
                  <p className="text-xs text-slate-400 mt-1">Enter the phone number you registered with</p>
                </div>
              )}
              <Button type="submit" disabled={loading} data-testid="forgot-submit-btn"
                className={`w-full h-12 font-medium ${mode === "phone" ? "bg-green-600 hover:bg-green-700" : "bg-orange-600 hover:bg-orange-700"}`}>
                {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : mode === "phone" ? "Send Recovery Code" : "Send Reset Link"}
              </Button>
            </form>
          </>
        )}

        {/* Step 2: OTP Entry + New Password (WhatsApp flow) */}
        {step === "otp" && (
          <>
            <div className="flex items-center gap-2 mb-2">
              <KeyRound className="w-6 h-6 text-green-600" />
              <h1 className="font-heading text-2xl font-bold text-slate-900">Enter Recovery Code</h1>
            </div>
            <p className="text-slate-500 mb-1 text-sm">
              A 6-digit code was sent to <strong>{phone}</strong> via WhatsApp.
            </p>
            <p className="text-xs text-slate-400 mb-6">Code expires in 2 minutes.</p>

            <form onSubmit={handleVerifyOtp} className="space-y-5">
              {/* OTP Boxes */}
              <div>
                <Label className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2 block">Recovery Code</Label>
                <div className="flex gap-2 justify-center" data-testid="otp-input-group">
                  {otp.map((digit, i) => (
                    <input key={i} ref={el => otpRefs.current[i] = el} value={digit}
                      onChange={(e) => handleOtpChange(i, e.target.value)}
                      onKeyDown={(e) => handleOtpKeyDown(i, e)}
                      onPaste={i === 0 ? handleOtpPaste : undefined}
                      className="w-12 h-14 text-center text-2xl font-bold border-2 border-slate-200 rounded-lg focus:border-green-500 focus:ring-2 focus:ring-green-200 outline-none transition-all"
                      maxLength={1} inputMode="numeric" data-testid={`otp-digit-${i}`} />
                  ))}
                </div>
                {countdown > 0 && (
                  <p className="text-xs text-center text-slate-400 mt-2">
                    Code expires in <span className="font-mono font-bold text-green-600">{Math.floor(countdown/60)}:{(countdown%60).toString().padStart(2,'0')}</span>
                  </p>
                )}
              </div>

              {/* New Password */}
              <div>
                <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">New Password</Label>
                <div className="relative mt-1">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                  <Input value={newPassword} onChange={(e) => setNewPassword(e.target.value)} placeholder="Min 8 characters"
                    type={showPassword ? "text" : "password"} className="pl-10 pr-10 h-11 bg-white" required data-testid="new-password-input" />
                  <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400">
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>
              <div>
                <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">Confirm Password</Label>
                <Input value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} placeholder="Re-enter password"
                  type={showPassword ? "text" : "password"} className="h-11 bg-white mt-1" required data-testid="confirm-password-input" />
              </div>

              <Button type="submit" disabled={loading || otp.join("").length !== 6} data-testid="verify-otp-btn"
                className="w-full h-12 font-medium bg-green-600 hover:bg-green-700">
                {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : "Verify & Reset Password"}
              </Button>
            </form>

            <div className="mt-4 text-center">
              <button onClick={handleResend} disabled={countdown > 0 || loading}
                className={`text-sm ${countdown > 0 ? "text-slate-300 cursor-not-allowed" : "text-green-600 hover:text-green-800 underline"}`}
                data-testid="resend-otp-btn">
                {countdown > 0 ? `Resend code in ${countdown}s` : "Resend Code"}
              </button>
            </div>
          </>
        )}

        {/* Step 3: Email sent confirmation */}
        {step === "email_sent" && (
          <div className="text-center">
            <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-6">
              <Mail className="w-8 h-8 text-green-600" />
            </div>
            <h1 className="font-heading text-2xl font-bold text-slate-900 mb-2">Check Your Email</h1>
            <p className="text-slate-500 mb-6">
              If an account exists for <strong>{email}</strong>, you will receive a password reset link shortly.
            </p>
            <p className="text-sm text-slate-400 mb-8">The link will expire in 1 hour.</p>
            <Button onClick={() => { setStep("input"); }} variant="outline" data-testid="try-again-btn">Try again</Button>
          </div>
        )}

        {/* Step 4: Success (after OTP verification) */}
        {step === "success" && (
          <div className="text-center">
            <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-6">
              <CheckCircle2 className="w-8 h-8 text-green-600" />
            </div>
            <h1 className="font-heading text-2xl font-bold text-slate-900 mb-2">Password Reset!</h1>
            <p className="text-slate-500 mb-8">Your password has been changed successfully. You can now login with your new password.</p>
            <Button onClick={() => navigate("/login")} className="bg-orange-600 hover:bg-orange-700" data-testid="go-to-login-btn">
              Go to Login
            </Button>
          </div>
        )}

        <div className="mt-8 text-center">
          <Link to="/login" className="inline-flex items-center text-slate-500 hover:text-slate-700">
            <ArrowLeft className="w-4 h-4 mr-2" /> Back to Sign In
          </Link>
        </div>
      </div>
    </div>
  );
};

export default ForgotPasswordPage;
