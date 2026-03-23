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
  AlertTriangle, Ruler, Scale, MapPin, Truck, Globe, Building2, Clock, Zap, Shield
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
  
  // AI Analysis results
  const [analysisResult, setAnalysisResult] = useState(null);
  const [dimensionsMissing, setDimensionsMissing] = useState(false);
  const [missingFields, setMissingFields] = useState({});
  const [requiredDimensions, setRequiredDimensions] = useState([]);
  const [partGeometry, setPartGeometry] = useState("rectangular");
  const [savingDimensions, setSavingDimensions] = useState(false);
  
  // Manual dimensions input - supports all geometry types
  const [manualDimensions, setManualDimensions] = useState({
    // Rectangular
    length: "",
    width: "",
    height: "",
    // Cylindrical/Circular
    diameter: "",
    outer_diameter: "",
    inner_diameter: "",
    thickness: "",
    // Conical
    large_diameter: "",
    small_diameter: "",
    taper_angle: "",
    // Sheet metal
    bend_radius: "",
    bend_angle: "",
    // Common
    weight: ""
  });
  
  // Geometry type options
  const GEOMETRY_TYPES = [
    { value: "rectangular", label: "Rectangular (Block, Bracket, Housing)" },
    { value: "cylindrical", label: "Cylindrical (Shaft, Pin, Bushing)" },
    { value: "circular_flat", label: "Circular Flat (Disc, Flange, Plate)" },
    { value: "conical", label: "Conical (Tapered Part)" },
    { value: "tube_pipe", label: "Tube/Pipe" },
    { value: "sheet_metal", label: "Sheet Metal" },
    { value: "complex", label: "Complex Geometry" }
  ];
  
  // Get dimension fields based on geometry type
  const getDimensionFields = (geometry) => {
    const fields = {
      rectangular: [
        { key: "length", label: "Length (mm)", required: true },
        { key: "width", label: "Width (mm)", required: true },
        { key: "height", label: "Height (mm)", required: true }
      ],
      cylindrical: [
        { key: "diameter", label: "Diameter (mm)", required: true },
        { key: "length", label: "Length (mm)", required: true },
        { key: "inner_diameter", label: "Inner Diameter (mm)", required: false }
      ],
      circular_flat: [
        { key: "diameter", label: "Diameter (mm)", required: true },
        { key: "thickness", label: "Thickness (mm)", required: true },
        { key: "inner_diameter", label: "Bore/Inner Diameter (mm)", required: false }
      ],
      conical: [
        { key: "large_diameter", label: "Large Diameter (mm)", required: true },
        { key: "small_diameter", label: "Small Diameter (mm)", required: true },
        { key: "length", label: "Length (mm)", required: true },
        { key: "taper_angle", label: "Taper Angle (°)", required: false }
      ],
      tube_pipe: [
        { key: "outer_diameter", label: "Outer Diameter (mm)", required: true },
        { key: "inner_diameter", label: "Inner Diameter (mm)", required: true },
        { key: "length", label: "Length (mm)", required: true }
      ],
      sheet_metal: [
        { key: "length", label: "Length (mm)", required: true },
        { key: "width", label: "Width (mm)", required: true },
        { key: "thickness", label: "Thickness (mm)", required: true },
        { key: "bend_angle", label: "Bend Angle (°)", required: false }
      ],
      complex: [
        { key: "length", label: "Max Length (mm)", required: false },
        { key: "width", label: "Max Width (mm)", required: false },
        { key: "height", label: "Max Height (mm)", required: false },
        { key: "diameter", label: "Max Diameter (mm)", required: false }
      ]
    };
    return fields[geometry] || fields.rectangular;
  };

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
        dimensions_missing, 
        missing_fields, 
        part_geometry, 
        required_dimensions,
        analyzed_count,
        analyzed_files,
        skipped_cad_files,
        note
      } = response.data;
      
      setAnalysisResult(analysis);
      setDimensionsMissing(dimensions_missing);
      setMissingFields(missing_fields || {});
      setPartGeometry(part_geometry || analysis?.part_geometry || "rectangular");
      setRequiredDimensions(required_dimensions || []);
      
      // Pre-fill manual dimensions with any extracted values
      const dims = analysis?.overall_dimensions || {};
      setManualDimensions(prev => ({
        ...prev,
        length: dims.length || "",
        width: dims.width || "",
        height: dims.height || "",
        diameter: dims.diameter || "",
        outer_diameter: dims.outer_diameter || "",
        inner_diameter: dims.inner_diameter || "",
        thickness: dims.thickness || "",
        large_diameter: dims.large_diameter || "",
        small_diameter: dims.small_diameter || "",
        taper_angle: dims.taper_angle || "",
        bend_radius: dims.bend_radius || "",
        bend_angle: dims.bend_angle || "",
        weight: analysis?.weight_kg || ""
      }));
      
      // Show appropriate messages based on analysis results
      if (analyzed_count === 0) {
        toast.warning(note || "No drawings could be analyzed. Please add PDF or image files.");
      } else if (skipped_cad_files?.length > 0) {
        toast.info(`Analyzed ${analyzed_count} drawing(s). ${skipped_cad_files.length} CAD file(s) kept as attachments.`);
      }
      
      if (dimensions_missing && analyzed_count > 0) {
        toast.warning("Some dimensions couldn't be extracted. Please review and fill in missing values.");
      } else if (analyzed_count > 0) {
        toast.success(`AI analysis complete - analyzed ${analyzed_count} drawing(s)!`);
      }
      setStep(4);
    } catch (error) {
      const errorMessage = error.response?.data?.detail || error.response?.data?.analysis?.error || "Analysis failed";
      
      // Check if it's a file format error
      if (errorMessage.includes("CAD format") || errorMessage.includes("DWG") || errorMessage.includes("STEP")) {
        toast.error(errorMessage, { duration: 8000 });
        // Don't proceed to step 4 for file format errors
        return;
      }
      
      toast.error("Analysis failed, but continuing with matching");
      setDimensionsMissing(true);
      setMissingFields({ length: true, width: true, height: true });
      setPartGeometry("rectangular");
      setStep(4);
    } finally {
      setAnalyzing(false);
    }
  };

  const saveManualDimensions = async () => {
    // Get required fields for current geometry
    const fields = getDimensionFields(partGeometry);
    const requiredFields = fields.filter(f => f.required);
    
    // Validate required fields have values
    const missingRequired = requiredFields.filter(f => !manualDimensions[f.key]);
    if (missingRequired.length > 0) {
      toast.error(`Please provide: ${missingRequired.map(f => f.label).join(", ")}`);
      return;
    }
    
    setSavingDimensions(true);
    try {
      // Build dimension payload based on geometry
      const payload = {
        part_geometry: partGeometry,
        weight: parseFloat(manualDimensions.weight) || null
      };
      
      // Add all dimension fields that have values
      const allDimFields = ["length", "width", "height", "diameter", "outer_diameter", 
                           "inner_diameter", "thickness", "large_diameter", "small_diameter",
                           "taper_angle", "bend_radius", "bend_angle"];
      
      allDimFields.forEach(field => {
        if (manualDimensions[field]) {
          payload[field] = parseFloat(manualDimensions[field]);
        }
      });
      
      const response = await api.put(`/rfqs/${rfqId}/dimensions`, payload);
      
      toast.success("Dimensions saved successfully!");
      setDimensionsMissing(false);
      setMissingFields({});
      
      // Update analysis result with new dimensions
      setAnalysisResult(prev => ({
        ...prev,
        part_geometry: response.data.part_geometry,
        overall_dimensions: response.data.overall_dimensions,
        max_dimension_mm: response.data.max_dimension_mm,
        max_diameter_mm: response.data.max_diameter_mm
      }));
    } catch (error) {
      toast.error("Failed to save dimensions");
    } finally {
      setSavingDimensions(false);
    }
  };

  const matchVendors = async () => {
    setMatching(true);
    try {
      await api.post(`/rfqs/${rfqId}/match`);
      toast.success("Vendors matched successfully");
      navigate(`/buyer/rfq/${rfqId}`);
    } catch (error) {
      toast.error("Matching failed");
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

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    Tolerance (mm)
                  </Label>
                  <Input
                    type="number"
                    step="0.01"
                    min={0.01}
                    value={formData.tolerance}
                    onChange={(e) => handleInputChange("tolerance", parseFloat(e.target.value) || 0.1)}
                    className="mt-1"
                    data-testid="tolerance-input"
                  />
                </div>

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

        {/* Step 4: Review Analysis & Vendor Matching */}
        {step === 4 && (
          <Card className="border-slate-200">
            <CardHeader>
              <CardTitle className="font-heading text-xl">
                {dimensionsMissing ? "Review & Complete Specifications" : "Vendor Matching"}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Show AI Analysis Results */}
              {analysisResult && (
                <div className="space-y-4">
                  {/* Part Geometry & Dimensions Section */}
                  <div className={`p-4 rounded-lg border-2 ${dimensionsMissing ? 'border-amber-400 bg-amber-50' : 'border-green-400 bg-green-50'}`}>
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        {dimensionsMissing ? (
                          <AlertTriangle className="w-5 h-5 text-amber-600" />
                        ) : (
                          <CheckCircle2 className="w-5 h-5 text-green-600" />
                        )}
                        <h3 className="font-semibold text-slate-900">
                          {dimensionsMissing ? "Dimensions - Action Required" : "Extracted Dimensions"}
                        </h3>
                      </div>
                      {/* Detected Geometry Badge */}
                      <span className="px-3 py-1 bg-blue-100 text-blue-700 text-xs font-medium rounded-full">
                        {GEOMETRY_TYPES.find(g => g.value === partGeometry)?.label || partGeometry}
                      </span>
                    </div>
                    
                    {dimensionsMissing && (
                      <p className="text-sm text-amber-700 mb-4">
                        We couldn't extract all dimensions from your drawing. Please select the correct geometry type and provide the missing values.
                      </p>
                    )}
                    
                    {/* Geometry Type Selector (when dimensions missing) */}
                    {dimensionsMissing && (
                      <div className="mb-4">
                        <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                          Part Geometry Type
                        </Label>
                        <Select
                          value={partGeometry}
                          onValueChange={(value) => {
                            setPartGeometry(value);
                            // Update missing fields based on new geometry
                            const fields = getDimensionFields(value);
                            const newMissing = {};
                            fields.filter(f => f.required).forEach(f => {
                              newMissing[f.key] = !manualDimensions[f.key];
                            });
                            setMissingFields(newMissing);
                          }}
                        >
                          <SelectTrigger className="mt-1 w-full md:w-1/2" data-testid="geometry-select">
                            <SelectValue placeholder="Select geometry type" />
                          </SelectTrigger>
                          <SelectContent>
                            {GEOMETRY_TYPES.map((g) => (
                              <SelectItem key={g.value} value={g.value}>{g.label}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    )}
                    
                    {/* Dynamic Dimension Fields based on Geometry */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      {getDimensionFields(partGeometry).map((field) => (
                        <div key={field.key}>
                          <Label className={`text-xs font-bold uppercase tracking-wider ${missingFields[field.key] ? 'text-red-600' : 'text-slate-500'}`}>
                            <Ruler className="w-3 h-3 inline mr-1" />
                            {field.label} {field.required && missingFields[field.key] && <span className="text-red-500">*</span>}
                          </Label>
                          <Input
                            type="number"
                            step="0.1"
                            min="0"
                            value={manualDimensions[field.key] || ""}
                            onChange={(e) => setManualDimensions(prev => ({ ...prev, [field.key]: e.target.value }))}
                            className={`mt-1 ${missingFields[field.key] ? 'border-red-400 focus:border-red-500' : ''}`}
                            placeholder={field.required && missingFields[field.key] ? "Required" : "Optional"}
                            data-testid={`dimension-${field.key}`}
                          />
                        </div>
                      ))}
                      {/* Weight is always shown */}
                      <div>
                        <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                          <Scale className="w-3 h-3 inline mr-1" />
                          Weight (kg)
                        </Label>
                        <Input
                          type="number"
                          step="0.1"
                          min="0"
                          value={manualDimensions.weight}
                          onChange={(e) => setManualDimensions(prev => ({ ...prev, weight: e.target.value }))}
                          className="mt-1"
                          placeholder="Optional"
                          data-testid="dimension-weight"
                        />
                      </div>
                    </div>
                    
                    {dimensionsMissing && (
                      <div className="mt-4 flex justify-end">
                        <Button
                          onClick={saveManualDimensions}
                          disabled={savingDimensions}
                          className="bg-amber-600 hover:bg-amber-700"
                          data-testid="save-dimensions-btn"
                        >
                          {savingDimensions ? (
                            <Loader2 className="w-4 h-4 animate-spin mr-2" />
                          ) : (
                            <CheckCircle2 className="w-4 h-4 mr-2" />
                          )}
                          Save Dimensions
                        </Button>
                      </div>
                    )}
                  </div>
                  
                  {/* Other Extracted Specs */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Recommended Processes */}
                    {analysisResult.recommended_processes?.length > 0 && (
                      <div className="p-4 rounded-lg bg-slate-50 border border-slate-200">
                        <h4 className="text-sm font-semibold text-slate-700 mb-2">Recommended Processes</h4>
                        <div className="flex flex-wrap gap-2">
                          {analysisResult.recommended_processes.map((process, idx) => (
                            <span key={idx} className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-full">
                              {process}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    {/* Complexity & Time Estimate */}
                    <div className="p-4 rounded-lg bg-slate-50 border border-slate-200">
                      <h4 className="text-sm font-semibold text-slate-700 mb-2">Complexity Analysis</h4>
                      <div className="space-y-1 text-sm">
                        <p className="text-slate-600">
                          <span className="font-medium">Complexity Score:</span> {analysisResult.complexity_score || "N/A"}/10
                        </p>
                        <p className="text-slate-600">
                          <span className="font-medium">Est. Machining Time:</span> {analysisResult.estimated_machining_time_hours || "N/A"} hours
                        </p>
                        {analysisResult.material_specs && (
                          <p className="text-slate-600">
                            <span className="font-medium">Material:</span> {analysisResult.material_specs}
                          </p>
                        )}
                      </div>
                    </div>
                    
                    {/* Holes & Threads */}
                    {(analysisResult.holes?.length > 0 || analysisResult.threads?.length > 0) && (
                      <div className="p-4 rounded-lg bg-slate-50 border border-slate-200">
                        <h4 className="text-sm font-semibold text-slate-700 mb-2">Features Detected</h4>
                        <div className="space-y-1 text-sm text-slate-600">
                          {analysisResult.holes?.length > 0 && (
                            <p>{analysisResult.holes.length} hole(s) detected</p>
                          )}
                          {analysisResult.threads?.length > 0 && (
                            <p>{analysisResult.threads.length} threaded feature(s)</p>
                          )}
                        </div>
                      </div>
                    )}
                    
                    {/* Special Requirements */}
                    {analysisResult.special_requirements?.length > 0 && (
                      <div className="p-4 rounded-lg bg-slate-50 border border-slate-200">
                        <h4 className="text-sm font-semibold text-slate-700 mb-2">Special Requirements</h4>
                        <ul className="list-disc list-inside text-sm text-slate-600 space-y-1">
                          {analysisResult.special_requirements.map((req, idx) => (
                            <li key={idx}>{req}</li>
                          ))}
                        </ul>
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
                    <p className="text-lg font-medium text-slate-900">Finding Best Vendors...</p>
                    <p className="text-slate-500 mt-1 text-sm">
                      Matching your requirements with capable manufacturers
                    </p>
                  </>
                ) : !dimensionsMissing ? (
                  <>
                    <CheckCircle2 className="w-12 h-12 text-green-500 mx-auto mb-3" />
                    <p className="text-lg font-medium text-slate-900">Ready to Match!</p>
                    <p className="text-slate-500 mt-1 text-sm">
                      All specifications confirmed - proceed to find matching vendors
                    </p>
                  </>
                ) : (
                  <>
                    <AlertTriangle className="w-12 h-12 text-amber-500 mx-auto mb-3" />
                    <p className="text-lg font-medium text-slate-900">Complete Dimensions Above</p>
                    <p className="text-slate-500 mt-1 text-sm">
                      Save the dimensions to enable accurate vendor matching
                    </p>
                  </>
                )}
              </div>

              <div className="flex justify-between pt-4">
                <Button variant="outline" onClick={() => setStep(3)}>
                  <ArrowLeft className="mr-2 w-4 h-4" /> Back
                </Button>
                <Button 
                  onClick={matchVendors} 
                  disabled={matching || dimensionsMissing}
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
            </CardContent>
          </Card>
        )}
      </div>
    </DashboardLayout>
  );
};

export default CreateRFQ;
