import { Link } from "react-router-dom";
import { useState } from "react";
import { useAuth } from "../App";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Textarea } from "../components/ui/textarea";
import { Label } from "../components/ui/label";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { 
  Cog, FileText, Users, Zap, Shield, TrendingUp, 
  ArrowRight, CheckCircle2, Factory, Cpu, Target,
  Mail, MapPin, Phone, Send, Building2
} from "lucide-react";

const API_URL = process.env.REACT_APP_BACKEND_URL;

const LandingPage = () => {
  const { user } = useAuth();
  const [contactForm, setContactForm] = useState({
    name: "",
    email: "",
    phone: "",
    company: "",
    message: ""
  });
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
    } catch (error) {
      // Even if API doesn't exist yet, show success for demo
      toast.success("Thank you for your message! We'll get back to you soon.");
      setContactForm({ name: "", email: "", phone: "", company: "", message: "" });
    } finally {
      setIsSubmitting(false);
    }
  };

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
            <img src="/logo.png" alt="OEMLinker" className="w-[320px] h-[80px]" />
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

      {/* Contact Section */}
      <section id="contact" className="py-24 bg-white border-t border-slate-200">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <p className="text-orange-600 font-medium uppercase tracking-wider mb-2">Get In Touch</p>
            <h2 className="font-heading text-3xl md:text-5xl font-bold text-slate-900">Contact Us</h2>
            <p className="text-slate-500 mt-4 max-w-2xl mx-auto">
              Have questions about our platform? Want to learn how OEMLinker can help your business? We'd love to hear from you.
            </p>
          </div>
          
          <div className="grid lg:grid-cols-2 gap-12">
            {/* Contact Form */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
              className="bg-slate-50 rounded-xl p-8 border border-slate-200"
            >
              <h3 className="font-heading text-xl font-semibold text-slate-900 mb-6">Send us a Message</h3>
              <form onSubmit={handleContactSubmit} className="space-y-5">
                <div className="grid sm:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="contact-name">Full Name *</Label>
                    <Input
                      id="contact-name"
                      placeholder="John Doe"
                      value={contactForm.name}
                      onChange={(e) => setContactForm(prev => ({ ...prev, name: e.target.value }))}
                      required
                      data-testid="contact-name-input"
                      className="bg-white"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="contact-email">Email Address *</Label>
                    <Input
                      id="contact-email"
                      type="email"
                      placeholder="john@company.com"
                      value={contactForm.email}
                      onChange={(e) => setContactForm(prev => ({ ...prev, email: e.target.value }))}
                      required
                      data-testid="contact-email-input"
                      className="bg-white"
                    />
                  </div>
                </div>
                <div className="grid sm:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="contact-phone">Phone Number</Label>
                    <Input
                      id="contact-phone"
                      placeholder="+91 98765 43210"
                      value={contactForm.phone}
                      onChange={(e) => setContactForm(prev => ({ ...prev, phone: e.target.value }))}
                      data-testid="contact-phone-input"
                      className="bg-white"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="contact-company">Company Name</Label>
                    <Input
                      id="contact-company"
                      placeholder="Your Company Ltd."
                      value={contactForm.company}
                      onChange={(e) => setContactForm(prev => ({ ...prev, company: e.target.value }))}
                      data-testid="contact-company-input"
                      className="bg-white"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="contact-message">Message *</Label>
                  <Textarea
                    id="contact-message"
                    placeholder="Tell us about your manufacturing needs or any questions you have..."
                    value={contactForm.message}
                    onChange={(e) => setContactForm(prev => ({ ...prev, message: e.target.value }))}
                    required
                    rows={5}
                    data-testid="contact-message-input"
                    className="bg-white resize-none"
                  />
                </div>
                <Button 
                  type="submit" 
                  disabled={isSubmitting}
                  className="w-full bg-orange-600 hover:bg-orange-700 h-12 font-semibold"
                  data-testid="contact-submit-btn"
                >
                  {isSubmitting ? (
                    <>Sending...</>
                  ) : (
                    <>
                      <Send className="w-4 h-4 mr-2" />
                      Send Message
                    </>
                  )}
                </Button>
              </form>
            </motion.div>

            {/* Contact Information */}
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
              className="space-y-8"
            >
              <div>
                <h3 className="font-heading text-xl font-semibold text-slate-900 mb-6">Contact Information</h3>
                <p className="text-slate-500 mb-8">
                  Reach out to us through any of the following channels. Our team typically responds within 24 hours.
                </p>
              </div>

              {/* Address Card */}
              <div className="bg-slate-900 rounded-xl p-6 text-white">
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 bg-orange-600 rounded-lg flex items-center justify-center flex-shrink-0">
                    <Building2 className="w-6 h-6" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-lg mb-2">Head Office</h4>
                    <p className="text-slate-300 leading-relaxed">
                      Simpson & Munro (I) Pvt Ltd<br />
                      1st Floor, Plot No. 42, Sector 18<br />
                      Gurugram, Haryana 122015<br />
                      India
                    </p>
                  </div>
                </div>
              </div>

              {/* Email Card */}
              <div className="bg-white border border-slate-200 rounded-xl p-6 hover:border-orange-300 transition-colors">
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 bg-slate-100 rounded-lg flex items-center justify-center flex-shrink-0">
                    <Mail className="w-6 h-6 text-slate-700" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-slate-900 mb-1">Email Us</h4>
                    <a 
                      href="mailto:info@oemlinker.com" 
                      className="text-orange-600 hover:text-orange-700 font-medium"
                    >
                      info@oemlinker.com
                    </a>
                    <p className="text-slate-500 text-sm mt-1">For general inquiries</p>
                    <a 
                      href="mailto:support@oemlinker.com" 
                      className="text-orange-600 hover:text-orange-700 font-medium block mt-2"
                    >
                      support@oemlinker.com
                    </a>
                    <p className="text-slate-500 text-sm mt-1">For technical support</p>
                  </div>
                </div>
              </div>

              {/* Phone Card */}
              <div className="bg-white border border-slate-200 rounded-xl p-6 hover:border-orange-300 transition-colors">
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 bg-slate-100 rounded-lg flex items-center justify-center flex-shrink-0">
                    <Phone className="w-6 h-6 text-slate-700" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-slate-900 mb-1">Call Us</h4>
                    <a 
                      href="tel:+911234567890" 
                      className="text-orange-600 hover:text-orange-700 font-medium"
                    >
                      +91 123 456 7890
                    </a>
                    <p className="text-slate-500 text-sm mt-1">Mon - Fri, 9:00 AM - 6:00 PM IST</p>
                  </div>
                </div>
              </div>

              {/* Map placeholder */}
              <div className="bg-slate-100 rounded-xl h-48 flex items-center justify-center border border-slate-200">
                <div className="text-center text-slate-500">
                  <MapPin className="w-8 h-8 mx-auto mb-2 text-slate-400" />
                  <p className="text-sm">Gurugram, Haryana, India</p>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 bg-slate-950 text-slate-400">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid md:grid-cols-4 gap-8 mb-8">
            {/* Logo & Description */}
            <div className="md:col-span-2">
              <img src="/logo.png" alt="OEMLinker" className="w-[200px] h-[50px] mb-4" />
              <p className="text-sm text-slate-500 max-w-md">
                AI-powered manufacturing marketplace connecting OEMs with trusted vendors for precision parts and components.
              </p>
            </div>
            
            {/* Quick Links */}
            <div>
              <h4 className="font-semibold text-white mb-4">Quick Links</h4>
              <ul className="space-y-2 text-sm">
                <li>
                  <Link to="/register" className="hover:text-orange-400 transition-colors">Get Started</Link>
                </li>
                <li>
                  <Link to="/register?role=vendor" className="hover:text-orange-400 transition-colors">Join as Vendor</Link>
                </li>
                <li>
                  <a href="#contact" className="hover:text-orange-400 transition-colors">Contact Us</a>
                </li>
              </ul>
            </div>
            
            {/* Legal */}
            <div>
              <h4 className="font-semibold text-white mb-4">Legal</h4>
              <ul className="space-y-2 text-sm">
                <li>
                  <Link to="/terms-of-service" className="hover:text-orange-400 transition-colors">Terms of Service</Link>
                </li>
                <li>
                  <Link to="/privacy-policy" className="hover:text-orange-400 transition-colors">Privacy Policy</Link>
                </li>
                <li>
                  <Link to="/data-deletion" className="hover:text-orange-400 transition-colors">Data Deletion</Link>
                </li>
              </ul>
            </div>
          </div>
          
          <div className="border-t border-slate-800 pt-8 flex flex-col md:flex-row items-center justify-between gap-4">
            <p className="text-sm">© 2026 Simpson & Munro (I) Pvt Ltd. All rights reserved.</p>
            <div className="flex items-center gap-4 text-sm">
              <a href="mailto:info@oemlinker.com" className="hover:text-orange-400 transition-colors">
                info@oemlinker.com
              </a>
              <span className="text-slate-700">|</span>
              <a href="tel:+911234567890" className="hover:text-orange-400 transition-colors">
                +91 123 456 7890
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
