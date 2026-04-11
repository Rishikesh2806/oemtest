import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../App";
import { Button } from "./ui/button";
import { Menu, X, ArrowRight } from "lucide-react";

const NAV_LINKS = [
  { to: "/#how-it-works", label: "Process" },
  { to: "/#features", label: "Features" },
  { to: "/machines", label: "Capabilities" },
  { to: "/rfqs", label: "RFQs" },
  { to: "/#contact", label: "Contact" },
];

const PublicNav = ({ activePage }) => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-white/95 backdrop-blur-xl border-b border-slate-200 shadow-sm" data-testid="public-nav">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2 flex-shrink-0">
          <img src="/logo.png" alt="OEMLinker" className="object-contain h-10 sm:h-[74px] w-auto max-w-[160px] sm:max-w-[240px]" />
        </Link>

        {/* Desktop nav */}
        <div className="hidden md:flex items-center gap-8 text-sm">
          {NAV_LINKS.map((link) => (
            <Link
              key={link.to}
              to={link.to}
              className={activePage === link.to
                ? "text-orange-600 font-semibold"
                : "text-slate-500 hover:text-orange-600 transition-colors duration-200 font-medium"}
              data-testid={`nav-${link.label.toLowerCase()}-link`}
            >
              {link.label}
            </Link>
          ))}
        </div>

        {/* Desktop auth buttons */}
        <div className="hidden md:flex items-center gap-3">
          {user ? (
            <Link to="/dashboard">
              <Button className="bg-orange-600 hover:bg-orange-700 text-white font-semibold h-9 px-5" data-testid="dashboard-btn">
                Dashboard <ArrowRight className="w-4 h-4 ml-1" />
              </Button>
            </Link>
          ) : (
            <>
              <Link to="/login">
                <Button variant="ghost" className="text-slate-600 hover:text-orange-600 hover:bg-orange-50 h-9 font-medium" data-testid="login-btn">Sign In</Button>
              </Link>
              <Link to="/register">
                <Button className="bg-orange-600 hover:bg-orange-700 text-white font-semibold h-9 px-5" data-testid="get-started-btn">Get Started</Button>
              </Link>
            </>
          )}
        </div>

        {/* Mobile: auth + hamburger */}
        <div className="flex md:hidden items-center gap-2">
          {user ? (
            <Link to="/dashboard">
              <Button size="sm" className="bg-orange-600 hover:bg-orange-700 text-white font-semibold h-8 px-3 text-xs">Dashboard</Button>
            </Link>
          ) : (
            <Link to="/login">
              <Button variant="ghost" size="sm" className="text-slate-600 h-8 px-2 text-xs font-medium">Sign In</Button>
            </Link>
          )}
          <button
            onClick={() => setMobileOpen(!mobileOpen)}
            className="p-2 rounded-lg hover:bg-slate-100 text-slate-700 transition-colors"
            data-testid="mobile-menu-toggle"
            aria-label="Toggle menu"
          >
            {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile dropdown */}
      {mobileOpen && (
        <div className="md:hidden border-t border-slate-100 bg-white shadow-lg animate-in slide-in-from-top-2 duration-200" data-testid="mobile-menu">
          <div className="px-4 py-3 space-y-1">
            {NAV_LINKS.map((link) => (
              <Link
                key={link.to}
                to={link.to}
                onClick={() => setMobileOpen(false)}
                className={`block px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  activePage === link.to
                    ? "bg-orange-50 text-orange-600"
                    : "text-slate-600 hover:bg-slate-50 hover:text-orange-600"
                }`}
                data-testid={`mobile-nav-${link.label.toLowerCase()}-link`}
              >
                {link.label}
              </Link>
            ))}
          </div>
          {!user && (
            <div className="px-4 pb-4 pt-2 border-t border-slate-100 flex gap-2">
              <Button variant="outline" className="flex-1 h-10 text-sm" onClick={() => { setMobileOpen(false); navigate("/login"); }}>Sign In</Button>
              <Button className="flex-1 h-10 text-sm bg-orange-600 hover:bg-orange-700 text-white" onClick={() => { setMobileOpen(false); navigate("/register"); }}>Get Started</Button>
            </div>
          )}
        </div>
      )}
    </nav>
  );
};

export default PublicNav;
