import { useState, useEffect } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth, api } from "../../App";
import { usePermissions } from "../../hooks/usePermissions";
import { Button } from "../ui/button";
import NotificationBell from "../NotificationBell";
import { toast } from "sonner";
import { 
  Factory, LayoutDashboard, FileText, Package, Settings, 
  LogOut, Menu, X, Wrench, Building2, Users, DollarSign,
  ChevronDown, Bell, MessageSquare, User, Mail, AlertTriangle, BarChart3, FolderOpen, Shield
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../ui/dropdown-menu";

// Define all possible nav items with their required permissions
const ALL_NAV_ITEMS = {
  // Staff dashboard (for custom roles without base role)
  staff_dashboard: { path: "/staff/dashboard", label: "Dashboard", icon: LayoutDashboard, permissions: [] },
  
  // Buyer items
  buyer_dashboard: { path: "/buyer/dashboard", label: "Dashboard", icon: LayoutDashboard, permissions: [] },
  my_rfqs: { path: "/buyer/rfqs", label: "My RFQs", icon: FileText, permissions: [] },
  received_quotes: { path: "/buyer/quotes", label: "Received Quotes", icon: DollarSign, permissions: [] },
  new_rfq: { path: "/buyer/rfq/new", label: "New RFQ", icon: FileText, permissions: [] },
  buyer_profile: { path: "/buyer/profile", label: "My Profile", icon: User, permissions: [] },
  
  // Vendor items
  vendor_dashboard: { path: "/vendor/dashboard", label: "Dashboard", icon: LayoutDashboard, permissions: [] },
  matched_rfqs: { path: "/vendor/matched-rfqs", label: "Matched RFQs", icon: FileText, permissions: [] },
  vendor_profile: { path: "/vendor/profile", label: "Company Profile", icon: Building2, permissions: [] },
  machines: { path: "/vendor/machines", label: "Machines", icon: Wrench, permissions: [] },
  vendor_quotes: { path: "/vendor/quotes", label: "My Quotes", icon: DollarSign, permissions: [] },
  
  // Admin items - no permission checks for admin role (full access)
  admin_dashboard: { path: "/admin/dashboard", label: "Dashboard", icon: LayoutDashboard, permissions: [] },
  analytics: { path: "/admin/analytics", label: "Analytics", icon: BarChart3, permissions: [] },
  whatsapp: { path: "/admin/whatsapp", label: "WhatsApp", icon: MessageSquare, permissions: [] },
  whatsapp_logs: { path: "/admin/whatsapp/logs", label: "WA Logs", icon: FileText, permissions: [] },
  roles: { path: "/admin/roles", label: "Roles", icon: Shield, permissions: [] },
  file_manager: { path: "/admin/files", label: "File Manager", icon: FolderOpen, permissions: [] },
  
  // Common items
  disputes: { path: "/disputes", label: "Disputes", icon: AlertTriangle, permissions: [] },
  messages: { path: "/chat", label: "Messages", icon: MessageSquare, permissions: [] },
};

// Define nav configurations for each role type
const ROLE_NAV_CONFIGS = {
  buyer: ['buyer_dashboard', 'my_rfqs', 'received_quotes', 'new_rfq', 'disputes', 'buyer_profile', 'messages'],
  vendor: ['vendor_dashboard', 'matched_rfqs', 'vendor_profile', 'machines', 'vendor_quotes', 'disputes', 'messages'],
  admin: ['admin_dashboard', 'analytics', 'whatsapp', 'whatsapp_logs', 'roles', 'file_manager', 'disputes'],
  // Staff roles - all items available, permission checks done at component/API level
  staff: ['staff_dashboard', 'admin_dashboard', 'analytics', 'whatsapp', 'whatsapp_logs', 'file_manager', 'disputes', 'messages', 'my_rfqs', 'received_quotes', 'new_rfq', 'matched_rfqs', 'vendor_quotes'],
};

const DashboardLayout = ({ children }) => {
  const { user, logout } = useAuth();
  const { hasAnyPermission, permissions, loading: permissionsLoading } = usePermissions();
  const location = useLocation();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [resendingVerification, setResendingVerification] = useState(false);

  useEffect(() => {
    fetchUnreadCount();
    const interval = setInterval(fetchUnreadCount, 30000); // Poll every 30s
    return () => clearInterval(interval);
  }, []);

  const fetchUnreadCount = async () => {
    try {
      const response = await api.get("/messages/unread-count");
      setUnreadCount(response.data.unread_count);
    } catch (e) {
      // Ignore errors
    }
  };

  const handleResendVerification = async () => {
    setResendingVerification(true);
    try {
      await api.post("/auth/resend-verification");
      toast.success("Verification email sent! Please check your inbox.");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to send verification email");
    } finally {
      setResendingVerification(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate("/");
  };

  // Get nav items based on user role and permissions
  const getNavItems = () => {
    // Determine base role type
    let roleType = user?.role || 'buyer';
    
    // If no base role but has custom_role, use staff configuration
    if (!user?.role && user?.custom_role) {
      roleType = 'staff';
    }
    
    // Get the nav config for this role type
    const navConfig = ROLE_NAV_CONFIGS[roleType] || ROLE_NAV_CONFIGS.buyer;
    
    // Build nav items based on config and permissions
    const items = [];
    
    for (const itemKey of navConfig) {
      const itemConfig = ALL_NAV_ITEMS[itemKey];
      if (!itemConfig) continue;
      
      // Check if user has required permissions (if any)
      const hasPermission = itemConfig.permissions.length === 0 || 
        hasAnyPermission(itemConfig.permissions);
      
      if (hasPermission) {
        items.push({
          path: itemConfig.path,
          label: itemConfig.label,
          icon: itemConfig.icon,
          badge: itemKey === 'messages' ? unreadCount : undefined
        });
      }
    }
    
    // Remove duplicates by path
    const uniqueItems = items.filter((item, index, self) => 
      index === self.findIndex(t => t.path === item.path)
    );
    
    return uniqueItems;
  };

  const navItems = getNavItems();

  const NavLink = ({ item }) => {
    const isActive = location.pathname === item.path || 
      (item.path === "/chat" && location.pathname.startsWith("/chat"));
    return (
      <Link
        to={item.path}
        className={`flex items-center gap-3 px-4 py-3 rounded-sm transition-colors ${
          isActive 
            ? "bg-orange-600 text-white" 
            : "text-slate-400 hover:text-white hover:bg-slate-800"
        }`}
        onClick={() => setSidebarOpen(false)}
        data-testid={`nav-${item.label.toLowerCase().replace(" ", "-")}`}
      >
        <item.icon className="w-5 h-5" />
        <span className="font-medium flex-1">{item.label}</span>
        {item.badge > 0 && (
          <span className="px-2 py-0.5 text-xs font-bold bg-red-500 text-white rounded-full">
            {item.badge > 99 ? "99+" : item.badge}
          </span>
        )}
      </Link>
    );
  };

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Mobile Header */}
      <header className="lg:hidden fixed top-0 left-0 right-0 z-50 glass border-b border-slate-200">
        <div className="flex items-center justify-between px-4 py-3">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 text-slate-600 hover:bg-slate-100 rounded-lg"
            data-testid="mobile-menu-btn"
          >
            {sidebarOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
          
          <Link to="/" className="flex items-center gap-2">
            <img src="/logo.png" alt="OEMLinker" className="w-[320px] h-[80px]" />
          </Link>

          <NotificationBell />
        </div>
      </header>

      {/* Sidebar */}
      <aside className={`fixed inset-y-0 left-0 z-40 w-64 bg-slate-900 transform transition-transform duration-200 lg:translate-x-0 ${
        sidebarOpen ? "translate-x-0" : "-translate-x-full"
      }`}>
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="p-6 border-b border-slate-800">
            <Link to="/" className="flex items-center gap-2">
              <img src="/logo.png" alt="OEMLinker" className="w-[320px] h-[80px]" />
            </Link>
          </div>

          {/* User Info */}
          <div className="p-4 border-b border-slate-800">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-slate-700 rounded-full flex items-center justify-center text-white font-medium">
                {user?.name?.charAt(0).toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-white font-medium truncate">{user?.name}</p>
                <p className="text-slate-400 text-sm capitalize">
                  {user?.custom_role ? user.custom_role.replace(/_/g, ' ') : user?.role || 'Staff'}
                </p>
              </div>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
            {navItems.map((item) => (
              <NavLink key={item.path} item={item} />
            ))}
          </nav>

          {/* Footer */}
          <div className="p-4 border-t border-slate-800">
            <button
              onClick={handleLogout}
              className="flex items-center gap-3 w-full px-4 py-3 text-slate-400 hover:text-white hover:bg-slate-800 rounded-sm transition-colors"
              data-testid="logout-btn"
            >
              <LogOut className="w-5 h-5" />
              <span className="font-medium">Sign Out</span>
            </button>
          </div>
        </div>
      </aside>

      {/* Mobile Overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-30 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main Content */}
      <main className="lg:ml-64 min-h-screen">
        {/* Desktop Header */}
        <header className="hidden lg:flex items-center justify-between px-8 py-4 bg-white border-b border-slate-200">
          <div>
            <h2 className="text-slate-400 text-sm">
              {user?.role === "vendor" ? "Vendor Portal" : 
               user?.role === "admin" ? "Admin Panel" : 
               user?.role === "buyer" ? "Buyer Portal" :
               user?.custom_role ? `${user.custom_role.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())} Portal` :
               "Portal"}
            </h2>
          </div>

          <div className="flex items-center gap-4">
            <NotificationBell />

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button className="flex items-center gap-2 px-3 py-2 hover:bg-slate-100 rounded-lg transition-colors">
                  <div className="w-8 h-8 bg-slate-200 rounded-full flex items-center justify-center text-slate-600 font-medium">
                    {user?.name?.charAt(0).toUpperCase()}
                  </div>
                  <span className="text-slate-700 font-medium">{user?.name?.split(" ")[0]}</span>
                  <ChevronDown className="w-4 h-4 text-slate-400" />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <div className="px-3 py-2">
                  <p className="text-sm font-medium text-slate-900">{user?.name}</p>
                  <p className="text-xs text-slate-500">{user?.email}</p>
                </div>
                <DropdownMenuSeparator />
                {user?.role === "vendor" && (
                  <DropdownMenuItem onClick={() => navigate("/vendor/profile")}>
                    <Settings className="w-4 h-4 mr-2" /> Profile Settings
                  </DropdownMenuItem>
                )}
                <DropdownMenuItem onClick={handleLogout} className="text-red-600">
                  <LogOut className="w-4 h-4 mr-2" /> Sign Out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>

        {/* Page Content */}
        <div className="p-6 lg:p-8 pt-20 lg:pt-8">
          {/* Email Verification Banner - Only show for non-WhatsApp users with unverified email */}
          {user && user.email_verified === false && !user.phone_login && (
            <div className="mb-6 bg-amber-50 border border-amber-200 rounded-lg p-4 flex items-center justify-between" data-testid="email-verification-banner">
              <div className="flex items-center gap-3">
                <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0" />
                <div>
                  <p className="text-amber-800 font-medium">Please verify your email address</p>
                  <p className="text-amber-700 text-sm">We sent a verification link to <strong>{user.email}</strong>. Check your inbox.</p>
                </div>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={handleResendVerification}
                disabled={resendingVerification}
                className="border-amber-400 text-amber-700 hover:bg-amber-100 flex-shrink-0"
              >
                {resendingVerification ? (
                  <Mail className="w-4 h-4 animate-pulse mr-2" />
                ) : (
                  <Mail className="w-4 h-4 mr-2" />
                )}
                Resend Email
              </Button>
            </div>
          )}
          
          {/* WhatsApp User - Prompt to add email for notifications */}
          {user && user.phone_login && !user.contact_email && (
            <div className="mb-6 bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-center justify-between" data-testid="add-email-banner">
              <div className="flex items-center gap-3">
                <Mail className="w-5 h-5 text-blue-600 flex-shrink-0" />
                <div>
                  <p className="text-blue-800 font-medium">Add your email for notifications</p>
                  <p className="text-blue-700 text-sm">Get RFQ matches, quote updates, and important alerts via email.</p>
                </div>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => window.location.href = user.role === 'vendor' ? '/vendor/profile' : '/buyer/profile'}
                className="border-blue-400 text-blue-700 hover:bg-blue-100 flex-shrink-0"
              >
                <Mail className="w-4 h-4 mr-2" />
                Add Email
              </Button>
            </div>
          )}
          {children}
        </div>
      </main>
    </div>
  );
};

export default DashboardLayout;
