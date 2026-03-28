import { useState, useEffect } from "react";
import { api } from "../App";
import { Button } from "./ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "./ui/dialog";
import { Textarea } from "./ui/textarea";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Badge } from "./ui/badge";
import { toast } from "sonner";
import { 
  Shield, ClipboardCheck, ShieldCheck, User, Building2, 
  Clock, CheckCircle2, XCircle, AlertTriangle, FileText,
  Image as ImageIcon, Download, Loader2, RefreshCw, Eye,
  MapPin, Calendar, CalendarClock, CreditCard
} from "lucide-react";

const STATUS_CONFIG = {
  requested: { label: "Requested", color: "bg-blue-100 text-blue-700", icon: Clock },
  payment_pending: { label: "Payment Pending", color: "bg-yellow-100 text-yellow-700", icon: Clock },
  payment_completed: { label: "Payment Completed", color: "bg-green-100 text-green-700", icon: CheckCircle2 },
  awaiting_assignment: { label: "Awaiting Assignment", color: "bg-purple-100 text-purple-700", icon: Clock },
  inspector_assigned: { label: "Inspector Assigned", color: "bg-blue-100 text-blue-700", icon: User },
  in_progress: { label: "In Progress", color: "bg-orange-100 text-orange-700", icon: ClipboardCheck },
  report_submitted: { label: "Report Submitted", color: "bg-indigo-100 text-indigo-700", icon: FileText },
  approved: { label: "Approved", color: "bg-green-100 text-green-700", icon: CheckCircle2 },
  rejected: { label: "Rejected", color: "bg-red-100 text-red-700", icon: XCircle },
  re_inspection_requested: { label: "Re-inspection Requested", color: "bg-amber-100 text-amber-700", icon: RefreshCw },
  completed: { label: "Completed", color: "bg-green-100 text-green-700", icon: CheckCircle2 },
  cancelled: { label: "Cancelled", color: "bg-slate-100 text-slate-700", icon: XCircle }
};

const RESULT_CONFIG = {
  pass: { label: "PASS", color: "bg-green-500 text-white", icon: CheckCircle2 },
  fail: { label: "FAIL", color: "bg-red-500 text-white", icon: XCircle },
  conditional_pass: { label: "CONDITIONAL PASS", color: "bg-yellow-500 text-white", icon: AlertTriangle }
};

const InspectionStatusCard = ({ orderId, isBuyer = false, isVendor = false, onRefresh }) => {
  const [loading, setLoading] = useState(true);
  const [inspection, setInspection] = useState(null);
  const [showReportModal, setShowReportModal] = useState(false);
  const [showApprovalModal, setShowApprovalModal] = useState(false);
  const [showScheduleModal, setShowScheduleModal] = useState(false);
  const [rejectionReason, setRejectionReason] = useState("");
  const [actionLoading, setActionLoading] = useState(false);
  const [scheduleForm, setScheduleForm] = useState({
    scheduled_date: "",
    scheduled_time: "",
    vendor_notes: ""
  });

  useEffect(() => {
    fetchInspection();
  }, [orderId]);

  const fetchInspection = async () => {
    setLoading(true);
    try {
      const res = await api.get(`/orders/${orderId}/inspection`);
      setInspection(res.data.inspection);
    } catch (error) {
      console.error("Failed to fetch inspection:", error);
    } finally {
      setLoading(false);
    }
  };

  const openScheduleModal = () => {
    // Set default date to tomorrow
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const defaultDate = tomorrow.toISOString().split('T')[0];
    
    setScheduleForm({ 
      scheduled_date: inspection?.scheduled_date || defaultDate,
      scheduled_time: inspection?.scheduled_time || "10:00",
      vendor_notes: inspection?.vendor_notes || ""
    });
    setShowScheduleModal(true);
  };

  const handleScheduleInspection = async () => {
    if (!scheduleForm.scheduled_date) {
      toast.error("Please select a date for the inspection");
      return;
    }
    
    setActionLoading(true);
    try {
      await api.post(`/vendor/orders/${orderId}/schedule-inspection`, {
        scheduled_date: scheduleForm.scheduled_date,
        scheduled_time: scheduleForm.scheduled_time,
        vendor_notes: scheduleForm.vendor_notes
      });
      
      toast.success("Inspection scheduled successfully!");
      setShowScheduleModal(false);
      fetchInspection();
      onRefresh?.();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to schedule inspection");
    } finally {
      setActionLoading(false);
    }
  };

  const handleApproveReject = async (action) => {
    setActionLoading(true);
    try {
      await api.post(`/inspections/${inspection.inspection_id}/approve`, {
        action,
        rejection_reason: action === "reject" ? rejectionReason : null
      });
      
      toast.success(`Inspection ${action}ed successfully`);
      setShowApprovalModal(false);
      fetchInspection();
      onRefresh?.();
    } catch (error) {
      toast.error(error.response?.data?.detail || `Failed to ${action} inspection`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleRequestReinspection = async () => {
    setActionLoading(true);
    try {
      await api.post(`/inspections/${inspection.inspection_id}/request-reinspection`, {
        reason: rejectionReason
      });
      
      toast.success("Re-inspection requested");
      setShowApprovalModal(false);
      fetchInspection();
      onRefresh?.();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to request re-inspection");
    } finally {
      setActionLoading(false);
    }
  };

  const handlePayInspectionFee = async () => {
    setActionLoading(true);
    try {
      // Step 1: Create Razorpay order
      const { data } = await api.post(`/inspections/${inspection.inspection_id}/create-razorpay-order`);

      // Step 2: Open Razorpay checkout
      const options = {
        key: data.key_id,
        amount: data.amount,
        currency: data.currency,
        name: "OEMLinker",
        description: `Inspection Fee - ${inspection.inspection_type === "basic" ? "Basic" : "Certified"} Inspection`,
        order_id: data.razorpay_order_id,
        handler: async (response) => {
          try {
            await api.post(`/inspections/${inspection.inspection_id}/verify-payment`, {
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
            });
            toast.success("Inspection fee paid successfully!");
            fetchInspection();
            onRefresh?.();
          } catch (err) {
            toast.error(err.response?.data?.detail || "Payment verification failed");
          }
        },
        prefill: data.prefill || {},
        theme: { color: "#f97316" },
        modal: { ondismiss: () => setActionLoading(false) }
      };

      if (!window.Razorpay) {
        const script = document.createElement("script");
        script.src = "https://checkout.razorpay.com/v1/checkout.js";
        script.onload = () => { new window.Razorpay(options).open(); };
        document.body.appendChild(script);
      } else {
        new window.Razorpay(options).open();
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to initiate payment");
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <Card className="border-slate-200">
        <CardContent className="py-8 flex items-center justify-center">
          <Loader2 className="w-6 h-6 animate-spin text-orange-600" />
        </CardContent>
      </Card>
    );
  }

  if (!inspection) {
    return null;
  }

  const statusConfig = STATUS_CONFIG[inspection.status] || STATUS_CONFIG.requested;
  const StatusIcon = statusConfig.icon;
  const resultConfig = inspection.result ? RESULT_CONFIG[inspection.result] : null;

  return (
    <>
      <Card className="border-slate-200">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Shield className="w-5 h-5 text-orange-600" />
              Inspection Status
            </div>
            <Badge className={statusConfig.color}>
              <StatusIcon className="w-3 h-3 mr-1" />
              {statusConfig.label}
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Inspection Type */}
          <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
            <div className="flex items-center gap-2">
              {inspection.inspection_type === "basic" ? (
                <ClipboardCheck className="w-4 h-4 text-blue-600" />
              ) : (
                <ShieldCheck className="w-4 h-4 text-purple-600" />
              )}
              <span className="text-sm font-medium">
                {inspection.inspection_type === "basic" ? "Basic Inspection" : "Certified Inspection"}
              </span>
            </div>
            <span className="text-sm font-medium text-slate-600">
              ₹{inspection.inspection_fee?.toLocaleString('en-IN')}
            </span>
          </div>

          {/* Inspector/Agency Info */}
          {(inspection.inspector_name || inspection.agency_name) && (
            <div className="flex items-center gap-3 p-3 bg-blue-50 rounded-lg">
              {inspection.inspector_name ? (
                <>
                  <User className="w-5 h-5 text-blue-600" />
                  <div>
                    <p className="text-sm font-medium text-blue-800">Inspector Assigned</p>
                    <p className="text-sm text-blue-600">{inspection.inspector_name}</p>
                  </div>
                </>
              ) : (
                <>
                  <Building2 className="w-5 h-5 text-purple-600" />
                  <div>
                    <p className="text-sm font-medium text-purple-800">Agency Assigned</p>
                    <p className="text-sm text-purple-600">{inspection.agency_name}</p>
                    {inspection.agency_contact && (
                      <p className="text-xs text-purple-500">{inspection.agency_contact}</p>
                    )}
                  </div>
                </>
              )}
            </div>
          )}

          {/* Result Badge */}
          {resultConfig && (
            <div className={`p-4 rounded-lg ${resultConfig.color} text-center`}>
              <resultConfig.icon className="w-8 h-8 mx-auto mb-2" />
              <p className="text-lg font-bold">{resultConfig.label}</p>
              {inspection.remarks && (
                <p className="text-sm mt-1 opacity-90">{inspection.remarks}</p>
              )}
            </div>
          )}

          {/* Inspection Date */}
          {inspection.inspection_date && (
            <div className="flex items-center gap-2 text-sm text-slate-600">
              <Calendar className="w-4 h-4" />
              <span>Inspected on: {new Date(inspection.inspection_date).toLocaleDateString()}</span>
            </div>
          )}

          {/* Geo Location */}
          {inspection.geo_location && (
            <div className="flex items-center gap-2 text-sm text-slate-600">
              <MapPin className="w-4 h-4" />
              <span>Location verified</span>
            </div>
          )}

          {/* Defects Found */}
          {inspection.defects_found && inspection.defects_found.length > 0 && (
            <div className="p-3 bg-red-50 rounded-lg">
              <p className="text-sm font-medium text-red-700 mb-2">Defects Found:</p>
              <ul className="list-disc list-inside text-sm text-red-600">
                {inspection.defects_found.map((defect, idx) => (
                  <li key={idx}>{defect}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Images Preview */}
          {inspection.image_urls && inspection.image_urls.length > 0 && (
            <div>
              <p className="text-sm font-medium text-slate-700 mb-2 flex items-center gap-1">
                <ImageIcon className="w-4 h-4" /> Inspection Images ({inspection.image_urls.length})
              </p>
              <div className="flex gap-2 overflow-x-auto pb-2">
                {inspection.image_urls.slice(0, 4).map((url, idx) => (
                  <a 
                    key={idx} 
                    href={url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="flex-shrink-0"
                  >
                    <img 
                      src={url} 
                      alt={`Inspection ${idx + 1}`}
                      className="w-20 h-20 object-cover rounded-lg border border-slate-200 hover:border-orange-400 transition-colors"
                    />
                  </a>
                ))}
                {inspection.image_urls.length > 4 && (
                  <div className="w-20 h-20 bg-slate-100 rounded-lg flex items-center justify-center text-sm text-slate-500">
                    +{inspection.image_urls.length - 4}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Report Files */}
          {inspection.report_urls && inspection.report_urls.length > 0 && (
            <div>
              <p className="text-sm font-medium text-slate-700 mb-2 flex items-center gap-1">
                <FileText className="w-4 h-4" /> Inspection Reports
              </p>
              <div className="space-y-2">
                {inspection.report_urls.map((url, idx) => (
                  <a 
                    key={idx}
                    href={url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 p-2 bg-slate-50 rounded hover:bg-slate-100 transition-colors"
                  >
                    <FileText className="w-4 h-4 text-orange-600" />
                    <span className="text-sm text-slate-700">Report {idx + 1}</span>
                    <Download className="w-4 h-4 text-slate-400 ml-auto" />
                  </a>
                ))}
              </div>
            </div>
          )}

          {/* Buyer Payment Action */}
          {isBuyer && inspection.status === "payment_pending" && (
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg space-y-3" data-testid="inspection-payment-section">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-amber-800">Inspection Fee Due</p>
                  <p className="text-xs text-amber-600">Pay to proceed with inspector assignment</p>
                </div>
                <p className="text-lg font-bold text-amber-900">
                  ₹{inspection.inspection_fee?.toLocaleString('en-IN')}
                </p>
              </div>
              <Button
                onClick={handlePayInspectionFee}
                disabled={actionLoading}
                className="w-full bg-orange-500 hover:bg-orange-600"
                data-testid="pay-inspection-fee-btn"
              >
                {actionLoading ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <CreditCard className="w-4 h-4 mr-2" />
                )}
                Pay ₹{inspection.inspection_fee?.toLocaleString('en-IN')} via Razorpay
              </Button>
            </div>
          )}

          {/* Payment Completed Badge */}
          {inspection.payment_status === "paid" && inspection.razorpay_payment_id && (
            <div className="flex items-center gap-2 p-2 bg-green-50 rounded-lg text-xs text-green-700">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Paid via Razorpay</span>
              <span className="font-mono text-green-600 ml-auto">{inspection.razorpay_payment_id}</span>
            </div>
          )}

          {/* Buyer Actions */}
          {isBuyer && inspection.status === "report_submitted" && (
            <div className="flex gap-2 pt-2">
              <Button 
                onClick={() => setShowApprovalModal(true)}
                className="flex-1 bg-green-600 hover:bg-green-700"
                data-testid="approve-inspection-btn"
              >
                <CheckCircle2 className="w-4 h-4 mr-1" /> Review & Approve
              </Button>
            </div>
          )}

          {isBuyer && (inspection.status === "approved" || inspection.status === "rejected") && (
            <div className="pt-2">
              <Button 
                variant="outline"
                onClick={() => setShowApprovalModal(true)}
                className="w-full"
                data-testid="request-reinspection-btn"
              >
                <RefreshCw className="w-4 h-4 mr-1" /> Request Re-inspection
              </Button>
            </div>
          )}

          {/* Vendor Actions - Schedule Inspection */}
          {isVendor && (inspection.status === "awaiting_assignment" || inspection.status === "payment_completed" || inspection.status === "re_inspection_requested") && (
            <div className="pt-2">
              <Button 
                onClick={openScheduleModal}
                className="w-full bg-orange-600 hover:bg-orange-700"
                data-testid="vendor-schedule-inspection-btn"
              >
                <CalendarClock className="w-4 h-4 mr-1" /> Schedule Inspection
              </Button>
            </div>
          )}

          {/* Show scheduled info for vendor */}
          {isVendor && inspection.scheduled_date && (
            <div className="pt-2 p-3 bg-blue-50 rounded-lg">
              <p className="text-sm font-medium text-blue-700 flex items-center gap-1">
                <Calendar className="w-4 h-4" /> Scheduled
              </p>
              <p className="text-blue-600">
                {new Date(inspection.scheduled_date).toLocaleDateString('en-IN', { 
                  weekday: 'long', 
                  year: 'numeric', 
                  month: 'long', 
                  day: 'numeric' 
                })}
                {inspection.scheduled_time && ` at ${inspection.scheduled_time}`}
              </p>
              {inspection.vendor_notes && (
                <p className="text-xs text-blue-500 mt-1">{inspection.vendor_notes}</p>
              )}
            </div>
          )}

          {/* View Full Report */}
          {inspection.result && (
            <Button 
              variant="outline"
              onClick={() => setShowReportModal(true)}
              className="w-full"
              data-testid="view-full-report-btn"
            >
              <Eye className="w-4 h-4 mr-1" /> View Full Report
            </Button>
          )}
        </CardContent>
      </Card>

      {/* Approval Modal */}
      <Dialog open={showApprovalModal} onOpenChange={setShowApprovalModal}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Review Inspection Result</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            {resultConfig && (
              <div className={`p-4 rounded-lg ${resultConfig.color} text-center`}>
                <resultConfig.icon className="w-8 h-8 mx-auto mb-1" />
                <p className="font-bold">{resultConfig.label}</p>
              </div>
            )}

            {inspection.remarks && (
              <div className="p-3 bg-slate-50 rounded-lg">
                <p className="text-sm text-slate-500">Inspector Remarks:</p>
                <p className="text-sm text-slate-700 mt-1">{inspection.remarks}</p>
              </div>
            )}

            <div>
              <label className="text-sm font-medium">Comments (for rejection/re-inspection)</label>
              <Textarea
                placeholder="Enter reason for rejection or re-inspection..."
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.target.value)}
                className="mt-1"
                rows={3}
              />
            </div>

            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={() => handleApproveReject("reject")}
                disabled={actionLoading}
                className="flex-1"
              >
                {actionLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Reject"}
              </Button>
              <Button
                onClick={() => handleApproveReject("approve")}
                disabled={actionLoading}
                className="flex-1 bg-green-600 hover:bg-green-700"
              >
                {actionLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Approve"}
              </Button>
            </div>

            <Button
              variant="ghost"
              onClick={handleRequestReinspection}
              disabled={actionLoading}
              className="w-full text-amber-600 hover:text-amber-700"
            >
              <RefreshCw className="w-4 h-4 mr-1" /> Request Re-inspection Instead
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Full Report Modal */}
      <Dialog open={showReportModal} onOpenChange={setShowReportModal}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileText className="w-5 h-5 text-orange-600" />
              Inspection Report
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            {/* Result */}
            {resultConfig && (
              <div className={`p-4 rounded-lg ${resultConfig.color} text-center`}>
                <resultConfig.icon className="w-10 h-10 mx-auto mb-2" />
                <p className="text-xl font-bold">{resultConfig.label}</p>
              </div>
            )}

            {/* Details Grid */}
            <div className="grid grid-cols-2 gap-4">
              <div className="p-3 bg-slate-50 rounded">
                <p className="text-xs text-slate-500">Inspection Type</p>
                <p className="font-medium capitalize">{inspection.inspection_type}</p>
              </div>
              <div className="p-3 bg-slate-50 rounded">
                <p className="text-xs text-slate-500">Inspection Date</p>
                <p className="font-medium">
                  {inspection.inspection_date 
                    ? new Date(inspection.inspection_date).toLocaleDateString() 
                    : 'N/A'}
                </p>
              </div>
              <div className="p-3 bg-slate-50 rounded">
                <p className="text-xs text-slate-500">Inspector/Agency</p>
                <p className="font-medium">{inspection.inspector_name || inspection.agency_name || 'N/A'}</p>
              </div>
              <div className="p-3 bg-slate-50 rounded">
                <p className="text-xs text-slate-500">Fee Paid</p>
                <p className="font-medium">₹{inspection.inspection_fee?.toLocaleString('en-IN')}</p>
              </div>
            </div>

            {/* Remarks */}
            {inspection.remarks && (
              <div className="p-4 bg-slate-50 rounded-lg">
                <p className="text-sm font-medium text-slate-700 mb-1">Inspector Remarks</p>
                <p className="text-slate-600">{inspection.remarks}</p>
              </div>
            )}

            {/* Defects */}
            {inspection.defects_found && inspection.defects_found.length > 0 && (
              <div className="p-4 bg-red-50 rounded-lg">
                <p className="text-sm font-medium text-red-700 mb-2">Defects Found:</p>
                <ul className="list-disc list-inside text-red-600">
                  {inspection.defects_found.map((defect, idx) => (
                    <li key={idx}>{defect}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Measurements */}
            {inspection.measurements && Object.keys(inspection.measurements).length > 0 && (
              <div className="p-4 bg-blue-50 rounded-lg">
                <p className="text-sm font-medium text-blue-700 mb-2">Measurements:</p>
                <div className="grid grid-cols-2 gap-2">
                  {Object.entries(inspection.measurements).map(([key, value]) => (
                    <div key={key} className="flex justify-between text-sm">
                      <span className="text-blue-600 capitalize">{key.replace(/_/g, ' ')}:</span>
                      <span className="font-medium text-blue-800">{value}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Images */}
            {inspection.image_urls && inspection.image_urls.length > 0 && (
              <div>
                <p className="text-sm font-medium text-slate-700 mb-2">Inspection Images</p>
                <div className="grid grid-cols-3 gap-2">
                  {inspection.image_urls.map((url, idx) => (
                    <a 
                      key={idx}
                      href={url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <img 
                        src={url}
                        alt={`Inspection ${idx + 1}`}
                        className="w-full h-32 object-cover rounded-lg border hover:border-orange-400"
                      />
                    </a>
                  ))}
                </div>
              </div>
            )}

            {/* Report Files */}
            {inspection.report_urls && inspection.report_urls.length > 0 && (
              <div>
                <p className="text-sm font-medium text-slate-700 mb-2">Report Documents</p>
                {inspection.report_urls.map((url, idx) => (
                  <a
                    key={idx}
                    href={url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 p-3 bg-slate-50 rounded-lg hover:bg-slate-100 mb-2"
                  >
                    <FileText className="w-5 h-5 text-orange-600" />
                    <span>Download Report {idx + 1}</span>
                    <Download className="w-4 h-4 text-slate-400 ml-auto" />
                  </a>
                ))}
              </div>
            )}

            {/* Buyer Notes */}
            {inspection.buyer_notes && (
              <div className="p-4 bg-yellow-50 rounded-lg">
                <p className="text-sm font-medium text-yellow-700 mb-1">Buyer Instructions</p>
                <p className="text-yellow-600">{inspection.buyer_notes}</p>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowReportModal(false)}>Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Schedule Inspection Modal (Vendor) */}
      <Dialog open={showScheduleModal} onOpenChange={setShowScheduleModal}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <CalendarClock className="w-5 h-5 text-orange-600" />
              Schedule Inspection
            </DialogTitle>
          </DialogHeader>
          
          {inspection && (
            <div className="space-y-4 mt-4">
              {/* Inspection Info */}
              <div className="p-3 bg-slate-50 rounded-lg">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-500">Inspection Type</span>
                  <Badge className={inspection.inspection_type === "basic" ? "bg-blue-100 text-blue-700" : "bg-purple-100 text-purple-700"}>
                    {inspection.inspection_type === "basic" ? "Basic" : "Certified"}
                  </Badge>
                </div>
                <div className="flex items-center justify-between mt-2">
                  <span className="text-sm text-slate-500">Fee</span>
                  <span className="font-medium">₹{inspection.inspection_fee?.toLocaleString('en-IN')}</span>
                </div>
              </div>

              <div>
                <Label>Inspection Date *</Label>
                <Input
                  type="date"
                  value={scheduleForm.scheduled_date}
                  onChange={(e) => setScheduleForm(prev => ({ ...prev, scheduled_date: e.target.value }))}
                  className="mt-1"
                  min={new Date().toISOString().split('T')[0]}
                  data-testid="inspection-date-input"
                />
              </div>

              <div>
                <Label>Preferred Time</Label>
                <Input
                  type="time"
                  value={scheduleForm.scheduled_time}
                  onChange={(e) => setScheduleForm(prev => ({ ...prev, scheduled_time: e.target.value }))}
                  className="mt-1"
                  data-testid="inspection-time-input"
                />
              </div>

              <div>
                <Label>Notes for Inspector</Label>
                <Textarea
                  placeholder="Any special instructions or access details for the inspection..."
                  value={scheduleForm.vendor_notes}
                  onChange={(e) => setScheduleForm(prev => ({ ...prev, vendor_notes: e.target.value }))}
                  className="mt-1"
                  rows={3}
                  data-testid="vendor-notes-input"
                />
              </div>

              <p className="text-xs text-slate-500">
                An inspector will be assigned by the platform based on availability and location.
              </p>
            </div>
          )}

          <DialogFooter className="mt-4">
            <Button variant="outline" onClick={() => setShowScheduleModal(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleScheduleInspection}
              disabled={actionLoading}
              className="bg-orange-600 hover:bg-orange-700"
              data-testid="confirm-schedule-btn"
            >
              {actionLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Schedule Inspection"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default InspectionStatusCard;
