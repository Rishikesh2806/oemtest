import { useState, useEffect, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../App";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Card, CardContent } from "../components/ui/card";
import { motion, useInView } from "framer-motion";
import {
  Factory, Search, Wrench, ArrowRight, ChevronRight,
  Cpu, Shield, Target, Layers, Filter,
  ArrowLeft, X, Lock
} from "lucide-react";

import PublicNav from "../components/PublicNav";

const API_URL = window.location.origin;

const fadeUp = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0, transition: { duration: 0.4 } } };

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
          Register to contact vendors, submit RFQs, and get detailed quotes. It takes less than 30 seconds.
        </p>
        <div className="space-y-3">
          <Button 
            className="w-full bg-orange-600 hover:bg-orange-700 text-white"
            onClick={() => navigate("/register")}
            data-testid="auth-gate-register-btn"
          >
            Sign Up Free
            <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
          <Button 
            variant="outline" 
            className="w-full"
            onClick={() => navigate("/login")}
            data-testid="auth-gate-login-btn"
          >
            Already have an account? Sign In
          </Button>
        </div>
        <p className="text-[10px] text-slate-400 text-center mt-4">
          No credit card required. Your data is secure.
        </p>
      </motion.div>
    </div>
  );
};

const VendorCard = ({ vendor, onContactClick }) => {
  return (
    <motion.div variants={fadeUp}>
      <Card className="border border-slate-200 hover:border-orange-300 hover:shadow-lg transition-all duration-300 group cursor-pointer h-full">
        <CardContent className="p-5">
          <div className="flex items-start justify-between mb-3">
            <div>
              <h3 className="font-bold text-slate-900 group-hover:text-orange-600 transition-colors text-sm" data-testid={`vendor-name-${vendor.vendor_id}`}>
                {vendor.company_name}
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                {vendor.machine_count} machine{vendor.machine_count > 1 ? "s" : ""}
                {vendor.best_tolerance_mm && <span> · ±{vendor.best_tolerance_mm}mm</span>}
              </p>
            </div>
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-orange-100 to-amber-100 flex items-center justify-center flex-shrink-0">
              <Factory className="w-5 h-5 text-orange-600" />
            </div>
          </div>

          {/* Capabilities */}
          <div className="mb-3">
            <p className="text-[10px] text-slate-400 uppercase font-medium mb-1.5">Capabilities</p>
            <div className="flex flex-wrap gap-1">
              {vendor.capabilities.slice(0, 4).map((cap, i) => (
                <span key={`cert-${cert}`} className="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 font-medium">
                  {cap}
                </span>
              ))}
              {vendor.capabilities.length > 4 && (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-orange-50 text-orange-600 font-medium">
                  +{vendor.capabilities.length - 4} more
                </span>
              )}
            </div>
          </div>

          {/* Materials */}
          <div className="mb-4">
            <p className="text-[10px] text-slate-400 uppercase font-medium mb-1.5">Materials</p>
            <div className="flex flex-wrap gap-1">
              {vendor.materials.slice(0, 5).map((mat, i) => (
                <span key={`mat-${mat}`} className="text-[10px] px-2 py-0.5 rounded-full bg-blue-50 text-blue-600 font-medium">
                  {mat}
                </span>
              ))}
              {vendor.materials.length > 5 && (
                <span className="text-[10px] text-slate-400">+{vendor.materials.length - 5}</span>
              )}
            </div>
          </div>

          {/* Machines preview */}
          {vendor.machines_preview?.length > 0 && (
            <div className="mb-4 border-t border-slate-100 pt-3">
              {vendor.machines_preview.slice(0, 2).map((m, i) => (
                <div key={i} className="flex items-center gap-2 text-xs text-slate-500 mb-1">
                  <Wrench className="w-3 h-3 text-slate-300" />
                  <span>{m.brand} {m.model}</span>
                </div>
              ))}
            </div>
          )}

          <div className="flex gap-2">
            <Link to={`/vendors/${vendor.vendor_id}`} className="flex-1">
              <Button variant="outline" size="sm" className="w-full text-xs" data-testid={`view-vendor-${vendor.vendor_id}`}>
                View Details <ChevronRight className="w-3 h-3 ml-1" />
              </Button>
            </Link>
            <Button 
              size="sm" 
              className="bg-orange-600 hover:bg-orange-700 text-white text-xs"
              onClick={(e) => { e.preventDefault(); onContactClick(); }}
              data-testid={`contact-vendor-${vendor.vendor_id}`}
            >
              Contact
            </Button>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
};

const VendorDirectory = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [vendors, setVendors] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [capFilter, setCapFilter] = useState("");
  const [matFilter, setMatFilter] = useState("");
  const [showAuthGate, setShowAuthGate] = useState(false);

  useEffect(() => {
    fetchVendors();
    fetchStats();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const fetchVendors = async (capability, material) => {
    setLoading(true);
    try {
      let url = `${API_URL}/api/public/vendors?limit=50`;
      if (capability) url += `&capability=${encodeURIComponent(capability)}`;
      if (material) url += `&material=${encodeURIComponent(material)}`;
      const res = await fetch(url);
      const data = await res.json();
      setVendors(data.vendors || []);
    } catch {
      setVendors([]);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_URL}/api/public/stats`);
      setStats(await res.json());
    } catch {}
  };

  const handleFilter = () => {
    fetchVendors(capFilter, matFilter);
  };

  const handleContactClick = () => {
    if (user) {
      navigate("/buyer/rfq/new");
    } else {
      setShowAuthGate(true);
    }
  };

  const filteredVendors = searchQuery
    ? vendors.filter(v =>
        v.company_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        v.capabilities.some(c => c.toLowerCase().includes(searchQuery.toLowerCase())) ||
        v.materials.some(m => m.toLowerCase().includes(searchQuery.toLowerCase()))
      )
    : vendors;

  return (
    <div className="min-h-screen bg-slate-50" data-testid="vendor-directory-page">
      <AuthGateModal isOpen={showAuthGate} onClose={() => setShowAuthGate(false)} />

      {/* Header */}
      <PublicNav activePage="/vendors" />

      {/* Hero */}
      <div className="bg-gradient-to-b from-slate-900 to-slate-800 text-white pt-32 sm:pt-36 pb-12 sm:pb-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <motion.h1 initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-3xl sm:text-4xl lg:text-5xl font-bold mb-4">
            Find the Right <span className="text-orange-400">Manufacturer</span>
          </motion.h1>
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }} className="text-base text-slate-300 max-w-2xl mx-auto mb-8">
            Browse verified manufacturers with CNC, laser, welding, and more. See their machines, materials, and capabilities before you submit an RFQ.
          </motion.p>

          {/* Search & Filters */}
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="max-w-3xl mx-auto">
            <div className="flex flex-col sm:flex-row gap-2 bg-white/10 backdrop-blur-sm p-2 rounded-xl">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input
                  placeholder="Search by name, capability, or material..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 bg-white text-slate-900 border-0 h-10"
                  data-testid="vendor-search-input"
                />
              </div>
              <div className="flex gap-2">
                <Input
                  placeholder="Capability..."
                  value={capFilter}
                  onChange={(e) => setCapFilter(e.target.value)}
                  className="bg-white text-slate-900 border-0 h-10 w-32"
                  data-testid="vendor-capability-filter"
                />
                <Input
                  placeholder="Material..."
                  value={matFilter}
                  onChange={(e) => setMatFilter(e.target.value)}
                  className="bg-white text-slate-900 border-0 h-10 w-32"
                  data-testid="vendor-material-filter"
                />
                <Button onClick={handleFilter} className="bg-orange-600 hover:bg-orange-700 h-10 px-4" data-testid="vendor-filter-btn">
                  <Filter className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </motion.div>

          {/* Stats */}
          {stats && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }} className="flex items-center justify-center gap-6 sm:gap-10 mt-8 text-sm">
              <div>
                <p className="text-2xl font-bold text-orange-400">{stats.vendors}+</p>
                <p className="text-slate-400">Manufacturers</p>
              </div>
              <div className="w-px h-8 bg-slate-700" />
              <div>
                <p className="text-2xl font-bold text-orange-400">{stats.machines}+</p>
                <p className="text-slate-400">Machines</p>
              </div>
              <div className="w-px h-8 bg-slate-700" />
              <div>
                <p className="text-2xl font-bold text-orange-400">{stats.rfqs_processed}+</p>
                <p className="text-slate-400">RFQs Processed</p>
              </div>
            </motion.div>
          )}
        </div>
      </div>

      {/* Vendor Grid */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-between mb-6">
          <p className="text-sm text-slate-500">
            {loading ? "Loading..." : `${filteredVendors.length} manufacturer${filteredVendors.length !== 1 ? "s" : ""} found`}
          </p>
          {!user && (
            <p className="text-xs text-slate-400">
              <Lock className="w-3 h-3 inline mr-1" />
              Register to contact vendors & submit RFQs
            </p>
          )}
        </div>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3, 4, 5, 6].map(i => (
              <div key={i} className="h-64 bg-slate-100 animate-pulse rounded-lg" />
            ))}
          </div>
        ) : filteredVendors.length === 0 ? (
          <div className="text-center py-16">
            <Factory className="w-12 h-12 text-slate-300 mx-auto mb-3" />
            <p className="text-slate-500 font-medium">No manufacturers found</p>
            <p className="text-sm text-slate-400 mt-1">Try adjusting your search or filters</p>
          </div>
        ) : (
          <motion.div
            initial="hidden"
            animate="show"
            variants={{ show: { transition: { staggerChildren: 0.05 } } }}
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
            data-testid="vendor-grid"
          >
            {filteredVendors.map(vendor => (
              <VendorCard
                key={vendor.vendor_id}
                vendor={vendor}
                onContactClick={handleContactClick}
              />
            ))}
          </motion.div>
        )}
      </div>

      {/* CTA */}
      {!user && (
        <div className="bg-slate-900 py-12">
          <div className="max-w-3xl mx-auto text-center px-4">
            <h2 className="text-xl sm:text-2xl font-bold text-white mb-3">
              Ready to Get Quotes?
            </h2>
            <p className="text-sm text-slate-400 mb-6">
              Upload your drawing, get AI analysis and matched vendors in minutes. Free to register.
            </p>
            <Button
              size="lg"
              onClick={() => navigate("/register")}
              className="bg-orange-600 hover:bg-orange-700 text-white"
              data-testid="cta-register-btn"
            >
              Create Free Account <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-6">
        <div className="max-w-7xl mx-auto px-4 text-center text-xs text-slate-400">
          <Link to="/" className="hover:text-orange-600">Home</Link>
          <span className="mx-2">·</span>
          <Link to="/vendors" className="hover:text-orange-600">Vendors</Link>
          <span className="mx-2">·</span>
          <Link to="/machines" className="hover:text-orange-600">Capabilities</Link>
          <span className="mx-2">·</span>
          <Link to="/rfqs" className="hover:text-orange-600">RFQs</Link>
          <span className="mx-2">·</span>
          <Link to="/login" className="hover:text-orange-600">Sign In</Link>
          <p className="mt-2">OEMLinker — AI-Powered Manufacturing Marketplace</p>
        </div>
      </footer>
    </div>
  );
};

export default VendorDirectory;
