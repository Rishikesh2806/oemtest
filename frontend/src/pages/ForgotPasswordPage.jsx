import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../App";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { toast } from "sonner";
import { Mail, ArrowLeft, CheckCircle2, Loader2, Shield } from "lucide-react";

const ForgotPasswordPage = () => {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      await api.post("/auth/forgot-password", { email });
      setSubmitted(true);
      toast.success("Password reset instructions sent!");
    } catch (error) {
      // Still show success to prevent email enumeration
      setSubmitted(true);
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
            <p className="text-slate-500 mb-8">
              Enter your email address and we'll send you instructions to reset your password.
            </p>

            <form onSubmit={handleSubmit} className="space-y-6">
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

              <Button
                type="submit"
                disabled={loading}
                className="w-full h-12 bg-orange-600 hover:bg-orange-700 font-medium"
                data-testid="forgot-submit-btn"
              >
                {loading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  "Send Reset Instructions"
                )}
              </Button>
            </form>
          </>
        ) : (
          <div className="text-center">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <CheckCircle2 className="w-8 h-8 text-green-600" />
            </div>
            <h1 className="font-heading text-2xl font-bold text-slate-900 mb-2">Check Your Email</h1>
            <p className="text-slate-500 mb-6">
              If an account exists for <strong>{email}</strong>, you will receive password reset instructions shortly.
            </p>
            <p className="text-sm text-slate-400 mb-8">
              The link will expire in 1 hour for security reasons.
            </p>
            <Button
              onClick={() => setSubmitted(false)}
              variant="outline"
              className="mr-3"
            >
              Try another email
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
