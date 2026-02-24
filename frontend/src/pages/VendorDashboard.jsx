import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useAuth, api } from "../App";
import DashboardLayout from "../components/layout/DashboardLayout";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { toast } from "sonner";
import { 
  Settings, FileText, Package, DollarSign, Wrench,
  ArrowRight, AlertCircle, Loader2, CheckCircle2, XCircle
} from "lucide-react";

const VendorDashboard = () => {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [hasProfile, setHasProfile] = useState(true);

  useEffect(() => {
    fetchDashboard();
  }, []);

  const fetchDashboard = async () => {
    try {
      const response = await api.get("/dashboard/vendor");
      if (response.data.error) {
        setHasProfile(false);
      } else {
        setStats(response.data);
      }
    } catch (error) {
      if (error.response?.status === 404) {
        setHasProfile(false);
      } else {
        toast.error("Failed to load dashboard");
      }
    } finally {
      setLoading(false);
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

  if (!hasProfile) {
    return (
      <DashboardLayout>
        <div className="flex flex-col items-center justify-center h-96">
          <AlertCircle className="w-16 h-16 text-orange-500 mb-4" />
          <h2 className="font-heading text-2xl font-bold text-slate-900 mb-2">
            Complete Your Vendor Profile
          </h2>
          <p className="text-slate-500 mb-6 text-center max-w-md">
            To start receiving RFQ matches and submitting quotes, please set up your company profile and add your machines.
          </p>
          <Link to="/vendor/profile">
            <Button className="bg-orange-600 hover:bg-orange-700">
              <Settings className="w-4 h-4 mr-2" /> Setup Profile
            </Button>
          </Link>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-8" data-testid="vendor-dashboard">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="font-heading text-2xl font-bold text-slate-900">
              {stats?.vendor_profile?.company_name || "Vendor Dashboard"}
            </h1>
            <div className="flex items-center gap-2 mt-1">
              {stats?.vendor_profile?.is_approved ? (
                <span className="flex items-center gap-1 text-sm text-green-600">
                  <CheckCircle2 className="w-4 h-4" /> Verified Vendor
                </span>
              ) : (
                <span className="flex items-center gap-1 text-sm text-amber-600">
                  <AlertCircle className="w-4 h-4" /> Pending Approval
                </span>
              )}
            </div>
          </div>
          <div className="flex gap-3">
            <Link to="/vendor/machines">
              <Button variant="outline" data-testid="manage-machines-btn">
                <Wrench className="w-4 h-4 mr-2" /> Machines
              </Button>
            </Link>
            <Link to="/vendor/profile">
              <Button variant="outline" data-testid="edit-profile-btn">
                <Settings className="w-4 h-4 mr-2" /> Profile
              </Button>
            </Link>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card className="border-slate-200">
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-slate-100 rounded-lg flex items-center justify-center">
                  <FileText className="w-6 h-6 text-slate-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-slate-900">{stats?.matched_rfqs || 0}</p>
                  <p className="text-sm text-slate-500">Matched RFQs</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-200">
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center">
                  <DollarSign className="w-6 h-6 text-orange-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-slate-900">{stats?.quotes_submitted || 0}</p>
                  <p className="text-sm text-slate-500">Quotes Sent</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-200">
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                  <Package className="w-6 h-6 text-green-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-slate-900">{stats?.total_orders || 0}</p>
                  <p className="text-sm text-slate-500">Total Orders</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-200">
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                  <Wrench className="w-6 h-6 text-blue-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-slate-900">{stats?.total_machines || 0}</p>
                  <p className="text-sm text-slate-500">Machines</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Revenue Card */}
        <Card className="border-slate-200 bg-gradient-to-r from-slate-900 to-slate-800">
          <CardContent className="py-8">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-400 text-sm uppercase tracking-wider mb-1">Total Revenue</p>
                <p className="text-4xl font-bold text-white">
                  ${stats?.total_revenue?.toLocaleString() || "0"}
                </p>
              </div>
              <DollarSign className="w-16 h-16 text-slate-700" />
            </div>
          </CardContent>
        </Card>

        <div className="grid md:grid-cols-2 gap-6">
          {/* Matched RFQs */}
          <Card className="border-slate-200">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="font-heading text-lg">Incoming RFQs</CardTitle>
            </CardHeader>
            <CardContent>
              {stats?.recent_rfqs?.length > 0 ? (
                <div className="space-y-3">
                  {stats.recent_rfqs.map((rfq) => (
                    <Link
                      key={rfq.rfq_id}
                      to={`/vendor/rfq/${rfq.rfq_id}`}
                      className="block p-4 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors"
                      data-testid={`rfq-item-${rfq.rfq_id}`}
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium text-slate-900">{rfq.title}</p>
                          <p className="text-sm text-slate-500">
                            {rfq.material_type} • Qty: {rfq.quantity}
                          </p>
                        </div>
                        <span className={`status-badge ${getStatusBadge(rfq.status)}`}>
                          {rfq.status.replace("_", " ")}
                        </span>
                      </div>
                    </Link>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8">
                  <FileText className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                  <p className="text-slate-500">No matched RFQs yet</p>
                  {!stats?.vendor_profile?.is_approved && (
                    <p className="text-sm text-amber-600 mt-2">
                      Your profile is pending approval
                    </p>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Recent Orders */}
          <Card className="border-slate-200">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="font-heading text-lg">Active Orders</CardTitle>
            </CardHeader>
            <CardContent>
              {stats?.recent_orders?.length > 0 ? (
                <div className="space-y-3">
                  {stats.recent_orders.map((order) => (
                    <Link
                      key={order.order_id}
                      to={`/orders/${order.order_id}`}
                      className="block p-4 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors"
                      data-testid={`order-item-${order.order_id}`}
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium text-slate-900">
                            Order #{order.order_id.slice(-8)}
                          </p>
                          <p className="text-sm text-slate-500">
                            ${order.total_amount?.toFixed(2)} {order.currency}
                          </p>
                        </div>
                        <span className={`status-badge ${getStatusBadge(order.status)}`}>
                          {order.status.replace("_", " ")}
                        </span>
                      </div>
                    </Link>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8">
                  <Package className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                  <p className="text-slate-500">No orders yet</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  );
};

export default VendorDashboard;
