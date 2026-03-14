import { useState, useEffect, useCallback, createContext, useContext } from 'react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Context for permissions
const PermissionsContext = createContext({
  permissions: [],
  loading: true,
  hasPermission: () => false,
  hasAnyPermission: () => false,
  hasAllPermissions: () => false,
  refreshPermissions: () => {},
});

// Provider component
export function PermissionsProvider({ children }) {
  const [permissions, setPermissions] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchPermissions = useCallback(async () => {
    const token = localStorage.getItem('token');
    if (!token) {
      setPermissions([]);
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/api/user/permissions`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setPermissions(data.permissions || []);
      } else {
        setPermissions([]);
      }
    } catch (error) {
      console.error('Failed to fetch permissions:', error);
      setPermissions([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch on mount
  useEffect(() => {
    fetchPermissions();
  }, [fetchPermissions]);
  
  // Listen for login/logout events via storage changes
  useEffect(() => {
    const handleStorageChange = (e) => {
      if (e.key === 'token') {
        // Small delay to ensure token is fully stored
        setTimeout(fetchPermissions, 100);
      }
    };
    
    window.addEventListener('storage', handleStorageChange);
    
    // Also check periodically if token changed (for same-tab login)
    const checkToken = setInterval(() => {
      const currentToken = localStorage.getItem('token');
      if (currentToken && permissions.length === 0 && !loading) {
        fetchPermissions();
      }
    }, 1000);
    
    return () => {
      window.removeEventListener('storage', handleStorageChange);
      clearInterval(checkToken);
    };
  }, [fetchPermissions, permissions.length, loading]);

  // Check if user has a specific permission
  const hasPermission = useCallback((permission) => {
    return permissions.includes(permission);
  }, [permissions]);

  // Check if user has any of the specified permissions
  const hasAnyPermission = useCallback((permissionList) => {
    return permissionList.some(p => permissions.includes(p));
  }, [permissions]);

  // Check if user has all of the specified permissions
  const hasAllPermissions = useCallback((permissionList) => {
    return permissionList.every(p => permissions.includes(p));
  }, [permissions]);

  const value = {
    permissions,
    loading,
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    refreshPermissions: fetchPermissions,
  };

  return (
    <PermissionsContext.Provider value={value}>
      {children}
    </PermissionsContext.Provider>
  );
}

// Hook to use permissions
export function usePermissions() {
  const context = useContext(PermissionsContext);
  if (!context) {
    throw new Error('usePermissions must be used within a PermissionsProvider');
  }
  return context;
}

// Component wrapper that shows children only if user has permission
export function PermissionGate({ 
  permission, 
  permissions: requiredPermissions, 
  requireAll = false,
  fallback = null, 
  children 
}) {
  const { hasPermission, hasAnyPermission, hasAllPermissions, loading } = usePermissions();

  if (loading) {
    return null; // Or a loading spinner
  }

  // Single permission check
  if (permission) {
    if (!hasPermission(permission)) {
      return fallback;
    }
    return children;
  }

  // Multiple permissions check
  if (requiredPermissions && requiredPermissions.length > 0) {
    const hasAccess = requireAll 
      ? hasAllPermissions(requiredPermissions)
      : hasAnyPermission(requiredPermissions);
    
    if (!hasAccess) {
      return fallback;
    }
  }

  return children;
}

// Dashboard action/card configurations based on permissions
export const DASHBOARD_ACTIONS = {
  // Admin Dashboard Actions
  admin: [
    {
      id: 'manage_users',
      title: 'Manage Users',
      description: 'View and manage user accounts',
      icon: 'Users',
      path: '/admin/dashboard',
      permissions: ['users.view'],
      color: 'blue'
    },
    {
      id: 'manage_vendors',
      title: 'Manage Vendors',
      description: 'Approve and manage vendor profiles',
      icon: 'Building2',
      path: '/admin/dashboard',
      permissions: ['vendors.view', 'vendors.approve'],
      color: 'green'
    },
    {
      id: 'view_rfqs',
      title: 'View All RFQs',
      description: 'Browse and manage all RFQs',
      icon: 'FileText',
      path: '/admin/dashboard',
      permissions: ['rfqs.view'],
      color: 'purple'
    },
    {
      id: 'analytics',
      title: 'Analytics',
      description: 'View platform analytics and reports',
      icon: 'BarChart3',
      path: '/admin/analytics',
      permissions: ['analytics.view_dashboard'],
      color: 'orange'
    },
    {
      id: 'whatsapp_admin',
      title: 'WhatsApp Management',
      description: 'Manage WhatsApp messages and templates',
      icon: 'MessageSquare',
      path: '/admin/whatsapp',
      permissions: ['whatsapp.view_messages', 'whatsapp.send_messages'],
      color: 'green'
    },
    {
      id: 'whatsapp_logs',
      title: 'WhatsApp Logs',
      description: 'View message logs and costs',
      icon: 'FileText',
      path: '/admin/whatsapp/logs',
      permissions: ['whatsapp.view_logs'],
      color: 'teal'
    },
    {
      id: 'roles_management',
      title: 'Roles & Permissions',
      description: 'Manage user roles and access',
      icon: 'Shield',
      path: '/admin/roles',
      permissions: ['admin.roles'],
      color: 'red'
    },
    {
      id: 'file_manager',
      title: 'File Manager',
      description: 'Manage uploaded files',
      icon: 'FolderOpen',
      path: '/admin/files',
      permissions: ['admin.file_manager'],
      color: 'yellow'
    },
    {
      id: 'disputes',
      title: 'Disputes',
      description: 'Handle and resolve disputes',
      icon: 'AlertTriangle',
      path: '/disputes',
      permissions: ['disputes.view', 'disputes.manage'],
      color: 'red'
    },
    {
      id: 'payments',
      title: 'Payments',
      description: 'View and process payments',
      icon: 'DollarSign',
      path: '/admin/dashboard',
      permissions: ['payments.view', 'payments.process'],
      color: 'green'
    },
    {
      id: 'financial_reports',
      title: 'Financial Reports',
      description: 'View financial analytics',
      icon: 'TrendingUp',
      path: '/admin/analytics',
      permissions: ['payments.reports', 'analytics.view_financials'],
      color: 'blue'
    }
  ],
  
  // Vendor Dashboard Actions
  vendor: [
    {
      id: 'view_rfqs',
      title: 'Browse RFQs',
      description: 'View matched RFQ opportunities',
      icon: 'FileText',
      path: '/vendor/matched-rfqs',
      permissions: ['rfqs.view'],
      color: 'blue'
    },
    {
      id: 'my_quotes',
      title: 'My Quotes',
      description: 'View and manage your quotes',
      icon: 'FileText',
      path: '/vendor/quotes',
      permissions: ['quotes.view'],
      color: 'purple'
    },
    {
      id: 'submit_quote',
      title: 'Submit Quotes',
      description: 'Create and submit quotes for RFQs',
      icon: 'Send',
      path: '/vendor/matched-rfqs',
      permissions: ['quotes.create'],
      color: 'green'
    },
    {
      id: 'my_orders',
      title: 'My Orders',
      description: 'View and track your orders',
      icon: 'Package',
      path: '/vendor/dashboard',
      permissions: ['orders.view'],
      color: 'orange'
    },
    {
      id: 'update_delivery',
      title: 'Update Delivery',
      description: 'Update order delivery status',
      icon: 'Truck',
      path: '/vendor/dashboard',
      permissions: ['orders.update_status'],
      color: 'teal'
    },
    {
      id: 'manage_machines',
      title: 'My Machines',
      description: 'Manage your machine inventory',
      icon: 'Wrench',
      path: '/vendor/machines',
      permissions: [],  // Base vendor permission
      color: 'gray'
    },
    {
      id: 'my_profile',
      title: 'Company Profile',
      description: 'Update your company profile',
      icon: 'Building2',
      path: '/vendor/profile',
      permissions: [],  // Base vendor permission
      color: 'blue'
    },
    {
      id: 'disputes',
      title: 'My Disputes',
      description: 'View and respond to disputes',
      icon: 'AlertTriangle',
      path: '/disputes',
      permissions: ['disputes.view'],
      color: 'red'
    }
  ],
  
  // Buyer Dashboard Actions
  buyer: [
    {
      id: 'create_rfq',
      title: 'Create RFQ',
      description: 'Submit a new Request for Quote',
      icon: 'Plus',
      path: '/buyer/rfq/new',
      permissions: ['rfqs.create'],
      color: 'green'
    },
    {
      id: 'my_rfqs',
      title: 'My RFQs',
      description: 'View and manage your RFQs',
      icon: 'FileText',
      path: '/buyer/rfqs',
      permissions: ['rfqs.view'],
      color: 'blue'
    },
    {
      id: 'analyze_drawings',
      title: 'AI Analysis',
      description: 'Get AI analysis on drawings',
      icon: 'Sparkles',
      path: '/buyer/rfqs',
      permissions: ['rfqs.analyze'],
      color: 'purple'
    },
    {
      id: 'find_vendors',
      title: 'Find Vendors',
      description: 'Match with suitable vendors',
      icon: 'Search',
      path: '/buyer/rfqs',
      permissions: ['rfqs.match_vendors'],
      color: 'orange'
    },
    {
      id: 'view_quotes',
      title: 'Review Quotes',
      description: 'View and compare vendor quotes',
      icon: 'FileText',
      path: '/buyer/quotes',
      permissions: ['quotes.view'],
      color: 'teal'
    },
    {
      id: 'approve_quotes',
      title: 'Approve Quotes',
      description: 'Approve or reject vendor quotes',
      icon: 'CheckCircle',
      path: '/buyer/quotes',
      permissions: ['quotes.approve'],
      color: 'green'
    },
    {
      id: 'negotiate',
      title: 'Negotiate',
      description: 'Negotiate with vendors',
      icon: 'MessageSquare',
      path: '/buyer/quotes',
      permissions: ['quotes.negotiate'],
      color: 'blue'
    },
    {
      id: 'my_orders',
      title: 'My Orders',
      description: 'View and track your orders',
      icon: 'Package',
      path: '/buyer/dashboard',
      permissions: ['orders.view'],
      color: 'orange'
    },
    {
      id: 'create_order',
      title: 'Create PO',
      description: 'Create purchase orders',
      icon: 'ShoppingCart',
      path: '/buyer/quotes',
      permissions: ['orders.create'],
      color: 'green'
    },
    {
      id: 'disputes',
      title: 'My Disputes',
      description: 'View and manage disputes',
      icon: 'AlertTriangle',
      path: '/disputes',
      permissions: ['disputes.view'],
      color: 'red'
    }
  ]
};

// Hook to get permitted actions for a dashboard
export function usePermittedActions(dashboardType) {
  const { permissions, loading, hasAnyPermission } = usePermissions();
  const [permittedActions, setPermittedActions] = useState([]);

  useEffect(() => {
    if (loading) return;

    const actions = DASHBOARD_ACTIONS[dashboardType] || [];
    const filtered = actions.filter(action => {
      // If no permissions required, always show
      if (!action.permissions || action.permissions.length === 0) {
        return true;
      }
      // Check if user has any of the required permissions
      return hasAnyPermission(action.permissions);
    });

    setPermittedActions(filtered);
  }, [dashboardType, permissions, loading, hasAnyPermission]);

  return { actions: permittedActions, loading };
}

export default usePermissions;
