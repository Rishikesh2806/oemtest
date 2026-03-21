import { useState, useEffect } from "react";
import { useParams, useNavigate, useSearchParams, Link } from "react-router-dom";
import { useAuth, api } from "../App";
import DashboardLayout from "../components/layout/DashboardLayout";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "../components/ui/dialog";
import { toast } from "sonner";
import { 
  Package, ArrowLeft, Loader2, CreditCard, 
  CheckCircle2, Clock, Truck, MapPin, AlertCircle,
  Star, MessageSquare, Building2, ThumbsUp, Send,
  FileText, User, Box, Calendar, AlertTriangle, Shield
} from "lucide-react";
import RaiseDisputeForm from "../components/RaiseDisputeForm";
import InspectionRequestModal from "../components/InspectionRequestModal";
import InspectionStatusCard from "../components/InspectionStatusCard";

const OrderDetail = () => {
  const { orderId } = useParams();
  const [searchParams] = useSearchParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [order, setOrder] = useState(null);
  const [orderDetails, setOrderDetails] = useState(null);
  const [loading, setLoading] = useState(true);
  const [processingPayment, setProcessingPayment] = useState(false);
  
  // Rating dialog state
  const [ratingDialogOpen, setRatingDialogOpen] = useState(false);
  const [rating, setRating] = useState({
    overall_rating: 5,
    quality_rating: 5,
    communication_rating: 5,
    delivery_rating: 5,
    review_text: "",
    would_recommend: true
  });
  const [submittingRating, setSubmittingRating] = useState(false);
  
  // Tracking dialog state
  const [trackingDialogOpen, setTrackingDialogOpen] = useState(false);
  const [trackingInfo, setTrackingInfo] = useState({
    courier: "",
    tracking_number: "",
    estimated_delivery: "",
    note: ""
  });
  const [submittingTracking, setSubmittingTracking] = useState(false);
  
  // Dispute state
  const [showDisputeForm, setShowDisputeForm] = useState(false);
  const [hasDispute, setHasDispute] = useState(false);
  const [existingDispute, setExistingDispute] = useState(null);
  
  // Inspection state
  const [showInspectionModal, setShowInspectionModal] = useState(false);

  useEffect(() => {
    fetchOrder();
    fetchOrderDetails();
    fetchDisputeStatus();
  }, [orderId]);

  useEffect(() => {
    const sessionId = searchParams.get("session_id");
    if (sessionId) {
      pollPaymentStatus(sessionId);
    }
  }, [searchParams]);

  const fetchOrder = async () => {
    try {
      const response = await api.get(`/orders/${orderId}`);
      setOrder(response.data);
    } catch (error) {
      toast.error("Failed to load order details");
    } finally {
      setLoading(false);
    }
  };

  const fetchOrderDetails = async () => {
    try {
      const response = await api.get(`/orders/${orderId}/details`);
      setOrderDetails(response.data);
    } catch (error) {
      console.error("Failed to load order details:", error);
    }
  };
  
  const fetchDisputeStatus = async () => {
    try {
      const response = await api.get(`/orders/${orderId}/dispute`);
      setHasDispute(response.data.has_dispute);
      setExistingDispute(response.data.dispute);
    } catch (error) {
      console.error("Failed to load dispute status:", error);
    }
  };

  const handleDisputeSuccess = (dispute) => {
    setShowDisputeForm(false);
    setHasDispute(true);
    setExistingDispute(dispute);
    navigate(`/disputes/${dispute.dispute_id}`);
  };

  const pollPaymentStatus = async (sessionId, attempts = 0) => {
    const maxAttempts = 5;
    const pollInterval = 2000;

    if (attempts >= maxAttempts) {
      toast.error("Payment status check timed out");
      return;
    }

    try {
      const response = await api.get(`/payments/status/${sessionId}`);
      
      if (response.data.payment_status === "paid") {
        toast.success("Payment successful!");
        fetchOrder();
        fetchOrderDetails();
        return;
      } else if (response.data.status === "expired") {
        toast.error("Payment session expired");
        return;
      }

      setTimeout(() => pollPaymentStatus(sessionId, attempts + 1), pollInterval);
    } catch (error) {
      console.error("Error checking payment status:", error);
    }
  };

  const initiatePayment = async () => {
    setProcessingPayment(true);
    try {
      const originUrl = window.location.origin;
      const response = await api.post("/payments/checkout", {
        order_id: orderId,
        origin_url: originUrl
      });
      
      if (response.data.url) {
        window.location.href = response.data.url;
      }
    } catch (error) {
      toast.error("Failed to initiate payment");
      setProcessingPayment(false);
    }
  };

  const updateStatus = async (newStatus, note = "") => {
    try {
      await api.put(`/orders/${orderId}/status`, { status: newStatus, note });
      toast.success("Status updated");
      fetchOrder();
      fetchOrderDetails();
    } catch (error) {
      toast.error("Failed to update status");
    }
  };

  const confirmDelivery = async () => {
    try {
      await api.post(`/orders/${orderId}/confirm-delivery`);
      toast.success("Delivery confirmed! You can now rate the vendor.");
      fetchOrder();
      fetchOrderDetails();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to confirm delivery");
    }
  };

  const submitRating = async () => {
    setSubmittingRating(true);
    try {
      await api.post(`/orders/${orderId}/rate`, rating);
      toast.success("Thank you for your feedback!");
      setRatingDialogOpen(false);
      fetchOrder();
      fetchOrderDetails();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to submit rating");
    } finally {
      setSubmittingRating(false);
    }
  };

  const submitTracking = async () => {
    setSubmittingTracking(true);
    try {
      await api.post(`/orders/${orderId}/add-tracking`, trackingInfo);
      toast.success("Tracking information added");
      setTrackingDialogOpen(false);
      fetchOrder();
      fetchOrderDetails();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to add tracking");
    } finally {
      setSubmittingTracking(false);
    }
  };

  const StarRating = ({ value, onChange, label }) => (
    <div className="space-y-1">
      <Label className="text-sm text-slate-600">{label}</Label>
      <div className="flex gap-1">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            type="button"
            onClick={() => onChange(star)}
            className="focus:outline-none transition-transform hover:scale-110"
          >
            <Star 
              className={`w-7 h-7 ${star <= value ? "fill-amber-400 text-amber-400" : "text-slate-300"}`}
            />
          </button>
        ))}
      </div>
    </div>
  );

  const getStatusIcon = (status) => {
    switch (status) {
      case "pending_payment": return <CreditCard className="w-5 h-5" />;
      case "paid": return <CheckCircle2 className="w-5 h-5" />;
      case "in_production": return <Clock className="w-5 h-5" />;
      case "quality_check": return <Box className="w-5 h-5" />;
      case "dispatched": return <Truck className="w-5 h-5" />;
      case "delivered": return <MapPin className="w-5 h-5" />;
      case "completed": return <CheckCircle2 className="w-5 h-5" />;
      default: return <Package className="w-5 h-5" />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case "pending_payment": return "text-amber-600 bg-amber-100";
      case "paid": return "text-green-600 bg-green-100";
      case "in_production": return "text-blue-600 bg-blue-100";
      case "quality_check": return "text-purple-600 bg-purple-100";
      case "dispatched": return "text-indigo-600 bg-indigo-100";
      case "delivered": return "text-teal-600 bg-teal-100";
      case "completed": return "text-green-600 bg-green-100";
      case "cancelled": return "text-red-600 bg-red-100";
      default: return "text-slate-600 bg-slate-100";
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

  if (!order) {
    return (
      <DashboardLayout>
        <div className="text-center py-12">
          <AlertCircle className="w-16 h-16 text-slate-300 mx-auto mb-4" />
          <p className="text-slate-500">Order not found</p>
        </div>
      </DashboardLayout>
    );
  }

  const isVendor = user?.role === "vendor";
  const isBuyer = user?.role === "buyer";

  const statusFlow = [
    { key: "pending_payment", label: "Pending Payment" },
    { key: "paid", label: "Paid" },
    { key: "in_production", label: "In Production" },
    { key: "quality_check", label: "Quality Check" },
    { key: "dispatched", label: "Dispatched" },
    { key: "delivered", label: "Delivered" },
    { key: "completed", label: "Completed" }
  ];

  const currentStatusIndex = statusFlow.findIndex(s => s.key === order.status);
  const canRate = isBuyer && 
    (order.status === "delivered" || order.status === "completed") && 
    !orderDetails?.is_rated;

  return (
    <DashboardLayout>
      <div className="space-y-6" data-testid="order-detail-page">
        {/* Header */}
        <div className="flex items-center justify-between">
          <Button 
            variant="ghost" 
            onClick={() => navigate(-1)}
            className="text-slate-600"
          >
            <ArrowLeft className="w-4 h-4 mr-2" /> Back
          </Button>
          
          <div className="flex items-center gap-2">
            {/* Dispute Button */}
            {hasDispute && existingDispute ? (
              <Button 
                variant="outline"
                onClick={() => navigate(`/disputes/${existingDispute.dispute_id}`)}
                className="border-amber-300 text-amber-700 hover:bg-amber-50"
                data-testid="view-dispute-btn"
              >
                <AlertTriangle className="w-4 h-4 mr-2" />
                View Dispute ({existingDispute.status})
              </Button>
            ) : order.status !== 'completed' && order.status !== 'cancelled' && (
              <Button 
                variant="outline"
                onClick={() => setShowDisputeForm(true)}
                className="border-red-300 text-red-700 hover:bg-red-50"
                data-testid="raise-dispute-btn"
              >
                <AlertTriangle className="w-4 h-4 mr-2" />
                Raise Dispute
              </Button>
            )}
            
            {/* Request Inspection Button - for buyers when order is ready for delivery */}
            {isBuyer && ['in_production', 'quality_check', 'dispatched'].includes(order.status) && (
              <Button
                variant="outline"
                onClick={() => setShowInspectionModal(true)}
                className="border-emerald-300 text-emerald-700 hover:bg-emerald-50"
                data-testid="request-inspection-btn"
              >
                <Shield className="w-4 h-4 mr-2" />
                Request Inspection
              </Button>
            )}
            
            {canRate && (
              <Button 
                onClick={() => setRatingDialogOpen(true)}
                className="bg-amber-500 hover:bg-amber-600"
                data-testid="rate-vendor-btn"
              >
                <Star className="w-4 h-4 mr-2" /> Rate Vendor
              </Button>
            )}
          </div>
        </div>

        {/* Order Summary */}
        <Card className="border-slate-200">
          <CardHeader>
            <div className="flex items-start justify-between">
              <div>
                <CardTitle className="font-heading text-2xl">
                  {order.po_number ? `PO: ${order.po_number}` : `Order #${order.order_id.slice(-8)}`}
                </CardTitle>
                <p className="text-slate-500 mt-1">
                  Created {new Date(order.created_at).toLocaleDateString()}
                </p>
              </div>
              <div className={`px-4 py-2 rounded-lg ${getStatusColor(order.status)}`}>
                <div className="flex items-center gap-2 font-medium">
                  {getStatusIcon(order.status)}
                  {order.status.replace(/_/g, " ").toUpperCase()}
                </div>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid md:grid-cols-4 gap-4">
              <div className="p-4 bg-slate-50 rounded-lg">
                <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-1">
                  Total Amount
                </p>
                <p className="text-2xl font-bold text-slate-900">
                  ${order.total_amount?.toLocaleString(undefined, {minimumFractionDigits: 2})}
                </p>
                <p className="text-sm text-slate-500">{order.currency}</p>
              </div>
              <div className="p-4 bg-slate-50 rounded-lg">
                <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-1">
                  Payment Status
                </p>
                <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium ${
                  order.payment_status === "paid" 
                    ? "bg-green-100 text-green-700" 
                    : "bg-amber-100 text-amber-700"
                }`}>
                  {order.payment_status === "paid" ? (
                    <CheckCircle2 className="w-4 h-4" />
                  ) : (
                    <Clock className="w-4 h-4" />
                  )}
                  {order.payment_status}
                </span>
              </div>
              <div className="p-4 bg-slate-50 rounded-lg">
                <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-1">
                  RFQ Reference
                </p>
                <p className="text-sm font-mono text-slate-600">
                  {order.rfq_id?.slice(-8)}
                </p>
                {orderDetails?.rfq?.title && (
                  <p className="text-xs text-slate-500 mt-1 truncate">
                    {orderDetails.rfq.title}
                  </p>
                )}
              </div>
              <div className="p-4 bg-slate-50 rounded-lg">
                <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-1">
                  Quantity
                </p>
                <p className="text-2xl font-bold text-slate-900">
                  {orderDetails?.rfq?.quantity || 1}
                </p>
                <p className="text-sm text-slate-500">units</p>
              </div>
            </div>

            {/* Payment Terms - Finalized */}
            {order.payment_terms && (
              <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex items-center gap-2 text-blue-800">
                  <CreditCard className="w-5 h-5" />
                  <p className="font-semibold">Payment Terms (Finalized)</p>
                </div>
                <p className="text-lg font-medium text-blue-900 mt-1">
                  {order.payment_terms_label || order.payment_terms}
                </p>
                {order.payment_terms_notes && (
                  <p className="text-sm text-blue-700 mt-1">{order.payment_terms_notes}</p>
                )}
              </div>
            )}

            {/* Payment Button for Buyer */}
            {isBuyer && order.status === "pending_payment" && order.payment_status !== "paid" && (
              <div className="mt-6 pt-6 border-t border-slate-200">
                <Button
                  onClick={initiatePayment}
                  disabled={processingPayment}
                  className="bg-orange-600 hover:bg-orange-700 w-full md:w-auto"
                  data-testid="pay-now-btn"
                >
                  {processingPayment ? (
                    <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  ) : (
                    <CreditCard className="w-4 h-4 mr-2" />
                  )}
                  Pay Now - ${order.total_amount?.toLocaleString(undefined, {minimumFractionDigits: 2})}
                </Button>
              </div>
            )}

            {/* Confirm Delivery Button for Buyer */}
            {isBuyer && order.status === "dispatched" && !order.delivery_confirmed && (
              <div className="mt-6 pt-6 border-t border-slate-200">
                <Button
                  onClick={confirmDelivery}
                  className="bg-teal-600 hover:bg-teal-700 w-full md:w-auto"
                  data-testid="confirm-delivery-btn"
                >
                  <CheckCircle2 className="w-4 h-4 mr-2" />
                  Confirm Delivery Received
                </Button>
                <p className="text-xs text-slate-500 mt-2">
                  Confirm when you've received the order to rate the vendor
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Vendor/Buyer Info Cards */}
        <div className="grid md:grid-cols-2 gap-6">
          {/* Vendor Info (for Buyer) */}
          {isBuyer && orderDetails?.vendor && (
            <Card className="border-slate-200">
              <CardHeader>
                <CardTitle className="font-heading text-lg flex items-center gap-2">
                  <Building2 className="w-5 h-5 text-orange-600" />
                  Vendor Information
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-600">Company</span>
                    <span className="font-medium">{orderDetails.vendor.company_name}</span>
                  </div>
                  {orderDetails.vendor.rating > 0 && (
                    <div className="flex items-center justify-between">
                      <span className="text-slate-600">Rating</span>
                      <span className="flex items-center gap-1 font-medium">
                        <Star className="w-4 h-4 fill-amber-400 text-amber-400" />
                        {orderDetails.vendor.rating.toFixed(1)}
                      </span>
                    </div>
                  )}
                  {orderDetails.vendor.address && (
                    <div className="flex items-center justify-between">
                      <span className="text-slate-600">Location</span>
                      <span className="text-sm">{orderDetails.vendor.address}</span>
                    </div>
                  )}
                  {orderDetails.vendor.vendor_id && (
                    <Link to={`/vendor-profile/${orderDetails.vendor.vendor_id}`}>
                      <Button variant="outline" size="sm" className="w-full mt-2">
                        View Full Profile
                      </Button>
                    </Link>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Buyer Info (for Vendor) */}
          {isVendor && orderDetails?.buyer && (
            <Card className="border-slate-200">
              <CardHeader>
                <CardTitle className="font-heading text-lg flex items-center gap-2">
                  <User className="w-5 h-5 text-orange-600" />
                  Buyer Information
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-600">Name</span>
                    <span className="font-medium">{orderDetails.buyer.name}</span>
                  </div>
                  {orderDetails.buyer.email && (
                    <div className="flex items-center justify-between">
                      <span className="text-slate-600">Email</span>
                      <span className="text-sm">{orderDetails.buyer.email}</span>
                    </div>
                  )}
                  {orderDetails.buyer.user_id && (
                    <Link to={`/chat?with=${orderDetails.buyer.user_id}`}>
                      <Button variant="outline" size="sm" className="w-full mt-2">
                        <MessageSquare className="w-4 h-4 mr-2" />
                        Message Buyer
                      </Button>
                    </Link>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Tracking Info */}
          {order.tracking_info && (
            <Card className="border-slate-200">
              <CardHeader>
                <CardTitle className="font-heading text-lg flex items-center gap-2">
                  <Truck className="w-5 h-5 text-indigo-600" />
                  Shipping Information
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-600">Courier</span>
                    <span className="font-medium">{order.tracking_info.courier}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-600">Tracking Number</span>
                    <span className="font-mono text-sm bg-slate-100 px-2 py-1 rounded">
                      {order.tracking_info.tracking_number}
                    </span>
                  </div>
                  {order.tracking_info.estimated_delivery && (
                    <div className="flex items-center justify-between">
                      <span className="text-slate-600">Est. Delivery</span>
                      <span>{order.tracking_info.estimated_delivery}</span>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Inspection Status Card */}
        <InspectionStatusCard 
          orderId={orderId} 
          isBuyer={isBuyer}
          isVendor={isVendor}
          onRefresh={() => fetchOrder()}
        />

        {/* Status Timeline */}
        <Card className="border-slate-200">
          <CardHeader>
            <CardTitle className="font-heading text-lg">Order Progress</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between overflow-x-auto pb-4">
              {statusFlow.map((status, i) => {
                const isActive = i <= currentStatusIndex;
                const isCurrent = status.key === order.status;
                
                return (
                  <div key={status.key} className="flex items-center">
                    <div className="flex flex-col items-center">
                      <div className={`w-10 h-10 rounded-full flex items-center justify-center border-2 transition-colors ${
                        isActive 
                          ? "border-orange-600 bg-orange-50 text-orange-600" 
                          : "border-slate-200 bg-white text-slate-400"
                      } ${isCurrent ? "ring-4 ring-orange-200" : ""}`}>
                        {getStatusIcon(status.key)}
                      </div>
                      <span className={`text-xs mt-2 text-center whitespace-nowrap ${
                        isActive ? "text-slate-900 font-medium" : "text-slate-400"
                      }`}>
                        {status.label}
                      </span>
                    </div>
                    {i < statusFlow.length - 1 && (
                      <div className={`w-8 md:w-16 h-0.5 mx-1 ${
                        i < currentStatusIndex ? "bg-orange-600" : "bg-slate-200"
                      }`} />
                    )}
                  </div>
                );
              })}
            </div>

            {/* Vendor Status Update Buttons */}
            {isVendor && order.payment_status === "paid" && order.status !== "completed" && (
              <div className="mt-6 pt-6 border-t border-slate-200">
                <p className="text-sm text-slate-500 mb-3">Update order status:</p>
                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => updateStatus("in_production", "Production started")}
                    disabled={currentStatusIndex >= statusFlow.findIndex(s => s.key === "in_production")}
                    data-testid="status-in_production-btn"
                  >
                    <Clock className="w-4 h-4 mr-1" /> Start Production
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => updateStatus("quality_check", "Quality inspection in progress")}
                    disabled={currentStatusIndex >= statusFlow.findIndex(s => s.key === "quality_check")}
                    data-testid="status-quality_check-btn"
                  >
                    <Box className="w-4 h-4 mr-1" /> Quality Check
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setTrackingDialogOpen(true)}
                    disabled={currentStatusIndex >= statusFlow.findIndex(s => s.key === "dispatched")}
                    data-testid="add-tracking-btn"
                  >
                    <Truck className="w-4 h-4 mr-1" /> Add Tracking & Ship
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Rating Display (if rated) */}
        {orderDetails?.rating && (
          <Card className="border-slate-200 bg-gradient-to-r from-amber-50 to-orange-50">
            <CardHeader>
              <CardTitle className="font-heading text-lg flex items-center gap-2">
                <Star className="w-5 h-5 fill-amber-400 text-amber-400" />
                Your Rating
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-4 gap-4 mb-4">
                {[
                  { label: "Overall", value: orderDetails.rating.overall_rating },
                  { label: "Quality", value: orderDetails.rating.quality_rating },
                  { label: "Communication", value: orderDetails.rating.communication_rating },
                  { label: "Delivery", value: orderDetails.rating.delivery_rating }
                ].map(item => (
                  <div key={item.label} className="text-center">
                    <p className="text-xs text-slate-500 mb-1">{item.label}</p>
                    <div className="flex justify-center gap-0.5">
                      {[1, 2, 3, 4, 5].map(star => (
                        <Star 
                          key={star}
                          className={`w-4 h-4 ${star <= item.value ? "fill-amber-400 text-amber-400" : "text-slate-300"}`}
                        />
                      ))}
                    </div>
                  </div>
                ))}
              </div>
              {orderDetails.rating.review_text && (
                <div className="bg-white p-3 rounded-lg border border-amber-200">
                  <p className="text-sm text-slate-600 italic">"{orderDetails.rating.review_text}"</p>
                </div>
              )}
              {orderDetails.rating.would_recommend && (
                <p className="text-sm text-green-600 mt-3 flex items-center gap-1">
                  <ThumbsUp className="w-4 h-4" /> You recommended this vendor
                </p>
              )}
            </CardContent>
          </Card>
        )}

        {/* Tracking Updates */}
        {order.tracking_updates?.length > 0 && (
          <Card className="border-slate-200">
            <CardHeader>
              <CardTitle className="font-heading text-lg">Activity Log</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {order.tracking_updates.slice().reverse().map((update, i) => (
                  <div key={i} className="flex items-start gap-4">
                    <div className="w-2 h-2 bg-orange-600 rounded-full mt-2" />
                    <div>
                      <p className="font-medium text-slate-900 capitalize">
                        {update.status.replace(/_/g, " ")}
                      </p>
                      {update.note && <p className="text-sm text-slate-500">{update.note}</p>}
                      <p className="text-xs text-slate-400 mt-1">
                        {new Date(update.timestamp).toLocaleString()}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Rating Dialog */}
      <Dialog open={ratingDialogOpen} onOpenChange={setRatingDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Star className="w-5 h-5 text-amber-500" />
              Rate Your Experience
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-5 py-4">
            <StarRating 
              label="Overall Rating" 
              value={rating.overall_rating} 
              onChange={(v) => setRating({...rating, overall_rating: v})}
            />
            <StarRating 
              label="Quality of Work" 
              value={rating.quality_rating} 
              onChange={(v) => setRating({...rating, quality_rating: v})}
            />
            <StarRating 
              label="Communication" 
              value={rating.communication_rating} 
              onChange={(v) => setRating({...rating, communication_rating: v})}
            />
            <StarRating 
              label="Delivery Time" 
              value={rating.delivery_rating} 
              onChange={(v) => setRating({...rating, delivery_rating: v})}
            />
            
            <div className="space-y-2">
              <Label>Write a Review (Optional)</Label>
              <Textarea 
                placeholder="Share your experience with this vendor..."
                value={rating.review_text}
                onChange={(e) => setRating({...rating, review_text: e.target.value})}
                rows={3}
              />
            </div>
            
            <label className="flex items-center gap-2 cursor-pointer">
              <input 
                type="checkbox"
                checked={rating.would_recommend}
                onChange={(e) => setRating({...rating, would_recommend: e.target.checked})}
                className="w-4 h-4 text-orange-600 rounded"
              />
              <span className="text-sm text-slate-600">
                I would recommend this vendor to others
              </span>
            </label>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setRatingDialogOpen(false)}>
              Cancel
            </Button>
            <Button 
              onClick={submitRating} 
              disabled={submittingRating}
              className="bg-amber-500 hover:bg-amber-600"
              data-testid="submit-rating-btn"
            >
              {submittingRating ? (
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
              ) : (
                <Send className="w-4 h-4 mr-2" />
              )}
              Submit Rating
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Tracking Info Dialog */}
      <Dialog open={trackingDialogOpen} onOpenChange={setTrackingDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Truck className="w-5 h-5 text-indigo-600" />
              Add Shipping Details
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Courier / Shipping Company *</Label>
              <Input 
                placeholder="e.g., FedEx, DHL, UPS"
                value={trackingInfo.courier}
                onChange={(e) => setTrackingInfo({...trackingInfo, courier: e.target.value})}
              />
            </div>
            
            <div className="space-y-2">
              <Label>Tracking Number *</Label>
              <Input 
                placeholder="Enter tracking number"
                value={trackingInfo.tracking_number}
                onChange={(e) => setTrackingInfo({...trackingInfo, tracking_number: e.target.value})}
              />
            </div>
            
            <div className="space-y-2">
              <Label>Estimated Delivery Date</Label>
              <Input 
                type="date"
                value={trackingInfo.estimated_delivery}
                onChange={(e) => setTrackingInfo({...trackingInfo, estimated_delivery: e.target.value})}
              />
            </div>
            
            <div className="space-y-2">
              <Label>Additional Notes</Label>
              <Textarea 
                placeholder="Any additional shipping information..."
                value={trackingInfo.note}
                onChange={(e) => setTrackingInfo({...trackingInfo, note: e.target.value})}
                rows={2}
              />
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setTrackingDialogOpen(false)}>
              Cancel
            </Button>
            <Button 
              onClick={submitTracking} 
              disabled={submittingTracking || !trackingInfo.courier || !trackingInfo.tracking_number}
              className="bg-indigo-600 hover:bg-indigo-700"
              data-testid="submit-tracking-btn"
            >
              {submittingTracking ? (
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
              ) : (
                <Send className="w-4 h-4 mr-2" />
              )}
              Add & Ship
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* Raise Dispute Form */}
      {showDisputeForm && (
        <RaiseDisputeForm
          orderId={orderId}
          onClose={() => setShowDisputeForm(false)}
          onSuccess={handleDisputeSuccess}
        />
      )}
      
      {/* Inspection Request Modal */}
      <InspectionRequestModal
        orderId={orderId}
        isOpen={showInspectionModal}
        onClose={() => setShowInspectionModal(false)}
        onSuccess={() => {
          fetchOrder();
        }}
      />
    </DashboardLayout>
  );
};

export default OrderDetail;
