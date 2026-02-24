import { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useAuth, api } from "../App";
import DashboardLayout from "../components/layout/DashboardLayout";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { toast } from "sonner";
import { 
  Building2, MapPin, Phone, Globe, Mail, Award, Star,
  Wrench, Package, CheckCircle2, ArrowLeft, Loader2,
  MessageSquare, ExternalLink, Briefcase, TrendingUp
} from "lucide-react";

const VendorProfileView = () => {
  const { vendorId } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [vendor, setVendor] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchVendor();
  }, [vendorId]);

  const fetchVendor = async () => {
    try {
      const response = await api.get(`/vendors/${vendorId}/full`);
      setVendor(response.data);
    } catch (error) {
      toast.error("Failed to load vendor profile");
    } finally {
      setLoading(false);
    }
  };

  const startChat = () => {
    navigate(`/chat?with=${vendor.user_id}`);
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

  if (!vendor) {
    return (
      <DashboardLayout>
        <div className="text-center py-12">
          <Building2 className="w-16 h-16 text-slate-300 mx-auto mb-4" />
          <p className="text-slate-500">Vendor not found</p>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="max-w-5xl mx-auto space-y-6" data-testid="vendor-profile-view">
        {/* Back Button */}
        <Button 
          variant="ghost" 
          onClick={() => navigate(-1)}
          className="text-slate-600"
        >
          <ArrowLeft className="w-4 h-4 mr-2" /> Back
        </Button>

        {/* Header Card */}
        <Card className="border-slate-200 overflow-hidden">
          <div className="bg-gradient-to-r from-slate-900 to-slate-800 px-6 py-8">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-4">
                <div className="w-20 h-20 bg-white rounded-lg flex items-center justify-center">
                  <Building2 className="w-10 h-10 text-slate-700" />
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-white">{vendor.company_name}</h1>
                  <div className="flex items-center gap-4 mt-2">
                    <span className="flex items-center gap-1 text-slate-300">
                      <MapPin className="w-4 h-4" />
                      {vendor.city}, {vendor.country}
                    </span>
                    <span className="flex items-center gap-1 text-amber-400">
                      <Star className="w-4 h-4 fill-current" />
                      {vendor.rating?.toFixed(1) || "N/A"}
                    </span>
                  </div>
                  {vendor.is_approved && (
                    <span className="inline-flex items-center gap-1 mt-2 px-2 py-1 bg-green-500/20 text-green-400 text-xs rounded">
                      <CheckCircle2 className="w-3 h-3" /> Verified Vendor
                    </span>
                  )}
                </div>
              </div>
              
              {user?.role === "buyer" && (
                <div className="flex gap-3">
                  <Button 
                    onClick={startChat}
                    className="bg-orange-600 hover:bg-orange-700"
                    data-testid="chat-vendor-btn"
                  >
                    <MessageSquare className="w-4 h-4 mr-2" /> Chat
                  </Button>
                </div>
              )}
            </div>
          </div>
          
          {/* Quick Stats */}
          <div className="grid grid-cols-4 divide-x divide-slate-200 bg-slate-50">
            <div className="p-4 text-center">
              <p className="text-2xl font-bold text-slate-900">{vendor.total_jobs || 0}</p>
              <p className="text-xs text-slate-500 uppercase">Jobs Completed</p>
            </div>
            <div className="p-4 text-center">
              <p className="text-2xl font-bold text-slate-900">{vendor.stats?.total_quotes || 0}</p>
              <p className="text-xs text-slate-500 uppercase">Quotes Sent</p>
            </div>
            <div className="p-4 text-center">
              <p className="text-2xl font-bold text-slate-900">{vendor.stats?.acceptance_rate || 0}%</p>
              <p className="text-xs text-slate-500 uppercase">Win Rate</p>
            </div>
            <div className="p-4 text-center">
              <p className="text-2xl font-bold text-slate-900">{vendor.machines?.length || 0}</p>
              <p className="text-xs text-slate-500 uppercase">Machines</p>
            </div>
          </div>
        </Card>

        <div className="grid md:grid-cols-3 gap-6">
          {/* Left Column - Contact & About */}
          <div className="space-y-6">
            {/* Contact Information */}
            <Card className="border-slate-200">
              <CardHeader>
                <CardTitle className="font-heading text-lg">Contact Information</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {vendor.contact?.email && (
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-slate-100 rounded-lg flex items-center justify-center">
                      <Mail className="w-5 h-5 text-slate-500" />
                    </div>
                    <div>
                      <p className="text-xs text-slate-500 uppercase">Email</p>
                      <a 
                        href={`mailto:${vendor.contact.email}`} 
                        className="text-orange-600 hover:underline"
                        data-testid="vendor-email"
                      >
                        {vendor.contact.email}
                      </a>
                    </div>
                  </div>
                )}
                
                {vendor.contact?.phone && (
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-slate-100 rounded-lg flex items-center justify-center">
                      <Phone className="w-5 h-5 text-slate-500" />
                    </div>
                    <div>
                      <p className="text-xs text-slate-500 uppercase">Phone</p>
                      <a 
                        href={`tel:${vendor.contact.phone}`}
                        className="text-slate-900 font-medium"
                        data-testid="vendor-phone"
                      >
                        {vendor.contact.phone}
                      </a>
                    </div>
                  </div>
                )}
                
                {vendor.contact?.website && (
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-slate-100 rounded-lg flex items-center justify-center">
                      <Globe className="w-5 h-5 text-slate-500" />
                    </div>
                    <div>
                      <p className="text-xs text-slate-500 uppercase">Website</p>
                      <a 
                        href={vendor.contact.website}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-orange-600 hover:underline flex items-center gap-1"
                        data-testid="vendor-website"
                      >
                        Visit Website <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                  </div>
                )}

                {vendor.address && (
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-slate-100 rounded-lg flex items-center justify-center">
                      <MapPin className="w-5 h-5 text-slate-500" />
                    </div>
                    <div>
                      <p className="text-xs text-slate-500 uppercase">Address</p>
                      <p className="text-slate-900">
                        {vendor.address}, {vendor.city}, {vendor.country}
                      </p>
                    </div>
                  </div>
                )}

                {user?.role === "buyer" && (
                  <Button 
                    onClick={startChat}
                    className="w-full mt-4 bg-slate-900 hover:bg-slate-800"
                  >
                    <MessageSquare className="w-4 h-4 mr-2" /> Send Message
                  </Button>
                )}
              </CardContent>
            </Card>

            {/* Certifications */}
            {vendor.certifications?.length > 0 && (
              <Card className="border-slate-200">
                <CardHeader>
                  <CardTitle className="font-heading text-lg flex items-center gap-2">
                    <Award className="w-5 h-5 text-orange-600" /> Certifications
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2">
                    {vendor.certifications.map((cert, i) => (
                      <span 
                        key={i}
                        className="px-3 py-1.5 bg-purple-100 text-purple-700 rounded-sm text-sm font-medium"
                      >
                        {cert}
                      </span>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Right Column - Machines & Capabilities */}
          <div className="md:col-span-2 space-y-6">
            {/* Description */}
            {vendor.description && (
              <Card className="border-slate-200">
                <CardHeader>
                  <CardTitle className="font-heading text-lg">About</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-slate-600 leading-relaxed">{vendor.description}</p>
                </CardContent>
              </Card>
            )}

            {/* Industries */}
            {vendor.industries?.length > 0 && (
              <Card className="border-slate-200">
                <CardHeader>
                  <CardTitle className="font-heading text-lg flex items-center gap-2">
                    <Briefcase className="w-5 h-5 text-orange-600" /> Industries Served
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2">
                    {vendor.industries.map((ind, i) => (
                      <span 
                        key={i}
                        className="px-3 py-1.5 bg-slate-100 text-slate-700 rounded-sm text-sm font-medium"
                      >
                        {ind}
                      </span>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Materials */}
            {vendor.materials_handled?.length > 0 && (
              <Card className="border-slate-200">
                <CardHeader>
                  <CardTitle className="font-heading text-lg">Materials Handled</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2">
                    {vendor.materials_handled.map((mat, i) => (
                      <span 
                        key={i}
                        className="px-3 py-1.5 bg-blue-100 text-blue-700 rounded-sm text-sm font-medium"
                      >
                        {mat}
                      </span>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Machines */}
            {vendor.machines?.length > 0 && (
              <Card className="border-slate-200">
                <CardHeader>
                  <CardTitle className="font-heading text-lg flex items-center gap-2">
                    <Wrench className="w-5 h-5 text-orange-600" /> Manufacturing Equipment
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid gap-4">
                    {vendor.machines.map((machine) => (
                      <div 
                        key={machine.machine_id}
                        className="p-4 bg-slate-50 rounded-lg border border-slate-200"
                      >
                        <div className="flex items-start justify-between">
                          <div>
                            <p className="font-semibold text-slate-900">{machine.machine_type}</p>
                            <p className="text-sm text-slate-500">
                              {machine.brand} {machine.model}
                            </p>
                          </div>
                          {machine.axis_config && (
                            <span className="px-2 py-1 bg-slate-200 text-slate-700 text-xs rounded">
                              {machine.axis_config}
                            </span>
                          )}
                        </div>
                        
                        <div className="mt-3 grid grid-cols-2 gap-4 text-sm">
                          {(machine.max_x || machine.max_y || machine.max_z) && (
                            <div>
                              <p className="text-xs text-slate-500 uppercase">Work Envelope</p>
                              <p className="font-mono text-slate-700">
                                {machine.max_x || "-"} × {machine.max_y || "-"} × {machine.max_z || "-"} mm
                              </p>
                            </div>
                          )}
                          {machine.max_diameter && (
                            <div>
                              <p className="text-xs text-slate-500 uppercase">Max Diameter</p>
                              <p className="font-mono text-slate-700">Ø{machine.max_diameter} mm</p>
                            </div>
                          )}
                          <div>
                            <p className="text-xs text-slate-500 uppercase">Tolerance</p>
                            <p className="font-mono text-slate-700">±{machine.tolerance_capability} mm</p>
                          </div>
                          {machine.materials_supported?.length > 0 && (
                            <div className="col-span-2">
                              <p className="text-xs text-slate-500 uppercase mb-1">Materials</p>
                              <div className="flex flex-wrap gap-1">
                                {machine.materials_supported.map((m, i) => (
                                  <span key={i} className="text-xs bg-slate-200 text-slate-600 px-2 py-0.5 rounded">
                                    {m}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
};

export default VendorProfileView;
