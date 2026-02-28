import { useState, useEffect } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth, api } from "../../App";
import { Button } from "../ui/button";
import NotificationBell from "../NotificationBell";
import { 
  Factory, LayoutDashboard, FileText, Package, Settings, 
  LogOut, Menu, X, Wrench, Building2, Users, DollarSign,
  ChevronDown, Bell, MessageSquare
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../ui/dropdown-menu";

const DashboardLayout = ({ children }) => {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);

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

  const handleLogout = async () => {
    await logout();
    navigate("/");
  };

  const buyerNavItems = [
    { path: "/buyer/dashboard", label: "Dashboard", icon: LayoutDashboard },
    { path: "/buyer/rfqs", label: "My RFQs", icon: FileText },
    { path: "/buyer/quotes", label: "Received Quotes", icon: DollarSign },
    { path: "/buyer/rfq/new", label: "New RFQ", icon: FileText },
    { path: "/chat", label: "Messages", icon: MessageSquare, badge: unreadCount },
  ];

  const vendorNavItems = [
    { path: "/vendor/dashboard", label: "Dashboard", icon: LayoutDashboard },
    { path: "/vendor/matched-rfqs", label: "Matched RFQs", icon: FileText },
    { path: "/vendor/profile", label: "Company Profile", icon: Building2 },
    { path: "/vendor/machines", label: "Machines", icon: Wrench },
    { path: "/vendor/quotes", label: "My Quotes", icon: DollarSign },
    { path: "/chat", label: "Messages", icon: MessageSquare, badge: unreadCount },
  ];

  const adminNavItems = [
    { path: "/admin/dashboard", label: "Dashboard", icon: LayoutDashboard },
  ];

  const getNavItems = () => {
    switch (user?.role) {
      case "vendor": return vendorNavItems;
      case "admin": return adminNavItems;
      default: return buyerNavItems;
    }
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
            <img src="https://static.prod-images.emergentagent.com/jobs/10fd967d-100a-4ba4-9810-7f001d27333f/images/538e025cbcf1bcc1a8edd395590b4013ce298ebbb676ea7cd077596def05a82f.png" alt="Offloadex Logo" className="w-8 h-8" />
            <span className="font-heading font-bold text-slate-900">OFFLOADEX</span>
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
              <img src="https://static.prod-images.emergentagent.com/jobs/10fd967d-100a-4ba4-9810-7f001d27333f/images/538e025cbcf1bcc1a8edd395590b4013ce298ebbb676ea7cd077596def05a82f.png" alt="Offloadex Logo" className="w-9 h-9" />
              <span className="font-heading font-bold text-xl text-white">OFFLOADEX</span>
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
                <p className="text-slate-400 text-sm capitalize">{user?.role}</p>
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
              {user?.role === "vendor" ? "Vendor Portal" : user?.role === "admin" ? "Admin Panel" : "Buyer Portal"}
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
          {children}
        </div>
      </main>
    </div>
  );
};

export default DashboardLayout;
