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
  ImageIcon, Loader2, Send
} from "lucide-react";

const API_URL = window.location.origin;
const fadeUp = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0, transition: { duration: 0.4 } } };

const STATUS_COLORS = {
  draft: "bg-slate-100 text-slate-600",
  open: "bg-emerald-100 text-emerald-700",
  submitted: "bg-blue-100 text-blue-700",
  analyzing: "bg-indigo-100 text-indigo-700",
  matching: "bg-amber-100 text-amber-700",
  quoted: "bg-purple-100 text-purple-700",
  awarded: "bg-green-100 text-green-700",
  in_production: "bg-cyan-100 text-cyan-700",
  po_issued: "bg-teal-100 text-teal-700",
  completed: "bg-emerald-100 text-emerald-700",
  expired: "bg-red-100 text-red-700",
  cancelled: "bg-red-100 text-red-700",
};

const STATUS_LABELS = {
  open: "Open for Quotes",
  submitted: "Open for Quotes",
  draft: "Draft",
  analyzing: "Analyzing",
  matching: "Matching Vendors",
  quoted: "Quoted",
  awarded: "Awarded",
  in_production: "In Production",
  po_issued: "PO Issued",
  completed: "Completed",
  expired: "Expired",
  cancelled: "Cancelled",
};

const AuthGateModal = ({ isOpen, onClose, action }) => {
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
        <h3 className="text-xl font-bold text-slate-900 mb-2">
          {action === "quote" ? "Register as a Vendor to Quote" : "Create a Free Account"}
        </h3>
        <p className="text-sm text-slate-500 mb-6">
          {action === "quote"
            ? "Join OEMLinker as a vendor to submit quotes on RFQs and win manufacturing orders."
            : "Register to submit your own RFQ and get matched with vendors instantly."}
        </p>
        <div className="space-y-3">
          <Button className="w-full bg-orange-600 hover:bg-orange-700 text-white" onClick={() => navigate("/register")} data-testid="auth-gate-register-btn">
            {action === "quote" ? "Register as Vendor" : "Sign Up Free"} <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
          <Button variant="outline" className="w-full" onClick={() => navigate("/login")} data-testid="auth-gate-login-btn">Already have an account? Sign In</Button>
        </div>
        <p className="text-[10px] text-slate-400 text-center mt-4">No credit card required. Your data is secure.</p>
      </motion.div>
    </div>
  );
};

const DrawingThumbnail = ({ drawingId }) => {
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState(false);

  if (!drawingId) {
    return (
      <div className="w-full h-full bg-slate-100 flex items-center justify-center">
        <ImageIcon className="w-8 h-8 text-slate-300" />
      </div>
    );
  }

  return (
    <div className="w-full h-full bg-slate-100 flex items-center justify-center overflow-hidden">
      {!loaded && !error && <div className="w-6 h-6 border-2 border-orange-300 border-t-transparent rounded-full animate-spin" />}
      <img
        src={`${API_URL}/api/public/drawings/${drawingId}/thumbnail`}
        alt="Drawing"
        className={`w-full h-full object-cover transition-opacity duration-300 ${loaded ? "opacity-100" : "opacity-0"}`}
        onLoad={() => setLoaded(true)}
        onError={() => setError(true)}
        style={error ? { display: "none" } : {}}
      />
      {error && <ImageIcon className="w-8 h-8 text-slate-300" />}
    </div>
  );
};

const RFQCard = ({ rfq, onQuoteClick }) => {
  const isQuotable = ["open", "submitted", "draft", "matching", "analyzing"].includes(rfq.status);
  
  return (
    <motion.div variants={fadeUp}>
      <Card className={`border hover:shadow-lg transition-all duration-300 h-full overflow-hidden ${
        isQuotable ? "border-emerald-200 hover:border-emerald-400" : "border-slate-200 hover:border-slate-300"
      }`}>
        {/* Drawing Preview */}
        <div className="h-36 relative">
          <DrawingThumbnail drawingId={rfq.drawing_id} />
          <div className="absolute top-2 left-2">
            <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[rfq.status] || "bg-slate-100 text-slate-600"}`}>
              {STATUS_LABELS[rfq.status] || rfq.status?.replace(/_/g, " ")}
            </span>
          </div>
          {isQuotable && (
            <div className="absolute top-2 right-2">
              <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold bg-emerald-500 text-white animate-pulse">
                Accepting Quotes
              </span>
            </div>
          )}
        </div>

        <CardContent className="p-4">
          <div className="mb-2">
            <p className="text-[10px] text-slate-400 font-mono">{rfq.rfq_number || "—"}</p>
            <h3 className="font-bold text-slate-900 text-sm truncate mt-0.5" data-testid={`rfq-title-${rfq.rfq_id}`}>{rfq.title}</h3>
          </div>

          <div className="grid grid-cols-2 gap-1.5 mb-3 text-xs">
            <div className="flex items-center gap-1.5 text-slate-500">
              <Layers className="w-3 h-3 text-blue-500 flex-shrink-0" />
              <span className="truncate">{rfq.material || "—"}</span>
            </div>
            <div className="flex items-center gap-1.5 text-slate-500">
              <Package className="w-3 h-3 text-amber-500 flex-shrink-0" />
              <span>{rfq.quantity} pc{rfq.quantity > 1 ? "s" : ""}</span>
            </div>
            {rfq.geometry && (
              <div className="flex items-center gap-1.5 text-slate-500">
                <Target className="w-3 h-3 text-emerald-500 flex-shrink-0" />
                <span className="capitalize truncate">{rfq.geometry}</span>
              </div>
            )}
            {rfq.complexity && (
              <div className="flex items-center gap-1.5 text-slate-500">
                <Cpu className="w-3 h-3 text-orange-500 flex-shrink-0" />
                <span>Complexity {rfq.complexity}/10</span>
              </div>
            )}
          </div>

          {rfq.processes?.length > 0 && (
            <div className="flex flex-wrap gap-1 mb-3">
              {rfq.processes.slice(0, 3).map((p, i) => (
                <span key={i} className="text-[10px] px-1.5 py-0.5 rounded-full bg-orange-50 text-orange-600 font-medium">{p}</span>
              ))}
              {rfq.processes.length > 3 && <span className="text-[10px] text-slate-400">+{rfq.processes.length - 3}</span>}
            </div>
          )}

          {rfq.dimensions_summary && rfq.dimensions_summary !== "— × — × — mm" && (
            <p className="text-[10px] text-slate-400 font-mono mb-3">{rfq.dimensions_summary}</p>
          )}

          <div className="flex items-center justify-between pt-2 border-t border-slate-100">
            <span className="text-[10px] text-slate-400 flex items-center gap-1">
              <Clock className="w-3 h-3" /> {rfq.created_at ? new Date(rfq.created_at).toLocaleDateString() : "—"}
            </span>
            {isQuotable && (
              <Button
                size="sm"
                className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs h-7 px-3"
                onClick={(e) => { e.stopPropagation(); onQuoteClick(); }}
                data-testid={`quote-btn-${rfq.rfq_id}`}
              >
                <Send className="w-3 h-3 mr-1" /> Quote
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
};

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
  const [authAction, setAuthAction] = useState("rfq");
  const [total, setTotal] = useState(0);

  const fetchRfqs = async (material, process) => {
    setLoading(true);
    try {
      let url = `${API_URL}/api/public/rfqs?limit=40`;
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

  const handleQuoteClick = () => {
    if (user) {
      navigate("/vendor/dashboard");
    } else {
      setAuthAction("quote");
      setShowAuthGate(true);
    }
  };

  const handleSubmitRFQ = () => {
    if (user) {
      navigate("/buyer/rfq/new");
    } else {
      setAuthAction("rfq");
      setShowAuthGate(true);
    }
  };

  const filteredRfqs = searchQuery
    ? rfqs.filter(r =>
        r.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        r.material?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        r.processes?.some(p => p.toLowerCase().includes(searchQuery.toLowerCase()))
      )
    : rfqs;

  // Split into quotable and non-quotable
  const quotableStatuses = new Set(["open", "submitted", "draft", "matching", "analyzing"]);
  const quotable = filteredRfqs.filter(r => quotableStatuses.has(r.status));
  const rest = filteredRfqs.filter(r => !quotableStatuses.has(r.status));

  return (
    <div className="min-h-screen bg-slate-50" data-testid="public-rfqs-page">
      <AuthGateModal isOpen={showAuthGate} onClose={() => setShowAuthGate(false)} action={authAction} />

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
            <span className="text-sm text-slate-500 font-medium">RFQ Marketplace</span>
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
            Browse <span className="text-orange-400">RFQ Marketplace</span>
          </motion.h1>
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }} className="text-base text-slate-300 max-w-2xl mx-auto mb-8">
            Explore manufacturing requests with part drawings, materials, and processes. Vendors — register to quote on open RFQs.
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

          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }} className="flex items-center justify-center gap-6 mt-6 text-sm">
            <div>
              <p className="text-2xl font-bold text-orange-400">{total}</p>
              <p className="text-slate-400">Total RFQs</p>
            </div>
            <div className="w-px h-8 bg-slate-700" />
            <div>
              <p className="text-2xl font-bold text-emerald-400">{quotable.length}</p>
              <p className="text-slate-400">Open for Quotes</p>
            </div>
          </motion.div>
        </div>
      </div>

      {/* RFQ Grid */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

        {loading ? (
          <div className="flex items-center justify-center py-16"><Loader2 className="w-8 h-8 animate-spin text-orange-600" /></div>
        ) : filteredRfqs.length === 0 ? (
          <div className="text-center py-16">
            <FileText className="w-12 h-12 text-slate-300 mx-auto mb-3" />
            <p className="text-slate-500 font-medium">No RFQs found</p>
          </div>
        ) : (
          <>
            {/* Open / Quotable RFQs */}
            {quotable.length > 0 && (
              <div className="mb-8">
                <div className="flex items-center gap-3 mb-4">
                  <h2 className="text-base font-bold text-slate-900">Open for Quotes</h2>
                  <span className="text-xs text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full font-medium">{quotable.length} RFQs</span>
                  {!user && (
                    <span className="text-[10px] text-slate-400 ml-auto"><Lock className="w-3 h-3 inline mr-1" />Register as vendor to submit quotes</span>
                  )}
                </div>
                <motion.div initial="hidden" animate="show" variants={{ show: { transition: { staggerChildren: 0.03 } } }}
                  className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4" data-testid="rfq-grid-quotable">
                  {quotable.map(rfq => <RFQCard key={rfq.rfq_id} rfq={rfq} onQuoteClick={handleQuoteClick} />)}
                </motion.div>
              </div>
            )}

            {/* Quoted / Completed / Expired */}
            {rest.length > 0 && (
              <div>
                <div className="flex items-center gap-3 mb-4">
                  <h2 className="text-base font-bold text-slate-900">Quoted & Completed</h2>
                  <span className="text-xs text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full font-medium">{rest.length} RFQs</span>
                </div>
                <motion.div initial="hidden" animate="show" variants={{ show: { transition: { staggerChildren: 0.03 } } }}
                  className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 opacity-80" data-testid="rfq-grid-completed">
                  {rest.map(rfq => <RFQCard key={rfq.rfq_id} rfq={rfq} onQuoteClick={handleQuoteClick} />)}
                </motion.div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Dual CTA */}
      {!user && (
        <div className="bg-slate-900 py-12">
          <div className="max-w-4xl mx-auto px-4 grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="text-center p-6 rounded-xl bg-gradient-to-br from-emerald-900/30 to-emerald-800/20 border border-emerald-800/30">
              <h3 className="text-lg font-bold text-white mb-2">Are You a Manufacturer?</h3>
              <p className="text-sm text-slate-400 mb-4">Register as a vendor to quote on open RFQs and win orders.</p>
              <Button onClick={() => { setAuthAction("quote"); setShowAuthGate(true); }}
                className="bg-emerald-600 hover:bg-emerald-700 text-white" data-testid="cta-vendor-register">
                Register as Vendor <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </div>
            <div className="text-center p-6 rounded-xl bg-gradient-to-br from-orange-900/30 to-amber-800/20 border border-orange-800/30">
              <h3 className="text-lg font-bold text-white mb-2">Need Parts Manufactured?</h3>
              <p className="text-sm text-slate-400 mb-4">Upload your drawing, get AI analysis and vendor matches in minutes.</p>
              <Button onClick={handleSubmitRFQ} className="bg-orange-600 hover:bg-orange-700 text-white" data-testid="cta-buyer-register">
                Submit Your RFQ <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </div>
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
