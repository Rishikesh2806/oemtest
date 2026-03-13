import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Alert, AlertDescription } from '../components/ui/alert';
import { 
  MessageSquare, 
  Send, 
  Download, 
  AlertTriangle, 
  CheckCircle, 
  XCircle,
  Clock,
  DollarSign,
  TrendingUp,
  Users,
  RefreshCw,
  Search,
  Filter,
  ChevronLeft,
  ChevronRight,
  FileText,
  Image,
  Mic,
  Phone
} from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Message type icons
const MessageTypeIcon = ({ type }) => {
  const icons = {
    text: <MessageSquare className="h-4 w-4" />,
    template: <FileText className="h-4 w-4" />,
    image: <Image className="h-4 w-4" />,
    document: <FileText className="h-4 w-4" />,
    audio: <Mic className="h-4 w-4" />,
    interactive: <MessageSquare className="h-4 w-4" />
  };
  return icons[type] || <MessageSquare className="h-4 w-4" />;
};

// Status badge component
const StatusBadge = ({ status, success }) => {
  if (!success && status !== 'delivered') {
    return <Badge variant="destructive" className="text-xs">Failed</Badge>;
  }
  
  const statusConfig = {
    sent: { variant: 'default', label: 'Sent' },
    delivered: { variant: 'secondary', label: 'Delivered' },
    read: { variant: 'success', label: 'Read' },
    failed: { variant: 'destructive', label: 'Failed' },
    error: { variant: 'destructive', label: 'Error' },
    pending: { variant: 'outline', label: 'Pending' }
  };
  
  const config = statusConfig[status] || { variant: 'outline', label: status };
  return <Badge variant={config.variant} className="text-xs">{config.label}</Badge>;
};

// Statistics Card
const StatCard = ({ title, value, subtitle, icon: Icon, trend, color = 'blue' }) => {
  const colorClasses = {
    blue: 'bg-blue-500/10 text-blue-500',
    green: 'bg-green-500/10 text-green-500',
    red: 'bg-red-500/10 text-red-500',
    yellow: 'bg-yellow-500/10 text-yellow-500',
    purple: 'bg-purple-500/10 text-purple-500'
  };
  
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-muted-foreground">{title}</p>
            <p className="text-2xl font-bold mt-1">{value}</p>
            {subtitle && <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>}
          </div>
          <div className={`p-3 rounded-full ${colorClasses[color]}`}>
            <Icon className="h-5 w-5" />
          </div>
        </div>
        {trend && (
          <div className="mt-2 flex items-center text-xs">
            <TrendingUp className={`h-3 w-3 mr-1 ${trend > 0 ? 'text-green-500' : 'text-red-500'}`} />
            <span className={trend > 0 ? 'text-green-500' : 'text-red-500'}>
              {trend > 0 ? '+' : ''}{trend}%
            </span>
            <span className="text-muted-foreground ml-1">vs last period</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default function WhatsAppLogs() {
  const [activeTab, setActiveTab] = useState('overview');
  const [logs, setLogs] = useState([]);
  const [stats, setStats] = useState(null);
  const [errors, setErrors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Get token from localStorage
  const getToken = () => localStorage.getItem('token');
  
  // Filters - use 'all' instead of empty string for Select components
  const [filters, setFilters] = useState({
    direction: 'all',
    status: 'all',
    message_type: 'all',
    phone: '',
    start_date: '',
    end_date: '',
    context: '',
    errors_only: false
  });
  
  // Pagination
  const [pagination, setPagination] = useState({
    skip: 0,
    limit: 50,
    total: 0,
    hasMore: false
  });
  
  // Fetch statistics
  const fetchStats = useCallback(async () => {
    try {
      const token = getToken();
      const params = new URLSearchParams();
      if (filters.start_date) params.append('start_date', filters.start_date);
      if (filters.end_date) params.append('end_date', filters.end_date);
      
      const response = await fetch(`${API_URL}/api/whatsapp/logs/stats?${params}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (err) {
      console.error('Failed to fetch stats:', err);
    }
  }, [filters.start_date, filters.end_date]);
  
  // Fetch logs
  const fetchLogs = useCallback(async (resetPagination = false) => {
    try {
      setLoading(true);
      const token = getToken();
      const skip = resetPagination ? 0 : pagination.skip;
      
      const params = new URLSearchParams({
        limit: pagination.limit.toString(),
        skip: skip.toString()
      });
      
      // Add filters - convert 'all' back to empty for API
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== '' && value !== 'all' && value !== false) {
          params.append(key, value.toString());
        }
      });
      
      const response = await fetch(`${API_URL}/api/whatsapp/logs?${params}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setLogs(data.logs);
        setPagination(prev => ({
          ...prev,
          skip,
          total: data.total,
          hasMore: data.has_more
        }));
        setError(null);
      } else {
        const errData = await response.json();
        setError(errData.detail || 'Failed to fetch logs');
      }
    } catch (err) {
      setError('Failed to fetch logs');
    } finally {
      setLoading(false);
    }
  }, [filters, pagination.skip, pagination.limit]);
  
  // Fetch errors
  const fetchErrors = useCallback(async () => {
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/api/whatsapp/logs/errors?days=7`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setErrors(data.errors);
      }
    } catch (err) {
      console.error('Failed to fetch errors:', err);
    }
  }, []);
  
  // Initial load
  useEffect(() => {
    fetchStats();
    fetchLogs(true);
    fetchErrors();
  }, []);
  
  // Refresh on filter change
  useEffect(() => {
    const timer = setTimeout(() => {
      fetchLogs(true);
    }, 300);
    return () => clearTimeout(timer);
  }, [filters]);
  
  // Handle filter changes
  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };
  
  // Clear filters - reset to 'all' for Select components
  const clearFilters = () => {
    setFilters({
      direction: 'all',
      status: 'all',
      message_type: 'all',
      phone: '',
      start_date: '',
      end_date: '',
      context: '',
      errors_only: false
    });
  };
  
  // Pagination handlers
  const handleNextPage = () => {
    setPagination(prev => ({ ...prev, skip: prev.skip + prev.limit }));
    fetchLogs();
  };
  
  const handlePrevPage = () => {
    setPagination(prev => ({ ...prev, skip: Math.max(0, prev.skip - prev.limit) }));
    fetchLogs();
  };
  
  // Format timestamp
  const formatTimestamp = (ts) => {
    if (!ts) return 'N/A';
    const date = new Date(ts);
    return date.toLocaleString('en-IN', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit'
    });
  };
  
  // Format phone for display
  const formatPhone = (phone) => {
    if (!phone) return 'N/A';
    return `***${phone.slice(-4)}`;
  };

  return (
    <div className="p-6 space-y-6" data-testid="whatsapp-logs-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">WhatsApp Logs</h1>
          <p className="text-muted-foreground">Monitor message delivery, errors, and costs</p>
        </div>
        <Button 
          variant="outline" 
          onClick={() => { fetchStats(); fetchLogs(true); fetchErrors(); }}
          data-testid="refresh-logs-btn"
        >
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>
      
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview" data-testid="tab-overview">Overview</TabsTrigger>
          <TabsTrigger value="logs" data-testid="tab-logs">Message Logs</TabsTrigger>
          <TabsTrigger value="errors" data-testid="tab-errors">Errors</TabsTrigger>
        </TabsList>
        
        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6">
          {stats ? (
            <>
              {/* Stats Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
                <StatCard
                  title="Total Outbound"
                  value={stats.total_outbound?.toLocaleString() || 0}
                  subtitle="Messages sent"
                  icon={Send}
                  color="blue"
                />
                <StatCard
                  title="Total Inbound"
                  value={stats.total_inbound?.toLocaleString() || 0}
                  subtitle="Messages received"
                  icon={Download}
                  color="green"
                />
                <StatCard
                  title="Success Rate"
                  value={`${stats.success_rate || 0}%`}
                  subtitle={`${stats.failure_count || 0} failed`}
                  icon={CheckCircle}
                  color={stats.success_rate >= 95 ? 'green' : stats.success_rate >= 80 ? 'yellow' : 'red'}
                />
                <StatCard
                  title="Estimated Cost"
                  value={`₹${stats.total_estimated_cost_inr?.toFixed(2) || '0.00'}`}
                  subtitle="Based on Gupshup pricing"
                  icon={DollarSign}
                  color="purple"
                />
                <StatCard
                  title="Unique Recipients"
                  value={stats.unique_recipients?.toLocaleString() || 0}
                  subtitle="Phone numbers reached"
                  icon={Users}
                  color="blue"
                />
              </div>
              
              {/* Message Type Breakdown */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">By Message Type</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {Object.entries(stats.by_message_type || {}).map(([type, data]) => (
                        <div key={type} className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <MessageTypeIcon type={type} />
                            <span className="capitalize">{type}</span>
                          </div>
                          <div className="text-right">
                            <span className="font-medium">{data.count}</span>
                            <span className="text-muted-foreground text-sm ml-2">
                              (₹{data.cost?.toFixed(2)})
                            </span>
                          </div>
                        </div>
                      ))}
                      {Object.keys(stats.by_message_type || {}).length === 0 && (
                        <p className="text-muted-foreground text-sm">No data available</p>
                      )}
                    </div>
                  </CardContent>
                </Card>
                
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">By Context</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {Object.entries(stats.by_context || {}).map(([context, count]) => (
                        <div key={context} className="flex items-center justify-between">
                          <span className="capitalize">{context?.replace(/_/g, ' ') || 'Unknown'}</span>
                          <Badge variant="secondary">{count}</Badge>
                        </div>
                      ))}
                      {Object.keys(stats.by_context || {}).length === 0 && (
                        <p className="text-muted-foreground text-sm">No data available</p>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </div>
              
              {/* Daily Breakdown */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Daily Activity (Last 7 Days)</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b">
                          <th className="text-left py-2">Date</th>
                          <th className="text-right py-2">Messages</th>
                          <th className="text-right py-2">Errors</th>
                          <th className="text-right py-2">Cost (₹)</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(stats.daily_breakdown || []).map((day) => (
                          <tr key={day.date} className="border-b hover:bg-muted/50">
                            <td className="py-2">{day.date}</td>
                            <td className="text-right">{day.count}</td>
                            <td className="text-right">
                              {day.errors > 0 ? (
                                <span className="text-red-500">{day.errors}</span>
                              ) : (
                                <span className="text-green-500">0</span>
                              )}
                            </td>
                            <td className="text-right">₹{day.cost?.toFixed(2)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            </>
          ) : (
            <div className="flex items-center justify-center h-64">
              <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          )}
        </TabsContent>
        
        {/* Logs Tab */}
        <TabsContent value="logs" className="space-y-4">
          {/* Filters */}
          <Card>
            <CardContent className="p-4">
              <div className="flex flex-wrap gap-3 items-end">
                <div className="flex-1 min-w-[150px]">
                  <label className="text-xs text-muted-foreground mb-1 block">Phone</label>
                  <div className="relative">
                    <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input
                      placeholder="Search phone..."
                      value={filters.phone}
                      onChange={(e) => handleFilterChange('phone', e.target.value)}
                      className="pl-8"
                      data-testid="filter-phone"
                    />
                  </div>
                </div>
                
                <div className="w-[130px]">
                  <label className="text-xs text-muted-foreground mb-1 block">Direction</label>
                  <Select value={filters.direction} onValueChange={(v) => handleFilterChange('direction', v)}>
                    <SelectTrigger data-testid="filter-direction">
                      <SelectValue placeholder="All" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All</SelectItem>
                      <SelectItem value="outbound">Outbound</SelectItem>
                      <SelectItem value="inbound">Inbound</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                
                <div className="w-[130px]">
                  <label className="text-xs text-muted-foreground mb-1 block">Status</label>
                  <Select value={filters.status} onValueChange={(v) => handleFilterChange('status', v)}>
                    <SelectTrigger data-testid="filter-status">
                      <SelectValue placeholder="All" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All</SelectItem>
                      <SelectItem value="sent">Sent</SelectItem>
                      <SelectItem value="delivered">Delivered</SelectItem>
                      <SelectItem value="failed">Failed</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                
                <div className="w-[130px]">
                  <label className="text-xs text-muted-foreground mb-1 block">Type</label>
                  <Select value={filters.message_type} onValueChange={(v) => handleFilterChange('message_type', v)}>
                    <SelectTrigger data-testid="filter-type">
                      <SelectValue placeholder="All" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All</SelectItem>
                      <SelectItem value="text">Text</SelectItem>
                      <SelectItem value="template">Template</SelectItem>
                      <SelectItem value="image">Image</SelectItem>
                      <SelectItem value="document">Document</SelectItem>
                      <SelectItem value="audio">Audio</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                
                <div className="w-[140px]">
                  <label className="text-xs text-muted-foreground mb-1 block">From Date</label>
                  <Input
                    type="date"
                    value={filters.start_date}
                    onChange={(e) => handleFilterChange('start_date', e.target.value)}
                    data-testid="filter-start-date"
                  />
                </div>
                
                <div className="w-[140px]">
                  <label className="text-xs text-muted-foreground mb-1 block">To Date</label>
                  <Input
                    type="date"
                    value={filters.end_date}
                    onChange={(e) => handleFilterChange('end_date', e.target.value)}
                    data-testid="filter-end-date"
                  />
                </div>
                
                <Button variant="outline" size="sm" onClick={clearFilters} data-testid="clear-filters-btn">
                  <Filter className="h-4 w-4 mr-1" />
                  Clear
                </Button>
              </div>
            </CardContent>
          </Card>
          
          {/* Logs Table */}
          <Card>
            <CardContent className="p-0">
              {loading ? (
                <div className="flex items-center justify-center h-64">
                  <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : error ? (
                <Alert variant="destructive" className="m-4">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              ) : logs.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
                  <MessageSquare className="h-12 w-12 mb-3 opacity-50" />
                  <p>No logs found</p>
                  <p className="text-sm">Try adjusting your filters</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-muted/50">
                      <tr>
                        <th className="text-left p-3 font-medium">Time</th>
                        <th className="text-left p-3 font-medium">Direction</th>
                        <th className="text-left p-3 font-medium">Phone</th>
                        <th className="text-left p-3 font-medium">Type</th>
                        <th className="text-left p-3 font-medium">Status</th>
                        <th className="text-left p-3 font-medium">Context</th>
                        <th className="text-left p-3 font-medium max-w-[300px]">Content</th>
                        <th className="text-right p-3 font-medium">Cost</th>
                      </tr>
                    </thead>
                    <tbody>
                      {logs.map((log, idx) => (
                        <tr key={log.log_id || idx} className="border-b hover:bg-muted/30">
                          <td className="p-3 whitespace-nowrap">
                            <div className="flex items-center gap-1">
                              <Clock className="h-3 w-3 text-muted-foreground" />
                              {formatTimestamp(log.timestamp)}
                            </div>
                          </td>
                          <td className="p-3">
                            <Badge variant={log.direction === 'outbound' ? 'default' : 'secondary'}>
                              {log.direction === 'outbound' ? (
                                <><Send className="h-3 w-3 mr-1" />Out</>
                              ) : (
                                <><Download className="h-3 w-3 mr-1" />In</>
                              )}
                            </Badge>
                          </td>
                          <td className="p-3">
                            <div className="flex items-center gap-1">
                              <Phone className="h-3 w-3 text-muted-foreground" />
                              {formatPhone(log.phone)}
                            </div>
                          </td>
                          <td className="p-3">
                            <div className="flex items-center gap-1">
                              <MessageTypeIcon type={log.message_type} />
                              <span className="capitalize">{log.message_type}</span>
                            </div>
                          </td>
                          <td className="p-3">
                            <StatusBadge status={log.status} success={log.success} />
                          </td>
                          <td className="p-3">
                            <span className="text-xs text-muted-foreground capitalize">
                              {log.context?.replace(/_/g, ' ') || '-'}
                            </span>
                          </td>
                          <td className="p-3 max-w-[300px]">
                            <p className="truncate text-xs" title={log.content_preview}>
                              {log.content_preview || '-'}
                            </p>
                            {log.error_message && (
                              <p className="text-xs text-red-500 truncate mt-1" title={log.error_message}>
                                Error: {log.error_message}
                              </p>
                            )}
                          </td>
                          <td className="p-3 text-right whitespace-nowrap">
                            {log.direction === 'outbound' && log.estimated_cost_inr > 0 ? (
                              <span className="text-muted-foreground">
                                ₹{log.estimated_cost_inr?.toFixed(2)}
                              </span>
                            ) : (
                              <span className="text-muted-foreground">-</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              
              {/* Pagination */}
              {logs.length > 0 && (
                <div className="flex items-center justify-between p-4 border-t">
                  <p className="text-sm text-muted-foreground">
                    Showing {pagination.skip + 1} - {Math.min(pagination.skip + logs.length, pagination.total)} of {pagination.total}
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handlePrevPage}
                      disabled={pagination.skip === 0}
                      data-testid="prev-page-btn"
                    >
                      <ChevronLeft className="h-4 w-4" />
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleNextPage}
                      disabled={!pagination.hasMore}
                      data-testid="next-page-btn"
                    >
                      Next
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
        
        {/* Errors Tab */}
        <TabsContent value="errors" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-red-500" />
                Error Summary (Last 7 Days)
              </CardTitle>
              <CardDescription>
                Grouped errors with occurrence counts
              </CardDescription>
            </CardHeader>
            <CardContent>
              {errors.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-40 text-muted-foreground">
                  <CheckCircle className="h-12 w-12 mb-3 text-green-500 opacity-50" />
                  <p>No errors in the last 7 days!</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {errors.map((err, idx) => (
                    <div key={idx} className="p-4 border rounded-lg bg-red-50/50 dark:bg-red-950/20">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <Badge variant="destructive">{err.error_code || 'ERROR'}</Badge>
                            <span className="text-sm font-medium">{err.count} occurrences</span>
                          </div>
                          <p className="mt-2 text-sm">{err.error_message || 'Unknown error'}</p>
                          <div className="mt-2 flex items-center gap-4 text-xs text-muted-foreground">
                            <span>Last: {formatTimestamp(err.last_occurrence)}</span>
                            <span>Sample phone: {err.sample_phone}</span>
                            {err.context && <span>Context: {err.context}</span>}
                          </div>
                        </div>
                        <XCircle className="h-5 w-5 text-red-500 flex-shrink-0" />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
