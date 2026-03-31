import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../App";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { toast } from "sonner";
import { Mail, ArrowLeft, CheckCircle2, Loader2, Shield, Phone, MessageCircle } from "lucide-react";

const ForgotPasswordPage = () => {
  const [mode, setMode] = useState("email"); // "email" | "phone"
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [resetMethod, setResetMethod] = useState("email");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const payload = mode === "email" ? { email } : { phone };
      const res = await api.post("/auth/forgot-password", payload);
      setResetMethod(res.data?.method || mode);
      setSubmitted(true);
      toast.success("Password reset instructions sent!");
    } catch {
      setSubmitted(true);
      setResetMethod(mode);
      toast.success("If an account exists, you will receive reset instructions.");
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

        {!submitted ? (
          <>
            <div className="flex items-center gap-2 mb-2">
              <Shield className="w-6 h-6 text-orange-600" />
              <h1 className="font-heading text-3xl font-bold text-slate-900">Reset Password</h1>
            </div>
            <p className="text-slate-500 mb-6">
              We'll send you a password reset link via {mode === "email" ? "email" : "WhatsApp"}.
            </p>

            {/* Mode Toggle */}
            <div className="flex gap-2 mb-6" data-testid="reset-mode-toggle">
              <button
                type="button"
                onClick={() => setMode("email")}
                className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-medium border transition-all ${
                  mode === "email"
                    ? "bg-orange-50 border-orange-300 text-orange-700"
                    : "bg-white border-slate-200 text-slate-500 hover:bg-slate-50"
                }`}
                data-testid="reset-via-email-btn"
              >
                <Mail className="w-4 h-4" /> Via Email
              </button>
              <button
                type="button"
                onClick={() => setMode("phone")}
                className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-medium border transition-all ${
                  mode === "phone"
                    ? "bg-green-50 border-green-300 text-green-700"
                    : "bg-white border-slate-200 text-slate-500 hover:bg-slate-50"
                }`}
                data-testid="reset-via-phone-btn"
              >
                <MessageCircle className="w-4 h-4" /> Via WhatsApp
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
              {mode === "email" ? (
                <div>
                  <Label htmlFor="email" className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    Email Address
                  </Label>
                  <div className="relative mt-1">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                    <Input
                      id="email"
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="you@company.com"
                      className="pl-10 h-12 bg-white border-slate-200 focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                      data-testid="forgot-email-input"
                      required
                    />
                  </div>
                </div>
              ) : (
                <div>
                  <Label htmlFor="phone" className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    Registered Phone Number
                  </Label>
                  <div className="relative mt-1">
                    <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                    <Input
                      id="phone"
                      type="tel"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      placeholder="+91 98765 43210"
                      className="pl-10 h-12 bg-white border-slate-200 focus:ring-2 focus:ring-green-500 focus:border-transparent"
                      data-testid="forgot-phone-input"
                      required
                    />
                  </div>
                  <p className="text-xs text-slate-400 mt-1">
                    Enter the phone number you used during WhatsApp registration
                  </p>
                </div>
              )}

              <Button
                type="submit"
                disabled={loading}
                className={`w-full h-12 font-medium ${
                  mode === "phone"
                    ? "bg-green-600 hover:bg-green-700"
                    : "bg-orange-600 hover:bg-orange-700"
                }`}
                data-testid="forgot-submit-btn"
              >
                {loading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : mode === "phone" ? (
                  "Send Reset Link via WhatsApp"
                ) : (
                  "Send Reset Instructions"
                )}
              </Button>
            </form>
          </>
        ) : (
          <div className="text-center">
            <div className={`w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-6 ${
              resetMethod === "whatsapp" ? "bg-green-100" : "bg-green-100"
            }`}>
              {resetMethod === "whatsapp" ? (
                <MessageCircle className="w-8 h-8 text-green-600" />
              ) : (
                <CheckCircle2 className="w-8 h-8 text-green-600" />
              )}
            </div>
            <h1 className="font-heading text-2xl font-bold text-slate-900 mb-2">
              {resetMethod === "whatsapp" ? "Check Your WhatsApp" : "Check Your Email"}
            </h1>
            <p className="text-slate-500 mb-6">
              {resetMethod === "whatsapp" ? (
                <>If an account exists for <strong>{phone}</strong>, you will receive a password reset link on WhatsApp.</>
              ) : (
                <>If an account exists for <strong>{email}</strong>, you will receive password reset instructions shortly.</>
              )}
            </p>
            <p className="text-sm text-slate-400 mb-8">
              The link will expire in 1 hour for security reasons.
            </p>
            <Button
              onClick={() => { setSubmitted(false); setResetMethod("email"); }}
              variant="outline"
              className="mr-3"
              data-testid="try-again-btn"
            >
              Try again
            </Button>
          </div>
        )}

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

export default ForgotPasswordPage;
