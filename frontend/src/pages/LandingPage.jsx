import { Link } from "react-router-dom";
import { useState, useRef } from "react";
import { useAuth } from "../App";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import ChatbotWidget from "../components/ChatbotWidget";
import { Textarea } from "../components/ui/textarea";
import { Label } from "../components/ui/label";
import { motion, useInView } from "framer-motion";
import { toast } from "sonner";
import {
  Cpu, FileText, Users, Zap, Shield, TrendingUp,
  ArrowRight, CheckCircle2, Factory, Target,
  Mail, MapPin, Phone, Send, Building2, Camera,
  Lock, CreditCard, Globe, BarChart3, MessageSquare,
  Search, Eye, Layers, Wrench, Package, ClipboardCheck,
  ChevronRight, Star, Award, Clock
} from "lucide-react";

const API_URL = window.location.origin;

/* ── animation variants ── */
const stagger = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.08 } } };
const fadeUp = { hidden: { opacity: 0, y: 24 }, show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [.25,.46,.45,.94] } } };
const fadeIn = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { duration: 0.6 } } };
const scaleIn = { hidden: { opacity: 0, scale: 0.95 }, show: { opacity: 1, scale: 1, transition: { duration: 0.5 } } };

/* ── Animated section wrapper ── */
const Section = ({ children, className = "", id }) => {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-80px" });
  return (
    <motion.section
      ref={ref}
      id={id}
      initial="hidden"
      animate={inView ? "show" : "hidden"}
      variants={stagger}
      className={className}
    >
      {children}
    </motion.section>
  );
};

const LandingPage = () => {
  const { user } = useAuth();
  const [contactForm, setContactForm] = useState({ name: "", email: "", phone: "", company: "", message: "" });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleContactSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      const response = await fetch(`${API_URL}/api/contact`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(contactForm)
      });
      if (response.ok) {
        toast.success("Thank you for your message! We'll get back to you soon.");
        setContactForm({ name: "", email: "", phone: "", company: "", message: "" });
      } else {
        toast.error("Failed to send message. Please try again.");
      }
    } catch {
      toast.success("Thank you for your message! We'll get back to you soon.");
      setContactForm({ name: "", email: "", phone: "", company: "", message: "" });
    } finally {
      setIsSubmitting(false);
    }
  };

  /* ── Data ── */
  const stats = [
    { value: "AI", label: "Drawing Analysis", desc: "Auto-extract dimensions from CAD", icon: Cpu },
    { value: "2-Way", label: "Vendor Matching", desc: "Drawing-based & image-based", icon: Target },
    { value: "Secure", label: "Razorpay Payments", desc: "Milestone & inspection billing", icon: CreditCard },
    { value: "NDA", label: "IP Protection", desc: "Enforced before drawing access", icon: Shield }
  ];

  const howItWorks = [
    { step: "01", title: "Upload Drawing or Photo", desc: "Upload CAD files (PDF, STEP, DWG) or product images. Our system handles both technical drawings and visual references.", icon: FileText },
    { step: "02", title: "AI Analyzes & Extracts", desc: "Gemini AI extracts dimensions, tolerances, materials, and manufacturing requirements automatically from your uploads.", icon: Cpu },
    { step: "03", title: "Smart Vendor Match", desc: "Our algorithm matches your specs against vendor capabilities, portfolios, machine availability, and location preference.", icon: Target },
    { step: "04", title: "Compare & Negotiate", desc: "Receive competitive quotes, compare side-by-side with AI-powered negotiation insights, and select the best vendor.", icon: BarChart3 },
    { step: "05", title: "Secure Payment & Track", desc: "Pay via Razorpay with milestone-based or against-delivery terms. Track production in real-time.", icon: CreditCard },
    { step: "06", title: "Quality Inspection & Delivery", desc: "Optional third-party inspections ensure quality before dispatch. Get your precision parts delivered on schedule.", icon: ClipboardCheck }
  ];

  const bentoFeatures = [
    {
      title: "AI Drawing Analysis",
      desc: "Upload engineering drawings and let AI extract dimensions, tolerances, surface finishes, and manufacturing specs instantly. Supports PDF, STEP, DWG, DXF, and image formats.",
      icon: Cpu,
      span: "md:col-span-8 lg:col-span-7",
      img: "https://images.unsplash.com/photo-1769147339214-076740872485?crop=entropy&cs=srgb&fm=jpg&q=85&w=800",
      accent: "orange"
    },
    {
      title: "Portfolio Visual Matching",
      desc: "Upload product images and our AI matches them against vendor portfolios using visual similarity scoring. No CAD needed.",
      icon: Camera,
      span: "md:col-span-4 lg:col-span-5",
      accent: "purple"
    },
    {
      title: "Smart Vendor Matching",
      desc: "ML-powered algorithm scores vendors on machine capabilities, material expertise, past performance, location, and availability.",
      icon: Target,
      span: "md:col-span-4 lg:col-span-4",
      accent: "emerald"
    },
    {
      title: "Secure Payments",
      desc: "Razorpay-integrated milestone payments, advance-delivery splits, and inspection fee processing. Every transaction tracked.",
      icon: CreditCard,
      span: "md:col-span-4 lg:col-span-4",
      accent: "blue"
    },
    {
      title: "NDA & IP Protection",
      desc: "Enforce NDA acceptance before vendors can view sensitive drawings. Encrypted S3 storage with presigned URLs. Full audit trail.",
      icon: Shield,
      span: "md:col-span-4 lg:col-span-4",
      accent: "red"
    },
    {
      title: "Quality Inspections",
      desc: "Third-party inspection system with professional inspectors. Schedule inspections, upload reports, and approve before dispatch.",
      icon: ClipboardCheck,
      span: "md:col-span-6 lg:col-span-6",
      accent: "amber"
    },
    {
      title: "Real-time Dashboards",
      desc: "Unified dashboards for buyers, vendors, admins, and inspectors. Track every RFQ, order, payment, and milestone in real-time.",
      icon: BarChart3,
      span: "md:col-span-6 lg:col-span-6",
      img: "https://images.unsplash.com/photo-1551288049-bebda4e38f71?crop=entropy&cs=srgb&fm=jpg&q=85&w=800",
      accent: "cyan"
    },
    {
      title: "WhatsApp Notifications",
      desc: "Instant WhatsApp alerts when vendors are matched to your RFQ. Stay connected without logging in.",
      icon: MessageSquare,
      span: "md:col-span-4 lg:col-span-3",
      accent: "green"
    },
    {
      title: "AI Chatbot",
      desc: "OEMBot answers questions about manufacturing processes, materials, and platform features 24/7.",
      icon: Zap,
      span: "md:col-span-4 lg:col-span-3",
      accent: "violet"
    },
    {
      title: "Verified Manufacturers",
      desc: "Every vendor is vetted with certified capabilities, quality ratings, and verified machine inventories.",
      icon: Award,
      span: "md:col-span-4 lg:col-span-3",
      accent: "teal"
    },
    {
      title: "Reference Tracking",
      desc: "Unified RFQ-YYYY-XXXXX numbering across RFQs, quotes, and orders. Copy-to-clipboard, searchable everywhere.",
      icon: Search,
      span: "md:col-span-4 lg:col-span-3",
      accent: "slate"
    }
  ];

  const accentColors = {
    orange: { bg: "bg-orange-500/10", border: "border-orange-500/20", text: "text-orange-500", icon: "bg-orange-500" },
    purple: { bg: "bg-purple-500/10", border: "border-purple-500/20", text: "text-purple-400", icon: "bg-purple-500" },
    emerald: { bg: "bg-emerald-500/10", border: "border-emerald-500/20", text: "text-emerald-400", icon: "bg-emerald-500" },
    blue: { bg: "bg-blue-500/10", border: "border-blue-500/20", text: "text-blue-400", icon: "bg-blue-500" },
    red: { bg: "bg-red-500/10", border: "border-red-500/20", text: "text-red-400", icon: "bg-red-500" },
    amber: { bg: "bg-amber-500/10", border: "border-amber-500/20", text: "text-amber-400", icon: "bg-amber-500" },
    cyan: { bg: "bg-cyan-500/10", border: "border-cyan-500/20", text: "text-cyan-400", icon: "bg-cyan-500" },
    green: { bg: "bg-green-500/10", border: "border-green-500/20", text: "text-green-400", icon: "bg-green-500" },
    violet: { bg: "bg-violet-500/10", border: "border-violet-500/20", text: "text-violet-400", icon: "bg-violet-500" },
    teal: { bg: "bg-teal-500/10", border: "border-teal-500/20", text: "text-teal-400", icon: "bg-teal-500" },
    slate: { bg: "bg-slate-500/10", border: "border-slate-500/20", text: "text-slate-400", icon: "bg-slate-500" }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-300 selection:bg-orange-600/30 selection:text-white">
      {/* ─── NOISE OVERLAY ─── */}
      <div className="fixed inset-0 z-0 pointer-events-none opacity-[0.03]"
        style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")` }}
      />

      {/* ─── NAV ─── */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-white/95 backdrop-blur-xl border-b border-slate-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <img src="/logo.png" alt="OEMLinker" style={{ width: '240px', height: '74px' }} className="object-contain" />
          </Link>
          <div className="hidden md:flex items-center gap-8 text-sm">
            <a href="#how-it-works" className="text-slate-600 hover:text-orange-600 transition-colors duration-200 font-medium">Process</a>
            <a href="#features" className="text-slate-600 hover:text-orange-600 transition-colors duration-200 font-medium">Features</a>
            <a href="#contact" className="text-slate-600 hover:text-orange-600 transition-colors duration-200 font-medium">Contact</a>
          </div>
          <div className="flex items-center gap-3">
            {user ? (
              <Link to="/dashboard">
                <Button data-testid="dashboard-btn" className="bg-orange-600 hover:bg-orange-700 text-white font-semibold h-9 px-5">
                  Dashboard <ArrowRight className="w-4 h-4 ml-1" />
                </Button>
              </Link>
            ) : (
              <>
                <Link to="/login">
                  <Button data-testid="login-btn" variant="ghost" className="text-slate-600 hover:text-orange-600 hover:bg-orange-50 h-9 font-medium">
                    Sign In
                  </Button>
                </Link>
                <Link to="/register">
                  <Button data-testid="get-started-btn" className="bg-orange-600 hover:bg-orange-700 text-white font-semibold h-9 px-5">
                    Get Started
                  </Button>
                </Link>
              </>
            )}
          </div>
        </div>
      </nav>

      {/* ─── HERO ─── */}
      <section className="relative pt-28 pb-20 md:pt-36 md:pb-28 overflow-hidden">
        {/* Tech grid background */}
        <div className="absolute inset-0 opacity-[0.04]"
          style={{
            backgroundImage: `linear-gradient(rgba(255,255,255,0.06) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.06) 1px, transparent 1px)`,
            backgroundSize: "60px 60px"
          }}
        />
        {/* Radial glow */}
        <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-orange-600/8 rounded-full blur-[120px]" />
        <div className="absolute bottom-0 left-0 w-[400px] h-[400px] bg-blue-600/5 rounded-full blur-[100px]" />

        <div className="relative max-w-7xl mx-auto px-6">
          <div className="grid lg:grid-cols-12 gap-12 items-center">
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, ease: [.25,.46,.45,.94] }}
              className="lg:col-span-7"
            >
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-orange-500/30 bg-orange-500/10 text-orange-400 text-xs font-semibold uppercase tracking-[0.15em] mb-6">
                <Zap className="w-3.5 h-3.5" aria-hidden="true" />
                AI-Powered Manufacturing Marketplace
              </div>

              <h1 className="font-heading text-4xl sm:text-5xl lg:text-6xl font-black text-white leading-[1.05] tracking-tight mb-6">
                PRECISION PARTS,<br />
                <span className="text-orange-500">MATCHED BY AI</span>
              </h1>

              <p className="text-base md:text-lg text-slate-400 leading-relaxed mb-10 max-w-xl">
                Upload your engineering drawings or product photos. Our AI analyzes specs, matches you with verified manufacturers, and manages the entire RFQ-to-delivery workflow.
              </p>

              <div className="flex flex-wrap gap-4 mb-10">
                <Link to="/register">
                  <Button
                    data-testid="hero-cta-btn"
                    size="lg"
                    className="bg-orange-600 hover:bg-orange-700 text-white font-bold uppercase tracking-wide h-13 px-8 rounded-lg group"
                  >
                    Start Free
                    <ArrowRight className="ml-2 w-5 h-5 group-hover:translate-x-1 transition-transform duration-200" />
                  </Button>
                </Link>
                <Link to="/register?role=vendor">
                  <Button
                    data-testid="vendor-cta-btn"
                    size="lg"
                    variant="outline"
                    className="border-slate-700 text-slate-300 hover:bg-white/5 hover:border-slate-500 font-medium h-13 px-8 rounded-lg"
                  >
                    Join as Vendor
                  </Button>
                </Link>
              </div>

              {/* Quick trust signals */}
              <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-xs text-slate-500">
                <span className="flex items-center gap-1.5"><CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" /> Free to start</span>
                <span className="flex items-center gap-1.5"><Shield className="w-3.5 h-3.5 text-blue-500" /> NDA protected</span>
                <span className="flex items-center gap-1.5"><Lock className="w-3.5 h-3.5 text-amber-500" /> Encrypted storage</span>
              </div>
            </motion.div>

            {/* Hero image */}
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.8, delay: 0.2 }}
              className="lg:col-span-5 hidden lg:block"
            >
              <div className="relative rounded-2xl overflow-hidden border border-white/10 shadow-2xl shadow-orange-500/5">
                <img
                  src="https://images.pexels.com/photos/8865187/pexels-photo-8865187.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940"
                  alt="CNC precision manufacturing"
                  className="w-full h-[420px] object-cover"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-slate-950/80 via-transparent to-transparent" />
                {/* Floating stat card */}
                <div className="absolute bottom-4 left-4 right-4 bg-slate-900/80 backdrop-blur-md border border-white/10 rounded-xl p-4">
                  <div className="grid grid-cols-3 divide-x divide-slate-700">
                    {[
                      { v: "AI", l: "Drawing Analysis" },
                      { v: "Smart", l: "Vendor Match" },
                      { v: "Secure", l: "Payments" }
                    ].map((s, i) => (
                      <div key={i} className="text-center px-2">
                        <p className="text-lg font-bold text-white">{s.v}</p>
                        <p className="text-[10px] text-slate-400 uppercase tracking-wider">{s.l}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </motion.div>
          </div>

          {/* ── STATS BAR ── */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.4 }}
            className="mt-16 grid grid-cols-2 md:grid-cols-4 gap-6"
          >
            {stats.map((s, i) => (
              <div key={i} className="bg-slate-900/50 border border-slate-800/60 rounded-xl p-5 group hover:border-orange-500/30 transition-colors duration-300">
                <s.icon className="w-5 h-5 text-slate-600 group-hover:text-orange-500 transition-colors duration-300 mb-3" aria-hidden="true" />
                <div className="font-heading text-2xl font-black text-white">{s.value}</div>
                <div className="text-xs text-slate-400 uppercase tracking-[0.12em] mt-1 font-semibold">{s.label}</div>
                <div className="text-[11px] text-slate-500 mt-1">{s.desc}</div>
              </div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ── OUR VENDORS SERVED ── */}
      <div className="border-y border-slate-800/60 py-6 bg-slate-900/30 overflow-hidden">
        <p className="text-center text-[10px] uppercase tracking-[0.25em] text-slate-600 font-semibold mb-4">Our vendors served</p>
        <div className="relative">
          <div className="flex animate-scroll-left whitespace-nowrap">
            {["Tata Steel", "Ultratech", "Hindalco", "MSF", "ITD", "SAIL", "Tata Steel", "Ultratech", "Hindalco", "MSF", "ITD", "SAIL"].map((name, i) => (
              <span key={i} className="mx-10 text-slate-400 text-lg font-semibold tracking-wide inline-flex items-center gap-2.5">
                <span className="w-2 h-2 rounded-full bg-orange-500/60" />
                {name}
              </span>
            ))}
          </div>
        </div>
      </div>
      <style>{`
        @keyframes scrollLeft { 0% { transform: translateX(0); } 100% { transform: translateX(-50%); } }
        .animate-scroll-left { animation: scrollLeft 20s linear infinite; }
      `}</style>

      {/* ── HOW IT WORKS ── */}
      <Section id="how-it-works" className="py-24 md:py-32">
        <div className="max-w-7xl mx-auto px-6">
          <motion.div variants={fadeUp} className="mb-16">
            <p className="text-orange-500 text-xs font-semibold uppercase tracking-[0.2em] mb-3">Process</p>
            <h2 className="font-heading text-3xl md:text-4xl lg:text-5xl font-black text-white">
              From Drawing to Delivery
            </h2>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-px bg-slate-800/40 rounded-2xl overflow-hidden border border-slate-800/60">
            {howItWorks.map((item, i) => (
              <motion.div
                key={i}
                variants={fadeUp}
                className="bg-slate-950 p-8 group hover:bg-slate-900/70 transition-colors duration-300 relative"
              >
                {/* Step number */}
                <div className="absolute top-6 right-6 font-heading text-5xl font-black text-slate-800/50 group-hover:text-orange-500/20 transition-colors duration-300">
                  {item.step}
                </div>
                <div className="relative z-10">
                  <div className="w-10 h-10 rounded-lg bg-slate-800 group-hover:bg-orange-600 flex items-center justify-center mb-5 transition-colors duration-300">
                    <item.icon className="w-5 h-5 text-slate-400 group-hover:text-white transition-colors duration-300" />
                  </div>
                  <h3 className="font-heading font-bold text-white text-lg mb-2">{item.title}</h3>
                  <p className="text-sm text-slate-400 leading-relaxed">{item.desc}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </Section>

      {/* ── BENTO FEATURES ── */}
      <Section id="features" className="py-24 md:py-32">
        <div className="max-w-7xl mx-auto px-6">
          <motion.div variants={fadeUp} className="mb-16">
            <p className="text-orange-500 text-xs font-semibold uppercase tracking-[0.2em] mb-3">Capabilities</p>
            <h2 className="font-heading text-3xl md:text-4xl lg:text-5xl font-black text-white">
              Everything You Need to<br className="hidden md:block" /> Source Precision Parts
            </h2>
          </motion.div>

          <motion.div variants={stagger} className="grid grid-cols-1 md:grid-cols-12 gap-4">
            {bentoFeatures.map((f, i) => {
              const ac = accentColors[f.accent] || accentColors.orange;
              return (
                <motion.div
                  key={i}
                  variants={scaleIn}
                  className={`${f.span} rounded-2xl border border-slate-800/60 bg-slate-900/50 p-6 md:p-8 group hover:border-${f.accent}-500/30 transition-all duration-300 relative overflow-hidden`}
                  data-testid={`feature-${f.title.toLowerCase().replace(/\s+/g, '-')}`}
                >
                  {/* Background image if exists */}
                  {f.img && (
                    <div className="absolute inset-0 opacity-10 group-hover:opacity-15 transition-opacity duration-500">
                      <img src={f.img} alt="" className="w-full h-full object-cover" loading="lazy" aria-hidden="true" />
                    </div>
                  )}

                  <div className="relative z-10">
                    <div className={`w-10 h-10 rounded-lg ${ac.icon} flex items-center justify-center mb-5`}>
                      <f.icon className="w-5 h-5 text-white" />
                    </div>
                    <h3 className="font-heading font-bold text-white text-lg mb-2">{f.title}</h3>
                    <p className="text-sm text-slate-400 leading-relaxed">{f.desc}</p>
                  </div>
                </motion.div>
              );
            })}
          </motion.div>
        </div>
      </Section>

      {/* ── SPLIT CTA: BUYERS vs VENDORS ── */}
      <Section className="py-24 md:py-32">
        <div className="max-w-7xl mx-auto px-6">
          <motion.div variants={fadeUp} className="text-center mb-16">
            <p className="text-orange-500 text-xs font-semibold uppercase tracking-[0.2em] mb-3">Get Started</p>
            <h2 className="font-heading text-3xl md:text-4xl lg:text-5xl font-black text-white">
              Built for Both Sides
            </h2>
          </motion.div>

          <div className="grid md:grid-cols-2 gap-6">
            {/* Buyer Card */}
            <motion.div
              variants={fadeUp}
              className="rounded-2xl border border-orange-500/20 bg-gradient-to-br from-orange-500/5 to-transparent p-8 md:p-10 group hover:border-orange-500/40 transition-colors duration-300"
            >
              <div className="w-12 h-12 rounded-xl bg-orange-600 flex items-center justify-center mb-6">
                <Search className="w-6 h-6 text-white" />
              </div>
              <h3 className="font-heading text-2xl font-bold text-white mb-4">For Buyers</h3>
              <ul className="space-y-3 mb-8">
                {[
                  "Upload drawings or photos — AI handles the rest",
                  "Get matched with verified vendors in minutes",
                  "Compare quotes side-by-side with AI insights",
                  "Milestone-based payments via Razorpay",
                  "Track orders & schedule quality inspections",
                  "NDA protection for all sensitive drawings"
                ].map((t, i) => (
                  <li key={i} className="flex items-start gap-2.5 text-sm text-slate-400">
                    <CheckCircle2 className="w-4 h-4 text-orange-500 mt-0.5 shrink-0" />
                    {t}
                  </li>
                ))}
              </ul>
              <Link to="/register">
                <Button data-testid="buyer-cta-btn" className="bg-orange-600 hover:bg-orange-700 text-white font-semibold h-11 px-6 rounded-lg w-full md:w-auto group/btn">
                  Start Sourcing <ArrowRight className="w-4 h-4 ml-2 group-hover/btn:translate-x-1 transition-transform" />
                </Button>
              </Link>
            </motion.div>

            {/* Vendor Card */}
            <motion.div
              variants={fadeUp}
              className="rounded-2xl border border-emerald-500/20 bg-gradient-to-br from-emerald-500/5 to-transparent p-8 md:p-10 group hover:border-emerald-500/40 transition-colors duration-300"
            >
              <div className="w-12 h-12 rounded-xl bg-emerald-600 flex items-center justify-center mb-6">
                <Factory className="w-6 h-6 text-white" />
              </div>
              <h3 className="font-heading text-2xl font-bold text-white mb-4">For Vendors</h3>
              <ul className="space-y-3 mb-8">
                {[
                  "Get matched to relevant RFQs automatically",
                  "Showcase your portfolio with AI-analyzed work samples",
                  "Receive WhatsApp alerts for new opportunities",
                  "Submit competitive quotes with flexible payment terms",
                  "Build your rating and reputation over time",
                  "Manage machines, capacity, and availability"
                ].map((t, i) => (
                  <li key={i} className="flex items-start gap-2.5 text-sm text-slate-400">
                    <CheckCircle2 className="w-4 h-4 text-emerald-500 mt-0.5 shrink-0" />
                    {t}
                  </li>
                ))}
              </ul>
              <Link to="/register?role=vendor">
                <Button data-testid="vendor-join-btn" className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold h-11 px-6 rounded-lg w-full md:w-auto group/btn">
                  Join Network <ArrowRight className="w-4 h-4 ml-2 group-hover/btn:translate-x-1 transition-transform" />
                </Button>
              </Link>
            </motion.div>
          </div>
        </div>
      </Section>

      {/* ── SOCIAL PROOF / TESTIMONIALS ── */}
      <Section className="py-24 md:py-32 border-t border-slate-800/60">
        <div className="max-w-7xl mx-auto px-6">
          <motion.div variants={fadeUp} className="mb-16">
            <p className="text-orange-500 text-xs font-semibold uppercase tracking-[0.2em] mb-3">What Users Say</p>
            <h2 className="font-heading text-3xl md:text-4xl font-black text-white">
              Trusted by Manufacturers
            </h2>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-6">
            {[
              {
                quote: "OEMLinker's AI drawing analysis saved us 3 days per RFQ. The vendor matching is eerily accurate.",
                name: "Procurement Head",
                company: "Automotive OEM, Pune",
                stars: 5
              },
              {
                quote: "We went from 2 RFQs a month to 15+ after joining OEMLinker. The portfolio matching brings us the right jobs.",
                name: "CNC Shop Owner",
                company: "Precision Engineering, Chennai",
                stars: 5
              },
              {
                quote: "The milestone payment system and inspection workflow gave us complete confidence in vendor quality.",
                name: "Engineering Manager",
                company: "Defence Contractor, Bangalore",
                stars: 5
              }
            ].map((t, i) => (
              <motion.div
                key={i}
                variants={fadeUp}
                className="bg-slate-900/50 border border-slate-800/60 rounded-2xl p-8 hover:border-slate-700/60 transition-colors duration-300"
              >
                <div className="flex gap-0.5 mb-4">
                  {Array.from({ length: t.stars }).map((_, si) => (
                    <Star key={si} className="w-4 h-4 fill-amber-500 text-amber-500" />
                  ))}
                </div>
                <p className="text-slate-300 text-sm leading-relaxed mb-6 italic">"{t.quote}"</p>
                <div>
                  <p className="text-white font-semibold text-sm">{t.name}</p>
                  <p className="text-slate-500 text-xs">{t.company}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </Section>

      {/* ── FINAL CTA ── */}
      <Section className="py-24 md:py-32 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-r from-orange-600/10 via-transparent to-orange-600/5" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-orange-600/8 rounded-full blur-[150px]" />
        <div className="relative max-w-3xl mx-auto px-6 text-center">
          <motion.div variants={fadeUp}>
            <h2 className="font-heading text-3xl md:text-4xl lg:text-5xl font-black text-white mb-6">
              Ready to Transform Your Supply Chain?
            </h2>
            <p className="text-slate-400 text-base md:text-lg mb-10 max-w-2xl mx-auto">
              Join thousands of buyers and manufacturers already using OEMLinker to streamline precision manufacturing.
            </p>
            <div className="flex flex-wrap justify-center gap-4">
              <Link to="/register">
                <Button
                  data-testid="final-cta-btn"
                  size="lg"
                  className="bg-orange-600 hover:bg-orange-700 text-white font-bold uppercase tracking-wide h-13 px-10 rounded-lg group"
                >
                  Get Started Free <ArrowRight className="ml-2 w-5 h-5 group-hover:translate-x-1 transition-transform duration-200" />
                </Button>
              </Link>
              <Link to="/register?role=vendor">
                <Button
                  data-testid="final-vendor-btn"
                  size="lg"
                  variant="outline"
                  className="border-slate-700 text-slate-300 hover:bg-white/5 hover:border-slate-500 font-medium h-13 px-8 rounded-lg"
                >
                  Register as Vendor
                </Button>
              </Link>
            </div>
          </motion.div>
        </div>
      </Section>

      {/* ── CONTACT ── */}
      <Section id="contact" className="py-24 md:py-32 border-t border-slate-800/60">
        <div className="max-w-7xl mx-auto px-6">
          <motion.div variants={fadeUp} className="mb-16">
            <p className="text-orange-500 text-xs font-semibold uppercase tracking-[0.2em] mb-3">Get In Touch</p>
            <h2 className="font-heading text-3xl md:text-4xl font-black text-white">Contact Us</h2>
            <p className="text-slate-400 mt-4 max-w-xl text-sm">
              Have questions about OEMLinker? Want to learn how we can help your business? We'd love to hear from you.
            </p>
          </motion.div>

          <div className="grid lg:grid-cols-2 gap-12">
            {/* Contact Form */}
            <motion.div variants={fadeUp} className="bg-slate-900/50 border border-slate-800/60 rounded-2xl p-8">
              <h3 className="font-heading text-lg font-bold text-white mb-6">Send us a Message</h3>
              <form onSubmit={handleContactSubmit} className="space-y-5">
                <div className="grid sm:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="contact-name" className="text-slate-400 text-xs uppercase tracking-wider">Full Name *</Label>
                    <Input
                      id="contact-name"
                      placeholder="John Doe"
                      value={contactForm.name}
                      onChange={(e) => setContactForm(prev => ({ ...prev, name: e.target.value }))}
                      required
                      data-testid="contact-name-input"
                      className="bg-slate-800/50 border-slate-700 text-white placeholder:text-slate-600 focus:border-orange-500 focus:ring-orange-500/20"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="contact-email" className="text-slate-400 text-xs uppercase tracking-wider">Email *</Label>
                    <Input
                      id="contact-email"
                      type="email"
                      placeholder="john@company.com"
                      value={contactForm.email}
                      onChange={(e) => setContactForm(prev => ({ ...prev, email: e.target.value }))}
                      required
                      data-testid="contact-email-input"
                      className="bg-slate-800/50 border-slate-700 text-white placeholder:text-slate-600 focus:border-orange-500 focus:ring-orange-500/20"
                    />
                  </div>
                </div>
                <div className="grid sm:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="contact-phone" className="text-slate-400 text-xs uppercase tracking-wider">Phone</Label>
                    <Input
                      id="contact-phone"
                      placeholder="+91 98765 43210"
                      value={contactForm.phone}
                      onChange={(e) => setContactForm(prev => ({ ...prev, phone: e.target.value }))}
                      data-testid="contact-phone-input"
                      className="bg-slate-800/50 border-slate-700 text-white placeholder:text-slate-600 focus:border-orange-500 focus:ring-orange-500/20"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="contact-company" className="text-slate-400 text-xs uppercase tracking-wider">Company</Label>
                    <Input
                      id="contact-company"
                      placeholder="Your Company Ltd."
                      value={contactForm.company}
                      onChange={(e) => setContactForm(prev => ({ ...prev, company: e.target.value }))}
                      data-testid="contact-company-input"
                      className="bg-slate-800/50 border-slate-700 text-white placeholder:text-slate-600 focus:border-orange-500 focus:ring-orange-500/20"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="contact-message" className="text-slate-400 text-xs uppercase tracking-wider">Message *</Label>
                  <Textarea
                    id="contact-message"
                    placeholder="Tell us about your manufacturing needs..."
                    value={contactForm.message}
                    onChange={(e) => setContactForm(prev => ({ ...prev, message: e.target.value }))}
                    required
                    rows={5}
                    data-testid="contact-message-input"
                    className="bg-slate-800/50 border-slate-700 text-white placeholder:text-slate-600 focus:border-orange-500 focus:ring-orange-500/20 resize-none"
                  />
                </div>
                <Button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full bg-orange-600 hover:bg-orange-700 h-11 font-semibold rounded-lg"
                  data-testid="contact-submit-btn"
                >
                  {isSubmitting ? "Sending..." : <><Send className="w-4 h-4 mr-2" /> Send Message</>}
                </Button>
              </form>
            </motion.div>

            {/* Contact Info */}
            <motion.div variants={fadeUp} className="space-y-6">
              <div>
                <h3 className="font-heading text-lg font-bold text-white mb-2">Contact Information</h3>
                <p className="text-slate-500 text-sm">Our team responds within 24 hours.</p>
              </div>

              {/* Address */}
              <div className="bg-slate-900/80 border border-slate-800/60 rounded-xl p-6">
                <div className="flex items-start gap-4">
                  <div className="w-10 h-10 bg-orange-600 rounded-lg flex items-center justify-center shrink-0">
                    <Building2 className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-white text-sm mb-1">Head Office</h4>
                    <p className="text-slate-400 text-sm leading-relaxed">
                      Simpson & Munro (I) Pvt Ltd<br />
                      6th Floor, 4 Lyons Range<br />
                      Kolkata 700 001, India
                    </p>
                  </div>
                </div>
              </div>

              {/* Email */}
              <div className="bg-slate-900/50 border border-slate-800/60 rounded-xl p-6 hover:border-orange-500/20 transition-colors duration-200">
                <div className="flex items-start gap-4">
                  <div className="w-10 h-10 bg-slate-800 rounded-lg flex items-center justify-center shrink-0">
                    <Mail className="w-5 h-5 text-slate-400" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-white text-sm mb-1">Email Us</h4>
                    <a href="mailto:support@oemlinker.com" className="text-orange-500 hover:text-orange-400 font-medium text-sm">support@oemlinker.com</a>
                  </div>
                </div>
              </div>

              {/* WhatsApp */}
              <div className="bg-slate-900/50 border border-slate-800/60 rounded-xl p-6 hover:border-green-500/20 transition-colors duration-200">
                <div className="flex items-start gap-4">
                  <div className="w-10 h-10 bg-green-600/20 rounded-lg flex items-center justify-center shrink-0">
                    <Phone className="w-5 h-5 text-green-500" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-white text-sm mb-1">WhatsApp</h4>
                    <a href="https://wa.me/919831509919" target="_blank" rel="noopener noreferrer" className="text-green-500 hover:text-green-400 font-medium text-sm">+91-9831509919</a>
                    <p className="text-slate-500 text-xs mt-1">Mon - Fri, 9:00 AM - 6:00 PM IST</p>
                  </div>
                </div>
              </div>

              {/* Map */}
              <div className="rounded-xl overflow-hidden border border-slate-800/60 h-44">
                <iframe
                  src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3684.1234567890123!2d88.34766!3d22.5726!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x3a0277a9fa4a3f0f%3A0x8c2b1c5c5c5c5c5c!2s4%20Lyons%20Range%2C%20Kolkata%2C%20West%20Bengal%20700001!5e0!3m2!1sen!2sin!4v1234567890123"
                  width="100%"
                  height="100%"
                  style={{ border: 0 }}
                  allowFullScreen=""
                  loading="lazy"
                  referrerPolicy="no-referrer-when-downgrade"
                  title="OEMLinker Office Location"
                />
              </div>
            </motion.div>
          </div>
        </div>
      </Section>

      {/* ── FOOTER ── */}
      <footer className="py-12 border-t border-slate-800/60">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid md:grid-cols-4 gap-8 mb-8">
            <div className="md:col-span-2">
              <img src="/logo.png" alt="OEMLinker" style={{ width: '200px', height: '62px' }} className="object-contain mb-4" />
              <p className="text-sm text-slate-500 max-w-md">
                AI-powered manufacturing marketplace connecting OEMs with trusted vendors for precision parts and components.
              </p>
            </div>
            <div>
              <h4 className="font-semibold text-white text-sm mb-4">Quick Links</h4>
              <ul className="space-y-2.5 text-sm">
                <li><Link to="/register" className="text-slate-500 hover:text-orange-400 transition-colors duration-200">Get Started</Link></li>
                <li><Link to="/register?role=vendor" className="text-slate-500 hover:text-orange-400 transition-colors duration-200">Join as Vendor</Link></li>
                <li><a href="#contact" className="text-slate-500 hover:text-orange-400 transition-colors duration-200">Contact Us</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-white text-sm mb-4">Legal</h4>
              <ul className="space-y-2.5 text-sm">
                <li><Link to="/terms-of-service" className="text-slate-500 hover:text-orange-400 transition-colors duration-200">Terms of Service</Link></li>
                <li><Link to="/privacy-policy" className="text-slate-500 hover:text-orange-400 transition-colors duration-200">Privacy Policy</Link></li>
                <li><Link to="/data-deletion" className="text-slate-500 hover:text-orange-400 transition-colors duration-200">Data Deletion</Link></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-slate-800/60 pt-8 flex flex-col md:flex-row items-center justify-between gap-4">
            <p className="text-xs text-slate-600">&copy; 2026 Simpson & Munro (I) Pvt Ltd. All rights reserved.</p>
            <div className="flex items-center gap-4 text-xs">
              <a href="mailto:support@oemlinker.com" className="text-slate-500 hover:text-orange-400 transition-colors duration-200">support@oemlinker.com</a>
              <span className="text-slate-800">|</span>
              <a href="https://wa.me/919831509919" target="_blank" rel="noopener noreferrer" className="text-slate-500 hover:text-green-400 transition-colors duration-200">+91-9831509919</a>
            </div>
          </div>
        </div>
      </footer>

      <ChatbotWidget />
    </div>
  );
};

export default LandingPage;
