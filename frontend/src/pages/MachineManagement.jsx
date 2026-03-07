import { useState, useEffect } from "react";
import { useAuth, api } from "../App";
import DashboardLayout from "../components/layout/DashboardLayout";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogClose } from "../components/ui/dialog";
import { toast } from "sonner";
import { 
  Plus, Wrench, Loader2, Edit2, Trash2, 
  Cog, Maximize2, Settings, CheckCircle2, Clock, AlertTriangle, Power,
  Upload, Download, FileSpreadsheet, X, Check, Image, Camera
} from "lucide-react";

const MATERIALS = [
  "Aluminum", "Steel", "Stainless Steel", "Carbon Steel",
  "Brass", "Copper", "Titanium", "Inconel", "Plastic", "Other"
];

const emptyMachine = {
  name: "",
  machine_category: "",
  machine_type: "",
  brand: "",
  model: "",
  tolerance: 0.01,
  max_x: 0,
  max_y: 0,
  max_z: 0,
  max_diameter: 0,
  max_length: 0,
  max_swing: 0,
  bore_diameter: 0,
  outer_diameter: 0,
  max_thickness: 0,
  tonnage: 0,
  max_taper_angle: 0,
  materials_supported: [],
  monthly_capacity_hours: 160,
  images: []
};

const MachineManagement = () => {
  const [machines, setMachines] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingMachine, setEditingMachine] = useState(null);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState(emptyMachine);
  const [machineCategories, setMachineCategories] = useState({});
  
  // Availability management
  const [availabilityDialogOpen, setAvailabilityDialogOpen] = useState(false);
  const [selectedMachine, setSelectedMachine] = useState(null);
  const [availabilityData, setAvailabilityData] = useState({
    availability_status: "available",
    engaged_until: "",
    availability_note: ""
  });
  const [updatingAvailability, setUpdatingAvailability] = useState(false);
  
  // Availability summary
  const [availabilitySummary, setAvailabilitySummary] = useState({
    available: 0, engaged: 0, maintenance: 0, offline: 0, total: 0
  });

  // Bulk import state
  const [bulkImportDialogOpen, setBulkImportDialogOpen] = useState(false);
  const [bulkImportFile, setBulkImportFile] = useState(null);
  const [bulkImportLoading, setBulkImportLoading] = useState(false);
  const [bulkImportResult, setBulkImportResult] = useState(null);
  const [dragOver, setDragOver] = useState(false);

  // Image upload state
  const [imageDialogOpen, setImageDialogOpen] = useState(false);
  const [selectedMachineForImage, setSelectedMachineForImage] = useState(null);
  const [uploadingImage, setUploadingImage] = useState(false);
  const [imagePreview, setImagePreview] = useState(null);

  useEffect(() => {
    fetchMachines();
    fetchCategories();
  }, []);

  const fetchMachines = async () => {
    try {
      const response = await api.get("/machines");
      setMachines(response.data);
      // Calculate availability summary
      const summary = { available: 0, engaged: 0, maintenance: 0, offline: 0, total: response.data.length };
      response.data.forEach(m => {
        const status = m.availability_status || "available";
        if (summary[status] !== undefined) summary[status]++;
      });
      setAvailabilitySummary(summary);
    } catch (error) {
      toast.error("Failed to load machines");
    } finally {
      setLoading(false);
    }
  };

  const fetchCategories = async () => {
    try {
      const response = await api.get("/machine-categories");
      setMachineCategories(response.data);
    } catch (error) {
      console.error("Failed to load categories");
    }
  };

  // Open availability dialog
  const openAvailabilityDialog = (machine) => {
    setSelectedMachine(machine);
    setAvailabilityData({
      availability_status: machine.availability_status || "available",
      engaged_until: machine.engaged_until || "",
      availability_note: machine.availability_note || ""
    });
    setAvailabilityDialogOpen(true);
  };

  // Update machine availability
  const updateAvailability = async () => {
    if (!selectedMachine) return;
    setUpdatingAvailability(true);
    try {
      await api.put(`/machines/${selectedMachine.machine_id}/availability`, availabilityData);
      toast.success("Machine availability updated");
      setAvailabilityDialogOpen(false);
      fetchMachines();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to update availability");
    } finally {
      setUpdatingAvailability(false);
    }
  };

  // Get availability badge
  const getAvailabilityBadge = (machine) => {
    const status = machine.availability_status || "available";
    const badges = {
      available: { icon: CheckCircle2, color: "bg-green-100 text-green-700", label: "Available" },
      engaged: { icon: Clock, color: "bg-blue-100 text-blue-700", label: "Engaged" },
      maintenance: { icon: AlertTriangle, color: "bg-yellow-100 text-yellow-700", label: "Maintenance" },
      offline: { icon: Power, color: "bg-gray-100 text-gray-500", label: "Offline" }
    };
    return badges[status] || badges.available;
  };

  // Get dimension fields based on selected category
  const getDimensionFields = () => {
    if (!formData.machine_category || !machineCategories[formData.machine_category]) {
      return [];
    }
    return machineCategories[formData.machine_category].dimension_fields || [];
  };

  // Get machine types for selected category
  const getMachineTypes = () => {
    if (!formData.machine_category || !machineCategories[formData.machine_category]) {
      return [];
    }
    return machineCategories[formData.machine_category].types || [];
  };

  // Detect category from machine type
  const detectCategoryFromType = (machineType) => {
    for (const [category, data] of Object.entries(machineCategories)) {
      if (data.types?.includes(machineType)) {
        return category;
      }
    }
    return "";
  };

  // Get display dimensions based on machine category/type
  const getMachineDimensions = (machine) => {
    const dims = [];
    const cat = detectCategoryFromType(machine.machine_type) || machine.machine_category;
    
    if (cat === "Turning/Lathe") {
      if (machine.max_length) dims.push(`L: ${machine.max_length}mm`);
      if (machine.max_diameter) dims.push(`Ø: ${machine.max_diameter}mm`);
      if (machine.max_swing) dims.push(`Swing: ${machine.max_swing}mm`);
    } else if (cat === "Boring") {
      if (machine.bore_diameter) dims.push(`Bore Ø: ${machine.bore_diameter}mm`);
      if (machine.outer_diameter) dims.push(`OD: ${machine.outer_diameter}mm`);
      if (machine.max_length) dims.push(`L: ${machine.max_length}mm`);
    } else if (cat === "Sheet Metal" || cat === "Welding") {
      if (machine.max_length) dims.push(`L: ${machine.max_length}mm`);
      if (machine.max_thickness) dims.push(`T: ${machine.max_thickness}mm`);
      if (machine.tonnage) dims.push(`${machine.tonnage}T`);
    } else if (cat === "Cutting") {
      if (machine.max_x) dims.push(`X: ${machine.max_x}mm`);
      if (machine.max_y) dims.push(`Y: ${machine.max_y}mm`);
      if (machine.max_thickness) dims.push(`T: ${machine.max_thickness}mm`);
    } else {
      // Default: Milling/VMC style
      if (machine.max_x || machine.max_y || machine.max_z) {
        dims.push(`${machine.max_x || 0}×${machine.max_y || 0}×${machine.max_z || 0}mm`);
      }
      if (machine.max_diameter) dims.push(`Ø: ${machine.max_diameter}mm`);
    }
    return dims.join(" | ");
  };

  const handleInputChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const toggleMaterial = (material) => {
    setFormData(prev => ({
      ...prev,
      materials_supported: prev.materials_supported.includes(material)
        ? prev.materials_supported.filter(m => m !== material)
        : [...prev.materials_supported, material]
    }));
  };

  const openAddDialog = () => {
    setEditingMachine(null);
    setFormData(emptyMachine);
    setDialogOpen(true);
  };

  const openEditDialog = (machine) => {
    setEditingMachine(machine);
    const detectedCategory = detectCategoryFromType(machine.machine_type) || machine.machine_category || "";
    
    setFormData({
      name: machine.name || `${machine.brand} ${machine.model}`.trim(),
      machine_category: detectedCategory,
      machine_type: machine.machine_type || "",
      brand: machine.brand || "",
      model: machine.model || "",
      tolerance: machine.tolerance || machine.tolerance_capability || 0.01,
      max_x: machine.max_x || 0,
      max_y: machine.max_y || 0,
      max_z: machine.max_z || 0,
      max_diameter: machine.max_diameter || 0,
      max_length: machine.max_length || 0,
      max_swing: machine.max_swing || 0,
      bore_diameter: machine.bore_diameter || 0,
      outer_diameter: machine.outer_diameter || 0,
      max_thickness: machine.max_thickness || 0,
      tonnage: machine.tonnage || 0,
      max_taper_angle: machine.max_taper_angle || 0,
      materials_supported: machine.materials_supported || machine.materials || [],
      monthly_capacity_hours: machine.monthly_capacity_hours || 160
    });
    setDialogOpen(true);
  };

  const handleSubmit = async () => {
    if (!formData.machine_category || !formData.machine_type || !formData.brand || !formData.model) {
      toast.error("Please fill in required fields (Category, Type, Brand, Model)");
      return;
    }

    setSaving(true);
    try {
      const payload = {
        name: formData.name || `${formData.brand} ${formData.model}`,
        machine_category: formData.machine_category,
        machine_type: formData.machine_type,
        brand: formData.brand,
        model: formData.model,
        tolerance: parseFloat(formData.tolerance) || 0.01,
        max_x: parseFloat(formData.max_x) || 0,
        max_y: parseFloat(formData.max_y) || 0,
        max_z: parseFloat(formData.max_z) || 0,
        max_diameter: parseFloat(formData.max_diameter) || 0,
        max_length: parseFloat(formData.max_length) || 0,
        max_swing: parseFloat(formData.max_swing) || 0,
        bore_diameter: parseFloat(formData.bore_diameter) || 0,
        outer_diameter: parseFloat(formData.outer_diameter) || 0,
        max_thickness: parseFloat(formData.max_thickness) || 0,
        tonnage: parseFloat(formData.tonnage) || 0,
        max_taper_angle: parseFloat(formData.max_taper_angle) || 0,
        materials_supported: formData.materials_supported,
        monthly_capacity_hours: parseInt(formData.monthly_capacity_hours) || 160
      };

      if (editingMachine) {
        await api.put(`/machines/${editingMachine.machine_id}`, payload);
        toast.success("Machine updated successfully");
      } else {
        await api.post("/machines", payload);
        toast.success("Machine added successfully");
      }
      
      setDialogOpen(false);
      fetchMachines();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to save machine");
    } finally {
      setSaving(false);
    }
  };

  const deleteMachine = async (machineId) => {
    if (!confirm("Are you sure you want to delete this machine?")) return;

    try {
      await api.delete(`/machines/${machineId}`);
      toast.success("Machine deleted");
      fetchMachines();
    } catch (error) {
      toast.error("Failed to delete machine");
    }
  };

  // Bulk import functions
  const downloadTemplate = async () => {
    try {
      const response = await api.get("/machines/bulk-import/template");
      const template = response.data.template;
      
      // Create blob and download
      const blob = new Blob([template], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'machine_import_template.csv';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      toast.success("Template downloaded");
    } catch (error) {
      toast.error("Failed to download template");
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      if (!file.name.endsWith('.csv')) {
        toast.error("Please select a CSV file");
        return;
      }
      setBulkImportFile(file);
      setBulkImportResult(null);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) {
      if (!file.name.endsWith('.csv')) {
        toast.error("Please select a CSV file");
        return;
      }
      setBulkImportFile(file);
      setBulkImportResult(null);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setDragOver(false);
  };

  const uploadBulkImport = async () => {
    if (!bulkImportFile) {
      toast.error("Please select a file first");
      return;
    }

    setBulkImportLoading(true);
    setBulkImportResult(null);

    try {
      const formData = new FormData();
      formData.append('file', bulkImportFile);

      const response = await api.post("/machines/bulk-import", formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      setBulkImportResult(response.data);
      
      if (response.data.successful > 0) {
        toast.success(`Successfully imported ${response.data.successful} machines`);
        fetchMachines();
      }
      
      if (response.data.failed > 0) {
        toast.warning(`${response.data.failed} rows had errors`);
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to import machines");
      setBulkImportResult({
        total_rows: 0,
        successful: 0,
        failed: 1,
        machines_created: [],
        errors: [{ row: 0, errors: [error.response?.data?.detail || "Upload failed"] }]
      });
    } finally {
      setBulkImportLoading(false);
    }
  };

  const resetBulkImport = () => {
    setBulkImportFile(null);
    setBulkImportResult(null);
  };

  // Image management functions
  const openImageDialog = (machine) => {
    setSelectedMachineForImage(machine);
    setImagePreview(null);
    setImageDialogOpen(true);
  };

  const handleImageSelect = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('image/')) {
      toast.error("Please select an image file");
      return;
    }

    // Validate file size (5MB)
    if (file.size > 5 * 1024 * 1024) {
      toast.error("Image must be less than 5MB");
      return;
    }

    // Show preview
    const reader = new FileReader();
    reader.onload = (e) => setImagePreview(e.target.result);
    reader.readAsDataURL(file);

    // Upload image
    await uploadMachineImage(file);
  };

  const uploadMachineImage = async (file) => {
    if (!selectedMachineForImage) return;

    setUploadingImage(true);
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await api.post(
        `/machines/${selectedMachineForImage.machine_id}/images`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      );

      toast.success("Image uploaded successfully");
      
      // Update local state
      setSelectedMachineForImage(prev => ({
        ...prev,
        images: response.data.images
      }));
      
      // Refresh machines list
      fetchMachines();
      setImagePreview(null);
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to upload image");
    } finally {
      setUploadingImage(false);
    }
  };

  const deleteMachineImage = async (imageUrl) => {
    if (!selectedMachineForImage) return;
    if (!confirm("Delete this image?")) return;

    try {
      const response = await api.delete(
        `/machines/${selectedMachineForImage.machine_id}/images`,
        { params: { image_url: imageUrl } }
      );

      toast.success("Image deleted");
      
      // Update local state
      setSelectedMachineForImage(prev => ({
        ...prev,
        images: response.data.images
      }));
      
      fetchMachines();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to delete image");
    }
  };

  const getMachineImages = (machine) => machine.images || [];

  const getMachineName = (machine) => machine.name || `${machine.brand} ${machine.model}`.trim() || "Unnamed Machine";
  const getMachineTolerance = (machine) => machine.tolerance || machine.tolerance_capability || 0;
  const getMachineMaterials = (machine) => machine.materials_supported || machine.materials || [];

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
      <div className="space-y-6" data-testid="machine-management-page">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="font-heading text-2xl font-bold text-slate-900">Machine Management</h1>
            <p className="text-slate-500">Add and manage your manufacturing capabilities</p>
          </div>
          <div className="flex gap-2">
            {/* Bulk Import Button */}
            <Dialog open={bulkImportDialogOpen} onOpenChange={(open) => {
              setBulkImportDialogOpen(open);
              if (!open) resetBulkImport();
            }}>
              <DialogTrigger asChild>
                <Button 
                  variant="outline"
                  className="border-orange-200 text-orange-600 hover:bg-orange-50"
                  data-testid="bulk-import-btn"
                >
                  <Upload className="w-4 h-4 mr-2" /> Bulk Import
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-xl">
                <DialogHeader>
                  <DialogTitle className="flex items-center gap-2">
                    <FileSpreadsheet className="w-5 h-5 text-orange-600" />
                    Bulk Import Machines
                  </DialogTitle>
                </DialogHeader>
                
                <div className="space-y-4 mt-4">
                  {/* Download Template */}
                  <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-slate-800">Step 1: Download Template</p>
                        <p className="text-sm text-slate-500">Get the CSV template with sample data</p>
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={downloadTemplate}
                        data-testid="download-template-btn"
                      >
                        <Download className="w-4 h-4 mr-2" /> Download
                      </Button>
                    </div>
                  </div>

                  {/* Upload Area */}
                  <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
                    <p className="font-medium text-slate-800 mb-2">Step 2: Upload Your CSV</p>
                    
                    {!bulkImportResult ? (
                      <div
                        className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
                          dragOver ? 'border-orange-500 bg-orange-50' : 'border-slate-300 hover:border-orange-400'
                        }`}
                        onDrop={handleDrop}
                        onDragOver={handleDragOver}
                        onDragLeave={handleDragLeave}
                        data-testid="drop-zone"
                      >
                        {bulkImportFile ? (
                          <div className="flex items-center justify-center gap-3">
                            <FileSpreadsheet className="w-8 h-8 text-green-600" />
                            <div className="text-left">
                              <p className="font-medium text-slate-800">{bulkImportFile.name}</p>
                              <p className="text-sm text-slate-500">{(bulkImportFile.size / 1024).toFixed(1)} KB</p>
                            </div>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => setBulkImportFile(null)}
                            >
                              <X className="w-4 h-4" />
                            </Button>
                          </div>
                        ) : (
                          <>
                            <Upload className="w-10 h-10 mx-auto text-slate-400 mb-2" />
                            <p className="text-slate-600">Drag and drop your CSV file here</p>
                            <p className="text-sm text-slate-400 mb-3">or</p>
                            <label>
                              <input
                                type="file"
                                accept=".csv"
                                onChange={handleFileSelect}
                                className="hidden"
                                data-testid="file-input"
                              />
                              <span className="inline-flex items-center px-4 py-2 bg-white border border-slate-300 rounded-md text-sm font-medium text-slate-700 hover:bg-slate-50 cursor-pointer">
                                Browse Files
                              </span>
                            </label>
                          </>
                        )}
                      </div>
                    ) : (
                      /* Import Results */
                      <div className="space-y-3">
                        {/* Summary */}
                        <div className="grid grid-cols-3 gap-3">
                          <div className="p-3 bg-white rounded border text-center">
                            <p className="text-2xl font-bold text-slate-800">{bulkImportResult.total_rows}</p>
                            <p className="text-xs text-slate-500">Total Rows</p>
                          </div>
                          <div className="p-3 bg-green-50 rounded border border-green-200 text-center">
                            <p className="text-2xl font-bold text-green-600">{bulkImportResult.successful}</p>
                            <p className="text-xs text-green-600">Imported</p>
                          </div>
                          <div className="p-3 bg-red-50 rounded border border-red-200 text-center">
                            <p className="text-2xl font-bold text-red-600">{bulkImportResult.failed}</p>
                            <p className="text-xs text-red-600">Failed</p>
                          </div>
                        </div>

                        {/* Errors */}
                        {bulkImportResult.errors?.length > 0 && (
                          <div className="max-h-40 overflow-y-auto bg-red-50 rounded-lg p-3 border border-red-200">
                            <p className="font-medium text-red-700 text-sm mb-2">Errors:</p>
                            {bulkImportResult.errors.map((err, i) => (
                              <div key={i} className="text-xs text-red-600 mb-1">
                                <span className="font-medium">Row {err.row}:</span> {err.errors?.join(", ")}
                              </div>
                            ))}
                          </div>
                        )}

                        {/* Success List */}
                        {bulkImportResult.machines_created?.length > 0 && (
                          <div className="max-h-40 overflow-y-auto bg-green-50 rounded-lg p-3 border border-green-200">
                            <p className="font-medium text-green-700 text-sm mb-2">Machines Created:</p>
                            {bulkImportResult.machines_created.map((m, i) => (
                              <div key={i} className="text-xs text-green-600 mb-1 flex items-center gap-1">
                                <Check className="w-3 h-3" />
                                {m.name} ({m.machine_type})
                              </div>
                            ))}
                          </div>
                        )}

                        <Button
                          variant="outline"
                          size="sm"
                          onClick={resetBulkImport}
                          className="w-full"
                        >
                          Import More
                        </Button>
                      </div>
                    )}
                  </div>

                  {/* Upload Button */}
                  {bulkImportFile && !bulkImportResult && (
                    <Button
                      className="w-full bg-orange-600 hover:bg-orange-700"
                      onClick={uploadBulkImport}
                      disabled={bulkImportLoading}
                      data-testid="upload-btn"
                    >
                      {bulkImportLoading ? (
                        <>
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                          Importing...
                        </>
                      ) : (
                        <>
                          <Upload className="w-4 h-4 mr-2" />
                          Import Machines
                        </>
                      )}
                    </Button>
                  )}

                  {/* Instructions */}
                  <div className="text-xs text-slate-500 space-y-1">
                    <p><strong>CSV Format:</strong> name, machine_category, machine_type, brand, model, dimensions...</p>
                    <p><strong>Required:</strong> machine_type, brand, model</p>
                    <p><strong>Note:</strong> Valid rows are imported, invalid ones are skipped with error details</p>
                  </div>
                </div>
              </DialogContent>
            </Dialog>

            {/* Add Machine Button */}
            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
              <DialogTrigger asChild>
                <Button 
                  onClick={openAddDialog}
                  className="bg-orange-600 hover:bg-orange-700"
                  data-testid="add-machine-btn"
                >
                  <Plus className="w-4 h-4 mr-2" /> Add Machine
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>
                  {editingMachine ? "Edit Machine" : "Add New Machine"}
                </DialogTitle>
              </DialogHeader>
              <div className="space-y-4 mt-4 pr-2">
                {/* Machine Name */}
                <div>
                  <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    Machine Name
                  </Label>
                  <Input
                    value={formData.name}
                    onChange={(e) => handleInputChange("name", e.target.value)}
                    placeholder="e.g., Haas VF-2SS (optional - auto-generated from brand/model)"
                    className="mt-1"
                  />
                </div>

                {/* Machine Category - Primary Selection */}
                <div>
                  <Label className="text-xs font-bold uppercase tracking-wider text-orange-600">
                    Machine Category *
                  </Label>
                  <Select
                    value={formData.machine_category}
                    onValueChange={(value) => handleInputChange("machine_category", value)}
                  >
                    <SelectTrigger className="mt-1 border-orange-200 focus:ring-orange-500" data-testid="machine-category-select">
                      <SelectValue placeholder="Select category first" />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.keys(machineCategories).map((category) => (
                        <SelectItem key={category} value={category}>{category}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  {/* Machine Type - Based on Category */}
                  <div>
                    <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                      Machine Type *
                    </Label>
                    <Select
                      value={formData.machine_type}
                      onValueChange={(value) => handleInputChange("machine_type", value)}
                      disabled={!formData.machine_category}
                    >
                      <SelectTrigger className="mt-1" data-testid="machine-type-select">
                        <SelectValue placeholder={formData.machine_category ? "Select type" : "Select category first"} />
                      </SelectTrigger>
                      <SelectContent>
                        {getMachineTypes().map((type) => (
                          <SelectItem key={type} value={type}>{type}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  
                  {/* Tolerance */}
                  <div>
                    <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                      Tolerance Capability (mm)
                    </Label>
                    <Input
                      type="number"
                      step="0.001"
                      value={formData.tolerance}
                      onChange={(e) => handleInputChange("tolerance", e.target.value)}
                      placeholder="0.01"
                      className="mt-1"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                      Brand *
                    </Label>
                    <Input
                      value={formData.brand}
                      onChange={(e) => handleInputChange("brand", e.target.value)}
                      placeholder="e.g., Mazak, Haas, DMG Mori"
                      className="mt-1"
                      data-testid="machine-brand-input"
                    />
                  </div>
                  <div>
                    <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                      Model *
                    </Label>
                    <Input
                      value={formData.model}
                      onChange={(e) => handleInputChange("model", e.target.value)}
                      placeholder="e.g., VCN-530C"
                      className="mt-1"
                      data-testid="machine-model-input"
                    />
                  </div>
                </div>

                {/* Conditional Dimension Fields Based on Category */}
                {formData.machine_category && getDimensionFields().length > 0 && (
                  <div className="border-t pt-4 mt-4">
                    <Label className="text-xs font-bold uppercase tracking-wider text-orange-600 flex items-center gap-1 mb-3">
                      <Maximize2 className="w-3 h-3" /> {formData.machine_category} Dimensions
                    </Label>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                      {getDimensionFields().map((field) => (
                        <div key={field.key}>
                          <Label className="text-xs text-slate-500">{field.label}</Label>
                          <Input
                            type="number"
                            step={field.key.includes("angle") ? "0.1" : "1"}
                            value={formData[field.key] || 0}
                            onChange={(e) => handleInputChange(field.key, e.target.value)}
                            className="mt-1"
                          />
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div>
                  <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    Monthly Capacity (hours)
                  </Label>
                  <Input
                    type="number"
                    value={formData.monthly_capacity_hours}
                    onChange={(e) => handleInputChange("monthly_capacity_hours", e.target.value)}
                    placeholder="160"
                    className="mt-1"
                  />
                </div>

                <div>
                  <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    Materials Supported
                  </Label>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {MATERIALS.map((material) => (
                      <button
                        key={material}
                        type="button"
                        onClick={() => toggleMaterial(material)}
                        className={`px-3 py-1.5 rounded-sm text-sm font-medium transition-colors ${
                          formData.materials_supported.includes(material)
                            ? "bg-orange-600 text-white"
                            : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                        }`}
                      >
                        {material}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="flex justify-end gap-3 pt-4 border-t">
                  <DialogClose asChild>
                    <Button variant="outline">Cancel</Button>
                  </DialogClose>
                  <Button
                    onClick={handleSubmit}
                    disabled={saving || !formData.machine_category}
                    className="bg-orange-600 hover:bg-orange-700"
                    data-testid="save-machine-btn"
                  >
                    {saving ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <>{editingMachine ? "Update" : "Add"} Machine</>
                    )}
                  </Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>
          </div>
        </div>

        {/* Machines Grid */}
        {machines.length > 0 ? (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {machines.map((machine) => {
              const availBadge = getAvailabilityBadge(machine);
              const AvailIcon = availBadge.icon;
              return (
              <Card key={machine.machine_id} className="border-slate-200 hover:border-orange-200 transition-colors overflow-hidden">
                {/* Machine Image Display */}
                {getMachineImages(machine).length > 0 ? (
                  <div className="relative h-32 bg-slate-100">
                    <img 
                      src={getMachineImages(machine)[0]} 
                      alt={getMachineName(machine)}
                      className="w-full h-full object-cover"
                    />
                    {getMachineImages(machine).length > 1 && (
                      <span className="absolute bottom-2 right-2 bg-black/60 text-white text-xs px-2 py-1 rounded">
                        +{getMachineImages(machine).length - 1} more
                      </span>
                    )}
                    <button
                      onClick={() => openImageDialog(machine)}
                      className="absolute top-2 right-2 bg-white/90 hover:bg-white p-1.5 rounded-full shadow-sm"
                      title="Manage Images"
                    >
                      <Camera className="w-4 h-4 text-slate-600" />
                    </button>
                  </div>
                ) : (
                  <div 
                    className="h-24 bg-slate-50 flex items-center justify-center cursor-pointer hover:bg-slate-100 transition-colors border-b"
                    onClick={() => openImageDialog(machine)}
                  >
                    <div className="text-center">
                      <Camera className="w-6 h-6 text-slate-300 mx-auto mb-1" />
                      <span className="text-xs text-slate-400">Add Photo</span>
                    </div>
                  </div>
                )}
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center">
                        <Cog className="w-5 h-5 text-orange-600" />
                      </div>
                      <div>
                        <CardTitle className="text-base">{getMachineName(machine)}</CardTitle>
                        <p className="text-sm text-slate-500">
                          {machine.machine_type}
                        </p>
                      </div>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      {(machine.machine_category || detectCategoryFromType(machine.machine_type)) && (
                        <span className="text-xs bg-orange-100 text-orange-700 px-2 py-1 rounded">
                          {machine.machine_category || detectCategoryFromType(machine.machine_type)}
                        </span>
                      )}
                      {/* Availability Badge */}
                      <button
                        onClick={() => openAvailabilityDialog(machine)}
                        className={`text-xs ${availBadge.color} px-2 py-1 rounded flex items-center gap-1 hover:opacity-80 transition-opacity`}
                        data-testid={`availability-${machine.machine_id}`}
                      >
                        <AvailIcon className="w-3 h-3" />
                        {availBadge.label}
                      </button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3 text-sm">
                    <div className="flex items-center gap-2">
                      <Settings className="w-4 h-4 text-slate-400" />
                      <span className="text-slate-600">{machine.brand} {machine.model}</span>
                    </div>
                    
                    {getMachineDimensions(machine) && (
                      <div className="flex items-center gap-2">
                        <Maximize2 className="w-4 h-4 text-slate-400" />
                        <span className="text-slate-600">{getMachineDimensions(machine)}</span>
                      </div>
                    )}

                    <div className="text-slate-600">
                      Tolerance: ±{getMachineTolerance(machine)} mm
                    </div>

                    {getMachineMaterials(machine).length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {getMachineMaterials(machine).slice(0, 3).map((m, i) => (
                          <span key={i} className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded">
                            {m}
                          </span>
                        ))}
                        {getMachineMaterials(machine).length > 3 && (
                          <span className="text-xs text-slate-400">
                            +{getMachineMaterials(machine).length - 3} more
                          </span>
                        )}
                      </div>
                    )}
                  </div>

                  <div className="flex gap-2 mt-4 pt-4 border-t border-slate-100">
                    <Button
                      variant="outline"
                      size="sm"
                      className="flex-1"
                      onClick={() => openEditDialog(machine)}
                      data-testid={`edit-machine-${machine.machine_id}`}
                    >
                      <Edit2 className="w-3 h-3 mr-1" /> Edit
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="text-red-600 hover:text-red-700 hover:bg-red-50"
                      onClick={() => deleteMachine(machine.machine_id)}
                      data-testid={`delete-machine-${machine.machine_id}`}
                    >
                      <Trash2 className="w-3 h-3" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
            })}
          </div>
        ) : (
          <Card className="border-slate-200">
            <CardContent className="py-12 text-center">
              <Wrench className="w-16 h-16 text-slate-300 mx-auto mb-4" />
              <h3 className="font-heading text-lg font-semibold text-slate-900 mb-2">
                No Machines Added Yet
              </h3>
              <p className="text-slate-500 mb-4">
                Add your manufacturing equipment to start receiving matching RFQs
              </p>
              <Button 
                onClick={openAddDialog}
                className="bg-orange-600 hover:bg-orange-700"
              >
                <Plus className="w-4 h-4 mr-2" /> Add Your First Machine
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Availability Summary */}
        {machines.length > 0 && (
          <div className="mt-8">
            <h3 className="font-semibold text-slate-900 mb-4">Machine Availability Summary</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Card className="border-green-200 bg-green-50">
                <CardContent className="p-4 text-center">
                  <CheckCircle2 className="w-8 h-8 text-green-600 mx-auto mb-2" />
                  <div className="text-2xl font-bold text-green-700">{availabilitySummary.available}</div>
                  <div className="text-sm text-green-600">Available</div>
                </CardContent>
              </Card>
              <Card className="border-blue-200 bg-blue-50">
                <CardContent className="p-4 text-center">
                  <Clock className="w-8 h-8 text-blue-600 mx-auto mb-2" />
                  <div className="text-2xl font-bold text-blue-700">{availabilitySummary.engaged}</div>
                  <div className="text-sm text-blue-600">Engaged</div>
                </CardContent>
              </Card>
              <Card className="border-yellow-200 bg-yellow-50">
                <CardContent className="p-4 text-center">
                  <AlertTriangle className="w-8 h-8 text-yellow-600 mx-auto mb-2" />
                  <div className="text-2xl font-bold text-yellow-700">{availabilitySummary.maintenance}</div>
                  <div className="text-sm text-yellow-600">Maintenance</div>
                </CardContent>
              </Card>
              <Card className="border-gray-200 bg-gray-50">
                <CardContent className="p-4 text-center">
                  <Power className="w-8 h-8 text-gray-500 mx-auto mb-2" />
                  <div className="text-2xl font-bold text-gray-600">{availabilitySummary.offline}</div>
                  <div className="text-sm text-gray-500">Offline</div>
                </CardContent>
              </Card>
            </div>
          </div>
        )}

        {/* Availability Dialog */}
        <Dialog open={availabilityDialogOpen} onOpenChange={setAvailabilityDialogOpen}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Update Machine Availability</DialogTitle>
            </DialogHeader>
            {selectedMachine && (
              <div className="space-y-4 py-4">
                <div className="text-sm text-slate-600 mb-4">
                  <strong>{getMachineName(selectedMachine)}</strong>
                  <br />
                  {selectedMachine.brand} {selectedMachine.model}
                </div>
                
                <div className="space-y-2">
                  <Label>Status</Label>
                  <Select
                    value={availabilityData.availability_status}
                    onValueChange={(v) => setAvailabilityData({...availabilityData, availability_status: v})}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="available">
                        <div className="flex items-center gap-2">
                          <CheckCircle2 className="w-4 h-4 text-green-600" /> Available
                        </div>
                      </SelectItem>
                      <SelectItem value="engaged">
                        <div className="flex items-center gap-2">
                          <Clock className="w-4 h-4 text-blue-600" /> Engaged
                        </div>
                      </SelectItem>
                      <SelectItem value="maintenance">
                        <div className="flex items-center gap-2">
                          <AlertTriangle className="w-4 h-4 text-yellow-600" /> Maintenance
                        </div>
                      </SelectItem>
                      <SelectItem value="offline">
                        <div className="flex items-center gap-2">
                          <Power className="w-4 h-4 text-gray-500" /> Offline
                        </div>
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {availabilityData.availability_status === "engaged" && (
                  <div className="space-y-2">
                    <Label>Engaged Until (Expected Available Date)</Label>
                    <Input
                      type="date"
                      value={availabilityData.engaged_until?.split('T')[0] || ""}
                      onChange={(e) => setAvailabilityData({...availabilityData, engaged_until: e.target.value})}
                    />
                  </div>
                )}

                <div className="space-y-2">
                  <Label>Note (Optional)</Label>
                  <Input
                    placeholder="E.g., Working on PO-12345..."
                    value={availabilityData.availability_note || ""}
                    onChange={(e) => setAvailabilityData({...availabilityData, availability_note: e.target.value})}
                  />
                </div>

                <div className="flex gap-3 pt-4">
                  <Button
                    variant="outline"
                    className="flex-1"
                    onClick={() => setAvailabilityDialogOpen(false)}
                  >
                    Cancel
                  </Button>
                  <Button
                    className="flex-1 bg-orange-600 hover:bg-orange-700"
                    onClick={updateAvailability}
                    disabled={updatingAvailability}
                  >
                    {updatingAvailability ? <Loader2 className="w-4 h-4 animate-spin" /> : "Update"}
                  </Button>
                </div>
              </div>
            )}
          </DialogContent>
        </Dialog>

        {/* Image Management Dialog */}
        <Dialog open={imageDialogOpen} onOpenChange={setImageDialogOpen}>
          <DialogContent className="sm:max-w-lg">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Image className="w-5 h-5 text-orange-600" />
                Machine Images
              </DialogTitle>
            </DialogHeader>
            {selectedMachineForImage && (
              <div className="space-y-4 py-4">
                <div className="text-sm text-slate-600 mb-4">
                  <strong>{getMachineName(selectedMachineForImage)}</strong>
                  <br />
                  {selectedMachineForImage.brand} {selectedMachineForImage.model}
                </div>

                {/* Current Images */}
                {selectedMachineForImage.images?.length > 0 && (
                  <div className="space-y-2">
                    <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                      Current Images ({selectedMachineForImage.images.length})
                    </Label>
                    <div className="grid grid-cols-3 gap-2">
                      {selectedMachineForImage.images.map((img, idx) => (
                        <div key={idx} className="relative group aspect-square rounded-lg overflow-hidden border">
                          <img 
                            src={img} 
                            alt={`Machine ${idx + 1}`}
                            className="w-full h-full object-cover"
                          />
                          <button
                            onClick={() => deleteMachineImage(img)}
                            className="absolute top-1 right-1 bg-red-500 text-white p-1 rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
                            title="Delete image"
                          >
                            <X className="w-3 h-3" />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Upload New Image */}
                <div className="space-y-2">
                  <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    Add New Image
                  </Label>
                  <div className="border-2 border-dashed border-slate-200 rounded-lg p-6 text-center hover:border-orange-300 transition-colors">
                    {imagePreview ? (
                      <div className="space-y-3">
                        <img 
                          src={imagePreview} 
                          alt="Preview" 
                          className="max-h-32 mx-auto rounded-lg"
                        />
                        {uploadingImage && (
                          <div className="flex items-center justify-center gap-2 text-sm text-orange-600">
                            <Loader2 className="w-4 h-4 animate-spin" />
                            Uploading...
                          </div>
                        )}
                      </div>
                    ) : (
                      <label className="cursor-pointer">
                        <input
                          type="file"
                          accept="image/*"
                          onChange={handleImageSelect}
                          className="hidden"
                          disabled={uploadingImage}
                        />
                        <Camera className="w-10 h-10 text-slate-300 mx-auto mb-2" />
                        <p className="text-slate-600 text-sm">Click to upload image</p>
                        <p className="text-xs text-slate-400 mt-1">JPG, PNG, WebP (max 5MB)</p>
                      </label>
                    )}
                  </div>
                </div>

                <div className="flex justify-end pt-4">
                  <Button
                    variant="outline"
                    onClick={() => setImageDialogOpen(false)}
                  >
                    Done
                  </Button>
                </div>
              </div>
            )}
          </DialogContent>
        </Dialog>
      </div>
    </DashboardLayout>
  );
};

export default MachineManagement;
