import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useAuth, api } from "../App";
import DashboardLayout from "../components/layout/DashboardLayout";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Badge } from "../components/ui/badge";
import { toast } from "sonner";
import { 
  Package, Search, Loader2, Calendar, Eye, Building2,
  Clock, CheckCircle2, Truck, XCircle, AlertTriangle, RefreshCw
} from "lucide-react";

const STATUS_CONFIG = {
  pending: { label: "Pending", color: "bg-yellow-100 text-yellow-700", icon: Clock },
  confirmed: { label: "Confirmed", color: "bg-blue-100 text-blue-700", icon: CheckCircle2 },
  in_production: { label: "In Production", color: "bg-purple-100 text-purple-700", icon: Package },
  quality_check: { label: "Quality Check", color: "bg-indigo-100 text-indigo-700", icon: AlertTriangle },
  dispatched: { label: "Dispatched", color: "bg-orange-100 text-orange-700", icon: Truck },
  delivered: { label: "Delivered", color: "bg-green-100 text-green-700", icon: CheckCircle2 },
  completed: { label: "Completed", color: "bg-green-100 text-green-700", icon: CheckCircle2 },
  cancelled: { label: "Cancelled", color: "bg-red-100 text-red-700", icon: XCircle },
};

const BuyerOrders = () => {
  const { user } = useAuth();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterStatus, setFilterStatus] = useState("all");

  useEffect(() => {
    fetchOrders();
  }, []);

  const fetchOrders = async () => {
    setLoading(true);
    try {
      const response = await api.get("/buyer/orders");
      setOrders(response.data.orders || []);
    } catch (error) {
      console.error("Failed to load orders:", error);
      toast.error("Failed to load orders");
    } finally {
      setLoading(false);
    }
  };

  const filteredOrders = orders.filter(order => {
    const matchesSearch = 
      order.order_id?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      order.rfq_title?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      order.vendor_name?.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = filterStatus === "all" || order.status === filterStatus;
    return matchesSearch && matchesStatus;
  });

  const statusFilters = [
    { value: "all", label: "All Orders" },
    { value: "pending", label: "Pending" },
    { value: "confirmed", label: "Confirmed" },
    { value: "in_production", label: "In Production" },
    { value: "dispatched", label: "Dispatched" },
    { value: "delivered", label: "Delivered" },
    { value: "completed", label: "Completed" },
  ];

  const stats = {
    total: orders.length,
    active: orders.filter(o => !["completed", "cancelled", "delivered"].includes(o.status)).length,
    completed: orders.filter(o => o.status === "completed" || o.status === "delivered").length,
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
      <div className="space-y-6" data-testid="buyer-orders-page">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="font-heading text-2xl font-bold text-slate-900">My Orders</h1>
            <p className="text-slate-500 mt-1">Track and manage your manufacturing orders</p>
          </div>
          <Button variant="outline" onClick={fetchOrders} data-testid="refresh-orders">
            <RefreshCw className="w-4 h-4 mr-2" /> Refresh
          </Button>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-3 gap-4">
          <Card className="border-slate-200">
            <CardContent className="py-4">
              <p className="text-sm text-slate-500">Total Orders</p>
              <p className="text-2xl font-bold text-slate-900">{stats.total}</p>
            </CardContent>
          </Card>
          <Card className="border-blue-200 bg-blue-50">
            <CardContent className="py-4">
              <p className="text-sm text-blue-600">Active</p>
              <p className="text-2xl font-bold text-blue-700">{stats.active}</p>
            </CardContent>
          </Card>
          <Card className="border-green-200 bg-green-50">
            <CardContent className="py-4">
              <p className="text-sm text-green-600">Completed</p>
              <p className="text-2xl font-bold text-green-700">{stats.completed}</p>
            </CardContent>
          </Card>
        </div>

        {/* Filters */}
        <Card className="border-slate-200">
          <CardContent className="pt-6">
            <div className="flex flex-col md:flex-row gap-4">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input
                  placeholder="Search orders..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                  data-testid="search-orders"
                />
              </div>
              <div className="flex gap-2 flex-wrap">
                {statusFilters.map(status => (
                  <Button
                    key={status.value}
                    variant={filterStatus === status.value ? "default" : "outline"}
                    size="sm"
                    onClick={() => setFilterStatus(status.value)}
                    className={filterStatus === status.value ? "bg-orange-600" : ""}
                  >
                    {status.label}
                  </Button>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Orders List */}
        {filteredOrders.length > 0 ? (
          <div className="space-y-4">
            {filteredOrders.map((order) => {
              const statusConfig = STATUS_CONFIG[order.status] || STATUS_CONFIG.pending;
              const StatusIcon = statusConfig.icon;
              
              return (
                <Card 
                  key={order.order_id}
                  className="border-slate-200 hover:shadow-md transition-all"
                  data-testid={`order-card-${order.order_id}`}
                >
                  <CardContent className="p-6">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center">
                          <Package className="w-6 h-6 text-orange-600" />
                        </div>
                        <div>
                          <div className="flex items-center gap-3">
                            <h3 className="font-semibold text-slate-900">
                              Order #{order.order_id?.slice(-8)}
                            </h3>
                            <Badge className={statusConfig.color}>
                              <StatusIcon className="w-3 h-3 mr-1" />
                              {statusConfig.label}
                            </Badge>
                          </div>
                          <p className="text-sm text-slate-500 mt-1">
                            {order.rfq_title || "Manufacturing Order"}
                          </p>
                          <div className="flex items-center gap-4 mt-2 text-xs text-slate-400">
                            {order.vendor_name && (
                              <span className="flex items-center gap-1">
                                <Building2 className="w-3 h-3" /> {order.vendor_name}
                              </span>
                            )}
                            <span className="flex items-center gap-1">
                              <Calendar className="w-3 h-3" />
                              {new Date(order.created_at).toLocaleDateString()}
                            </span>
                          </div>
                        </div>
                      </div>
                      
                      <div className="text-right">
                        <p className="text-xl font-bold text-slate-900">
                          ₹{order.total_amount?.toLocaleString('en-IN', {minimumFractionDigits: 2})}
                        </p>
                        <Link to={`/orders/${order.order_id}`}>
                          <Button variant="outline" size="sm" className="mt-2">
                            <Eye className="w-4 h-4 mr-1" /> View Details
                          </Button>
                        </Link>
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
              <Package className="w-16 h-16 text-slate-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-slate-900 mb-2">No Orders Found</h3>
              <p className="text-slate-500 mb-6">
                {searchTerm || filterStatus !== "all" 
                  ? "Try adjusting your search or filters"
                  : "You don't have any orders yet. Accept a quote to create your first order."}
              </p>
              <Link to="/buyer/quotes">
                <Button variant="outline">View Received Quotes</Button>
              </Link>
            </CardContent>
          </Card>
        )}
      </div>
    </DashboardLayout>
  );
};

export default BuyerOrders;
