import { useState, useEffect } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth, api } from "../App";
import DashboardLayout from "../components/layout/DashboardLayout";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { toast } from "sonner";
import { 
  Package, ArrowLeft, Loader2, CreditCard, 
  CheckCircle2, Clock, Truck, MapPin, AlertCircle
} from "lucide-react";

const OrderDetail = () => {
  const { orderId } = useParams();
  const [searchParams] = useSearchParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [processingPayment, setProcessingPayment] = useState(false);

  useEffect(() => {
    fetchOrder();
  }, [orderId]);

  useEffect(() => {
    // Check for payment callback
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
        return;
      } else if (response.data.status === "expired") {
        toast.error("Payment session expired");
        return;
      }

      // Continue polling
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
    } catch (error) {
      toast.error("Failed to update status");
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case "pending_payment": return <CreditCard className="w-5 h-5" />;
      case "paid": return <CheckCircle2 className="w-5 h-5" />;
      case "in_production": return <Clock className="w-5 h-5" />;
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
      case "dispatched": return "text-purple-600 bg-purple-100";
      case "delivered": return "text-indigo-600 bg-indigo-100";
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
        </div>

        {/* Order Summary */}
        <Card className="border-slate-200">
          <CardHeader>
            <div className="flex items-start justify-between">
              <div>
                <CardTitle className="font-heading text-2xl">
                  Order #{order.order_id.slice(-8)}
                </CardTitle>
                <p className="text-slate-500 mt-1">
                  Created {new Date(order.created_at).toLocaleDateString()}
                </p>
              </div>
              <div className={`px-4 py-2 rounded-lg ${getStatusColor(order.status)}`}>
                <div className="flex items-center gap-2 font-medium">
                  {getStatusIcon(order.status)}
                  {order.status.replace("_", " ").toUpperCase()}
                </div>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid md:grid-cols-3 gap-6">
              <div className="p-4 bg-slate-50 rounded-lg">
                <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-1">
                  Total Amount
                </p>
                <p className="text-3xl font-bold text-slate-900">
                  ${order.total_amount?.toFixed(2)}
                </p>
                <p className="text-sm text-slate-500">{order.currency}</p>
              </div>
              <div className="p-4 bg-slate-50 rounded-lg">
                <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-1">
                  Payment Status
                </p>
                <span className={`status-badge ${order.payment_status === "paid" ? "status-paid" : "status-pending"}`}>
                  {order.payment_status}
                </span>
              </div>
              <div className="p-4 bg-slate-50 rounded-lg">
                <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-1">
                  RFQ Reference
                </p>
                <p className="text-sm font-mono text-slate-600">
                  {order.rfq_id}
                </p>
              </div>
            </div>

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
                  Pay Now - ${order.total_amount?.toFixed(2)}
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

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
            {isVendor && order.payment_status === "paid" && (
              <div className="mt-6 pt-6 border-t border-slate-200">
                <p className="text-sm text-slate-500 mb-3">Update order status:</p>
                <div className="flex flex-wrap gap-2">
                  {["in_production", "quality_check", "dispatched", "delivered"].map((status) => (
                    <Button
                      key={status}
                      variant="outline"
                      size="sm"
                      onClick={() => updateStatus(status)}
                      disabled={statusFlow.findIndex(s => s.key === status) <= currentStatusIndex}
                      data-testid={`status-${status}-btn`}
                    >
                      {status.replace("_", " ")}
                    </Button>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

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
                      <p className="font-medium text-slate-900">{update.status}</p>
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
    </DashboardLayout>
  );
};

export default OrderDetail;
