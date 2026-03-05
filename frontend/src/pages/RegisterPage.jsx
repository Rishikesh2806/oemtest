import { useState, useMemo, useEffect } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth, api } from "../App";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { toast } from "sonner";
import { 
  Factory, Mail, Lock, User, ArrowRight, Building2, ShoppingCart, 
  Search, Loader2, CheckCircle2, MapPin, Phone, Globe, FileText,
  Shield, Eye, EyeOff, AlertCircle
} from "lucide-react";

// Password strength validation
const validatePassword = (password) => {
  const requirements = [
    { label: "At least 8 characters", met: password.length >= 8 },
    { label: "One uppercase letter", met: /[A-Z]/.test(password) },
    { label: "One lowercase letter", met: /[a-z]/.test(password) },
    { label: "One number", met: /\d/.test(password) },
    { label: "One special character (!@#$%^&*)", met: /[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/`~]/.test(password) }
  ];
  const strength = requirements.filter(r => r.met).length;
  return { requirements, strength, isValid: strength === 5 };
};

const PasswordStrengthIndicator = ({ password }) => {
  const { requirements, strength } = validatePassword(password);
  
  const getStrengthColor = () => {
    if (strength <= 2) return "bg-red-500";
    if (strength <= 3) return "bg-yellow-500";
    if (strength <= 4) return "bg-blue-500";
    return "bg-green-500";
  };
  
  const getStrengthText = () => {
    if (strength <= 2) return "Weak";
    if (strength <= 3) return "Fair";
    if (strength <= 4) return "Good";
    return "Strong";
  };

  if (!password) return null;
  
  return (
    <div className="mt-2 space-y-2">
      <div className="flex items-center gap-2">
        <div className="flex-1 h-2 bg-slate-200 rounded-full overflow-hidden">
          <div 
            className={`h-full transition-all duration-300 ${getStrengthColor()}`}
            style={{ width: `${(strength / 5) * 100}%` }}
          />
        </div>
        <span className={`text-xs font-medium ${strength === 5 ? 'text-green-600' : 'text-slate-500'}`}>
          {getStrengthText()}
        </span>
      </div>
      <div className="grid grid-cols-1 gap-1">
        {requirements.map((req, idx) => (
          <div key={idx} className="flex items-center gap-1.5 text-xs">
            {req.met ? (
              <CheckCircle2 className="w-3 h-3 text-green-500" />
            ) : (
              <AlertCircle className="w-3 h-3 text-slate-300" />
            )}
            <span className={req.met ? "text-green-600" : "text-slate-400"}>
              {req.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

const RegisterPage = () => {
  const [searchParams] = useSearchParams();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [role, setRole] = useState(searchParams.get("role") || "buyer");
  const [loading, setLoading] = useState(false);
  const { register, loginWithGoogle } = useAuth();
  const navigate = useNavigate();
  
  // Password validation
  const passwordValidation = useMemo(() => validatePassword(password), [password]);

  // Vendor-specific fields
  const [gstin, setGstin] = useState("");
  const [gstinVerified, setGstinVerified] = useState(false);
  const [gstinLoading, setGstinLoading] = useState(false);
  const [companyName, setCompanyName] = useState("");
  const [tradeName, setTradeName] = useState("");
  const [address, setAddress] = useState("");
  const [country, setCountry] = useState("India");
  const [city, setCity] = useState("");
  const [state, setState] = useState("");
  const [pincode, setPincode] = useState("");
  const [phone, setPhone] = useState("");
  const [gstinStatus, setGstinStatus] = useState("");
  
  // City suggestions based on country
  const [availableCities, setAvailableCities] = useState([]);
  const [loadingCities, setLoadingCities] = useState(false);
  const [showCitySuggestions, setShowCitySuggestions] = useState(false);
  
  // Country options (India only)
  const COUNTRY_OPTIONS = ["India"];
  
  // Fetch cities when country changes
  useEffect(() => {
    const fetchCities = async () => {
      if (!country || role !== "vendor") return;
      
      setLoadingCities(true);
      try {
        const response = await api.get(`/locations/cities?countries=${encodeURIComponent(country)}`);
        const cityData = response.data[country];
        if (cityData?.cities) {
          setAvailableCities(cityData.cities);
        }
      } catch (error) {
        console.error("Failed to fetch cities:", error);
      } finally {
        setLoadingCities(false);
      }
    };

    fetchCities();
  }, [country, role]);

  const verifyGstin = async () => {
    if (!gstin || gstin.length !== 15) {
      toast.error("Please enter a valid 15-character GSTIN");
      return;
    }

    setGstinLoading(true);
    try {
      const response = await api.get(`/gstin/verify/${gstin}`);
      const data = response.data;

      if (data.valid) {
        setGstinVerified(true);
        setCompanyName(data.legal_name || data.trade_name || "");
        setTradeName(data.trade_name || "");
        setAddress(data.address || "");
        setCity(data.city || "");
        setState(data.state || "");
        setPincode(data.pincode || "");
        setGstinStatus(data.status || "");
        
        // Auto-fill name if empty
        if (!name && data.legal_name) {
          setName(data.legal_name);
        }
        
        toast.success("GSTIN verified successfully!");
      } else {
        setGstinVerified(false);
        toast.error(data.error || "GSTIN verification failed");
      }
    } catch (error) {
      setGstinVerified(false);
      toast.error("Failed to verify GSTIN. Please try again.");
    } finally {
      setGstinLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validate password strength before submission
    if (!passwordValidation.isValid) {
      toast.error("Please ensure your password meets all requirements");
      return;
    }
    
    setLoading(true);

    try {
      // For vendors, include additional fields
      const userData = {
        name,
        email,
        password,
        role,
        ...(role === "vendor" && {
          gstin,
          company_name: companyName,
          trade_name: tradeName,
          address,
          country,
          city,
          state,
          pincode,
          phone
        })
      };

      const user = await register(userData.name, userData.email, userData.password, userData.role, {
        gstin: userData.gstin,
        company_name: userData.company_name,
        trade_name: userData.trade_name,
        address: userData.address,
        country: userData.country,
        city: userData.city,
        state: userData.state,
        pincode: userData.pincode,
        phone: userData.phone
      });
      
      toast.success("Account created successfully!");
      
      if (user.role === "vendor") {
        navigate("/vendor/profile");
      } else {
        navigate("/buyer/dashboard");
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex">
      {/* Left Panel - Image */}
      <div className="hidden lg:block lg:w-1/2 relative">
        <div 
          className="absolute inset-0 bg-cover bg-center"
          style={{ backgroundImage: `url(https://images.pexels.com/photos/32845690/pexels-photo-32845690.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940)` }}
        />
        <div className="absolute inset-0 bg-slate-900/60" />
        <div className="absolute inset-0 flex items-end p-12">
          <div className="text-white">
            <p className="text-orange-400 font-medium uppercase tracking-wider mb-2">Get Started Today</p>
            <h2 className="font-heading text-3xl font-bold mb-4">AI-Powered Manufacturing Matching</h2>
            <p className="text-slate-300">Whether you're sourcing parts or offering manufacturing services, we've got you covered.</p>
          </div>
        </div>
      </div>

      {/* Right Panel - Form */}
      <div className="flex-1 flex items-center justify-center px-6 py-12 overflow-y-auto">
        <div className="w-full max-w-md">
          <Link to="/" className="flex items-center gap-2 mb-8">
            <img src="/logo.png" alt="OEMLinker" className="w-[320px] h-[80px]" />
          </Link>

          <h1 className="font-heading text-3xl font-bold text-slate-900 mb-2">Create your account</h1>
          <p className="text-slate-500 mb-8">Join the manufacturing marketplace</p>

          {/* Role Selection */}
          <div className="grid grid-cols-2 gap-4 mb-8">
            <button
              type="button"
              onClick={() => {
                setRole("buyer");
                setGstinVerified(false);
                setGstin("");
              }}
              className={`p-4 rounded-lg border-2 transition-all ${
                role === "buyer" 
                  ? "border-orange-600 bg-orange-50" 
                  : "border-slate-200 hover:border-slate-300"
              }`}
              data-testid="role-buyer-btn"
            >
              <ShoppingCart className={`w-6 h-6 mx-auto mb-2 ${role === "buyer" ? "text-orange-600" : "text-slate-400"}`} />
              <span className={`block font-medium ${role === "buyer" ? "text-orange-600" : "text-slate-600"}`}>
                I'm a Buyer
              </span>
              <span className="text-xs text-slate-500">Source manufacturing</span>
            </button>
            <button
              type="button"
              onClick={() => setRole("vendor")}
              className={`p-4 rounded-lg border-2 transition-all ${
                role === "vendor" 
                  ? "border-orange-600 bg-orange-50" 
                  : "border-slate-200 hover:border-slate-300"
              }`}
              data-testid="role-vendor-btn"
            >
              <Building2 className={`w-6 h-6 mx-auto mb-2 ${role === "vendor" ? "text-orange-600" : "text-slate-400"}`} />
              <span className={`block font-medium ${role === "vendor" ? "text-orange-600" : "text-slate-600"}`}>
                I'm a Vendor
              </span>
              <span className="text-xs text-slate-500">Offer services</span>
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* GSTIN Verification for Vendors */}
            {role === "vendor" && (
              <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg space-y-4">
                <div className="flex items-center gap-2 text-blue-800">
                  <FileText className="w-5 h-5" />
                  <span className="font-medium">Quick Registration with GSTIN</span>
                </div>
                
                <div>
                  <Label htmlFor="gstin" className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    GSTIN Number
                  </Label>
                  <div className="flex gap-2 mt-1">
                    <div className="relative flex-1">
                      <Input
                        id="gstin"
                        type="text"
                        value={gstin}
                        onChange={(e) => {
                          setGstin(e.target.value.toUpperCase());
                          setGstinVerified(false);
                        }}
                        placeholder="e.g., 27AABCU9603R1ZM"
                        maxLength={15}
                        className={`h-12 bg-white border-slate-200 uppercase ${
                          gstinVerified ? "border-green-500 bg-green-50" : ""
                        }`}
                        data-testid="gstin-input"
                      />
                      {gstinVerified && (
                        <CheckCircle2 className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-green-600" />
                      )}
                    </div>
                    <Button
                      type="button"
                      onClick={verifyGstin}
                      disabled={gstinLoading || gstin.length !== 15}
                      className="bg-blue-600 hover:bg-blue-700"
                    >
                      {gstinLoading ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Search className="w-4 h-4" />
                      )}
                    </Button>
                  </div>
                  <p className="text-xs text-blue-600 mt-1">Enter GSTIN to auto-fill company details</p>
                </div>

                {/* Verified Company Details */}
                {gstinVerified && (
                  <div className="space-y-3 pt-3 border-t border-blue-200">
                    <div className="flex items-center gap-2 text-green-700">
                      <CheckCircle2 className="w-4 h-4" />
                      <span className="text-sm font-medium">GSTIN Verified - {gstinStatus}</span>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <Label className="text-xs text-slate-500">Legal Name</Label>
                        <Input
                          value={companyName}
                          onChange={(e) => setCompanyName(e.target.value)}
                          className="h-10 text-sm"
                        />
                      </div>
                      <div>
                        <Label className="text-xs text-slate-500">Trade Name</Label>
                        <Input
                          value={tradeName}
                          onChange={(e) => setTradeName(e.target.value)}
                          className="h-10 text-sm"
                        />
                      </div>
                      <div className="col-span-2">
                        <Label className="text-xs text-slate-500">Address</Label>
                        <Input
                          value={address}
                          onChange={(e) => setAddress(e.target.value)}
                          className="h-10 text-sm"
                        />
                      </div>
                      <div>
                        <Label className="text-xs text-slate-500">Country</Label>
                        <Select value={country} onValueChange={setCountry}>
                          <SelectTrigger className="h-10 text-sm">
                            <SelectValue placeholder="Select country" />
                          </SelectTrigger>
                          <SelectContent>
                            {COUNTRY_OPTIONS.map((c) => (
                              <SelectItem key={c} value={c}>{c}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="relative">
                        <Label className="text-xs text-slate-500">City</Label>
                        <Input
                          value={city}
                          onChange={(e) => {
                            setCity(e.target.value);
                            setShowCitySuggestions(true);
                          }}
                          onFocus={() => setShowCitySuggestions(true)}
                          onBlur={() => setTimeout(() => setShowCitySuggestions(false), 200)}
                          className="h-10 text-sm"
                          placeholder={loadingCities ? "Loading cities..." : "Type or select city"}
                        />
                        {/* City suggestions dropdown */}
                        {showCitySuggestions && availableCities.length > 0 && (
                          <div className="absolute z-50 w-full mt-1 bg-white border border-slate-200 rounded-md shadow-lg max-h-48 overflow-y-auto">
                            {availableCities
                              .filter(c => !city || c.name.toLowerCase().includes(city.toLowerCase()))
                              .slice(0, 10)
                              .map((cityOption) => (
                                <button
                                  key={cityOption.name}
                                  type="button"
                                  className={`w-full px-3 py-2 text-left text-sm hover:bg-slate-50 flex items-center justify-between ${
                                    cityOption.has_vendors ? "bg-purple-50" : ""
                                  }`}
                                  onMouseDown={(e) => {
                                    e.preventDefault();
                                    setCity(cityOption.name);
                                    setShowCitySuggestions(false);
                                  }}
                                >
                                  <span>{cityOption.name}</span>
                                  {cityOption.has_vendors && (
                                    <span className="text-xs text-purple-600 flex items-center gap-1">
                                      <Building2 className="w-3 h-3" />
                                      {cityOption.vendor_count} vendors
                                    </span>
                                  )}
                                </button>
                              ))}
                          </div>
                        )}
                      </div>
                      <div>
                        <Label className="text-xs text-slate-500">State</Label>
                        <Input
                          value={state}
                          onChange={(e) => setState(e.target.value)}
                          className="h-10 text-sm"
                        />
                      </div>
                      <div>
                        <Label className="text-xs text-slate-500">Pincode</Label>
                        <Input
                          value={pincode}
                          onChange={(e) => setPincode(e.target.value)}
                          className="h-10 text-sm"
                        />
                      </div>
                      <div>
                        <Label className="text-xs text-slate-500">Phone</Label>
                        <Input
                          value={phone}
                          onChange={(e) => setPhone(e.target.value)}
                          placeholder="+91 "
                          className="h-10 text-sm"
                        />
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            <div>
              <Label htmlFor="name" className="text-xs font-bold uppercase tracking-wider text-slate-500">
                {role === "vendor" ? "Contact Person Name" : "Full Name"}
              </Label>
              <div className="relative mt-1">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                <Input
                  id="name"
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder={role === "vendor" ? "Contact person name" : "John Smith"}
                  className="pl-10 h-12 bg-white border-slate-200 focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                  data-testid="register-name-input"
                  required
                />
              </div>
            </div>

            <div>
              <Label htmlFor="email" className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Email Address
              </Label>
              <div className="relative mt-1">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@company.com"
                  className="pl-10 h-12 bg-white border-slate-200 focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                  data-testid="register-email-input"
                  required
                />
              </div>
            </div>

            <div>
              <Label htmlFor="password" className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1">
                <Shield className="w-3 h-3" />
                Password
              </Label>
              <div className="relative mt-1">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Create a strong password"
                  className={`pl-10 pr-10 h-12 bg-white border-slate-200 focus:ring-2 focus:ring-orange-500 focus:border-transparent ${
                    password && !passwordValidation.isValid ? "border-yellow-400" : ""
                  } ${password && passwordValidation.isValid ? "border-green-400" : ""}`}
                  data-testid="register-password-input"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
              <PasswordStrengthIndicator password={password} />
            </div>

            <Button
              type="submit"
              disabled={loading || !passwordValidation.isValid}
              className="w-full h-12 bg-gradient-to-r from-orange-600 to-orange-500 hover:from-orange-700 hover:to-orange-600 text-white font-bold disabled:opacity-50"
              data-testid="register-submit-btn"
            >
              {loading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <>
                  Create Account
                  <ArrowRight className="w-5 h-5 ml-2" />
                </>
              )}
            </Button>
          </form>

          <div className="relative my-8">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-slate-200"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-4 bg-slate-50 text-slate-500">or continue with</span>
            </div>
          </div>

          <Button
            type="button"
            variant="outline"
            onClick={() => loginWithGoogle(role)}
            className="w-full h-12 border-2 hover:bg-slate-50"
            data-testid="google-register-btn"
          >
            <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Continue with Google
          </Button>

          <p className="text-center text-sm text-slate-500 mt-8">
            Already have an account?{" "}
            <Link to="/login" className="text-orange-600 hover:underline font-medium">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default RegisterPage;
