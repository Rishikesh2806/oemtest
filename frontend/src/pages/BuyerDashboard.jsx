import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth, api } from "../App";
import DashboardLayout from "../components/layout/DashboardLayout";
import PermittedActions from "../components/PermittedActions";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { toast } from "sonner";
import { 
  Plus, FileText, Package, Clock, TrendingUp, 
  ArrowRight, CheckCircle2, AlertCircle, Loader2
} from "lucide-react";
import RefNumber from "../components/RefNumber";

const BuyerDashboard = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboard();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const fetchDashboard = async () => {
    try {
      const response = await api.get("/dashboard/buyer");
      setStats(response.data);
    } catch (error) {
      toast.error("Failed to load dashboard");
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
      cancelled: "status-cancelled"
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

  return (
    <DashboardLayout>
      <div className="space-y-8" data-testid="buyer-dashboard">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="font-heading text-2xl font-bold text-slate-900">
              Welcome back, {user?.name?.split(" ")[0]}
            </h1>
            <p className="text-slate-500">Manage your RFQs and orders</p>
          </div>
          <Link to="/buyer/rfq/new">
            <Button className="bg-orange-600 hover:bg-orange-700" data-testid="create-rfq-btn">
              <Plus className="w-4 h-4 mr-2" /> New RFQ
            </Button>
          </Link>
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
                  <p className="text-2xl font-bold text-slate-900">{stats?.total_rfqs || 0}</p>
                  <p className="text-sm text-slate-500">Total RFQs</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-200">
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center">
                  <Clock className="w-6 h-6 text-orange-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-slate-900">{stats?.active_rfqs || 0}</p>
                  <p className="text-sm text-slate-500">Active RFQs</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-200">
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                  <TrendingUp className="w-6 h-6 text-blue-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-slate-900">{stats?.pending_quotes || 0}</p>
                  <p className="text-sm text-slate-500">Pending Quotes</p>
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
        </div>
        
        {/* Permitted Quick Actions */}
        <PermittedActions 
          dashboardType="buyer" 
          title="Quick Actions"
          description="Available actions based on your permissions"
          columns={4}
        />

        {/* Recent RFQs */}
        <Card className="border-slate-200">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="font-heading text-lg">Recent RFQs</CardTitle>
            <Link to="/buyer/rfqs" className="text-sm text-orange-600 hover:text-orange-700 flex items-center gap-1">
              View All <ArrowRight className="w-4 h-4" />
            </Link>
          </CardHeader>
          <CardContent>
            {stats?.recent_rfqs?.length > 0 ? (
              <div className="space-y-3">
                {stats.recent_rfqs.map((rfq) => (
                  <Link
                    key={rfq.rfq_id}
                    to={`/buyer/rfq/${rfq.rfq_id}`}
                    className="block p-4 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors"
                    data-testid={`rfq-item-${rfq.rfq_id}`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <FileText className="w-5 h-5 text-slate-400" />
                        <div>
                          <p className="font-medium text-slate-900">{rfq.title}</p>
                          <div className="flex items-center gap-2 mt-0.5">
                            <RefNumber value={rfq.rfq_number} />
                            <span className="text-sm text-slate-500">
                              {rfq.material_type} • Qty: {rfq.quantity}
                            </span>
                          </div>
                        </div>
                      </div>
                      <span className={`status-badge ${getStatusBadge(rfq.status)}`}>
                        {rfq.status.replace("_", " ")}
                      </span>
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <div className="text-center py-12">
                <FileText className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                <p className="text-slate-500 mb-4">No RFQs yet</p>
                <Link to="/buyer/rfq/new">
                  <Button className="bg-orange-600 hover:bg-orange-700">
                    <Plus className="w-4 h-4 mr-2" /> Create Your First RFQ
                  </Button>
                </Link>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent Orders */}
        <Card className="border-slate-200">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="font-heading text-lg">Recent Orders</CardTitle>
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
                      <div className="flex items-center gap-3">
                        <Package className="w-5 h-5 text-slate-400" />
                        <div>
                          <p className="font-medium text-slate-900">{order.item_name || "Manufacturing Order"}</p>
                          <div className="flex items-center gap-2 mt-0.5">
                            <RefNumber value={order.order_number} />
                            <span className="text-sm text-slate-500">
                              ₹{order.total_amount?.toLocaleString('en-IN', {minimumFractionDigits: 2})}
                            </span>
                          </div>
                        </div>
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
    </DashboardLayout>
  );
};

export default BuyerDashboard;
