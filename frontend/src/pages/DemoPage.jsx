import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../App";
import { Button } from "../components/ui/button";
import { Card, CardContent } from "../components/ui/card";
import { toast } from "sonner";
import {
  ShoppingCart, Factory, ArrowRight, Loader2,
  FileText, Search, BarChart3, Package, CheckCircle2,
  Wrench, ClipboardList, DollarSign, Truck, Eye, Lock
} from "lucide-react";

const API_URL = process.env.REACT_APP_BACKEND_URL;

const JOURNEYS = [
  {
    role: "buyer",
    title: "Buyer Experience",
    subtitle: "Source parts from verified manufacturers",
    icon: ShoppingCart,
    color: "from-blue-600 to-indigo-700",
    accent: "blue",
    steps: [
      { icon: FileText, label: "Create RFQ", desc: "Upload drawings & specifications" },
      { icon: Search, label: "AI Analysis", desc: "Auto-extract dimensions & tolerances" },
      { icon: Factory, label: "Smart Matching", desc: "Find capable vendors instantly" },
      { icon: BarChart3, label: "Compare Quotes", desc: "Side-by-side vendor comparison" },
      { icon: CheckCircle2, label: "Award & Track", desc: "Place order, track production" },
    ],
    dashboardPath: "/buyer/dashboard",
    demoData: {
      rfqs: "3 RFQs (Aerospace Bracket, CNC Shaft, Aluminium Housing)",
      quotes: "2 competing quotes with price comparison",
      order: "1 active order in production",
    }
  },
  {
    role: "vendor",
    title: "Vendor Experience",
    subtitle: "Get matched to relevant manufacturing jobs",
    icon: Factory,
    color: "from-emerald-600 to-teal-700",
    accent: "emerald",
    steps: [
      { icon: ClipboardList, label: "Get Matched", desc: "AI matches your machines to RFQs" },
      { icon: Eye, label: "View RFQ Details", desc: "Drawings, specs & requirements" },
      { icon: DollarSign, label: "Submit Quote", desc: "Competitive pricing with terms" },
      { icon: Wrench, label: "Win Orders", desc: "Get awarded based on capability" },
      { icon: Truck, label: "Deliver & Grow", desc: "Build reputation with ratings" },
    ],
    dashboardPath: "/vendor/dashboard",
    demoData: {
      machines: "3 CNC machines (Mazak, DMG Mori, Okuma)",
      rfqs: "2 matched RFQs waiting for quotes",
      portfolio: "Aerospace, Automotive & Medical experience",
    }
  }
];

export default function DemoPage() {
  const navigate = useNavigate();
  const { user, loading: authLoading, updateUser, logout } = useAuth();
  const [loading, setLoading] = useState(null);
  const [seeding, setSeeding] = useState(false);
  const [seeded, setSeeded] = useState(false);

  // Auth gate — only admin or authorized users can access
  const isAuthorized = user && (user.role === "admin" || user.custom_role);

  // If auth is still loading, show nothing
  if (authLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-orange-500" />
      </div>
    );
  }

  // If not logged in or not authorized, show access denied
  if (!isAuthorized) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center">
        <div className="text-center max-w-md mx-auto px-4">
          <div className="w-16 h-16 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center mx-auto mb-4">
            <Lock className="w-8 h-8 text-red-400" />
          </div>
          <h2 className="text-2xl font-bold text-white mb-2">Access Restricted</h2>
          <p className="text-slate-400 mb-6">
            {!user 
              ? "Please log in as an admin to access the demo environment."
              : "Only admin and authorized users can access the demo."
            }
          </p>
          <Button 
            onClick={() => navigate(user ? "/" : "/login")} 
            className="bg-orange-600 hover:bg-orange-700"
            data-testid="demo-access-denied-btn"
          >
            {user ? "Go to Homepage" : "Log In"}
          </Button>
        </div>
      </div>
    );
  }

  const seedDemoData = async () => {
    setSeeding(true);
    try {
      const res = await fetch(`${API_URL}/api/demo/seed`, { method: "POST" });
      if (!res.ok) throw new Error("Seed failed");
      setSeeded(true);
      toast.success("Demo data ready!");
    } catch (err) {
      toast.error("Failed to seed demo data");
    } finally {
      setSeeding(false);
    }
  };

  const enterDemo = async (role) => {
    setLoading(role);
    try {
      // Seed first if not done
      if (!seeded) {
        const seedRes = await fetch(`${API_URL}/api/demo/seed`, { method: "POST" });
        if (!seedRes.ok) throw new Error("Seed failed");
        setSeeded(true);
      }

      // Login as demo user
      const res = await fetch(`${API_URL}/api/demo/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role })
      });
      if (!res.ok) throw new Error("Login failed");
      const data = await res.json();

      // Mark this as a demo session for cleanup on logout
      localStorage.setItem("demo_session", "true");

      // Store auth and update context
      localStorage.setItem("token", data.access_token);
      localStorage.setItem("user", JSON.stringify(data.user));
      updateUser(data.user);

      // Navigate to dashboard
      const journey = JOURNEYS.find(j => j.role === role);
      toast.success(`Welcome to OEMLinker as ${role.charAt(0).toUpperCase() + role.slice(1)}!`);
      navigate(journey.dashboardPath);
    } catch (err) {
      toast.error(`Failed to start ${role} demo`);
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 relative overflow-hidden">
      {/* Background effects */}
      <div className="absolute inset-0 opacity-30">
        <div className="absolute top-20 left-10 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl" />
        <div className="absolute bottom-20 right-10 w-96 h-96 bg-orange-500/10 rounded-full blur-3xl" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-emerald-500/5 rounded-full blur-3xl" />
      </div>

      <div className="relative z-10 max-w-6xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center gap-2 bg-orange-500/10 border border-orange-500/20 text-orange-400 px-4 py-1.5 rounded-full text-sm font-medium mb-4">
            <span className="w-2 h-2 bg-orange-400 rounded-full animate-pulse" />
            Interactive Demo
          </div>
          <h1 className="text-4xl sm:text-5xl font-bold text-white tracking-tight mb-3">
            Experience <span className="bg-gradient-to-r from-orange-400 to-amber-400 bg-clip-text text-transparent">OEMLinker</span>
          </h1>
          <p className="text-slate-400 text-lg max-w-2xl mx-auto">
            AI-powered manufacturing marketplace. Choose a role below to explore the platform with realistic demo data.
          </p>
        </div>

        {/* Journey Cards */}
        <div className="grid md:grid-cols-3 gap-5 mb-8">
          {JOURNEYS.map((journey) => {
            const Icon = journey.icon;
            const isLoading = loading === journey.role;

            return (
              <Card
                key={journey.role}
                data-testid={`demo-card-${journey.role}`}
                className="bg-slate-900/80 border-slate-700/50 backdrop-blur-sm hover:border-slate-600 transition-all duration-300 group cursor-pointer overflow-hidden"
                onClick={() => !loading && enterDemo(journey.role)}
              >
                <CardContent className="p-0">
                  {/* Gradient header */}
                  <div className={`bg-gradient-to-r ${journey.color} p-5 relative`}>
                    <div className="absolute inset-0 bg-black/10" />
                    <div className="relative flex items-center gap-3">
                      <div className="w-12 h-12 rounded-xl bg-white/20 backdrop-blur flex items-center justify-center">
                        <Icon className="w-6 h-6 text-white" />
                      </div>
                      <div>
                        <h3 className="text-lg font-bold text-white">{journey.title}</h3>
                        <p className="text-white/70 text-sm">{journey.subtitle}</p>
                      </div>
                    </div>
                  </div>

                  <div className="p-5 space-y-4">
                    {/* Steps */}
                    <div className="space-y-2">
                      {journey.steps.map((step, i) => {
                        const StepIcon = step.icon;
                        return (
                          <div key={i} className="flex items-center gap-3 group/step">
                            <div className="flex items-center justify-center w-7 h-7 rounded-lg bg-slate-800 border border-slate-700 text-slate-400 group-hover/step:border-slate-600 transition-colors shrink-0">
                              <StepIcon className="w-3.5 h-3.5" />
                            </div>
                            <div className="min-w-0">
                              <p className="text-sm text-slate-300 font-medium leading-tight">{step.label}</p>
                              <p className="text-xs text-slate-500 leading-tight">{step.desc}</p>
                            </div>
                            {i < journey.steps.length - 1 && (
                              <ArrowRight className="w-3 h-3 text-slate-600 ml-auto shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
                            )}
                          </div>
                        );
                      })}
                    </div>

                    {/* Demo data preview */}
                    <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-700/50">
                      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Pre-loaded data</p>
                      {Object.entries(journey.demoData).map(([key, val]) => (
                        <p key={key} className="text-xs text-slate-500 leading-relaxed">
                          <span className="text-slate-400">{val}</span>
                        </p>
                      ))}
                    </div>

                    {/* CTA */}
                    <Button
                      data-testid={`demo-enter-${journey.role}`}
                      className={`w-full bg-gradient-to-r ${journey.color} hover:opacity-90 text-white font-semibold h-11 transition-all`}
                      disabled={!!loading}
                      onClick={(e) => { e.stopPropagation(); enterDemo(journey.role); }}
                    >
                      {isLoading ? (
                        <><Loader2 className="w-4 h-4 animate-spin mr-2" /> Setting up...</>
                      ) : (
                        <>Enter as {journey.title.split(" ")[0]} <ArrowRight className="w-4 h-4 ml-2" /></>
                      )}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* Footer */}
        <div className="text-center">
          <p className="text-slate-500 text-sm">
            Demo accounts use temporary data. All credentials: <code className="bg-slate-800 px-2 py-0.5 rounded text-orange-400 text-xs">demo123</code>
          </p>
          <Button
            variant="link"
            className="text-slate-400 hover:text-white mt-1"
            onClick={() => navigate("/")}
          >
            Back to OEMLinker Homepage
          </Button>
        </div>
      </div>
    </div>
  );
}
