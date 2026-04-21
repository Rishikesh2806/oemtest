import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../App";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Card, CardContent } from "../components/ui/card";
import { motion } from "framer-motion";
import {
  Wrench, Search, Filter, ArrowRight, Lock, X,
  Factory, Cpu, Layers, Target, Box,
  ChevronRight, Loader2, MapPin
} from "lucide-react";


import PublicNav from "../components/PublicNav";

const API_URL = window.location.origin;
const fadeUp = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0, transition: { duration: 0.4 } } };

const AuthGateModal = ({ isOpen, onClose }) => {
  const navigate = useNavigate();
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={onClose}>
      <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
        className="bg-white rounded-xl p-8 max-w-md w-full mx-4 shadow-2xl" onClick={e => e.stopPropagation()} data-testid="auth-gate-modal">
        <div className="flex justify-between items-start mb-4">
          <div className="w-12 h-12 rounded-full bg-orange-100 flex items-center justify-center"><Lock className="w-6 h-6 text-orange-600" /></div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600"><X className="w-5 h-5" /></button>
        </div>
        <h3 className="text-xl font-bold text-slate-900 mb-2">Create a Free Account</h3>
        <p className="text-sm text-slate-500 mb-6">Register to submit RFQs and get matched with the right machines and vendors.</p>
        <div className="space-y-3">
          <Button className="w-full bg-orange-600 hover:bg-orange-700 text-white" onClick={() => navigate("/register")} data-testid="auth-gate-register-btn">
            Sign Up Free <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
          <Button variant="outline" className="w-full" onClick={() => navigate("/login")} data-testid="auth-gate-login-btn">Already have an account? Sign In</Button>
        </div>
      </motion.div>
    </div>
  );
};

const AVAILABILITY_COLORS = {
  available: "bg-emerald-100 text-emerald-700",
  engaged: "bg-amber-100 text-amber-700",
  maintenance: "bg-red-100 text-red-700",
  offline: "bg-slate-100 text-slate-500",
};

const AVAILABILITY_LABELS = {
  available: "Available for Job",
  engaged: "Currently Engaged",
  maintenance: "Under Maintenance",
  offline: "Offline",
};

const MachineCard = ({ machine, onSubmitRFQ }) => {
  const isAvailable = machine.availability_status === "available" || !machine.availability_status;
  const hasImage = machine.images && machine.images.length > 0;
  const [imgError, setImgError] = React.useState(false);
  const showImage = hasImage && !imgError;
  return (
  <motion.div variants={fadeUp}>
    <Card className={`border hover:shadow-lg transition-all duration-300 h-full overflow-hidden ${
      isAvailable ? "border-emerald-200 hover:border-emerald-400" : "border-slate-200 hover:border-slate-300"
    }`}>
      {/* Machine Image */}
      <div className="h-40 relative overflow-hidden bg-slate-50">
        {showImage ? (
          <>
            <img
              src={machine.images[0]}
              alt={`${machine.brand} ${machine.model}`}
              className="w-full h-full object-cover"
              loading="lazy"
              onError={() => setImgError(true)}
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/50 via-transparent to-transparent" />
            <div className="absolute bottom-2 left-3">
              <h3 className="font-bold text-white text-sm drop-shadow-md" data-testid={`machine-name-${machine.machine_id}`}>
                {machine.machine_type}{machine.axis_config ? ` · ${machine.axis_config}` : ""}
              </h3>
              <p className="text-[11px] text-white/80 drop-shadow-sm">{machine.brand} {machine.model}</p>
            </div>
          </>
        ) : (
          <div className="w-full h-full flex flex-col items-center justify-center">
            <Cpu className="w-10 h-10 text-slate-300 mb-2" />
            <span className="text-xs text-slate-400 font-medium">{machine.machine_type}</span>
            <span className="text-[10px] text-slate-300">{machine.brand} {machine.model}</span>
          </div>
        )}
        <div className="absolute top-2 right-2">
          <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium whitespace-nowrap ${AVAILABILITY_COLORS[machine.availability_status] || AVAILABILITY_COLORS.available}`}>
            {AVAILABILITY_LABELS[machine.availability_status] || "Available for Job"}
          </span>
        </div>
      </div>

      <CardContent className="p-4">
        {!showImage && (
          <div className="mb-2">
            <h3 className="font-bold text-slate-900 text-sm" data-testid={`machine-name-${machine.machine_id}`}>
              {machine.machine_type}{machine.axis_config ? ` · ${machine.axis_config}` : ""}
            </h3>
            <p className="text-xs text-slate-500">{machine.brand} {machine.model}</p>
          </div>
        )}

        {/* Envelope */}
        {(machine.envelope?.x || machine.envelope?.y || machine.envelope?.z) && (
          <div className="bg-slate-50 rounded-lg p-2.5 mb-3">
            <p className="text-[10px] text-slate-400 uppercase font-medium mb-1">Work Envelope</p>
            <div className="flex items-center gap-2">
              <Box className="w-3.5 h-3.5 text-slate-400" />
              <p className="text-xs font-mono text-slate-700">
                {machine.envelope.x || "—"} × {machine.envelope.y || "—"} × {machine.envelope.z || "—"} mm
              </p>
            </div>
          </div>
        )}

        {/* Tolerance */}
        {machine.tolerance_mm && (
          <div className="flex items-center gap-2 mb-3 text-xs text-slate-500">
            <Target className="w-3.5 h-3.5 text-emerald-500" />
            <span>Tolerance: <span className="font-mono font-medium text-slate-700">±{machine.tolerance_mm}mm</span></span>
          </div>
        )}

        {/* Materials */}
        {machine.materials?.length > 0 && (
          <div className="mb-3">
            <p className="text-[10px] text-slate-400 uppercase font-medium mb-1.5">Materials</p>
            <div className="flex flex-wrap gap-1">
              {machine.materials.slice(0, 5).map((mat) => (
                <span key={`mat-${mat}`} className="text-[10px] px-2 py-0.5 rounded-full bg-blue-50 text-blue-600 font-medium">{mat}</span>
              ))}
              {machine.materials.length > 5 && <span className="text-[10px] text-slate-400">+{machine.materials.length - 5}</span>}
            </div>
          </div>
        )}

        {/* Manufacturer */}
        <div className="pt-3 border-t border-slate-100">
          <div className="flex items-center justify-between">
            <Link to={`/vendors/${machine.vendor_id}`} className="text-xs text-slate-700 hover:text-orange-600 font-medium flex items-center gap-1 truncate max-w-[60%]" data-testid={`machine-vendor-${machine.machine_id}`}>
              <Factory className="w-3 h-3 flex-shrink-0" /> {machine.vendor_name}
            </Link>
            <Button size="sm" variant="ghost" className="text-xs text-orange-600 hover:bg-orange-50 h-7 px-2" onClick={onSubmitRFQ}>
              Submit RFQ <ChevronRight className="w-3 h-3 ml-0.5" />
            </Button>
          </div>
          {machine.vendor_city && (
            <p className="text-[10px] text-slate-400 mt-1 flex items-center gap-1 ml-0.5">
              <MapPin className="w-2.5 h-2.5" /> {machine.vendor_city}
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  </motion.div>
  );
};

const PublicMachines = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [machines, setMachines] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [materialFilter, setMaterialFilter] = useState("");
  const [filterOptions, setFilterOptions] = useState({ machine_types: [] });
  const [showAuthGate, setShowAuthGate] = useState(false);
  const [total, setTotal] = useState(0);

  const fetchMachines = async (machineType, material) => {
    setLoading(true);
    try {
      let url = `${API_URL}/api/public/machines?limit=50`;
      if (machineType) url += `&machine_type=${encodeURIComponent(machineType)}`;
      if (material) url += `&material=${encodeURIComponent(material)}`;
      const res = await fetch(url);
      const data = await res.json();
      setMachines(data.machines || []);
      setTotal(data.total || 0);
      if (data.filters) setFilterOptions(data.filters);
    } catch { setMachines([]); }
    setLoading(false);
  };

  useEffect(() => { fetchMachines(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleFilter = () => fetchMachines(typeFilter, materialFilter);

  const handleSubmitRFQ = () => {
    if (user) navigate("/buyer/rfq/new");
    else setShowAuthGate(true);
  };

  const filteredMachines = searchQuery
    ? machines.filter(m =>
        `${m.brand} ${m.model}`.toLowerCase().includes(searchQuery.toLowerCase()) ||
        m.machine_type?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        m.vendor_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        m.materials?.some(mat => mat.toLowerCase().includes(searchQuery.toLowerCase()))
      )
    : machines;

  // Sort: available machines first, then engaged, then rest
  const sortedMachines = [...filteredMachines].sort((a, b) => {
    const order = { available: 0, engaged: 1, maintenance: 2, offline: 3 };
    const aOrder = order[a.availability_status] ?? 0;
    const bOrder = order[b.availability_status] ?? 0;
    return aOrder - bOrder;
  });

  const availableCount = sortedMachines.filter(m => !m.availability_status || m.availability_status === "available").length;

  return (
    <div className="min-h-screen bg-slate-50" data-testid="public-machines-page">
      <AuthGateModal isOpen={showAuthGate} onClose={() => setShowAuthGate(false)} />

      <PublicNav activePage="/machines" />

      {/* Hero */}
      <div className="bg-gradient-to-b from-slate-900 to-slate-800 text-white pt-32 sm:pt-36 pb-12 sm:pb-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <motion.h1 initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-3xl sm:text-4xl lg:text-5xl font-bold mb-4">
            Explore <span className="text-orange-400">Machine Capabilities</span>
          </motion.h1>
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }} className="text-base text-slate-300 max-w-2xl mx-auto mb-8">
            Browse CNC lathes, milling centers, 5-axis machines, grinders, and more across our verified manufacturer network.
          </motion.p>

          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="max-w-3xl mx-auto">
            <div className="flex flex-col sm:flex-row gap-2 bg-white/10 backdrop-blur-sm p-2 rounded-xl">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input placeholder="Search by brand, model, type, or material..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 bg-white text-slate-900 border-0 h-10" data-testid="machine-search-input" />
              </div>
              <div className="flex gap-2">
                <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}
                  className="bg-white text-slate-900 border-0 h-10 rounded-md px-3 text-sm" data-testid="machine-type-filter">
                  <option value="">All Types</option>
                  {filterOptions.machine_types.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
                <Input placeholder="Material..." value={materialFilter} onChange={(e) => setMaterialFilter(e.target.value)}
                  className="bg-white text-slate-900 border-0 h-10 w-32" data-testid="machine-material-filter" />
                <Button onClick={handleFilter} className="bg-orange-600 hover:bg-orange-700 h-10 px-4" data-testid="machine-filter-btn">
                  <Filter className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </motion.div>

          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }} className="flex items-center justify-center gap-6 mt-6 text-sm">
            <span>
              <span className="text-2xl font-bold text-orange-400">{total}</span>
              <span className="text-slate-400 ml-1">Total</span>
            </span>
            <span className="w-px h-8 bg-slate-700" />
            <span>
              <span className="text-2xl font-bold text-emerald-400">{availableCount}</span>
              <span className="text-slate-400 ml-1">Available for Job</span>
            </span>
          </motion.p>
        </div>
      </div>

      {/* Machine Grid */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-between mb-6">
          <p className="text-sm text-slate-500">{loading ? "Loading..." : `${sortedMachines.length} capabilit${sortedMachines.length !== 1 ? "ies" : "y"}`}</p>
          {!user && (
            <p className="text-xs text-slate-400"><Lock className="w-3 h-3 inline mr-1" />Register to submit RFQs</p>
          )}
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16"><Loader2 className="w-8 h-8 animate-spin text-orange-600" /></div>
        ) : sortedMachines.length === 0 ? (
          <div className="text-center py-16">
            <Wrench className="w-12 h-12 text-slate-300 mx-auto mb-3" />
            <p className="text-slate-500 font-medium">No machines found</p>
          </div>
        ) : (
          <motion.div initial="hidden" animate="show" variants={{ show: { transition: { staggerChildren: 0.03 } } }}
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4" data-testid="machine-grid">
            {sortedMachines.map(m => <MachineCard key={m.machine_id} machine={m} onSubmitRFQ={handleSubmitRFQ} />)}
          </motion.div>
        )}
      </div>

      {!user && (
        <div className="bg-slate-900 py-12">
          <div className="max-w-3xl mx-auto text-center px-4">
            <h2 className="text-xl sm:text-2xl font-bold text-white mb-3">Found the Right Machine?</h2>
            <p className="text-sm text-slate-400 mb-6">Submit your RFQ and our AI will match you with the best vendor automatically.</p>
            <Button size="lg" onClick={() => navigate("/register")} className="bg-orange-600 hover:bg-orange-700 text-white" data-testid="cta-register-btn">
              Create Free Account <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          </div>
        </div>
      )}

      <footer className="bg-white border-t border-slate-200 py-6">
        <div className="max-w-7xl mx-auto px-4 text-center text-xs text-slate-400">
          <Link to="/" className="hover:text-orange-600">Home</Link>
          <span className="mx-2">·</span>
          <Link to="/rfqs" className="hover:text-orange-600">RFQs</Link>
          <span className="mx-2">·</span>
          <Link to="/machines" className="hover:text-orange-600">Capabilities</Link>
          <span className="mx-2">·</span>
          <Link to="/#contact" className="hover:text-orange-600">Contact</Link>
          <p className="mt-2">OEMLinker — AI-Powered Manufacturing Marketplace</p>
        </div>
      </footer>
    </div>
  );
};

export default PublicMachines;
