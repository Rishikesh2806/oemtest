import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth, api } from "../App";
import DashboardLayout from "../components/layout/DashboardLayout";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { toast } from "sonner";
import { 
  Upload, FileText, ArrowRight, ArrowLeft, 
  CheckCircle2, Loader2, X, Cpu, Target, Package,
  AlertTriangle, Ruler, Scale
} from "lucide-react";

const MATERIALS = [
  "Aluminum", "Steel", "Stainless Steel", "Carbon Steel", 
  "Brass", "Copper", "Titanium", "Plastic/Nylon", "ABS", "Other"
];

const SURFACE_FINISHES = [
  "As Machined", "Anodized", "Powder Coated", "Painted",
  "Polished", "Brushed", "Chrome Plated", "Zinc Plated", "None"
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
  
  // AI Analysis results
  const [analysisResult, setAnalysisResult] = useState(null);
  const [dimensionsMissing, setDimensionsMissing] = useState(false);
  const [missingFields, setMissingFields] = useState({});
  const [savingDimensions, setSavingDimensions] = useState(false);
  
  // Manual dimensions input
  const [manualDimensions, setManualDimensions] = useState({
    length: "",
    width: "",
    height: "",
    weight: ""
  });

  const [formData, setFormData] = useState({
    title: "",
    description: "",
    material_type: "",
    quantity: 1,
    tolerance: 0.1,
    surface_finish: "",
    supply_type: "vendor_material",
    deadline: "",
    preferred_payment_terms: "net_30",
    payment_terms_notes: ""
  });

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

    setLoading(true);
    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const formDataUpload = new FormData();
        formDataUpload.append("file", file);

        setUploadProgress(prev => ({ ...prev, [i]: 0 }));

        await api.post(`/rfqs/${rfqId}/drawings`, formDataUpload, {
          headers: { "Content-Type": "multipart/form-data" },
          onUploadProgress: (progressEvent) => {
            const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            setUploadProgress(prev => ({ ...prev, [i]: percent }));
          }
        });
      }
      
      toast.success("Drawings uploaded successfully");
      setStep(3);
    } catch (error) {
      toast.error("Failed to upload drawings");
    } finally {
      setLoading(false);
    }
  };

  const analyzeDrawings = async () => {
    setAnalyzing(true);
    try {
      const response = await api.post(`/rfqs/${rfqId}/analyze`);
      const { analysis, dimensions_missing, missing_fields } = response.data;
      
      setAnalysisResult(analysis);
      setDimensionsMissing(dimensions_missing);
      setMissingFields(missing_fields || {});
      
      // Pre-fill manual dimensions with any extracted values
      const dims = analysis?.overall_dimensions || {};
      setManualDimensions({
        length: dims.length || "",
        width: dims.width || "",
        height: dims.height || "",
        weight: analysis?.weight_kg || ""
      });
      
      if (dimensions_missing) {
        toast.warning("Some dimensions couldn't be extracted. Please review and fill in missing values.");
      } else {
        toast.success("AI analysis complete - all dimensions extracted!");
      }
      setStep(4);
    } catch (error) {
      toast.error("Analysis failed, but continuing with matching");
      setDimensionsMissing(true);
      setMissingFields({ length: true, width: true, height: true });
      setStep(4);
    } finally {
      setAnalyzing(false);
    }
  };

  const saveManualDimensions = async () => {
    // Validate that at least length and width are provided
    if (!manualDimensions.length || !manualDimensions.width) {
      toast.error("Please provide at least Length and Width dimensions");
      return;
    }
    
    setSavingDimensions(true);
    try {
      const response = await api.put(`/rfqs/${rfqId}/dimensions`, {
        length: parseFloat(manualDimensions.length) || null,
        width: parseFloat(manualDimensions.width) || null,
        height: parseFloat(manualDimensions.height) || null,
        weight: parseFloat(manualDimensions.weight) || null
      });
      
      toast.success("Dimensions saved successfully!");
      setDimensionsMissing(false);
      setMissingFields({});
      
      // Update analysis result with new dimensions
      setAnalysisResult(prev => ({
        ...prev,
        overall_dimensions: response.data.overall_dimensions,
        max_dimension_mm: response.data.max_dimension_mm
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
                  Supports PDF, STEP, DWG, DXF, PNG, JPG
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
                <Button variant="outline" onClick={() => setStep(1)}>
                  <ArrowLeft className="mr-2 w-4 h-4" /> Back
                </Button>
                <Button 
                  onClick={uploadFiles} 
                  disabled={loading || files.length === 0}
                  className="bg-orange-600 hover:bg-orange-700"
                  data-testid="upload-btn"
                >
                  {loading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <>Upload & Continue <ArrowRight className="ml-2 w-4 h-4" /></>
                  )}
                </Button>
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
                  {/* Dimensions Section */}
                  <div className={`p-4 rounded-lg border-2 ${dimensionsMissing ? 'border-amber-400 bg-amber-50' : 'border-green-400 bg-green-50'}`}>
                    <div className="flex items-center gap-2 mb-3">
                      {dimensionsMissing ? (
                        <AlertTriangle className="w-5 h-5 text-amber-600" />
                      ) : (
                        <CheckCircle2 className="w-5 h-5 text-green-600" />
                      )}
                      <h3 className="font-semibold text-slate-900">
                        {dimensionsMissing ? "Dimensions - Action Required" : "Extracted Dimensions"}
                      </h3>
                    </div>
                    
                    {dimensionsMissing && (
                      <p className="text-sm text-amber-700 mb-4">
                        We couldn't extract all dimensions from your drawing. Please provide the missing values below for accurate vendor matching.
                      </p>
                    )}
                    
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div>
                        <Label className={`text-xs font-bold uppercase tracking-wider ${missingFields.length ? 'text-red-600' : 'text-slate-500'}`}>
                          <Ruler className="w-3 h-3 inline mr-1" />
                          Length (mm) {missingFields.length && <span className="text-red-500">*</span>}
                        </Label>
                        <Input
                          type="number"
                          step="0.1"
                          min="0"
                          value={manualDimensions.length}
                          onChange={(e) => setManualDimensions(prev => ({ ...prev, length: e.target.value }))}
                          className={`mt-1 ${missingFields.length ? 'border-red-400 focus:border-red-500' : ''}`}
                          placeholder={missingFields.length ? "Required" : ""}
                          data-testid="dimension-length"
                        />
                      </div>
                      <div>
                        <Label className={`text-xs font-bold uppercase tracking-wider ${missingFields.width ? 'text-red-600' : 'text-slate-500'}`}>
                          <Ruler className="w-3 h-3 inline mr-1" />
                          Width (mm) {missingFields.width && <span className="text-red-500">*</span>}
                        </Label>
                        <Input
                          type="number"
                          step="0.1"
                          min="0"
                          value={manualDimensions.width}
                          onChange={(e) => setManualDimensions(prev => ({ ...prev, width: e.target.value }))}
                          className={`mt-1 ${missingFields.width ? 'border-red-400 focus:border-red-500' : ''}`}
                          placeholder={missingFields.width ? "Required" : ""}
                          data-testid="dimension-width"
                        />
                      </div>
                      <div>
                        <Label className={`text-xs font-bold uppercase tracking-wider ${missingFields.height ? 'text-red-600' : 'text-slate-500'}`}>
                          <Ruler className="w-3 h-3 inline mr-1" />
                          Height (mm) {missingFields.height && <span className="text-red-500">*</span>}
                        </Label>
                        <Input
                          type="number"
                          step="0.1"
                          min="0"
                          value={manualDimensions.height}
                          onChange={(e) => setManualDimensions(prev => ({ ...prev, height: e.target.value }))}
                          className={`mt-1 ${missingFields.height ? 'border-red-400 focus:border-red-500' : ''}`}
                          placeholder={missingFields.height ? "Required" : ""}
                          data-testid="dimension-height"
                        />
                      </div>
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
