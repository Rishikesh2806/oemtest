import { Link } from "react-router-dom";
import { useAuth } from "../App";
import { Button } from "../components/ui/button";
import { motion } from "framer-motion";
import { 
  Cog, FileText, Users, Zap, Shield, TrendingUp, 
  ArrowRight, CheckCircle2, Factory, Cpu, Target
} from "lucide-react";

const LandingPage = () => {
  const { user } = useAuth();

  const features = [
    {
      icon: <Cpu className="w-6 h-6" />,
      title: "AI Drawing Analysis",
      description: "Upload engineering drawings and let AI extract dimensions, tolerances, and manufacturing requirements automatically."
    },
    {
      icon: <Target className="w-6 h-6" />,
      title: "Smart Vendor Matching",
      description: "Our ML algorithm matches your RFQ with vendors based on machine capabilities, materials, and past performance."
    },
    {
      icon: <FileText className="w-6 h-6" />,
      title: "Streamlined RFQ Process",
      description: "From drawing upload to purchase order in a single workflow. Compare quotes and track orders effortlessly."
    },
    {
      icon: <Shield className="w-6 h-6" />,
      title: "Secure & Compliant",
      description: "NDA protection for drawings, encrypted file storage, and role-based access control for all users."
    },
    {
      icon: <TrendingUp className="w-6 h-6" />,
      title: "Real-time Tracking",
      description: "Monitor production status, delivery updates, and payment milestones from a unified dashboard."
    },
    {
      icon: <Users className="w-6 h-6" />,
      title: "Verified Manufacturers",
      description: "Access a network of vetted manufacturing partners with certified capabilities and quality ratings."
    }
  ];

  const howItWorks = [
    { step: "01", title: "Upload Drawing", description: "Upload your engineering drawings (PDF, CAD, STEP, DWG, DXF)" },
    { step: "02", title: "AI Analysis", description: "Our AI extracts dimensions, tolerances, and manufacturing specs" },
    { step: "03", title: "Vendor Match", description: "Get matched with capable vendors based on your requirements" },
    { step: "04", title: "Compare Quotes", description: "Review and compare quotes from multiple manufacturers" },
    { step: "05", title: "Issue PO", description: "Select the best vendor and issue a purchase order" },
    { step: "06", title: "Track & Receive", description: "Monitor production and receive your precision parts" }
  ];

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 glass border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <img src="/logo.svg" alt="OEMLinker" className="w-[180px] h-[48px]" />
          </Link>
          
          <div className="flex items-center gap-4">
            {user ? (
              <Link to="/dashboard">
                <Button data-testid="dashboard-btn" className="bg-slate-900 hover:bg-slate-800">
                  Dashboard
                </Button>
              </Link>
            ) : (
              <>
                <Link to="/login">
                  <Button data-testid="login-btn" variant="ghost" className="text-slate-600 hover:text-slate-900">
                    Sign In
                  </Button>
                </Link>
                <Link to="/register">
                  <Button data-testid="get-started-btn" className="bg-orange-600 hover:bg-orange-700">
                    Get Started
                  </Button>
                </Link>
              </>
            )}
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative pt-32 pb-24 overflow-hidden">
        <div className="absolute inset-0 tech-grid opacity-50" />
        <div 
          className="absolute inset-0 bg-cover bg-center opacity-5"
          style={{ backgroundImage: `url(https://images.pexels.com/photos/9407363/pexels-photo-9407363.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940)` }}
        />
        
        <div className="relative max-w-7xl mx-auto px-6">
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="max-w-3xl"
          >
            <p className="text-orange-600 font-medium uppercase tracking-wider mb-4">
              AI-Powered Manufacturing Marketplace
            </p>
            <h1 className="font-heading text-5xl md:text-7xl font-black text-slate-900 leading-none tracking-tight mb-6">
              PRECISION<br />
              <span className="text-orange-600">ON DEMAND</span>
            </h1>
            <p className="text-lg md:text-xl text-slate-600 leading-relaxed mb-8 max-w-2xl">
              Connect with verified manufacturers instantly. Upload drawings, get AI-powered analysis, 
              and receive competitive quotes from capable vendors matched to your specifications.
            </p>
            
            <div className="flex flex-wrap gap-4">
              <Link to="/register">
                <Button 
                  data-testid="hero-cta-btn"
                  size="lg" 
                  className="bg-orange-600 hover:bg-orange-700 text-white font-bold uppercase tracking-wide h-14 px-8"
                >
                  Start Free <ArrowRight className="ml-2 w-5 h-5" />
                </Button>
              </Link>
              <Link to="/register?role=vendor">
                <Button 
                  data-testid="vendor-cta-btn"
                  size="lg" 
                  variant="outline"
                  className="border-slate-300 hover:bg-slate-100 font-medium h-14 px-8"
                >
                  Join as Vendor
                </Button>
              </Link>
            </div>
          </motion.div>

          {/* Stats */}
          <motion.div 
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="mt-16 grid grid-cols-2 md:grid-cols-4 gap-8"
          >
            {[
              { value: "500+", label: "Verified Vendors" },
              { value: "10K+", label: "RFQs Processed" },
              { value: "98%", label: "Match Accuracy" },
              { value: "48h", label: "Avg Quote Time" }
            ].map((stat, i) => (
              <div key={i} className="text-center md:text-left">
                <div className="font-heading text-4xl font-black text-slate-900">{stat.value}</div>
                <div className="text-sm text-slate-500 uppercase tracking-wider mt-1">{stat.label}</div>
              </div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-24 bg-white border-y border-slate-200">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <p className="text-orange-600 font-medium uppercase tracking-wider mb-2">Process</p>
            <h2 className="font-heading text-3xl md:text-5xl font-bold text-slate-900">How It Works</h2>
          </div>
          
          <div className="grid md:grid-cols-3 lg:grid-cols-6 gap-8">
            {howItWorks.map((item, i) => (
              <motion.div 
                key={i}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: i * 0.1 }}
                className="text-center"
              >
                <div className="font-heading text-5xl font-black text-slate-100 mb-2">{item.step}</div>
                <h3 className="font-heading font-semibold text-slate-900 mb-2">{item.title}</h3>
                <p className="text-sm text-slate-500">{item.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-24">
        <div className="max-w-7xl mx-auto px-6">
          <div className="mb-16">
            <p className="text-orange-600 font-medium uppercase tracking-wider mb-2">Capabilities</p>
            <h2 className="font-heading text-3xl md:text-5xl font-bold text-slate-900">
              Intelligent Manufacturing Solutions
            </h2>
          </div>
          
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: i * 0.1 }}
                className="bg-white border border-slate-200 p-6 rounded-lg hover:border-orange-500/50 hover:shadow-lg transition-all duration-300 group"
              >
                <div className="w-12 h-12 bg-slate-900 rounded-sm flex items-center justify-center text-white mb-4 group-hover:bg-orange-600 transition-colors">
                  {feature.icon}
                </div>
                <h3 className="font-heading font-semibold text-lg text-slate-900 mb-2">{feature.title}</h3>
                <p className="text-slate-500 text-sm leading-relaxed">{feature.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 bg-slate-900">
        <div className="max-w-7xl mx-auto px-6">
          <div className="max-w-3xl mx-auto text-center">
            <h2 className="font-heading text-3xl md:text-5xl font-bold text-white mb-6">
              Ready to Transform Your Manufacturing Supply Chain?
            </h2>
            <p className="text-slate-400 text-lg mb-8">
              Join thousands of buyers and manufacturers already using OEMLinker to streamline their production workflow.
            </p>
            <div className="flex flex-wrap justify-center gap-4">
              <Link to="/register">
                <Button 
                  size="lg" 
                  className="bg-orange-600 hover:bg-orange-700 text-white font-bold uppercase tracking-wide h-14 px-8"
                >
                  Get Started Free
                </Button>
              </Link>
              <Link to="/register?role=vendor">
                <Button 
                  size="lg" 
                  variant="outline"
                  className="border-slate-600 text-white hover:bg-slate-800 font-medium h-14 px-8"
                >
                  Register as Vendor
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 bg-slate-950 text-slate-400">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <img src="/logo.svg" alt="OEMLinker" className="w-[180px] h-[48px]" />
            </div>
            <p className="text-sm">© 2025 OEMLinker. Precision Manufacturing on Demand.</p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
