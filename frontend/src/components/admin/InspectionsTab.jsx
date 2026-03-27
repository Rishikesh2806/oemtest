import { useState, useEffect } from "react";
import { api } from "../../App";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Badge } from "../ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "../ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";
import { Textarea } from "../ui/textarea";
import { toast } from "sonner";
import {
  Shield, ClipboardCheck, ShieldCheck, User, Building2,
  Clock, CheckCircle2, XCircle, AlertTriangle, Loader2,
  RefreshCw, Search, Eye, UserPlus, Plus, MapPin, Phone,
  Mail, Calendar, DollarSign, Package, FileText, Edit
} from "lucide-react";

const STATUS_CONFIG = {
  requested: { label: "Requested", color: "bg-blue-100 text-blue-700" },
  payment_pending: { label: "Payment Pending", color: "bg-yellow-100 text-yellow-700" },
  payment_completed: { label: "Payment Completed", color: "bg-green-100 text-green-700" },
  awaiting_assignment: { label: "Awaiting Assignment", color: "bg-purple-100 text-purple-700" },
  inspector_assigned: { label: "Inspector Assigned", color: "bg-blue-100 text-blue-700" },
  in_progress: { label: "In Progress", color: "bg-orange-100 text-orange-700" },
  report_submitted: { label: "Report Submitted", color: "bg-indigo-100 text-indigo-700" },
  approved: { label: "Approved", color: "bg-green-100 text-green-700" },
  rejected: { label: "Rejected", color: "bg-red-100 text-red-700" },
  re_inspection_requested: { label: "Re-inspection Requested", color: "bg-amber-100 text-amber-700" },
  completed: { label: "Completed", color: "bg-green-100 text-green-700" },
  cancelled: { label: "Cancelled", color: "bg-slate-100 text-slate-700" }
};

const InspectionsTab = ({ canAssign = true, canManageInspectors = true, canManagePricing = true }) => {
  const [loading, setLoading] = useState(true);
  const [inspections, setInspections] = useState([]);
  const [inspectors, setInspectors] = useState([]);
  const [pricing, setPricing] = useState([]);
  const [filterStatus, setFilterStatus] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  
  // Modals
  const [selectedInspection, setSelectedInspection] = useState(null);
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [showCreateInspectorModal, setShowCreateInspectorModal] = useState(false);
  const [showPricingModal, setShowPricingModal] = useState(false);
  
  // Assignment form
  const [assignForm, setAssignForm] = useState({
    inspector_id: "",
    agency_name: "",
    agency_contact: ""
  });
  
  // New inspector form
  const [inspectorForm, setInspectorForm] = useState({
    name: "",
    email: "",
    phone: "",
    password: "",
    city: "",
    state: "",
    pincode: ""
  });
  
  // Pricing form
  const [pricingForm, setPricingForm] = useState({
    inspection_type: "basic",
    base_price: "",
    region: "",
    description: ""
  });
  
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetchData();
  }, [filterStatus]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const statusParam = filterStatus && filterStatus !== "all" ? `?status=${filterStatus}` : "";
      
      // Always fetch inspections (base permission)
      const inspectionsRes = await api.get(`/admin/inspections${statusParam}`);
      setInspections(inspectionsRes.data.inspections || []);

      // Only fetch inspectors/pricing if user has permission (avoid 403 breaking everything)
      if (canManageInspectors) {
        try {
          const inspectorsRes = await api.get("/admin/inspectors");
          setInspectors(inspectorsRes.data.inspectors || []);
        } catch { /* no permission — skip */ }
      }

      if (canManagePricing) {
        try {
          const pricingRes = await api.get("/admin/inspection-pricing");
          setPricing(pricingRes.data.pricing || []);
        } catch { /* no permission — skip */ }
      }
    } catch (error) {
      console.error("Failed to fetch inspection data:", error);
      toast.error("Failed to load inspection data");
    } finally {
      setLoading(false);
    }
  };

  const handleAssignInspector = async () => {
    if (!selectedInspection) return;
    
    const isBasic = selectedInspection.inspection_type === "basic";
    
    if (isBasic && !assignForm.inspector_id) {
      toast.error("Please select an inspector");
      return;
    }
    
    if (!isBasic && !assignForm.agency_name) {
      toast.error("Please enter agency name");
      return;
    }
    
    setSubmitting(true);
    try {
      const payload = isBasic 
        ? { inspector_id: assignForm.inspector_id }
        : { agency_name: assignForm.agency_name, agency_contact: assignForm.agency_contact };
      
      await api.post(`/admin/orders/${selectedInspection.order_id}/assign-inspector`, payload);
      
      toast.success("Inspector/Agency assigned successfully!");
      setShowAssignModal(false);
      setAssignForm({ inspector_id: "", agency_name: "", agency_contact: "" });
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to assign inspector");
    } finally {
      setSubmitting(false);
    }
  };

  const handleCreateInspector = async () => {
    if (!inspectorForm.name || !inspectorForm.email || !inspectorForm.password) {
      toast.error("Name, email, and password are required");
      return;
    }
    
    setSubmitting(true);
    try {
      await api.post("/admin/inspectors/create", inspectorForm);
      
      toast.success("Inspector created successfully!");
      setShowCreateInspectorModal(false);
      setInspectorForm({ name: "", email: "", phone: "", password: "", city: "", state: "", pincode: "" });
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to create inspector");
    } finally {
      setSubmitting(false);
    }
  };

  const handleApproveInspector = async (inspectorId, action) => {
    try {
      await api.post(`/admin/inspectors/${inspectorId}/approve`, { action });
      toast.success(`Inspector ${action}d successfully`);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || `Failed to ${action} inspector`);
    }
  };

  const handleSavePricing = async () => {
    if (!pricingForm.inspection_type || !pricingForm.base_price) {
      toast.error("Inspection type and base price are required");
      return;
    }
    
    setSubmitting(true);
    try {
      await api.post("/admin/inspection-pricing", {
        inspection_type: pricingForm.inspection_type,
        base_price: parseFloat(pricingForm.base_price),
        region: pricingForm.region || null,
        description: pricingForm.description
      });
      
      toast.success("Pricing saved successfully!");
      setShowPricingModal(false);
      setPricingForm({ inspection_type: "basic", base_price: "", region: "", description: "" });
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to save pricing");
    } finally {
      setSubmitting(false);
    }
  };

  const openAssignModal = (inspection) => {
    setSelectedInspection(inspection);
    setAssignForm({ inspector_id: "", agency_name: "", agency_contact: "" });
    setShowAssignModal(true);
  };

  const openDetailModal = (inspection) => {
    setSelectedInspection(inspection);
    setShowDetailModal(true);
  };

  const filteredInspections = inspections.filter(insp => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      insp.order_id?.toLowerCase().includes(query) ||
      insp.inspection_id?.toLowerCase().includes(query) ||
      insp.buyer_name?.toLowerCase().includes(query) ||
      insp.buyer_email?.toLowerCase().includes(query)
    );
  });

  const pendingAssignment = inspections.filter(i => 
    i.status === "awaiting_assignment" || i.status === "re_inspection_requested"
  ).length;

  const availableInspectors = inspectors.filter(i => 
    i.is_available && i.approval_status === "approved"
  );
  
  const pendingInspectorApprovals = inspectors.filter(i => i.approval_status === "pending");

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-orange-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <Card className="border-blue-200 bg-blue-50">
          <CardContent className="py-3">
            <p className="text-xs text-blue-600 font-medium">Total Inspections</p>
            <p className="text-2xl font-bold text-blue-700">{inspections.length}</p>
          </CardContent>
        </Card>
        <Card className={`border-purple-200 ${pendingAssignment > 0 ? 'bg-purple-100' : 'bg-purple-50'}`}>
          <CardContent className="py-3">
            <p className="text-xs text-purple-600 font-medium">Pending Assignment</p>
            <p className="text-2xl font-bold text-purple-700">{pendingAssignment}</p>
          </CardContent>
        </Card>
        <Card className="border-green-200 bg-green-50">
          <CardContent className="py-3">
            <p className="text-xs text-green-600 font-medium">Available Inspectors</p>
            <p className="text-2xl font-bold text-green-700">{availableInspectors.length}</p>
          </CardContent>
        </Card>
        <Card className={`border-amber-200 ${pendingInspectorApprovals.length > 0 ? 'bg-amber-100' : 'bg-amber-50'}`}>
          <CardContent className="py-3">
            <p className="text-xs text-amber-600 font-medium">Pending Approvals</p>
            <p className="text-2xl font-bold text-amber-700">{pendingInspectorApprovals.length}</p>
          </CardContent>
        </Card>
        <Card className="border-slate-200">
          <CardContent className="py-3">
            <p className="text-xs text-slate-500 font-medium">Pricing Rules</p>
            <p className="text-2xl font-bold text-slate-700">{pricing.length}</p>
          </CardContent>
        </Card>
      </div>

      {/* Actions Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <Input
              placeholder="Search inspections..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 w-64"
              data-testid="inspection-search"
            />
          </div>
          <Select value={filterStatus} onValueChange={setFilterStatus}>
            <SelectTrigger className="w-48" data-testid="status-filter">
              <SelectValue placeholder="Filter by status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Statuses</SelectItem>
              <SelectItem value="awaiting_assignment">Awaiting Assignment</SelectItem>
              <SelectItem value="inspector_assigned">Inspector Assigned</SelectItem>
              <SelectItem value="in_progress">In Progress</SelectItem>
              <SelectItem value="report_submitted">Report Submitted</SelectItem>
              <SelectItem value="approved">Approved</SelectItem>
              <SelectItem value="rejected">Rejected</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="flex items-center gap-2">
          {canManagePricing && (
            <Button 
              variant="outline" 
              onClick={() => setShowPricingModal(true)}
              data-testid="manage-pricing-btn"
            >
              <DollarSign className="w-4 h-4 mr-1" /> Manage Pricing
            </Button>
          )}
          {canManageInspectors && (
            <Button 
              onClick={() => setShowCreateInspectorModal(true)}
              className="bg-orange-600 hover:bg-orange-700"
              data-testid="add-inspector-btn"
            >
              <UserPlus className="w-4 h-4 mr-1" /> Add Inspector
            </Button>
          )}
          <Button variant="ghost" onClick={fetchData}>
            <RefreshCw className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Pending Inspector Approvals */}
      {pendingInspectorApprovals.length > 0 && canManageInspectors && (
        <Card className="border-amber-200 bg-amber-50">
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2 text-amber-800">
              <AlertTriangle className="w-4 h-4" />
              Pending Inspector Approvals ({pendingInspectorApprovals.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {pendingInspectorApprovals.map((inspector) => (
                <div 
                  key={inspector.inspector_id}
                  className="flex items-center justify-between p-3 bg-white rounded-lg border border-amber-200"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-amber-100 rounded-full flex items-center justify-center">
                      <User className="w-5 h-5 text-amber-600" />
                    </div>
                    <div>
                      <p className="font-medium text-slate-900">{inspector.name}</p>
                      <p className="text-sm text-slate-500">{inspector.email}</p>
                      {inspector.city && (
                        <p className="text-xs text-slate-400">{inspector.city}, {inspector.state}</p>
                      )}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleApproveInspector(inspector.inspector_id, "reject")}
                      className="text-red-600 border-red-200 hover:bg-red-50"
                    >
                      <XCircle className="w-4 h-4" />
                    </Button>
                    <Button
                      size="sm"
                      onClick={() => handleApproveInspector(inspector.inspector_id, "approve")}
                      className="bg-green-600 hover:bg-green-700"
                    >
                      <CheckCircle2 className="w-4 h-4 mr-1" /> Approve
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Inspections List */}
      <Card className="border-slate-200">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg flex items-center gap-2">
            <Shield className="w-5 h-5 text-orange-600" />
            Inspection Requests ({filteredInspections.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {filteredInspections.length === 0 ? (
            <div className="text-center py-8 text-slate-500">
              <ClipboardCheck className="w-12 h-12 text-slate-300 mx-auto mb-2" />
              <p>No inspection requests found</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200">
                    <th className="text-left py-3 px-2 font-medium text-slate-500">Inspection</th>
                    <th className="text-left py-3 px-2 font-medium text-slate-500">Order</th>
                    <th className="text-left py-3 px-2 font-medium text-slate-500">Type</th>
                    <th className="text-left py-3 px-2 font-medium text-slate-500">Buyer</th>
                    <th className="text-left py-3 px-2 font-medium text-slate-500">Status</th>
                    <th className="text-left py-3 px-2 font-medium text-slate-500">Fee</th>
                    <th className="text-left py-3 px-2 font-medium text-slate-500">Assigned To</th>
                    <th className="text-left py-3 px-2 font-medium text-slate-500">Date</th>
                    <th className="text-right py-3 px-2 font-medium text-slate-500">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredInspections.map((inspection) => {
                    const statusConfig = STATUS_CONFIG[inspection.status] || {};
                    const canAssignNow = canAssign && (
                      inspection.status === "awaiting_assignment" || 
                      inspection.status === "re_inspection_requested"
                    );
                    
                    return (
                      <tr 
                        key={inspection.inspection_id}
                        className="border-b border-slate-100 hover:bg-slate-50"
                      >
                        <td className="py-3 px-2">
                          <span className="font-mono text-xs text-slate-600">
                            {inspection.inspection_id?.slice(-8)}
                          </span>
                        </td>
                        <td className="py-3 px-2">
                          <span className="font-mono text-xs">
                            {inspection.order_id?.slice(-8)}
                          </span>
                        </td>
                        <td className="py-3 px-2">
                          <div className="flex items-center gap-1">
                            {inspection.inspection_type === "basic" ? (
                              <>
                                <ClipboardCheck className="w-3 h-3 text-blue-600" />
                                <span className="text-blue-700">Basic</span>
                              </>
                            ) : (
                              <>
                                <ShieldCheck className="w-3 h-3 text-purple-600" />
                                <span className="text-purple-700">Certified</span>
                              </>
                            )}
                          </div>
                        </td>
                        <td className="py-3 px-2">
                          <div>
                            <p className="font-medium text-slate-800">{inspection.buyer_name || 'N/A'}</p>
                            <p className="text-xs text-slate-400">{inspection.buyer_email}</p>
                          </div>
                        </td>
                        <td className="py-3 px-2">
                          <Badge className={statusConfig.color}>
                            {statusConfig.label || inspection.status}
                          </Badge>
                        </td>
                        <td className="py-3 px-2">
                          <span className="font-medium">
                            ₹{inspection.inspection_fee?.toLocaleString('en-IN')}
                          </span>
                        </td>
                        <td className="py-3 px-2">
                          {inspection.inspector_name ? (
                            <div className="flex items-center gap-1">
                              <User className="w-3 h-3 text-slate-400" />
                              <span>{inspection.inspector_name}</span>
                            </div>
                          ) : inspection.agency_name ? (
                            <div className="flex items-center gap-1">
                              <Building2 className="w-3 h-3 text-slate-400" />
                              <span>{inspection.agency_name}</span>
                            </div>
                          ) : (
                            <span className="text-slate-400">-</span>
                          )}
                        </td>
                        <td className="py-3 px-2 text-slate-500 text-xs">
                          {new Date(inspection.created_at).toLocaleDateString()}
                        </td>
                        <td className="py-3 px-2 text-right">
                          <div className="flex items-center justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => openDetailModal(inspection)}
                              data-testid={`view-inspection-${inspection.inspection_id}`}
                            >
                              <Eye className="w-4 h-4" />
                            </Button>
                            {canAssignNow && (
                              <Button
                                size="sm"
                                onClick={() => openAssignModal(inspection)}
                                className="bg-orange-600 hover:bg-orange-700"
                                data-testid={`assign-inspector-${inspection.inspection_id}`}
                              >
                                <UserPlus className="w-4 h-4 mr-1" /> Assign
                              </Button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Inspectors List */}
      <Card className="border-slate-200">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg flex items-center gap-2">
            <User className="w-5 h-5 text-orange-600" />
            Registered Inspectors ({inspectors.filter(i => i.approval_status === "approved").length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {inspectors.filter(i => i.approval_status === "approved").length === 0 ? (
            <div className="text-center py-8 text-slate-500">
              <User className="w-12 h-12 text-slate-300 mx-auto mb-2" />
              <p>No approved inspectors yet</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {inspectors.filter(i => i.approval_status === "approved").map((inspector) => (
                <div 
                  key={inspector.inspector_id}
                  className="p-4 border border-slate-200 rounded-lg hover:border-orange-300 transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                        inspector.is_available ? 'bg-green-100' : 'bg-slate-100'
                      }`}>
                        <User className={`w-5 h-5 ${inspector.is_available ? 'text-green-600' : 'text-slate-400'}`} />
                      </div>
                      <div>
                        <p className="font-medium text-slate-900">{inspector.name}</p>
                        <p className="text-xs text-slate-500">{inspector.email}</p>
                      </div>
                    </div>
                    <Badge className={inspector.is_available ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-500'}>
                      {inspector.is_available ? 'Available' : 'Unavailable'}
                    </Badge>
                  </div>
                  <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                    <div className="flex items-center gap-1 text-slate-500">
                      <MapPin className="w-3 h-3" />
                      {inspector.city || 'N/A'}, {inspector.state || 'N/A'}
                    </div>
                    <div className="flex items-center gap-1 text-slate-500">
                      <ClipboardCheck className="w-3 h-3" />
                      {inspector.total_inspections || 0} inspections
                    </div>
                  </div>
                  {inspector.avg_rating > 0 && (
                    <div className="mt-2 text-xs text-amber-600">
                      Rating: {inspector.avg_rating.toFixed(1)} / 5
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Pricing Config */}
      <Card className="border-slate-200">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg flex items-center gap-2">
            <DollarSign className="w-5 h-5 text-orange-600" />
            Inspection Pricing
          </CardTitle>
        </CardHeader>
        <CardContent>
          {pricing.length === 0 ? (
            <div className="text-center py-8 text-slate-500">
              <DollarSign className="w-12 h-12 text-slate-300 mx-auto mb-2" />
              <p>No pricing configured yet</p>
              {canManagePricing && (
                <Button 
                  variant="outline" 
                  className="mt-4"
                  onClick={() => setShowPricingModal(true)}
                >
                  <Plus className="w-4 h-4 mr-1" /> Add Pricing
                </Button>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {pricing.map((p, idx) => (
                <div 
                  key={p.pricing_id || idx}
                  className={`p-4 rounded-lg border-2 ${
                    p.inspection_type === 'basic' 
                      ? 'border-blue-200 bg-blue-50' 
                      : 'border-purple-200 bg-purple-50'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {p.inspection_type === 'basic' ? (
                        <ClipboardCheck className="w-5 h-5 text-blue-600" />
                      ) : (
                        <ShieldCheck className="w-5 h-5 text-purple-600" />
                      )}
                      <span className="font-medium capitalize">{p.inspection_type}</span>
                    </div>
                    <span className={`text-xl font-bold ${
                      p.inspection_type === 'basic' ? 'text-blue-700' : 'text-purple-700'
                    }`}>
                      ₹{p.base_price?.toLocaleString('en-IN')}
                    </span>
                  </div>
                  {p.region && (
                    <p className="text-xs text-slate-500 mt-1">Region: {p.region}</p>
                  )}
                  {p.description && (
                    <p className="text-sm text-slate-600 mt-2">{p.description}</p>
                  )}
                  <div className="flex items-center justify-between mt-2">
                    <span className={`text-xs ${p.is_active ? 'text-green-600' : 'text-slate-400'}`}>
                      {p.is_active ? 'Active' : 'Inactive'}
                    </span>
                    {canManagePricing && (
                      <Button 
                        variant="ghost" 
                        size="sm"
                        onClick={() => {
                          setPricingForm({
                            inspection_type: p.inspection_type,
                            base_price: p.base_price.toString(),
                            region: p.region || "",
                            description: p.description || ""
                          });
                          setShowPricingModal(true);
                        }}
                      >
                        <Edit className="w-3 h-3" />
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Assign Inspector Modal */}
      <Dialog open={showAssignModal} onOpenChange={setShowAssignModal}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Assign Inspector / Agency</DialogTitle>
          </DialogHeader>
          
          {selectedInspection && (
            <div className="space-y-4 mt-4">
              {/* Inspection Info */}
              <div className="p-3 bg-slate-50 rounded-lg">
                <p className="text-sm text-slate-500">Order ID</p>
                <p className="font-mono">{selectedInspection.order_id}</p>
                <p className="text-sm text-slate-500 mt-2">Inspection Type</p>
                <p className="font-medium capitalize">{selectedInspection.inspection_type}</p>
              </div>

              {selectedInspection.inspection_type === "basic" ? (
                <div>
                  <Label>Select Inspector</Label>
                  <Select 
                    value={assignForm.inspector_id}
                    onValueChange={(v) => setAssignForm(prev => ({ ...prev, inspector_id: v }))}
                  >
                    <SelectTrigger className="mt-1" data-testid="inspector-select">
                      <SelectValue placeholder="Choose an inspector" />
                    </SelectTrigger>
                    <SelectContent>
                      {availableInspectors.length === 0 ? (
                        <div className="p-2 text-center text-slate-500 text-sm">
                          No available inspectors
                        </div>
                      ) : (
                        availableInspectors.map((inspector) => (
                          <SelectItem key={inspector.inspector_id} value={inspector.inspector_id}>
                            <div className="flex items-center gap-2">
                              <User className="w-4 h-4 text-slate-400" />
                              <span>{inspector.name}</span>
                              {inspector.city && (
                                <span className="text-xs text-slate-400">({inspector.city})</span>
                              )}
                            </div>
                          </SelectItem>
                        ))
                      )}
                    </SelectContent>
                  </Select>
                </div>
              ) : (
                <>
                  <div>
                    <Label>Agency Name *</Label>
                    <Input
                      placeholder="Enter certified agency name"
                      value={assignForm.agency_name}
                      onChange={(e) => setAssignForm(prev => ({ ...prev, agency_name: e.target.value }))}
                      className="mt-1"
                      data-testid="agency-name-input"
                    />
                  </div>
                  <div>
                    <Label>Agency Contact</Label>
                    <Input
                      placeholder="Contact person / phone"
                      value={assignForm.agency_contact}
                      onChange={(e) => setAssignForm(prev => ({ ...prev, agency_contact: e.target.value }))}
                      className="mt-1"
                      data-testid="agency-contact-input"
                    />
                  </div>
                </>
              )}
            </div>
          )}

          <DialogFooter className="mt-4">
            <Button variant="outline" onClick={() => setShowAssignModal(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleAssignInspector}
              disabled={submitting}
              className="bg-orange-600 hover:bg-orange-700"
              data-testid="confirm-assign-btn"
            >
              {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : "Assign"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Inspection Detail Modal */}
      <Dialog open={showDetailModal} onOpenChange={setShowDetailModal}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Shield className="w-5 h-5 text-orange-600" />
              Inspection Details
            </DialogTitle>
          </DialogHeader>
          
          {selectedInspection && (
            <div className="space-y-4 mt-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="p-3 bg-slate-50 rounded">
                  <p className="text-xs text-slate-500">Inspection ID</p>
                  <p className="font-mono text-sm">{selectedInspection.inspection_id}</p>
                </div>
                <div className="p-3 bg-slate-50 rounded">
                  <p className="text-xs text-slate-500">Order ID</p>
                  <p className="font-mono text-sm">{selectedInspection.order_id}</p>
                </div>
                <div className="p-3 bg-slate-50 rounded">
                  <p className="text-xs text-slate-500">Type</p>
                  <p className="font-medium capitalize">{selectedInspection.inspection_type}</p>
                </div>
                <div className="p-3 bg-slate-50 rounded">
                  <p className="text-xs text-slate-500">Fee</p>
                  <p className="font-bold">₹{selectedInspection.inspection_fee?.toLocaleString('en-IN')}</p>
                </div>
              </div>

              <div className="p-3 bg-slate-50 rounded">
                <p className="text-xs text-slate-500">Status</p>
                <Badge className={STATUS_CONFIG[selectedInspection.status]?.color}>
                  {STATUS_CONFIG[selectedInspection.status]?.label || selectedInspection.status}
                </Badge>
              </div>

              {selectedInspection.buyer_name && (
                <div className="p-3 bg-slate-50 rounded">
                  <p className="text-xs text-slate-500">Buyer</p>
                  <p className="font-medium">{selectedInspection.buyer_name}</p>
                  <p className="text-sm text-slate-500">{selectedInspection.buyer_email}</p>
                </div>
              )}

              {(selectedInspection.inspector_name || selectedInspection.agency_name) && (
                <div className="p-3 bg-blue-50 rounded">
                  <p className="text-xs text-blue-600">Assigned To</p>
                  <p className="font-medium">
                    {selectedInspection.inspector_name || selectedInspection.agency_name}
                  </p>
                  {selectedInspection.agency_contact && (
                    <p className="text-sm text-blue-500">{selectedInspection.agency_contact}</p>
                  )}
                </div>
              )}

              {selectedInspection.result && (
                <div className={`p-4 rounded text-center ${
                  selectedInspection.result === 'pass' ? 'bg-green-100 text-green-800' :
                  selectedInspection.result === 'fail' ? 'bg-red-100 text-red-800' :
                  'bg-yellow-100 text-yellow-800'
                }`}>
                  <p className="text-lg font-bold">{selectedInspection.result.toUpperCase()}</p>
                  {selectedInspection.remarks && (
                    <p className="text-sm mt-1">{selectedInspection.remarks}</p>
                  )}
                </div>
              )}

              {selectedInspection.buyer_notes && (
                <div className="p-3 bg-yellow-50 rounded">
                  <p className="text-xs text-yellow-700">Buyer Instructions</p>
                  <p className="text-sm">{selectedInspection.buyer_notes}</p>
                </div>
              )}

              <div className="text-xs text-slate-400">
                Created: {new Date(selectedInspection.created_at).toLocaleString()}
              </div>
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDetailModal(false)}>Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Create Inspector Modal */}
      <Dialog open={showCreateInspectorModal} onOpenChange={setShowCreateInspectorModal}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Create Inspector Account</DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4 mt-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Name *</Label>
                <Input
                  placeholder="Full name"
                  value={inspectorForm.name}
                  onChange={(e) => setInspectorForm(prev => ({ ...prev, name: e.target.value }))}
                  data-testid="inspector-name-input"
                />
              </div>
              <div>
                <Label>Phone</Label>
                <Input
                  placeholder="Phone number"
                  value={inspectorForm.phone}
                  onChange={(e) => setInspectorForm(prev => ({ ...prev, phone: e.target.value }))}
                />
              </div>
            </div>
            <div>
              <Label>Email *</Label>
              <Input
                type="email"
                placeholder="email@example.com"
                value={inspectorForm.email}
                onChange={(e) => setInspectorForm(prev => ({ ...prev, email: e.target.value }))}
                data-testid="inspector-email-input"
              />
            </div>
            <div>
              <Label>Password *</Label>
              <Input
                type="password"
                placeholder="Set password"
                value={inspectorForm.password}
                onChange={(e) => setInspectorForm(prev => ({ ...prev, password: e.target.value }))}
                data-testid="inspector-password-input"
              />
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <Label>City</Label>
                <Input
                  placeholder="City"
                  value={inspectorForm.city}
                  onChange={(e) => setInspectorForm(prev => ({ ...prev, city: e.target.value }))}
                />
              </div>
              <div>
                <Label>State</Label>
                <Input
                  placeholder="State"
                  value={inspectorForm.state}
                  onChange={(e) => setInspectorForm(prev => ({ ...prev, state: e.target.value }))}
                />
              </div>
              <div>
                <Label>Pincode</Label>
                <Input
                  placeholder="Pincode"
                  value={inspectorForm.pincode}
                  onChange={(e) => setInspectorForm(prev => ({ ...prev, pincode: e.target.value }))}
                />
              </div>
            </div>
          </div>

          <DialogFooter className="mt-4">
            <Button variant="outline" onClick={() => setShowCreateInspectorModal(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleCreateInspector}
              disabled={submitting}
              className="bg-orange-600 hover:bg-orange-700"
              data-testid="create-inspector-btn"
            >
              {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : "Create Inspector"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Pricing Modal */}
      <Dialog open={showPricingModal} onOpenChange={setShowPricingModal}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Manage Inspection Pricing</DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4 mt-4">
            <div>
              <Label>Inspection Type *</Label>
              <Select 
                value={pricingForm.inspection_type}
                onValueChange={(v) => setPricingForm(prev => ({ ...prev, inspection_type: v }))}
              >
                <SelectTrigger className="mt-1" data-testid="pricing-type-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="basic">Basic Inspection</SelectItem>
                  <SelectItem value="certified">Certified Inspection</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Base Price (INR) *</Label>
              <Input
                type="number"
                placeholder="e.g., 500"
                value={pricingForm.base_price}
                onChange={(e) => setPricingForm(prev => ({ ...prev, base_price: e.target.value }))}
                className="mt-1"
                data-testid="pricing-amount-input"
              />
            </div>
            <div>
              <Label>Region (Optional)</Label>
              <Input
                placeholder="e.g., North India, All"
                value={pricingForm.region}
                onChange={(e) => setPricingForm(prev => ({ ...prev, region: e.target.value }))}
                className="mt-1"
              />
            </div>
            <div>
              <Label>Description</Label>
              <Textarea
                placeholder="Brief description of this pricing tier..."
                value={pricingForm.description}
                onChange={(e) => setPricingForm(prev => ({ ...prev, description: e.target.value }))}
                className="mt-1"
                rows={2}
              />
            </div>
          </div>

          <DialogFooter className="mt-4">
            <Button variant="outline" onClick={() => setShowPricingModal(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleSavePricing}
              disabled={submitting}
              className="bg-orange-600 hover:bg-orange-700"
              data-testid="save-pricing-btn"
            >
              {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : "Save Pricing"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default InspectionsTab;
