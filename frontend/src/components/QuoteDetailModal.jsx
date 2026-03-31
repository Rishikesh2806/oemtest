import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { api } from "../App";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Textarea } from "./ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "./ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import { toast } from "sonner";
import {
  Building2, Star, MapPin, DollarSign, Clock, CreditCard,
  Wrench, Award, Globe, Phone, Mail, User, MessageSquare,
  CheckCircle2, XCircle, RefreshCw, Loader2, Send, ArrowRight,
  AlertCircle, History
} from "lucide-react";

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

const QuoteDetailModal = ({ quoteId, open, onOpenChange, onQuoteUpdated, rfqId }) => {
  const [quote, setQuote] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("details");
  const [negotiating, setNegotiating] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  
  const [negotiationForm, setNegotiationForm] = useState({
    request_type: "general",
    message: "",
    requested_price: "",
    requested_lead_time: "",
    requested_payment_terms: "",
    payment_terms_notes: ""
  });

  useEffect(() => {
    if (open && quoteId) {
      fetchQuoteDetail();
    }
  }, [open, quoteId]);

  const fetchQuoteDetail = async () => {
    setLoading(true);
    try {
      const response = await api.get(`/quotes/${quoteId}`);
      setQuote(response.data);
    } catch (error) {
      toast.error("Failed to load quote details");
      onOpenChange(false);
    } finally {
      setLoading(false);
    }
  };

  const submitNegotiation = async () => {
    if (!negotiationForm.message.trim()) {
      toast.error("Please provide a message explaining your request");
      return;
    }

    setSubmitting(true);
    try {
      const payload = {
        request_type: negotiationForm.request_type,
        message: negotiationForm.message,
        requested_price: negotiationForm.requested_price ? parseFloat(negotiationForm.requested_price) : null,
        requested_lead_time: negotiationForm.requested_lead_time ? parseInt(negotiationForm.requested_lead_time) : null,
        requested_payment_terms: negotiationForm.requested_payment_terms || null,
        payment_terms_notes: negotiationForm.payment_terms_notes || null
      };
      
      await api.post(`/quotes/${quoteId}/negotiate`, payload);
      toast.success("Negotiation request sent to vendor");
      setNegotiating(false);
      setNegotiationForm({
        request_type: "general",
        message: "",
        requested_price: "",
        requested_lead_time: "",
        requested_payment_terms: "",
        payment_terms_notes: ""
      });
      fetchQuoteDetail();
      if (onQuoteUpdated) onQuoteUpdated();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to send negotiation request");
    } finally {
      setSubmitting(false);
    }
  };

  const acceptCounterOffer = async (negotiationId) => {
    try {
      await api.post(`/quotes/${quoteId}/negotiate/${negotiationId}/accept-counter`);
      toast.success("Counter offer accepted");
      fetchQuoteDetail();
      if (onQuoteUpdated) onQuoteUpdated();
    } catch (error) {
      toast.error("Failed to accept counter offer");
    }
  };

  const getNegotiationStatusBadge = (status) => {
    const styles = {
      pending: "bg-amber-100 text-amber-700",
      accepted: "bg-green-100 text-green-700",
      counter_offered: "bg-blue-100 text-blue-700",
      counter_accepted: "bg-green-100 text-green-700",
      rejected: "bg-red-100 text-red-700"
    };
    const labels = {
      pending: "Pending Response",
      accepted: "Accepted",
      counter_offered: "Counter Offered",
      counter_accepted: "Counter Accepted",
      rejected: "Rejected"
    };
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${styles[status] || "bg-slate-100 text-slate-700"}`}>
        {labels[status] || status}
      </span>
    );
  };

  if (!open) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto" data-testid="quote-detail-modal">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-orange-600" />
          </div>
        ) : quote ? (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-3">
                <div className="w-12 h-12 bg-slate-100 rounded-lg flex items-center justify-center">
                  <Building2 className="w-6 h-6 text-slate-600" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-slate-900">{quote.vendor_name}</h2>
                  <p className="text-sm text-slate-500 font-normal">Quote for: {quote.rfq_title}</p>
                </div>
              </DialogTitle>
            </DialogHeader>

            {/* Price and Key Info */}
            <div className="grid grid-cols-3 gap-4 p-4 bg-slate-50 rounded-lg mb-4">
              <div className="text-center">
                <div className="flex items-center justify-center gap-1 text-2xl font-bold text-slate-900">
                  <DollarSign className="w-5 h-5" />
                  {((quote.total_cost || quote.price || 0) * 1.025).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </div>
                <p className="text-sm text-slate-500">Total Payable ({quote.currency})</p>
                <p className="text-[10px] text-slate-400">incl. 2.5% platform fee</p>
              </div>
              <div className="text-center">
                <div className="flex items-center justify-center gap-1 text-2xl font-bold text-slate-900">
                  <Clock className="w-5 h-5" />
                  {quote.lead_time_days}
                </div>
                <p className="text-sm text-slate-500">Lead Time (days)</p>
              </div>
              <div className="text-center">
                <div className="flex items-center justify-center gap-1 text-2xl font-bold text-amber-600">
                  <Star className="w-5 h-5 fill-amber-400" />
                  {quote.vendor_rating?.toFixed(1) || "N/A"}
                </div>
                <p className="text-sm text-slate-500">Vendor Rating</p>
              </div>
            </div>

            {/* Quote Status */}
            {quote.negotiation_status && quote.negotiation_status !== "resolved" && (
              <div className="flex items-center gap-2 p-3 bg-amber-50 border border-amber-200 rounded-lg mb-4">
                <AlertCircle className="w-5 h-5 text-amber-600" />
                <span className="text-sm text-amber-800">
                  {quote.negotiation_status === "buyer_requested" 
                    ? "Negotiation request pending vendor response"
                    : quote.negotiation_status === "vendor_countered"
                    ? "Vendor has made a counter offer - check negotiations tab"
                    : "Negotiation in progress"}
                </span>
              </div>
            )}

            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="details">Quote Details</TabsTrigger>
                <TabsTrigger value="vendor">Vendor Info</TabsTrigger>
                <TabsTrigger value="negotiations" className="relative">
                  Negotiations
                  {quote.negotiations?.filter(n => n.status === "counter_offered").length > 0 && (
                    <span className="absolute -top-1 -right-1 w-4 h-4 bg-orange-500 text-white text-xs rounded-full flex items-center justify-center">
                      !
                    </span>
                  )}
                </TabsTrigger>
              </TabsList>

              <TabsContent value="details" className="space-y-4 mt-4">
                {/* Cost Breakdown - Item-wise */}
                {quote.is_itemwise && quote.items && quote.items.length > 0 && (
                  <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                    <div className="flex items-center gap-2 mb-3">
                      <DollarSign className="w-4 h-4 text-blue-600" />
                      <span className="font-medium text-blue-800">Item-wise Cost Breakdown ({quote.items.length} items)</span>
                    </div>
                    <div className="space-y-3">
                      {quote.items.map((item, idx) => {
                        const itemAdditional = item.additional_costs ? 
                          Object.values(item.additional_costs).reduce((a, b) => a + b, 0) : 0;
                        return (
                          <div key={item.item_id || idx} className="p-3 bg-white rounded border border-blue-100">
                            <div className="flex justify-between items-start">
                              <div>
                                <p className="font-medium text-slate-800">
                                  {idx + 1}. {item.title || `Item ${idx + 1}`}
                                </p>
                                {item.remarks && (
                                  <p className="text-xs text-slate-500 mt-1">{item.remarks}</p>
                                )}
                              </div>
                              <span className="font-bold text-slate-900">
                                ₹{(item.total_cost || 0).toLocaleString('en-IN')}
                              </span>
                            </div>
                            <div className="grid grid-cols-3 gap-2 mt-2 text-xs text-slate-600">
                              <div>
                                <span className="text-slate-400">Material:</span>{' '}
                                {item.material_provided_by_buyer ? 'Buyer' : `₹${(item.material_cost || 0).toLocaleString('en-IN')}`}
                              </div>
                              <div>
                                <span className="text-slate-400">Labour:</span>{' '}
                                ₹{(item.labour_cost || 0).toLocaleString('en-IN')}
                              </div>
                              <div>
                                <span className="text-slate-400">Additional:</span>{' '}
                                {itemAdditional > 0 ? `₹${itemAdditional.toLocaleString('en-IN')}` : '-'}
                              </div>
                            </div>
                            {item.additional_costs && Object.keys(item.additional_costs).length > 0 && (
                              <div className="mt-2 pt-2 border-t border-blue-100">
                                <p className="text-xs text-slate-400 mb-1">Additional Costs:</p>
                                <div className="flex flex-wrap gap-1">
                                  {Object.entries(item.additional_costs).map(([key, value]) => (
                                    <span key={key} className="text-xs px-2 py-0.5 bg-blue-50 text-blue-700 rounded">
                                      {key.replace(/_/g, ' ')}: ₹{value.toLocaleString('en-IN')}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                    <div className="mt-3 pt-3 border-t border-blue-200 space-y-2">
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-blue-700">Vendor Quote Total</span>
                        <span className="text-base font-semibold text-blue-800">
                          ₹{(quote.total_cost || quote.price || 0).toLocaleString('en-IN')}
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-orange-600">Platform Fee (2.5%)</span>
                        <span className="text-sm font-medium text-orange-600">
                          + ₹{((quote.total_cost || quote.price || 0) * 0.025).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </span>
                      </div>
                      <div className="flex justify-between items-center pt-2 border-t border-blue-200">
                        <span className="font-bold text-blue-900">Total Payable</span>
                        <span className="text-xl font-bold text-blue-900">
                          ₹{((quote.total_cost || quote.price || 0) * 1.025).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Cost Breakdown - Flat Quote */}
                {!quote.is_itemwise && (quote.material_cost || quote.machining_cost) && (
                  <div className="p-4 bg-green-50 rounded-lg border border-green-200">
                    <div className="flex items-center gap-2 mb-3">
                      <DollarSign className="w-4 h-4 text-green-600" />
                      <span className="font-medium text-green-800">Cost Breakdown</span>
                    </div>
                    <div className="space-y-2">
                      {quote.material_provided_by_buyer ? (
                        <div className="flex justify-between text-sm">
                          <span className="text-slate-600">Material</span>
                          <span className="italic text-slate-400">Provided by buyer</span>
                        </div>
                      ) : quote.material_cost > 0 && (
                        <div className="flex justify-between text-sm">
                          <span className="text-slate-600">Material Cost</span>
                          <span className="font-medium">₹{quote.material_cost?.toLocaleString('en-IN')}</span>
                        </div>
                      )}
                      {quote.machining_cost > 0 && (
                        <div className="flex justify-between text-sm">
                          <span className="text-slate-600">Labour/Machining Cost</span>
                          <span className="font-medium">₹{quote.machining_cost?.toLocaleString('en-IN')}</span>
                        </div>
                      )}
                      {quote.additional_costs && Object.keys(quote.additional_costs).length > 0 && (
                        <>
                          <div className="border-t border-green-200 pt-2 mt-2">
                            <p className="text-xs text-slate-500 mb-1">Additional Costs:</p>
                          </div>
                          {Object.entries(quote.additional_costs).map(([key, value]) => (
                            <div key={key} className="flex justify-between text-sm">
                              <span className="text-slate-600 capitalize">{key.replace(/_/g, ' ')}</span>
                              <span className="font-medium">₹{value?.toLocaleString('en-IN')}</span>
                            </div>
                          ))}
                        </>
                      )}
                      <div className="border-t border-green-200 pt-2 mt-2 space-y-2">
                        <div className="flex justify-between">
                          <span className="text-sm text-green-700">Vendor Quote Total</span>
                          <span className="text-base font-semibold text-green-800">
                            ₹{(quote.total_cost || quote.price || 0).toLocaleString('en-IN')}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-orange-600">Platform Fee (2.5%)</span>
                          <span className="text-sm font-medium text-orange-600">
                            + ₹{((quote.total_cost || quote.price || 0) * 0.025).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                          </span>
                        </div>
                        <div className="flex justify-between pt-2 border-t border-green-200">
                          <span className="font-bold text-green-900">Total Payable</span>
                          <span className="text-lg font-bold text-green-900">
                            ₹{((quote.total_cost || quote.price || 0) * 1.025).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                          </span>
                        </div>
                      </div>
                    </div>
                    {quote.cost_breakdown_remarks && (
                      <p className="text-xs text-slate-500 mt-2 italic">{quote.cost_breakdown_remarks}</p>
                    )}
                  </div>
                )}

                {/* Payment Terms */}
                <div className="p-4 bg-slate-50 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <CreditCard className="w-4 h-4 text-slate-500" />
                    <span className="font-medium text-slate-700">Payment Terms</span>
                  </div>
                  <p className="text-slate-900">{getPaymentTermLabel(quote.proposed_payment_terms)}</p>
                  {quote.payment_terms_notes && (
                    <p className="text-sm text-slate-500 mt-1 italic">"{quote.payment_terms_notes}"</p>
                  )}
                </div>

                {/* Vendor Notes */}
                {quote.notes && (
                  <div className="p-4 bg-slate-50 rounded-lg">
                    <div className="flex items-center gap-2 mb-2">
                      <MessageSquare className="w-4 h-4 text-slate-500" />
                      <span className="font-medium text-slate-700">Vendor Notes</span>
                    </div>
                    <p className="text-slate-600">{quote.notes}</p>
                  </div>
                )}

                {/* RFQ Reference */}
                <div className="p-4 bg-slate-50 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="font-medium text-slate-700">RFQ Details</span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div><span className="text-slate-500">Material:</span> <span className="text-slate-900">{quote.rfq_material}</span></div>
                    <div><span className="text-slate-500">Quantity:</span> <span className="text-slate-900">{quote.rfq_quantity} units</span></div>
                    <div><span className="text-slate-500">Tolerance:</span> <span className="text-slate-900">{quote.rfq_tolerance ? `±${quote.rfq_tolerance} mm` : "As per drawing"}</span></div>
                    <div><span className="text-slate-500">Your Preferred Terms:</span> <span className="text-slate-900">{getPaymentTermLabel(quote.rfq_preferred_payment_terms)}</span></div>
                  </div>
                </div>

                {/* Quote Dates */}
                <div className="flex justify-between text-sm text-slate-500">
                  <span>Submitted: {new Date(quote.created_at).toLocaleDateString()}</span>
                  <span>Expires: {new Date(quote.expires_at).toLocaleDateString()}</span>
                </div>
              </TabsContent>

              <TabsContent value="vendor" className="space-y-4 mt-4">
                {/* Contact Info */}
                <div className="p-4 bg-slate-50 rounded-lg space-y-3">
                  <h4 className="font-medium text-slate-700">Contact Information</h4>
                  {quote.vendor_contact_name && (
                    <div className="flex items-center gap-2 text-sm">
                      <User className="w-4 h-4 text-slate-400" />
                      <span>{quote.vendor_contact_name}</span>
                    </div>
                  )}
                  {quote.vendor_email && (
                    <div className="flex items-center gap-2 text-sm">
                      <Mail className="w-4 h-4 text-slate-400" />
                      <a href={`mailto:${quote.vendor_email}`} className="text-orange-600 hover:underline">{quote.vendor_email}</a>
                    </div>
                  )}
                  {quote.vendor_phone && (
                    <div className="flex items-center gap-2 text-sm">
                      <Phone className="w-4 h-4 text-slate-400" />
                      <span>{quote.vendor_phone}</span>
                    </div>
                  )}
                  {quote.vendor_location && (
                    <div className="flex items-center gap-2 text-sm">
                      <MapPin className="w-4 h-4 text-slate-400" />
                      <span>{quote.vendor_location}</span>
                    </div>
                  )}
                  {quote.vendor_website && (
                    <div className="flex items-center gap-2 text-sm">
                      <Globe className="w-4 h-4 text-slate-400" />
                      <a href={quote.vendor_website} target="_blank" rel="noopener noreferrer" className="text-orange-600 hover:underline">{quote.vendor_website}</a>
                    </div>
                  )}
                </div>

                {/* Stats */}
                <div className="grid grid-cols-3 gap-3">
                  <div className="p-3 bg-slate-50 rounded-lg text-center">
                    <p className="text-lg font-bold text-slate-900">{quote.vendor_total_jobs || 0}</p>
                    <p className="text-xs text-slate-500">Completed Jobs</p>
                  </div>
                  <div className="p-3 bg-slate-50 rounded-lg text-center">
                    <p className="text-lg font-bold text-slate-900">{quote.vendor_acceptance_rate || 0}%</p>
                    <p className="text-xs text-slate-500">Acceptance Rate</p>
                  </div>
                  <div className="p-3 bg-slate-50 rounded-lg text-center">
                    <p className="text-lg font-bold text-amber-600">{quote.vendor_rating?.toFixed(1) || "N/A"}</p>
                    <p className="text-xs text-slate-500">Rating</p>
                  </div>
                </div>

                {/* Certifications */}
                {quote.vendor_certifications?.length > 0 && (
                  <div className="p-4 bg-slate-50 rounded-lg">
                    <div className="flex items-center gap-2 mb-2">
                      <Award className="w-4 h-4 text-slate-500" />
                      <span className="font-medium text-slate-700">Certifications</span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {quote.vendor_certifications.map((cert, i) => (
                        <span key={i} className="px-2 py-1 bg-green-100 text-green-700 text-xs rounded-full">{cert}</span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Machines */}
                {quote.vendor_machines?.length > 0 && (
                  <div className="p-4 bg-slate-50 rounded-lg">
                    <div className="flex items-center gap-2 mb-2">
                      <Wrench className="w-4 h-4 text-slate-500" />
                      <span className="font-medium text-slate-700">Available Machines ({quote.vendor_machines.length})</span>
                    </div>
                    <div className="space-y-2 max-h-40 overflow-y-auto">
                      {quote.vendor_machines.map((machine, i) => (
                        <div key={i} className="flex items-center justify-between text-sm p-2 bg-white rounded">
                          <span className="font-medium">{machine.machine_type}</span>
                          <span className="text-slate-500">{machine.brand} {machine.model}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* View Full Profile Link */}
                {quote.vendor_id_ref && (
                  <Link to={`/vendor-profile/${quote.vendor_id_ref}`}>
                    <Button variant="outline" className="w-full">
                      View Full Vendor Profile <ArrowRight className="w-4 h-4 ml-2" />
                    </Button>
                  </Link>
                )}
              </TabsContent>

              <TabsContent value="negotiations" className="space-y-4 mt-4">
                {/* Request Negotiation Button */}
                {quote.status === "pending" && !negotiating && (
                  <Button 
                    onClick={() => setNegotiating(true)}
                    variant="outline"
                    className="w-full border-orange-300 text-orange-600 hover:bg-orange-50"
                    data-testid="start-negotiation-btn"
                  >
                    <RefreshCw className="w-4 h-4 mr-2" /> Request Modification / Negotiate
                  </Button>
                )}

                {/* Negotiation Form */}
                {negotiating && (
                  <div className="p-4 bg-orange-50 border border-orange-200 rounded-lg space-y-4">
                    <h4 className="font-medium text-slate-900">Request Quote Modification</h4>
                    
                    <div>
                      <Label>What would you like to negotiate?</Label>
                      <Select 
                        value={negotiationForm.request_type} 
                        onValueChange={(v) => setNegotiationForm({...negotiationForm, request_type: v})}
                      >
                        <SelectTrigger className="mt-1">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="price">Price Adjustment</SelectItem>
                          <SelectItem value="lead_time">Lead Time Change</SelectItem>
                          <SelectItem value="payment_terms">Payment Terms</SelectItem>
                          <SelectItem value="general">General Request</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    {negotiationForm.request_type === "price" && (
                      <div>
                        <Label>Requested Price ($)</Label>
                        <Input
                          type="number"
                          step="0.01"
                          placeholder={`Current: ₹${quote.price?.toLocaleString('en-IN')}`}
                          value={negotiationForm.requested_price}
                          onChange={(e) => setNegotiationForm({...negotiationForm, requested_price: e.target.value})}
                          className="mt-1"
                        />
                      </div>
                    )}

                    {negotiationForm.request_type === "lead_time" && (
                      <div>
                        <Label>Requested Lead Time (days)</Label>
                        <Input
                          type="number"
                          placeholder={`Current: ${quote.lead_time_days} days`}
                          value={negotiationForm.requested_lead_time}
                          onChange={(e) => setNegotiationForm({...negotiationForm, requested_lead_time: e.target.value})}
                          className="mt-1"
                        />
                      </div>
                    )}

                    {negotiationForm.request_type === "payment_terms" && (
                      <div>
                        <Label>Requested Payment Terms</Label>
                        <Select 
                          value={negotiationForm.requested_payment_terms} 
                          onValueChange={(v) => setNegotiationForm({...negotiationForm, requested_payment_terms: v})}
                        >
                          <SelectTrigger className="mt-1">
                            <SelectValue placeholder="Select preferred terms" />
                          </SelectTrigger>
                          <SelectContent>
                            {PAYMENT_TERMS.map((term) => (
                              <SelectItem key={term.value} value={term.value}>{term.label}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        {(negotiationForm.requested_payment_terms === "milestone_based" || negotiationForm.requested_payment_terms === "custom") && (
                          <div className="mt-2">
                            <Label>{negotiationForm.requested_payment_terms === "milestone_based" ? "Milestone Details" : "Custom Terms Details"}</Label>
                            <Textarea
                              placeholder={negotiationForm.requested_payment_terms === "milestone_based" 
                                ? "e.g., 50% advance, 50% after inspection" 
                                : "Describe your custom payment terms..."}
                              value={negotiationForm.payment_terms_notes}
                              onChange={(e) => setNegotiationForm({...negotiationForm, payment_terms_notes: e.target.value})}
                              className="mt-1"
                              rows={2}
                              data-testid="negotiation-payment-notes"
                            />
                            <p className="text-xs text-slate-400 mt-1">
                              Specify percentages and stages for the payment schedule
                            </p>
                          </div>
                        )}
                      </div>
                    )}

                    <div>
                      <Label>Message to Vendor *</Label>
                      <Textarea
                        placeholder="Explain your request and reasoning..."
                        value={negotiationForm.message}
                        onChange={(e) => setNegotiationForm({...negotiationForm, message: e.target.value})}
                        className="mt-1"
                        rows={3}
                      />
                    </div>

                    <div className="flex gap-2">
                      <Button
                        onClick={submitNegotiation}
                        disabled={submitting}
                        className="bg-orange-600 hover:bg-orange-700"
                      >
                        {submitting ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Send className="w-4 h-4 mr-2" />}
                        Send Request
                      </Button>
                      <Button variant="outline" onClick={() => setNegotiating(false)}>
                        Cancel
                      </Button>
                    </div>
                  </div>
                )}

                {/* Negotiation History */}
                {quote.negotiations?.length > 0 ? (
                  <div className="space-y-3">
                    <h4 className="font-medium text-slate-700 flex items-center gap-2">
                      <History className="w-4 h-4" /> Negotiation History
                    </h4>
                    {quote.negotiations.map((neg) => (
                      <div 
                        key={neg.negotiation_id} 
                        className={`p-4 rounded-lg border ${
                          neg.status === "counter_offered" ? "bg-blue-50 border-blue-200" : "bg-slate-50 border-slate-200"
                        }`}
                      >
                        <div className="flex items-start justify-between mb-2">
                          <div>
                            <span className="font-medium text-slate-900">
                              {neg.request_type === "price" ? "Price Adjustment" :
                               neg.request_type === "lead_time" ? "Lead Time Change" :
                               neg.request_type === "payment_terms" ? "Payment Terms" : "General Request"}
                            </span>
                            <p className="text-xs text-slate-500">{new Date(neg.created_at).toLocaleString()}</p>
                          </div>
                          {getNegotiationStatusBadge(neg.status)}
                        </div>
                        
                        <p className="text-sm text-slate-600 mb-2">"{neg.message}"</p>
                        
                        {/* Show requested changes */}
                        <div className="text-sm space-y-1">
                          {neg.requested_price && (
                            <p className="text-slate-500">
                              Requested Price: <span className="text-slate-900 font-medium">₹{neg.requested_price.toLocaleString('en-IN')}</span>
                              <span className="text-slate-400 ml-2">(was ${neg.original_price?.toLocaleString()})</span>
                            </p>
                          )}
                          {neg.requested_lead_time && (
                            <p className="text-slate-500">
                              Requested Lead Time: <span className="text-slate-900 font-medium">{neg.requested_lead_time} days</span>
                              <span className="text-slate-400 ml-2">(was {neg.original_lead_time} days)</span>
                            </p>
                          )}
                          {neg.requested_payment_terms && (
                            <p className="text-slate-500">
                              Requested Terms: <span className="text-slate-900 font-medium">{getPaymentTermLabel(neg.requested_payment_terms)}</span>
                            </p>
                          )}
                        </div>

                        {/* Vendor Response */}
                        {neg.response && (
                          <div className="mt-3 pt-3 border-t border-slate-200">
                            <p className="text-sm font-medium text-slate-700">Vendor Response:</p>
                            <p className="text-sm text-slate-600">"{neg.response}"</p>
                          </div>
                        )}

                        {/* Counter Offer Details */}
                        {neg.status === "counter_offered" && (
                          <div className="mt-3 p-3 bg-white rounded border border-blue-200">
                            <p className="text-sm font-medium text-blue-800 mb-2">Counter Offer:</p>
                            <div className="text-sm space-y-1">
                              {neg.counter_price && (
                                <p>Price: <span className="font-medium">₹{neg.counter_price.toLocaleString('en-IN')}</span></p>
                              )}
                              {neg.counter_lead_time && (
                                <p>Lead Time: <span className="font-medium">{neg.counter_lead_time} days</span></p>
                              )}
                              {neg.counter_payment_terms && (
                                <p>Terms: <span className="font-medium">{getPaymentTermLabel(neg.counter_payment_terms)}</span></p>
                              )}
                            </div>
                            <Button
                              size="sm"
                              onClick={() => acceptCounterOffer(neg.negotiation_id)}
                              className="mt-3 bg-green-600 hover:bg-green-700"
                            >
                              <CheckCircle2 className="w-4 h-4 mr-1" /> Accept Counter Offer
                            </Button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : !negotiating && (
                  <div className="text-center py-8 text-slate-500">
                    <History className="w-12 h-12 mx-auto mb-2 text-slate-300" />
                    <p>No negotiations yet</p>
                    <p className="text-sm">Click the button above to start a negotiation</p>
                  </div>
                )}
              </TabsContent>
            </Tabs>

            {/* Action Buttons */}
            {quote.status === "pending" && (
              <DialogFooter className="mt-6 pt-4 border-t flex gap-2">
                <Link to={`/chat?with=${quote.vendor_user_id}&rfq=${rfqId}`}>
                  <Button variant="outline">
                    <MessageSquare className="w-4 h-4 mr-2" /> Chat with Vendor
                  </Button>
                </Link>
              </DialogFooter>
            )}
          </>
        ) : (
          <div className="text-center py-12 text-slate-500">
            Failed to load quote details
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default QuoteDetailModal;
