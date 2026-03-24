import { useState, useEffect, createContext, useContext, useRef } from "react";
import { BrowserRouter, Routes, Route, Navigate, useLocation, useNavigate } from "react-router-dom";
import axios from "axios";
import { Toaster } from "./components/ui/sonner";
import { PermissionsProvider } from "./hooks/usePermissions";
import ChatbotWidget from "./components/ChatbotWidget";

// Pages
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import ForgotPasswordPage from "./pages/ForgotPasswordPage";
import ResetPasswordPage from "./pages/ResetPasswordPage";
import VerifyEmailPage from "./pages/VerifyEmailPage";
import BuyerDashboard from "./pages/BuyerDashboard";
import BuyerRFQList from "./pages/BuyerRFQList";
import BuyerQuotes from "./pages/BuyerQuotes";
import BuyerProfile from "./pages/BuyerProfile";
import BuyerOrders from "./pages/BuyerOrders";
import VendorDashboard from "./pages/VendorDashboard";
import VendorMatchedRFQs from "./pages/VendorMatchedRFQs";
import VendorOrders from "./pages/VendorOrders";
import AdminDashboard from "./pages/AdminDashboard";
import AdminAnalytics from "./pages/AdminAnalytics";
import WhatsAppAdmin from "./pages/WhatsAppAdmin";
import WhatsAppInbox from "./pages/WhatsAppInbox";
import WhatsAppLogs from "./pages/WhatsAppLogs";
import RolesManagement from "./pages/RolesManagement";
import StaffDashboard from "./pages/StaffDashboard";
import FileManager from "./pages/FileManager";
import CreateRFQ from "./pages/CreateRFQ";
import RFQDetail from "./pages/RFQDetail";
import VendorProfile from "./pages/VendorProfile";
import VendorProfileView from "./pages/VendorProfileView";
import MachineManagement from "./pages/MachineManagement";
import OrderDetail from "./pages/OrderDetail";
import QuotesList from "./pages/QuotesList";
import ChatPage from "./pages/ChatPage";
import NotificationsPage from "./pages/NotificationsPage";
import DisputesPage from "./pages/DisputesPage";
import DisputeDetailPage from "./pages/DisputeDetailPage";
import TermsOfService from "./pages/TermsOfService";
import PrivacyPolicy from "./pages/PrivacyPolicy";
import DataDeletion from "./pages/DataDeletion";
import DataDeletionStatus from "./pages/DataDeletionStatus";
import MagicLogin from "./pages/MagicLogin";
import InspectorDashboard from "./pages/InspectorDashboard";
import GoogleCallback from "./pages/GoogleCallback";

// Use window.location.origin for API calls - this ensures requests go to the same domain
// This fixes issues where REACT_APP_BACKEND_URL might point to a different host
const BACKEND_URL = window.location.origin;
export const API = `${BACKEND_URL}/api`;

// Auth Context
const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
};

// API instance with auth
export const api = axios.create({
  baseURL: API,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Auth Provider
const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const checkAuth = async () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    // Skip auth check if returning from OAuth callback
    if (window.location.hash?.includes("session_id=")) {
      setLoading(false);
      return;
    }

    const token = localStorage.getItem("token");
    if (!token) {
      setLoading(false);
      return;
    }

    try {
      const response = await api.get("/auth/me");
      setUser(response.data);
    } catch (error) {
      localStorage.removeItem("token");
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkAuth();
  }, []);

  const login = async (email, password) => {
    const response = await api.post("/auth/login", { email, password });
    localStorage.setItem("token", response.data.access_token);
    setUser(response.data.user);
    return response.data.user;
  };

  const register = async (name, email, password, role, vendorDetails = {}) => {
    const payload = { name, email, password, role };
    
    // Add vendor-specific fields if registering as a vendor
    if (role === "vendor" && Object.keys(vendorDetails).length > 0) {
      Object.assign(payload, vendorDetails);
    }
    
    const response = await api.post("/auth/register", payload);
    localStorage.setItem("token", response.data.access_token);
    setUser(response.data.user);
    return response.data.user;
  };

  const loginWithGoogle = async () => {
    try {
      const clientId = process.env.REACT_APP_GOOGLE_CLIENT_ID;
      const redirectUri = window.location.origin + "/auth/google/callback";
      
      if (!clientId) {
        console.error("Google OAuth not configured: REACT_APP_GOOGLE_CLIENT_ID is missing");
        return;
      }
      
      // Build Google OAuth URL
      const params = new URLSearchParams({
        client_id: clientId,
        redirect_uri: redirectUri,
        response_type: "code",
        scope: "openid email profile",
        access_type: "offline",
        prompt: "consent"
      });
      
      window.location.href = `https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`;
    } catch (error) {
      console.error("Google login error:", error);
    }
  };

  const logout = async () => {
    try {
      await api.post("/auth/logout");
    } catch (e) {
      console.error("Logout error:", e);
    }
    localStorage.removeItem("token");
    setUser(null);
  };

  const updateUser = (userData) => {
    setUser(userData);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, loginWithGoogle, logout, updateUser, checkAuth }}>
      {children}
    </AuthContext.Provider>
  );
};

// Auth Callback Component
const AuthCallback = () => {
  const navigate = useNavigate();
  const { updateUser } = useAuth();
  const hasProcessed = useRef(false);

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const processAuth = async () => {
      const hash = window.location.hash;
      const sessionIdMatch = hash.match(/session_id=([^&]+)/);
      
      if (!sessionIdMatch) {
        navigate("/login");
        return;
      }

      const sessionId = sessionIdMatch[1];

      try {
        const response = await api.post("/auth/session", { session_id: sessionId });
        updateUser(response.data);
        
        // Redirect based on role
        const role = response.data.role;
        const customRole = response.data.custom_role;
        if (role === "vendor") {
          navigate("/vendor/dashboard", { replace: true });
        } else if (role === "admin") {
          navigate("/admin/dashboard", { replace: true });
        } else if (role === "inspector") {
          navigate("/inspector/dashboard", { replace: true });
        } else if (role === "buyer") {
          navigate("/buyer/dashboard", { replace: true });
        } else if (customRole) {
          // User has no base role but has a custom role - send to admin dashboard
          navigate("/admin/dashboard", { replace: true });
        } else {
          navigate("/buyer/dashboard", { replace: true });
        }
      } catch (error) {
        console.error("Auth callback error:", error);
        navigate("/login");
      }
    };

    processAuth();
  }, [navigate, updateUser]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="text-center">
        <div className="w-8 h-8 border-2 border-orange-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
        <p className="text-slate-600">Authenticating...</p>
      </div>
    </div>
  );
};

// Protected Route Component
const ProtectedRoute = ({ children, allowedRoles }) => {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="w-8 h-8 border-2 border-orange-600 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Determine effective role for routing
  // Users with custom_role but no base role are treated as "staff"
  const effectiveRole = user.role || (user.custom_role ? "staff" : "");

  if (allowedRoles && !allowedRoles.includes(effectiveRole)) {
    // Redirect to appropriate dashboard based on role or custom_role
    if (user.role === "vendor") {
      return <Navigate to="/vendor/dashboard" replace />;
    } else if (user.role === "admin") {
      return <Navigate to="/admin/dashboard" replace />;
    } else if (user.role === "buyer") {
      return <Navigate to="/buyer/dashboard" replace />;
    } else if (user.custom_role) {
      // User has no base role but has a custom role - send to admin dashboard
      return <Navigate to="/admin/dashboard" replace />;
    }
    return <Navigate to="/buyer/dashboard" replace />;
  }

  return children;
};

// App Router
const AppRouter = () => {
  const location = useLocation();

  // Check for OAuth callback
  if (location.hash?.includes("session_id=")) {
    return <AuthCallback />;
  }

  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route path="/verify-email" element={<VerifyEmailPage />} />
      <Route path="/auth/google/callback" element={<GoogleCallback />} />
      
      {/* Generic dashboard redirect */}
      <Route path="/dashboard" element={<DashboardRedirect />} />
      
      {/* Buyer Routes */}
      <Route path="/buyer/dashboard" element={
        <ProtectedRoute allowedRoles={["buyer"]}>
          <BuyerDashboard />
        </ProtectedRoute>
      } />
      <Route path="/buyer/rfqs" element={
        <ProtectedRoute allowedRoles={["buyer", "staff"]}>
          <BuyerRFQList />
        </ProtectedRoute>
      } />
      <Route path="/buyer/quotes" element={
        <ProtectedRoute allowedRoles={["buyer", "staff"]}>
          <BuyerQuotes />
        </ProtectedRoute>
      } />
      <Route path="/buyer/profile" element={
        <ProtectedRoute allowedRoles={["buyer"]}>
          <BuyerProfile />
        </ProtectedRoute>
      } />
      <Route path="/buyer/orders" element={
        <ProtectedRoute allowedRoles={["buyer", "staff"]}>
          <BuyerOrders />
        </ProtectedRoute>
      } />
      <Route path="/buyer/rfq/new" element={
        <ProtectedRoute allowedRoles={["buyer", "staff"]}>
          <CreateRFQ />
        </ProtectedRoute>
      } />
      <Route path="/buyer/rfq/:rfqId" element={
        <ProtectedRoute allowedRoles={["buyer", "staff"]}>
          <RFQDetail />
        </ProtectedRoute>
      } />
      <Route path="/orders/:orderId" element={
        <ProtectedRoute>
          <OrderDetail />
        </ProtectedRoute>
      } />
      
      {/* Vendor Routes */}
      <Route path="/vendor/dashboard" element={
        <ProtectedRoute allowedRoles={["vendor"]}>
          <VendorDashboard />
        </ProtectedRoute>
      } />
      <Route path="/vendor/profile" element={
        <ProtectedRoute allowedRoles={["vendor"]}>
          <VendorProfile />
        </ProtectedRoute>
      } />
      <Route path="/vendor/matched-rfqs" element={
        <ProtectedRoute allowedRoles={["vendor"]}>
          <VendorMatchedRFQs />
        </ProtectedRoute>
      } />
      <Route path="/vendor/orders" element={
        <ProtectedRoute allowedRoles={["vendor"]}>
          <VendorOrders />
        </ProtectedRoute>
      } />
      <Route path="/vendor/machines" element={
        <ProtectedRoute allowedRoles={["vendor"]}>
          <MachineManagement />
        </ProtectedRoute>
      } />
      <Route path="/vendor/quotes" element={
        <ProtectedRoute allowedRoles={["vendor"]}>
          <QuotesList />
        </ProtectedRoute>
      } />
      <Route path="/vendor/rfq/:rfqId" element={
        <ProtectedRoute allowedRoles={["vendor"]}>
          <RFQDetail />
        </ProtectedRoute>
      } />
      
      {/* Shared Routes */}
      <Route path="/vendor-profile/:vendorId" element={
        <ProtectedRoute>
          <VendorProfileView />
        </ProtectedRoute>
      } />
      <Route path="/chat" element={
        <ProtectedRoute>
          <ChatPage />
        </ProtectedRoute>
      } />
      <Route path="/chat/:conversationId" element={
        <ProtectedRoute>
          <ChatPage />
        </ProtectedRoute>
      } />
      <Route path="/notifications" element={
        <ProtectedRoute>
          <NotificationsPage />
        </ProtectedRoute>
      } />
      
      {/* Admin Routes */}
      <Route path="/admin/dashboard" element={
        <ProtectedRoute allowedRoles={["admin", "staff"]}>
          <AdminDashboard />
        </ProtectedRoute>
      } />
      <Route path="/admin/analytics" element={
        <ProtectedRoute allowedRoles={["admin", "staff"]}>
          <AdminAnalytics />
        </ProtectedRoute>
      } />
      <Route path="/admin/whatsapp" element={
        <ProtectedRoute allowedRoles={["admin", "staff"]}>
          <WhatsAppAdmin />
        </ProtectedRoute>
      } />
      <Route path="/admin/whatsapp/inbox" element={
        <ProtectedRoute allowedRoles={["admin", "staff"]}>
          <WhatsAppInbox />
        </ProtectedRoute>
      } />
      <Route path="/admin/whatsapp/logs" element={
        <ProtectedRoute allowedRoles={["admin", "staff"]}>
          <WhatsAppLogs />
        </ProtectedRoute>
      } />
      <Route path="/admin/roles" element={
        <ProtectedRoute allowedRoles={["admin"]}>
          <RolesManagement />
        </ProtectedRoute>
      } />
      <Route path="/admin/files" element={
        <ProtectedRoute allowedRoles={["admin", "staff"]}>
          <FileManager />
        </ProtectedRoute>
      } />
      
      {/* Staff Dashboard (for custom roles) */}
      <Route path="/staff/dashboard" element={
        <ProtectedRoute allowedRoles={["admin", "staff"]}>
          <StaffDashboard />
        </ProtectedRoute>
      } />
      
      {/* Inspector Routes */}
      <Route path="/inspector/dashboard" element={
        <ProtectedRoute allowedRoles={["inspector", "admin"]}>
          <InspectorDashboard />
        </ProtectedRoute>
      } />
      
      {/* Dispute Routes */}
      <Route path="/disputes" element={
        <ProtectedRoute allowedRoles={["buyer", "vendor", "admin"]}>
          <DisputesPage />
        </ProtectedRoute>
      } />
      <Route path="/disputes/:disputeId" element={
        <ProtectedRoute allowedRoles={["buyer", "vendor", "admin"]}>
          <DisputeDetailPage />
        </ProtectedRoute>
      } />
      
      {/* Legal Pages */}
      <Route path="/terms-of-service" element={<TermsOfService />} />
      <Route path="/privacy-policy" element={<PrivacyPolicy />} />
      <Route path="/data-deletion" element={<DataDeletion />} />
      <Route path="/data-deletion-status" element={<DataDeletionStatus />} />
      <Route path="/magic-login" element={<MagicLogin />} />
      
      {/* Catch all - must be last */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

// Dashboard Redirect based on role
const DashboardRedirect = () => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="w-8 h-8 border-2 border-orange-600 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (user.role === "vendor") {
    return <Navigate to="/vendor/dashboard" replace />;
  } else if (user.role === "admin") {
    return <Navigate to="/admin/dashboard" replace />;
  }
  
  return <Navigate to="/buyer/dashboard" replace />;
};

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <PermissionsProvider>
          <AppRouter />
          <Toaster position="top-right" />
          <ChatbotWidget />
        </PermissionsProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
