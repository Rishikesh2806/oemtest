import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useAuth, api } from "../App";
import DashboardLayout from "../components/layout/DashboardLayout";
import { Button } from "../components/ui/button";
import { Card, CardContent } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { toast } from "sonner";
import { 
  FileText, Search, Loader2, Calendar, Package,
  Clock, Send, Eye, MessageSquare, CheckCircle2, Target,
  CreditCard, Building2
} from "lucide-react";
import RefNumber from "../components/RefNumber";

const PAYMENT_TERMS = [
  { value: "net_30", label: "Net 30 Days" },
  { value: "net_45", label: "Net 45 Days" },
  { value: "net_60", label: "Net 60 Days" },
  { value: "50_advance_50_delivery", label: "50% Advance, 50% on Delivery" },
  { value: "100_advance", label: "100% Advance" },
  { value: "against_delivery", label: "Payment Against Delivery" },
  { value: "milestone_based", label: "Milestone-Based Payment" },
  { value: "letter_of_credit", label: "Letter of Credit (LC)" },
  { value: "custom", label: "Custom Terms" }
];

const getPaymentTermLabel = (value) => {
  const term = PAYMENT_TERMS.find(t => t.value === value);
  return term ? term.label : value;
};

const VendorMatchedRFQs = () => {
  const { user } = useAuth();
  const [rfqs, setRfqs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterStatus, setFilterStatus] = useState("all");
  const [existingQuotes, setExistingQuotes] = useState({});

  useEffect(() => {
    fetchMatchedRFQs();
  }, []);

  const fetchMatchedRFQs = async () => {
    try {
      const response = await api.get("/vendor/matched-rfqs");
      setRfqs(response.data.rfqs || []);
      
      // Build a map of existing quotes
      const quotesMap = {};
      for (const rfq of response.data.rfqs || []) {
        if (rfq.vendor_quote) {
          quotesMap[rfq.rfq_id] = rfq.vendor_quote;
        }
      }
      setExistingQuotes(quotesMap);
    } catch (error) {
      console.error("Failed to load matched RFQs:", error);
      toast.error("Failed to load matched RFQs");
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    const badges = {
      matching: "bg-purple-100 text-purple-600",
      quoted: "bg-amber-100 text-amber-600",
      accepted: "bg-green-100 text-green-600",
      in_progress: "bg-indigo-100 text-indigo-600",
      completed: "bg-teal-100 text-teal-600",
      cancelled: "bg-red-100 text-red-600"
    };
    return badges[status] || "bg-slate-100 text-slate-600";
  };

  const getMatchScoreColor = (score) => {
    if (score >= 80) return "text-green-600 bg-green-100";
    if (score >= 60) return "text-amber-600 bg-amber-100";
    return "text-slate-600 bg-slate-100";
  };

  const filteredRFQs = rfqs.filter(rfq => {
    const term = searchTerm.toLowerCase();
    const matchesSearch = rfq.title?.toLowerCase().includes(term) ||
                         rfq.rfq_number?.toLowerCase().includes(term) ||
                         rfq.material_type?.toLowerCase().includes(term);
    const matchesStatus = filterStatus === "all" || rfq.status === filterStatus ||
                         (filterStatus === "needs_quote" && !existingQuotes[rfq.rfq_id]);
    return matchesSearch && matchesStatus;
  });

  const statuses = [
    { value: "all", label: "All RFQs" },
    { value: "needs_quote", label: "Needs Quote" },
    { value: "matching", label: "Matching" },
    { value: "quoted", label: "Quoted" },
    { value: "accepted", label: "Accepted" },
    { value: "in_progress", label: "In Progress" }
  ];

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
      <div className="space-y-6" data-testid="vendor-matched-rfqs">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="font-heading text-2xl font-bold text-slate-900">Matched RFQs</h1>
            <p className="text-slate-500 mt-1">
              {rfqs.length} opportunities matched to your capabilities
            </p>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <span className="flex items-center gap-1 px-3 py-1 bg-green-100 text-green-700 rounded-full">
              <CheckCircle2 className="w-4 h-4" />
              {Object.keys(existingQuotes).length} Quoted
            </span>
            <span className="flex items-center gap-1 px-3 py-1 bg-amber-100 text-amber-700 rounded-full">
              <Clock className="w-4 h-4" />
              {rfqs.length - Object.keys(existingQuotes).length} Pending
            </span>
          </div>
        </div>

        {/* Filters */}
        <Card className="border-slate-200">
          <CardContent className="pt-6">
            <div className="flex flex-col md:flex-row gap-4">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input
                  placeholder="Search by title or material..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                  data-testid="search-rfqs"
                />
              </div>
              <div className="flex gap-2 flex-wrap">
                {statuses.map(status => (
                  <Button
                    key={status.value}
                    variant={filterStatus === status.value ? "default" : "outline"}
                    size="sm"
                    onClick={() => setFilterStatus(status.value)}
                    className={filterStatus === status.value ? "bg-orange-600" : ""}
                    data-testid={`filter-${status.value}`}
                  >
                    {status.label}
                  </Button>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* RFQ List */}
        {filteredRFQs.length > 0 ? (
          <div className="grid gap-4">
            {filteredRFQs.map((rfq) => {
              const hasQuoted = !!existingQuotes[rfq.rfq_id];
              const quote = existingQuotes[rfq.rfq_id];
              
              return (
                <Card 
                  key={rfq.rfq_id}
                  className={`border-slate-200 hover:shadow-md transition-all ${
                    hasQuoted ? "border-l-4 border-l-green-500" : "border-l-4 border-l-amber-500"
                  }`}
                  data-testid={`rfq-card-${rfq.rfq_id}`}
                >
                  <CardContent className="p-6">
                    <div className="flex items-start justify-between gap-6">
                      {/* RFQ Info */}
                      <div className="flex-1">
                        <div className="flex items-start gap-4">
                          <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center flex-shrink-0">
                            <FileText className="w-6 h-6 text-orange-600" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-3">
                              <h3 className="font-semibold text-slate-900 text-lg">{rfq.title}</h3>
                              <RefNumber value={rfq.rfq_number} />
                              <span className={`status-badge ${getStatusBadge(rfq.status)}`}>
                                {rfq.status?.replace("_", " ")}
                              </span>
                              {rfq.match_score && (
                                <span className={`px-2 py-0.5 rounded text-xs font-bold ${getMatchScoreColor(rfq.match_score)}`}>
                                  <Target className="w-3 h-3 inline mr-1" />
                                  {rfq.match_score}% Match
                                </span>
                              )}
                            </div>
                            
                            <div className="flex items-center gap-4 mt-2 text-sm text-slate-500">
                              <span className="flex items-center gap-1">
                                <Package className="w-4 h-4" /> {rfq.material_type}
                              </span>
                              <span>Qty: {rfq.quantity}</span>
                              <span>Tolerance: {rfq.tolerance ? `±${rfq.tolerance}mm` : "As per drawing"}</span>
                              {rfq.buyer_company && (
                                <span className="flex items-center gap-1">
                                  <Building2 className="w-4 h-4" /> {rfq.buyer_company}
                                </span>
                              )}
                            </div>
                            
                            {/* Material Supply Type */}
                            <div className="mt-2">
                              <span className={`px-2 py-1 rounded text-xs font-medium ${
                                rfq.supply_type === "buyer_material" 
                                  ? "bg-blue-100 text-blue-700" 
                                  : "bg-orange-100 text-orange-700"
                              }`}>
                                {rfq.supply_type === "buyer_material" 
                                  ? "Buyer Supplies Material (Service Only)" 
                                  : "You Supply Material (Turnkey)"}
                              </span>
                            </div>
                            
                            {rfq.description && (
                              <p className="text-sm text-slate-500 mt-2 line-clamp-2">{rfq.description}</p>
                            )}
                            
                            {/* Buyer's Preferred Payment Terms */}
                            {rfq.preferred_payment_terms && (
                              <div className="mt-2 flex items-center gap-2 text-xs">
                                <CreditCard className="w-3 h-3 text-blue-500" />
                                <span className="text-blue-600">
                                  Buyer prefers: {getPaymentTermLabel(rfq.preferred_payment_terms)}
                                </span>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                      
                      {/* Quote Info & Actions */}
                      <div className="flex-shrink-0 text-right min-w-[200px]">
                        {hasQuoted ? (
                          <div className="space-y-2">
                            <div className="text-xs font-bold uppercase tracking-wider text-green-600">
                              Your Quote
                            </div>
                            <div className="flex items-center justify-end gap-1 text-2xl font-bold text-slate-900">
                              <span className="text-xl">₹</span>
                              {quote.price?.toLocaleString('en-IN', {minimumFractionDigits: 2})}
                            </div>
                            <div className="flex items-center justify-end gap-1 text-sm text-slate-500">
                              <Clock className="w-4 h-4" /> {quote.lead_time_days} days
                            </div>
                            <span className={`inline-block status-badge ${
                              quote.status === "accepted" ? "bg-green-100 text-green-600" :
                              quote.status === "rejected" ? "bg-red-100 text-red-600" :
                              "bg-amber-100 text-amber-600"
                            }`}>
                              {quote.status}
                            </span>
                          </div>
                        ) : (
                          <div className="space-y-3">
                            <div className="text-xs font-bold uppercase tracking-wider text-amber-600">
                              No Quote Yet
                            </div>
                            <Link to={`/vendor/rfq/${rfq.rfq_id}`}>
                              <Button
                                className="bg-orange-600 hover:bg-orange-700 w-full"
                                data-testid={`submit-quote-${rfq.rfq_id}`}
                              >
                                <Send className="w-4 h-4 mr-2" /> Submit Quote
                              </Button>
                            </Link>
                          </div>
                        )}
                        
                        <div className="flex gap-2 mt-3 justify-end">
                          <Link to={`/vendor/rfq/${rfq.rfq_id}`}>
                            <Button variant="outline" size="sm">
                              <Eye className="w-4 h-4 mr-1" /> Details
                            </Button>
                          </Link>
                          {rfq.buyer_id && (
                            <Link to={`/chat?with=${rfq.buyer_id}`}>
                              <Button variant="outline" size="sm">
                                <MessageSquare className="w-4 h-4 mr-1" /> Chat
                              </Button>
                            </Link>
                          )}
                        </div>
                        
                        <p className="text-xs text-slate-400 mt-2 flex items-center gap-1 justify-end">
                          <Calendar className="w-3 h-3" />
                          {new Date(rfq.created_at).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        ) : (
          <Card className="border-slate-200">
            <CardContent className="py-16 text-center">
              <FileText className="w-16 h-16 text-slate-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-slate-900 mb-2">No Matched RFQs Found</h3>
              <p className="text-slate-500 mb-6">
                {searchTerm || filterStatus !== "all" 
                  ? "Try adjusting your search or filters"
                  : "You haven't been matched to any RFQs yet. Make sure your machine capabilities are up to date."}
              </p>
              <Link to="/vendor/machines">
                <Button variant="outline">
                  Update Machine Capabilities
                </Button>
              </Link>
            </CardContent>
          </Card>
        )}
      </div>
    </DashboardLayout>
  );
};

export default VendorMatchedRFQs;
