import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth, api } from "../App";
import DashboardLayout from "../components/layout/DashboardLayout";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { toast } from "sonner";
import { Loader2, Save, Building2, Globe, Phone, MapPin, Award, X, Mail, BadgeCheck, FileText, Search } from "lucide-react";
import { usePhoneCheck, PhoneStatusIndicator } from "../components/PhoneCheck";

const INDUSTRIES = [
  "Aerospace", "Automotive", "Medical", "Electronics", 
  "Defense", "Industrial", "Consumer Products", "Energy"
];

const CERTIFICATIONS = [
  "ISO 9001", "ISO 13485", "AS9100", "IATF 16949", 
  "NADCAP", "ISO 14001", "CE Marking"
];

const MATERIALS = [
  "Aluminum", "Steel", "Stainless Steel", "Carbon Steel",
  "Brass", "Copper", "Titanium", "Plastic", "Other"
];

const INDIAN_STATES = [
  "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
  "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand",
  "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
  "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab",
  "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
  "Uttar Pradesh", "Uttarakhand", "West Bengal",
  "Delhi", "Jammu and Kashmir", "Ladakh", "Puducherry"
];

const VendorProfile = () => {
  const { user, updateUser } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [isNew, setIsNew] = useState(false);
  const { phoneStatus, phoneMessage, checkPhone } = usePhoneCheck(user?.user_id);
  
  // Past experiences state
  const [experiences, setExperiences] = useState([]);
  const [showExpForm, setShowExpForm] = useState(false);
  const [expSaving, setExpSaving] = useState(false);
  const [newExperience, setNewExperience] = useState({
    title: "",
    description: "",
    industry: "",
    material: "",
    processes_used: [],
    part_type: "",
    year: new Date().getFullYear()
  });

  const [formData, setFormData] = useState({
    company_name: "",
    description: "",
    address: "",
    city: "",
    state: "",
    pincode: "",
    country: "India",
    phone: "",
    contact_email: "",
    website: "",
    certifications: [],
    industries: [],
    materials_handled: []
  });

  // GST Information
  const [gstInfo, setGstInfo] = useState({
    gstin: "",
    gst_verified: false,
    gst_status: "",
    legal_name: "",
    trade_name: "",
    taxpayer_type: "",
    constitution: "",
    gst_registration_date: ""
  });
  const [gstinInput, setGstinInput] = useState("");
  const [gstVerifying, setGstVerifying] = useState(false);

  useEffect(() => {
    fetchProfile();
    fetchExperiences();
  }, []);

  const fetchProfile = async () => {
    try {
      const response = await api.get("/vendors/profile");
      // Ensure arrays are properly initialized
      setFormData({
        company_name: response.data.company_name || "",
        description: response.data.description || "",
        address: response.data.address || "",
        city: response.data.city || "",
        state: response.data.state || "",
        pincode: response.data.pincode || "",
        country: response.data.country || "India",
        phone: response.data.phone || "",
        contact_email: response.data.contact_email || "",
        website: response.data.website || "",
        certifications: response.data.certifications || [],
        industries: response.data.industries || [],
        materials_handled: response.data.materials_handled || []
      });
      
      // Set GST info if available
      const gst = {
        gstin: response.data.gstin || "",
        gst_verified: response.data.gst_verified || false,
        gst_status: response.data.gst_status || "",
        legal_name: response.data.legal_name || "",
        trade_name: response.data.trade_name || "",
        taxpayer_type: response.data.taxpayer_type || "",
        constitution: response.data.constitution || "",
        gst_registration_date: response.data.gst_registration_date || ""
      };
      setGstInfo(gst);
      setGstinInput(gst.gstin);
    } catch (error) {
      if (error.response?.status === 404) {
        setIsNew(true);
      } else {
        toast.error("Failed to load profile");
      }
    } finally {
      setLoading(false);
    }
  };

  const fetchExperiences = async () => {
    try {
      const response = await api.get("/vendors/experiences");
      setExperiences(response.data.experiences || []);
    } catch (error) {
      console.error("Failed to load experiences:", error);
    }
  };

  const handleAddExperience = async () => {
    if (!newExperience.title) {
      toast.error("Experience title is required");
      return;
    }
    
    setExpSaving(true);
    try {
      // Ensure processes_used is an array before sending
      let processesArray = [];
      if (Array.isArray(newExperience.processes_used)) {
        processesArray = newExperience.processes_used;
      } else if (typeof newExperience.processes_used === 'string' && newExperience.processes_used.trim()) {
        processesArray = newExperience.processes_used.split(",").map(p => p.trim()).filter(p => p);
      }
      
      const experienceData = {
        title: newExperience.title,
        description: newExperience.description || "",
        industry: newExperience.industry || "",
        material: newExperience.material || "",
        processes_used: processesArray,
        part_type: newExperience.part_type || "",
        year: newExperience.year || new Date().getFullYear()
      };
      
      console.log("Sending experience data:", experienceData);
      
      const response = await api.post("/vendors/experiences", experienceData);
      console.log("Experience saved:", response.data);
      
      toast.success("Experience added successfully");
      setShowExpForm(false);
      setNewExperience({
        title: "",
        description: "",
        industry: "",
        material: "",
        processes_used: [],
        part_type: "",
        year: new Date().getFullYear()
      });
      fetchExperiences();
    } catch (error) {
      console.error("Failed to add experience:", error);
      toast.error("Failed to add experience: " + (error.response?.data?.detail || error.message));
    } finally {
      setExpSaving(false);
    }
  };

  const handleDeleteExperience = async (experienceId) => {
    try {
      await api.delete(`/vendors/experiences/${experienceId}`);
      toast.success("Experience deleted");
      fetchExperiences();
    } catch (error) {
      toast.error("Failed to delete experience");
    }
  };

  const handleInputChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const toggleArrayItem = (field, item) => {
    setFormData(prev => {
      const currentArray = prev[field] || [];
      return {
        ...prev,
        [field]: currentArray.includes(item)
          ? currentArray.filter(i => i !== item)
          : [...currentArray, item]
      };
    });
  };

  const verifyGstin = async () => {
    const gstin = gstinInput.toUpperCase().trim();
    if (!gstin || gstin.length !== 15) {
      toast.error("Please enter a valid 15-character GSTIN");
      return;
    }
    setGstVerifying(true);
    try {
      const res = await api.get(`/gstin/verify/${gstin}`);
      const data = res.data;
      if (data.duplicate) {
        toast.error(data.error || "This GSTIN is already registered with another account.");
        return;
      }
      if (data.valid) {
        const verified = {
          gstin: data.gstin,
          gst_verified: true,
          gst_status: data.status || "",
          legal_name: data.legal_name || "",
          trade_name: data.trade_name || "",
          taxpayer_type: data.taxpayer_type || "",
          constitution: data.constitution || "",
          gst_registration_date: data.registration_date || ""
        };
        setGstInfo(verified);
        // Auto-fill address fields from GST data if empty
        setFormData(prev => ({
          ...prev,
          ...(data.city && !prev.city ? { city: data.city } : {}),
          ...(data.state && !prev.state ? { state: data.state } : {}),
          ...(data.pincode && !prev.pincode ? { pincode: data.pincode } : {}),
          ...(data.address && !prev.address ? { address: data.address } : {})
        }));
        toast.success("GSTIN verified successfully!");
      } else {
        toast.error(data.error || "GSTIN verification failed");
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || "GSTIN verification failed");
    } finally {
      setGstVerifying(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.company_name) {
      toast.error("Company name is required");
      return;
    }

    setSaving(true);
    try {
      // Include GST data in the save payload
      const payload = { ...formData };
      if (gstInfo.gstin) {
        payload.gstin = gstInfo.gstin;
        payload.gst_verified = gstInfo.gst_verified;
        payload.gst_status = gstInfo.gst_status;
        payload.legal_name = gstInfo.legal_name;
        payload.trade_name = gstInfo.trade_name;
        payload.taxpayer_type = gstInfo.taxpayer_type;
        payload.constitution = gstInfo.constitution;
        payload.gst_registration_date = gstInfo.gst_registration_date;
      }
      
      if (isNew) {
        await api.post("/vendors/profile", payload);
        toast.success("Profile created successfully");
      } else {
        await api.put("/vendors/profile", payload);
        toast.success("Profile updated successfully");
      }
      
      // Update user context with company name
      updateUser({ ...user, company_name: formData.company_name });
      
      if (isNew) {
        navigate("/vendor/machines");
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to save profile");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-orange-600" />
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="max-w-3xl mx-auto" data-testid="vendor-profile-page">
        <div className="mb-6">
          <h1 className="font-heading text-2xl font-bold text-slate-900">
            {isNew ? "Setup Your Vendor Profile" : "Edit Vendor Profile"}
          </h1>
          <p className="text-slate-500">
            {isNew 
              ? "Complete your company profile to start receiving RFQ matches"
              : "Keep your profile updated to improve matching"
            }
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <Card className="border-slate-200 mb-6">
            <CardHeader>
              <CardTitle className="font-heading text-lg flex items-center gap-2">
                <Building2 className="w-5 h-5 text-orange-600" /> Company Information
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  Company Name *
                </Label>
                <Input
                  value={formData.company_name}
                  onChange={(e) => handleInputChange("company_name", e.target.value)}
                  placeholder="Your Company Name"
                  className="mt-1"
                  data-testid="company-name-input"
                />
              </div>

              <div>
                <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  Description
                </Label>
                <Textarea
                  value={formData.description}
                  onChange={(e) => handleInputChange("description", e.target.value)}
                  placeholder="Describe your company and capabilities..."
                  className="mt-1 min-h-[100px]"
                  data-testid="description-input"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    <MapPin className="w-3 h-3 inline mr-1" /> Address
                  </Label>
                  <Input
                    value={formData.address}
                    onChange={(e) => handleInputChange("address", e.target.value)}
                    placeholder="Street address"
                    className="mt-1"
                    data-testid="address-input"
                  />
                </div>
                <div>
                  <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    City
                  </Label>
                  <Input
                    value={formData.city}
                    onChange={(e) => handleInputChange("city", e.target.value)}
                    placeholder="City"
                    className="mt-1"
                    data-testid="city-input"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    State *
                  </Label>
                  <select
                    value={formData.state}
                    onChange={(e) => handleInputChange("state", e.target.value)}
                    className="mt-1 w-full h-10 px-3 rounded-md border border-slate-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                    data-testid="state-select"
                  >
                    <option value="">Select State</option>
                    {INDIAN_STATES.map((state) => (
                      <option key={state} value={state}>{state}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    Pincode
                  </Label>
                  <Input
                    value={formData.pincode}
                    onChange={(e) => {
                      // Allow only numbers and limit to 6 digits
                      const value = e.target.value.replace(/\D/g, '').slice(0, 6);
                      handleInputChange("pincode", value);
                    }}
                    placeholder="6-digit pincode"
                    className="mt-1"
                    maxLength={6}
                    data-testid="pincode-input"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    <Phone className="w-3 h-3 inline mr-1" /> Phone
                  </Label>
                  <Input
                    value={formData.phone}
                    onChange={(e) => { handleInputChange("phone", e.target.value); checkPhone(e.target.value); }}
                    placeholder="+91 98765 43210"
                    className={`mt-1 ${phoneStatus === "taken" ? "border-red-400" : phoneStatus === "available" ? "border-green-400" : ""}`}
                    data-testid="phone-input"
                  />
                  <PhoneStatusIndicator status={phoneStatus} message={phoneMessage} />
                </div>
                <div>
                  <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    <Mail className="w-3 h-3 inline mr-1" /> Email *
                  </Label>
                  <Input
                    type="email"
                    value={formData.contact_email}
                    onChange={(e) => handleInputChange("contact_email", e.target.value)}
                    placeholder="contact@yourcompany.com"
                    className="mt-1"
                    data-testid="email-input"
                  />
                  <p className="text-xs text-slate-400 mt-1">For RFQ notifications & updates</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    Country
                  </Label>
                  <Input
                    value={formData.country}
                    onChange={(e) => handleInputChange("country", e.target.value)}
                    placeholder="Country"
                    className="mt-1"
                    data-testid="country-input"
                  />
                </div>
                <div>
                  <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    <Globe className="w-3 h-3 inline mr-1" /> Website
                  </Label>
                  <Input
                    value={formData.website}
                    onChange={(e) => handleInputChange("website", e.target.value)}
                    placeholder="https://www.yourcompany.com"
                    className="mt-1"
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* GST Information Card */}
          <Card className={`border-slate-200 mb-6 ${gstInfo.gst_verified ? 'bg-gradient-to-r from-green-50 to-emerald-50' : ''}`} data-testid="gst-info-card">
            <CardHeader>
              <CardTitle className="font-heading text-lg flex items-center gap-2">
                <FileText className={`w-5 h-5 ${gstInfo.gst_verified ? 'text-green-600' : 'text-orange-600'}`} /> GST Information
                {gstInfo.gst_verified && (
                  <span className="ml-2 inline-flex items-center gap-1 text-xs font-medium text-green-700 bg-green-100 px-2 py-1 rounded-full">
                    <BadgeCheck className="w-3 h-3" /> Verified
                  </span>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* GSTIN Input + Verify */}
              <div>
                <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  GSTIN Number
                </Label>
                <div className="flex gap-2 mt-1">
                  <Input
                    data-testid="gstin-input"
                    value={gstinInput}
                    onChange={(e) => setGstinInput(e.target.value.toUpperCase())}
                    placeholder="e.g. 22AAAAA0000A1Z5"
                    maxLength={15}
                    className="font-mono uppercase"
                    disabled={gstInfo.gst_verified}
                  />
                  <Button
                    type="button"
                    data-testid="gstin-verify-btn"
                    onClick={verifyGstin}
                    disabled={gstVerifying || gstInfo.gst_verified || gstinInput.length !== 15}
                    variant={gstInfo.gst_verified ? "outline" : "default"}
                    className={gstInfo.gst_verified ? "text-green-600 border-green-200" : "bg-orange-600 hover:bg-orange-700"}
                  >
                    {gstVerifying ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : gstInfo.gst_verified ? (
                      <><BadgeCheck className="w-4 h-4 mr-1" /> Verified</>
                    ) : (
                      <><Search className="w-4 h-4 mr-1" /> Verify</>
                    )}
                  </Button>
                  {gstInfo.gst_verified && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="text-slate-400 hover:text-red-500"
                      onClick={() => {
                        setGstInfo({ gstin: "", gst_verified: false, gst_status: "", legal_name: "", trade_name: "", taxpayer_type: "", constitution: "", gst_registration_date: "" });
                        setGstinInput("");
                      }}
                      data-testid="gstin-clear-btn"
                    >
                      <X className="w-4 h-4" />
                    </Button>
                  )}
                </div>
                {gstinInput && gstinInput.length !== 15 && (
                  <p className="text-xs text-amber-600 mt-1">{gstinInput.length}/15 characters</p>
                )}
              </div>

              {/* Verified GST Details */}
              {gstInfo.gst_verified && (
                <div className="grid grid-cols-2 gap-4 pt-2 border-t border-green-200">
                  <div>
                    <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">GSTIN</Label>
                    <p className="mt-1 text-slate-800 font-mono text-sm bg-white px-3 py-2 rounded border" data-testid="gstin-display">
                      {gstInfo.gstin}
                    </p>
                  </div>
                  <div>
                    <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">GST Status</Label>
                    <p className="mt-1 text-slate-800 text-sm bg-white px-3 py-2 rounded border">
                      <span className={`inline-flex items-center gap-1 ${gstInfo.gst_status === 'Active' ? 'text-green-600' : 'text-amber-600'}`}>
                        {gstInfo.gst_status || 'N/A'}
                      </span>
                    </p>
                  </div>
                  {gstInfo.legal_name && (
                    <div>
                      <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">Legal Name</Label>
                      <p className="mt-1 text-slate-800 text-sm bg-white px-3 py-2 rounded border">{gstInfo.legal_name}</p>
                    </div>
                  )}
                  {gstInfo.trade_name && (
                    <div>
                      <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">Trade Name</Label>
                      <p className="mt-1 text-slate-800 text-sm bg-white px-3 py-2 rounded border">{gstInfo.trade_name}</p>
                    </div>
                  )}
                  {gstInfo.taxpayer_type && (
                    <div>
                      <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">Taxpayer Type</Label>
                      <p className="mt-1 text-slate-800 text-sm bg-white px-3 py-2 rounded border">{gstInfo.taxpayer_type}</p>
                    </div>
                  )}
                  {gstInfo.constitution && (
                    <div>
                      <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">Constitution</Label>
                      <p className="mt-1 text-slate-800 text-sm bg-white px-3 py-2 rounded border">{gstInfo.constitution}</p>
                    </div>
                  )}
                  {gstInfo.gst_registration_date && (
                    <div className="col-span-2">
                      <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">GST Registration Date</Label>
                      <p className="mt-1 text-slate-800 text-sm bg-white px-3 py-2 rounded border">{gstInfo.gst_registration_date}</p>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="border-slate-200 mb-6">
            <CardHeader>
              <CardTitle className="font-heading text-lg flex items-center gap-2">
                <Award className="w-5 h-5 text-orange-600" /> Certifications
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {CERTIFICATIONS.map((cert) => (
                  <button
                    key={cert}
                    type="button"
                    onClick={() => toggleArrayItem("certifications", cert)}
                    className={`px-3 py-1.5 rounded-sm text-sm font-medium transition-colors ${
                      formData.certifications.includes(cert)
                        ? "bg-orange-600 text-white"
                        : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                    }`}
                    data-testid={`cert-${cert}`}
                  >
                    {cert}
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-200 mb-6">
            <CardHeader>
              <CardTitle className="font-heading text-lg">Industries Served</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {INDUSTRIES.map((industry) => (
                  <button
                    key={industry}
                    type="button"
                    onClick={() => toggleArrayItem("industries", industry)}
                    className={`px-3 py-1.5 rounded-sm text-sm font-medium transition-colors ${
                      formData.industries.includes(industry)
                        ? "bg-slate-900 text-white"
                        : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                    }`}
                    data-testid={`industry-${industry}`}
                  >
                    {industry}
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-200 mb-6">
            <CardHeader>
              <CardTitle className="font-heading text-lg">Materials Handled</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {MATERIALS.map((material) => (
                  <button
                    key={material}
                    type="button"
                    onClick={() => toggleArrayItem("materials_handled", material)}
                    className={`px-3 py-1.5 rounded-sm text-sm font-medium transition-colors ${
                      formData.materials_handled.includes(material)
                        ? "bg-slate-900 text-white"
                        : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                    }`}
                    data-testid={`material-${material}`}
                  >
                    {material}
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Past Experiences Section */}
          <Card className="border-slate-200 mb-6">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="font-heading text-lg">Past Experiences</CardTitle>
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => setShowExpForm(!showExpForm)}
                className="text-sm"
              >
                {showExpForm ? "Cancel" : "+ Add Experience"}
              </Button>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-slate-500 mb-4">
                Add your past manufacturing projects to improve RFQ matching accuracy. Include details about similar parts you've made.
              </p>
              
              {/* Add Experience Form */}
              {showExpForm && (
                <div className="bg-slate-50 p-4 rounded-lg mb-4 space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <Label className="text-sm">Project Title *</Label>
                      <Input
                        value={newExperience.title}
                        onChange={(e) => setNewExperience({...newExperience, title: e.target.value})}
                        placeholder="e.g., CNC Machined Shaft for Automotive"
                        className="mt-1"
                      />
                    </div>
                    <div>
                      <Label className="text-sm">Part Type</Label>
                      <Input
                        value={newExperience.part_type}
                        onChange={(e) => setNewExperience({...newExperience, part_type: e.target.value})}
                        placeholder="e.g., shaft, housing, bracket"
                        className="mt-1"
                      />
                    </div>
                    <div>
                      <Label className="text-sm">Industry</Label>
                      <Input
                        value={newExperience.industry}
                        onChange={(e) => setNewExperience({...newExperience, industry: e.target.value})}
                        placeholder="e.g., Automotive, Aerospace"
                        className="mt-1"
                      />
                    </div>
                    <div>
                      <Label className="text-sm">Material</Label>
                      <Input
                        value={newExperience.material}
                        onChange={(e) => setNewExperience({...newExperience, material: e.target.value})}
                        placeholder="e.g., Steel, Aluminum"
                        className="mt-1"
                      />
                    </div>
                    <div>
                      <Label className="text-sm">Processes Used</Label>
                      <Input
                        value={Array.isArray(newExperience.processes_used) ? newExperience.processes_used.join(", ") : newExperience.processes_used}
                        onChange={(e) => {
                          // Store as string while typing, parse to array on blur
                          setNewExperience({
                            ...newExperience, 
                            processes_used: e.target.value
                          });
                        }}
                        onBlur={(e) => {
                          // Convert to array when user finishes typing
                          const processes = e.target.value.split(",").map(p => p.trim()).filter(p => p);
                          setNewExperience({
                            ...newExperience,
                            processes_used: processes
                          });
                        }}
                        placeholder="e.g., CNC Turning, Milling, Grinding"
                        className="mt-1"
                      />
                      <p className="text-xs text-slate-400 mt-1">Separate processes with commas</p>
                    </div>
                    <div>
                      <Label className="text-sm">Year</Label>
                      <Input
                        type="number"
                        value={newExperience.year}
                        onChange={(e) => setNewExperience({...newExperience, year: parseInt(e.target.value)})}
                        className="mt-1"
                      />
                    </div>
                  </div>
                  <div>
                    <Label className="text-sm">Description</Label>
                    <Textarea
                      value={newExperience.description}
                      onChange={(e) => setNewExperience({...newExperience, description: e.target.value})}
                      placeholder="Brief description of the project, quantities, tolerances achieved, etc."
                      className="mt-1"
                      rows={2}
                    />
                  </div>
                  <Button
                    type="button"
                    onClick={handleAddExperience}
                    disabled={expSaving}
                    className="bg-green-600 hover:bg-green-700"
                  >
                    {expSaving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                    Save Experience
                  </Button>
                </div>
              )}
              
              {/* Experience List */}
              {experiences.length === 0 ? (
                <p className="text-slate-400 text-sm italic">No past experiences added yet. Add your project history to improve matching.</p>
              ) : (
                <div className="space-y-3">
                  {experiences.map((exp) => (
                    <div key={exp.experience_id} className="bg-white border border-slate-200 rounded-lg p-4">
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <h4 className="font-medium text-slate-900">{exp.title}</h4>
                          {exp.description && (
                            <p className="text-sm text-slate-600 mt-1">{exp.description}</p>
                          )}
                          <div className="flex flex-wrap gap-2 mt-2">
                            {exp.industry && (
                              <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">{exp.industry}</span>
                            )}
                            {exp.material && (
                              <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">{exp.material}</span>
                            )}
                            {exp.part_type && (
                              <span className="text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded">{exp.part_type}</span>
                            )}
                            {exp.year && (
                              <span className="text-xs bg-slate-100 text-slate-600 px-2 py-1 rounded">{exp.year}</span>
                            )}
                            {exp.processes_used?.map((proc, i) => (
                              <span key={i} className="text-xs bg-orange-100 text-orange-700 px-2 py-1 rounded">{proc}</span>
                            ))}
                          </div>
                        </div>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDeleteExperience(exp.experience_id)}
                          className="text-red-500 hover:text-red-700 hover:bg-red-50"
                        >
                          <X className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <div className="flex justify-end gap-4">
            <Button 
              type="button" 
              variant="outline"
              onClick={() => navigate("/vendor/dashboard")}
            >
              Cancel
            </Button>
            <Button 
              type="submit"
              disabled={saving}
              className="bg-orange-600 hover:bg-orange-700"
              data-testid="save-profile-btn"
            >
              {saving ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <><Save className="w-4 h-4 mr-2" /> {isNew ? "Create Profile" : "Save Changes"}</>
              )}
            </Button>
          </div>
        </form>
      </div>
    </DashboardLayout>
  );
};

export default VendorProfile;
