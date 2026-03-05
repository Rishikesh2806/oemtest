import { useState, useEffect, createContext, useContext, useRef } from "react";
import { BrowserRouter, Routes, Route, Navigate, useLocation, useNavigate } from "react-router-dom";
import axios from "axios";
import { Toaster } from "./components/ui/sonner";

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
import VendorDashboard from "./pages/VendorDashboard";
import VendorMatchedRFQs from "./pages/VendorMatchedRFQs";
import AdminDashboard from "./pages/AdminDashboard";
import CreateRFQ from "./pages/CreateRFQ";
import RFQDetail from "./pages/RFQDetail";
import VendorProfile from "./pages/VendorProfile";
import VendorProfileView from "./pages/VendorProfileView";
import MachineManagement from "./pages/MachineManagement";
import OrderDetail from "./pages/OrderDetail";
import QuotesList from "./pages/QuotesList";
import ChatPage from "./pages/ChatPage";
import NotificationsPage from "./pages/NotificationsPage";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
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
  withCredentials: true,
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

  const loginWithGoogle = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + "/dashboard";
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
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
        if (role === "vendor") {
          navigate("/vendor/dashboard", { replace: true });
        } else if (role === "admin") {
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

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    // Redirect to appropriate dashboard
    if (user.role === "vendor") {
      return <Navigate to="/vendor/dashboard" replace />;
    } else if (user.role === "admin") {
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
      
      {/* Generic dashboard redirect */}
      <Route path="/dashboard" element={<DashboardRedirect />} />
      
      {/* Buyer Routes */}
      <Route path="/buyer/dashboard" element={
        <ProtectedRoute allowedRoles={["buyer"]}>
          <BuyerDashboard />
        </ProtectedRoute>
      } />
      <Route path="/buyer/rfqs" element={
        <ProtectedRoute allowedRoles={["buyer"]}>
          <BuyerRFQList />
        </ProtectedRoute>
      } />
      <Route path="/buyer/quotes" element={
        <ProtectedRoute allowedRoles={["buyer"]}>
          <BuyerQuotes />
        </ProtectedRoute>
      } />
      <Route path="/buyer/profile" element={
        <ProtectedRoute allowedRoles={["buyer"]}>
          <BuyerProfile />
        </ProtectedRoute>
      } />
      <Route path="/buyer/rfq/new" element={
        <ProtectedRoute allowedRoles={["buyer"]}>
          <CreateRFQ />
        </ProtectedRoute>
      } />
      <Route path="/buyer/rfq/:rfqId" element={
        <ProtectedRoute allowedRoles={["buyer"]}>
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
        <ProtectedRoute allowedRoles={["admin"]}>
          <AdminDashboard />
        </ProtectedRoute>
      } />
      
      {/* Catch all */}
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
        <AppRouter />
        <Toaster position="top-right" />
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
