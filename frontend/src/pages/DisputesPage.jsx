import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth, api } from "../App";
import DashboardLayout from "../components/layout/DashboardLayout";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Textarea } from "../components/ui/textarea";
import { Label } from "../components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Badge } from "../components/ui/badge";
import { toast } from "sonner";
import {
  AlertTriangle, MessageSquare, Clock, CheckCircle2, XCircle,
  ChevronRight, Filter, Search, Plus, FileText, User, Building2,
  AlertCircle, Package, RefreshCw, Eye
} from "lucide-react";

// Dispute Types
const DISPUTE_TYPES = [
  { value: "quality_issue", label: "Quality Issue", icon: "🔍" },
  { value: "delivery_delay", label: "Delivery Delay", icon: "🕐" },
  { value: "wrong_specifications", label: "Wrong Specifications", icon: "📐" },
  { value: "payment_issue", label: "Payment Issue", icon: "💰" },
  { value: "communication", label: "Communication Problem", icon: "💬" },
  { value: "damaged_goods", label: "Damaged Goods", icon: "📦" },
  { value: "incomplete_order", label: "Incomplete Order", icon: "❌" },
  { value: "other", label: "Other", icon: "❓" }
];

// Status badges
const STATUS_CONFIG = {
  open: { color: "bg-red-100 text-red-700 border-red-200", label: "Open", icon: AlertCircle },
  under_review: { color: "bg-blue-100 text-blue-700 border-blue-200", label: "Under Review", icon: Eye },
  awaiting_response: { color: "bg-amber-100 text-amber-700 border-amber-200", label: "Awaiting Response", icon: Clock },
  escalated: { color: "bg-purple-100 text-purple-700 border-purple-200", label: "Escalated", icon: AlertTriangle },
  resolved: { color: "bg-green-100 text-green-700 border-green-200", label: "Resolved", icon: CheckCircle2 },
  closed: { color: "bg-slate-100 text-slate-700 border-slate-200", label: "Closed", icon: XCircle }
};

// Format time ago
const formatTimeAgo = (dateString) => {
  if (!dateString) return '';
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);
  
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
};

// Dispute Card Component
const DisputeCard = ({ dispute, onClick, userRole }) => {
  const statusConfig = STATUS_CONFIG[dispute.status] || STATUS_CONFIG.open;
  const StatusIcon = statusConfig.icon;
  const typeInfo = DISPUTE_TYPES.find(t => t.value === dispute.dispute_type) || DISPUTE_TYPES[7];
  
  const isInitiator = dispute.initiated_by === (userRole === "buyer" ? "buyer" : "vendor");
  
  return (
    <Card 
      className="border-slate-200 hover:shadow-md transition-all cursor-pointer group"
      onClick={onClick}
      data-testid={`dispute-card-${dispute.dispute_id}`}
    >
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-lg">{typeInfo.icon}</span>
              <h3 className="font-semibold text-slate-900 truncate group-hover:text-orange-600 transition-colors">
                {dispute.subject}
              </h3>
            </div>
            
            <div className="flex items-center gap-3 text-sm text-slate-500 mb-2">
              <span className="font-mono text-xs bg-slate-100 px-2 py-0.5 rounded">
                #{dispute.dispute_id?.slice(-8)}
              </span>
              <span>•</span>
              <span>{typeInfo.label}</span>
              {dispute.priority === "high" && (
                <>
                  <span>•</span>
                  <span className="text-red-600 font-medium">High Priority</span>
                </>
              )}
            </div>
            
            <div className="flex items-center gap-4 text-sm">
              <div className="flex items-center gap-1 text-slate-500">
                <Package className="w-3.5 h-3.5" />
                <span>Order #{dispute.order_id?.slice(-8)}</span>
              </div>
              <div className="flex items-center gap-1 text-slate-500">
                <Clock className="w-3.5 h-3.5" />
                <span>{formatTimeAgo(dispute.created_at)}</span>
              </div>
              {isInitiator && (
                <Badge variant="outline" className="text-xs">You initiated</Badge>
              )}
            </div>
          </div>
          
          <div className="flex flex-col items-end gap-2">
            <Badge className={`${statusConfig.color} border`}>
              <StatusIcon className="w-3 h-3 mr-1" />
              {statusConfig.label}
            </Badge>
            <span className="text-sm font-medium text-slate-700">
              ₹{dispute.order_amount?.toLocaleString('en-IN') || 0}
            </span>
          </div>
        </div>
        
        <div className="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between text-sm">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1.5">
              <User className="w-3.5 h-3.5 text-blue-500" />
              <span className="text-slate-600">{dispute.buyer_name}</span>
            </div>
            <span className="text-slate-300">vs</span>
            <div className="flex items-center gap-1.5">
              <Building2 className="w-3.5 h-3.5 text-orange-500" />
              <span className="text-slate-600">{dispute.vendor_name}</span>
            </div>
          </div>
          <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-orange-500 transition-colors" />
        </div>
      </CardContent>
    </Card>
  );
};

const DisputesPage = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [disputes, setDisputes] = useState([]);
  const [statusCounts, setStatusCounts] = useState({});
  const [loading, setLoading] = useState(true);
  const [selectedStatus, setSelectedStatus] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");

  const fetchDisputes = async () => {
    setLoading(true);
    try {
      const params = selectedStatus !== "all" ? `?status=${selectedStatus}` : "";
      const response = await api.get(`/disputes${params}`);
      setDisputes(response.data.disputes || []);
      setStatusCounts(response.data.status_counts || {});
    } catch (error) {
      console.error("Error fetching disputes:", error);
      toast.error("Failed to load disputes");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDisputes();
  }, [selectedStatus]);

  const filteredDisputes = disputes.filter(d => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      d.subject?.toLowerCase().includes(query) ||
      d.dispute_id?.toLowerCase().includes(query) ||
      d.order_id?.toLowerCase().includes(query) ||
      d.buyer_name?.toLowerCase().includes(query) ||
      d.vendor_name?.toLowerCase().includes(query)
    );
  });

  const totalOpen = (statusCounts.open || 0) + (statusCounts.under_review || 0) + 
                    (statusCounts.awaiting_response || 0) + (statusCounts.escalated || 0);

  return (
    <DashboardLayout>
      <div className="space-y-6" data-testid="disputes-page">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
              <AlertTriangle className="w-6 h-6 text-orange-500" />
              Dispute Resolution
            </h1>
            <p className="text-slate-500 text-sm mt-1">
              Manage and resolve disputes between buyers and vendors
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={fetchDisputes} disabled={loading}>
              <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
          <Card 
            className={`cursor-pointer transition-all ${selectedStatus === 'all' ? 'ring-2 ring-orange-500' : 'hover:shadow-md'}`}
            onClick={() => setSelectedStatus('all')}
          >
            <CardContent className="p-4 text-center">
              <p className="text-2xl font-bold text-slate-900">{disputes.length}</p>
              <p className="text-xs text-slate-500">All Disputes</p>
            </CardContent>
          </Card>
          {Object.entries(STATUS_CONFIG).map(([status, config]) => {
            const Icon = config.icon;
            const count = statusCounts[status] || 0;
            return (
              <Card 
                key={status}
                className={`cursor-pointer transition-all ${selectedStatus === status ? 'ring-2 ring-orange-500' : 'hover:shadow-md'}`}
                onClick={() => setSelectedStatus(status)}
              >
                <CardContent className="p-4 text-center">
                  <p className={`text-2xl font-bold ${count > 0 && status === 'open' ? 'text-red-600' : 'text-slate-900'}`}>
                    {count}
                  </p>
                  <p className="text-xs text-slate-500 flex items-center justify-center gap-1">
                    <Icon className="w-3 h-3" /> {config.label}
                  </p>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* Search */}
        <div className="flex gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-slate-400" />
            <Input
              placeholder="Search disputes by ID, subject, order, or party name..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
              data-testid="dispute-search-input"
            />
          </div>
        </div>

        {/* Disputes List */}
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <RefreshCw className="w-6 h-6 text-orange-500 animate-spin" />
          </div>
        ) : filteredDisputes.length === 0 ? (
          <Card className="border-slate-200">
            <CardContent className="py-12 text-center">
              <AlertTriangle className="w-12 h-12 text-slate-300 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-slate-700 mb-2">No Disputes Found</h3>
              <p className="text-slate-500 mb-4">
                {selectedStatus !== 'all' 
                  ? `No disputes with status "${STATUS_CONFIG[selectedStatus]?.label || selectedStatus}"`
                  : searchQuery 
                    ? "No disputes match your search"
                    : "Great news! There are no active disputes."}
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {filteredDisputes.map((dispute) => (
              <DisputeCard
                key={dispute.dispute_id}
                dispute={dispute}
                onClick={() => navigate(`/disputes/${dispute.dispute_id}`)}
                userRole={user?.role}
              />
            ))}
          </div>
        )}
      </div>
    </DashboardLayout>
  );
};

export default DisputesPage;
