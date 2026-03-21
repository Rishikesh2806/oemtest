import { useState, useEffect } from "react";
import { useAuth, api } from "../App";
import DashboardLayout from "../components/layout/DashboardLayout";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Switch } from "../components/ui/switch";
import { Badge } from "../components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "../components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { toast } from "sonner";
import {
  ClipboardCheck, Package, Upload, Camera, FileText, CheckCircle2,
  XCircle, AlertTriangle, Loader2, MapPin, Clock, Eye, User,
  Building2, RefreshCw, Plus, Trash2
} from "lucide-react";

const STATUS_CONFIG = {
  inspector_assigned: { label: "Assigned", color: "bg-blue-100 text-blue-700" },
  in_progress: { label: "In Progress", color: "bg-orange-100 text-orange-700" },
  report_submitted: { label: "Report Submitted", color: "bg-indigo-100 text-indigo-700" },
  approved: { label: "Approved", color: "bg-green-100 text-green-700" },
  rejected: { label: "Rejected", color: "bg-red-100 text-red-700" }
};

const InspectorDashboard = () => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [inspectorProfile, setInspectorProfile] = useState(null);
  const [assignments, setAssignments] = useState([]);
  const [selectedInspection, setSelectedInspection] = useState(null);
  const [showReportModal, setShowReportModal] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Report form state
  const [reportForm, setReportForm] = useState({
    result: "",
    remarks: "",
    images: [],
    reportFiles: [],
    measurements: {},
    defects: []
  });
  const [newDefect, setNewDefect] = useState("");
  const [newMeasurement, setNewMeasurement] = useState({ key: "", value: "" });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [profileRes, assignmentsRes] = await Promise.all([
        api.get("/inspector/profile"),
        api.get("/inspector/assignments")
      ]);
      setInspectorProfile(profileRes.data);
      setAssignments(assignmentsRes.data.inspections || []);
    } catch (error) {
      if (error.response?.status === 404) {
        // Not an inspector yet
        setInspectorProfile(null);
      } else {
        toast.error("Failed to load data");
      }
    } finally {
      setLoading(false);
    }
  };

  const toggleAvailability = async () => {
    try {
      const newStatus = !inspectorProfile.is_available;
      await api.put("/inspector/availability", { is_available: newStatus });
      setInspectorProfile(prev => ({ ...prev, is_available: newStatus }));
      toast.success(`You are now ${newStatus ? 'available' : 'unavailable'} for assignments`);
    } catch (error) {
      toast.error("Failed to update availability");
    }
  };

  const openReportModal = (inspection) => {
    setSelectedInspection(inspection);
    setReportForm({
      result: "",
      remarks: "",
      images: [],
      reportFiles: [],
      measurements: {},
      defects: []
    });
    setShowReportModal(true);
  };

  const addDefect = () => {
    if (newDefect.trim()) {
      setReportForm(prev => ({
        ...prev,
        defects: [...prev.defects, newDefect.trim()]
      }));
      setNewDefect("");
    }
  };

  const removeDefect = (index) => {
    setReportForm(prev => ({
      ...prev,
      defects: prev.defects.filter((_, i) => i !== index)
    }));
  };

  const addMeasurement = () => {
    if (newMeasurement.key && newMeasurement.value) {
      setReportForm(prev => ({
        ...prev,
        measurements: {
          ...prev.measurements,
          [newMeasurement.key]: newMeasurement.value
        }
      }));
      setNewMeasurement({ key: "", value: "" });
    }
  };

  const removeMeasurement = (key) => {
    setReportForm(prev => {
      const updated = { ...prev.measurements };
      delete updated[key];
      return { ...prev, measurements: updated };
    });
  };

  const handleImageUpload = async (e) => {
    const files = Array.from(e.target.files);
    if (files.length === 0) return;

    // For MVP, we'll use placeholder S3 paths
    // In production, implement actual S3 upload
    const imagePaths = files.map((file, idx) => 
      `inspections/${selectedInspection.inspection_id}/image_${Date.now()}_${idx}.jpg`
    );
    
    setReportForm(prev => ({
      ...prev,
      images: [...prev.images, ...imagePaths]
    }));
    
    toast.success(`${files.length} image(s) added`);
  };

  const handleReportUpload = async (e) => {
    const files = Array.from(e.target.files);
    if (files.length === 0) return;

    const reportPaths = files.map((file, idx) =>
      `inspections/${selectedInspection.inspection_id}/report_${Date.now()}_${idx}.pdf`
    );

    setReportForm(prev => ({
      ...prev,
      reportFiles: [...prev.reportFiles, ...reportPaths]
    }));

    toast.success(`${files.length} report(s) added`);
  };

  const submitReport = async () => {
    if (!reportForm.result) {
      toast.error("Please select inspection result (Pass/Fail)");
      return;
    }

    if (reportForm.images.length === 0) {
      toast.error("At least one inspection image is required");
      return;
    }

    setSubmitting(true);
    try {
      await api.post(`/inspector/orders/${selectedInspection.order_id}/report`, {
        result: reportForm.result,
        remarks: reportForm.remarks,
        images: reportForm.images,
        report_files: reportForm.reportFiles,
        measurements: reportForm.measurements,
        defects_found: reportForm.defects,
        geo_location: null // Could implement geolocation capture
      });

      toast.success("Inspection report submitted successfully!");
      setShowReportModal(false);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to submit report");
    } finally {
      setSubmitting(false);
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

  if (!inspectorProfile) {
    return (
      <DashboardLayout>
        <div className="max-w-2xl mx-auto">
          <Card className="border-slate-200">
            <CardContent className="py-12 text-center">
              <ClipboardCheck className="w-16 h-16 text-slate-300 mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-slate-800 mb-2">
                Not Registered as Inspector
              </h2>
              <p className="text-slate-500 mb-6">
                You need to register as an inspector to access this dashboard.
              </p>
              <Button 
                className="bg-orange-600 hover:bg-orange-700"
                onClick={() => window.location.href = '/inspector/register'}
              >
                Register as Inspector
              </Button>
            </CardContent>
          </Card>
        </div>
      </DashboardLayout>
    );
  }

  if (inspectorProfile.approval_status === "pending") {
    return (
      <DashboardLayout>
        <div className="max-w-2xl mx-auto">
          <Card className="border-yellow-200 bg-yellow-50">
            <CardContent className="py-12 text-center">
              <Clock className="w-16 h-16 text-yellow-500 mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-yellow-800 mb-2">
                Registration Pending Approval
              </h2>
              <p className="text-yellow-700">
                Your inspector registration is being reviewed. You'll be notified once approved.
              </p>
            </CardContent>
          </Card>
        </div>
      </DashboardLayout>
    );
  }

  const pendingAssignments = assignments.filter(a => 
    ['inspector_assigned', 'in_progress'].includes(a.status)
  );
  const completedAssignments = assignments.filter(a =>
    ['report_submitted', 'approved', 'rejected'].includes(a.status)
  );

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Inspector Dashboard</h1>
            <p className="text-slate-500">Manage your inspection assignments</p>
          </div>
          <Button variant="outline" onClick={fetchData}>
            <RefreshCw className="w-4 h-4 mr-2" /> Refresh
          </Button>
        </div>

        {/* Profile Card */}
        <Card className="border-slate-200">
          <CardContent className="py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-orange-100 rounded-full flex items-center justify-center">
                  <User className="w-6 h-6 text-orange-600" />
                </div>
                <div>
                  <p className="font-semibold text-slate-900">{inspectorProfile.name}</p>
                  <p className="text-sm text-slate-500">
                    {inspectorProfile.city}, {inspectorProfile.state}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <div className="text-right">
                  <p className="text-sm text-slate-500">Total Inspections</p>
                  <p className="text-xl font-bold text-slate-900">{inspectorProfile.total_inspections}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-slate-600">Available</span>
                  <Switch
                    checked={inspectorProfile.is_available}
                    onCheckedChange={toggleAvailability}
                    data-testid="availability-toggle"
                  />
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card className="border-blue-200 bg-blue-50">
            <CardContent className="py-4">
              <p className="text-xs text-blue-600 uppercase font-medium">Pending</p>
              <p className="text-2xl font-bold text-blue-700">{pendingAssignments.length}</p>
            </CardContent>
          </Card>
          <Card className="border-green-200 bg-green-50">
            <CardContent className="py-4">
              <p className="text-xs text-green-600 uppercase font-medium">Completed</p>
              <p className="text-2xl font-bold text-green-700">{completedAssignments.length}</p>
            </CardContent>
          </Card>
          <Card className="border-slate-200">
            <CardContent className="py-4">
              <p className="text-xs text-slate-500 uppercase font-medium">Rating</p>
              <p className="text-2xl font-bold text-slate-900">
                {inspectorProfile.avg_rating > 0 ? inspectorProfile.avg_rating.toFixed(1) : 'N/A'}
              </p>
            </CardContent>
          </Card>
          <Card className={inspectorProfile.is_available ? "border-green-200 bg-green-50" : "border-slate-200"}>
            <CardContent className="py-4">
              <p className="text-xs text-slate-500 uppercase font-medium">Status</p>
              <p className={`text-lg font-bold ${inspectorProfile.is_available ? 'text-green-700' : 'text-slate-500'}`}>
                {inspectorProfile.is_available ? 'Available' : 'Unavailable'}
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Pending Assignments */}
        <Card className="border-slate-200">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Package className="w-5 h-5 text-orange-600" />
              Active Assignments ({pendingAssignments.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            {pendingAssignments.length === 0 ? (
              <div className="text-center py-8 text-slate-500">
                <ClipboardCheck className="w-12 h-12 text-slate-300 mx-auto mb-2" />
                <p>No pending assignments</p>
              </div>
            ) : (
              <div className="space-y-4">
                {pendingAssignments.map((inspection) => {
                  const statusConfig = STATUS_CONFIG[inspection.status];
                  return (
                    <div 
                      key={inspection.inspection_id}
                      className="p-4 border border-slate-200 rounded-lg hover:border-orange-300 transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="flex items-center gap-2">
                            <p className="font-semibold text-slate-900">
                              Order: {inspection.order_id}
                            </p>
                            <Badge className={statusConfig?.color || 'bg-slate-100'}>
                              {statusConfig?.label || inspection.status}
                            </Badge>
                          </div>
                          <p className="text-sm text-slate-500 mt-1">
                            Type: {inspection.inspection_type === 'basic' ? 'Basic Inspection' : 'Certified'}
                          </p>
                          <p className="text-sm text-slate-500">
                            Fee: ₹{inspection.inspection_fee?.toLocaleString('en-IN')}
                          </p>
                        </div>
                        <Button 
                          onClick={() => openReportModal(inspection)}
                          className="bg-orange-600 hover:bg-orange-700"
                          data-testid={`submit-report-${inspection.inspection_id}`}
                        >
                          <FileText className="w-4 h-4 mr-2" /> Submit Report
                        </Button>
                      </div>
                      {inspection.buyer_notes && (
                        <div className="mt-3 p-2 bg-yellow-50 rounded text-sm text-yellow-700">
                          <strong>Buyer Notes:</strong> {inspection.buyer_notes}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Completed Assignments */}
        <Card className="border-slate-200">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-green-600" />
              Completed Inspections ({completedAssignments.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            {completedAssignments.length === 0 ? (
              <div className="text-center py-8 text-slate-500">
                <p>No completed inspections yet</p>
              </div>
            ) : (
              <div className="space-y-3">
                {completedAssignments.slice(0, 10).map((inspection) => {
                  const statusConfig = STATUS_CONFIG[inspection.status];
                  return (
                    <div 
                      key={inspection.inspection_id}
                      className="flex items-center justify-between p-3 bg-slate-50 rounded-lg"
                    >
                      <div>
                        <p className="font-medium text-slate-800">Order: {inspection.order_id}</p>
                        <p className="text-sm text-slate-500">
                          {new Date(inspection.inspection_date || inspection.created_at).toLocaleDateString()}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        {inspection.result && (
                          <Badge className={
                            inspection.result === 'pass' ? 'bg-green-100 text-green-700' :
                            inspection.result === 'fail' ? 'bg-red-100 text-red-700' :
                            'bg-yellow-100 text-yellow-700'
                          }>
                            {inspection.result.toUpperCase()}
                          </Badge>
                        )}
                        <Badge className={statusConfig?.color || 'bg-slate-100'}>
                          {statusConfig?.label || inspection.status}
                        </Badge>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Submit Report Modal */}
      <Dialog open={showReportModal} onOpenChange={setShowReportModal}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileText className="w-5 h-5 text-orange-600" />
              Submit Inspection Report
            </DialogTitle>
          </DialogHeader>
          
          {selectedInspection && (
            <div className="space-y-6 mt-4">
              {/* Order Info */}
              <div className="p-3 bg-slate-50 rounded-lg">
                <p className="text-sm text-slate-500">Order ID</p>
                <p className="font-semibold">{selectedInspection.order_id}</p>
              </div>

              {/* Result Selection */}
              <div>
                <Label className="text-sm font-medium">Inspection Result *</Label>
                <Select 
                  value={reportForm.result} 
                  onValueChange={(v) => setReportForm(prev => ({ ...prev, result: v }))}
                >
                  <SelectTrigger className="mt-1" data-testid="result-select">
                    <SelectValue placeholder="Select result" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="pass">
                      <div className="flex items-center gap-2">
                        <CheckCircle2 className="w-4 h-4 text-green-600" />
                        Pass
                      </div>
                    </SelectItem>
                    <SelectItem value="conditional_pass">
                      <div className="flex items-center gap-2">
                        <AlertTriangle className="w-4 h-4 text-yellow-600" />
                        Conditional Pass
                      </div>
                    </SelectItem>
                    <SelectItem value="fail">
                      <div className="flex items-center gap-2">
                        <XCircle className="w-4 h-4 text-red-600" />
                        Fail
                      </div>
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Remarks */}
              <div>
                <Label className="text-sm font-medium">Remarks / Observations</Label>
                <Textarea
                  placeholder="Describe your inspection findings..."
                  value={reportForm.remarks}
                  onChange={(e) => setReportForm(prev => ({ ...prev, remarks: e.target.value }))}
                  className="mt-1"
                  rows={3}
                  data-testid="remarks-input"
                />
              </div>

              {/* Image Upload */}
              <div>
                <Label className="text-sm font-medium">
                  Inspection Images * ({reportForm.images.length} uploaded)
                </Label>
                <div className="mt-1 flex items-center gap-2">
                  <input
                    type="file"
                    accept="image/*"
                    multiple
                    onChange={handleImageUpload}
                    className="hidden"
                    id="image-upload"
                  />
                  <label
                    htmlFor="image-upload"
                    className="flex items-center gap-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 rounded-lg cursor-pointer transition-colors"
                  >
                    <Camera className="w-4 h-4" />
                    Upload Images
                  </label>
                  <span className="text-sm text-slate-500">
                    {reportForm.images.length > 0 && `${reportForm.images.length} image(s) selected`}
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-1">
                  At least one image is mandatory for proof
                </p>
              </div>

              {/* Report Upload */}
              <div>
                <Label className="text-sm font-medium">
                  Report Documents (PDF) - Optional
                </Label>
                <div className="mt-1 flex items-center gap-2">
                  <input
                    type="file"
                    accept=".pdf"
                    multiple
                    onChange={handleReportUpload}
                    className="hidden"
                    id="report-upload"
                  />
                  <label
                    htmlFor="report-upload"
                    className="flex items-center gap-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 rounded-lg cursor-pointer transition-colors"
                  >
                    <Upload className="w-4 h-4" />
                    Upload PDF
                  </label>
                  <span className="text-sm text-slate-500">
                    {reportForm.reportFiles.length > 0 && `${reportForm.reportFiles.length} file(s) selected`}
                  </span>
                </div>
              </div>

              {/* Measurements */}
              <div>
                <Label className="text-sm font-medium">Measurements (Optional)</Label>
                <div className="mt-2 space-y-2">
                  {Object.entries(reportForm.measurements).map(([key, value]) => (
                    <div key={key} className="flex items-center gap-2 p-2 bg-slate-50 rounded">
                      <span className="text-sm font-medium capitalize">{key}:</span>
                      <span className="text-sm">{value}</span>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeMeasurement(key)}
                        className="ml-auto text-red-500"
                      >
                        <Trash2 className="w-3 h-3" />
                      </Button>
                    </div>
                  ))}
                  <div className="flex gap-2">
                    <Input
                      placeholder="Measurement name"
                      value={newMeasurement.key}
                      onChange={(e) => setNewMeasurement(prev => ({ ...prev, key: e.target.value }))}
                      className="flex-1"
                    />
                    <Input
                      placeholder="Value"
                      value={newMeasurement.value}
                      onChange={(e) => setNewMeasurement(prev => ({ ...prev, value: e.target.value }))}
                      className="flex-1"
                    />
                    <Button variant="outline" onClick={addMeasurement}>
                      <Plus className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </div>

              {/* Defects */}
              <div>
                <Label className="text-sm font-medium">Defects Found (Optional)</Label>
                <div className="mt-2 space-y-2">
                  {reportForm.defects.map((defect, idx) => (
                    <div key={idx} className="flex items-center gap-2 p-2 bg-red-50 rounded">
                      <XCircle className="w-4 h-4 text-red-500" />
                      <span className="text-sm text-red-700">{defect}</span>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeDefect(idx)}
                        className="ml-auto text-red-500"
                      >
                        <Trash2 className="w-3 h-3" />
                      </Button>
                    </div>
                  ))}
                  <div className="flex gap-2">
                    <Input
                      placeholder="Describe defect..."
                      value={newDefect}
                      onChange={(e) => setNewDefect(e.target.value)}
                      className="flex-1"
                    />
                    <Button variant="outline" onClick={addDefect}>
                      <Plus className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          )}

          <DialogFooter className="mt-6">
            <Button variant="outline" onClick={() => setShowReportModal(false)}>
              Cancel
            </Button>
            <Button
              onClick={submitReport}
              disabled={submitting}
              className="bg-orange-600 hover:bg-orange-700"
              data-testid="submit-report-btn"
            >
              {submitting ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <>
                  <CheckCircle2 className="w-4 h-4 mr-2" />
                  Submit Report
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </DashboardLayout>
  );
};

export default InspectorDashboard;
