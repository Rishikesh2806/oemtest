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
import { Loader2, Save, Building2, Globe, Phone, MapPin, Award, X } from "lucide-react";

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

const VendorProfile = () => {
  const { user, updateUser } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [isNew, setIsNew] = useState(false);

  const [formData, setFormData] = useState({
    company_name: "",
    description: "",
    address: "",
    city: "",
    country: "",
    phone: "",
    website: "",
    certifications: [],
    industries: [],
    materials_handled: []
  });

  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    try {
      const response = await api.get("/vendors/profile");
      setFormData(response.data);
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

  const handleInputChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const toggleArrayItem = (field, item) => {
    setFormData(prev => ({
      ...prev,
      [field]: prev[field].includes(item)
        ? prev[field].filter(i => i !== item)
        : [...prev[field], item]
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.company_name) {
      toast.error("Company name is required");
      return;
    }

    setSaving(true);
    try {
      if (isNew) {
        await api.post("/vendors/profile", formData);
        toast.success("Profile created successfully");
      } else {
        await api.put("/vendors/profile", formData);
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
                  />
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
                  />
                </div>
                <div>
                  <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    <Phone className="w-3 h-3 inline mr-1" /> Phone
                  </Label>
                  <Input
                    value={formData.phone}
                    onChange={(e) => handleInputChange("phone", e.target.value)}
                    placeholder="+1 234 567 8900"
                    className="mt-1"
                  />
                </div>
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
