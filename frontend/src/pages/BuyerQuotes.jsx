import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { api } from "../App";
import DashboardLayout from "../components/layout/DashboardLayout";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Card, CardContent } from "../components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { toast } from "sonner";
import {
  DollarSign, Clock, Star, MapPin, Building2, Search,
  Filter, Loader2, CheckCircle2, XCircle, AlertCircle,
  FileText, ExternalLink, MessageSquare, CreditCard, RefreshCw
} from "lucide-react";

const PAYMENT_TERMS_LABELS = {
  net_30: "Net 30 Days",
  net_45: "Net 45 Days",
  net_60: "Net 60 Days",
  "50_advance_50_delivery": "50% Advance",
  "100_advance": "100% Advance",
  against_delivery: "Against Delivery",
  milestone_based: "Milestone Based",
  letter_of_credit: "Letter of Credit",
  custom: "Custom Terms"
};

const BuyerQuotes = () => {
  const [quotes, setQuotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [sortBy, setSortBy] = useState("newest");

  useEffect(() => {
    fetchQuotes();
  }, []);

  const fetchQuotes = async () => {
    setLoading(true);
    try {
      const response = await api.get("/buyer/quotes");
      setQuotes(response.data);
    } catch (error) {
      toast.error("Failed to load quotes");
    } finally {
      setLoading(false);
    }
  };

  const acceptQuote = async (quoteId) => {
    try {
      await api.post(`/quotes/${quoteId}/accept`);
      toast.success("Quote accepted! Order created.");
      fetchQuotes();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to accept quote");
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case "pending":
        return "bg-amber-100 text-amber-700";
      case "accepted":
        return "bg-green-100 text-green-700";
      case "rejected":
        return "bg-red-100 text-red-700";
      case "expired":
        return "bg-slate-100 text-slate-700";
      default:
        return "bg-slate-100 text-slate-700";
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case "pending":
        return <AlertCircle className="w-4 h-4" />;
      case "accepted":
        return <CheckCircle2 className="w-4 h-4" />;
      case "rejected":
        return <XCircle className="w-4 h-4" />;
      default:
        return null;
    }
  };

  // Filter and sort quotes
  const filteredQuotes = quotes
    .filter(quote => {
      const matchesSearch = 
        quote.rfq_title?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        quote.vendor_name?.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesStatus = statusFilter === "all" || quote.status === statusFilter;
      return matchesSearch && matchesStatus;
    })
    .sort((a, b) => {
      switch (sortBy) {
        case "newest":
          return new Date(b.created_at) - new Date(a.created_at);
        case "oldest":
          return new Date(a.created_at) - new Date(b.created_at);
        case "price_low":
          return a.price - b.price;
        case "price_high":
          return b.price - a.price;
        case "lead_time":
          return a.lead_time_days - b.lead_time_days;
        default:
          return 0;
      }
    });

  // Stats
  const stats = {
    total: quotes.length,
    pending: quotes.filter(q => q.status === "pending").length,
    accepted: quotes.filter(q => q.status === "accepted").length,
    rejected: quotes.filter(q => q.status === "rejected").length
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
      <div className="space-y-6" data-testid="buyer-quotes-page">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="font-heading text-2xl font-bold text-slate-900">Received Quotes</h1>
            <p className="text-slate-500">View and manage all quotes from vendors</p>
          </div>
          <Button onClick={fetchQuotes} variant="outline" className="gap-2">
            <RefreshCw className="w-4 h-4" /> Refresh
          </Button>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card className="bg-slate-50">
            <CardContent className="p-4 text-center">
              <p className="text-2xl font-bold text-slate-900">{stats.total}</p>
              <p className="text-sm text-slate-500">Total Quotes</p>
            </CardContent>
          </Card>
          <Card className="bg-amber-50 border-amber-200">
            <CardContent className="p-4 text-center">
              <p className="text-2xl font-bold text-amber-700">{stats.pending}</p>
              <p className="text-sm text-amber-600">Pending</p>
            </CardContent>
          </Card>
          <Card className="bg-green-50 border-green-200">
            <CardContent className="p-4 text-center">
              <p className="text-2xl font-bold text-green-700">{stats.accepted}</p>
              <p className="text-sm text-green-600">Accepted</p>
            </CardContent>
          </Card>
          <Card className="bg-red-50 border-red-200">
            <CardContent className="p-4 text-center">
              <p className="text-2xl font-bold text-red-700">{stats.rejected}</p>
              <p className="text-sm text-red-600">Rejected</p>
            </CardContent>
          </Card>
        </div>

        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <Input
              placeholder="Search by RFQ title or vendor name..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>
          <div className="flex gap-2">
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[140px]">
                <Filter className="w-4 h-4 mr-2" />
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value="accepted">Accepted</SelectItem>
                <SelectItem value="rejected">Rejected</SelectItem>
              </SelectContent>
            </Select>
            <Select value={sortBy} onValueChange={setSortBy}>
              <SelectTrigger className="w-[160px]">
                <SelectValue placeholder="Sort by" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="newest">Newest First</SelectItem>
                <SelectItem value="oldest">Oldest First</SelectItem>
                <SelectItem value="price_low">Price: Low to High</SelectItem>
                <SelectItem value="price_high">Price: High to Low</SelectItem>
                <SelectItem value="lead_time">Lead Time</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Quotes List */}
        {filteredQuotes.length === 0 ? (
          <Card>
            <CardContent className="p-12 text-center">
              <DollarSign className="w-16 h-16 text-slate-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-slate-900 mb-2">
                {quotes.length === 0 ? "No quotes received yet" : "No quotes match your filters"}
              </h3>
              <p className="text-slate-500 mb-4">
                {quotes.length === 0 
                  ? "Create an RFQ and submit it to receive quotes from vendors"
                  : "Try adjusting your search or filter criteria"}
              </p>
              {quotes.length === 0 && (
                <Link to="/buyer/rfq/new">
                  <Button className="bg-orange-600 hover:bg-orange-700">
                    <FileText className="w-4 h-4 mr-2" /> Create New RFQ
                  </Button>
                </Link>
              )}
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {filteredQuotes.map((quote) => (
              <Card key={quote.quote_id} className="hover:shadow-md transition-shadow" data-testid={`quote-card-${quote.quote_id}`}>
                <CardContent className="p-5">
                  <div className="flex flex-col lg:flex-row lg:items-start gap-4">
                    {/* Vendor Info */}
                    <div className="flex-1">
                      <div className="flex items-start gap-3 mb-3">
                        <div className="w-12 h-12 bg-slate-100 rounded-lg flex items-center justify-center flex-shrink-0">
                          <Building2 className="w-6 h-6 text-slate-500" />
                        </div>
                        <div>
                          <h3 className="font-semibold text-slate-900">{quote.vendor_name || "Vendor"}</h3>
                          <div className="flex items-center gap-3 text-sm text-slate-500">
                            {quote.vendor_rating > 0 && (
                              <span className="flex items-center gap-1">
                                <Star className="w-4 h-4 text-amber-500 fill-amber-500" /> 
                                {quote.vendor_rating?.toFixed(1)}
                              </span>
                            )}
                            {quote.vendor_location && (
                              <span className="flex items-center gap-1">
                                <MapPin className="w-3 h-3" /> {quote.vendor_location}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* RFQ Reference */}
                      <div className="bg-slate-50 rounded-lg p-3 mb-3">
                        <p className="text-xs text-slate-500 mb-1">For RFQ:</p>
                        <Link 
                          to={`/buyer/rfq/${quote.rfq_id}`}
                          className="text-sm font-medium text-orange-600 hover:underline"
                        >
                          {quote.rfq_title || quote.rfq_id}
                        </Link>
                      </div>

                      {/* Quote Details Grid */}
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
                        {quote.proposed_payment_terms && (
                          <div className="flex items-center gap-2">
                            <CreditCard className="w-4 h-4 text-slate-400" />
                            <span className="text-slate-600">
                              {PAYMENT_TERMS_LABELS[quote.proposed_payment_terms] || quote.proposed_payment_terms}
                            </span>
                          </div>
                        )}
                        <div className="flex items-center gap-2">
                          <DollarSign className="w-4 h-4 text-slate-400" />
                          <span className="text-slate-600">{quote.currency || "USD"}</span>
                        </div>
                        {quote.expires_at && (
                          <div className="flex items-center gap-2">
                            <Clock className="w-4 h-4 text-slate-400" />
                            <span className="text-slate-600">
                              Valid: {new Date(quote.expires_at).toLocaleDateString()}
                            </span>
                          </div>
                        )}
                        {quote.vendor_acceptance_rate !== undefined && (
                          <div className="flex items-center gap-2">
                            <CheckCircle2 className="w-4 h-4 text-slate-400" />
                            <span className="text-slate-600">{quote.vendor_acceptance_rate}% rate</span>
                          </div>
                        )}
                      </div>

                      {/* Notes */}
                      {quote.notes && (
                        <p className="text-sm text-slate-500 mt-3 italic">"{quote.notes}"</p>
                      )}
                    </div>

                    {/* Price & Status */}
                    <div className="lg:text-right lg:min-w-[180px]">
                      <div className="flex lg:justify-end items-center gap-1 text-2xl font-bold text-slate-900">
                        <DollarSign className="w-5 h-5" />
                        {quote.price?.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </div>
                      <div className="flex lg:justify-end items-center gap-1 text-sm text-slate-500 mt-1">
                        <Clock className="w-4 h-4" /> {quote.lead_time_days} days lead time
                      </div>
                      <div className="flex lg:justify-end mt-2">
                        <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium ${getStatusBadge(quote.status)}`}>
                          {getStatusIcon(quote.status)}
                          {quote.status.charAt(0).toUpperCase() + quote.status.slice(1)}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 mt-2 lg:text-right">
                        Received: {new Date(quote.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>

                  {/* Actions */}
                  {quote.status === "pending" && (
                    <div className="mt-4 pt-4 border-t border-slate-200 flex flex-wrap gap-2">
                      <Link to={`/buyer/rfq/${quote.rfq_id}`}>
                        <Button variant="outline" className="border-orange-300 text-orange-600 hover:bg-orange-50">
                          <ExternalLink className="w-4 h-4 mr-2" /> View Details & Negotiate
                        </Button>
                      </Link>
                      <Button
                        onClick={() => acceptQuote(quote.quote_id)}
                        className="bg-green-600 hover:bg-green-700"
                      >
                        <CheckCircle2 className="w-4 h-4 mr-2" /> Accept Quote
                      </Button>
                      {quote.vendor_user_id && (
                        <Link to={`/chat?with=${quote.vendor_user_id}&rfq=${quote.rfq_id}`}>
                          <Button variant="outline">
                            <MessageSquare className="w-4 h-4 mr-2" /> Chat
                          </Button>
                        </Link>
                      )}
                    </div>
                  )}

                  {/* Negotiation Status */}
                  {quote.negotiation_status && quote.negotiation_status !== "resolved" && (
                    <div className="mt-3">
                      <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${
                        quote.negotiation_status === "buyer_requested" 
                          ? "bg-amber-100 text-amber-700" 
                          : "bg-blue-100 text-blue-700"
                      }`}>
                        <RefreshCw className="w-3 h-3" />
                        {quote.negotiation_status === "buyer_requested" 
                          ? "Negotiation Pending" 
                          : "Counter Offer Available"}
                      </span>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Results Count */}
        {filteredQuotes.length > 0 && (
          <p className="text-sm text-slate-500 text-center">
            Showing {filteredQuotes.length} of {quotes.length} quotes
          </p>
        )}
      </div>
    </DashboardLayout>
  );
};

export default BuyerQuotes;
