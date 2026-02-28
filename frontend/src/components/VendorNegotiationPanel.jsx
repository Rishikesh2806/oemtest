import { useState, useEffect } from "react";
import { api } from "../App";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Textarea } from "./ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { toast } from "sonner";
import {
  RefreshCw, CheckCircle2, XCircle, MessageSquare,
  DollarSign, Clock, CreditCard, Loader2, Send, AlertCircle
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

const VendorNegotiationPanel = ({ quoteId, onNegotiationResolved }) => {
  const [negotiations, setNegotiations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [respondingTo, setRespondingTo] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  
  const [responseForm, setResponseForm] = useState({
    action: "accept",
    message: "",
    counter_price: "",
    counter_lead_time: "",
    counter_payment_terms: ""
  });

  useEffect(() => {
    if (quoteId) {
      fetchNegotiations();
    }
  }, [quoteId]);

  const fetchNegotiations = async () => {
    try {
      const response = await api.get(`/quotes/${quoteId}/negotiations`);
      setNegotiations(response.data);
    } catch (error) {
      console.error("Failed to fetch negotiations");
    } finally {
      setLoading(false);
    }
  };

  const submitResponse = async (negotiationId) => {
    setSubmitting(true);
    try {
      const payload = {
        action: responseForm.action,
        message: responseForm.message || null,
        counter_price: responseForm.counter_price ? parseFloat(responseForm.counter_price) : null,
        counter_lead_time: responseForm.counter_lead_time ? parseInt(responseForm.counter_lead_time) : null,
        counter_payment_terms: responseForm.counter_payment_terms || null
      };
      
      await api.post(`/quotes/${quoteId}/negotiate/${negotiationId}/respond`, payload);
      toast.success(
        responseForm.action === "accept" ? "Request accepted" :
        responseForm.action === "counter" ? "Counter offer sent" : "Request declined"
      );
      setRespondingTo(null);
      setResponseForm({
        action: "accept",
        message: "",
        counter_price: "",
        counter_lead_time: "",
        counter_payment_terms: ""
      });
      fetchNegotiations();
      if (onNegotiationResolved) onNegotiationResolved();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to respond");
    } finally {
      setSubmitting(false);
    }
  };

  const pendingNegotiations = negotiations.filter(n => n.status === "pending");

  if (loading) {
    return (
      <div className="flex items-center justify-center py-4">
        <Loader2 className="w-5 h-5 animate-spin text-orange-600" />
      </div>
    );
  }

  if (pendingNegotiations.length === 0) {
    return null;
  }

  return (
    <Card className="border-amber-200 bg-amber-50" data-testid="vendor-negotiation-panel">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center gap-2 text-amber-800">
          <AlertCircle className="w-5 h-5" />
          Negotiation Requests ({pendingNegotiations.length})
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {pendingNegotiations.map((neg) => (
          <div key={neg.negotiation_id} className="bg-white rounded-lg p-4 border border-amber-200">
            {/* Request Header */}
            <div className="flex items-start justify-between mb-3">
              <div>
                <span className="font-medium text-slate-900">
                  {neg.request_type === "price" ? "Price Adjustment Request" :
                   neg.request_type === "lead_time" ? "Lead Time Change Request" :
                   neg.request_type === "payment_terms" ? "Payment Terms Request" : "General Request"}
                </span>
                <p className="text-xs text-slate-500">
                  From: {neg.buyer_name} | {new Date(neg.created_at).toLocaleString()}
                </p>
              </div>
              <span className="px-2 py-1 bg-amber-100 text-amber-700 text-xs rounded-full font-medium">
                Pending Response
              </span>
            </div>

            {/* Request Details */}
            <div className="bg-slate-50 p-3 rounded mb-3">
              <p className="text-sm text-slate-700 mb-2">"{neg.message}"</p>
              <div className="text-sm space-y-1">
                {neg.requested_price && (
                  <p className="flex items-center gap-2">
                    <DollarSign className="w-4 h-4 text-slate-400" />
                    <span>Requested: <strong>${neg.requested_price.toLocaleString()}</strong></span>
                    <span className="text-slate-400">(Current: ${neg.original_price?.toLocaleString()})</span>
                  </p>
                )}
                {neg.requested_lead_time && (
                  <p className="flex items-center gap-2">
                    <Clock className="w-4 h-4 text-slate-400" />
                    <span>Requested: <strong>{neg.requested_lead_time} days</strong></span>
                    <span className="text-slate-400">(Current: {neg.original_lead_time} days)</span>
                  </p>
                )}
                {neg.requested_payment_terms && (
                  <p className="flex items-center gap-2">
                    <CreditCard className="w-4 h-4 text-slate-400" />
                    <span>Requested: <strong>{getPaymentTermLabel(neg.requested_payment_terms)}</strong></span>
                  </p>
                )}
              </div>
            </div>

            {/* Response Actions */}
            {respondingTo === neg.negotiation_id ? (
              <div className="space-y-3 pt-3 border-t">
                <div>
                  <Label>Your Response</Label>
                  <Select 
                    value={responseForm.action} 
                    onValueChange={(v) => setResponseForm({...responseForm, action: v})}
                  >
                    <SelectTrigger className="mt-1">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="accept">Accept Request</SelectItem>
                      <SelectItem value="counter">Make Counter Offer</SelectItem>
                      <SelectItem value="reject">Decline Request</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {responseForm.action === "counter" && (
                  <div className="space-y-3 p-3 bg-blue-50 rounded-lg">
                    <p className="text-sm font-medium text-blue-800">Your Counter Offer:</p>
                    {neg.requested_price && (
                      <div>
                        <Label>Counter Price ($)</Label>
                        <Input
                          type="number"
                          step="0.01"
                          placeholder={`Original: $${neg.original_price}`}
                          value={responseForm.counter_price}
                          onChange={(e) => setResponseForm({...responseForm, counter_price: e.target.value})}
                          className="mt-1"
                        />
                      </div>
                    )}
                    {neg.requested_lead_time && (
                      <div>
                        <Label>Counter Lead Time (days)</Label>
                        <Input
                          type="number"
                          placeholder={`Original: ${neg.original_lead_time} days`}
                          value={responseForm.counter_lead_time}
                          onChange={(e) => setResponseForm({...responseForm, counter_lead_time: e.target.value})}
                          className="mt-1"
                        />
                      </div>
                    )}
                    {neg.requested_payment_terms && (
                      <div>
                        <Label>Counter Payment Terms</Label>
                        <Select 
                          value={responseForm.counter_payment_terms} 
                          onValueChange={(v) => setResponseForm({...responseForm, counter_payment_terms: v})}
                        >
                          <SelectTrigger className="mt-1">
                            <SelectValue placeholder="Select terms" />
                          </SelectTrigger>
                          <SelectContent>
                            {PAYMENT_TERMS.map((term) => (
                              <SelectItem key={term.value} value={term.value}>{term.label}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    )}
                  </div>
                )}

                <div>
                  <Label>Message (Optional)</Label>
                  <Textarea
                    placeholder="Add a message to the buyer..."
                    value={responseForm.message}
                    onChange={(e) => setResponseForm({...responseForm, message: e.target.value})}
                    className="mt-1"
                    rows={2}
                  />
                </div>

                <div className="flex gap-2">
                  <Button
                    onClick={() => submitResponse(neg.negotiation_id)}
                    disabled={submitting}
                    className={
                      responseForm.action === "accept" ? "bg-green-600 hover:bg-green-700" :
                      responseForm.action === "counter" ? "bg-blue-600 hover:bg-blue-700" :
                      "bg-red-600 hover:bg-red-700"
                    }
                  >
                    {submitting ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : 
                     responseForm.action === "accept" ? <CheckCircle2 className="w-4 h-4 mr-2" /> :
                     responseForm.action === "counter" ? <RefreshCw className="w-4 h-4 mr-2" /> :
                     <XCircle className="w-4 h-4 mr-2" />}
                    {responseForm.action === "accept" ? "Accept" :
                     responseForm.action === "counter" ? "Send Counter" : "Decline"}
                  </Button>
                  <Button variant="outline" onClick={() => setRespondingTo(null)}>
                    Cancel
                  </Button>
                </div>
              </div>
            ) : (
              <div className="flex gap-2 pt-3 border-t">
                <Button
                  onClick={() => {
                    setRespondingTo(neg.negotiation_id);
                    setResponseForm({...responseForm, action: "accept"});
                  }}
                  size="sm"
                  className="bg-green-600 hover:bg-green-700"
                >
                  <CheckCircle2 className="w-4 h-4 mr-1" /> Accept
                </Button>
                <Button
                  onClick={() => {
                    setRespondingTo(neg.negotiation_id);
                    setResponseForm({...responseForm, action: "counter"});
                  }}
                  size="sm"
                  variant="outline"
                  className="border-blue-300 text-blue-600 hover:bg-blue-50"
                >
                  <RefreshCw className="w-4 h-4 mr-1" /> Counter
                </Button>
                <Button
                  onClick={() => {
                    setRespondingTo(neg.negotiation_id);
                    setResponseForm({...responseForm, action: "reject"});
                  }}
                  size="sm"
                  variant="outline"
                  className="border-red-300 text-red-600 hover:bg-red-50"
                >
                  <XCircle className="w-4 h-4 mr-1" /> Decline
                </Button>
              </div>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  );
};

export default VendorNegotiationPanel;
