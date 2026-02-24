import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useAuth, api } from "../App";
import DashboardLayout from "../components/layout/DashboardLayout";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { toast } from "sonner";
import { 
  DollarSign, Clock, FileText, Loader2, CheckCircle2, XCircle
} from "lucide-react";

const QuotesList = () => {
  const [quotes, setQuotes] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchQuotes();
  }, []);

  const fetchQuotes = async () => {
    try {
      const response = await api.get("/quotes/vendor");
      setQuotes(response.data);
    } catch (error) {
      toast.error("Failed to load quotes");
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    const statusMap = {
      pending: "status-pending",
      accepted: "status-completed",
      rejected: "status-cancelled",
      expired: "status-cancelled"
    };
    return statusMap[status] || "status-pending";
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case "accepted": return <CheckCircle2 className="w-4 h-4 text-green-600" />;
      case "rejected": return <XCircle className="w-4 h-4 text-red-600" />;
      default: return <Clock className="w-4 h-4 text-amber-600" />;
    }
  };

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-orange-600" />
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-6" data-testid="quotes-list-page">
        <div>
          <h1 className="font-heading text-2xl font-bold text-slate-900">My Quotes</h1>
          <p className="text-slate-500">Track all your submitted quotations</p>
        </div>

        {quotes.length > 0 ? (
          <div className="space-y-4">
            {quotes.map((quote) => (
              <Card key={quote.quote_id} className="border-slate-200">
                <CardContent className="py-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="w-12 h-12 bg-slate-100 rounded-lg flex items-center justify-center">
                        <FileText className="w-6 h-6 text-slate-500" />
                      </div>
                      <div>
                        <Link 
                          to={`/vendor/rfq/${quote.rfq_id}`}
                          className="font-medium text-slate-900 hover:text-orange-600"
                        >
                          RFQ #{quote.rfq_id.slice(-8)}
                        </Link>
                        <p className="text-sm text-slate-500">
                          Submitted {new Date(quote.created_at).toLocaleDateString()}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-6">
                      <div className="text-right">
                        <div className="flex items-center gap-1 text-lg font-bold text-slate-900">
                          <DollarSign className="w-4 h-4" />
                          {quote.price?.toFixed(2)}
                        </div>
                        <div className="flex items-center gap-1 text-sm text-slate-500">
                          <Clock className="w-3 h-3" /> {quote.lead_time_days} days
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        {getStatusIcon(quote.status)}
                        <span className={`status-badge ${getStatusBadge(quote.status)}`}>
                          {quote.status}
                        </span>
                      </div>
                    </div>
                  </div>

                  {quote.notes && (
                    <p className="mt-3 pt-3 border-t border-slate-100 text-sm text-slate-500">
                      {quote.notes}
                    </p>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <Card className="border-slate-200">
            <CardContent className="py-12 text-center">
              <FileText className="w-16 h-16 text-slate-300 mx-auto mb-4" />
              <h3 className="font-heading text-lg font-semibold text-slate-900 mb-2">
                No Quotes Yet
              </h3>
              <p className="text-slate-500">
                Submit quotes on matched RFQs to see them here
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    </DashboardLayout>
  );
};

export default QuotesList;
