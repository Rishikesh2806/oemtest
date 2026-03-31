import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth, api } from "../App";
import DashboardLayout from "../components/layout/DashboardLayout";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Checkbox } from "../components/ui/checkbox";
import { toast } from "sonner";
import { 
  Upload, FileText, ArrowRight, ArrowLeft, 
  CheckCircle2, Loader2, X, Cpu, Target, Package,
  AlertTriangle, Ruler, Scale, MapPin, Truck, Globe, Building2, Clock, Zap, Shield, Camera, Search
} from "lucide-react";
import { Switch } from "../components/ui/switch";

const MATERIALS = [
  "Aluminum", "Steel", "Stainless Steel", "Carbon Steel", 
  "Brass", "Copper", "Titanium", "Plastic/Nylon", "ABS", "Other"
];

const SURFACE_FINISHES = [
  "As Machined", "Anodized", "Powder Coated", "Painted",
  "Polished", "Brushed", "Chrome Plated", "Zinc Plated", "None"
];

const URGENCY_OPTIONS = [
  { value: "urgent", label: "Urgent - Need ASAP", icon: "🔴", color: "text-red-600" },
  { value: "high", label: "High Priority", icon: "🟠", color: "text-orange-600" },
  { value: "normal", label: "Normal", icon: "🟢", color: "text-green-600" },
  { value: "low", label: "Low Priority - Flexible", icon: "🔵", color: "text-blue-600" }
];

const PAYMENT_TERMS = [
  { value: "net_30", label: "Net 30 Days" },
  { value: "net_45", label: "Net 45 Days" },
  { value: "net_60", label: "Net 60 Days" },
  { value: "50_advance_50_delivery", label: "50% Advance, 50% on Delivery" },
  { value: "100_advance", label: "100% Advance" },
  { value: "against_delivery", label: "Payment Against Delivery" },
  { value: "milestone_based", label: "Milestone-Based Payment" },
  { value: "letter_of_credit", label: "Letter of Credit (LC)" },
  { value: "custom", label: "Custom Terms" }
];

const CreateRFQ = () => {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [matching, setMatching] = useState(false);
  const [rfqId, setRfqId] = useState(null);
  const [files, setFiles] = useState([]);
  const [uploadProgress, setUploadProgress] = useState({});
  const [uploadController, setUploadController] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  
  const [analysisResult, setAnalysisResult] = useState(null);
  const [partGeometry, setPartGeometry] = useState("rectangular");
  const [imageType, setImageType] = useState(null);
  const [noMatchesFound, setNoMatchesFound] = useState(false);

  const [formData, setFormData] = useState({
    title: "",
    description: "",
    material_type: "",
    quantity: 1,
    tolerance: 0.1,
    surface_finish: "",
    supply_type: "vendor_material",
    deadline: "",
    urgency: "normal",
    preferred_payment_terms: "net_30",
    payment_terms_notes: "",
    // Delivery location
    delivery_address: "",
    delivery_city: "",
    delivery_state: "",
    delivery_country: "India",
    delivery_pincode: "",
    incoterms: "EXW",
    // Preferred vendor locations
    preferred_vendor_countries: [],
    preferred_vendor_cities: [],
    // NDA Protection
    require_nda: false,
    nda_id: null
  });

  // Incoterms options
  const INCOTERMS_OPTIONS = [
    { value: "EXW", label: "EXW - Ex Works" },
    { value: "FCA", label: "FCA - Free Carrier" },
    { value: "FOB", label: "FOB - Free on Board" },
    { value: "CFR", label: "CFR - Cost and Freight" },
    { value: "CIF", label: "CIF - Cost, Insurance and Freight" },
    { value: "CPT", label: "CPT - Carriage Paid To" },
    { value: "CIP", label: "CIP - Carriage and Insurance Paid To" },
    { value: "DAP", label: "DAP - Delivered at Place" },
    { value: "DPU", label: "DPU - Delivered at Place Unloaded" },
    { value: "DDP", label: "DDP - Delivered Duty Paid" }
  ];

  // Country options for vendor preferences (India only)
  const COUNTRY_OPTIONS = ["India"];

  // State for available cities (India only)
  const [availableCities, setAvailableCities] = useState({});
  const [loadingCities, setLoadingCities] = useState(false);

  // Fetch India cities on component mount
  useEffect(() => {
    const fetchCities = async () => {
      setLoadingCities(true);
      try {
        const response = await api.get(`/locations/cities?countries=India`);
        setAvailableCities(response.data);
        // Auto-set India as preferred country
        if (!formData.preferred_vendor_countries.includes("India")) {
          setFormData(prev => ({
            ...prev,
            preferred_vendor_countries: ["India"]
          }));
        }
      } catch (error) {
        console.error("Failed to fetch cities:", error);
      } finally {
        setLoadingCities(false);
      }
    };

    fetchCities();
  }, []);

  const handleInputChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleFileSelect = (e) => {
    const selectedFiles = Array.from(e.target.files);
    setFiles(prev => [...prev, ...selectedFiles]);
  };

  const removeFile = (index) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const droppedFiles = Array.from(e.dataTransfer.files);
    setFiles(prev => [...prev, ...droppedFiles]);
  };

  const createRFQ = async () => {
    if (!formData.title || !formData.material_type) {
      toast.error("Please fill in required fields");
      return;
    }

    setLoading(true);
    try {
      const response = await api.post("/rfqs", formData);
      setRfqId(response.data.rfq_id);
      toast.success("RFQ created successfully");
      setStep(2);
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to create RFQ");
    } finally {
      setLoading(false);
    }
  };

  const uploadFiles = async () => {
    if (files.length === 0) {
      toast.error("Please upload at least one drawing");
      return;
    }

    // Create abort controller for cancellation
    const controller = new AbortController();
    setUploadController(controller);
    setIsUploading(true);
    setLoading(true);
    
    try {
      for (let i = 0; i < files.length; i++) {
        // Check if upload was cancelled
        if (controller.signal.aborted) {
          throw new Error("Upload cancelled");
        }
        
        const file = files[i];
        const formDataUpload = new FormData();
        formDataUpload.append("file", file);

        setUploadProgress(prev => ({ ...prev, [i]: 0 }));

        await api.post(`/rfqs/${rfqId}/drawings`, formDataUpload, {
          headers: { "Content-Type": "multipart/form-data" },
          signal: controller.signal,
          onUploadProgress: (progressEvent) => {
            const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            setUploadProgress(prev => ({ ...prev, [i]: percent }));
          }
        });
      }
      
      toast.success("Drawings uploaded successfully");
      setStep(3);
    } catch (error) {
      if (error.name === 'CanceledError' || error.message === 'Upload cancelled') {
        toast.info("Upload cancelled");
        setUploadProgress({});
      } else {
        toast.error("Failed to upload drawings");
      }
    } finally {
      setLoading(false);
      setIsUploading(false);
      setUploadController(null);
    }
  };

  const cancelUpload = () => {
    if (uploadController) {
      uploadController.abort();
      toast.info("Cancelling upload...");
    }
  };

  const analyzeDrawings = async () => {
    setAnalyzing(true);
    try {
      const response = await api.post(`/rfqs/${rfqId}/analyze`);
      const { 
        analysis, 
        part_geometry, 
        image_type,
        analyzed_count,
        skipped_cad_files,
        note
      } = response.data;
      
      setAnalysisResult(analysis);
      setPartGeometry(part_geometry || analysis?.part_geometry || "rectangular");
      setImageType(image_type || analysis?.image_type || "technical_drawing");
      
      // Show appropriate messages based on analysis results
      if (analyzed_count === 0) {
        toast.warning(note || "No drawings could be analyzed. Please add PDF or image files.");
      } else if (image_type === "reference_photo") {
        toast.success(`AI detected reference photo(s) - will match against vendor portfolios!`);
      } else if (skipped_cad_files?.length > 0) {
        toast.info(`Analyzed ${analyzed_count} drawing(s). ${skipped_cad_files.length} CAD file(s) kept as attachments.`);
      } else {
        toast.success(`AI analysis complete - analyzed ${analyzed_count} drawing(s)!`);
      }
      setStep(4);
    } catch (error) {
      const errorMessage = error.response?.data?.detail || error.response?.data?.analysis?.error || "Analysis failed";
      
      // Check if it's a file format error
      if (errorMessage.includes("CAD format") || errorMessage.includes("DWG") || errorMessage.includes("STEP")) {
        toast.error(errorMessage, { duration: 8000 });
        return;
      }
      
      toast.error("Analysis failed, but continuing with matching");
      setStep(4);
    } finally {
      setAnalyzing(false);
    }
  };

  const matchVendors = async () => {
    setMatching(true);
    setNoMatchesFound(false);
    try {
      // Use AI-determined image_type for routing
      const usePortfolioMatch = imageType === "reference_photo";
      
      const endpoint = usePortfolioMatch 
        ? `/rfqs/${rfqId}/portfolio-match`
        : `/rfqs/${rfqId}/match`;
      
      const response = await api.post(endpoint);
      const matchedCount = response.data?.total_matches ?? response.data?.matched_vendors?.length ?? 0;
      if (matchedCount === 0) {
        setNoMatchesFound(true);
        toast.info("No vendors matched yet. Your RFQ is live — vendors can still find and quote on it.");
      } else {
        const matchType = response.data?.match_type === "portfolio" ? "by portfolio similarity" : "";
        toast.success(`${matchedCount} vendor${matchedCount > 1 ? 's' : ''} matched ${matchType}!`);
        navigate(`/buyer/rfq/${rfqId}`);
      }
    } catch (error) {
      toast.error("Matching failed. Please try again.");
    } finally {
      setMatching(false);
    }
  };

  return (
    <DashboardLayout>
      <div className="max-w-4xl mx-auto" data-testid="create-rfq-page">
        {/* Progress Steps */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            {[
              { num: 1, label: "RFQ Details", icon: FileText },
              { num: 2, label: "Upload Drawings", icon: Upload },
              { num: 3, label: "AI Analysis", icon: Cpu },
              { num: 4, label: "Vendor Match", icon: Target }
            ].map((s, i) => (
              <div key={s.num} className="flex items-center">
                <div className={`flex flex-col items-center ${step >= s.num ? "text-orange-600" : "text-slate-400"}`}>
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center border-2 
                    ${step >= s.num ? "border-orange-600 bg-orange-50" : "border-slate-300"}`}>
                    <s.icon className="w-5 h-5" />
                  </div>
                  <span className="text-xs mt-1 font-medium hidden sm:block">{s.label}</span>
                </div>
                {i < 3 && (
                  <div className={`w-16 sm:w-24 h-0.5 mx-2 ${step > s.num ? "bg-orange-600" : "bg-slate-200"}`} />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Step 1: RFQ Details */}
        {step === 1 && (
          <Card className="border-slate-200">
            <CardHeader>
              <CardTitle className="font-heading text-xl">RFQ Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div>
                <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  Title *
                </Label>
                <Input
                  value={formData.title}
                  onChange={(e) => handleInputChange("title", e.target.value)}
                  placeholder="e.g., CNC Machined Bracket"
                  className="mt-1"
                  data-testid="rfq-title-input"
                />
              </div>

              <div>
                <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  Description
                </Label>
                <Textarea
                  value={formData.description}
                  onChange={(e) => handleInputChange("description", e.target.value)}
                  placeholder="Describe the part and any special requirements..."
                  className="mt-1 min-h-[100px]"
                  data-testid="rfq-description-input"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    Material Type *
                  </Label>
                  <Select
                    value={formData.material_type}
                    onValueChange={(value) => handleInputChange("material_type", value)}
                  >
                    <SelectTrigger className="mt-1" data-testid="material-select">
                      <SelectValue placeholder="Select material" />
                    </SelectTrigger>
                    <SelectContent>
                      {MATERIALS.map((m) => (
                        <SelectItem key={m} value={m}>{m}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    Quantity
                  </Label>
                  <Input
                    type="number"
                    min={1}
                    value={formData.quantity}
                    onChange={(e) => handleInputChange("quantity", parseInt(e.target.value) || 1)}
                    className="mt-1"
                    data-testid="quantity-input"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 gap-4">
                <div>
                  <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    Surface Finish
                  </Label>
                  <Select
                    value={formData.surface_finish}
                    onValueChange={(value) => handleInputChange("surface_finish", value)}
                  >
                    <SelectTrigger className="mt-1" data-testid="finish-select">
                      <SelectValue placeholder="Select finish" />
                    </SelectTrigger>
                    <SelectContent>
                      {SURFACE_FINISHES.map((f) => (
                        <SelectItem key={f} value={f}>{f}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Urgency & Deadline */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    <Zap className="w-3 h-3 inline mr-1" /> Urgency Level
                  </Label>
                  <Select
                    value={formData.urgency}
                    onValueChange={(value) => handleInputChange("urgency", value)}
                  >
                    <SelectTrigger className="mt-1" data-testid="urgency-select">
                      <SelectValue placeholder="Select urgency" />
                    </SelectTrigger>
                    <SelectContent>
                      {URGENCY_OPTIONS.map((option) => (
                        <SelectItem key={option.value} value={option.value}>
                          <span className="flex items-center gap-2">
                            <span>{option.icon}</span>
                            <span>{option.label}</span>
                          </span>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-slate-400 mt-1">
                    Helps vendors prioritize your request
                  </p>
                </div>

                <div>
                  <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    <Clock className="w-3 h-3 inline mr-1" /> Deadline (Optional)
                  </Label>
                  <Input
                    type="date"
                    value={formData.deadline}
                    onChange={(e) => handleInputChange("deadline", e.target.value)}
                    className="mt-1"
                    min={new Date().toISOString().split('T')[0]}
                    data-testid="deadline-input"
                  />
                  <p className="text-xs text-slate-400 mt-1">
                    When do you need this delivered?
                  </p>
                </div>
              </div>

              <div>
                <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  Supply Type
                </Label>
                <div className="grid grid-cols-2 gap-4 mt-2">
                  <button
                    type="button"
                    onClick={() => handleInputChange("supply_type", "vendor_material")}
                    className={`p-4 rounded-lg border-2 text-left transition-all ${
                      formData.supply_type === "vendor_material"
                        ? "border-orange-600 bg-orange-50"
                        : "border-slate-200 hover:border-slate-300"
                    }`}
                    data-testid="supply-vendor-btn"
                  >
                    <Package className={`w-5 h-5 mb-2 ${formData.supply_type === "vendor_material" ? "text-orange-600" : "text-slate-400"}`} />
                    <p className="font-medium text-slate-900">Vendor Supplies Material</p>
                    <p className="text-xs text-slate-500">Complete turnkey solution</p>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleInputChange("supply_type", "buyer_material")}
                    className={`p-4 rounded-lg border-2 text-left transition-all ${
                      formData.supply_type === "buyer_material"
                        ? "border-orange-600 bg-orange-50"
                        : "border-slate-200 hover:border-slate-300"
                    }`}
                    data-testid="supply-buyer-btn"
                  >
                    <Package className={`w-5 h-5 mb-2 ${formData.supply_type === "buyer_material" ? "text-orange-600" : "text-slate-400"}`} />
                    <p className="font-medium text-slate-900">I Supply Material</p>
                    <p className="text-xs text-slate-500">Service/machining only</p>
                  </button>
                </div>
              </div>

              {/* Payment Terms */}
              <div className="pt-4 border-t border-slate-200">
                <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  Preferred Payment Terms
                </Label>
                <div className="grid grid-cols-2 gap-4 mt-2">
                  <Select
                    value={formData.preferred_payment_terms}
                    onValueChange={(value) => handleInputChange("preferred_payment_terms", value)}
                  >
                    <SelectTrigger data-testid="payment-terms-select">
                      <SelectValue placeholder="Select payment terms" />
                    </SelectTrigger>
                    <SelectContent>
                      {PAYMENT_TERMS.map((term) => (
                        <SelectItem key={term.value} value={term.value}>{term.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  
                  {formData.preferred_payment_terms === "custom" && (
                    <Input
                      placeholder="Specify custom terms..."
                      value={formData.payment_terms_notes}
                      onChange={(e) => handleInputChange("payment_terms_notes", e.target.value)}
                      data-testid="payment-terms-notes"
                    />
                  )}
                </div>
                {formData.preferred_payment_terms !== "custom" && (
                  <Textarea
                    placeholder="Additional payment notes (optional)"
                    value={formData.payment_terms_notes}
                    onChange={(e) => handleInputChange("payment_terms_notes", e.target.value)}
                    className="mt-2"
                    rows={2}
                    data-testid="payment-notes-textarea"
                  />
                )}
              </div>

              {/* IP Protection / NDA Section */}
              <div className="pt-6 border-t border-slate-200">
                <div className="flex items-center gap-2 mb-4">
                  <Shield className="w-5 h-5 text-orange-600" />
                  <h3 className="font-semibold text-slate-900">IP Protection</h3>
                </div>
                
                <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <Label className="text-sm font-medium text-amber-900 flex items-center gap-2">
                        <Shield className="w-4 h-4" />
                        Require NDA for Drawings
                      </Label>
                      <p className="text-xs text-amber-700 mt-1">
                        When enabled, vendors must accept a Non-Disclosure Agreement before they can view 
                        or download your drawings and technical documents. This helps protect your intellectual property.
                      </p>
                    </div>
                    <Switch
                      checked={formData.require_nda}
                      onCheckedChange={(checked) => handleInputChange("require_nda", checked)}
                      data-testid="require-nda-switch"
                    />
                  </div>
                  
                  {formData.require_nda && (
                    <div className="mt-3 pt-3 border-t border-amber-200">
                      <div className="flex items-center gap-2 text-xs text-amber-700">
                        <CheckCircle2 className="w-4 h-4 text-green-600" />
                        <span>Default NDA template will be used. Contact admin for custom NDA.</span>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Delivery Location Section */}
              <div className="pt-6 border-t border-slate-200">
                <div className="flex items-center gap-2 mb-4">
                  <Truck className="w-5 h-5 text-orange-600" />
                  <h3 className="font-semibold text-slate-900">Delivery Location</h3>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="md:col-span-2">
                    <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                      Delivery Address
                    </Label>
                    <div className="relative mt-1">
                      <MapPin className="absolute left-3 top-3 w-4 h-4 text-slate-400" />
                      <Textarea
                        value={formData.delivery_address}
                        onChange={(e) => handleInputChange("delivery_address", e.target.value)}
                        placeholder="Street address, building, floor, etc."
                        className="pl-10"
                        rows={2}
                        data-testid="delivery-address"
                      />
                    </div>
                  </div>
                  <div>
                    <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">City</Label>
                    <Input
                      value={formData.delivery_city}
                      onChange={(e) => handleInputChange("delivery_city", e.target.value)}
                      placeholder="City"
                      className="mt-1"
                      data-testid="delivery-city"
                    />
                  </div>
                  <div>
                    <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">State</Label>
                    <Input
                      value={formData.delivery_state}
                      onChange={(e) => handleInputChange("delivery_state", e.target.value)}
                      placeholder="State/Province"
                      className="mt-1"
                      data-testid="delivery-state"
                    />
                  </div>
                  <div>
                    <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">Country</Label>
                    <Select
                      value={formData.delivery_country}
                      onValueChange={(value) => handleInputChange("delivery_country", value)}
                    >
                      <SelectTrigger className="mt-1" data-testid="delivery-country">
                        <SelectValue placeholder="Select country" />
                      </SelectTrigger>
                      <SelectContent>
                        {COUNTRY_OPTIONS.map((country) => (
                          <SelectItem key={country} value={country}>{country}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">PIN/ZIP Code</Label>
                    <Input
                      value={formData.delivery_pincode}
                      onChange={(e) => handleInputChange("delivery_pincode", e.target.value)}
                      placeholder="PIN Code"
                      className="mt-1"
                      data-testid="delivery-pincode"
                    />
                  </div>
                </div>
              </div>

              {/* Incoterms Section */}
              <div className="pt-6 border-t border-slate-200">
                <div className="flex items-center gap-2 mb-4">
                  <Globe className="w-5 h-5 text-orange-600" />
                  <h3 className="font-semibold text-slate-900">Shipping Terms & Vendor Preferences</h3>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                      Incoterms
                    </Label>
                    <Select
                      value={formData.incoterms}
                      onValueChange={(value) => handleInputChange("incoterms", value)}
                    >
                      <SelectTrigger className="mt-1" data-testid="incoterms-select">
                        <SelectValue placeholder="Select incoterms" />
                      </SelectTrigger>
                      <SelectContent>
                        {INCOTERMS_OPTIONS.map((term) => (
                          <SelectItem key={term.value} value={term.value}>{term.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-slate-400 mt-1">
                      Defines responsibility for shipping, insurance, and duties
                    </p>
                  </div>
                  
                  <div>
                    <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                      Preferred Vendor Location (India)
                    </Label>
                    <p className="text-xs text-slate-400 mt-1 mb-2">
                      Select cities where you prefer vendors to be located
                    </p>
                  </div>
                </div>
                
                <div className="mt-2">
                  <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    Select Preferred Cities (Optional)
                  </Label>
                  
                  {loadingCities ? (
                    <div className="flex items-center gap-2 mt-2 text-slate-500">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span className="text-sm">Loading cities...</span>
                    </div>
                  ) : (
                    <div className="mt-2 space-y-3">
                      <div className="border border-slate-200 rounded-lg p-3">
                        <div className="flex flex-wrap gap-2 max-h-48 overflow-y-auto">
                          {availableCities?.India?.cities?.map((city) => {
                            const isSelected = formData.preferred_vendor_cities.includes(city.name);
                            return (
                              <button
                                key={city.name}
                                type="button"
                                onClick={() => {
                                  if (isSelected) {
                                    handleInputChange("preferred_vendor_cities", 
                                      formData.preferred_vendor_cities.filter(c => c !== city.name)
                                    );
                                  } else {
                                    handleInputChange("preferred_vendor_cities", 
                                      [...formData.preferred_vendor_cities, city.name]
                                    );
                                  }
                                }}
                                className={`px-2 py-1 text-xs rounded-full border transition-all flex items-center gap-1 ${
                                  isSelected
                                    ? "bg-orange-600 text-white border-orange-600"
                                    : city.has_vendors
                                      ? "bg-purple-50 text-purple-700 border-purple-200 hover:bg-purple-100"
                                      : "bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100"
                                }`}
                              >
                                {city.has_vendors && !isSelected && (
                                  <Building2 className="w-3 h-3" />
                                )}
                                {city.name}
                                {city.has_vendors && !isSelected && (
                                  <span className="text-purple-500">({city.vendor_count})</span>
                                )}
                              </button>
                            );
                          })}
                        </div>
                        {availableCities?.India?.vendor_city_count > 0 && (
                          <p className="text-xs text-purple-600 mt-2 flex items-center gap-1">
                            <Building2 className="w-3 h-3" />
                            Purple = Cities with registered vendors
                          </p>
                        )}
                      </div>
                      
                      {/* Selected cities summary */}
                      {formData.preferred_vendor_cities.length > 0 && (
                        <div className="bg-orange-50 border border-orange-200 rounded-lg p-2">
                          <p className="text-xs text-orange-700">
                            <strong>Selected:</strong> {formData.preferred_vendor_cities.join(", ")}
                          </p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>

              <div className="flex justify-end pt-4">
                <Button 
                  onClick={createRFQ} 
                  disabled={loading}
                  className="bg-orange-600 hover:bg-orange-700"
                  data-testid="next-step-btn"
                >
                  {loading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <>Next: Upload Drawings <ArrowRight className="ml-2 w-4 h-4" /></>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Step 2: Upload Drawings */}
        {step === 2 && (
          <Card className="border-slate-200">
            <CardHeader>
              <CardTitle className="font-heading text-xl">Upload Engineering Drawings</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div
                className="upload-zone rounded-lg p-8 text-center cursor-pointer"
                onDrop={handleDrop}
                onDragOver={(e) => e.preventDefault()}
                onClick={() => document.getElementById("file-input").click()}
                data-testid="upload-zone"
              >
                <Upload className="w-12 h-12 text-slate-400 mx-auto mb-4" />
                <p className="text-slate-600 font-medium">
                  Drag and drop your files here, or click to browse
                </p>
                <p className="text-sm text-slate-500 mt-2">
                  <strong>For AI Analysis:</strong> PDF, PNG, JPG (recommended)
                </p>
                <p className="text-xs text-orange-600 mt-1">
                  Note: DWG, STEP, DXF files can be uploaded but need PDF/image export for AI analysis
                </p>
                <input
                  id="file-input"
                  type="file"
                  multiple
                  accept=".pdf,.step,.stp,.dwg,.dxf,.png,.jpg,.jpeg"
                  onChange={handleFileSelect}
                  className="hidden"
                />
              </div>

              {files.length > 0 && (
                <div className="space-y-2">
                  <p className="text-sm font-medium text-slate-600">Selected Files:</p>
                  {files.map((file, index) => (
                    <div 
                      key={index} 
                      className="flex items-center justify-between p-3 bg-slate-50 rounded-lg"
                    >
                      <div className="flex items-center gap-3">
                        <FileText className="w-5 h-5 text-slate-400" />
                        <div>
                          <p className="text-sm font-medium text-slate-900">{file.name}</p>
                          <p className="text-xs text-slate-500">
                            {(file.size / 1024).toFixed(1)} KB
                          </p>
                        </div>
                      </div>
                      {uploadProgress[index] !== undefined ? (
                        <div className="w-20 h-2 bg-slate-200 rounded-full overflow-hidden">
                          <div 
                            className="h-full bg-orange-600 transition-all"
                            style={{ width: `${uploadProgress[index]}%` }}
                          />
                        </div>
                      ) : (
                        <button 
                          onClick={() => removeFile(index)}
                          className="text-slate-400 hover:text-red-500"
                        >
                          <X className="w-5 h-5" />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}

              <div className="flex justify-between pt-4">
                <Button variant="outline" onClick={() => setStep(1)} disabled={isUploading}>
                  <ArrowLeft className="mr-2 w-4 h-4" /> Back
                </Button>
                <div className="flex gap-2">
                  {isUploading && (
                    <Button 
                      variant="destructive"
                      onClick={cancelUpload}
                      data-testid="cancel-upload-btn"
                    >
                      <X className="mr-2 w-4 h-4" /> Cancel Upload
                    </Button>
                  )}
                  <Button 
                    onClick={uploadFiles} 
                    disabled={loading || files.length === 0}
                    className="bg-orange-600 hover:bg-orange-700"
                    data-testid="upload-btn"
                  >
                    {loading ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin mr-2" />
                        Uploading...
                      </>
                    ) : (
                      <>Upload & Continue <ArrowRight className="ml-2 w-4 h-4" /></>
                    )}
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Step 3: AI Analysis */}
        {step === 3 && (
          <Card className="border-slate-200">
            <CardHeader>
              <CardTitle className="font-heading text-xl">AI Drawing Analysis</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="text-center py-8">
                {analyzing ? (
                  <>
                    <div className="w-16 h-16 mx-auto mb-4 relative">
                      <Cpu className="w-16 h-16 text-orange-600 animate-pulse" />
                    </div>
                    <p className="text-lg font-medium text-slate-900">Analyzing Your Drawings...</p>
                    <p className="text-slate-500 mt-2">
                      Our AI is extracting dimensions, tolerances, and manufacturing requirements
                    </p>
                  </>
                ) : (
                  <>
                    <Cpu className="w-16 h-16 text-slate-400 mx-auto mb-4" />
                    <p className="text-lg font-medium text-slate-900">Ready for AI Analysis</p>
                    <p className="text-slate-500 mt-2">
                      Click below to analyze your drawings and extract manufacturing specifications
                    </p>
                  </>
                )}
              </div>

              <div className="flex justify-between pt-4">
                <Button variant="outline" onClick={() => setStep(2)}>
                  <ArrowLeft className="mr-2 w-4 h-4" /> Back
                </Button>
                <Button 
                  onClick={analyzeDrawings} 
                  disabled={analyzing}
                  className="bg-orange-600 hover:bg-orange-700"
                  data-testid="analyze-btn"
                >
                  {analyzing ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin mr-2" /> Analyzing...
                    </>
                  ) : (
                    <>Start Analysis <ArrowRight className="ml-2 w-4 h-4" /></>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Step 4: Vendor Matching */}
        {step === 4 && (
          <Card data-testid="step4-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Target className="w-5 h-5 text-orange-600" />
                Vendor Matching
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Show AI Analysis Summary (read-only) */}
              {analysisResult && (
                <div className="p-4 rounded-lg border border-green-200 bg-green-50">
                  <div className="flex items-center gap-2 mb-3">
                    <CheckCircle2 className="w-5 h-5 text-green-600" />
                    <h3 className="font-semibold text-slate-900">Analysis Summary</h3>
                    {imageType && (
                      <span data-testid="image-type-badge" className={`ml-auto inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1 rounded-full border ${
                        imageType === "reference_photo"
                          ? "bg-purple-50 text-purple-700 border-purple-200"
                          : "bg-blue-50 text-blue-700 border-blue-200"
                      }`}>
                        {imageType === "reference_photo" ? (
                          <><Camera className="w-3 h-3" /> Reference Photo</>
                        ) : (
                          <><Cpu className="w-3 h-3" /> Technical Drawing</>
                        )}
                      </span>
                    )}
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                    {analysisResult.overall_dimensions && (
                      <div className="p-2 bg-white rounded border">
                        <p className="text-xs text-slate-500 font-medium">Dimensions</p>
                        <p className="text-slate-800 font-mono text-xs">
                          {Object.entries(analysisResult.overall_dimensions)
                            .filter(([, v]) => v)
                            .map(([k, v]) => `${k}: ${v}mm`)
                            .join(', ') || 'Extracted'}
                        </p>
                      </div>
                    )}
                    {analysisResult.complexity_score && (
                      <div className="p-2 bg-white rounded border">
                        <p className="text-xs text-slate-500 font-medium">Complexity</p>
                        <p className="text-slate-800">{analysisResult.complexity_score}/10</p>
                      </div>
                    )}
                    {analysisResult.recommended_processes?.length > 0 && (
                      <div className="p-2 bg-white rounded border col-span-2">
                        <p className="text-xs text-slate-500 font-medium">Processes</p>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {analysisResult.recommended_processes.map((p, i) => (
                            <span key={i} className="px-1.5 py-0.5 bg-blue-50 text-blue-600 text-xs rounded">{p}</span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Matching Status */}
              <div className="text-center py-4">
                {matching ? (
                  <>
                    <div className="w-12 h-12 mx-auto mb-3 relative">
                      <Target className="w-12 h-12 text-orange-600 animate-pulse" />
                    </div>
                    <p className="text-lg font-medium text-slate-900">
                      {imageType === "reference_photo" ? "Matching with Vendor Portfolios..." : "Finding Best Vendors..."}
                    </p>
                    <p className="text-slate-500 mt-1 text-sm">
                      {imageType === "reference_photo"
                        ? "Comparing your part photos with vendor portfolio items to find the best fit" 
                        : "Matching your requirements with capable manufacturers"}
                    </p>
                  </>
                ) : noMatchesFound ? (
                  <>
                    <div className="w-16 h-16 mx-auto mb-4 bg-amber-50 rounded-full flex items-center justify-center">
                      <Search className="w-8 h-8 text-amber-500" />
                    </div>
                    <p className="text-lg font-medium text-slate-900">No Exact Matches Right Now</p>
                    <p className="text-slate-500 mt-2 text-sm max-w-md mx-auto">
                      Don't worry — your RFQ is now live on the marketplace. Vendors can discover it and submit quotes directly. We'll notify you as soon as a vendor responds.
                    </p>
                    <div className="mt-4 flex items-center justify-center gap-3">
                      <Button 
                        variant="outline"
                        onClick={() => navigate(`/buyer/rfq/${rfqId}`)}
                        data-testid="view-rfq-btn"
                      >
                        View RFQ Details
                      </Button>
                      <Button 
                        onClick={() => navigate('/buyer/rfqs')}
                        className="bg-orange-600 hover:bg-orange-700"
                        data-testid="go-to-rfqs-btn"
                      >
                        Go to My RFQs
                      </Button>
                    </div>
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-12 h-12 text-green-500 mx-auto mb-3" />
                    <p className="text-lg font-medium text-slate-900">Ready to Match!</p>
                    <p className="text-slate-500 mt-1 text-sm">
                      {imageType === "reference_photo"
                        ? "We'll match your part photos against vendor portfolios to find the best manufacturers"
                        : "All specifications confirmed — proceed to find matching vendors"}
                    </p>
                  </>
                )}
              </div>

              {!noMatchesFound && (
                <div className="flex justify-between pt-4">
                  <Button variant="outline" onClick={() => setStep(3)}>
                    <ArrowLeft className="mr-2 w-4 h-4" /> Back
                  </Button>
                  <Button 
                    onClick={matchVendors} 
                    disabled={matching}
                    className="bg-orange-600 hover:bg-orange-700 px-8"
                    data-testid="match-btn"
                  >
                    {matching ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin mr-2" /> Matching...
                      </>
                    ) : (
                      <>Find Matching Vendors <Target className="ml-2 w-4 h-4" /></>
                    )}
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </DashboardLayout>
  );
};

export default CreateRFQ;
