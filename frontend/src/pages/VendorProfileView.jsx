import { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useAuth, api } from "../App";
import DashboardLayout from "../components/layout/DashboardLayout";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../components/ui/dialog";
import { toast } from "sonner";
import { 
  Building2, MapPin, Phone, Globe, Mail, Award, Star,
  Wrench, Package, CheckCircle2, ArrowLeft, Loader2,
  MessageSquare, ExternalLink, Briefcase, TrendingUp, ThumbsUp,
  Quote, Image, X, ChevronLeft, ChevronRight, Maximize2,
  Settings, Gauge, Ruler, Activity, Info
} from "lucide-react";

// Helper function to get machine availability badge
const getAvailabilityBadge = (status) => {
  const badges = {
    available: { label: "Available", color: "bg-green-100 text-green-700 border-green-200" },
    engaged: { label: "Engaged", color: "bg-amber-100 text-amber-700 border-amber-200" },
    maintenance: { label: "Maintenance", color: "bg-slate-100 text-slate-600 border-slate-200" },
    offline: { label: "Offline", color: "bg-red-100 text-red-700 border-red-200" }
  };
  return badges[status] || badges.available;
};

// Helper to format dimension display based on machine category/type
const getMachineDimensions = (machine) => {
  const dims = [];
  
  // Standard XYZ dimensions
  if (machine.max_x || machine.max_y || machine.max_z) {
    dims.push({ 
      label: "Work Envelope (XYZ)", 
      value: `${machine.max_x || '-'} × ${machine.max_y || '-'} × ${machine.max_z || '-'} mm` 
    });
  }
  
  // Turning/Lathe specific
  if (machine.max_diameter) dims.push({ label: "Max Diameter", value: `Ø${machine.max_diameter} mm` });
  if (machine.max_length) dims.push({ label: "Max Length", value: `${machine.max_length} mm` });
  if (machine.max_swing) dims.push({ label: "Max Swing", value: `Ø${machine.max_swing} mm` });
  
  // Boring specific
  if (machine.spindle_bore) dims.push({ label: "Spindle Bore", value: `Ø${machine.spindle_bore} mm` });
  if (machine.spindle_travel) dims.push({ label: "Spindle Travel", value: `${machine.spindle_travel} mm` });
  if (machine.bore_diameter) dims.push({ label: "Bore Diameter", value: `Ø${machine.bore_diameter} mm` });
  
  // VTL/Table specific
  if (machine.table_diameter) dims.push({ label: "Table Diameter", value: `Ø${machine.table_diameter} mm` });
  if (machine.table_size_x || machine.table_size_y) {
    dims.push({ label: "Table Size", value: `${machine.table_size_x || '-'} × ${machine.table_size_y || '-'} mm` });
  }
  if (machine.max_weight) dims.push({ label: "Max Weight", value: `${machine.max_weight} kg` });
  
  // Sheet Metal specific
  if (machine.tonnage) dims.push({ label: "Tonnage", value: `${machine.tonnage} tons` });
  if (machine.max_thickness) dims.push({ label: "Max Thickness", value: `${machine.max_thickness} mm` });
  if (machine.laser_power) dims.push({ label: "Laser Power", value: `${machine.laser_power} W` });
  
  // Gear specific
  if (machine.max_module) dims.push({ label: "Max Module", value: machine.max_module });
  if (machine.min_teeth) dims.push({ label: "Min Teeth", value: machine.min_teeth });
  
  // Grinding/Drilling specific
  if (machine.arm_length) dims.push({ label: "Arm Length", value: `${machine.arm_length} mm` });
  if (machine.max_depth) dims.push({ label: "Max Depth", value: `${machine.max_depth} mm` });
  if (machine.max_stroke || machine.stroke) dims.push({ label: "Stroke", value: `${machine.max_stroke || machine.stroke} mm` });
  
  // Heat Treatment
  if (machine.max_temp) dims.push({ label: "Max Temp", value: `${machine.max_temp}°C` });
  
  // EDM specific
  if (machine.max_taper_angle) dims.push({ label: "Max Taper Angle", value: `${machine.max_taper_angle}°` });
  
  // 5-Axis specific
  if (machine.a_axis_range) dims.push({ label: "A-Axis Range", value: `${machine.a_axis_range}°` });
  if (machine.c_axis_range) dims.push({ label: "C-Axis Range", value: `${machine.c_axis_range}°` });
  
  // Welding
  if (machine.amperage) dims.push({ label: "Amperage", value: `${machine.amperage} A` });
  
  // Inspection
  if (machine.accuracy) dims.push({ label: "Accuracy", value: `±${machine.accuracy} mm` });
  
  // Additive
  if (machine.layer_thickness) dims.push({ label: "Layer Thickness", value: `${machine.layer_thickness} mm` });
  
  return dims;
};

const VendorProfileView = () => {
  const { vendorId } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [vendor, setVendor] = useState(null);
  const [ratings, setRatings] = useState(null);
  const [loading, setLoading] = useState(true);
  
  // Image gallery state
  const [selectedMachine, setSelectedMachine] = useState(null);
  const [galleryOpen, setGalleryOpen] = useState(false);
  const [currentImageIndex, setCurrentImageIndex] = useState(0);

  useEffect(() => {
    fetchVendor();
    fetchRatings();
  }, [vendorId]);
  
  // Image gallery handlers
  const openGallery = (machine, imageIndex = 0) => {
    setSelectedMachine(machine);
    setCurrentImageIndex(imageIndex);
    setGalleryOpen(true);
  };
  
  const closeGallery = () => {
    setGalleryOpen(false);
    setSelectedMachine(null);
    setCurrentImageIndex(0);
  };
  
  const nextImage = () => {
    if (selectedMachine && selectedMachine.images) {
      setCurrentImageIndex((prev) => 
        prev === selectedMachine.images.length - 1 ? 0 : prev + 1
      );
    }
  };
  
  const prevImage = () => {
    if (selectedMachine && selectedMachine.images) {
      setCurrentImageIndex((prev) => 
        prev === 0 ? selectedMachine.images.length - 1 : prev - 1
      );
    }
  };
  
  // Get the proper image URL
  const getImageUrl = (imageUrl) => {
    if (!imageUrl) return null;
    // Handle relative URLs
    if (imageUrl.startsWith('/api/')) {
      const backendUrl = window.location.origin;
      return `${backendUrl}${imageUrl}`;
    }
    return imageUrl;
  };

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

  const fetchRatings = async () => {
    try {
      const response = await api.get(`/vendors/${vendorId}/ratings`);
      setRatings(response.data);
    } catch (error) {
      console.error("Failed to load ratings:", error);
    }
  };

  const startChat = () => {
    navigate(`/chat?with=${vendor.user_id}`);
  };

  const StarDisplay = ({ value, size = "sm" }) => (
    <div className="flex gap-0.5">
      {[1, 2, 3, 4, 5].map((star) => (
        <Star 
          key={star}
          className={`${size === "sm" ? "w-4 h-4" : "w-5 h-5"} ${
            star <= value ? "fill-amber-400 text-amber-400" : "text-slate-300"
          }`}
        />
      ))}
    </div>
  );

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
              <Card className="border-slate-200" data-testid="vendor-machines-section">
                <CardHeader>
                  <CardTitle className="font-heading text-lg flex items-center gap-2">
                    <Wrench className="w-5 h-5 text-orange-600" /> Manufacturing Equipment ({vendor.machines.length})
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid gap-6">
                    {vendor.machines.map((machine) => {
                      const availabilityBadge = getAvailabilityBadge(machine.availability_status);
                      const dimensions = getMachineDimensions(machine);
                      const hasImages = machine.images && machine.images.length > 0;
                      
                      return (
                        <div 
                          key={machine.machine_id}
                          className="bg-slate-50 rounded-lg border border-slate-200 overflow-hidden"
                          data-testid={`machine-card-${machine.machine_id}`}
                        >
                          <div className="flex flex-col lg:flex-row">
                            {/* Machine Images Section */}
                            <div className="lg:w-1/3 p-4">
                              {hasImages ? (
                                <div className="space-y-2">
                                  {/* Main Image */}
                                  <div 
                                    className="relative aspect-video bg-white rounded-lg overflow-hidden cursor-pointer group"
                                    onClick={() => openGallery(machine, 0)}
                                    data-testid={`machine-main-image-${machine.machine_id}`}
                                  >
                                    <img 
                                      src={getImageUrl(machine.images[0])}
                                      alt={machine.name || machine.machine_type}
                                      className="w-full h-full object-cover"
                                    />
                                    <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-all flex items-center justify-center">
                                      <Maximize2 className="w-8 h-8 text-white opacity-0 group-hover:opacity-100 transition-opacity" />
                                    </div>
                                    {machine.images.length > 1 && (
                                      <span className="absolute bottom-2 right-2 px-2 py-1 bg-black/60 text-white text-xs rounded flex items-center gap-1">
                                        <Image className="w-3 h-3" />
                                        {machine.images.length}
                                      </span>
                                    )}
                                  </div>
                                  
                                  {/* Thumbnail Gallery */}
                                  {machine.images.length > 1 && (
                                    <div className="flex gap-2 overflow-x-auto py-1">
                                      {machine.images.slice(0, 4).map((img, idx) => (
                                        <div 
                                          key={idx}
                                          className="w-16 h-16 flex-shrink-0 rounded-md overflow-hidden cursor-pointer border-2 border-transparent hover:border-orange-400 transition-colors"
                                          onClick={() => openGallery(machine, idx)}
                                        >
                                          <img 
                                            src={getImageUrl(img)}
                                            alt={`${machine.name || machine.machine_type} ${idx + 1}`}
                                            className="w-full h-full object-cover"
                                          />
                                        </div>
                                      ))}
                                      {machine.images.length > 4 && (
                                        <div 
                                          className="w-16 h-16 flex-shrink-0 rounded-md bg-slate-200 flex items-center justify-center cursor-pointer hover:bg-slate-300 transition-colors"
                                          onClick={() => openGallery(machine, 4)}
                                        >
                                          <span className="text-sm font-medium text-slate-600">+{machine.images.length - 4}</span>
                                        </div>
                                      )}
                                    </div>
                                  )}
                                </div>
                              ) : (
                                <div className="aspect-video bg-slate-100 rounded-lg flex flex-col items-center justify-center text-slate-400">
                                  <Wrench className="w-12 h-12 mb-2" />
                                  <span className="text-sm">No photos available</span>
                                </div>
                              )}
                            </div>
                            
                            {/* Machine Details Section */}
                            <div className="flex-1 p-4 lg:border-l border-slate-200">
                              {/* Header */}
                              <div className="flex items-start justify-between mb-4">
                                <div>
                                  <div className="flex items-center gap-2">
                                    <h3 className="font-semibold text-lg text-slate-900">
                                      {machine.name || machine.machine_type}
                                    </h3>
                                    {machine.machine_category && (
                                      <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded-full">
                                        {machine.machine_category}
                                      </span>
                                    )}
                                  </div>
                                  <p className="text-sm text-slate-500 mt-1">
                                    {machine.brand} {machine.model}
                                  </p>
                                </div>
                                <div className="flex flex-col items-end gap-2">
                                  <span className={`px-3 py-1 text-xs font-medium rounded-full border ${availabilityBadge.color}`}>
                                    {availabilityBadge.label}
                                  </span>
                                  {machine.axis_config && (
                                    <span className="px-2 py-1 bg-slate-200 text-slate-700 text-xs rounded">
                                      {machine.axis_config}
                                    </span>
                                  )}
                                </div>
                              </div>
                              
                              {/* Specifications Grid */}
                              <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-4">
                                {/* Tolerance - Always show */}
                                <div className="bg-white rounded-lg p-3 border border-slate-100">
                                  <div className="flex items-center gap-2 text-slate-500 mb-1">
                                    <Gauge className="w-4 h-4" />
                                    <span className="text-xs uppercase">Tolerance</span>
                                  </div>
                                  <p className="font-mono font-medium text-slate-900">
                                    ±{machine.tolerance || machine.tolerance_capability || 0.1} mm
                                  </p>
                                </div>
                                
                                {/* Dynamic dimensions based on machine type */}
                                {dimensions.slice(0, 5).map((dim, idx) => (
                                  <div key={idx} className="bg-white rounded-lg p-3 border border-slate-100">
                                    <div className="flex items-center gap-2 text-slate-500 mb-1">
                                      <Ruler className="w-4 h-4" />
                                      <span className="text-xs uppercase">{dim.label}</span>
                                    </div>
                                    <p className="font-mono font-medium text-slate-900 text-sm">{dim.value}</p>
                                  </div>
                                ))}
                                
                                {/* Capacity */}
                                {machine.monthly_capacity_hours && (
                                  <div className="bg-white rounded-lg p-3 border border-slate-100">
                                    <div className="flex items-center gap-2 text-slate-500 mb-1">
                                      <Activity className="w-4 h-4" />
                                      <span className="text-xs uppercase">Monthly Capacity</span>
                                    </div>
                                    <p className="font-mono font-medium text-slate-900">{machine.monthly_capacity_hours} hrs</p>
                                  </div>
                                )}
                              </div>
                              
                              {/* Materials Supported */}
                              {(machine.materials_supported?.length > 0 || machine.materials?.length > 0) && (
                                <div>
                                  <p className="text-xs text-slate-500 uppercase mb-2">Materials Supported</p>
                                  <div className="flex flex-wrap gap-1">
                                    {(machine.materials_supported || machine.materials || []).map((m, i) => (
                                      <span key={i} className="text-xs bg-emerald-100 text-emerald-700 px-2 py-1 rounded">
                                        {m}
                                      </span>
                                    ))}
                                  </div>
                                </div>
                              )}
                              
                              {/* Availability Note */}
                              {machine.availability_note && (
                                <div className="mt-3 flex items-start gap-2 p-2 bg-amber-50 rounded-lg border border-amber-200">
                                  <Info className="w-4 h-4 text-amber-600 mt-0.5 flex-shrink-0" />
                                  <p className="text-sm text-amber-700">{machine.availability_note}</p>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Customer Reviews */}
            {ratings && (
              <Card className="border-slate-200" data-testid="vendor-ratings-section">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="font-heading text-lg flex items-center gap-2">
                      <Star className="w-5 h-5 fill-amber-400 text-amber-400" /> Customer Reviews
                    </CardTitle>
                    {ratings.stats?.total_reviews > 0 && (
                      <span className="text-sm text-slate-500">
                        {ratings.stats.total_reviews} review{ratings.stats.total_reviews !== 1 ? "s" : ""}
                      </span>
                    )}
                  </div>
                </CardHeader>
                <CardContent>
                  {ratings.stats?.total_reviews > 0 ? (
                    <div className="space-y-6">
                      {/* Rating Summary */}
                      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 p-4 bg-gradient-to-r from-amber-50 to-orange-50 rounded-lg">
                        <div className="col-span-2 md:col-span-1 text-center">
                          <p className="text-4xl font-bold text-amber-600">
                            {ratings.stats.average_overall.toFixed(1)}
                          </p>
                          <StarDisplay value={Math.round(ratings.stats.average_overall)} />
                          <p className="text-xs text-slate-500 mt-1">Overall</p>
                        </div>
                        <div className="text-center">
                          <p className="text-lg font-semibold">{ratings.stats.average_quality.toFixed(1)}</p>
                          <p className="text-xs text-slate-500">Quality</p>
                        </div>
                        <div className="text-center">
                          <p className="text-lg font-semibold">{ratings.stats.average_communication.toFixed(1)}</p>
                          <p className="text-xs text-slate-500">Communication</p>
                        </div>
                        <div className="text-center">
                          <p className="text-lg font-semibold">{ratings.stats.average_delivery.toFixed(1)}</p>
                          <p className="text-xs text-slate-500">Delivery</p>
                        </div>
                        <div className="text-center">
                          <div className="flex items-center justify-center gap-1 text-green-600">
                            <ThumbsUp className="w-4 h-4" />
                            <span className="text-lg font-semibold">{ratings.stats.recommendation_rate}%</span>
                          </div>
                          <p className="text-xs text-slate-500">Recommend</p>
                        </div>
                      </div>

                      {/* Individual Reviews */}
                      <div className="space-y-4">
                        {ratings.ratings.slice(0, 5).map((review) => (
                          <div 
                            key={review.rating_id}
                            className="p-4 border border-slate-200 rounded-lg"
                            data-testid={`review-${review.rating_id}`}
                          >
                            <div className="flex items-start justify-between">
                              <div>
                                <p className="font-medium text-slate-900">{review.buyer_name}</p>
                                <p className="text-xs text-slate-500 mt-0.5">
                                  {review.rfq_title && `Order: ${review.rfq_title}`}
                                </p>
                              </div>
                              <div className="text-right">
                                <StarDisplay value={review.overall_rating} />
                                <p className="text-xs text-slate-400 mt-1">
                                  {new Date(review.created_at).toLocaleDateString()}
                                </p>
                              </div>
                            </div>
                            
                            {review.review_text && (
                              <div className="mt-3 pl-4 border-l-2 border-slate-200">
                                <p className="text-sm text-slate-600 italic">"{review.review_text}"</p>
                              </div>
                            )}
                            
                            <div className="flex items-center gap-4 mt-3 text-xs text-slate-500">
                              <span>Quality: {review.quality_rating}/5</span>
                              <span>Communication: {review.communication_rating}/5</span>
                              <span>Delivery: {review.delivery_rating}/5</span>
                              {review.would_recommend && (
                                <span className="flex items-center gap-1 text-green-600">
                                  <ThumbsUp className="w-3 h-3" /> Recommended
                                </span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-8">
                      <Quote className="w-12 h-12 text-slate-300 mx-auto mb-2" />
                      <p className="text-slate-500">No reviews yet</p>
                      <p className="text-xs text-slate-400 mt-1">
                        Be the first to work with this vendor!
                      </p>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
      
      {/* Image Gallery Modal */}
      <Dialog open={galleryOpen} onOpenChange={setGalleryOpen}>
        <DialogContent className="max-w-4xl h-[90vh] p-0 bg-slate-900 border-slate-800" data-testid="image-gallery-modal">
          <DialogHeader className="absolute top-0 left-0 right-0 z-10 p-4 bg-gradient-to-b from-black/80 to-transparent">
            <div className="flex items-center justify-between text-white">
              <DialogTitle className="text-lg font-medium">
                {selectedMachine?.name || selectedMachine?.machine_type} - Photos
              </DialogTitle>
              <Button 
                variant="ghost" 
                size="icon"
                className="text-white hover:bg-white/20"
                onClick={closeGallery}
              >
                <X className="w-5 h-5" />
              </Button>
            </div>
            {selectedMachine?.images?.length > 1 && (
              <p className="text-slate-400 text-sm">
                {currentImageIndex + 1} of {selectedMachine.images.length}
              </p>
            )}
          </DialogHeader>
          
          {selectedMachine && selectedMachine.images && (
            <div className="relative h-full flex items-center justify-center">
              {/* Main Image */}
              <img 
                src={getImageUrl(selectedMachine.images[currentImageIndex])}
                alt={`${selectedMachine.name || selectedMachine.machine_type} ${currentImageIndex + 1}`}
                className="max-h-[80vh] max-w-full object-contain"
                data-testid="gallery-main-image"
              />
              
              {/* Navigation Arrows */}
              {selectedMachine.images.length > 1 && (
                <>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="absolute left-4 top-1/2 -translate-y-1/2 text-white bg-black/50 hover:bg-black/70 rounded-full w-12 h-12"
                    onClick={prevImage}
                    data-testid="gallery-prev-btn"
                  >
                    <ChevronLeft className="w-8 h-8" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-white bg-black/50 hover:bg-black/70 rounded-full w-12 h-12"
                    onClick={nextImage}
                    data-testid="gallery-next-btn"
                  >
                    <ChevronRight className="w-8 h-8" />
                  </Button>
                </>
              )}
              
              {/* Thumbnail Strip */}
              {selectedMachine.images.length > 1 && (
                <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-2 bg-black/60 p-2 rounded-lg">
                  {selectedMachine.images.map((img, idx) => (
                    <button
                      key={idx}
                      className={`w-14 h-14 rounded overflow-hidden border-2 transition-all ${
                        idx === currentImageIndex ? 'border-orange-500 scale-105' : 'border-transparent opacity-60 hover:opacity-100'
                      }`}
                      onClick={() => setCurrentImageIndex(idx)}
                    >
                      <img 
                        src={getImageUrl(img)}
                        alt={`Thumbnail ${idx + 1}`}
                        className="w-full h-full object-cover"
                      />
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </DashboardLayout>
  );
};

export default VendorProfileView;
