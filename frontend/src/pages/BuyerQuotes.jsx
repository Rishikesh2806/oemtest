import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { api } from "../App";
import DashboardLayout from "../components/layout/DashboardLayout";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Card, CardContent } from "../components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { toast } from "sonner";
import QuoteDetailModal from "../components/QuoteDetailModal";
import {
  DollarSign, Clock, Star, MapPin, Building2, Search,
  Filter, Loader2, CheckCircle2, XCircle, AlertCircle,
  FileText, ExternalLink, MessageSquare, CreditCard, RefreshCw,
  ChevronDown, ChevronRight, Package, Target, Eye
} from "lucide-react";
import RefNumber from "../components/RefNumber";

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
  const [expandedRFQs, setExpandedRFQs] = useState({});
  const [selectedQuoteId, setSelectedQuoteId] = useState(null);
  const [quoteDetailOpen, setQuoteDetailOpen] = useState(false);

  useEffect(() => {
    fetchQuotes();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const fetchQuotes = async () => {
    setLoading(true);
    try {
      const response = await api.get("/buyer/quotes");
      setQuotes(response.data);
      // Expand all RFQs by default
      const expanded = {};
      response.data.forEach(q => {
        expanded[q.rfq_id] = true;
      });
      setExpandedRFQs(expanded);
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

  const toggleRFQ = (rfqId) => {
    setExpandedRFQs(prev => ({
      ...prev,
      [rfqId]: !prev[rfqId]
    }));
  };

  const openQuoteDetail = (quoteId) => {
    setSelectedQuoteId(quoteId);
    setQuoteDetailOpen(true);
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

  const getNegotiationStatusInfo = (quote) => {
    if (!quote.negotiation_status || quote.negotiation_status === "resolved") {
      return null;
    }
    
    const neg = quote.latest_negotiation;
    if (!neg) return null;

    return {
      status: quote.negotiation_status,
      type: neg.request_type,
      requestedPrice: neg.requested_price,
      counterPrice: neg.counter_price,
      message: neg.message,
      response: neg.response
    };
  };

  // Filter quotes
  const filteredQuotes = quotes.filter(quote => {
    const matchesSearch = 
      quote.rfq_title?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      quote.vendor_name?.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === "all" || quote.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  // Group quotes by RFQ with RFQ details
  const groupedQuotes = filteredQuotes.reduce((groups, quote) => {
    const rfqId = quote.rfq_id;
    if (!groups[rfqId]) {
      groups[rfqId] = {
        rfq_id: rfqId,
        rfq_title: quote.rfq_title || "Untitled RFQ",
        rfq_material_type: quote.rfq_material_type,
        rfq_quantity: quote.rfq_quantity,
        rfq_tolerance: quote.rfq_tolerance,
        rfq_supply_type: quote.rfq_supply_type,
        rfq_preferred_payment_terms: quote.rfq_preferred_payment_terms,
        rfq_status: quote.rfq_status,
        quotes: []
      };
    }
    groups[rfqId].quotes.push(quote);
    return groups;
  }, {});

  // Sort quotes within each group
  Object.values(groupedQuotes).forEach(group => {
    group.quotes.sort((a, b) => {
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
  });

  // Convert to array and sort groups by most recent quote
  const sortedGroups = Object.values(groupedQuotes).sort((a, b) => {
    const aLatest = new Date(Math.max(...a.quotes.map(q => new Date(q.created_at))));
    const bLatest = new Date(Math.max(...b.quotes.map(q => new Date(q.created_at))));
    return bLatest - aLatest;
  });

  // Stats
  const stats = {
    total: quotes.length,
    pending: quotes.filter(q => q.status === "pending").length,
    accepted: quotes.filter(q => q.status === "accepted").length,
    negotiating: quotes.filter(q => q.negotiation_status && q.negotiation_status !== "resolved").length
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
            <p className="text-slate-500">View and manage all quotes from vendors, grouped by RFQ</p>
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
          <Card className="bg-blue-50 border-blue-200">
            <CardContent className="p-4 text-center">
              <p className="text-2xl font-bold text-blue-700">{stats.negotiating}</p>
              <p className="text-sm text-blue-600">In Negotiation</p>
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

        {/* Grouped Quotes List */}
        {sortedGroups.length === 0 ? (
          <Card>
            <CardContent className="p-12 text-center">
              <div className="text-6xl text-slate-300 mx-auto mb-4">₹</div>
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
            {sortedGroups.map((group) => {
              const pendingCount = group.quotes.filter(q => q.status === "pending").length;
              const acceptedCount = group.quotes.filter(q => q.status === "accepted").length;
              const negotiatingCount = group.quotes.filter(q => q.negotiation_status && q.negotiation_status !== "resolved").length;
              const lowestPrice = Math.min(...group.quotes.map(q => q.price));
              const isExpanded = expandedRFQs[group.rfq_id];

              return (
                <Card key={group.rfq_id} className="overflow-hidden" data-testid={`rfq-group-${group.rfq_id}`}>
                  {/* RFQ Header - Clickable to expand/collapse */}
                  <div 
                    className="bg-slate-50 p-4 cursor-pointer hover:bg-slate-100 transition-colors"
                    onClick={() => toggleRFQ(group.rfq_id)}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex items-start gap-3">
                        {isExpanded ? (
                          <ChevronDown className="w-5 h-5 text-slate-500 mt-1" />
                        ) : (
                          <ChevronRight className="w-5 h-5 text-slate-500 mt-1" />
                        )}
                        <FileText className="w-5 h-5 text-orange-600 mt-1" />
                        <div>
                          <h3 className="font-semibold text-slate-900">{group.rfq_title}</h3>
                          
                          {/* RFQ Details */}
                          <div className="flex flex-wrap items-center gap-3 mt-2 text-sm text-slate-500">
                            {group.rfq_material_type && (
                              <span className="flex items-center gap-1">
                                <Package className="w-4 h-4" /> {group.rfq_material_type}
                              </span>
                            )}
                            {group.rfq_quantity && (
                              <span>Qty: {group.rfq_quantity}</span>
                            )}
                            {group.rfq_tolerance && (
                              <span>±{group.rfq_tolerance}mm</span>
                            )}
                            <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                              group.rfq_supply_type === "buyer_material" 
                                ? "bg-blue-100 text-blue-700" 
                                : "bg-orange-100 text-orange-700"
                            }`}>
                              {group.rfq_supply_type === "buyer_material" ? "I Supply Material" : "Vendor Supplies"}
                            </span>
                          </div>
                          
                          {/* Preferred Payment Terms */}
                          {group.rfq_preferred_payment_terms && (
                            <div className="flex items-center gap-1 mt-1 text-xs text-blue-600">
                              <CreditCard className="w-3 h-3" />
                              Preferred: {PAYMENT_TERMS_LABELS[group.rfq_preferred_payment_terms] || group.rfq_preferred_payment_terms}
                            </div>
                          )}
                          
                          <p className="text-sm text-slate-500 mt-1">
                            {group.quotes.length} quote{group.quotes.length !== 1 ? 's' : ''} received
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3 flex-shrink-0">
                        <div className="flex flex-wrap gap-2">
                          {pendingCount > 0 && (
                            <span className="px-2 py-1 bg-amber-100 text-amber-700 text-xs font-medium rounded-full">
                              {pendingCount} pending
                            </span>
                          )}
                          {acceptedCount > 0 && (
                            <span className="px-2 py-1 bg-green-100 text-green-700 text-xs font-medium rounded-full">
                              {acceptedCount} accepted
                            </span>
                          )}
                          {negotiatingCount > 0 && (
                            <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs font-medium rounded-full">
                              {negotiatingCount} negotiating
                            </span>
                          )}
                        </div>
                        <div className="text-right">
                          <p className="text-xs text-slate-500">Lowest</p>
                          <p className="font-bold text-slate-900">₹{lowestPrice.toLocaleString('en-IN')}</p>
                        </div>
                        <Link 
                          to={`/buyer/rfq/${group.rfq_id}`}
                          onClick={(e) => e.stopPropagation()}
                        >
                          <Button variant="outline" size="sm">
                            <ExternalLink className="w-4 h-4 mr-1" /> View RFQ
                          </Button>
                        </Link>
                      </div>
                    </div>
                  </div>

                  {/* Quotes List - Collapsible */}
                  {isExpanded && (
                    <CardContent className="p-0 divide-y divide-slate-100">
                      {group.quotes.map((quote) => {
                        const negInfo = getNegotiationStatusInfo(quote);
                        
                        return (
                          <div 
                            key={quote.quote_id} 
                            className={`p-4 hover:bg-slate-50 transition-colors ${
                              negInfo ? "border-l-4 border-l-blue-400" : ""
                            }`}
                            data-testid={`quote-card-${quote.quote_id}`}
                          >
                            <div className="flex flex-col lg:flex-row lg:items-start gap-4">
                              {/* Vendor Info */}
                              <div className="flex items-start gap-3 flex-1">
                                <div className="w-10 h-10 bg-slate-100 rounded-lg flex items-center justify-center flex-shrink-0">
                                  <Building2 className="w-5 h-5 text-slate-500" />
                                </div>
                                <div className="flex-1">
                                  <div className="flex items-center gap-2">
                                    <h4 className="font-medium text-slate-900">{quote.vendor_name || "Vendor"}</h4>
                                    <RefNumber value={quote.quotation_number} />
                                  </div>
                                  <div className="flex items-center gap-3 text-sm text-slate-500">
                                    {quote.vendor_rating > 0 && (
                                      <span className="flex items-center gap-1">
                                        <Star className="w-3 h-3 text-amber-500 fill-amber-500" /> 
                                        {quote.vendor_rating?.toFixed(1)}
                                      </span>
                                    )}
                                    {quote.vendor_location && (
                                      <span className="flex items-center gap-1">
                                        <MapPin className="w-3 h-3" /> {quote.vendor_location}
                                      </span>
                                    )}
                                    {quote.vendor_acceptance_rate > 0 && (
                                      <span className="flex items-center gap-1">
                                        <Target className="w-3 h-3" /> {quote.vendor_acceptance_rate}%
                                      </span>
                                    )}
                                  </div>
                                  
                                  {/* Quote Terms */}
                                  <div className="flex flex-wrap items-center gap-3 mt-2 text-sm">
                                    {quote.proposed_payment_terms && (
                                      <span className="flex items-center gap-1 text-slate-600">
                                        <CreditCard className="w-4 h-4 text-slate-400" />
                                        {PAYMENT_TERMS_LABELS[quote.proposed_payment_terms] || quote.proposed_payment_terms}
                                      </span>
                                    )}
                                    <span className="flex items-center gap-1 text-slate-600">
                                      <Clock className="w-4 h-4 text-slate-400" />
                                      {quote.lead_time_days} days
                                    </span>
                                  </div>
                                  
                                  {/* Negotiation Info */}
                                  {negInfo && (
                                    <div className="mt-3 p-3 bg-blue-50 rounded-lg border border-blue-200">
                                      <div className="flex items-center gap-2 mb-2">
                                        <RefreshCw className="w-4 h-4 text-blue-600" />
                                        <span className="text-sm font-medium text-blue-800">
                                          {negInfo.status === "buyer_requested" 
                                            ? "Negotiation Pending Response" 
                                            : "Counter Offer Received"}
                                        </span>
                                      </div>
                                      
                                      {negInfo.status === "buyer_requested" && (
                                        <div className="text-sm text-blue-700">
                                          <p>Your request: {negInfo.type === "price" ? "Price adjustment" : negInfo.type === "lead_time" ? "Lead time change" : negInfo.type === "payment_terms" ? "Payment terms" : "General request"}</p>
                                          {negInfo.requestedPrice && (
                                            <p>Requested price: <strong>₹{negInfo.requestedPrice.toLocaleString('en-IN')}</strong></p>
                                          )}
                                        </div>
                                      )}
                                      
                                      {negInfo.status === "vendor_countered" && (
                                        <div className="text-sm text-blue-700">
                                          <p className="font-medium">Vendor's counter offer:</p>
                                          {negInfo.counterPrice && (
                                            <p>Counter price: <strong>₹{negInfo.counterPrice.toLocaleString('en-IN')}</strong></p>
                                          )}
                                          {negInfo.response && (
                                            <p className="italic mt-1">"{negInfo.response}"</p>
                                          )}
                                        </div>
                                      )}
                                    </div>
                                  )}
                                </div>
                              </div>

                              {/* Price & Status */}
                              <div className="flex items-center gap-4">
                                <div className="text-right">
                                  <div className="flex items-center gap-1 text-xl font-bold text-slate-900">
                                    <span>₹</span>
                                    {quote.price?.toLocaleString('en-IN', {minimumFractionDigits: 2})}
                                  </div>
                                  <p className="text-xs text-slate-500">INR</p>
                                </div>
                                <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium ${getStatusBadge(quote.status)}`}>
                                  {getStatusIcon(quote.status)}
                                  {quote.status.charAt(0).toUpperCase() + quote.status.slice(1)}
                                </span>
                              </div>

                              {/* Actions */}
                              {quote.status === "pending" && (
                                <div className="flex flex-wrap gap-2">
                                  <Button
                                    onClick={() => openQuoteDetail(quote.quote_id)}
                                    variant="outline"
                                    size="sm"
                                    className="border-orange-300 text-orange-600 hover:bg-orange-50"
                                  >
                                    <Eye className="w-4 h-4 mr-1" /> Details & Negotiate
                                  </Button>
                                  <Button
                                    onClick={() => acceptQuote(quote.quote_id)}
                                    size="sm"
                                    className="bg-green-600 hover:bg-green-700"
                                  >
                                    <CheckCircle2 className="w-4 h-4 mr-1" /> Accept
                                  </Button>
                                  {quote.vendor_user_id && (
                                    <Link to={`/chat?with=${quote.vendor_user_id}&rfq=${quote.rfq_id}`}>
                                      <Button variant="outline" size="sm">
                                        <MessageSquare className="w-4 h-4" />
                                      </Button>
                                    </Link>
                                  )}
                                </div>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </CardContent>
                  )}
                </Card>
              );
            })}
          </div>
        )}

        {/* Results Count */}
        {sortedGroups.length > 0 && (
          <p className="text-sm text-slate-500 text-center">
            Showing {filteredQuotes.length} quotes across {sortedGroups.length} RFQ{sortedGroups.length !== 1 ? 's' : ''}
          </p>
        )}
      </div>

      {/* Quote Detail Modal */}
      <QuoteDetailModal
        quoteId={selectedQuoteId}
        open={quoteDetailOpen}
        onOpenChange={setQuoteDetailOpen}
        onQuoteUpdated={fetchQuotes}
        rfqId={quotes.find(q => q.quote_id === selectedQuoteId)?.rfq_id}
      />
    </DashboardLayout>
  );
};

export default BuyerQuotes;
