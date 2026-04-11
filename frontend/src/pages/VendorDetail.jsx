import { useState, useEffect } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { useAuth } from "../App";
import { Button } from "../components/ui/button";
import { Card, CardContent } from "../components/ui/card";
import { motion } from "framer-motion";
import {
  Factory, ArrowLeft, Wrench, Cpu, Layers,
  Target, Lock, ArrowRight, X, Loader2
} from "lucide-react";


import PublicNav from "../components/PublicNav";

const API_URL = window.location.origin;

const AuthGateModal = ({ isOpen, onClose }) => {
  const navigate = useNavigate();
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={onClose}>
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-white rounded-xl p-8 max-w-md w-full mx-4 shadow-2xl"
        onClick={e => e.stopPropagation()}
        data-testid="auth-gate-modal"
      >
        <div className="flex justify-between items-start mb-4">
          <div className="w-12 h-12 rounded-full bg-orange-100 flex items-center justify-center">
            <Lock className="w-6 h-6 text-orange-600" />
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <X className="w-5 h-5" />
          </button>
        </div>
        <h3 className="text-xl font-bold text-slate-900 mb-2">Create a Free Account</h3>
        <p className="text-sm text-slate-500 mb-6">
          Register to contact this vendor, submit RFQs, and get detailed quotes.
        </p>
        <div className="space-y-3">
          <Button className="w-full bg-orange-600 hover:bg-orange-700 text-white" onClick={() => navigate("/register")} data-testid="auth-gate-register-btn">
            Sign Up Free <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
          <Button variant="outline" className="w-full" onClick={() => navigate("/login")} data-testid="auth-gate-login-btn">
            Already have an account? Sign In
          </Button>
        </div>
      </motion.div>
    </div>
  );
};

const VendorDetail = () => {
  const { vendorId } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [vendor, setVendor] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showAuthGate, setShowAuthGate] = useState(false);

  useEffect(() => {
    const fetchVendor = async () => {
      setLoading(true);
      try {
        const res = await fetch(`${API_URL}/api/public/vendors/${vendorId}`);
        if (res.ok) {
          setVendor(await res.json());
        }
      } catch {}
      setLoading(false);
    };
    fetchVendor();
  }, [vendorId]);

  const handleContact = () => {
    if (user) {
      navigate("/buyer/rfq/new");
    } else {
      setShowAuthGate(true);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <Loader2 className="w-8 h-8 animate-spin text-orange-600" />
      </div>
    );
  }

  if (!vendor) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-slate-50">
        <Factory className="w-12 h-12 text-slate-300 mb-3" />
        <p className="text-slate-500 font-medium">Vendor not found</p>
        <Link to="/vendors" className="mt-4 text-orange-600 text-sm hover:underline">Back to directory</Link>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50" data-testid="vendor-detail-page">
      <AuthGateModal isOpen={showAuthGate} onClose={() => setShowAuthGate(false)} />

      {/* Header */}
      <PublicNav activePage="/vendors" />

      {/* Vendor Hero */}
      <div className="bg-gradient-to-b from-slate-900 to-slate-800 text-white pt-28 pb-10">
        <div className="max-w-5xl mx-auto px-4 sm:px-6">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="flex items-start gap-5">
            <div className="w-16 h-16 rounded-xl bg-gradient-to-br from-orange-500 to-amber-600 flex items-center justify-center flex-shrink-0">
              <Factory className="w-8 h-8 text-white" />
            </div>
            <div className="flex-1">
              <h1 className="text-2xl sm:text-3xl font-bold" data-testid="vendor-detail-name">{vendor.company_name}</h1>
              <div className="flex flex-wrap items-center gap-4 mt-2 text-sm text-slate-300">
                <span className="flex items-center gap-1"><Wrench className="w-3.5 h-3.5" /> {vendor.machine_count} machines</span>
                <span className="flex items-center gap-1"><Cpu className="w-3.5 h-3.5" /> {vendor.capabilities.length} capabilities</span>
                {vendor.best_tolerance_mm && (
                  <span className="flex items-center gap-1"><Target className="w-3.5 h-3.5" /> ±{vendor.best_tolerance_mm}mm precision</span>
                )}
              </div>
              <div className="flex flex-wrap gap-2 mt-4">
                {vendor.capabilities.map((cap, i) => (
                  <span key={i} className="text-xs px-3 py-1 rounded-full bg-white/10 text-white/80 font-medium">{cap}</span>
                ))}
              </div>
            </div>
            <Button
              onClick={handleContact}
              className="bg-orange-600 hover:bg-orange-700 text-white flex-shrink-0"
              data-testid="vendor-detail-contact-btn"
            >
              Contact Vendor
            </Button>
          </motion.div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8 space-y-6">
        {/* Materials */}
        <Card>
          <CardContent className="p-5">
            <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2 mb-3">
              <Layers className="w-4 h-4 text-blue-600" /> Materials Supported
            </h2>
            <div className="flex flex-wrap gap-2">
              {vendor.materials.map((mat, i) => (
                <span key={i} className="text-xs px-3 py-1.5 rounded-full bg-blue-50 text-blue-700 font-medium border border-blue-100">
                  {mat}
                </span>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Machine Fleet */}
        <div>
          <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2 mb-3">
            <Wrench className="w-4 h-4 text-orange-600" /> Machine Fleet ({vendor.machines.length})
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3" data-testid="vendor-machines-grid">
            {vendor.machines.map((m, i) => (
              <Card key={i} className="border border-slate-200">
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-semibold text-slate-900 text-sm">{m.brand} {m.model}</p>
                      <p className="text-xs text-slate-500 mt-0.5">{m.machine_type}{m.axis_config ? ` · ${m.axis_config}` : ""}</p>
                    </div>
                    <div className="w-8 h-8 rounded-lg bg-orange-50 flex items-center justify-center">
                      <Cpu className="w-4 h-4 text-orange-600" />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-2 mt-3 text-xs">
                    {(m.max_x || m.max_y || m.max_z) && (
                      <div className="bg-slate-50 rounded px-2 py-1.5">
                        <p className="text-slate-400 font-medium">Envelope</p>
                        <p className="text-slate-700 font-mono">{m.max_x || "—"} × {m.max_y || "—"} × {m.max_z || "—"} mm</p>
                      </div>
                    )}
                    {m.tolerance_capability && (
                      <div className="bg-slate-50 rounded px-2 py-1.5">
                        <p className="text-slate-400 font-medium">Tolerance</p>
                        <p className="text-slate-700 font-mono">±{m.tolerance_capability}mm</p>
                      </div>
                    )}
                  </div>
                  {m.materials?.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {m.materials.slice(0, 4).map((mat, j) => (
                        <span key={j} className="text-[10px] px-1.5 py-0.5 rounded bg-blue-50 text-blue-600">{mat}</span>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        {/* CTA for unauth users */}
        {!user && (
          <Card className="bg-gradient-to-r from-orange-50 to-amber-50 border-orange-200">
            <CardContent className="p-6 text-center">
              <h3 className="font-bold text-slate-900 mb-2">Want to Work with This Manufacturer?</h3>
              <p className="text-sm text-slate-500 mb-4">Create a free account to submit your RFQ and get quotes.</p>
              <Button onClick={() => navigate("/register")} className="bg-orange-600 hover:bg-orange-700 text-white" data-testid="vendor-detail-cta">
                Sign Up Free <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
};

export default VendorDetail;
