import { useState, useEffect } from "react";
import { useSearchParams, useNavigate, Link } from "react-router-dom";
import { api } from "../App";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Loader2, CheckCircle, XCircle, Mail } from "lucide-react";

const VerifyEmailPage = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState("verifying"); // verifying, success, error, already_verified
  const [message, setMessage] = useState("");
  const token = searchParams.get("token");

  useEffect(() => {
    if (token) {
      verifyEmail();
    } else {
      setStatus("error");
      setMessage("No verification token provided.");
    }
  }, [token]);

  const verifyEmail = async () => {
    try {
      const response = await api.post("/auth/verify-email", { token });
      if (response.data.already_verified) {
        setStatus("already_verified");
        setMessage("Your email has already been verified.");
      } else {
        setStatus("success");
        setMessage("Your email has been verified successfully!");
      }
    } catch (error) {
      setStatus("error");
      setMessage(error.response?.data?.detail || "Verification failed. The link may be invalid or expired.");
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100 flex items-center justify-center p-4">
      <Card className="w-full max-w-md" data-testid="verify-email-card">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <img src="/logo.png" alt="OEMLinker" className="w-[200px] h-[50px] object-contain" />
          </div>
          <CardTitle className="text-xl font-bold text-slate-900">
            Email Verification
          </CardTitle>
        </CardHeader>
        <CardContent className="text-center">
          {status === "verifying" && (
            <div className="py-8">
              <Loader2 className="w-16 h-16 animate-spin text-orange-600 mx-auto mb-4" />
              <p className="text-slate-600">Verifying your email address...</p>
            </div>
          )}

          {status === "success" && (
            <div className="py-8">
              <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-green-700 mb-2">Email Verified!</h3>
              <p className="text-slate-600 mb-6">{message}</p>
              <Button 
                onClick={() => navigate("/login")}
                className="bg-orange-600 hover:bg-orange-700"
                data-testid="go-to-login-btn"
              >
                Go to Login
              </Button>
            </div>
          )}

          {status === "already_verified" && (
            <div className="py-8">
              <CheckCircle className="w-16 h-16 text-blue-500 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-blue-700 mb-2">Already Verified</h3>
              <p className="text-slate-600 mb-6">{message}</p>
              <Button 
                onClick={() => navigate("/login")}
                className="bg-orange-600 hover:bg-orange-700"
              >
                Go to Login
              </Button>
            </div>
          )}

          {status === "error" && (
            <div className="py-8">
              <XCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-red-700 mb-2">Verification Failed</h3>
              <p className="text-slate-600 mb-6">{message}</p>
              <div className="space-y-3">
                <Button 
                  onClick={() => navigate("/login")}
                  className="bg-orange-600 hover:bg-orange-700 w-full"
                >
                  Go to Login
                </Button>
                <p className="text-sm text-slate-500">
                  Need a new verification link?{" "}
                  <Link to="/login" className="text-orange-600 hover:underline">
                    Login and request one
                  </Link>
                </p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default VerifyEmailPage;
