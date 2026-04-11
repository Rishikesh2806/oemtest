import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../App";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Card, CardContent } from "../components/ui/card";
import { motion } from "framer-motion";
import {
  FileText, Search, Filter, ArrowRight, Lock, X,
  Factory, Cpu, Layers, Target, Package, Clock,
  ChevronRight, Loader2
} from "lucide-react";

const API_URL = window.location.origin;
const fadeUp = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0, transition: { duration: 0.4 } } };

const STATUS_COLORS = {
  draft: "bg-slate-100 text-slate-600",
  submitted: "bg-blue-100 text-blue-700",
  matching: "bg-amber-100 text-amber-700",
  quoted: "bg-purple-100 text-purple-700",
  awarded: "bg-green-100 text-green-700",
  in_production: "bg-cyan-100 text-cyan-700",
  completed: "bg-emerald-100 text-emerald-700",
  cancelled: "bg-red-100 text-red-700",
};

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
        <p className="text-sm text-slate-500 mb-6">Register to submit your own RFQ and get matched with vendors instantly.</p>
        <div className="space-y-3">
          <Button className="w-full bg-orange-600 hover:bg-orange-700 text-white" onClick={() => navigate("/register")} data-testid="auth-gate-register-btn">
            Sign Up Free <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
          <Button variant="outline" className="w-full" onClick={() => navigate("/login")} data-testid="auth-gate-login-btn">Already have an account? Sign In</Button>
        </div>
        <p className="text-[10px] text-slate-400 text-center mt-4">No credit card required. Your data is secure.</p>
      </motion.div>
    </div>
  );
};

const RFQCard = ({ rfq }) => (
  <motion.div variants={fadeUp}>
    <Card className="border border-slate-200 hover:border-orange-300 hover:shadow-lg transition-all duration-300 h-full">
      <CardContent className="p-5">
        <div className="flex items-start justify-between mb-2">
          <div className="flex-1 min-w-0">
            <p className="text-[10px] text-slate-400 font-mono">{rfq.rfq_number || "—"}</p>
            <h3 className="font-bold text-slate-900 text-sm truncate mt-0.5" data-testid={`rfq-title-${rfq.rfq_id}`}>{rfq.title}</h3>
          </div>
          <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium whitespace-nowrap ml-2 ${STATUS_COLORS[rfq.status] || "bg-slate-100 text-slate-600"}`}>
            {(rfq.status || "draft").replace(/_/g, " ")}
          </span>
        </div>

        <div className="grid grid-cols-2 gap-2 mb-3 text-xs">
          <div className="flex items-center gap-1.5 text-slate-500">
            <Layers className="w-3 h-3 text-blue-500" />
            <span>{rfq.material || "—"}</span>
          </div>
          <div className="flex items-center gap-1.5 text-slate-500">
            <Package className="w-3 h-3 text-amber-500" />
            <span>{rfq.quantity} pc{rfq.quantity > 1 ? "s" : ""}</span>
          </div>
          {rfq.geometry && (
            <div className="flex items-center gap-1.5 text-slate-500">
              <Target className="w-3 h-3 text-emerald-500" />
              <span className="capitalize">{rfq.geometry}</span>
            </div>
          )}
          {rfq.complexity && (
            <div className="flex items-center gap-1.5 text-slate-500">
              <Cpu className="w-3 h-3 text-orange-500" />
              <span>Complexity {rfq.complexity}/10</span>
            </div>
          )}
        </div>

        {rfq.processes?.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-3">
            {rfq.processes.slice(0, 4).map((p, i) => (
              <span key={i} className="text-[10px] px-2 py-0.5 rounded-full bg-orange-50 text-orange-600 font-medium">{p}</span>
            ))}
            {rfq.processes.length > 4 && <span className="text-[10px] text-slate-400">+{rfq.processes.length - 4}</span>}
          </div>
        )}

        {rfq.dimensions_summary && rfq.dimensions_summary !== "— × — × — mm" && (
          <p className="text-[10px] text-slate-400 font-mono mb-3">{rfq.dimensions_summary}</p>
        )}

        {rfq.surface_finish && (
          <p className="text-[10px] text-slate-400 mb-3">Finish: {rfq.surface_finish}</p>
        )}

        <div className="flex items-center justify-between text-[10px] text-slate-400 pt-2 border-t border-slate-100">
          <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> {new Date(rfq.created_at).toLocaleDateString()}</span>
          {rfq.supply_type === "buyer_material" && (
            <span className="text-green-600 font-medium">Buyer Material</span>
          )}
        </div>
      </CardContent>
    </Card>
  </motion.div>
);

const PublicRFQs = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [rfqs, setRfqs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [materialFilter, setMaterialFilter] = useState("");
  const [processFilter, setProcessFilter] = useState("");
  const [filters, setFilters] = useState({ materials: [], statuses: [] });
  const [showAuthGate, setShowAuthGate] = useState(false);
  const [total, setTotal] = useState(0);

  const fetchRfqs = async (material, process) => {
    setLoading(true);
    try {
      let url = `${API_URL}/api/public/rfqs?limit=30`;
      if (material) url += `&material=${encodeURIComponent(material)}`;
      if (process) url += `&process=${encodeURIComponent(process)}`;
      const res = await fetch(url);
      const data = await res.json();
      setRfqs(data.rfqs || []);
      setTotal(data.total || 0);
      if (data.filters) setFilters(data.filters);
    } catch { setRfqs([]); }
    setLoading(false);
  };

  useEffect(() => { fetchRfqs(); }, []);

  const handleFilter = () => fetchRfqs(materialFilter, processFilter);

  const filteredRfqs = searchQuery
    ? rfqs.filter(r =>
        r.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        r.material?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        r.processes?.some(p => p.toLowerCase().includes(searchQuery.toLowerCase()))
      )
    : rfqs;

  return (
    <div className="min-h-screen bg-slate-50" data-testid="public-rfqs-page">
      <AuthGateModal isOpen={showAuthGate} onClose={() => setShowAuthGate(false)} />

      <header className="bg-white border-b border-slate-200 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/" className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-orange-500 to-amber-600 flex items-center justify-center">
                <Factory className="w-4 h-4 text-white" />
              </div>
              <span className="font-bold text-slate-900 text-lg">OEMLinker</span>
            </Link>
            <span className="text-slate-300">|</span>
            <span className="text-sm text-slate-500 font-medium">RFQ Showcase</span>
          </div>
          <div className="flex items-center gap-3">
            <Link to="/vendors" className="text-sm text-slate-500 hover:text-orange-600 font-medium hidden sm:block">Vendors</Link>
            <Link to="/machines" className="text-sm text-slate-500 hover:text-orange-600 font-medium hidden sm:block">Machines</Link>
            {user ? (
              <Button size="sm" onClick={() => navigate("/dashboard")} className="bg-orange-600 hover:bg-orange-700 text-white">Dashboard</Button>
            ) : (
              <>
                <Button variant="ghost" size="sm" onClick={() => navigate("/login")}>Sign In</Button>
                <Button size="sm" onClick={() => navigate("/register")} className="bg-orange-600 hover:bg-orange-700 text-white">Get Started Free</Button>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Hero */}
      <div className="bg-gradient-to-b from-slate-900 to-slate-800 text-white py-12 sm:py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <motion.h1 initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-3xl sm:text-4xl lg:text-5xl font-bold mb-4">
            Browse <span className="text-orange-400">RFQ Showcase</span>
          </motion.h1>
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }} className="text-base text-slate-300 max-w-2xl mx-auto mb-8">
            See real manufacturing requests processed on our platform — materials, processes, complexity levels, and more.
          </motion.p>

          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="max-w-3xl mx-auto">
            <div className="flex flex-col sm:flex-row gap-2 bg-white/10 backdrop-blur-sm p-2 rounded-xl">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input placeholder="Search by part name, material, or process..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 bg-white text-slate-900 border-0 h-10" data-testid="rfq-search-input" />
              </div>
              <div className="flex gap-2">
                <select value={materialFilter} onChange={(e) => setMaterialFilter(e.target.value)}
                  className="bg-white text-slate-900 border-0 h-10 rounded-md px-3 text-sm" data-testid="rfq-material-filter">
                  <option value="">All Materials</option>
                  {filters.materials.map(m => <option key={m} value={m}>{m}</option>)}
                </select>
                <Input placeholder="Process..." value={processFilter} onChange={(e) => setProcessFilter(e.target.value)}
                  className="bg-white text-slate-900 border-0 h-10 w-32" data-testid="rfq-process-filter" />
                <Button onClick={handleFilter} className="bg-orange-600 hover:bg-orange-700 h-10 px-4" data-testid="rfq-filter-btn">
                  <Filter className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </motion.div>

          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }} className="text-sm text-slate-400 mt-6">
            <span className="text-2xl font-bold text-orange-400">{total}</span> RFQs processed on our platform
          </motion.p>
        </div>
      </div>

      {/* RFQ Grid */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-between mb-6">
          <p className="text-sm text-slate-500">{loading ? "Loading..." : `${filteredRfqs.length} RFQ${filteredRfqs.length !== 1 ? "s" : ""}`}</p>
          {!user && (
            <Button size="sm" onClick={() => setShowAuthGate(true)} className="bg-orange-600 hover:bg-orange-700 text-white text-xs" data-testid="submit-rfq-btn">
              <FileText className="w-3.5 h-3.5 mr-1.5" /> Submit Your RFQ
            </Button>
          )}
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16"><Loader2 className="w-8 h-8 animate-spin text-orange-600" /></div>
        ) : filteredRfqs.length === 0 ? (
          <div className="text-center py-16">
            <FileText className="w-12 h-12 text-slate-300 mx-auto mb-3" />
            <p className="text-slate-500 font-medium">No RFQs found</p>
          </div>
        ) : (
          <motion.div initial="hidden" animate="show" variants={{ show: { transition: { staggerChildren: 0.03 } } }}
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4" data-testid="rfq-grid">
            {filteredRfqs.map(rfq => <RFQCard key={rfq.rfq_id} rfq={rfq} />)}
          </motion.div>
        )}
      </div>

      {!user && (
        <div className="bg-slate-900 py-12">
          <div className="max-w-3xl mx-auto text-center px-4">
            <h2 className="text-xl sm:text-2xl font-bold text-white mb-3">Need Parts Manufactured?</h2>
            <p className="text-sm text-slate-400 mb-6">Upload your drawing, get AI analysis and matched vendors in minutes.</p>
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
          <Link to="/vendors" className="hover:text-orange-600">Vendors</Link>
          <span className="mx-2">·</span>
          <Link to="/machines" className="hover:text-orange-600">Machines</Link>
          <span className="mx-2">·</span>
          <Link to="/rfqs" className="hover:text-orange-600">RFQs</Link>
          <p className="mt-2">OEMLinker — AI-Powered Manufacturing Marketplace</p>
        </div>
      </footer>
    </div>
  );
};

export default PublicRFQs;
