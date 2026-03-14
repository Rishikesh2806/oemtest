import React, { useState, useEffect } from 'react';
import { useAuth, api } from '../App';
import DashboardLayout from '../components/layout/DashboardLayout';
import PermittedActions from '../components/PermittedActions';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import { 
  Users, FileText, Package, TrendingUp, Clock, 
  RefreshCw, CheckCircle2, AlertTriangle, Bell
} from 'lucide-react';

// Role display names and descriptions
const ROLE_INFO = {
  sales_manager: {
    title: 'Sales Manager',
    description: 'Manage RFQs, quotes, and vendor relationships',
    icon: TrendingUp,
    color: 'green'
  },
  support_agent: {
    title: 'Support Agent',
    description: 'Handle customer support and disputes',
    icon: Users,
    color: 'purple'
  },
  finance_admin: {
    title: 'Finance Admin',
    description: 'Manage payments and financial operations',
    icon: Package,
    color: 'yellow'
  },
  regional_manager: {
    title: 'Regional Manager',
    description: 'Manage regional vendors and RFQs',
    icon: TrendingUp,
    color: 'orange'
  },
  supervisor: {
    title: 'Supervisor',
    description: 'Oversee team operations and performance',
    icon: Users,
    color: 'blue'
  }
};

export default function StaffDashboard() {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [recentActivity, setRecentActivity] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Determine the dashboard type based on user's custom_role or role
  const customRole = user?.custom_role;
  const dashboardType = customRole || user?.role || 'admin';
  const roleInfo = ROLE_INFO[dashboardType] || ROLE_INFO.supervisor;
  
  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        
        // Fetch stats based on role
        const statsResponse = await api.get('/api/admin/stats');
        if (statsResponse.data) {
          setStats(statsResponse.data);
        }
        
        // Fetch recent activity
        const activityResponse = await api.get('/api/admin/activity?limit=5');
        if (activityResponse.data?.activities) {
          setRecentActivity(activityResponse.data.activities);
        }
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error);
      } finally {
        setLoading(false);
      }
    };
    
    fetchDashboardData();
  }, []);
  
  const RoleIcon = roleInfo.icon;
  
  const colorClasses = {
    green: 'bg-green-500/10 text-green-600',
    purple: 'bg-purple-500/10 text-purple-600',
    yellow: 'bg-yellow-500/10 text-yellow-600',
    orange: 'bg-orange-500/10 text-orange-600',
    blue: 'bg-blue-500/10 text-blue-600'
  };

  return (
    <DashboardLayout>
      <div className="space-y-6" data-testid="staff-dashboard">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className={`p-3 rounded-xl ${colorClasses[roleInfo.color]}`}>
              <RoleIcon className="h-8 w-8" />
            </div>
            <div>
              <h1 className="text-2xl font-bold">{roleInfo.title} Dashboard</h1>
              <p className="text-muted-foreground">{roleInfo.description}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-sm">
              {user?.name || 'User'}
            </Badge>
            <Button variant="outline" size="sm" onClick={() => window.location.reload()}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          </div>
        </div>
        
        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Active RFQs</p>
                    <p className="text-2xl font-bold">{stats.active_rfqs || 0}</p>
                  </div>
                  <FileText className="h-8 w-8 text-blue-500/50" />
                </div>
              </CardContent>
            </Card>
            
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Pending Quotes</p>
                    <p className="text-2xl font-bold">{stats.pending_quotes || 0}</p>
                  </div>
                  <Clock className="h-8 w-8 text-orange-500/50" />
                </div>
              </CardContent>
            </Card>
            
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Active Orders</p>
                    <p className="text-2xl font-bold">{stats.active_orders || 0}</p>
                  </div>
                  <Package className="h-8 w-8 text-green-500/50" />
                </div>
              </CardContent>
            </Card>
            
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Open Disputes</p>
                    <p className="text-2xl font-bold">{stats.open_disputes || 0}</p>
                  </div>
                  <AlertTriangle className="h-8 w-8 text-red-500/50" />
                </div>
              </CardContent>
            </Card>
          </div>
        )}
        
        {/* Quick Actions based on permissions */}
        <PermittedActions 
          dashboardType={dashboardType}
          title="Your Actions"
          description="Available actions based on your role and permissions"
          columns={4}
        />
        
        {/* Recent Activity */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bell className="h-5 w-5" />
              Recent Activity
            </CardTitle>
            <CardDescription>Latest updates and notifications</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex items-center justify-center h-32">
                <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : recentActivity.length > 0 ? (
              <div className="space-y-3">
                {recentActivity.map((activity, index) => (
                  <div 
                    key={index}
                    className="flex items-start gap-3 p-3 rounded-lg bg-muted/50"
                  >
                    <div className={`p-2 rounded-full ${
                      activity.type === 'rfq' ? 'bg-blue-500/10 text-blue-500' :
                      activity.type === 'quote' ? 'bg-green-500/10 text-green-500' :
                      activity.type === 'order' ? 'bg-purple-500/10 text-purple-500' :
                      'bg-gray-500/10 text-gray-500'
                    }`}>
                      {activity.type === 'rfq' ? <FileText className="h-4 w-4" /> :
                       activity.type === 'quote' ? <CheckCircle2 className="h-4 w-4" /> :
                       activity.type === 'order' ? <Package className="h-4 w-4" /> :
                       <Bell className="h-4 w-4" />}
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium">{activity.title}</p>
                      <p className="text-xs text-muted-foreground">{activity.description}</p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {new Date(activity.timestamp).toLocaleString()}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <Bell className="h-12 w-12 mx-auto mb-3 opacity-50" />
                <p>No recent activity</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
