import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useAuth, api } from "../App";
import DashboardLayout from "../components/layout/DashboardLayout";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Textarea } from "../components/ui/textarea";
import { Label } from "../components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Badge } from "../components/ui/badge";
import { Input } from "../components/ui/input";
import { toast } from "sonner";
import {
  AlertTriangle, MessageSquare, Clock, CheckCircle2, XCircle,
  ArrowLeft, Send, User, Building2, Package, FileText,
  AlertCircle, Eye, RefreshCw, Gavel, DollarSign, Calendar
} from "lucide-react";

// Dispute Types
const DISPUTE_TYPES = {
  quality_issue: { label: "Quality Issue", icon: "🔍", color: "text-red-600" },
  delivery_delay: { label: "Delivery Delay", icon: "🕐", color: "text-amber-600" },
  wrong_specifications: { label: "Wrong Specifications", icon: "📐", color: "text-purple-600" },
  payment_issue: { label: "Payment Issue", icon: "💰", color: "text-green-600" },
  communication: { label: "Communication Problem", icon: "💬", color: "text-blue-600" },
  damaged_goods: { label: "Damaged Goods", icon: "📦", color: "text-orange-600" },
  incomplete_order: { label: "Incomplete Order", icon: "❌", color: "text-red-600" },
  other: { label: "Other", icon: "❓", color: "text-slate-600" }
};

// Status badges
const STATUS_CONFIG = {
  open: { color: "bg-red-100 text-red-700 border-red-200", label: "Open", icon: AlertCircle },
  under_review: { color: "bg-blue-100 text-blue-700 border-blue-200", label: "Under Review", icon: Eye },
  awaiting_response: { color: "bg-amber-100 text-amber-700 border-amber-200", label: "Awaiting Response", icon: Clock },
  escalated: { color: "bg-purple-100 text-purple-700 border-purple-200", label: "Escalated", icon: AlertTriangle },
  resolved: { color: "bg-green-100 text-green-700 border-green-200", label: "Resolved", icon: CheckCircle2 },
  closed: { color: "bg-slate-100 text-slate-700 border-slate-200", label: "Closed", icon: XCircle }
};

// Resolution Types
const RESOLUTION_TYPES = [
  { value: "full_refund", label: "Full Refund", description: "Complete refund to buyer" },
  { value: "partial_refund", label: "Partial Refund", description: "Partial amount refunded" },
  { value: "replacement", label: "Replacement", description: "Vendor provides replacement" },
  { value: "rework", label: "Rework", description: "Vendor reworks the order" },
  { value: "no_action", label: "No Action Required", description: "Issue resolved without action" },
  { value: "mutual_agreement", label: "Mutual Agreement", description: "Both parties agreed on resolution" }
];

// Format date
const formatDate = (dateString) => {
  if (!dateString) return '';
  return new Date(dateString).toLocaleString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
};

// Timeline Event Component
const TimelineEvent = ({ event, isLast }) => {
  const roleColors = {
    admin: "bg-purple-500",
    buyer: "bg-blue-500",
    vendor: "bg-orange-500"
  };
  
  const eventIcons = {
    dispute_created: AlertTriangle,
    response_added: MessageSquare,
    status_changed: RefreshCw,
    dispute_resolved: CheckCircle2
  };
  
  const Icon = eventIcons[event.event] || MessageSquare;
  
  return (
    <div className="flex gap-4">
      <div className="flex flex-col items-center">
        <div className={`w-8 h-8 rounded-full ${roleColors[event.user_role] || 'bg-slate-400'} flex items-center justify-center`}>
          <Icon className="w-4 h-4 text-white" />
        </div>
        {!isLast && <div className="w-0.5 flex-1 bg-slate-200 my-2" />}
      </div>
      <div className="flex-1 pb-6">
        <div className="flex items-center gap-2 mb-1">
          <span className="font-medium text-slate-900">{event.user_name}</span>
          <Badge variant="outline" className="text-xs capitalize">{event.user_role}</Badge>
          <span className="text-xs text-slate-400">{formatDate(event.timestamp)}</span>
        </div>
        <div className="bg-slate-50 rounded-lg p-3 border border-slate-100">
          <p className="text-slate-700 whitespace-pre-wrap">{event.message}</p>
          {event.evidence_urls && event.evidence_urls.length > 0 && (
            <div className="mt-2 pt-2 border-t border-slate-200">
              <p className="text-xs text-slate-500 mb-1">Evidence attached:</p>
              <div className="flex gap-2 flex-wrap">
                {event.evidence_urls.map((url, i) => (
                  <a 
                    key={i} 
                    href={url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-xs text-blue-600 hover:underline"
                  >
                    📎 Attachment {i + 1}
                  </a>
                ))}
              </div>
            </div>
          )}
          {event.resolution_type && (
            <div className="mt-2 pt-2 border-t border-slate-200">
              <p className="text-sm font-medium text-green-700">
                Resolution: {RESOLUTION_TYPES.find(r => r.value === event.resolution_type)?.label || event.resolution_type}
              </p>
              {event.refund_amount && (
                <p className="text-sm text-slate-600">
                  Refund Amount: ₹{event.refund_amount.toLocaleString('en-IN')}
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const DisputeDetailPage = () => {
  const { disputeId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [dispute, setDispute] = useState(null);
  const [order, setOrder] = useState(null);
  const [userRole, setUserRole] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  
  // Response form
  const [responseMessage, setResponseMessage] = useState("");
  
  // Admin resolution form
  const [showResolveForm, setShowResolveForm] = useState(false);
  const [resolutionType, setResolutionType] = useState("");
  const [resolutionNotes, setResolutionNotes] = useState("");
  const [refundAmount, setRefundAmount] = useState("");

  const fetchDispute = async () => {
    setLoading(true);
    try {
      const response = await api.get(`/disputes/${disputeId}`);
      setDispute(response.data.dispute);
      setOrder(response.data.order);
      setUserRole(response.data.user_role);
    } catch (error) {
      console.error("Error fetching dispute:", error);
      toast.error("Failed to load dispute details");
      navigate("/disputes");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDispute();
  }, [disputeId]);

  const handleSubmitResponse = async () => {
    if (!responseMessage.trim()) {
      toast.error("Please enter a message");
      return;
    }
    
    setSubmitting(true);
    try {
      await api.post(`/disputes/${disputeId}/respond`, {
        message: responseMessage,
        evidence_urls: []
      });
      toast.success("Response submitted successfully");
      setResponseMessage("");
      fetchDispute();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to submit response");
    } finally {
      setSubmitting(false);
    }
  };

  const handleResolve = async () => {
    if (!resolutionType || !resolutionNotes.trim()) {
      toast.error("Please fill in all required fields");
      return;
    }
    
    setSubmitting(true);
    try {
      await api.put(`/disputes/${disputeId}/resolve`, {
        resolution_type: resolutionType,
        resolution_notes: resolutionNotes,
        refund_amount: refundAmount ? parseFloat(refundAmount) : null
      });
      toast.success("Dispute resolved successfully");
      setShowResolveForm(false);
      fetchDispute();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to resolve dispute");
    } finally {
      setSubmitting(false);
    }
  };

  const handleStatusChange = async (newStatus) => {
    try {
      await api.put(`/disputes/${disputeId}/status`, {
        status: newStatus,
        notes: `Status changed to ${newStatus}`
      });
      toast.success("Status updated");
      fetchDispute();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to update status");
    }
  };

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-96">
          <RefreshCw className="w-8 h-8 text-orange-500 animate-spin" />
        </div>
      </DashboardLayout>
    );
  }

  if (!dispute) {
    return (
      <DashboardLayout>
        <div className="text-center py-12">
          <AlertTriangle className="w-12 h-12 text-slate-300 mx-auto mb-4" />
          <p className="text-slate-500">Dispute not found</p>
        </div>
      </DashboardLayout>
    );
  }

  const statusConfig = STATUS_CONFIG[dispute.status] || STATUS_CONFIG.open;
  const StatusIcon = statusConfig.icon;
  const typeInfo = DISPUTE_TYPES[dispute.dispute_type] || DISPUTE_TYPES.other;
  const isResolved = dispute.status === 'resolved' || dispute.status === 'closed';
  const isAdmin = userRole === 'admin';

  return (
    <DashboardLayout>
      <div className="space-y-6" data-testid="dispute-detail-page">
        {/* Header */}
        <div className="flex items-center justify-between">
          <Button variant="ghost" onClick={() => navigate("/disputes")} className="text-slate-600">
            <ArrowLeft className="w-4 h-4 mr-2" /> Back to Disputes
          </Button>
          <div className="flex items-center gap-2">
            {dispute.priority === "high" && (
              <Badge className="bg-red-100 text-red-700 border border-red-200">
                High Priority
              </Badge>
            )}
            <Badge className={`${statusConfig.color} border`}>
              <StatusIcon className="w-3 h-3 mr-1" />
              {statusConfig.label}
            </Badge>
          </div>
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Dispute Info & Timeline */}
          <div className="lg:col-span-2 space-y-6">
            {/* Dispute Header Card */}
            <Card className="border-slate-200">
              <CardContent className="pt-6">
                <div className="flex items-start gap-4">
                  <div className="text-4xl">{typeInfo.icon}</div>
                  <div className="flex-1">
                    <h1 className="text-xl font-bold text-slate-900 mb-1">{dispute.subject}</h1>
                    <p className={`text-sm font-medium ${typeInfo.color}`}>{typeInfo.label}</p>
                    <p className="text-slate-600 mt-3">{dispute.description}</p>
                    {dispute.expected_resolution && (
                      <div className="mt-3 p-3 bg-blue-50 rounded-lg border border-blue-100">
                        <p className="text-sm font-medium text-blue-800">Expected Resolution:</p>
                        <p className="text-sm text-blue-700">{dispute.expected_resolution}</p>
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Resolution Card (if resolved) */}
            {dispute.resolution_type && (
              <Card className="border-green-200 bg-green-50">
                <CardHeader className="pb-2">
                  <CardTitle className="text-lg flex items-center gap-2 text-green-800">
                    <Gavel className="w-5 h-5" />
                    Resolution
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <p className="font-medium text-green-900">
                      {RESOLUTION_TYPES.find(r => r.value === dispute.resolution_type)?.label}
                    </p>
                    <p className="text-green-800">{dispute.resolution_notes}</p>
                    {dispute.refund_amount && (
                      <p className="text-green-700 font-medium">
                        Refund Amount: ₹{dispute.refund_amount.toLocaleString('en-IN')}
                      </p>
                    )}
                    <p className="text-sm text-green-600">
                      Resolved on {formatDate(dispute.resolved_at)}
                    </p>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Timeline */}
            <Card className="border-slate-200">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Clock className="w-5 h-5 text-slate-500" />
                  Dispute Timeline
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-0">
                  {dispute.timeline?.map((event, index) => (
                    <TimelineEvent 
                      key={index} 
                      event={event} 
                      isLast={index === dispute.timeline.length - 1}
                    />
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Response Form */}
            {!isResolved && (
              <Card className="border-slate-200">
                <CardHeader>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <MessageSquare className="w-5 h-5 text-blue-500" />
                    Add Response
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <Textarea
                      placeholder="Type your response here..."
                      value={responseMessage}
                      onChange={(e) => setResponseMessage(e.target.value)}
                      rows={4}
                      data-testid="response-textarea"
                    />
                    <div className="flex justify-end">
                      <Button 
                        onClick={handleSubmitResponse} 
                        disabled={submitting || !responseMessage.trim()}
                        data-testid="submit-response-btn"
                      >
                        <Send className="w-4 h-4 mr-2" />
                        {submitting ? "Submitting..." : "Submit Response"}
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Right Column - Details & Actions */}
          <div className="space-y-6">
            {/* Order Info */}
            <Card className="border-slate-200">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-slate-500 uppercase tracking-wider">
                  Order Details
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-sm text-slate-500">Order ID</span>
                  <span className="text-sm font-mono">{dispute.order_id?.slice(-12)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-slate-500">RFQ</span>
                  <span className="text-sm font-medium truncate max-w-[150px]">{dispute.rfq_title}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-slate-500">Order Amount</span>
                  <span className="text-sm font-bold text-slate-900">₹{dispute.order_amount?.toLocaleString('en-IN')}</span>
                </div>
                <div className="pt-2 border-t border-slate-100">
                  <Button 
                    variant="outline" 
                    className="w-full"
                    onClick={() => navigate(`/orders/${dispute.order_id}`)}
                  >
                    <Package className="w-4 h-4 mr-2" />
                    View Order
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Parties */}
            <Card className="border-slate-200">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-slate-500 uppercase tracking-wider">
                  Parties Involved
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="p-3 bg-blue-50 rounded-lg">
                  <div className="flex items-center gap-2 mb-1">
                    <User className="w-4 h-4 text-blue-600" />
                    <span className="text-xs text-blue-600 font-medium uppercase">Buyer</span>
                    {dispute.initiated_by === "buyer" && (
                      <Badge className="text-xs bg-blue-100 text-blue-700">Initiator</Badge>
                    )}
                  </div>
                  <p className="font-medium text-slate-900">{dispute.buyer_name}</p>
                  <p className="text-xs text-slate-500">{dispute.buyer_email}</p>
                </div>
                <div className="p-3 bg-orange-50 rounded-lg">
                  <div className="flex items-center gap-2 mb-1">
                    <Building2 className="w-4 h-4 text-orange-600" />
                    <span className="text-xs text-orange-600 font-medium uppercase">Vendor</span>
                    {dispute.initiated_by === "vendor" && (
                      <Badge className="text-xs bg-orange-100 text-orange-700">Initiator</Badge>
                    )}
                  </div>
                  <p className="font-medium text-slate-900">{dispute.vendor_name}</p>
                </div>
              </CardContent>
            </Card>

            {/* Dispute Info */}
            <Card className="border-slate-200">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-slate-500 uppercase tracking-wider">
                  Dispute Info
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-sm text-slate-500">Dispute ID</span>
                  <span className="text-sm font-mono">{dispute.dispute_id?.slice(-12)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-slate-500">Created</span>
                  <span className="text-sm">{formatDate(dispute.created_at)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-slate-500">Last Updated</span>
                  <span className="text-sm">{formatDate(dispute.updated_at)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-slate-500">Responses</span>
                  <span className="text-sm font-medium">{dispute.timeline?.length || 0}</span>
                </div>
              </CardContent>
            </Card>

            {/* Admin Actions */}
            {isAdmin && !isResolved && (
              <Card className="border-purple-200 bg-purple-50">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-purple-700 uppercase tracking-wider">
                    Admin Actions
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {!showResolveForm ? (
                    <>
                      <div className="space-y-2">
                        <Label className="text-xs text-purple-700">Change Status</Label>
                        <Select onValueChange={handleStatusChange} value={dispute.status}>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="open">Open</SelectItem>
                            <SelectItem value="under_review">Under Review</SelectItem>
                            <SelectItem value="awaiting_response">Awaiting Response</SelectItem>
                            <SelectItem value="escalated">Escalated</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <Button 
                        className="w-full bg-green-600 hover:bg-green-700"
                        onClick={() => setShowResolveForm(true)}
                        data-testid="resolve-dispute-btn"
                      >
                        <Gavel className="w-4 h-4 mr-2" />
                        Resolve Dispute
                      </Button>
                    </>
                  ) : (
                    <div className="space-y-4">
                      <div>
                        <Label className="text-xs">Resolution Type *</Label>
                        <Select onValueChange={setResolutionType} value={resolutionType}>
                          <SelectTrigger>
                            <SelectValue placeholder="Select resolution" />
                          </SelectTrigger>
                          <SelectContent>
                            {RESOLUTION_TYPES.map(r => (
                              <SelectItem key={r.value} value={r.value}>
                                {r.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      
                      {(resolutionType === "full_refund" || resolutionType === "partial_refund") && (
                        <div>
                          <Label className="text-xs">Refund Amount (₹)</Label>
                          <Input
                            type="number"
                            placeholder="Enter amount"
                            value={refundAmount}
                            onChange={(e) => setRefundAmount(e.target.value)}
                            max={dispute.order_amount}
                          />
                          <p className="text-xs text-slate-500 mt-1">
                            Max: ₹{dispute.order_amount?.toLocaleString('en-IN')}
                          </p>
                        </div>
                      )}
                      
                      <div>
                        <Label className="text-xs">Resolution Notes *</Label>
                        <Textarea
                          placeholder="Explain the resolution..."
                          value={resolutionNotes}
                          onChange={(e) => setResolutionNotes(e.target.value)}
                          rows={3}
                        />
                      </div>
                      
                      <div className="flex gap-2">
                        <Button 
                          variant="outline" 
                          onClick={() => setShowResolveForm(false)}
                          className="flex-1"
                        >
                          Cancel
                        </Button>
                        <Button 
                          onClick={handleResolve}
                          disabled={submitting}
                          className="flex-1 bg-green-600 hover:bg-green-700"
                        >
                          {submitting ? "Resolving..." : "Confirm"}
                        </Button>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
};

export default DisputeDetailPage;
