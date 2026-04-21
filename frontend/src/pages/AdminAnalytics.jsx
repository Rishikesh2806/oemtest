import { useState, useEffect } from "react";
import { useAuth, api } from "../App";
import DashboardLayout from "../components/layout/DashboardLayout";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { toast } from "sonner";
import { 
  Users, FileText, Package, DollarSign, Building2, Wrench,
  TrendingUp, TrendingDown, Activity, BarChart3, PieChart,
  ArrowUpRight, ArrowDownRight, RefreshCw, Download, Clock,
  CheckCircle2, AlertCircle, Zap, Target, Percent
} from "lucide-react";

// Metric Card Component
const MetricCard = ({ title, value, change, changeType, icon: Icon, color, subtitle }) => {
  const colorClasses = {
    blue: "bg-blue-500",
    green: "bg-emerald-500",
    orange: "bg-orange-500",
    purple: "bg-purple-500",
    cyan: "bg-cyan-500",
    pink: "bg-pink-500",
    slate: "bg-slate-500"
  };
  
  return (
    <Card className="border-slate-200 hover:shadow-md transition-shadow" data-testid={`metric-${title.toLowerCase().replace(/\s+/g, '-')}`}>
      <CardContent className="pt-5 pb-4">
        <div className="flex justify-between items-start">
          <div>
            <p className="text-sm font-medium text-slate-500">{title}</p>
            <p className="text-2xl font-bold text-slate-900 mt-1">{value}</p>
            {subtitle && <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>}
          </div>
          <div className={`w-10 h-10 ${colorClasses[color] || colorClasses.blue} rounded-lg flex items-center justify-center shadow-sm`}>
            <Icon className="w-5 h-5 text-white" />
          </div>
        </div>
        {change !== undefined && (
          <div className={`flex items-center mt-3 text-sm ${changeType === 'up' ? 'text-emerald-600' : changeType === 'down' ? 'text-red-600' : 'text-slate-500'}`}>
            {changeType === 'up' && <ArrowUpRight className="w-4 h-4 mr-1" />}
            {changeType === 'down' && <ArrowDownRight className="w-4 h-4 mr-1" />}
            <span className="font-medium">{change}</span>
            <span className="text-slate-400 ml-1">vs last period</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

// Progress Bar Component
const ProgressBar = ({ value, max, color = "orange", label, showPercent = true }) => {
  const percent = max > 0 ? Math.round((value / max) * 100) : 0;
  const colorClasses = {
    orange: "bg-orange-500",
    green: "bg-emerald-500",
    blue: "bg-blue-500",
    purple: "bg-purple-500"
  };
  
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="text-slate-600">{label}</span>
        <span className="font-medium text-slate-900">{showPercent ? `${percent}%` : value}</span>
      </div>
      <div className="w-full bg-slate-100 rounded-full h-2">
        <div 
          className={`${colorClasses[color]} h-2 rounded-full transition-all duration-500`}
          style={{ width: `${Math.min(percent, 100)}%` }}
        />
      </div>
    </div>
  );
};

// Simple Bar Chart Component
const SimpleBarChart = ({ data, valueKey, labelKey, color = "orange", height = 200 }) => {
  if (!data || data.length === 0) return <p className="text-slate-400 text-sm">No data available</p>;
  
  const maxValue = Math.max(...data.map(d => d[valueKey] || 0));
  const colorClasses = {
    orange: "bg-orange-500",
    green: "bg-emerald-500",
    blue: "bg-blue-500",
    purple: "bg-purple-500"
  };
  
  return (
    <div className="flex items-end justify-between gap-2" style={{ height }}>
      {data.map((item, index) => {
        const value = item[valueKey] || 0;
        const barHeight = maxValue > 0 ? (value / maxValue) * 100 : 0;
        return (
          <div key={index} className="flex flex-col items-center flex-1">
            <span className="text-xs text-slate-600 mb-1 font-medium">
              {value >= 1000 ? `${(value/1000).toFixed(0)}k` : value >= 100000 ? `${(value/100000).toFixed(1)}L` : value.toLocaleString('en-IN')}
            </span>
            <div 
              className={`w-full ${colorClasses[color]} rounded-t-sm transition-all duration-500 min-h-[4px]`}
              style={{ height: `${Math.max(barHeight, 2)}%` }}
            />
            <span className="text-xs text-slate-500 mt-2 truncate max-w-full">
              {item[labelKey]}
            </span>
          </div>
        );
      })}
    </div>
  );
};

// Status Distribution Component
const StatusDistribution = ({ data, title }) => {
  if (!data || Object.keys(data).length === 0) return null;
  
  const total = Object.values(data).reduce((a, b) => a + b, 0);
  const statusColors = {
    draft: "bg-slate-400",
    submitted: "bg-blue-500",
    analyzing: "bg-purple-500",
    matching: "bg-cyan-500",
    quoted: "bg-amber-500",
    po_issued: "bg-green-500",
    in_production: "bg-orange-500",
    completed: "bg-emerald-500",
    cancelled: "bg-red-500",
    pending: "bg-amber-500",
    accepted: "bg-green-500",
    rejected: "bg-red-500",
    created: "bg-blue-500",
    confirmed: "bg-cyan-500",
    shipped: "bg-purple-500",
    delivered: "bg-emerald-500"
  };
  
  return (
    <div className="space-y-3">
      <h4 className="text-sm font-semibold text-slate-700">{title}</h4>
      {Object.entries(data).map(([status, count]) => (
        <div key={status} className="flex items-center gap-3">
          <div className={`w-3 h-3 rounded-full ${statusColors[status] || 'bg-slate-400'}`} />
          <span className="text-sm text-slate-600 flex-1 capitalize">{status.replace('_', ' ')}</span>
          <span className="text-sm font-medium text-slate-900">{count}</span>
          <span className="text-xs text-slate-400">({total > 0 ? Math.round(count/total*100) : 0}%)</span>
        </div>
      ))}
    </div>
  );
};

// Recent Activity Item
const ActivityItem = ({ type, title, subtitle, time, status }) => {
  const icons = {
    user: Users,
    rfq: FileText,
    quote: DollarSign,
    order: Package
  };
  const Icon = icons[type] || Activity;
  
  const statusColors = {
    completed: "text-emerald-600",
    pending: "text-amber-600",
    urgent: "text-red-600",
    normal: "text-slate-600"
  };
  
  return (
    <div className="flex items-start gap-3 py-3 border-b border-slate-100 last:border-0">
      <div className="w-8 h-8 bg-slate-100 rounded-lg flex items-center justify-center flex-shrink-0">
        <Icon className="w-4 h-4 text-slate-600" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-slate-900 truncate">{title}</p>
        <p className="text-xs text-slate-500">{subtitle}</p>
      </div>
      <div className="text-right flex-shrink-0">
        <p className={`text-xs font-medium capitalize ${statusColors[status] || 'text-slate-600'}`}>
          {status?.replace('_', ' ')}
        </p>
        <p className="text-xs text-slate-400">{time}</p>
      </div>
    </div>
  );
};

// Format currency
const formatCurrency = (value) => {
  if (value >= 10000000) return `₹${(value / 10000000).toFixed(2)} Cr`;
  if (value >= 100000) return `₹${(value / 100000).toFixed(2)} L`;
  if (value >= 1000) return `₹${(value / 1000).toFixed(1)}K`;
  return `₹${value?.toLocaleString('en-IN') || 0}`;
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

const AdminAnalytics = () => {
  const { user } = useAuth();
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState(null);

  const fetchAnalytics = async () => {
    setLoading(true);
    try {
      const response = await api.get("/admin/analytics");
      setAnalytics(response.data);
      setLastRefresh(new Date());
    } catch (error) {
      console.error("Error fetching analytics:", error);
      toast.error("Failed to load analytics data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
    // Auto refresh every 5 minutes
    const interval = setInterval(fetchAnalytics, 300000);
    return () => clearInterval(interval);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleExport = async () => {
    try {
      const response = await api.get("/admin/analytics/export", {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `oemlinker_orders_${new Date().toISOString().split('T')[0]}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast.success("Export downloaded successfully");
    } catch (error) {
      toast.error("Failed to export data");
    }
  };

  if (loading && !analytics) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-96">
          <div className="text-center">
            <RefreshCw className="w-8 h-8 text-orange-500 animate-spin mx-auto mb-3" />
            <p className="text-slate-600">Loading analytics...</p>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  const { summary, users, vendors, machines, rfqs, quotes, orders, revenue, recent_activity, health } = analytics || {};

  return (
    <DashboardLayout>
      <div className="space-y-6" data-testid="admin-analytics-page">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Platform Analytics</h1>
            <p className="text-slate-500 text-sm mt-1">
              Real-time insights into your marketplace performance
              {lastRefresh && (
                <span className="ml-2 text-slate-400">
                  • Last updated: {lastRefresh.toLocaleTimeString()}
                </span>
              )}
            </p>
          </div>
          <div className="flex gap-2">
            <Button 
              variant="outline" 
              onClick={fetchAnalytics}
              disabled={loading}
              data-testid="refresh-analytics-btn"
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
            <Button onClick={handleExport} data-testid="export-analytics-btn">
              <Download className="w-4 h-4 mr-2" />
              Export CSV
            </Button>
          </div>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <MetricCard 
            title="Total Users" 
            value={summary?.total_users || 0}
            subtitle={`+${users?.new_this_week || 0} this week`}
            icon={Users}
            color="blue"
          />
          <MetricCard 
            title="Active RFQs" 
            value={summary?.total_rfqs || 0}
            subtitle={`+${rfqs?.new_this_week || 0} this week`}
            icon={FileText}
            color="purple"
          />
          <MetricCard 
            title="Total Quotes" 
            value={summary?.total_quotes || 0}
            subtitle={`${quotes?.conversion_rate || 0}% conversion`}
            icon={DollarSign}
            color="green"
          />
          <MetricCard 
            title="Total Orders" 
            value={summary?.total_orders || 0}
            subtitle={`${orders?.active || 0} active`}
            icon={Package}
            color="orange"
          />
          <MetricCard 
            title="Total Revenue" 
            value={formatCurrency(summary?.total_revenue || 0)}
            subtitle={`${formatCurrency(revenue?.pending || 0)} pending`}
            icon={TrendingUp}
            color="cyan"
          />
          <MetricCard 
            title="Platform GMV" 
            value={formatCurrency(summary?.platform_gmv || 0)}
            subtitle="Total quote value"
            icon={BarChart3}
            color="pink"
          />
        </div>

        {/* Platform Health Indicators */}
        <Card className="border-slate-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg flex items-center gap-2">
              <Activity className="w-5 h-5 text-orange-500" />
              Platform Health
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              <div className="text-center p-4 bg-slate-50 rounded-lg">
                <div className={`text-3xl font-bold ${(health?.rfq_match_rate || 0) >= 70 ? 'text-emerald-600' : (health?.rfq_match_rate || 0) >= 40 ? 'text-amber-600' : 'text-red-600'}`}>
                  {health?.rfq_match_rate || 0}%
                </div>
                <div className="text-sm text-slate-600 mt-1">RFQ Match Rate</div>
                <div className="text-xs text-slate-400">RFQs with vendor matches</div>
              </div>
              <div className="text-center p-4 bg-slate-50 rounded-lg">
                <div className={`text-3xl font-bold ${(health?.quote_conversion_rate || 0) >= 30 ? 'text-emerald-600' : (health?.quote_conversion_rate || 0) >= 15 ? 'text-amber-600' : 'text-red-600'}`}>
                  {health?.quote_conversion_rate || 0}%
                </div>
                <div className="text-sm text-slate-600 mt-1">Quote Conversion</div>
                <div className="text-xs text-slate-400">Quotes accepted</div>
              </div>
              <div className="text-center p-4 bg-slate-50 rounded-lg">
                <div className={`text-3xl font-bold ${(health?.vendor_approval_rate || 0) >= 80 ? 'text-emerald-600' : (health?.vendor_approval_rate || 0) >= 50 ? 'text-amber-600' : 'text-red-600'}`}>
                  {health?.vendor_approval_rate || 0}%
                </div>
                <div className="text-sm text-slate-600 mt-1">Vendor Approval</div>
                <div className="text-xs text-slate-400">Vendors approved</div>
              </div>
              <div className="text-center p-4 bg-slate-50 rounded-lg">
                <div className={`text-3xl font-bold ${(health?.machine_availability_rate || 0) >= 60 ? 'text-emerald-600' : (health?.machine_availability_rate || 0) >= 30 ? 'text-amber-600' : 'text-red-600'}`}>
                  {health?.machine_availability_rate || 0}%
                </div>
                <div className="text-sm text-slate-600 mt-1">Machine Availability</div>
                <div className="text-xs text-slate-400">Machines available</div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Revenue Trend & User Breakdown */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Revenue Trend */}
          <Card className="border-slate-200">
            <CardHeader className="pb-2">
              <CardTitle className="text-lg flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-emerald-500" />
                Revenue Trend (6 Months)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <SimpleBarChart 
                data={revenue?.monthly_trend || []}
                valueKey="revenue"
                labelKey="month"
                color="green"
                height={180}
              />
              <div className="mt-4 pt-4 border-t border-slate-100 grid grid-cols-3 gap-4 text-center">
                <div>
                  <p className="text-lg font-bold text-slate-900">{formatCurrency(revenue?.total || 0)}</p>
                  <p className="text-xs text-slate-500">Total Revenue</p>
                </div>
                <div>
                  <p className="text-lg font-bold text-emerald-600">{formatCurrency(revenue?.paid || 0)}</p>
                  <p className="text-xs text-slate-500">Paid</p>
                </div>
                <div>
                  <p className="text-lg font-bold text-amber-600">{formatCurrency(revenue?.pending || 0)}</p>
                  <p className="text-xs text-slate-500">Pending</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* User Breakdown */}
          <Card className="border-slate-200">
            <CardHeader className="pb-2">
              <CardTitle className="text-lg flex items-center gap-2">
                <Users className="w-5 h-5 text-blue-500" />
                User Breakdown
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-3 gap-4 text-center">
                <div className="p-3 bg-blue-50 rounded-lg">
                  <p className="text-2xl font-bold text-blue-600">{users?.buyers || 0}</p>
                  <p className="text-xs text-slate-600">Buyers</p>
                </div>
                <div className="p-3 bg-orange-50 rounded-lg">
                  <p className="text-2xl font-bold text-orange-600">{users?.vendors || 0}</p>
                  <p className="text-xs text-slate-600">Vendors</p>
                </div>
                <div className="p-3 bg-emerald-50 rounded-lg">
                  <p className="text-2xl font-bold text-emerald-600">{users?.verified || 0}</p>
                  <p className="text-xs text-slate-600">Verified</p>
                </div>
              </div>
              <ProgressBar 
                value={users?.verified || 0} 
                max={users?.total || 1} 
                color="green" 
                label="Email Verification Rate"
              />
              <div className="grid grid-cols-3 gap-3 pt-2">
                <div className="text-center p-2 bg-slate-50 rounded">
                  <p className="text-lg font-bold text-slate-900">+{users?.new_today || 0}</p>
                  <p className="text-xs text-slate-500">Today</p>
                </div>
                <div className="text-center p-2 bg-slate-50 rounded">
                  <p className="text-lg font-bold text-slate-900">+{users?.new_this_week || 0}</p>
                  <p className="text-xs text-slate-500">This Week</p>
                </div>
                <div className="text-center p-2 bg-slate-50 rounded">
                  <p className="text-lg font-bold text-slate-900">+{users?.new_this_month || 0}</p>
                  <p className="text-xs text-slate-500">This Month</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* RFQ & Quote Analysis */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* RFQ Status Distribution */}
          <Card className="border-slate-200">
            <CardHeader className="pb-2">
              <CardTitle className="text-lg flex items-center gap-2">
                <FileText className="w-5 h-5 text-purple-500" />
                RFQ Analysis
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="text-center p-3 bg-purple-50 rounded-lg">
                  <p className="text-xl font-bold text-purple-600">{rfqs?.total || 0}</p>
                  <p className="text-xs text-slate-600">Total RFQs</p>
                </div>
                <div className="text-center p-3 bg-emerald-50 rounded-lg">
                  <p className="text-xl font-bold text-emerald-600">{rfqs?.with_matches || 0}</p>
                  <p className="text-xs text-slate-600">Matched</p>
                </div>
              </div>
              <StatusDistribution data={rfqs?.by_status} title="By Status" />
              {rfqs?.by_urgency && Object.keys(rfqs.by_urgency).length > 0 && (
                <div className="pt-3 border-t border-slate-100">
                  <h4 className="text-sm font-semibold text-slate-700 mb-2">By Urgency</h4>
                  <div className="flex gap-2">
                    {Object.entries(rfqs.by_urgency).map(([urgency, count]) => (
                      <div key={urgency} className={`flex-1 text-center p-2 rounded ${
                        urgency === 'urgent' ? 'bg-red-50' : 
                        urgency === 'high' ? 'bg-orange-50' : 
                        urgency === 'low' ? 'bg-blue-50' : 'bg-green-50'
                      }`}>
                        <p className="text-lg font-bold">{count}</p>
                        <p className="text-xs text-slate-500 capitalize">{urgency}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Quote Metrics */}
          <Card className="border-slate-200">
            <CardHeader className="pb-2">
              <CardTitle className="text-lg flex items-center gap-2">
                <DollarSign className="w-5 h-5 text-emerald-500" />
                Quote Metrics
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="text-center p-3 bg-emerald-50 rounded-lg">
                  <p className="text-xl font-bold text-emerald-600">{quotes?.total || 0}</p>
                  <p className="text-xs text-slate-600">Total Quotes</p>
                </div>
                <div className="text-center p-3 bg-amber-50 rounded-lg">
                  <p className="text-xl font-bold text-amber-600">{quotes?.conversion_rate || 0}%</p>
                  <p className="text-xs text-slate-600">Conversion</p>
                </div>
              </div>
              <div className="space-y-2">
                <ProgressBar 
                  value={quotes?.accepted || 0} 
                  max={quotes?.total || 1} 
                  color="green" 
                  label={`Accepted (${quotes?.accepted || 0})`}
                />
                <ProgressBar 
                  value={quotes?.pending || 0} 
                  max={quotes?.total || 1} 
                  color="orange" 
                  label={`Pending (${quotes?.pending || 0})`}
                />
                <ProgressBar 
                  value={quotes?.rejected || 0} 
                  max={quotes?.total || 1} 
                  color="purple" 
                  label={`Rejected (${quotes?.rejected || 0})`}
                />
              </div>
              <div className="pt-3 border-t border-slate-100">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Avg Quote Value</span>
                  <span className="font-bold text-slate-900">{formatCurrency(quotes?.average_value || 0)}</span>
                </div>
                <div className="flex justify-between text-sm mt-2">
                  <span className="text-slate-500">Total Quote Value</span>
                  <span className="font-bold text-emerald-600">{formatCurrency(quotes?.total_value || 0)}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Order Status */}
          <Card className="border-slate-200">
            <CardHeader className="pb-2">
              <CardTitle className="text-lg flex items-center gap-2">
                <Package className="w-5 h-5 text-orange-500" />
                Order Status
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="text-center p-3 bg-orange-50 rounded-lg">
                  <p className="text-xl font-bold text-orange-600">{orders?.total || 0}</p>
                  <p className="text-xs text-slate-600">Total Orders</p>
                </div>
                <div className="text-center p-3 bg-emerald-50 rounded-lg">
                  <p className="text-xl font-bold text-emerald-600">{orders?.completed || 0}</p>
                  <p className="text-xs text-slate-600">Completed</p>
                </div>
              </div>
              <StatusDistribution data={orders?.by_status} title="By Status" />
            </CardContent>
          </Card>
        </div>

        {/* Vendor & Machine Stats */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Vendor Stats */}
          <Card className="border-slate-200">
            <CardHeader className="pb-2">
              <CardTitle className="text-lg flex items-center gap-2">
                <Building2 className="w-5 h-5 text-orange-500" />
                Vendor Statistics
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-3 gap-3">
                <div className="text-center p-3 bg-slate-50 rounded-lg">
                  <p className="text-xl font-bold text-slate-900">{vendors?.total_profiles || 0}</p>
                  <p className="text-xs text-slate-600">Total</p>
                </div>
                <div className="text-center p-3 bg-emerald-50 rounded-lg">
                  <p className="text-xl font-bold text-emerald-600">{vendors?.approved || 0}</p>
                  <p className="text-xs text-slate-600">Approved</p>
                </div>
                <div className="text-center p-3 bg-amber-50 rounded-lg">
                  <p className="text-xl font-bold text-amber-600">{vendors?.pending_approval || 0}</p>
                  <p className="text-xs text-slate-600">Pending</p>
                </div>
              </div>
              {vendors?.top_vendors && vendors.top_vendors.length > 0 && (
                <div className="pt-3 border-t border-slate-100">
                  <h4 className="text-sm font-semibold text-slate-700 mb-2">Top Vendors</h4>
                  <div className="space-y-2">
                    {vendors.top_vendors.slice(0, 5).map((vendor, index) => (
                      <div key={index} className="flex items-center justify-between text-sm">
                        <div className="flex items-center gap-2">
                          <span className="w-5 h-5 bg-orange-100 text-orange-600 rounded-full flex items-center justify-center text-xs font-bold">
                            {index + 1}
                          </span>
                          <span className="text-slate-700 truncate max-w-[150px]">{vendor.company_name}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-slate-500">{vendor.total_jobs} jobs</span>
                          {vendor.rating > 0 && (
                            <span className="text-amber-500">★ {vendor.rating.toFixed(1)}</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Machine Stats */}
          <Card className="border-slate-200">
            <CardHeader className="pb-2">
              <CardTitle className="text-lg flex items-center gap-2">
                <Wrench className="w-5 h-5 text-cyan-500" />
                Machine Statistics
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-4 gap-2">
                <div className="text-center p-2 bg-slate-50 rounded-lg">
                  <p className="text-lg font-bold text-slate-900">{machines?.total || 0}</p>
                  <p className="text-xs text-slate-600">Total</p>
                </div>
                <div className="text-center p-2 bg-blue-50 rounded-lg">
                  <p className="text-lg font-bold text-blue-600">{machines?.active || 0}</p>
                  <p className="text-xs text-slate-600">Active</p>
                </div>
                <div className="text-center p-2 bg-emerald-50 rounded-lg">
                  <p className="text-lg font-bold text-emerald-600">{machines?.available || 0}</p>
                  <p className="text-xs text-slate-600">Available</p>
                </div>
                <div className="text-center p-2 bg-amber-50 rounded-lg">
                  <p className="text-lg font-bold text-amber-600">{machines?.engaged || 0}</p>
                  <p className="text-xs text-slate-600">Engaged</p>
                </div>
              </div>
              {machines?.by_category && machines.by_category.length > 0 && (
                <div className="pt-3 border-t border-slate-100">
                  <h4 className="text-sm font-semibold text-slate-700 mb-2">Top Categories</h4>
                  <div className="space-y-2">
                    {machines.by_category.slice(0, 6).map((cat, index) => (
                      <div key={index} className="flex items-center justify-between">
                        <span className="text-sm text-slate-600 truncate max-w-[200px]">{cat._id || 'Uncategorized'}</span>
                        <span className="text-sm font-medium text-slate-900">{cat.count}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Recent Activity */}
        <Card className="border-slate-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg flex items-center gap-2">
              <Clock className="w-5 h-5 text-slate-500" />
              Recent Activity
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {/* Recent Users */}
              <div>
                <h4 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
                  <Users className="w-4 h-4" /> New Users
                </h4>
                {recent_activity?.users?.map((user, i) => (
                  <ActivityItem 
                    key={i}
                    type="user"
                    title={user.name}
                    subtitle={user.email}
                    time={formatTimeAgo(user.created_at)}
                    status={user.role}
                  />
                ))}
              </div>
              
              {/* Recent RFQs */}
              <div>
                <h4 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
                  <FileText className="w-4 h-4" /> New RFQs
                </h4>
                {recent_activity?.rfqs?.map((rfq, i) => (
                  <ActivityItem 
                    key={i}
                    type="rfq"
                    title={rfq.title}
                    subtitle={rfq.rfq_id}
                    time={formatTimeAgo(rfq.created_at)}
                    status={rfq.urgency || rfq.status}
                  />
                ))}
              </div>
              
              {/* Recent Quotes */}
              <div>
                <h4 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
                  <DollarSign className="w-4 h-4" /> New Quotes
                </h4>
                {recent_activity?.quotes?.map((quote, i) => (
                  <ActivityItem 
                    key={i}
                    type="quote"
                    title={formatCurrency(quote.price)}
                    subtitle={quote.quote_id}
                    time={formatTimeAgo(quote.created_at)}
                    status={quote.status}
                  />
                ))}
              </div>
              
              {/* Recent Orders */}
              <div>
                <h4 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
                  <Package className="w-4 h-4" /> New Orders
                </h4>
                {recent_activity?.orders?.map((order, i) => (
                  <ActivityItem 
                    key={i}
                    type="order"
                    title={formatCurrency(order.total_amount)}
                    subtitle={order.order_id}
                    time={formatTimeAgo(order.created_at)}
                    status={order.status}
                  />
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
};

export default AdminAnalytics;
