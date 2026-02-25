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
  Cog, Maximize2, Settings
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
  monthly_capacity_hours: 160
};

const MachineManagement = () => {
  const [machines, setMachines] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingMachine, setEditingMachine] = useState(null);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState(emptyMachine);
  const [machineCategories, setMachineCategories] = useState({});

  useEffect(() => {
    fetchMachines();
    fetchCategories();
  }, []);

  const fetchMachines = async () => {
    try {
      const response = await api.get("/machines");
      setMachines(response.data);
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

        {/* Machines Grid */}
        {machines.length > 0 ? (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {machines.map((machine) => (
              <Card key={machine.machine_id} className="border-slate-200 hover:border-orange-200 transition-colors">
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
                    {(machine.machine_category || detectCategoryFromType(machine.machine_type)) && (
                      <span className="text-xs bg-orange-100 text-orange-700 px-2 py-1 rounded">
                        {machine.machine_category || detectCategoryFromType(machine.machine_type)}
                      </span>
                    )}
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
            ))}
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
      </div>
    </DashboardLayout>
  );
};

export default MachineManagement;
