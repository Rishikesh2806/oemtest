import { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useAuth, api } from "../App";
import DashboardLayout from "../components/layout/DashboardLayout";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "../components/ui/dialog";
import { toast } from "sonner";
import { 
  FileText, Package, Star, MapPin, Loader2, 
  CheckCircle2, Send, DollarSign, Clock, ArrowLeft,
  Building2, Cpu, Wrench, AlertCircle, Target, MessageSquare, Eye,
  BarChart3, CreditCard
} from "lucide-react";
import QuoteComparison from "../components/quotes/QuoteComparison";

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

const RFQDetail = () => {
  const { rfqId } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [rfq, setRfq] = useState(null);
  const [quotes, setQuotes] = useState([]);
  const [drawings, setDrawings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [quoteDialogOpen, setQuoteDialogOpen] = useState(false);
  const [submittingQuote, setSubmittingQuote] = useState(false);

  const [quoteForm, setQuoteForm] = useState({
    price: "",
    lead_time_days: "",
    notes: "",
    proposed_payment_terms: "net_30",
    payment_terms_notes: ""
  });

  const [compareDialogOpen, setCompareDialogOpen] = useState(false);

  useEffect(() => {
    fetchRFQData();
  }, [rfqId]);

  const fetchRFQData = async () => {
    try {
      const [rfqRes, quotesRes, drawingsRes] = await Promise.all([
        api.get(`/rfqs/${rfqId}`),
        api.get(`/quotes/rfq/${rfqId}`),
        api.get(`/rfqs/${rfqId}/drawings`)
      ]);
      setRfq(rfqRes.data);
      setQuotes(quotesRes.data);
      setDrawings(drawingsRes.data);
    } catch (error) {
      toast.error("Failed to load RFQ details");
    } finally {
      setLoading(false);
    }
  };

  const submitQuote = async () => {
    if (!quoteForm.price || !quoteForm.lead_time_days) {
      toast.error("Please fill in price and lead time");
      return;
    }

    setSubmittingQuote(true);
    try {
      await api.post("/quotes", {
        rfq_id: rfqId,
        price: parseFloat(quoteForm.price),
        lead_time_days: parseInt(quoteForm.lead_time_days),
        notes: quoteForm.notes
      });
      toast.success("Quote submitted successfully");
      setQuoteDialogOpen(false);
      fetchRFQData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to submit quote");
    } finally {
      setSubmittingQuote(false);
    }
  };

  const acceptQuote = async (quoteId) => {
    try {
      const response = await api.post(`/quotes/${quoteId}/accept`);
      toast.success("Quote accepted! Order created.");
      navigate(`/orders/${response.data.order_id}`);
    } catch (error) {
      toast.error("Failed to accept quote");
    }
  };

  const getStatusBadge = (status) => {
    const statusMap = {
      draft: "status-draft",
      submitted: "status-submitted",
      analyzing: "status-analyzing",
      matching: "status-matching",
      quoted: "status-quoted",
      po_issued: "status-po_issued",
      in_production: "status-in_production",
      completed: "status-completed",
      cancelled: "status-cancelled",
      pending: "status-pending",
      accepted: "status-completed",
      rejected: "status-cancelled"
    };
    return statusMap[status] || "status-draft";
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

  if (!rfq) {
    return (
      <DashboardLayout>
        <div className="text-center py-12">
          <AlertCircle className="w-16 h-16 text-slate-300 mx-auto mb-4" />
          <p className="text-slate-500">RFQ not found</p>
        </div>
      </DashboardLayout>
    );
  }

  const isVendor = user?.role === "vendor";
  const isBuyer = user?.role === "buyer";

  return (
    <DashboardLayout>
      <div className="space-y-6" data-testid="rfq-detail-page">
        {/* Back Button & Header */}
        <div className="flex items-center justify-between">
          <Button 
            variant="ghost" 
            onClick={() => navigate(-1)}
            className="text-slate-600"
          >
            <ArrowLeft className="w-4 h-4 mr-2" /> Back
          </Button>
          <span className={`status-badge ${getStatusBadge(rfq.status)}`}>
            {rfq.status.replace("_", " ")}
          </span>
        </div>

        {/* RFQ Info */}
        <Card className="border-slate-200">
          <CardHeader>
            <div className="flex items-start justify-between">
              <div>
                <CardTitle className="font-heading text-2xl">{rfq.title}</CardTitle>
                <p className="text-slate-500 mt-1">RFQ #{rfq.rfq_id.slice(-8)}</p>
              </div>
              {isVendor && rfq.status === "matching" && (
                <Dialog open={quoteDialogOpen} onOpenChange={setQuoteDialogOpen}>
                  <DialogTrigger asChild>
                    <Button className="bg-orange-600 hover:bg-orange-700" data-testid="submit-quote-btn">
                      <Send className="w-4 h-4 mr-2" /> Submit Quote
                    </Button>
                  </DialogTrigger>
                  <DialogContent className="max-w-md">
                    <DialogHeader>
                      <DialogTitle>Submit Your Quote</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-4 mt-4">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                            Price (USD) *
                          </Label>
                          <Input
                            type="number"
                            step="0.01"
                            value={quoteForm.price}
                            onChange={(e) => setQuoteForm(prev => ({ ...prev, price: e.target.value }))}
                            placeholder="0.00"
                            className="mt-1"
                            data-testid="quote-price-input"
                          />
                        </div>
                        <div>
                          <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                            Lead Time (Days) *
                          </Label>
                          <Input
                            type="number"
                            min={1}
                            value={quoteForm.lead_time_days}
                            onChange={(e) => setQuoteForm(prev => ({ ...prev, lead_time_days: e.target.value }))}
                            placeholder="10"
                            className="mt-1"
                            data-testid="quote-leadtime-input"
                          />
                        </div>
                      </div>
                      
                      {/* Payment Terms */}
                      <div>
                        <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                          <CreditCard className="w-3 h-3 inline mr-1" /> Proposed Payment Terms *
                        </Label>
                        <Select
                          value={quoteForm.proposed_payment_terms}
                          onValueChange={(value) => setQuoteForm(prev => ({ ...prev, proposed_payment_terms: value }))}
                        >
                          <SelectTrigger className="mt-1" data-testid="quote-payment-terms">
                            <SelectValue placeholder="Select payment terms" />
                          </SelectTrigger>
                          <SelectContent>
                            {PAYMENT_TERMS.map((term) => (
                              <SelectItem key={term.value} value={term.value}>{term.label}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        {rfq.preferred_payment_terms && (
                          <p className="text-xs text-slate-500 mt-1">
                            Buyer prefers: {getPaymentTermLabel(rfq.preferred_payment_terms)}
                          </p>
                        )}
                      </div>
                      
                      {quoteForm.proposed_payment_terms === "custom" && (
                        <div>
                          <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                            Custom Payment Terms
                          </Label>
                          <Input
                            value={quoteForm.payment_terms_notes}
                            onChange={(e) => setQuoteForm(prev => ({ ...prev, payment_terms_notes: e.target.value }))}
                            placeholder="Describe your payment terms..."
                            className="mt-1"
                          />
                        </div>
                      )}
                      
                      <div>
                        <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                          Notes
                        </Label>
                        <Textarea
                          value={quoteForm.notes}
                          onChange={(e) => setQuoteForm(prev => ({ ...prev, notes: e.target.value }))}
                          placeholder="Additional details about your quote..."
                          className="mt-1"
                          rows={2}
                          data-testid="quote-notes-input"
                        />
                      </div>
                      <Button
                        onClick={submitQuote}
                        disabled={submittingQuote}
                        className="w-full bg-orange-600 hover:bg-orange-700"
                        data-testid="confirm-quote-btn"
                      >
                        {submittingQuote ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <>Submit Quote</>
                        )}
                      </Button>
                    </div>
                  </DialogContent>
                </Dialog>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {rfq.description && (
              <p className="text-slate-600 mb-6">{rfq.description}</p>
            )}
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              <div>
                <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Material</p>
                <p className="text-slate-900 font-medium mt-1">{rfq.material_type}</p>
              </div>
              <div>
                <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Quantity</p>
                <p className="text-slate-900 font-medium mt-1">{rfq.quantity} units</p>
              </div>
              <div>
                <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Tolerance</p>
                <p className="text-slate-900 font-medium mt-1">±{rfq.tolerance} mm</p>
              </div>
              <div>
                <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Surface Finish</p>
                <p className="text-slate-900 font-medium mt-1">{rfq.surface_finish || "Not specified"}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* AI Analysis */}
        {rfq.ai_analysis && (
          <Card className="border-slate-200">
            <CardHeader>
              <CardTitle className="font-heading text-lg flex items-center gap-2">
                <Cpu className="w-5 h-5 text-orange-600" /> AI Analysis Results
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Dimensions & Metrics Row */}
              <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
                {/* Overall Dimensions */}
                <div className="p-4 bg-slate-50 rounded-lg">
                  <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                    Overall Dimensions
                  </p>
                  {rfq.ai_analysis.overall_dimensions && (
                    rfq.ai_analysis.overall_dimensions.length || rfq.ai_analysis.overall_dimensions.width
                  ) ? (
                    <div className="space-y-1">
                      {rfq.ai_analysis.overall_dimensions.length && (
                        <p className="font-mono text-sm">Length: <span className="font-bold text-slate-900">{rfq.ai_analysis.overall_dimensions.length} mm</span></p>
                      )}
                      {rfq.ai_analysis.overall_dimensions.width && (
                        <p className="font-mono text-sm">Width: <span className="font-bold text-slate-900">{rfq.ai_analysis.overall_dimensions.width} mm</span></p>
                      )}
                      {rfq.ai_analysis.overall_dimensions.height && (
                        <p className="font-mono text-sm">Height: <span className="font-bold text-slate-900">{rfq.ai_analysis.overall_dimensions.height} mm</span></p>
                      )}
                    </div>
                  ) : (
                    <p className="text-sm text-slate-500">See drawing for dimensions</p>
                  )}
                </div>

                {/* Material Spec */}
                <div className="p-4 bg-slate-50 rounded-lg">
                  <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                    Material Detected
                  </p>
                  <p className="font-medium text-slate-900">
                    {rfq.ai_analysis.material_specs || rfq.material_type || "Not specified"}
                  </p>
                </div>

                {/* Complexity Score */}
                <div className="p-4 bg-slate-50 rounded-lg">
                  <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                    Complexity Score
                  </p>
                  <div className="flex items-center gap-2">
                    <div className="score-indicator flex-1">
                      <div 
                        className="score-indicator-fill" 
                        style={{ width: `${(rfq.ai_analysis.complexity_score || 5) * 10}%` }}
                      />
                    </div>
                    <span className="font-bold text-slate-900">{rfq.ai_analysis.complexity_score || 5}/10</span>
                  </div>
                </div>

                {/* Machining Time */}
                <div className="p-4 bg-slate-50 rounded-lg">
                  <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                    Est. Machining Time
                  </p>
                  <p className="font-medium text-slate-900 text-lg">
                    {rfq.ai_analysis.estimated_machining_time_hours || 2} hours
                  </p>
                </div>
              </div>

              {/* Recommended Processes - Full Width */}
              {rfq.ai_analysis.recommended_processes && rfq.ai_analysis.recommended_processes.length > 0 && (
                <div className="p-4 bg-orange-50 rounded-lg border border-orange-100">
                  <p className="text-xs font-bold uppercase tracking-wider text-orange-700 mb-3">
                    Recommended Manufacturing Processes
                  </p>
                  <div className="space-y-2">
                    {rfq.ai_analysis.recommended_processes.map((process, i) => (
                      <div key={i} className="flex items-start gap-2">
                        <span className="text-orange-600 mt-0.5">✓</span>
                        <span className="text-sm text-slate-700">{process}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Features Grid */}
              <div className="grid md:grid-cols-2 gap-4">
                {/* Holes */}
                {rfq.ai_analysis.holes && rfq.ai_analysis.holes.length > 0 && (
                  <div className="p-4 bg-slate-50 rounded-lg">
                    <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                      Hole Features
                    </p>
                    <div className="space-y-1">
                      {rfq.ai_analysis.holes.map((hole, i) => (
                        <p key={i} className="text-sm">
                          <span className="font-mono font-medium">Ø{hole.diameter}mm</span>
                          <span className="text-slate-500"> × {hole.quantity || 1} pcs</span>
                          {hole.depth && <span className="text-slate-500"> (Depth: {hole.depth}mm)</span>}
                          {!hole.depth && <span className="text-slate-500"> (THRU)</span>}
                        </p>
                      ))}
                    </div>
                  </div>
                )}

                {/* Threads */}
                {rfq.ai_analysis.threads && rfq.ai_analysis.threads.length > 0 && (
                  <div className="p-4 bg-slate-50 rounded-lg">
                    <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                      Thread Specifications
                    </p>
                    <div className="space-y-1">
                      {rfq.ai_analysis.threads.map((thread, i) => (
                        <p key={i} className="text-sm">
                          <span className="font-mono font-medium">{thread.size}</span>
                          <span className="text-slate-500"> × {thread.quantity || 1} pcs</span>
                          {thread.type && <span className="text-slate-500"> ({thread.type})</span>}
                        </p>
                      ))}
                    </div>
                  </div>
                )}

                {/* Tolerances */}
                {rfq.ai_analysis.critical_tolerances && rfq.ai_analysis.critical_tolerances.length > 0 && (
                  <div className="p-4 bg-slate-50 rounded-lg">
                    <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                      Critical Tolerances
                    </p>
                    <div className="space-y-1">
                      {rfq.ai_analysis.critical_tolerances.map((tol, i) => (
                        <p key={i} className="text-sm">
                          <span className="font-medium">±{tol.tolerance} {tol.unit || 'mm'}</span>
                          {tol.feature && <span className="text-slate-500"> - {tol.feature}</span>}
                        </p>
                      ))}
                    </div>
                  </div>
                )}

                {/* Surface Finish */}
                {rfq.ai_analysis.surface_finish && (
                  <div className="p-4 bg-slate-50 rounded-lg">
                    <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                      Surface Finish
                    </p>
                    <p className="font-medium text-slate-900">{rfq.ai_analysis.surface_finish}</p>
                  </div>
                )}
              </div>

              {/* Special Requirements */}
              {rfq.ai_analysis.special_requirements && rfq.ai_analysis.special_requirements.length > 0 && (
                <div className="p-4 bg-amber-50 rounded-lg border border-amber-100">
                  <p className="text-xs font-bold uppercase tracking-wider text-amber-700 mb-2">
                    Special Requirements
                  </p>
                  <ul className="space-y-1">
                    {rfq.ai_analysis.special_requirements.map((req, i) => (
                      <li key={i} className="text-sm text-slate-700 flex items-start gap-2">
                        <span className="text-amber-600">!</span>
                        {req}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Drawings */}
        {drawings.length > 0 && (
          <Card className="border-slate-200">
            <CardHeader>
              <CardTitle className="font-heading text-lg">Uploaded Drawings</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {drawings.map((drawing) => {
                  const isImage = ['png', 'jpg', 'jpeg', 'gif', 'webp'].includes(drawing.file_type?.toLowerCase());
                  const isPdf = drawing.file_type?.toLowerCase() === 'pdf';
                  const API_URL = process.env.REACT_APP_BACKEND_URL;
                  const token = localStorage.getItem('token');
                  
                  return (
                    <div 
                      key={drawing.drawing_id}
                      className="p-4 bg-slate-50 rounded-lg border border-slate-200 hover:border-orange-300 transition-colors"
                      data-testid={`drawing-${drawing.drawing_id}`}
                    >
                      {/* Preview for images */}
                      {isImage && drawing.file_data && (
                        <div className="mb-3 rounded overflow-hidden bg-white border">
                          <img 
                            src={drawing.file_data.startsWith('data:') ? drawing.file_data : `data:image/${drawing.file_type};base64,${drawing.file_data}`}
                            alt={drawing.filename}
                            className="w-full h-32 object-contain"
                          />
                        </div>
                      )}
                      
                      {/* Icon for non-images */}
                      {!isImage && (
                        <div className="mb-3 h-32 flex items-center justify-center bg-white rounded border">
                          <FileText className="w-12 h-12 text-slate-300" />
                        </div>
                      )}
                      
                      <p className="text-sm font-medium text-slate-900 truncate mb-1">{drawing.filename}</p>
                      <p className="text-xs text-slate-500 mb-3">
                        {(drawing.file_size / 1024).toFixed(1)} KB • {drawing.file_type?.toUpperCase()}
                      </p>
                      
                      <div className="flex gap-2">
                        <Button 
                          variant="outline" 
                          size="sm" 
                          className="flex-1"
                          onClick={() => {
                            // Open in new tab with auth
                            window.open(`${API_URL}/api/drawings/${drawing.drawing_id}/view?token=${token}`, '_blank');
                          }}
                          data-testid={`view-drawing-${drawing.drawing_id}`}
                        >
                          <Eye className="w-4 h-4 mr-1" /> View
                        </Button>
                        <Button 
                          variant="outline" 
                          size="sm" 
                          className="flex-1"
                          onClick={async () => {
                            try {
                              const response = await api.get(`/drawings/${drawing.drawing_id}/download`, {
                                responseType: 'blob'
                              });
                              const url = window.URL.createObjectURL(new Blob([response.data]));
                              const link = document.createElement('a');
                              link.href = url;
                              link.setAttribute('download', drawing.filename);
                              document.body.appendChild(link);
                              link.click();
                              link.remove();
                              window.URL.revokeObjectURL(url);
                            } catch (err) {
                              toast.error("Failed to download file");
                            }
                          }}
                          data-testid={`download-drawing-${drawing.drawing_id}`}
                        >
                          <FileText className="w-4 h-4 mr-1" /> Download
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Matched Vendors (Buyer View) */}
        {isBuyer && rfq.matched_vendors?.length > 0 && (
          <Card className="border-slate-200">
            <CardHeader>
              <CardTitle className="font-heading text-lg flex items-center gap-2">
                <Target className="w-5 h-5 text-orange-600" /> Matched Vendors Based on Drawing Analysis
              </CardTitle>
              <p className="text-sm text-slate-500 mt-1">
                Vendors ranked by machine capability, material compatibility, and tolerance requirements
              </p>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {rfq.matched_vendors.map((vendor, i) => (
                  <div 
                    key={vendor.vendor_id}
                    className={`p-5 rounded-lg border-2 transition-all ${
                      i === 0 ? "bg-orange-50 border-orange-200" : "bg-slate-50 border-slate-200"
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-start gap-4">
                        <div className={`w-14 h-14 rounded-lg flex items-center justify-center ${
                          i === 0 ? "bg-orange-600 text-white" : "bg-slate-200 text-slate-500"
                        }`}>
                          {i === 0 ? (
                            <span className="font-bold text-lg">TOP</span>
                          ) : (
                            <Building2 className="w-6 h-6" />
                          )}
                        </div>
                        <div className="flex-1">
                          <p className="font-semibold text-lg text-slate-900">{vendor.company_name}</p>
                          <div className="flex items-center gap-4 mt-1 text-sm text-slate-500">
                            <span className="flex items-center gap-1">
                              <MapPin className="w-4 h-4" /> {vendor.location}
                            </span>
                            <span className="flex items-center gap-1">
                              <Star className="w-4 h-4 text-amber-500" /> {vendor.rating?.toFixed(1)}
                            </span>
                            <span>{vendor.total_jobs} jobs completed</span>
                          </div>
                          
                          {/* Capability Badges */}
                          <div className="flex flex-wrap gap-2 mt-3">
                            {vendor.tolerance_capable && (
                              <span className="flex items-center gap-1 text-xs bg-green-100 text-green-700 px-2 py-1 rounded">
                                <CheckCircle2 className="w-3 h-3" /> Tolerance Capable
                              </span>
                            )}
                            {vendor.materials_match && (
                              <span className="flex items-center gap-1 text-xs bg-green-100 text-green-700 px-2 py-1 rounded">
                                <CheckCircle2 className="w-3 h-3" /> Material Match
                              </span>
                            )}
                            {vendor.dimension_capable && (
                              <span className="flex items-center gap-1 text-xs bg-green-100 text-green-700 px-2 py-1 rounded">
                                <CheckCircle2 className="w-3 h-3" /> Size Compatible
                              </span>
                            )}
                          </div>

                          {/* Process Matches */}
                          {vendor.process_matches?.length > 0 && (
                            <div className="mt-3">
                              <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-1">
                                Matched Processes
                              </p>
                              <div className="flex flex-wrap gap-1">
                                {vendor.process_matches.map((process, j) => (
                                  <span key={j} className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
                                    {process}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Matching Machines */}
                          <div className="mt-3">
                            <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-1">
                              Matching Machines
                            </p>
                            <div className="flex flex-wrap gap-1">
                              {vendor.matching_machines?.map((machine, j) => (
                                <span key={j} className="text-xs bg-slate-200 text-slate-700 px-2 py-1 rounded font-mono">
                                  {machine}
                                </span>
                              ))}
                            </div>
                          </div>

                          {/* Certifications */}
                          {vendor.certifications?.length > 0 && (
                            <div className="mt-3">
                              <div className="flex flex-wrap gap-1">
                                {vendor.certifications.map((cert, j) => (
                                  <span key={j} className="text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded">
                                    {cert}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                      
                      {/* Match Score */}
                      <div className="text-right ml-4">
                        <div className={`text-3xl font-bold ${
                          vendor.suitability_score >= 80 ? "text-green-600" : 
                          vendor.suitability_score >= 60 ? "text-orange-600" : "text-slate-600"
                        }`}>
                          {vendor.suitability_score}%
                        </div>
                        <div className="text-xs text-slate-500 uppercase font-medium">Match Score</div>
                        <div className="w-24 h-2 bg-slate-200 rounded-full mt-2 overflow-hidden">
                          <div 
                            className={`h-full rounded-full ${
                              vendor.suitability_score >= 80 ? "bg-green-500" : 
                              vendor.suitability_score >= 60 ? "bg-orange-500" : "bg-slate-400"
                            }`}
                            style={{ width: `${vendor.suitability_score}%` }}
                          />
                        </div>
                      </div>
                    </div>
                    
                    {/* Action Buttons */}
                    <div className="flex gap-2 mt-4 pt-4 border-t border-slate-200">
                      <Link to={`/vendor-profile/${vendor.vendor_id}`}>
                        <Button variant="outline" size="sm" data-testid={`view-profile-${vendor.vendor_id}`}>
                          <Eye className="w-4 h-4 mr-1" /> View Profile
                        </Button>
                      </Link>
                      <Link to={`/chat?with=${vendor.user_id}&rfq=${rfqId}`}>
                        <Button variant="outline" size="sm" data-testid={`chat-vendor-${vendor.vendor_id}`}>
                          <MessageSquare className="w-4 h-4 mr-1" /> Chat
                        </Button>
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Quotes */}
        {quotes.length > 0 && (
          <Card className="border-slate-200">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="font-heading text-lg">
                {isBuyer ? "Received Quotes" : "Quote Status"}
              </CardTitle>
              {isBuyer && quotes.filter(q => q.status === "pending").length >= 2 && (
                <Button 
                  variant="outline" 
                  onClick={() => setCompareDialogOpen(true)}
                  className="border-orange-300 text-orange-600 hover:bg-orange-50"
                  data-testid="compare-quotes-btn"
                >
                  <BarChart3 className="w-4 h-4 mr-2" />
                  Compare Quotes
                </Button>
              )}
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {quotes.map((quote) => (
                  <div 
                    key={quote.quote_id}
                    className={`p-4 rounded-lg border ${
                      quote.is_selected 
                        ? "bg-green-50 border-green-200" 
                        : "bg-slate-50 border-slate-200"
                    }`}
                    data-testid={`quote-card-${quote.quote_id}`}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 bg-slate-200 rounded-lg flex items-center justify-center">
                            <Building2 className="w-5 h-5 text-slate-500" />
                          </div>
                          <div>
                            <p className="font-medium text-slate-900">
                              {quote.vendor_name || "Vendor"}
                            </p>
                            <div className="flex items-center gap-3 text-sm text-slate-500">
                              {quote.vendor_rating > 0 && (
                                <span className="flex items-center gap-1">
                                  <Star className="w-4 h-4 text-amber-500" /> {quote.vendor_rating?.toFixed(1)}
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
                        {quote.notes && (
                          <p className="text-sm text-slate-500 mt-2 italic">"{quote.notes}"</p>
                        )}
                        {/* Vendor Machines Preview */}
                        {quote.vendor_machines?.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-2">
                            {quote.vendor_machines.slice(0, 2).map((machine, i) => (
                              <span key={i} className="text-xs bg-slate-200 text-slate-600 px-2 py-0.5 rounded font-mono">
                                {machine}
                              </span>
                            ))}
                            {quote.vendor_machines.length > 2 && (
                              <span className="text-xs text-slate-400">+{quote.vendor_machines.length - 2} more</span>
                            )}
                          </div>
                        )}
                      </div>
                      <div className="text-right">
                        <div className="flex items-center gap-1 text-2xl font-bold text-slate-900">
                          <DollarSign className="w-5 h-5" />
                          {quote.price?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </div>
                        <div className="flex items-center gap-1 text-sm text-slate-500 mt-1">
                          <Clock className="w-4 h-4" /> {quote.lead_time_days} days
                        </div>
                        <span className={`status-badge mt-2 ${getStatusBadge(quote.status)}`}>
                          {quote.status}
                        </span>
                      </div>
                    </div>
                    
                    {isBuyer && quote.status === "pending" && (
                      <div className="mt-4 pt-4 border-t border-slate-200 flex gap-2">
                        <Button
                          onClick={() => acceptQuote(quote.quote_id)}
                          className="bg-green-600 hover:bg-green-700"
                          data-testid={`accept-quote-${quote.quote_id}`}
                        >
                          <CheckCircle2 className="w-4 h-4 mr-2" /> Accept Quote
                        </Button>
                        {quote.vendor_id_ref && (
                          <Link to={`/vendor-profile/${quote.vendor_id_ref}`}>
                            <Button variant="outline" size="default">
                              <Eye className="w-4 h-4 mr-2" /> View Profile
                            </Button>
                          </Link>
                        )}
                        {quote.vendor_user_id && (
                          <Link to={`/chat?with=${quote.vendor_user_id}&rfq=${rfqId}`}>
                            <Button variant="outline" size="default">
                              <MessageSquare className="w-4 h-4 mr-2" /> Chat
                            </Button>
                          </Link>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Quote Comparison Dialog */}
        {isBuyer && (
          <QuoteComparison
            quotes={quotes}
            open={compareDialogOpen}
            onOpenChange={setCompareDialogOpen}
            onAcceptQuote={acceptQuote}
            rfqId={rfqId}
          />
        )}
      </div>
    </DashboardLayout>
  );
};

export default RFQDetail;
