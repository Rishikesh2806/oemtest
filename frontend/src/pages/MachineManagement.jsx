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

const MACHINE_TYPES = [
  "CNC Milling", "CNC Turning", "CNC Lathe", "VMC", "HMC",
  "5-Axis CNC", "Laser Cutting", "Waterjet", "EDM",
  "Press Brake", "Sheet Metal", "Welding", "Grinding", "Other"
];

const AXIS_CONFIGS = ["3-axis", "4-axis", "5-axis", "Multi-axis"];

const MATERIALS = [
  "Aluminum", "Steel", "Stainless Steel", "Carbon Steel",
  "Brass", "Copper", "Titanium", "Plastic", "Other"
];

const emptyMachine = {
  machine_type: "",
  brand: "",
  model: "",
  max_x: "",
  max_y: "",
  max_z: "",
  max_diameter: "",
  tonnage: "",
  tolerance_capability: "0.1",
  axis_config: "",
  materials_supported: [],
  monthly_capacity_hours: "160"
};

const MachineManagement = () => {
  const [machines, setMachines] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingMachine, setEditingMachine] = useState(null);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState(emptyMachine);

  useEffect(() => {
    fetchMachines();
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
    setFormData({
      machine_type: machine.machine_type || "",
      brand: machine.brand || "",
      model: machine.model || "",
      max_x: machine.max_x?.toString() || "",
      max_y: machine.max_y?.toString() || "",
      max_z: machine.max_z?.toString() || "",
      max_diameter: machine.max_diameter?.toString() || "",
      tonnage: machine.tonnage?.toString() || "",
      tolerance_capability: machine.tolerance_capability?.toString() || "0.1",
      axis_config: machine.axis_config || "",
      materials_supported: machine.materials_supported || [],
      monthly_capacity_hours: machine.monthly_capacity_hours?.toString() || "160"
    });
    setDialogOpen(true);
  };

  const handleSubmit = async () => {
    if (!formData.machine_type || !formData.brand || !formData.model) {
      toast.error("Please fill in required fields");
      return;
    }

    setSaving(true);
    try {
      const payload = {
        ...formData,
        max_x: formData.max_x ? parseFloat(formData.max_x) : null,
        max_y: formData.max_y ? parseFloat(formData.max_y) : null,
        max_z: formData.max_z ? parseFloat(formData.max_z) : null,
        max_diameter: formData.max_diameter ? parseFloat(formData.max_diameter) : null,
        tonnage: formData.tonnage ? parseFloat(formData.tonnage) : null,
        tolerance_capability: parseFloat(formData.tolerance_capability) || 0.1,
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
              <div className="space-y-4 mt-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                      Machine Type *
                    </Label>
                    <Select
                      value={formData.machine_type}
                      onValueChange={(value) => handleInputChange("machine_type", value)}
                    >
                      <SelectTrigger className="mt-1" data-testid="machine-type-select">
                        <SelectValue placeholder="Select type" />
                      </SelectTrigger>
                      <SelectContent>
                        {MACHINE_TYPES.map((type) => (
                          <SelectItem key={type} value={type}>{type}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                      Axis Config
                    </Label>
                    <Select
                      value={formData.axis_config}
                      onValueChange={(value) => handleInputChange("axis_config", value)}
                    >
                      <SelectTrigger className="mt-1">
                        <SelectValue placeholder="Select config" />
                      </SelectTrigger>
                      <SelectContent>
                        {AXIS_CONFIGS.map((config) => (
                          <SelectItem key={config} value={config}>{config}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
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
                      placeholder="e.g., Mazak, Haas, DMG"
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

                <div>
                  <Label className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1">
                    <Maximize2 className="w-3 h-3" /> Max Work Envelope (mm)
                  </Label>
                  <div className="grid grid-cols-3 gap-4 mt-1">
                    <Input
                      type="number"
                      value={formData.max_x}
                      onChange={(e) => handleInputChange("max_x", e.target.value)}
                      placeholder="X"
                    />
                    <Input
                      type="number"
                      value={formData.max_y}
                      onChange={(e) => handleInputChange("max_y", e.target.value)}
                      placeholder="Y"
                    />
                    <Input
                      type="number"
                      value={formData.max_z}
                      onChange={(e) => handleInputChange("max_z", e.target.value)}
                      placeholder="Z"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                      Max Diameter (mm)
                    </Label>
                    <Input
                      type="number"
                      value={formData.max_diameter}
                      onChange={(e) => handleInputChange("max_diameter", e.target.value)}
                      placeholder="For lathes/turning"
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                      Tolerance Capability (mm)
                    </Label>
                    <Input
                      type="number"
                      step="0.001"
                      value={formData.tolerance_capability}
                      onChange={(e) => handleInputChange("tolerance_capability", e.target.value)}
                      placeholder="0.1"
                      className="mt-1"
                    />
                  </div>
                </div>

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
                            ? "bg-slate-900 text-white"
                            : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                        }`}
                      >
                        {material}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="flex justify-end gap-3 pt-4">
                  <DialogClose asChild>
                    <Button variant="outline">Cancel</Button>
                  </DialogClose>
                  <Button
                    onClick={handleSubmit}
                    disabled={saving}
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
              <Card key={machine.machine_id} className="border-slate-200">
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-slate-100 rounded-lg flex items-center justify-center">
                        <Cog className="w-5 h-5 text-slate-500" />
                      </div>
                      <div>
                        <CardTitle className="text-base">{machine.machine_type}</CardTitle>
                        <p className="text-sm text-slate-500">
                          {machine.brand} {machine.model}
                        </p>
                      </div>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3 text-sm">
                    {(machine.max_x || machine.max_y || machine.max_z) && (
                      <div className="flex items-center gap-2">
                        <Maximize2 className="w-4 h-4 text-slate-400" />
                        <span className="text-slate-600">
                          {machine.max_x || "-"} × {machine.max_y || "-"} × {machine.max_z || "-"} mm
                        </span>
                      </div>
                    )}
                    
                    {machine.axis_config && (
                      <div className="flex items-center gap-2">
                        <Settings className="w-4 h-4 text-slate-400" />
                        <span className="text-slate-600">{machine.axis_config}</span>
                      </div>
                    )}

                    <div className="text-slate-600">
                      Tolerance: ±{machine.tolerance_capability} mm
                    </div>

                    {machine.materials_supported?.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {machine.materials_supported.slice(0, 3).map((m, i) => (
                          <span key={i} className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded">
                            {m}
                          </span>
                        ))}
                        {machine.materials_supported.length > 3 && (
                          <span className="text-xs text-slate-400">
                            +{machine.materials_supported.length - 3} more
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
