import { useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useAuth } from "../App";
import { Loader2 } from "lucide-react";

const QuoteRedirect = () => {
  const { rfqId } = useParams();
  const { user, loading } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (loading) return;

    if (!user) {
      navigate(`/login?redirect=/quote/rfq/${rfqId}`, { replace: true });
      return;
    }

    if (user.role === "vendor") {
      navigate(`/vendor/rfq/${rfqId}`, { replace: true });
    } else if (user.role === "buyer") {
      navigate(`/buyer/rfq/${rfqId}`, { replace: true });
    } else if (user.role === "admin" || user.custom_role) {
      navigate(`/admin/dashboard`, { replace: true });
    } else {
      navigate(`/login?redirect=/quote/rfq/${rfqId}`, { replace: true });
    }
  }, [user, loading, rfqId, navigate]);

  return (
    <div data-testid="quote-redirect" className="min-h-screen bg-slate-50 flex items-center justify-center">
      <div className="text-center">
        <Loader2 className="w-8 h-8 text-orange-600 animate-spin mx-auto mb-4" />
        <p className="text-slate-500">Redirecting to RFQ...</p>
      </div>
    </div>
  );
};

export default QuoteRedirect;
