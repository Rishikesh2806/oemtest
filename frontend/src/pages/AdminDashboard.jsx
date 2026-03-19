import { useState, useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth, api } from "../App";
import { usePermissions } from "../hooks/usePermissions";
import DashboardLayout from "../components/layout/DashboardLayout";
import PermittedActions from "../components/PermittedActions";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "../components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { toast } from "sonner";
import { 
  Users, FileText, Package, DollarSign, Building2, Wrench, FileCheck,
  CheckCircle2, XCircle, Loader2, Search, Plus, Edit, Trash2,
  Eye, Send, AlertCircle, RefreshCw, ChevronRight, Clock, Camera, Upload,
  Link, X, CheckCircle
} from "lucide-react";
import { Checkbox } from "../components/ui/checkbox";

// Tab configuration with required permissions
const TAB_CONFIG = {
  overview: { label: "Overview", icon: Package, permissions: [] },
  users: { label: "Users", icon: Users, permissions: ['users.view'] },
  vendors: { label: "Vendors", icon: Building2, permissions: ['vendors.view'] },
  machines: { label: "Machines", icon: Wrench, permissions: ['machines.view'] },
  rfqs: { label: "RFQs", icon: FileText, permissions: ['rfqs.view'] },
  quotes: { label: "Quotes", icon: DollarSign, permissions: ['quotes.view'] },
  orders: { label: "Orders", icon: Package, permissions: ['orders.view'] },
  drawings: { label: "Drawings", icon: FileCheck, permissions: ['rfqs.view'] },
  ndas: { label: "NDAs", icon: FileText, permissions: ['rfqs.view'] },
};

// Tab components
const TabButton = ({ active, onClick, icon: Icon, label, count }) => (
  <button
    onClick={onClick}
    className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
      active 
        ? "border-orange-600 text-orange-600" 
        : "border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300"
    }`}
  >
    <Icon className="w-4 h-4" />
    {label}
    {count !== undefined && (
      <span className={`ml-1 px-2 py-0.5 text-xs rounded-full ${
        active ? "bg-orange-100 text-orange-700" : "bg-slate-100 text-slate-600"
      }`}>
        {count}
      </span>
    )}
  </button>
);

// Status badge component
const StatusBadge = ({ status }) => {
  const statusStyles = {
    draft: "bg-slate-100 text-slate-600",
    submitted: "bg-blue-100 text-blue-700",
    analyzing: "bg-purple-100 text-purple-700",
    matching: "bg-cyan-100 text-cyan-700",
    quoted: "bg-amber-100 text-amber-700",
    po_issued: "bg-green-100 text-green-700",
    in_production: "bg-orange-100 text-orange-700",
    completed: "bg-green-100 text-green-700",
    cancelled: "bg-red-100 text-red-700",
    pending: "bg-amber-100 text-amber-700",
    accepted: "bg-green-100 text-green-700",
    rejected: "bg-red-100 text-red-700",
    paid: "bg-green-100 text-green-700",
    sent: "bg-blue-100 text-blue-700",
    signed: "bg-green-100 text-green-700",
    expired: "bg-red-100 text-red-700",
  };
  
  return (
    <span className={`px-2 py-1 text-xs font-medium rounded ${statusStyles[status] || "bg-slate-100 text-slate-600"}`}>
      {status?.replace("_", " ")}
    </span>
  );
};

// ============== OVERVIEW TAB ==============
const OverviewTab = ({ stats, pendingVendors, onApproveVendor, onRejectVendor, onRefresh, dashboardType = "admin" }) => (
  <div className="space-y-6">
    {/* Stats Cards */}
    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
      <Card className="border-slate-200">
        <CardContent className="pt-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-slate-100 rounded-lg flex items-center justify-center">
              <Users className="w-5 h-5 text-slate-600" />
            </div>
            <div>
              <p className="text-xl font-bold text-slate-900">{stats?.total_users || 0}</p>
              <p className="text-xs text-slate-500">Users</p>
            </div>
          </div>
        </CardContent>
      </Card>
      
      <Card className="border-slate-200">
        <CardContent className="pt-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center">
              <Building2 className="w-5 h-5 text-orange-600" />
            </div>
            <div>
              <p className="text-xl font-bold text-slate-900">{stats?.approved_vendors || 0}</p>
              <p className="text-xs text-slate-500">Vendors</p>
            </div>
          </div>
        </CardContent>
      </Card>
      
      <Card className="border-slate-200">
        <CardContent className="pt-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              <FileText className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <p className="text-xl font-bold text-slate-900">{stats?.total_rfqs || 0}</p>
              <p className="text-xs text-slate-500">RFQs</p>
            </div>
          </div>
        </CardContent>
      </Card>
      
      <Card className="border-slate-200">
        <CardContent className="pt-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-amber-100 rounded-lg flex items-center justify-center">
              <DollarSign className="w-5 h-5 text-amber-600" />
            </div>
            <div>
              <p className="text-xl font-bold text-slate-900">{stats?.total_quotes || 0}</p>
              <p className="text-xs text-slate-500">Quotes</p>
            </div>
          </div>
        </CardContent>
      </Card>
      
      <Card className="border-slate-200">
        <CardContent className="pt-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
              <Package className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <p className="text-xl font-bold text-slate-900">{stats?.total_orders || 0}</p>
              <p className="text-xs text-slate-500">Orders</p>
            </div>
          </div>
        </CardContent>
      </Card>
      
      <Card className="border-slate-200">
        <CardContent className="pt-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
              <FileCheck className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <p className="text-xl font-bold text-slate-900">{stats?.total_ndas || 0}</p>
              <p className="text-xs text-slate-500">NDAs</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
    
    {/* Permitted Quick Actions */}
    <PermittedActions 
      dashboardType={dashboardType} 
      title="Quick Actions"
      description="Available actions based on your permissions"
      columns={4}
    />
    
    {/* Pending Vendors */}
    <Card className="border-slate-200">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="font-heading text-lg flex items-center gap-2">
          <Building2 className="w-5 h-5 text-orange-600" />
          Pending Vendor Approvals ({stats?.pending_vendors || 0})
        </CardTitle>
        <Button variant="ghost" size="sm" onClick={onRefresh}>
          <RefreshCw className="w-4 h-4" />
        </Button>
      </CardHeader>
      <CardContent>
        {pendingVendors.length > 0 ? (
          <div className="space-y-3">
            {pendingVendors.map((vendor) => (
              <div
                key={vendor.vendor_id}
                className="flex items-center justify-between p-4 bg-slate-50 rounded-lg"
                data-testid={`pending-vendor-${vendor.vendor_id}`}
              >
                <div>
                  <p className="font-medium text-slate-900">{vendor.company_name}</p>
                  <p className="text-sm text-slate-500">
                    {vendor.city}, {vendor.country} • {vendor.industries?.slice(0, 2).join(", ")}
                  </p>
                  <div className="flex flex-wrap gap-1 mt-2">
                    {vendor.certifications?.slice(0, 3).map((cert, i) => (
                      <span key={i} className="text-xs bg-slate-200 text-slate-600 px-2 py-0.5 rounded">
                        {cert}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button
                    onClick={() => onApproveVendor(vendor.vendor_id)}
                    className="bg-green-600 hover:bg-green-700"
                    size="sm"
                  >
                    <CheckCircle2 className="w-4 h-4 mr-1" /> Approve
                  </Button>
                  <Button
                    onClick={() => onRejectVendor(vendor.vendor_id)}
                    variant="outline"
                    size="sm"
                    className="text-red-600 border-red-200 hover:bg-red-50"
                  >
                    <XCircle className="w-4 h-4 mr-1" /> Reject
                  </Button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8">
            <CheckCircle2 className="w-12 h-12 text-green-300 mx-auto mb-4" />
            <p className="text-slate-500">No pending approvals</p>
          </div>
        )}
      </CardContent>
    </Card>
  </div>
);

// ============== USERS TAB ==============
const UsersTab = ({ users, loading, onRefresh, onUpdateUser, onDeleteUser, onCreateUser, canEdit = true, canDelete = true, canCreate = true }) => {
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("all");
  const [editUser, setEditUser] = useState(null);
  const [editForm, setEditForm] = useState({ name: "", role: "", custom_role: "" });
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [addForm, setAddForm] = useState({ name: "", email: "", password: "", role: "", custom_role: "", company_name: "" });
  const [adding, setAdding] = useState(false);
  const [availableRoles, setAvailableRoles] = useState([]);
  const [loadingRoles, setLoadingRoles] = useState(false);
  
  // Fetch available roles
  useEffect(() => {
    const fetchRoles = async () => {
      setLoadingRoles(true);
      try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/admin/roles?include_base_roles=false`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (response.ok) {
          const data = await response.json();
          setAvailableRoles(data.roles || []);
        }
      } catch (error) {
        console.error('Failed to fetch roles:', error);
      } finally {
        setLoadingRoles(false);
      }
    };
    fetchRoles();
  }, []);
  
  const filteredUsers = users.filter(u => {
    const matchesSearch = u.name?.toLowerCase().includes(search.toLowerCase()) || 
                          u.email?.toLowerCase().includes(search.toLowerCase());
    const matchesRole = roleFilter === "all" || u.role === roleFilter;
    return matchesSearch && matchesRole;
  });
  
  const handleEdit = (user) => {
    setEditUser(user);
    setEditForm({ name: user.name, role: user.role, custom_role: user.custom_role || "", company_name: user.company_name || "" });
  };
  
  const handleSave = async () => {
    await onUpdateUser(editUser.user_id, editForm);
    setEditUser(null);
  };

  const handleAddUser = async () => {
    if (!addForm.email || !addForm.password || !addForm.name) {
      toast.error("Please fill all required fields");
      return;
    }
    setAdding(true);
    try {
      await onCreateUser(addForm);
      setShowAddDialog(false);
      setAddForm({ name: "", email: "", password: "", role: "", custom_role: "", company_name: "" });
    } finally {
      setAdding(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex gap-4 items-center">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <Input
            placeholder="Search users..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10"
          />
        </div>
        <Select value={roleFilter} onValueChange={setRoleFilter}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="All roles" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Roles</SelectItem>
            <SelectItem value="buyer">Buyers</SelectItem>
            <SelectItem value="vendor">Vendors</SelectItem>
            <SelectItem value="admin">Admins</SelectItem>
          </SelectContent>
        </Select>
        <Button variant="outline" size="sm" onClick={onRefresh}>
          <RefreshCw className="w-4 h-4" />
        </Button>
        {canCreate && (
          <Button onClick={() => setShowAddDialog(true)} className="bg-orange-600 hover:bg-orange-700">
            <Plus className="w-4 h-4 mr-2" /> Add User
          </Button>
        )}
      </div>
      
      {/* Users Table */}
      <Card className="border-slate-200">
        <CardContent className="p-0">
          <table className="w-full">
            <thead className="bg-slate-50 border-b">
              <tr>
                <th className="text-left p-4 text-xs font-bold uppercase text-slate-500">User</th>
                <th className="text-left p-4 text-xs font-bold uppercase text-slate-500">Role</th>
                <th className="text-left p-4 text-xs font-bold uppercase text-slate-500">Company</th>
                <th className="text-left p-4 text-xs font-bold uppercase text-slate-500">Created</th>
                {(canEdit || canDelete) && (
                  <th className="text-right p-4 text-xs font-bold uppercase text-slate-500">Actions</th>
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredUsers.map((user) => (
                <tr key={user.user_id} className="hover:bg-slate-50" data-testid={`user-row-${user.user_id}`}>
                  <td className="p-4">
                    <div>
                      <p className="font-medium text-slate-900">{user.name}</p>
                      <p className="text-sm text-slate-500">{user.email}</p>
                    </div>
                  </td>
                  <td className="p-4">
                    <StatusBadge status={user.role} />
                  </td>
                  <td className="p-4 text-slate-600">{user.company_name || "-"}</td>
                  <td className="p-4 text-sm text-slate-500">
                    {new Date(user.created_at).toLocaleDateString()}
                  </td>
                  {(canEdit || canDelete) && (
                    <td className="p-4 text-right">
                      <div className="flex justify-end gap-2">
                        {canEdit && (
                          <Button variant="ghost" size="sm" onClick={() => handleEdit(user)}>
                            <Edit className="w-4 h-4" />
                          </Button>
                        )}
                        {canDelete && (
                          <Button 
                            variant="ghost" 
                            size="sm" 
                            className="text-red-600 hover:bg-red-50"
                            onClick={() => onDeleteUser(user.user_id)}
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        )}
                      </div>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
          {filteredUsers.length === 0 && (
            <div className="text-center py-12 text-slate-500">No users found</div>
          )}
        </CardContent>
      </Card>
      
      {/* Edit Dialog */}
      <Dialog open={!!editUser} onOpenChange={() => setEditUser(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Edit User</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            <div>
              <Label>Name</Label>
              <Input
                value={editForm.name}
                onChange={(e) => setEditForm(prev => ({ ...prev, name: e.target.value }))}
                data-testid="edit-user-name"
              />
            </div>
            <div>
              <Label>Company Name</Label>
              <Input
                value={editForm.company_name || ""}
                onChange={(e) => setEditForm(prev => ({ ...prev, company_name: e.target.value }))}
                data-testid="edit-user-company"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Base Role</Label>
                <Select 
                  value={editForm.role || "none"} 
                  onValueChange={(v) => setEditForm(prev => ({ ...prev, role: v === "none" ? "" : v }))}
                >
                  <SelectTrigger data-testid="edit-user-role">
                    <SelectValue placeholder="None" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">None</SelectItem>
                    <SelectItem value="buyer">Buyer</SelectItem>
                    <SelectItem value="vendor">Vendor</SelectItem>
                    <SelectItem value="admin">Admin</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Custom Role</Label>
                <Select 
                  value={editForm.custom_role || "none"} 
                  onValueChange={(v) => setEditForm(prev => ({ ...prev, custom_role: v === "none" ? "" : v }))}
                >
                  <SelectTrigger data-testid="edit-user-custom-role">
                    <SelectValue placeholder="None" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">None</SelectItem>
                    {availableRoles.map(role => (
                      <SelectItem key={role.role_id} value={role.role_id}>
                        <div className="flex items-center gap-2">
                          <div 
                            className="w-2 h-2 rounded-full" 
                            style={{ backgroundColor: role.color || '#6b7280' }}
                          />
                          {role.name}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            {editForm.custom_role && (
              <p className="text-xs text-muted-foreground">
                User will have permissions from both {editForm.role} role and {availableRoles.find(r => r.role_id === editForm.custom_role)?.name || editForm.custom_role} role
              </p>
            )}
            <Button onClick={handleSave} className="w-full bg-orange-600 hover:bg-orange-700" data-testid="save-user-btn">
              Save Changes
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Add User Dialog */}
      <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Add New User</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            <div>
              <Label>Name *</Label>
              <Input
                value={addForm.name}
                onChange={(e) => setAddForm(prev => ({ ...prev, name: e.target.value }))}
                placeholder="Full name"
                data-testid="add-user-name"
              />
            </div>
            <div>
              <Label>Email *</Label>
              <Input
                type="email"
                value={addForm.email}
                onChange={(e) => setAddForm(prev => ({ ...prev, email: e.target.value }))}
                placeholder="email@example.com"
                data-testid="add-user-email"
              />
            </div>
            <div>
              <Label>Password *</Label>
              <Input
                type="password"
                value={addForm.password}
                onChange={(e) => setAddForm(prev => ({ ...prev, password: e.target.value }))}
                placeholder="Minimum 6 characters"
                data-testid="add-user-password"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Base Role</Label>
                <Select 
                  value={addForm.role || "none"} 
                  onValueChange={(v) => setAddForm(prev => ({ ...prev, role: v === "none" ? "" : v }))}
                >
                  <SelectTrigger data-testid="add-user-role">
                    <SelectValue placeholder="None" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">None</SelectItem>
                    <SelectItem value="buyer">Buyer</SelectItem>
                    <SelectItem value="vendor">Vendor</SelectItem>
                    <SelectItem value="admin">Admin</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Custom Role</Label>
                <Select 
                  value={addForm.custom_role || "none"} 
                  onValueChange={(v) => setAddForm(prev => ({ ...prev, custom_role: v === "none" ? "" : v }))}
                >
                  <SelectTrigger data-testid="add-user-custom-role">
                    <SelectValue placeholder="Optional" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">None</SelectItem>
                    {availableRoles.map(role => (
                      <SelectItem key={role.role_id} value={role.role_id}>
                        <div className="flex items-center gap-2">
                          <div 
                            className="w-2 h-2 rounded-full" 
                            style={{ backgroundColor: role.color || '#6b7280' }}
                          />
                          {role.name}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            {addForm.custom_role && (
              <p className="text-xs text-muted-foreground">
                User will have permissions from both {addForm.role} role and {availableRoles.find(r => r.role_id === addForm.custom_role)?.name || addForm.custom_role} role
              </p>
            )}
            <div>
              <Label>Company Name</Label>
              <Input
                value={addForm.company_name}
                onChange={(e) => setAddForm(prev => ({ ...prev, company_name: e.target.value }))}
                placeholder="Company name (optional)"
                data-testid="add-user-company"
              />
            </div>
            <Button onClick={handleAddUser} disabled={adding} className="w-full bg-orange-600 hover:bg-orange-700" data-testid="create-user-btn">
              {adding ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Plus className="w-4 h-4 mr-2" />}
              Create User
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

// ============== RFQs TAB ==============
const RFQsTab = ({ rfqs, loading, onRefresh, onUpdateRFQ, onDeleteRFQ, canEdit = true, canDelete = true, canMatchVendors = true }) => {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [editRFQ, setEditRFQ] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [matchRFQ, setMatchRFQ] = useState(null);
  const [matchDialogOpen, setMatchDialogOpen] = useState(false);
  const [vendorSearch, setVendorSearch] = useState("");
  const [vendorCategory, setVendorCategory] = useState("all");
  const [availableVendors, setAvailableVendors] = useState([]);
  const [selectedVendors, setSelectedVendors] = useState([]);
  const [matchedVendors, setMatchedVendors] = useState([]);
  const [loadingVendors, setLoadingVendors] = useState(false);
  const [matchingInProgress, setMatchingInProgress] = useState(false);
  const [viewMatchesRFQ, setViewMatchesRFQ] = useState(null);
  const [viewRFQ, setViewRFQ] = useState(null);
  const [viewRFQData, setViewRFQData] = useState(null);
  const [loadingRFQDetails, setLoadingRFQDetails] = useState(false);
  const [downloadingPDF, setDownloadingPDF] = useState(false);
  
  const filteredRFQs = rfqs.filter(r => {
    const matchesSearch = r.title?.toLowerCase().includes(search.toLowerCase()) ||
                          r.rfq_id?.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = statusFilter === "all" || r.status === statusFilter;
    return matchesSearch && matchesStatus;
  });
  
  // View RFQ Details
  const openViewRFQ = async (rfq) => {
    setViewRFQ(rfq);
    setLoadingRFQDetails(true);
    try {
      const res = await api.get(`/admin/rfqs/${rfq.rfq_id}`);
      setViewRFQData(res.data);
    } catch (error) {
      toast.error("Failed to load RFQ details");
      setViewRFQ(null);
    } finally {
      setLoadingRFQDetails(false);
    }
  };
  
  // Download RFQ as PDF
  const downloadPDF = async (rfqId) => {
    setDownloadingPDF(true);
    try {
      const res = await api.get(`/admin/rfqs/${rfqId}/pdf`, { responseType: 'blob' });
      const blob = new Blob([res.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `RFQ_${rfqId}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      toast.success("PDF downloaded successfully");
    } catch (error) {
      toast.error("Failed to download PDF");
    } finally {
      setDownloadingPDF(false);
    }
  };
  
  const handleEdit = (rfq) => {
    setEditRFQ(rfq);
    setEditForm({ 
      title: rfq.title, 
      status: rfq.status, 
      material_type: rfq.material_type,
      quantity: rfq.quantity,
      tolerance: rfq.tolerance
    });
  };
  
  const handleSave = async () => {
    await onUpdateRFQ(editRFQ.rfq_id, editForm);
    setEditRFQ(null);
  };
  
  // Open match vendors dialog
  const openMatchDialog = async (rfq) => {
    setMatchRFQ(rfq);
    setSelectedVendors([]);
    setMatchDialogOpen(true);
    await loadVendors();
    await loadMatchedVendors(rfq.rfq_id);
  };
  
  // Load vendors for matching
  const loadVendors = async (searchTerm = "", category = "") => {
    setLoadingVendors(true);
    try {
      const params = new URLSearchParams();
      if (searchTerm) params.append("search", searchTerm);
      if (category && category !== "all") params.append("category", category);
      params.append("approved_only", "true");
      
      const res = await api.get(`/admin/vendors/search?${params.toString()}`);
      setAvailableVendors(res.data.vendors || []);
    } catch (error) {
      toast.error("Failed to load vendors");
    } finally {
      setLoadingVendors(false);
    }
  };
  
  // Load matched vendors for an RFQ
  const loadMatchedVendors = async (rfqId) => {
    try {
      const res = await api.get(`/admin/rfq/${rfqId}/matches`);
      setMatchedVendors(res.data.matches || []);
    } catch (error) {
      console.error("Failed to load matched vendors:", error);
      setMatchedVendors([]);
    }
  };
  
  // Toggle vendor selection
  const toggleVendorSelection = (vendor) => {
    setSelectedVendors(prev => {
      const exists = prev.find(v => v.vendor_id === vendor.vendor_id);
      if (exists) {
        return prev.filter(v => v.vendor_id !== vendor.vendor_id);
      }
      return [...prev, vendor];
    });
  };
  
  // Match selected vendors
  const handleMatchVendors = async () => {
    if (selectedVendors.length === 0) {
      toast.error("Please select at least one vendor");
      return;
    }
    
    setMatchingInProgress(true);
    try {
      const vendorIds = selectedVendors.map(v => v.vendor_id);
      await api.post(`/admin/rfq/${matchRFQ.rfq_id}/match-vendors`, { vendor_ids: vendorIds });
      toast.success(`Successfully matched ${selectedVendors.length} vendor(s)`);
      setMatchDialogOpen(false);
      setSelectedVendors([]);
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to match vendors");
    } finally {
      setMatchingInProgress(false);
    }
  };
  
  // Remove a match
  const handleRemoveMatch = async (vendorId) => {
    try {
      await api.delete(`/admin/rfq/${viewMatchesRFQ.rfq_id}/match/${vendorId}`);
      toast.success("Match removed");
      await loadMatchedVendors(viewMatchesRFQ.rfq_id);
    } catch (error) {
      toast.error("Failed to remove match");
    }
  };
  
  // Handle vendor search
  useEffect(() => {
    if (matchDialogOpen) {
      const timeoutId = setTimeout(() => {
        loadVendors(vendorSearch, vendorCategory);
      }, 300);
      return () => clearTimeout(timeoutId);
    }
  }, [vendorSearch, vendorCategory, matchDialogOpen]);

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex gap-4 items-center">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <Input
            placeholder="Search RFQs..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10"
          />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="All statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="draft">Draft</SelectItem>
            <SelectItem value="submitted">Submitted</SelectItem>
            <SelectItem value="analyzing">Analyzing</SelectItem>
            <SelectItem value="matching">Matching</SelectItem>
            <SelectItem value="quoted">Quoted</SelectItem>
            <SelectItem value="completed">Completed</SelectItem>
          </SelectContent>
        </Select>
        <Button variant="outline" size="sm" onClick={onRefresh}>
          <RefreshCw className="w-4 h-4" />
        </Button>
      </div>
      
      {/* RFQs Table */}
      <Card className="border-slate-200">
        <CardContent className="p-0">
          <table className="w-full">
            <thead className="bg-slate-50 border-b">
              <tr>
                <th className="text-left p-4 text-xs font-bold uppercase text-slate-500">RFQ</th>
                <th className="text-left p-4 text-xs font-bold uppercase text-slate-500">Buyer</th>
                <th className="text-left p-4 text-xs font-bold uppercase text-slate-500">Material</th>
                <th className="text-left p-4 text-xs font-bold uppercase text-slate-500">Matched</th>
                <th className="text-left p-4 text-xs font-bold uppercase text-slate-500">Status</th>
                <th className="text-left p-4 text-xs font-bold uppercase text-slate-500">Created</th>
                <th className="text-right p-4 text-xs font-bold uppercase text-slate-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredRFQs.map((rfq) => (
                <tr key={rfq.rfq_id} className="hover:bg-slate-50" data-testid={`rfq-row-${rfq.rfq_id}`}>
                  <td className="p-4">
                    <div>
                      <p className="font-medium text-slate-900">{rfq.title}</p>
                      <p className="text-xs text-slate-500 font-mono">{rfq.rfq_id}</p>
                    </div>
                  </td>
                  <td className="p-4">
                    <div>
                      <p className="text-sm text-slate-900">{rfq.buyer_info?.name || "-"}</p>
                      <p className="text-xs text-slate-500">{rfq.buyer_info?.email}</p>
                    </div>
                  </td>
                  <td className="p-4 text-slate-600">{rfq.material_type}</td>
                  <td className="p-4">
                    <button 
                      className="flex items-center gap-1 text-sm text-orange-600 hover:underline"
                      onClick={() => { setViewMatchesRFQ(rfq); loadMatchedVendors(rfq.rfq_id); }}
                      data-testid={`view-matches-${rfq.rfq_id}`}
                    >
                      <Users className="w-4 h-4" />
                      {rfq.matched_vendors?.length || 0} vendors
                    </button>
                  </td>
                  <td className="p-4"><StatusBadge status={rfq.status} /></td>
                  <td className="p-4 text-sm text-slate-500">
                    {new Date(rfq.created_at).toLocaleDateString()}
                  </td>
                  <td className="p-4 text-right">
                    <div className="flex justify-end gap-2">
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        onClick={() => openViewRFQ(rfq)}
                        className="text-blue-600 hover:bg-blue-50"
                        data-testid={`view-rfq-${rfq.rfq_id}`}
                      >
                        <Eye className="w-4 h-4" />
                      </Button>
                      {canMatchVendors && (
                        <Button 
                          variant="outline" 
                          size="sm" 
                          onClick={() => openMatchDialog(rfq)}
                          className="text-orange-600 border-orange-200 hover:bg-orange-50"
                          data-testid={`match-vendors-${rfq.rfq_id}`}
                        >
                          <Link className="w-4 h-4 mr-1" /> Match
                        </Button>
                      )}
                      {canEdit && (
                        <Button variant="ghost" size="sm" onClick={() => handleEdit(rfq)}>
                          <Edit className="w-4 h-4" />
                        </Button>
                      )}
                      {canDelete && (
                        <Button 
                          variant="ghost" 
                          size="sm" 
                          className="text-red-600 hover:bg-red-50"
                          onClick={() => onDeleteRFQ(rfq.rfq_id)}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {filteredRFQs.length === 0 && (
            <div className="text-center py-12 text-slate-500">No RFQs found</div>
          )}
        </CardContent>
      </Card>
      
      {/* Edit Dialog */}
      <Dialog open={!!editRFQ} onOpenChange={() => setEditRFQ(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit RFQ</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            <div>
              <Label>Title</Label>
              <Input
                value={editForm.title}
                onChange={(e) => setEditForm(prev => ({ ...prev, title: e.target.value }))}
              />
            </div>
            <div>
              <Label>Status</Label>
              <Select value={editForm.status} onValueChange={(v) => setEditForm(prev => ({ ...prev, status: v }))}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="draft">Draft</SelectItem>
                  <SelectItem value="submitted">Submitted</SelectItem>
                  <SelectItem value="analyzing">Analyzing</SelectItem>
                  <SelectItem value="matching">Matching</SelectItem>
                  <SelectItem value="quoted">Quoted</SelectItem>
                  <SelectItem value="po_issued">PO Issued</SelectItem>
                  <SelectItem value="completed">Completed</SelectItem>
                  <SelectItem value="cancelled">Cancelled</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Material</Label>
                <Input
                  value={editForm.material_type}
                  onChange={(e) => setEditForm(prev => ({ ...prev, material_type: e.target.value }))}
                />
              </div>
              <div>
                <Label>Quantity</Label>
                <Input
                  type="number"
                  value={editForm.quantity}
                  onChange={(e) => setEditForm(prev => ({ ...prev, quantity: parseInt(e.target.value) }))}
                />
              </div>
            </div>
            <Button onClick={handleSave} className="w-full bg-orange-600 hover:bg-orange-700">
              Save Changes
            </Button>
          </div>
        </DialogContent>
      </Dialog>
      
      {/* Match Vendors Dialog */}
      <Dialog open={matchDialogOpen} onOpenChange={setMatchDialogOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Link className="w-5 h-5 text-orange-600" />
              Match Vendors to RFQ
            </DialogTitle>
            {matchRFQ && (
              <p className="text-sm text-slate-500">
                {matchRFQ.title} • {matchRFQ.material_type} • Qty: {matchRFQ.quantity}
              </p>
            )}
          </DialogHeader>
          
          <div className="flex gap-4 overflow-hidden flex-1">
            {/* Left: Vendor Search */}
            <div className="flex-1 flex flex-col border-r pr-4">
              <div className="space-y-3 mb-4">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <Input 
                    placeholder="Search vendors by name..."
                    value={vendorSearch}
                    onChange={(e) => setVendorSearch(e.target.value)}
                    className="pl-10"
                  />
                </div>
                <Select value={vendorCategory} onValueChange={setVendorCategory}>
                  <SelectTrigger>
                    <SelectValue placeholder="Filter by capability" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Categories</SelectItem>
                    <SelectItem value="CNC">CNC Machining</SelectItem>
                    <SelectItem value="VMC">VMC</SelectItem>
                    <SelectItem value="HMC">HMC</SelectItem>
                    <SelectItem value="Lathe">Lathe</SelectItem>
                    <SelectItem value="Milling">Milling</SelectItem>
                    <SelectItem value="Casting">Casting</SelectItem>
                    <SelectItem value="Forging">Forging</SelectItem>
                    <SelectItem value="Sheet Metal">Sheet Metal</SelectItem>
                    <SelectItem value="Grinding">Grinding</SelectItem>
                    <SelectItem value="Welding">Welding</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <div className="flex-1 overflow-y-auto space-y-2 max-h-[400px]">
                {loadingVendors ? (
                  <div className="text-center py-8 text-slate-500">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
                    Loading vendors...
                  </div>
                ) : availableVendors.length === 0 ? (
                  <div className="text-center py-8 text-slate-500">No vendors found</div>
                ) : (
                  availableVendors.map(vendor => {
                    const isSelected = selectedVendors.some(v => v.vendor_id === vendor.vendor_id);
                    const isAlreadyMatched = matchedVendors.some(m => m.vendor_id === vendor.vendor_id);
                    
                    return (
                      <div 
                        key={vendor.vendor_id}
                        className={`p-3 rounded-lg border cursor-pointer transition-all ${
                          isAlreadyMatched ? 'bg-green-50 border-green-200 opacity-60' :
                          isSelected ? 'bg-orange-50 border-orange-300' : 'bg-white border-slate-200 hover:border-orange-200'
                        }`}
                        onClick={() => !isAlreadyMatched && toggleVendorSelection(vendor)}
                        data-testid={`vendor-${vendor.vendor_id}`}
                      >
                        <div className="flex justify-between items-start">
                          <div className="flex-1">
                            <div className="flex items-center gap-2">
                              <p className="font-medium text-slate-900">{vendor.company_name}</p>
                              {isAlreadyMatched && (
                                <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">Already Matched</span>
                              )}
                              {vendor.is_approved && !isAlreadyMatched && (
                                <CheckCircle className="w-4 h-4 text-green-500" />
                              )}
                            </div>
                            <p className="text-xs text-slate-500">{vendor.city}, {vendor.state}</p>
                            <div className="flex flex-wrap gap-1 mt-1">
                              {vendor.machine_categories?.slice(0, 3).map(cat => (
                                <span key={cat} className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded">{cat}</span>
                              ))}
                              {vendor.machines_count > 0 && (
                                <span className="text-xs text-slate-500">{vendor.machines_count} machines</span>
                              )}
                            </div>
                          </div>
                          {!isAlreadyMatched && (
                            <Checkbox 
                              checked={isSelected}
                              className="mt-1"
                              onCheckedChange={() => toggleVendorSelection(vendor)}
                            />
                          )}
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
            
            {/* Right: Selected Vendors */}
            <div className="w-64 flex flex-col">
              <h4 className="font-medium text-slate-900 mb-3 flex items-center gap-2">
                <Users className="w-4 h-4 text-orange-600" />
                Selected ({selectedVendors.length})
              </h4>
              
              <div className="flex-1 overflow-y-auto space-y-2 max-h-[400px]">
                {selectedVendors.length === 0 ? (
                  <p className="text-sm text-slate-400 text-center py-4">Select vendors from the list</p>
                ) : (
                  selectedVendors.map(vendor => (
                    <div key={vendor.vendor_id} className="p-2 bg-orange-50 rounded border border-orange-200 flex justify-between items-center">
                      <div>
                        <p className="text-sm font-medium text-slate-900">{vendor.company_name}</p>
                        <p className="text-xs text-slate-500">{vendor.city}</p>
                      </div>
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        onClick={() => toggleVendorSelection(vendor)}
                        className="text-slate-400 hover:text-red-500"
                      >
                        <X className="w-4 h-4" />
                      </Button>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
          
          <DialogFooter className="border-t pt-4 mt-4">
            <Button variant="outline" onClick={() => setMatchDialogOpen(false)}>Cancel</Button>
            <Button 
              onClick={handleMatchVendors} 
              disabled={selectedVendors.length === 0 || matchingInProgress}
              className="bg-orange-600 hover:bg-orange-700"
              data-testid="confirm-match-btn"
            >
              {matchingInProgress ? (
                <><Loader2 className="w-4 h-4 animate-spin mr-2" /> Matching...</>
              ) : (
                <><Link className="w-4 h-4 mr-2" /> Match {selectedVendors.length} Vendor(s)</>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* View Matched Vendors Dialog */}
      <Dialog open={!!viewMatchesRFQ} onOpenChange={() => setViewMatchesRFQ(null)}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Users className="w-5 h-5 text-orange-600" />
              Matched Vendors
            </DialogTitle>
            {viewMatchesRFQ && (
              <p className="text-sm text-slate-500">{viewMatchesRFQ.title}</p>
            )}
          </DialogHeader>
          
          <div className="space-y-3 mt-4">
            {matchedVendors.length === 0 ? (
              <div className="text-center py-8 text-slate-500">
                <Users className="w-12 h-12 mx-auto mb-2 text-slate-300" />
                <p>No vendors matched yet</p>
                {canMatchVendors && (
                  <Button 
                    variant="outline" 
                    size="sm" 
                    className="mt-4"
                    onClick={() => { setViewMatchesRFQ(null); openMatchDialog(viewMatchesRFQ); }}
                  >
                    <Plus className="w-4 h-4 mr-1" /> Match Vendors
                  </Button>
                )}
              </div>
            ) : (
              matchedVendors.map(match => (
                <div key={match.vendor_id} className="p-4 border rounded-lg bg-white">
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <p className="font-medium text-slate-900">{match.vendor_info?.company_name || "Unknown Vendor"}</p>
                        <span className={`text-xs px-2 py-0.5 rounded ${
                          match.status === 'quoted' ? 'bg-green-100 text-green-700' :
                          match.status === 'viewed' ? 'bg-blue-100 text-blue-700' :
                          match.status === 'responded' ? 'bg-purple-100 text-purple-700' :
                          'bg-slate-100 text-slate-600'
                        }`}>
                          {match.status?.toUpperCase()}
                        </span>
                        {match.match_type === 'manual' && (
                          <span className="text-xs bg-orange-100 text-orange-700 px-2 py-0.5 rounded">Manual</span>
                        )}
                      </div>
                      <p className="text-sm text-slate-500">{match.vendor_info?.city}, {match.vendor_info?.state}</p>
                      {match.has_quoted && match.quote_info && (
                        <div className="mt-2 p-2 bg-green-50 rounded text-sm">
                          <span className="font-medium text-green-700">
                            Quote: ₹{match.quote_info.total_price?.toLocaleString('en-IN')}
                          </span>
                          <span className="text-green-600 ml-2">({match.quote_info.status})</span>
                        </div>
                      )}
                      <p className="text-xs text-slate-400 mt-1">
                        Matched: {new Date(match.created_at).toLocaleString()}
                      </p>
                    </div>
                    {canMatchVendors && (
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        className="text-red-500 hover:bg-red-50"
                        onClick={() => handleRemoveMatch(match.vendor_id)}
                        data-testid={`remove-match-${match.vendor_id}`}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
          
          {matchedVendors.length > 0 && canMatchVendors && (
            <div className="border-t pt-4 mt-4">
              <Button 
                variant="outline" 
                onClick={() => { setViewMatchesRFQ(null); openMatchDialog(viewMatchesRFQ); }}
                className="w-full"
              >
                <Plus className="w-4 h-4 mr-1" /> Add More Vendors
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>
      
      {/* View RFQ Details Dialog */}
      <Dialog open={!!viewRFQ} onOpenChange={() => { setViewRFQ(null); setViewRFQData(null); }}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <div className="flex items-center justify-between">
              <DialogTitle className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-orange-600" />
                RFQ Details
              </DialogTitle>
              <Button
                variant="outline"
                size="sm"
                onClick={() => downloadPDF(viewRFQ?.rfq_id)}
                disabled={downloadingPDF || !viewRFQData}
                className="text-orange-600 border-orange-200 hover:bg-orange-50"
                data-testid="download-pdf-btn"
              >
                {downloadingPDF ? (
                  <><Loader2 className="w-4 h-4 animate-spin mr-2" /> Generating...</>
                ) : (
                  <><FileCheck className="w-4 h-4 mr-2" /> Download PDF</>
                )}
              </Button>
            </div>
          </DialogHeader>
          
          {loadingRFQDetails ? (
            <div className="text-center py-12">
              <Loader2 className="w-8 h-8 animate-spin mx-auto text-orange-600" />
              <p className="text-slate-500 mt-2">Loading RFQ details...</p>
            </div>
          ) : viewRFQData ? (
            <div className="space-y-6 mt-4">
              {/* Header Info */}
              <div className="flex items-center justify-between bg-orange-50 p-4 rounded-lg border border-orange-200">
                <div>
                  <p className="text-xs text-slate-500">RFQ ID</p>
                  <p className="font-mono text-sm font-medium">{viewRFQData.rfq_id}</p>
                </div>
                <div className="text-center">
                  <p className="text-xs text-slate-500">Status</p>
                  <StatusBadge status={viewRFQData.status} />
                </div>
                <div className="text-right">
                  <p className="text-xs text-slate-500">Created</p>
                  <p className="text-sm">{new Date(viewRFQData.created_at).toLocaleDateString()}</p>
                </div>
              </div>
              
              {/* Buyer Details */}
              <div>
                <h4 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
                  <Users className="w-4 h-4 text-slate-400" /> Buyer Details
                </h4>
                <div className="grid grid-cols-2 gap-4 bg-slate-50 p-4 rounded-lg">
                  <div>
                    <p className="text-xs text-slate-500">Name</p>
                    <p className="font-medium">{viewRFQData.buyer_info?.name || 'N/A'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Company</p>
                    <p className="font-medium">{viewRFQData.buyer_info?.company_name || 'N/A'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Email</p>
                    <p className="text-sm">{viewRFQData.buyer_info?.email || 'N/A'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Phone</p>
                    <p className="text-sm">{viewRFQData.buyer_info?.phone || 'N/A'}</p>
                  </div>
                  {(viewRFQData.buyer_info?.city || viewRFQData.buyer_info?.state) && (
                    <div className="col-span-2">
                      <p className="text-xs text-slate-500">Location</p>
                      <p className="text-sm">{[viewRFQData.buyer_info?.city, viewRFQData.buyer_info?.state].filter(Boolean).join(', ')}</p>
                    </div>
                  )}
                </div>
              </div>
              
              {/* RFQ Details */}
              <div>
                <h4 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
                  <FileText className="w-4 h-4 text-slate-400" /> RFQ Information
                </h4>
                <div className="grid grid-cols-2 gap-4 bg-slate-50 p-4 rounded-lg">
                  <div className="col-span-2">
                    <p className="text-xs text-slate-500">Part Name / Title</p>
                    <p className="font-medium text-lg">{viewRFQData.title || 'N/A'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Material</p>
                    <p className="font-medium">{viewRFQData.material_type || 'N/A'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Quantity</p>
                    <p className="font-medium">{viewRFQData.quantity || 'N/A'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Tolerance</p>
                    <p className="font-medium">{viewRFQData.tolerance ? `${viewRFQData.tolerance} mm` : 'N/A'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Surface Finish</p>
                    <p className="font-medium">{viewRFQData.surface_finish || 'N/A'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Deadline</p>
                    <p className="font-medium">{viewRFQData.deadline || 'As per RFQ'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Delivery Location</p>
                    <p className="font-medium">{viewRFQData.delivery_location || viewRFQData.delivery_address || 'N/A'}</p>
                  </div>
                </div>
                
                {viewRFQData.description && (
                  <div className="mt-4">
                    <p className="text-xs text-slate-500 mb-1">Description / Specifications</p>
                    <div className="bg-white border rounded-lg p-3 text-sm whitespace-pre-wrap">
                      {viewRFQData.description}
                    </div>
                  </div>
                )}
              </div>
              
              {/* AI Analysis */}
              {viewRFQData.ai_summary && (viewRFQData.ai_summary.recommended_processes?.length > 0 || viewRFQData.ai_summary.overall_dimensions) && (
                <div>
                  <h4 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
                    <Wrench className="w-4 h-4 text-slate-400" /> Technical Analysis (AI)
                  </h4>
                  <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
                    {viewRFQData.ai_summary.recommended_processes?.length > 0 && (
                      <div className="mb-3">
                        <p className="text-xs text-blue-600 mb-1">Recommended Processes</p>
                        <div className="flex flex-wrap gap-2">
                          {viewRFQData.ai_summary.recommended_processes.map((proc, i) => (
                            <span key={i} className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded">{proc}</span>
                          ))}
                        </div>
                      </div>
                    )}
                    {viewRFQData.ai_summary.overall_dimensions && Object.keys(viewRFQData.ai_summary.overall_dimensions).length > 0 && (
                      <div className="mb-3">
                        <p className="text-xs text-blue-600 mb-1">Dimensions</p>
                        <p className="text-sm">
                          {Object.entries(viewRFQData.ai_summary.overall_dimensions)
                            .filter(([k, v]) => v)
                            .map(([k, v]) => `${k}: ${v}mm`)
                            .join(' × ')}
                        </p>
                      </div>
                    )}
                    {viewRFQData.ai_summary.part_geometry && (
                      <div className="mb-3">
                        <p className="text-xs text-blue-600 mb-1">Part Geometry</p>
                        <p className="text-sm">{viewRFQData.ai_summary.part_geometry}</p>
                      </div>
                    )}
                    {viewRFQData.ai_summary.complexity_score > 0 && (
                      <div>
                        <p className="text-xs text-blue-600 mb-1">Complexity Score</p>
                        <p className="text-sm font-medium">{viewRFQData.ai_summary.complexity_score}/10</p>
                      </div>
                    )}
                  </div>
                </div>
              )}
              
              {/* Drawings / Attachments */}
              {viewRFQData.drawings && viewRFQData.drawings.length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
                    <Camera className="w-4 h-4 text-slate-400" /> Attachments ({viewRFQData.drawings.length})
                  </h4>
                  <div className="space-y-3">
                    {viewRFQData.drawings.map((drawing, i) => {
                      const isImage = drawing.is_image || drawing.file_type?.startsWith('image/');
                      const isPdf = drawing.is_pdf || drawing.file_type === 'application/pdf';
                      const fileUrl = drawing.file_url || drawing.view_url || drawing.s3_url;
                      
                      return (
                        <div key={i} className="bg-slate-50 rounded-lg border overflow-hidden">
                          {/* Preview for images */}
                          {isImage && fileUrl && (
                            <div className="bg-slate-100 p-2 flex justify-center border-b">
                              <img 
                                src={fileUrl} 
                                alt={drawing.filename || `Drawing ${i + 1}`}
                                className="max-h-40 max-w-full object-contain rounded"
                                onError={(e) => { e.target.style.display = 'none'; }}
                              />
                            </div>
                          )}
                          
                          {/* Preview for PDFs using iframe */}
                          {isPdf && fileUrl && (
                            <div className="bg-slate-100 p-2 border-b">
                              <iframe 
                                src={fileUrl} 
                                className="w-full h-48 border rounded"
                                title={drawing.filename || `Drawing ${i + 1}`}
                              />
                            </div>
                          )}
                          
                          {/* File info and actions */}
                          <div className="flex items-center gap-3 p-3">
                            <div className="w-10 h-10 bg-orange-100 rounded flex items-center justify-center flex-shrink-0">
                              <FileText className="w-5 h-5 text-orange-600" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium truncate">{drawing.filename || drawing.original_filename || `Drawing ${i + 1}`}</p>
                              <p className="text-xs text-slate-500">
                                {drawing.file_type || 'File'}
                                {drawing.file_size && ` • ${(drawing.file_size / 1024).toFixed(1)} KB`}
                              </p>
                            </div>
                            {fileUrl && (
                              <div className="flex gap-2">
                                <a 
                                  href={fileUrl} 
                                  target="_blank" 
                                  rel="noopener noreferrer"
                                  className="px-3 py-1.5 bg-blue-50 text-blue-600 hover:bg-blue-100 rounded text-sm flex items-center gap-1"
                                  data-testid={`view-drawing-${i}`}
                                >
                                  <Eye className="w-3.5 h-3.5" /> View
                                </a>
                                <a 
                                  href={fileUrl} 
                                  download={drawing.filename || `drawing_${i + 1}`}
                                  className="px-3 py-1.5 bg-orange-50 text-orange-600 hover:bg-orange-100 rounded text-sm flex items-center gap-1"
                                  data-testid={`download-drawing-${i}`}
                                >
                                  <FileCheck className="w-3.5 h-3.5" /> Download
                                </a>
                              </div>
                            )}
                            {!fileUrl && (
                              <span className="text-xs text-red-500">File not available</span>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
              
              {/* Matched Vendors */}
              {viewRFQData.matched_vendors_details && viewRFQData.matched_vendors_details.length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
                    <Building2 className="w-4 h-4 text-slate-400" /> Matched Vendors ({viewRFQData.matched_vendors_details.length})
                  </h4>
                  <div className="space-y-2">
                    {viewRFQData.matched_vendors_details.slice(0, 5).map((mv, i) => (
                      <div key={i} className="flex items-center justify-between p-2 bg-slate-50 rounded">
                        <div>
                          <p className="text-sm font-medium">{mv.vendor_details?.company_name || mv.company_name || 'Unknown'}</p>
                          <p className="text-xs text-slate-500">{mv.vendor_details?.city}, {mv.vendor_details?.state}</p>
                        </div>
                        <span className={`text-xs px-2 py-0.5 rounded ${
                          mv.match_type === 'manual' ? 'bg-orange-100 text-orange-700' : 'bg-green-100 text-green-700'
                        }`}>
                          {mv.suitability_score}% match
                        </span>
                      </div>
                    ))}
                    {viewRFQData.matched_vendors_details.length > 5 && (
                      <p className="text-xs text-slate-500 text-center">+ {viewRFQData.matched_vendors_details.length - 5} more vendors</p>
                    )}
                  </div>
                </div>
              )}
              
              {/* Quotes */}
              {viewRFQData.quotes && viewRFQData.quotes.length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
                    <DollarSign className="w-4 h-4 text-slate-400" /> Quotes Received ({viewRFQData.quotes.length})
                  </h4>
                  <div className="space-y-2">
                    {viewRFQData.quotes.map((quote, i) => (
                      <div key={i} className="flex items-center justify-between p-3 bg-green-50 rounded-lg border border-green-200">
                        <div>
                          <p className="text-sm font-medium">{quote.vendor_info?.company_name || 'Unknown Vendor'}</p>
                          <p className="text-xs text-slate-500">Lead time: {quote.lead_time_days} days</p>
                        </div>
                        <div className="text-right">
                          <p className="font-bold text-green-700">₹{quote.total_price?.toLocaleString('en-IN') || quote.price?.toLocaleString('en-IN')}</p>
                          <StatusBadge status={quote.status} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-12 text-slate-500">
              <AlertCircle className="w-12 h-12 mx-auto mb-2 text-slate-300" />
              <p>Failed to load RFQ details</p>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

// ============== QUOTES TAB ==============
const QuotesTab = ({ quotes, loading, onRefresh, onUpdateQuote, onDeleteQuote }) => {
  const [statusFilter, setStatusFilter] = useState("all");
  const [editQuote, setEditQuote] = useState(null);
  const [editForm, setEditForm] = useState({});
  
  const filteredQuotes = quotes.filter(q => statusFilter === "all" || q.status === statusFilter);
  
  const handleEdit = (quote) => {
    setEditQuote(quote);
    setEditForm({ 
      price: quote.price, 
      lead_time_days: quote.lead_time_days, 
      status: quote.status,
      notes: quote.notes || ""
    });
  };
  
  const handleSave = async () => {
    await onUpdateQuote(editQuote.quote_id, editForm);
    setEditQuote(null);
  };

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex gap-4 items-center justify-between">
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="All statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="pending">Pending</SelectItem>
            <SelectItem value="accepted">Accepted</SelectItem>
            <SelectItem value="rejected">Rejected</SelectItem>
          </SelectContent>
        </Select>
        <Button variant="outline" size="sm" onClick={onRefresh}>
          <RefreshCw className="w-4 h-4" />
        </Button>
      </div>
      
      {/* Quotes Table */}
      <Card className="border-slate-200">
        <CardContent className="p-0">
          <table className="w-full">
            <thead className="bg-slate-50 border-b">
              <tr>
                <th className="text-left p-4 text-xs font-bold uppercase text-slate-500">Quote ID</th>
                <th className="text-left p-4 text-xs font-bold uppercase text-slate-500">RFQ</th>
                <th className="text-left p-4 text-xs font-bold uppercase text-slate-500">Vendor</th>
                <th className="text-left p-4 text-xs font-bold uppercase text-slate-500">Price</th>
                <th className="text-left p-4 text-xs font-bold uppercase text-slate-500">Lead Time</th>
                <th className="text-left p-4 text-xs font-bold uppercase text-slate-500">Status</th>
                <th className="text-right p-4 text-xs font-bold uppercase text-slate-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredQuotes.map((quote) => (
                <tr key={quote.quote_id} className="hover:bg-slate-50" data-testid={`quote-row-${quote.quote_id}`}>
                  <td className="p-4 text-xs font-mono text-slate-600">{quote.quote_id}</td>
                  <td className="p-4 text-sm text-slate-900">{quote.rfq_info?.title || quote.rfq_id}</td>
                  <td className="p-4 text-sm text-slate-900">{quote.vendor_info?.company_name || "-"}</td>
                  <td className="p-4 font-medium text-slate-900">₹{quote.price?.toLocaleString('en-IN', {minimumFractionDigits: 2})}</td>
                  <td className="p-4 text-slate-600">{quote.lead_time_days} days</td>
                  <td className="p-4"><StatusBadge status={quote.status} /></td>
                  <td className="p-4 text-right">
                    <div className="flex justify-end gap-2">
                      <Button variant="ghost" size="sm" onClick={() => handleEdit(quote)}>
                        <Edit className="w-4 h-4" />
                      </Button>
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        className="text-red-600 hover:bg-red-50"
                        onClick={() => onDeleteQuote(quote.quote_id)}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {filteredQuotes.length === 0 && (
            <div className="text-center py-12 text-slate-500">No quotes found</div>
          )}
        </CardContent>
      </Card>
      
      {/* Edit Dialog */}
      <Dialog open={!!editQuote} onOpenChange={() => setEditQuote(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Quote</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Price ($)</Label>
                <Input
                  type="number"
                  step="0.01"
                  value={editForm.price}
                  onChange={(e) => setEditForm(prev => ({ ...prev, price: parseFloat(e.target.value) }))}
                />
              </div>
              <div>
                <Label>Lead Time (days)</Label>
                <Input
                  type="number"
                  value={editForm.lead_time_days}
                  onChange={(e) => setEditForm(prev => ({ ...prev, lead_time_days: parseInt(e.target.value) }))}
                />
              </div>
            </div>
            <div>
              <Label>Status</Label>
              <Select value={editForm.status} onValueChange={(v) => setEditForm(prev => ({ ...prev, status: v }))}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="pending">Pending</SelectItem>
                  <SelectItem value="accepted">Accepted</SelectItem>
                  <SelectItem value="rejected">Rejected</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Notes</Label>
              <Textarea
                value={editForm.notes}
                onChange={(e) => setEditForm(prev => ({ ...prev, notes: e.target.value }))}
              />
            </div>
            <Button onClick={handleSave} className="w-full bg-orange-600 hover:bg-orange-700">
              Save Changes
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

// ============== ORDERS TAB ==============
const OrdersTab = ({ orders, loading, onRefresh, onUpdateOrder, onDeleteOrder }) => {
  const [statusFilter, setStatusFilter] = useState("all");
  const [editOrder, setEditOrder] = useState(null);
  const [editForm, setEditForm] = useState({});
  
  const filteredOrders = orders.filter(o => statusFilter === "all" || o.status === statusFilter);
  
  const handleEdit = (order) => {
    setEditOrder(order);
    setEditForm({ 
      status: order.status, 
      payment_status: order.payment_status,
      total_amount: order.total_amount
    });
  };
  
  const handleSave = async () => {
    await onUpdateOrder(editOrder.order_id, editForm);
    setEditOrder(null);
  };

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex gap-4 items-center justify-between">
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="All statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="pending_payment">Pending Payment</SelectItem>
            <SelectItem value="paid">Paid</SelectItem>
            <SelectItem value="in_production">In Production</SelectItem>
            <SelectItem value="dispatched">Dispatched</SelectItem>
            <SelectItem value="delivered">Delivered</SelectItem>
            <SelectItem value="completed">Completed</SelectItem>
          </SelectContent>
        </Select>
        <Button variant="outline" size="sm" onClick={onRefresh}>
          <RefreshCw className="w-4 h-4" />
        </Button>
      </div>
      
      {/* Orders Table */}
      <Card className="border-slate-200">
        <CardContent className="p-0">
          <table className="w-full">
            <thead className="bg-slate-50 border-b">
              <tr>
                <th className="text-left p-4 text-xs font-bold uppercase text-slate-500">Order ID</th>
                <th className="text-left p-4 text-xs font-bold uppercase text-slate-500">RFQ</th>
                <th className="text-left p-4 text-xs font-bold uppercase text-slate-500">Buyer</th>
                <th className="text-left p-4 text-xs font-bold uppercase text-slate-500">Vendor</th>
                <th className="text-left p-4 text-xs font-bold uppercase text-slate-500">Amount</th>
                <th className="text-left p-4 text-xs font-bold uppercase text-slate-500">Status</th>
                <th className="text-right p-4 text-xs font-bold uppercase text-slate-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredOrders.map((order) => (
                <tr key={order.order_id} className="hover:bg-slate-50" data-testid={`order-row-${order.order_id}`}>
                  <td className="p-4 text-xs font-mono text-slate-600">{order.order_id}</td>
                  <td className="p-4 text-sm text-slate-900">{order.rfq_info?.title || "-"}</td>
                  <td className="p-4 text-sm text-slate-900">{order.buyer_info?.name || "-"}</td>
                  <td className="p-4 text-sm text-slate-900">{order.vendor_info?.company_name || "-"}</td>
                  <td className="p-4 font-medium text-slate-900">₹{order.total_amount?.toLocaleString('en-IN', {minimumFractionDigits: 2})}</td>
                  <td className="p-4"><StatusBadge status={order.status} /></td>
                  <td className="p-4 text-right">
                    <div className="flex justify-end gap-2">
                      <Button variant="ghost" size="sm" onClick={() => handleEdit(order)}>
                        <Edit className="w-4 h-4" />
                      </Button>
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        className="text-red-600 hover:bg-red-50"
                        onClick={() => onDeleteOrder(order.order_id)}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {filteredOrders.length === 0 && (
            <div className="text-center py-12 text-slate-500">No orders found</div>
          )}
        </CardContent>
      </Card>
      
      {/* Edit Dialog */}
      <Dialog open={!!editOrder} onOpenChange={() => setEditOrder(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Order</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            <div>
              <Label>Order Status</Label>
              <Select value={editForm.status} onValueChange={(v) => setEditForm(prev => ({ ...prev, status: v }))}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="pending_payment">Pending Payment</SelectItem>
                  <SelectItem value="paid">Paid</SelectItem>
                  <SelectItem value="in_production">In Production</SelectItem>
                  <SelectItem value="quality_check">Quality Check</SelectItem>
                  <SelectItem value="dispatched">Dispatched</SelectItem>
                  <SelectItem value="delivered">Delivered</SelectItem>
                  <SelectItem value="completed">Completed</SelectItem>
                  <SelectItem value="cancelled">Cancelled</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Payment Status</Label>
              <Select value={editForm.payment_status} onValueChange={(v) => setEditForm(prev => ({ ...prev, payment_status: v }))}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="pending">Pending</SelectItem>
                  <SelectItem value="paid">Paid</SelectItem>
                  <SelectItem value="refunded">Refunded</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Total Amount ($)</Label>
              <Input
                type="number"
                step="0.01"
                value={editForm.total_amount}
                onChange={(e) => setEditForm(prev => ({ ...prev, total_amount: parseFloat(e.target.value) }))}
              />
            </div>
            <Button onClick={handleSave} className="w-full bg-orange-600 hover:bg-orange-700">
              Save Changes
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

// ============== DRAWINGS TAB ==============
const DrawingsTab = ({ drawings, loading, onRefresh, onDeleteDrawing }) => {
  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button variant="outline" size="sm" onClick={onRefresh}>
          <RefreshCw className="w-4 h-4" />
        </Button>
      </div>
      
      <Card className="border-slate-200">
        <CardContent className="p-0">
          <table className="w-full">
            <thead className="bg-slate-50 border-b">
              <tr>
                <th className="text-left p-4 text-xs font-bold uppercase text-slate-500">Drawing ID</th>
                <th className="text-left p-4 text-xs font-bold uppercase text-slate-500">Filename</th>
                <th className="text-left p-4 text-xs font-bold uppercase text-slate-500">RFQ</th>
                <th className="text-left p-4 text-xs font-bold uppercase text-slate-500">Type</th>
                <th className="text-left p-4 text-xs font-bold uppercase text-slate-500">Size</th>
                <th className="text-left p-4 text-xs font-bold uppercase text-slate-500">AI Analysis</th>
                <th className="text-right p-4 text-xs font-bold uppercase text-slate-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {drawings.map((drawing) => (
                <tr key={drawing.drawing_id} className="hover:bg-slate-50" data-testid={`drawing-row-${drawing.drawing_id}`}>
                  <td className="p-4 text-xs font-mono text-slate-600">{drawing.drawing_id}</td>
                  <td className="p-4 text-sm text-slate-900">{drawing.filename}</td>
                  <td className="p-4 text-sm text-slate-600">{drawing.rfq_info?.title || drawing.rfq_id}</td>
                  <td className="p-4 text-sm text-slate-600">{drawing.file_type}</td>
                  <td className="p-4 text-sm text-slate-600">{(drawing.file_size / 1024).toFixed(1)} KB</td>
                  <td className="p-4">
                    {drawing.ai_analysis ? (
                      <CheckCircle2 className="w-4 h-4 text-green-600" />
                    ) : (
                      <XCircle className="w-4 h-4 text-slate-400" />
                    )}
                  </td>
                  <td className="p-4 text-right">
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      className="text-red-600 hover:bg-red-50"
                      onClick={() => onDeleteDrawing(drawing.drawing_id)}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {drawings.length === 0 && (
            <div className="text-center py-12 text-slate-500">No drawings found</div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

// ============== NDAs TAB ==============
const NDAsTab = ({ ndas, users, vendors, loading, onRefresh, onCreateNDA, onUpdateNDA, onSendNDA, onDeleteNDA }) => {
  const [statusFilter, setStatusFilter] = useState("all");
  const [createOpen, setCreateOpen] = useState(false);
  const [editNDA, setEditNDA] = useState(null);
  const [createForm, setCreateForm] = useState({
    title: "",
    buyer_id: "",
    vendor_id: "",
    content: "",
    valid_until: ""
  });
  const [editForm, setEditForm] = useState({});
  
  const filteredNDAs = ndas.filter(n => statusFilter === "all" || n.status === statusFilter);
  const buyers = users.filter(u => u.role === "buyer");
  
  const handleCreate = async () => {
    await onCreateNDA(createForm);
    setCreateOpen(false);
    setCreateForm({ title: "", buyer_id: "", vendor_id: "", content: "", valid_until: "" });
  };
  
  const handleEdit = (nda) => {
    setEditNDA(nda);
    setEditForm({ title: nda.title, status: nda.status, content: nda.content });
  };
  
  const handleSave = async () => {
    await onUpdateNDA(editNDA.nda_id, editForm);
    setEditNDA(null);
  };

  return (
    <div className="space-y-4">
      {/* Actions */}
      <div className="flex gap-4 items-center justify-between">
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="All statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="draft">Draft</SelectItem>
            <SelectItem value="sent">Sent</SelectItem>
            <SelectItem value="signed">Signed</SelectItem>
            <SelectItem value="expired">Expired</SelectItem>
          </SelectContent>
        </Select>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={onRefresh}>
            <RefreshCw className="w-4 h-4" />
          </Button>
          <Dialog open={createOpen} onOpenChange={setCreateOpen}>
            <DialogTrigger asChild>
              <Button className="bg-orange-600 hover:bg-orange-700" size="sm">
                <Plus className="w-4 h-4 mr-1" /> New NDA
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-lg">
              <DialogHeader>
                <DialogTitle>Create New NDA</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 mt-4">
                <div>
                  <Label>Title</Label>
                  <Input
                    value={createForm.title}
                    onChange={(e) => setCreateForm(prev => ({ ...prev, title: e.target.value }))}
                    placeholder="NDA Title"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Buyer</Label>
                    <Select value={createForm.buyer_id} onValueChange={(v) => setCreateForm(prev => ({ ...prev, buyer_id: v }))}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select buyer" />
                      </SelectTrigger>
                      <SelectContent>
                        {buyers.map(b => (
                          <SelectItem key={b.user_id} value={b.user_id}>{b.name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label>Vendor</Label>
                    <Select value={createForm.vendor_id} onValueChange={(v) => setCreateForm(prev => ({ ...prev, vendor_id: v }))}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select vendor" />
                      </SelectTrigger>
                      <SelectContent>
                        {vendors.map(v => (
                          <SelectItem key={v.vendor_id} value={v.vendor_id}>{v.company_name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div>
                  <Label>Content</Label>
                  <Textarea
                    value={createForm.content}
                    onChange={(e) => setCreateForm(prev => ({ ...prev, content: e.target.value }))}
                    placeholder="NDA terms and conditions..."
                    className="min-h-[150px]"
                  />
                </div>
                <div>
                  <Label>Valid Until</Label>
                  <Input
                    type="date"
                    value={createForm.valid_until}
                    onChange={(e) => setCreateForm(prev => ({ ...prev, valid_until: e.target.value }))}
                  />
                </div>
                <Button onClick={handleCreate} className="w-full bg-orange-600 hover:bg-orange-700">
                  Create NDA
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>
      
      {/* NDAs Table */}
      <Card className="border-slate-200">
        <CardContent className="p-0">
          <table className="w-full">
            <thead className="bg-slate-50 border-b">
              <tr>
                <th className="text-left p-4 text-xs font-bold uppercase text-slate-500">NDA</th>
                <th className="text-left p-4 text-xs font-bold uppercase text-slate-500">Buyer</th>
                <th className="text-left p-4 text-xs font-bold uppercase text-slate-500">Vendor</th>
                <th className="text-left p-4 text-xs font-bold uppercase text-slate-500">Status</th>
                <th className="text-left p-4 text-xs font-bold uppercase text-slate-500">Signatures</th>
                <th className="text-left p-4 text-xs font-bold uppercase text-slate-500">Valid Until</th>
                <th className="text-right p-4 text-xs font-bold uppercase text-slate-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredNDAs.map((nda) => (
                <tr key={nda.nda_id} className="hover:bg-slate-50" data-testid={`nda-row-${nda.nda_id}`}>
                  <td className="p-4">
                    <div>
                      <p className="font-medium text-slate-900">{nda.title}</p>
                      <p className="text-xs text-slate-500 font-mono">{nda.nda_id}</p>
                    </div>
                  </td>
                  <td className="p-4 text-sm text-slate-900">{nda.buyer_info?.name || "-"}</td>
                  <td className="p-4 text-sm text-slate-900">{nda.vendor_info?.company_name || "-"}</td>
                  <td className="p-4"><StatusBadge status={nda.status} /></td>
                  <td className="p-4">
                    <div className="flex gap-2">
                      <span className={`text-xs px-2 py-1 rounded ${nda.buyer_signed ? "bg-green-100 text-green-700" : "bg-slate-100 text-slate-500"}`}>
                        Buyer {nda.buyer_signed ? "✓" : "○"}
                      </span>
                      <span className={`text-xs px-2 py-1 rounded ${nda.vendor_signed ? "bg-green-100 text-green-700" : "bg-slate-100 text-slate-500"}`}>
                        Vendor {nda.vendor_signed ? "✓" : "○"}
                      </span>
                    </div>
                  </td>
                  <td className="p-4 text-sm text-slate-500">
                    {nda.valid_until ? new Date(nda.valid_until).toLocaleDateString() : "-"}
                  </td>
                  <td className="p-4 text-right">
                    <div className="flex justify-end gap-2">
                      {nda.status === "draft" && (
                        <Button variant="ghost" size="sm" onClick={() => onSendNDA(nda.nda_id)}>
                          <Send className="w-4 h-4" />
                        </Button>
                      )}
                      <Button variant="ghost" size="sm" onClick={() => handleEdit(nda)}>
                        <Edit className="w-4 h-4" />
                      </Button>
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        className="text-red-600 hover:bg-red-50"
                        onClick={() => onDeleteNDA(nda.nda_id)}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {filteredNDAs.length === 0 && (
            <div className="text-center py-12 text-slate-500">No NDAs found</div>
          )}
        </CardContent>
      </Card>
      
      {/* Edit Dialog */}
      <Dialog open={!!editNDA} onOpenChange={() => setEditNDA(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit NDA</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            <div>
              <Label>Title</Label>
              <Input
                value={editForm.title}
                onChange={(e) => setEditForm(prev => ({ ...prev, title: e.target.value }))}
              />
            </div>
            <div>
              <Label>Status</Label>
              <Select value={editForm.status} onValueChange={(v) => setEditForm(prev => ({ ...prev, status: v }))}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="draft">Draft</SelectItem>
                  <SelectItem value="sent">Sent</SelectItem>
                  <SelectItem value="signed">Signed</SelectItem>
                  <SelectItem value="expired">Expired</SelectItem>
                  <SelectItem value="rejected">Rejected</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Content</Label>
              <Textarea
                value={editForm.content}
                onChange={(e) => setEditForm(prev => ({ ...prev, content: e.target.value }))}
                className="min-h-[150px]"
              />
            </div>
            <Button onClick={handleSave} className="w-full bg-orange-600 hover:bg-orange-700">
              Save Changes
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

// ============== VENDORS TAB ==============
const VendorsTab = ({ vendors, loading, onRefresh, onApprove, onReject, onUpdateVendor, onCreateVendor, canEdit = true, canDelete = true, canCreate = true, canApprove = true, canSearchMachines = true, canViewMachines = true, canCreateMachines = true, canEditMachines = true, canDeleteMachines = true, canManageMachineImages = true }) => {
  const [approvedFilter, setApprovedFilter] = useState("all");
  const [selectedVendor, setSelectedVendor] = useState(null);
  const [vendorProfile, setVendorProfile] = useState(null);
  const [machines, setMachines] = useState([]);
  const [profileLoading, setProfileLoading] = useState(false);
  const [editMachine, setEditMachine] = useState(null);
  const [createMachineOpen, setCreateMachineOpen] = useState(false);
  const [showAddVendorDialog, setShowAddVendorDialog] = useState(false);
  const [addingVendor, setAddingVendor] = useState(false);
  const [addVendorForm, setAddVendorForm] = useState({
    name: "", email: "", password: "", company_name: "", description: "",
    address: "", city: "", country: "", phone: "", website: ""
  });
  const [machineCategories, setMachineCategories] = useState({});
  const [machineForm, setMachineForm] = useState({
    name: "", machine_category: "", machine_type: "", brand: "", model: "", 
    tolerance: 0.01, max_x: 0, max_y: 0, max_z: 0,
    max_diameter: 0, max_length: 0, max_swing: 0,
    bore_diameter: 0, outer_diameter: 0, max_thickness: 0, tonnage: 0,
    max_taper_angle: 0, materials: ""
  });
  const [profileForm, setProfileForm] = useState({});
  
  // Machine images state
  const [machineImages, setMachineImages] = useState([]);
  const [uploadingImage, setUploadingImage] = useState(false);
  
  // Machine search state
  const [showMachineSearch, setShowMachineSearch] = useState(false);
  const [machineSearchLoading, setMachineSearchLoading] = useState(false);
  const [machineSearchResults, setMachineSearchResults] = useState(null);
  const [machineSearchForm, setMachineSearchForm] = useState({
    machine_category: "",
    machine_type: "",
    min_x: "",
    min_y: "",
    min_z: "",
    min_diameter: "",
    min_length: "",
    min_weight: "",
    min_tonnage: "",
    material: "",
    city: "",
    state: "",
    approved_only: true
  });
  
  // Load machine categories on mount
  useEffect(() => {
    const loadCategories = async () => {
      try {
        const res = await api.get("/machine-categories");
        setMachineCategories(res.data);
      } catch (error) {
        console.error("Failed to load machine categories");
      }
    };
    loadCategories();
  }, []);
  
  // Search vendors by machine capabilities
  const searchVendorsByMachines = async () => {
    setMachineSearchLoading(true);
    try {
      const params = new URLSearchParams();
      if (machineSearchForm.machine_category) params.append("machine_category", machineSearchForm.machine_category);
      if (machineSearchForm.machine_type) params.append("machine_type", machineSearchForm.machine_type);
      if (machineSearchForm.min_x) params.append("min_x", machineSearchForm.min_x);
      if (machineSearchForm.min_y) params.append("min_y", machineSearchForm.min_y);
      if (machineSearchForm.min_z) params.append("min_z", machineSearchForm.min_z);
      if (machineSearchForm.min_diameter) params.append("min_diameter", machineSearchForm.min_diameter);
      if (machineSearchForm.min_length) params.append("min_length", machineSearchForm.min_length);
      if (machineSearchForm.min_weight) params.append("min_weight", machineSearchForm.min_weight);
      if (machineSearchForm.min_tonnage) params.append("min_tonnage", machineSearchForm.min_tonnage);
      if (machineSearchForm.material) params.append("material", machineSearchForm.material);
      if (machineSearchForm.city) params.append("city", machineSearchForm.city);
      if (machineSearchForm.state) params.append("state", machineSearchForm.state);
      params.append("approved_only", machineSearchForm.approved_only);
      
      const res = await api.get(`/admin/vendors/search-by-machines?${params.toString()}`);
      setMachineSearchResults(res.data);
      toast.success(`Found ${res.data.total} vendors with ${res.data.machines_found} matching machines`);
    } catch (error) {
      toast.error("Failed to search vendors");
      console.error(error);
    } finally {
      setMachineSearchLoading(false);
    }
  };
  
  const clearMachineSearch = () => {
    setMachineSearchForm({
      machine_category: "",
      machine_type: "",
      min_x: "",
      min_y: "",
      min_z: "",
      min_diameter: "",
      min_length: "",
      min_weight: "",
      min_tonnage: "",
      material: "",
      city: "",
      state: "",
      approved_only: true
    });
    setMachineSearchResults(null);
  };
  
  // Get search dimension fields based on selected search category
  const getSearchDimensionFields = () => {
    if (!machineSearchForm.machine_category || !machineCategories[machineSearchForm.machine_category]) {
      return [];
    }
    return machineCategories[machineSearchForm.machine_category].dimension_fields || [];
  };
  
  // Get machine types for selected search category
  const getSearchMachineTypes = () => {
    if (!machineSearchForm.machine_category || !machineCategories[machineSearchForm.machine_category]) {
      return [];
    }
    return machineCategories[machineSearchForm.machine_category].types || [];
  };
  
  // Get dimension fields based on selected category
  const getDimensionFields = () => {
    if (!machineForm.machine_category || !machineCategories[machineForm.machine_category]) {
      return [];
    }
    return machineCategories[machineForm.machine_category].dimension_fields || [];
  };
  
  // Get machine types for selected category
  const getMachineTypes = () => {
    if (!machineForm.machine_category || !machineCategories[machineForm.machine_category]) {
      return [];
    }
    return machineCategories[machineForm.machine_category].types || [];
  };
  
  const filteredVendors = vendors.filter(v => {
    if (approvedFilter === "all") return true;
    return approvedFilter === "approved" ? v.is_approved : !v.is_approved;
  });
  
  const loadVendorProfile = async (vendorId) => {
    setProfileLoading(true);
    try {
      const res = await api.get(`/admin/vendors/${vendorId}/full`);
      setVendorProfile(res.data.vendor);
      setMachines(res.data.machines);
      setProfileForm({
        company_name: res.data.vendor.company_name || "",
        description: res.data.vendor.description || "",
        phone: res.data.vendor.phone || "",
        website: res.data.vendor.website || "",
        address: res.data.vendor.address || "",
        city: res.data.vendor.city || "",
        state: res.data.vendor.state || "",
        pincode: res.data.vendor.pincode || "",
        country: res.data.vendor.country || "India",
        gstin: res.data.vendor.gstin || "",
        certifications: res.data.vendor.certifications?.join(", ") || "",
        industries: res.data.vendor.industries?.join(", ") || "",
        rating: res.data.vendor.rating || 0,
        is_approved: res.data.vendor.is_approved || false,
        email: res.data.user?.email || "",
        phone_login: res.data.vendor.phone_login || ""
      });
      setSelectedVendor(vendorId);
    } catch (error) {
      toast.error("Failed to load vendor profile");
    } finally {
      setProfileLoading(false);
    }
  };
  
  const saveProfile = async () => {
    try {
      const data = {
        ...profileForm,
        certifications: profileForm.certifications?.split(",").map(s => s.trim()).filter(Boolean) || [],
        industries: profileForm.industries?.split(",").map(s => s.trim()).filter(Boolean) || []
      };
      await api.put(`/admin/vendors/${selectedVendor}/profile`, data);
      toast.success("Profile updated");
      onRefresh();
    } catch (error) {
      toast.error("Failed to update profile");
    }
  };
  
  const saveMachine = async () => {
    try {
      const data = {
        ...machineForm,
        materials: typeof machineForm.materials === 'string' 
          ? machineForm.materials.split(",").map(s => s.trim()).filter(Boolean)
          : machineForm.materials
      };
      
      if (editMachine) {
        await api.put(`/admin/machines/${editMachine.machine_id}`, data);
        toast.success("Machine updated");
      } else {
        await api.post("/admin/machines", { ...data, vendor_id: selectedVendor });
        toast.success("Machine created");
      }
      setEditMachine(null);
      setCreateMachineOpen(false);
      setMachineForm({ name: "", machine_type: "", brand: "", model: "", tolerance: 0.01, max_x: 0, max_y: 0, max_z: 0, max_diameter: 0, materials: [] });
      loadVendorProfile(selectedVendor);
    } catch (error) {
      toast.error("Failed to save machine");
    }
  };
  
  const deleteMachine = async (machineId) => {
    if (!confirm("Are you sure you want to delete this machine?")) return;
    try {
      await api.delete(`/admin/machines/${machineId}`);
      toast.success("Machine deleted");
      loadVendorProfile(selectedVendor);
    } catch (error) {
      toast.error("Failed to delete machine");
    }
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
  
  const openEditMachine = (machine) => {
    setEditMachine(machine);
    // Detect category from machine type
    const detectedCategory = detectCategoryFromType(machine.machine_type) || machine.machine_category || "";
    
    // Handle both old and new field names
    setMachineForm({
      name: machine.name || machine.model || "",
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
      materials: (machine.materials || machine.materials_supported)?.join(", ") || ""
    });
    // Load machine images
    setMachineImages(machine.images || []);
  };
  
  // Upload machine image
  const uploadMachineImage = async (machineId, file) => {
    if (!canManageMachineImages) {
      toast.error("You don't have permission to manage machine images");
      return;
    }
    
    setUploadingImage(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const res = await api.post(`/admin/machines/${machineId}/images`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      setMachineImages(res.data.images || []);
      // Update the machine in the local machines array
      setMachines(prev => prev.map(m => 
        m.machine_id === machineId ? {...m, images: res.data.images} : m
      ));
      toast.success("Image uploaded successfully");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to upload image");
    } finally {
      setUploadingImage(false);
    }
  };
  
  // Delete machine image
  const deleteMachineImage = async (machineId, imageUrl) => {
    if (!canManageMachineImages) {
      toast.error("You don't have permission to manage machine images");
      return;
    }
    
    try {
      const res = await api.delete(`/admin/machines/${machineId}/images`, {
        params: { image_url: imageUrl }
      });
      
      setMachineImages(res.data.images || []);
      // Update the machine in the local machines array
      setMachines(prev => prev.map(m => 
        m.machine_id === machineId ? {...m, images: res.data.images} : m
      ));
      toast.success("Image deleted");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to delete image");
    }
  };
  
  const resetMachineForm = () => {
    setMachineForm({
      name: "", machine_category: "", machine_type: "", brand: "", model: "", 
      tolerance: 0.01, max_x: 0, max_y: 0, max_z: 0,
      max_diameter: 0, max_length: 0, max_swing: 0,
      bore_diameter: 0, outer_diameter: 0, max_thickness: 0, tonnage: 0,
      max_taper_angle: 0, materials: ""
    });
    setMachineImages([]);
  };
  
  // Helper to get machine display name
  const getMachineName = (machine) => machine.name || `${machine.brand} ${machine.model}`.trim() || "Unnamed Machine";
  const getMachineTolerance = (machine) => machine.tolerance || machine.tolerance_capability || 0;
  const getMachineMaterials = (machine) => machine.materials || machine.materials_supported || [];
  
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

  // Vendor Profile Detail View
  if (selectedVendor && vendorProfile) {
    return (
      <div className="space-y-6">
        {/* Back Button */}
        <Button variant="outline" size="sm" onClick={() => setSelectedVendor(null)}>
          <ChevronRight className="w-4 h-4 rotate-180 mr-1" /> Back to Vendors
        </Button>
        
        {/* Profile Card */}
        <Card className="border-slate-200">
          <CardHeader>
            <CardTitle className="font-heading flex items-center gap-2">
              <Building2 className="w-5 h-5 text-orange-600" />
              {vendorProfile.company_name} - Profile Management
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label>Company Name</Label>
                <Input value={profileForm.company_name} onChange={(e) => setProfileForm(p => ({...p, company_name: e.target.value}))} />
              </div>
              <div>
                <Label>Email (User Account)</Label>
                <Input value={profileForm.email} disabled className="bg-slate-50" />
              </div>
              <div>
                <Label>Phone</Label>
                <Input value={profileForm.phone} onChange={(e) => setProfileForm(p => ({...p, phone: e.target.value}))} />
              </div>
              <div>
                <Label>WhatsApp Login Number</Label>
                <Input value={profileForm.phone_login} disabled className="bg-slate-50 font-mono" placeholder="WhatsApp registered" />
              </div>
              <div>
                <Label>Website</Label>
                <Input value={profileForm.website} onChange={(e) => setProfileForm(p => ({...p, website: e.target.value}))} />
              </div>
              <div>
                <Label>GSTIN</Label>
                <Input value={profileForm.gstin} disabled className="bg-slate-50 font-mono text-xs" placeholder="GST Number" />
              </div>
              <div>
                <Label>Rating (0-5)</Label>
                <Input type="number" step="0.1" min="0" max="5" value={profileForm.rating} onChange={(e) => setProfileForm(p => ({...p, rating: parseFloat(e.target.value)}))} />
              </div>
              <div>
                <Label>City</Label>
                <Input value={profileForm.city} onChange={(e) => setProfileForm(p => ({...p, city: e.target.value}))} />
              </div>
              <div>
                <Label>State</Label>
                <Input value={profileForm.state} onChange={(e) => setProfileForm(p => ({...p, state: e.target.value}))} />
              </div>
              <div>
                <Label>Pincode</Label>
                <Input value={profileForm.pincode} onChange={(e) => setProfileForm(p => ({...p, pincode: e.target.value}))} maxLength={6} />
              </div>
              <div>
                <Label>Country</Label>
                <Input value={profileForm.country} onChange={(e) => setProfileForm(p => ({...p, country: e.target.value}))} />
              </div>
              <div className="md:col-span-2">
                <Label>Address</Label>
                <Input value={profileForm.address} onChange={(e) => setProfileForm(p => ({...p, address: e.target.value}))} />
              </div>
              <div className="md:col-span-2">
                <Label>Description</Label>
                <Textarea value={profileForm.description} onChange={(e) => setProfileForm(p => ({...p, description: e.target.value}))} />
              </div>
              <div>
                <Label>Certifications (comma-separated)</Label>
                <Input value={profileForm.certifications} onChange={(e) => setProfileForm(p => ({...p, certifications: e.target.value}))} placeholder="ISO 9001, AS9100, IATF 16949" />
              </div>
              <div>
                <Label>Industries (comma-separated)</Label>
                <Input value={profileForm.industries} onChange={(e) => setProfileForm(p => ({...p, industries: e.target.value}))} placeholder="Automotive, Aerospace, Medical" />
              </div>
              <div className="flex items-center gap-2">
                <input type="checkbox" id="vendor-approved" checked={profileForm.is_approved} onChange={(e) => setProfileForm(p => ({...p, is_approved: e.target.checked}))} className="rounded" />
                <Label htmlFor="vendor-approved">Approved</Label>
              </div>
            </div>
            <Button onClick={saveProfile} className="mt-4 bg-orange-600 hover:bg-orange-700">
              Save Profile Changes
            </Button>
          </CardContent>
        </Card>
        
        {/* Machines Card */}
        <Card className="border-slate-200">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="font-heading flex items-center gap-2">
              <Wrench className="w-5 h-5 text-orange-600" />
              Machines ({machines.length})
            </CardTitle>
            {canCreateMachines && (
              <Button size="sm" className="bg-orange-600 hover:bg-orange-700" onClick={() => { setCreateMachineOpen(true); setEditMachine(null); resetMachineForm(); }} data-testid="add-machine-btn">
                <Plus className="w-4 h-4 mr-1" /> Add Machine
              </Button>
            )}
          </CardHeader>
          <CardContent>
            {machines.length > 0 ? (
              <div className="space-y-3">
                {machines.map((machine) => (
                  <div key={machine.machine_id} className="p-4 bg-slate-50 rounded-lg border flex items-center justify-between" data-testid={`machine-${machine.machine_id}`}>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <p className="font-medium text-slate-900">{getMachineName(machine)}</p>
                        {(machine.machine_category || detectCategoryFromType(machine.machine_type)) && (
                          <span className="text-xs bg-orange-100 text-orange-700 px-2 py-0.5 rounded">
                            {machine.machine_category || detectCategoryFromType(machine.machine_type)}
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-slate-500">{machine.machine_type} • {machine.brand} {machine.model}</p>
                      <div className="flex flex-wrap gap-4 mt-2 text-xs text-slate-500">
                        <span>Tolerance: ±{getMachineTolerance(machine)}mm</span>
                        {getMachineDimensions(machine) && <span>{getMachineDimensions(machine)}</span>}
                        {getMachineMaterials(machine).length > 0 && <span>Materials: {getMachineMaterials(machine).slice(0, 3).join(", ")}</span>}
                      </div>
                    </div>
                    {(canEditMachines || canDeleteMachines) && (
                      <div className="flex gap-2">
                        {canEditMachines && (
                          <Button variant="ghost" size="sm" onClick={() => openEditMachine(machine)} data-testid={`edit-machine-${machine.machine_id}`}>
                            <Edit className="w-4 h-4" />
                          </Button>
                        )}
                        {canDeleteMachines && (
                          <Button variant="ghost" size="sm" className="text-red-600 hover:bg-red-50" onClick={() => deleteMachine(machine.machine_id)} data-testid={`delete-machine-${machine.machine_id}`}>
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-center py-8 text-slate-500">No machines registered for this vendor</p>
            )}
          </CardContent>
        </Card>
        
        {/* Machine Edit/Create Dialog */}
        <Dialog open={!!editMachine || createMachineOpen} onOpenChange={() => { setEditMachine(null); setCreateMachineOpen(false); }}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>{editMachine ? "Edit Machine" : "Add New Machine"}</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 mt-4 max-h-[60vh] overflow-y-auto pr-2">
              <div className="grid grid-cols-2 gap-4">
                {/* Machine Name */}
                <div className="col-span-2">
                  <Label>Machine Name</Label>
                  <Input value={machineForm.name} onChange={(e) => setMachineForm(m => ({...m, name: e.target.value}))} placeholder="e.g. Haas VF-2SS" />
                </div>
                
                {/* Machine Category - Primary Selection */}
                <div className="col-span-2">
                  <Label className="text-orange-600 font-medium">Machine Category *</Label>
                  <Select 
                    value={machineForm.machine_category} 
                    onValueChange={(v) => setMachineForm(m => ({...m, machine_category: v, machine_type: ""}))}
                  >
                    <SelectTrigger className="border-orange-200 focus:ring-orange-500"><SelectValue placeholder="Select category first" /></SelectTrigger>
                    <SelectContent>
                      {Object.keys(machineCategories).map((category) => (
                        <SelectItem key={category} value={category}>{category}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                
                {/* Machine Type - Based on Category */}
                <div>
                  <Label>Machine Type</Label>
                  <Select 
                    value={machineForm.machine_type} 
                    onValueChange={(v) => setMachineForm(m => ({...m, machine_type: v}))}
                    disabled={!machineForm.machine_category}
                  >
                    <SelectTrigger><SelectValue placeholder={machineForm.machine_category ? "Select type" : "Select category first"} /></SelectTrigger>
                    <SelectContent>
                      {getMachineTypes().map((type) => (
                        <SelectItem key={type} value={type}>{type}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                
                {/* Brand */}
                <div>
                  <Label>Brand</Label>
                  <Input value={machineForm.brand} onChange={(e) => setMachineForm(m => ({...m, brand: e.target.value}))} placeholder="e.g. Haas, DMG Mori" />
                </div>
                
                {/* Model */}
                <div>
                  <Label>Model</Label>
                  <Input value={machineForm.model} onChange={(e) => setMachineForm(m => ({...m, model: e.target.value}))} placeholder="e.g. VF-2SS" />
                </div>
                
                {/* Tolerance */}
                <div>
                  <Label>Tolerance (mm)</Label>
                  <Input type="number" step="0.001" value={machineForm.tolerance} onChange={(e) => setMachineForm(m => ({...m, tolerance: parseFloat(e.target.value) || 0}))} />
                </div>
                
                {/* Conditional Dimension Fields Based on Category */}
                {machineForm.machine_category && (
                  <>
                    <div className="col-span-2 border-t pt-4 mt-2">
                      <p className="text-sm font-medium text-slate-700 mb-3">
                        {machineForm.machine_category} Dimensions
                      </p>
                    </div>
                    {getDimensionFields().map((field) => (
                      <div key={field.key}>
                        <Label>{field.label}</Label>
                        <Input 
                          type="number" 
                          step={field.key.includes("angle") ? "0.1" : "1"}
                          value={machineForm[field.key] || 0} 
                          onChange={(e) => setMachineForm(m => ({...m, [field.key]: parseFloat(e.target.value) || 0}))} 
                        />
                      </div>
                    ))}
                  </>
                )}
                
                {/* Materials */}
                <div className="col-span-2 border-t pt-4 mt-2">
                  <Label>Materials (comma-separated)</Label>
                  <Input value={machineForm.materials} onChange={(e) => setMachineForm(m => ({...m, materials: e.target.value}))} placeholder="Aluminum, Steel, Stainless Steel, Titanium" />
                </div>
                
                {/* Machine Images Section - Only show when editing an existing machine */}
                {editMachine && canManageMachineImages && (
                  <div className="col-span-2 border-t pt-4 mt-2">
                    <Label className="flex items-center gap-2 mb-3">
                      <Camera className="w-4 h-4 text-orange-600" />
                      Machine Images ({machineImages.length})
                    </Label>
                    
                    {/* Image Grid */}
                    {machineImages.length > 0 && (
                      <div className="grid grid-cols-3 gap-2 mb-3">
                        {machineImages.map((imgUrl, idx) => (
                          <div key={idx} className="relative group rounded-lg overflow-hidden border bg-slate-50">
                            <img 
                              src={imgUrl} 
                              alt={`Machine ${idx + 1}`} 
                              className="w-full h-20 object-cover"
                              onError={(e) => { e.target.src = '/placeholder-machine.png'; e.target.onerror = null; }}
                            />
                            <button
                              onClick={() => deleteMachineImage(editMachine.machine_id, imgUrl)}
                              className="absolute top-1 right-1 p-1 bg-red-500 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
                              title="Delete image"
                            >
                              <XCircle className="w-4 h-4" />
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                    
                    {/* Upload Button */}
                    <div className="flex items-center gap-2">
                      <input
                        type="file"
                        id="machine-image-upload"
                        accept="image/jpeg,image/png,image/webp"
                        className="hidden"
                        onChange={(e) => {
                          const file = e.target.files?.[0];
                          if (file) {
                            uploadMachineImage(editMachine.machine_id, file);
                            e.target.value = '';
                          }
                        }}
                      />
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        disabled={uploadingImage}
                        onClick={() => document.getElementById('machine-image-upload').click()}
                        className="w-full"
                      >
                        {uploadingImage ? (
                          <>
                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                            Uploading...
                          </>
                        ) : (
                          <>
                            <Upload className="w-4 h-4 mr-2" />
                            Upload Image
                          </>
                        )}
                      </Button>
                    </div>
                    <p className="text-xs text-slate-500 mt-1">Max 5MB. JPEG, PNG, or WebP only.</p>
                  </div>
                )}
              </div>
              <Button onClick={saveMachine} className="w-full bg-orange-600 hover:bg-orange-700" disabled={!machineForm.machine_category}>
                {editMachine ? "Update Machine" : "Create Machine"}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>
    );
  }

  // Vendors List View
  const handleAddVendor = async () => {
    if (!addVendorForm.email || !addVendorForm.password || !addVendorForm.name || !addVendorForm.company_name) {
      toast.error("Please fill all required fields");
      return;
    }
    setAddingVendor(true);
    try {
      await onCreateVendor(addVendorForm);
      setShowAddVendorDialog(false);
      setAddVendorForm({
        name: "", email: "", password: "", company_name: "", description: "",
        address: "", city: "", country: "", phone: "", website: ""
      });
    } finally {
      setAddingVendor(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Filters and Search Toggle */}
      <div className="flex gap-4 items-center justify-between flex-wrap">
        <div className="flex gap-2 items-center">
          <Select value={approvedFilter} onValueChange={setApprovedFilter}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder="All vendors" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Vendors</SelectItem>
              <SelectItem value="approved">Approved</SelectItem>
              <SelectItem value="pending">Pending</SelectItem>
            </SelectContent>
          </Select>
          {canSearchMachines && (
            <Button 
              variant={showMachineSearch ? "default" : "outline"} 
              size="sm" 
              onClick={() => setShowMachineSearch(!showMachineSearch)}
              className={showMachineSearch ? "bg-orange-600 hover:bg-orange-700" : ""}
              data-testid="search-by-machines-btn"
            >
              <Search className="w-4 h-4 mr-2" />
              Search by Machines
            </Button>
          )}
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={onRefresh}>
            <RefreshCw className="w-4 h-4" />
          </Button>
          {canCreate && (
            <Button onClick={() => setShowAddVendorDialog(true)} className="bg-orange-600 hover:bg-orange-700">
              <Plus className="w-4 h-4 mr-2" /> Add Vendor
            </Button>
          )}
        </div>
      </div>
      
      {/* Machine Search Panel - Only show if user has permission */}
      {canSearchMachines && showMachineSearch && (
        <Card className="border-orange-200 bg-orange-50/30">
          <CardHeader className="py-3">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Wrench className="w-4 h-4 text-orange-600" />
              Search Vendors by Machine Capabilities
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {/* Machine Category */}
              <div>
                <Label className="text-xs">Machine Category</Label>
                <Select 
                  value={machineSearchForm.machine_category || "__all__"} 
                  onValueChange={(v) => setMachineSearchForm(f => ({...f, machine_category: v === "__all__" ? "" : v, machine_type: ""}))}
                >
                  <SelectTrigger className="h-9">
                    <SelectValue placeholder="Any category" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__all__">Any Category</SelectItem>
                    {Object.keys(machineCategories).sort().map(cat => (
                      <SelectItem key={cat} value={cat}>{cat}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              {/* Machine Type */}
              <div>
                <Label className="text-xs">Machine Type</Label>
                <Select 
                  value={machineSearchForm.machine_type || "__all__"} 
                  onValueChange={(v) => setMachineSearchForm(f => ({...f, machine_type: v === "__all__" ? "" : v}))}
                  disabled={!machineSearchForm.machine_category}
                >
                  <SelectTrigger className="h-9">
                    <SelectValue placeholder="Any type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__all__">Any Type</SelectItem>
                    {getSearchMachineTypes().map(type => (
                      <SelectItem key={type} value={type}>{type}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              {/* Material */}
              <div>
                <Label className="text-xs">Material</Label>
                <Input 
                  className="h-9" 
                  placeholder="e.g. Steel, Aluminum" 
                  value={machineSearchForm.material}
                  onChange={(e) => setMachineSearchForm(f => ({...f, material: e.target.value}))}
                />
              </div>
              
              {/* Location - City */}
              <div>
                <Label className="text-xs">City</Label>
                <Input 
                  className="h-9" 
                  placeholder="e.g. Mumbai, Chennai" 
                  value={machineSearchForm.city}
                  onChange={(e) => setMachineSearchForm(f => ({...f, city: e.target.value}))}
                />
              </div>
            </div>
            
            {/* Dynamic Dimension Fields based on category */}
            {machineSearchForm.machine_category && getSearchDimensionFields().length > 0 && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-2 border-t">
                <div className="col-span-full">
                  <Label className="text-xs text-orange-700">Minimum Dimensions for {machineSearchForm.machine_category}</Label>
                </div>
                {getSearchDimensionFields().map(field => (
                  <div key={field.key}>
                    <Label className="text-xs">{field.label.replace('Max ', 'Min ')}</Label>
                    <Input 
                      type="number" 
                      className="h-9" 
                      placeholder="0"
                      value={machineSearchForm[`min_${field.key.replace('max_', '')}`] || ""}
                      onChange={(e) => setMachineSearchForm(f => ({
                        ...f, 
                        [`min_${field.key.replace('max_', '')}`]: e.target.value
                      }))}
                    />
                  </div>
                ))}
              </div>
            )}
            
            {/* Common dimension fields when no category selected */}
            {!machineSearchForm.machine_category && (
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3 pt-2 border-t">
                <div className="col-span-full">
                  <Label className="text-xs text-slate-500">Minimum Dimensions (common)</Label>
                </div>
                <div>
                  <Label className="text-xs">Min X (mm)</Label>
                  <Input 
                    type="number" 
                    className="h-9" 
                    placeholder="0"
                    value={machineSearchForm.min_x}
                    onChange={(e) => setMachineSearchForm(f => ({...f, min_x: e.target.value}))}
                  />
                </div>
                <div>
                  <Label className="text-xs">Min Y (mm)</Label>
                  <Input 
                    type="number" 
                    className="h-9" 
                    placeholder="0"
                    value={machineSearchForm.min_y}
                    onChange={(e) => setMachineSearchForm(f => ({...f, min_y: e.target.value}))}
                  />
                </div>
                <div>
                  <Label className="text-xs">Min Z (mm)</Label>
                  <Input 
                    type="number" 
                    className="h-9" 
                    placeholder="0"
                    value={machineSearchForm.min_z}
                    onChange={(e) => setMachineSearchForm(f => ({...f, min_z: e.target.value}))}
                  />
                </div>
                <div>
                  <Label className="text-xs">Min Diameter (mm)</Label>
                  <Input 
                    type="number" 
                    className="h-9" 
                    placeholder="0"
                    value={machineSearchForm.min_diameter}
                    onChange={(e) => setMachineSearchForm(f => ({...f, min_diameter: e.target.value}))}
                  />
                </div>
                <div>
                  <Label className="text-xs">Min Length (mm)</Label>
                  <Input 
                    type="number" 
                    className="h-9" 
                    placeholder="0"
                    value={machineSearchForm.min_length}
                    onChange={(e) => setMachineSearchForm(f => ({...f, min_length: e.target.value}))}
                  />
                </div>
              </div>
            )}
            
            {/* Search Actions */}
            <div className="flex gap-2 justify-end pt-2">
              <div className="flex items-center gap-2 mr-auto">
                <input 
                  type="checkbox" 
                  id="approved-only" 
                  checked={machineSearchForm.approved_only}
                  onChange={(e) => setMachineSearchForm(f => ({...f, approved_only: e.target.checked}))}
                  className="rounded"
                />
                <Label htmlFor="approved-only" className="text-xs">Approved vendors only</Label>
              </div>
              <Button variant="outline" size="sm" onClick={clearMachineSearch}>
                Clear
              </Button>
              <Button 
                size="sm" 
                onClick={searchVendorsByMachines} 
                disabled={machineSearchLoading}
                className="bg-orange-600 hover:bg-orange-700"
              >
                {machineSearchLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Search className="w-4 h-4 mr-2" />}
                Search Vendors
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
      
      {/* Machine Search Results */}
      {machineSearchResults && (
        <Card className="border-green-200 bg-green-50/30">
          <CardHeader className="py-3">
            <div className="flex justify-between items-center">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-green-600" />
                Search Results: {machineSearchResults.total} vendors with {machineSearchResults.machines_found} matching machines
              </CardTitle>
              <Button variant="ghost" size="sm" onClick={() => setMachineSearchResults(null)}>
                <XCircle className="w-4 h-4" />
              </Button>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <table className="w-full">
              <thead className="bg-green-100/50 border-b">
                <tr>
                  <th className="text-left p-3 text-xs font-bold uppercase text-slate-600">Company</th>
                  <th className="text-left p-3 text-xs font-bold uppercase text-slate-600">Location</th>
                  <th className="text-left p-3 text-xs font-bold uppercase text-slate-600">Matching Machines</th>
                  <th className="text-left p-3 text-xs font-bold uppercase text-slate-600">Total Machines</th>
                  <th className="text-left p-3 text-xs font-bold uppercase text-slate-600">Rating</th>
                  {canEdit && <th className="text-right p-3 text-xs font-bold uppercase text-slate-600">Actions</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-green-100">
                {machineSearchResults.vendors.map((vendor) => (
                  <tr key={vendor.vendor_id} className="hover:bg-green-50">
                    <td className="p-3">
                      <div>
                        <p className="font-medium text-slate-900">{vendor.company_name}</p>
                        <p className="text-xs text-slate-500">{vendor.user_info?.email}</p>
                      </div>
                    </td>
                    <td className="p-3">
                      <p className="text-sm">{vendor.city || '-'}{vendor.state ? `, ${vendor.state}` : ''}</p>
                    </td>
                    <td className="p-3">
                      <div>
                        <span className="text-lg font-bold text-green-600">{vendor.matching_machine_count}</span>
                        <div className="text-xs text-slate-500 max-w-xs">
                          {vendor.matching_machines?.slice(0, 3).map((m, i) => (
                            <span key={i} className="inline-block bg-slate-100 px-1 rounded mr-1 mb-1">
                              {m.machine_type || m.name}
                            </span>
                          ))}
                          {vendor.matching_machines?.length > 3 && (
                            <span className="text-slate-400">+{vendor.matching_machines.length - 3} more</span>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="p-3">
                      <span className="text-sm">{vendor.total_machine_count}</span>
                    </td>
                    <td className="p-3">
                      {vendor.rating > 0 ? (
                        <span className="text-amber-600">⭐ {vendor.rating?.toFixed(1)}</span>
                      ) : '-'}
                    </td>
                    {canEdit && (
                      <td className="p-3 text-right">
                        <Button variant="ghost" size="sm" onClick={() => loadVendorProfile(vendor.vendor_id)}>
                          <Eye className="w-4 h-4" />
                        </Button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
            {machineSearchResults.vendors.length === 0 && (
              <div className="text-center py-8 text-slate-500">
                No vendors found matching your criteria
              </div>
            )}
          </CardContent>
        </Card>
      )}
      
      {/* All Vendors Table (hidden when showing search results) */}
      {!machineSearchResults && (
        <>
          {/* Vendors Table */}
      <Card className="border-slate-200">
        <CardContent className="p-0">
          <table className="w-full">
            <thead className="bg-slate-50 border-b">
              <tr>
                <th className="text-left p-4 text-xs font-bold uppercase text-slate-500">Company</th>
                <th className="text-left p-4 text-xs font-bold uppercase text-slate-500">Contact / Email</th>
                <th className="text-left p-4 text-xs font-bold uppercase text-slate-500">Phone</th>
                <th className="text-left p-4 text-xs font-bold uppercase text-slate-500">Location</th>
                <th className="text-left p-4 text-xs font-bold uppercase text-slate-500">GST</th>
                <th className="text-left p-4 text-xs font-bold uppercase text-slate-500">Machines</th>
                <th className="text-left p-4 text-xs font-bold uppercase text-slate-500">Status</th>
                {(canEdit || canApprove) && (
                  <th className="text-right p-4 text-xs font-bold uppercase text-slate-500">Actions</th>
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredVendors.map((vendor) => (
                <tr key={vendor.vendor_id} className="hover:bg-slate-50" data-testid={`vendor-row-${vendor.vendor_id}`}>
                  <td className="p-4">
                    <div>
                      <p className="font-medium text-slate-900">{vendor.company_name}</p>
                      <p className="text-xs text-slate-500 font-mono">{vendor.vendor_id}</p>
                      {vendor.website && (
                        <a href={vendor.website} target="_blank" rel="noopener noreferrer" className="text-xs text-blue-600 hover:underline">
                          {vendor.website.replace(/https?:\/\//, '').slice(0, 25)}
                        </a>
                      )}
                    </div>
                  </td>
                  <td className="p-4">
                    <div>
                      <p className="text-sm font-medium text-slate-900">{vendor.user_info?.name || '-'}</p>
                      <p className="text-xs text-blue-600">{vendor.user_info?.email || '-'}</p>
                      {vendor.phone_login && (
                        <p className="text-xs text-slate-500">📱 {vendor.phone_login}</p>
                      )}
                    </div>
                  </td>
                  <td className="p-4">
                    <p className="text-sm text-slate-900">{vendor.phone || '-'}</p>
                  </td>
                  <td className="p-4">
                    <div className="text-sm">
                      <p className="text-slate-900">{vendor.city || '-'}{vendor.state ? `, ${vendor.state}` : ''}</p>
                      {vendor.pincode && <p className="text-xs text-slate-500">📮 {vendor.pincode}</p>}
                      <p className="text-xs text-slate-400">{vendor.country || 'India'}</p>
                    </div>
                  </td>
                  <td className="p-4">
                    {vendor.gstin ? (
                      <div>
                        <p className="text-xs font-mono text-slate-700">{vendor.gstin}</p>
                        <p className="text-xs text-green-600">✓ Verified</p>
                      </div>
                    ) : (
                      <span className="text-xs text-slate-400">-</span>
                    )}
                  </td>
                  <td className="p-4">
                    <div className="flex items-center gap-1">
                      <span className="text-sm font-medium text-slate-900">{vendor.machine_count || 0}</span>
                      {vendor.rating > 0 && (
                        <span className="text-xs text-amber-600">⭐ {vendor.rating?.toFixed(1)}</span>
                      )}
                    </div>
                  </td>
                  <td className="p-4">
                    <StatusBadge status={vendor.is_approved ? "approved" : "pending"} />
                  </td>
                  {(canEdit || canApprove) && (
                    <td className="p-4 text-right">
                      <div className="flex justify-end gap-2">
                        {canEdit && (
                          <Button variant="ghost" size="sm" onClick={() => loadVendorProfile(vendor.vendor_id)} title="Manage Profile & Machines">
                            <Eye className="w-4 h-4" />
                          </Button>
                        )}
                        {canApprove && !vendor.is_approved && (
                          <Button variant="ghost" size="sm" className="text-green-600 hover:bg-green-50" onClick={() => onApprove(vendor.vendor_id)}>
                            <CheckCircle2 className="w-4 h-4" />
                          </Button>
                        )}
                        {canApprove && vendor.is_approved && (
                          <Button variant="ghost" size="sm" className="text-amber-600 hover:bg-amber-50" onClick={() => onReject(vendor.vendor_id)}>
                            <XCircle className="w-4 h-4" />
                          </Button>
                        )}
                      </div>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
          {filteredVendors.length === 0 && (
            <div className="text-center py-12 text-slate-500">No vendors found</div>
          )}
        </CardContent>
      </Card>
        </>
      )}

      {/* Add Vendor Dialog */}
      <Dialog open={showAddVendorDialog} onOpenChange={setShowAddVendorDialog}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Add New Vendor</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Contact Name *</Label>
                <Input
                  value={addVendorForm.name}
                  onChange={(e) => setAddVendorForm(prev => ({ ...prev, name: e.target.value }))}
                  placeholder="Full name"
                />
              </div>
              <div>
                <Label>Company Name *</Label>
                <Input
                  value={addVendorForm.company_name}
                  onChange={(e) => setAddVendorForm(prev => ({ ...prev, company_name: e.target.value }))}
                  placeholder="Company name"
                />
              </div>
              <div>
                <Label>Email *</Label>
                <Input
                  type="email"
                  value={addVendorForm.email}
                  onChange={(e) => setAddVendorForm(prev => ({ ...prev, email: e.target.value }))}
                  placeholder="email@company.com"
                />
              </div>
              <div>
                <Label>Password *</Label>
                <Input
                  type="password"
                  value={addVendorForm.password}
                  onChange={(e) => setAddVendorForm(prev => ({ ...prev, password: e.target.value }))}
                  placeholder="Minimum 6 characters"
                />
              </div>
              <div>
                <Label>Phone</Label>
                <Input
                  value={addVendorForm.phone}
                  onChange={(e) => setAddVendorForm(prev => ({ ...prev, phone: e.target.value }))}
                  placeholder="+1 234 567 8900"
                />
              </div>
              <div>
                <Label>Website</Label>
                <Input
                  value={addVendorForm.website}
                  onChange={(e) => setAddVendorForm(prev => ({ ...prev, website: e.target.value }))}
                  placeholder="https://company.com"
                />
              </div>
              <div>
                <Label>City</Label>
                <Input
                  value={addVendorForm.city}
                  onChange={(e) => setAddVendorForm(prev => ({ ...prev, city: e.target.value }))}
                  placeholder="City"
                />
              </div>
              <div>
                <Label>Country</Label>
                <Input
                  value={addVendorForm.country}
                  onChange={(e) => setAddVendorForm(prev => ({ ...prev, country: e.target.value }))}
                  placeholder="Country"
                />
              </div>
              <div className="col-span-2">
                <Label>Address</Label>
                <Input
                  value={addVendorForm.address}
                  onChange={(e) => setAddVendorForm(prev => ({ ...prev, address: e.target.value }))}
                  placeholder="Street address"
                />
              </div>
              <div className="col-span-2">
                <Label>Description</Label>
                <Textarea
                  value={addVendorForm.description}
                  onChange={(e) => setAddVendorForm(prev => ({ ...prev, description: e.target.value }))}
                  placeholder="Brief description of capabilities..."
                  rows={3}
                />
              </div>
            </div>
            <Button onClick={handleAddVendor} disabled={addingVendor} className="w-full bg-orange-600 hover:bg-orange-700">
              {addingVendor ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Plus className="w-4 h-4 mr-2" />}
              Create Vendor
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

// ============== MACHINES TAB ==============
const MachinesTab = ({ machines, loading, onRefresh, vendors, canCreate = true, canEdit = true, canDelete = true, canManageImages = true }) => {
  const [searchTerm, setSearchTerm] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [vendorFilter, setVendorFilter] = useState("all");
  const [machineCategories, setMachineCategories] = useState({});
  const [editMachine, setEditMachine] = useState(null);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [machineForm, setMachineForm] = useState({});
  const [machineImages, setMachineImages] = useState([]);
  const [uploadingImage, setUploadingImage] = useState(false);
  const [saving, setSaving] = useState(false);
  
  // Load categories
  useEffect(() => {
    const loadCategories = async () => {
      try {
        const res = await api.get("/machine-categories");
        setMachineCategories(res.data);
      } catch (error) {
        console.error("Failed to load categories");
      }
    };
    loadCategories();
  }, []);
  
  // Get unique categories from machines
  const uniqueCategories = [...new Set(machines.map(m => m.machine_category || 'Uncategorized').filter(Boolean))];
  
  // Get machine types for selected category
  const getMachineTypes = () => {
    if (!machineForm.machine_category || !machineCategories[machineForm.machine_category]) {
      return [];
    }
    return machineCategories[machineForm.machine_category].types || [];
  };
  
  // Get dimension fields for selected category
  const getDimensionFields = () => {
    if (!machineForm.machine_category || !machineCategories[machineForm.machine_category]) {
      return [];
    }
    return machineCategories[machineForm.machine_category].dimension_fields || [];
  };
  
  // Filter machines
  const filteredMachines = machines.filter(m => {
    const matchesSearch = !searchTerm || 
      m.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      m.machine_type?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      m.brand?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      m.model?.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory = categoryFilter === "all" || m.machine_category === categoryFilter;
    const matchesVendor = vendorFilter === "all" || m.vendor_id === vendorFilter;
    return matchesSearch && matchesCategory && matchesVendor;
  });
  
  // Reset form
  const resetForm = () => {
    setMachineForm({
      vendor_id: "",
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
      materials: ""
    });
    setMachineImages([]);
  };
  
  // Open create dialog
  const openCreateDialog = () => {
    setEditMachine(null);
    resetForm();
    setCreateDialogOpen(true);
  };
  
  // Open edit dialog
  const openEditDialog = (machine) => {
    setEditMachine(machine);
    setMachineForm({
      name: machine.name || machine.model || "",
      machine_category: machine.machine_category || "",
      machine_type: machine.machine_type || "",
      brand: machine.brand || "",
      model: machine.model || "",
      tolerance: machine.tolerance || 0.01,
      max_x: machine.max_x || 0,
      max_y: machine.max_y || 0,
      max_z: machine.max_z || 0,
      max_diameter: machine.max_diameter || 0,
      max_length: machine.max_length || 0,
      materials: (machine.materials || machine.materials_supported)?.join(", ") || ""
    });
    setMachineImages(machine.images || []);
    setEditDialogOpen(true);
  };
  
  // Save machine (update)
  const saveMachine = async () => {
    if (!editMachine) return;
    setSaving(true);
    try {
      const payload = {
        ...machineForm,
        materials: machineForm.materials ? machineForm.materials.split(",").map(m => m.trim()) : []
      };
      await api.put(`/admin/machines/${editMachine.machine_id}`, payload);
      toast.success("Machine updated");
      setEditDialogOpen(false);
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to update machine");
    } finally {
      setSaving(false);
    }
  };
  
  // Create new machine
  const createMachine = async () => {
    if (!machineForm.vendor_id) {
      toast.error("Please select a vendor");
      return;
    }
    if (!machineForm.machine_category) {
      toast.error("Please select a machine category");
      return;
    }
    setSaving(true);
    try {
      const payload = {
        ...machineForm,
        materials: machineForm.materials ? machineForm.materials.split(",").map(m => m.trim()) : []
      };
      await api.post("/admin/machines", payload);
      toast.success("Machine created successfully");
      setCreateDialogOpen(false);
      resetForm();
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to create machine");
    } finally {
      setSaving(false);
    }
  };
  
  // Delete machine
  const deleteMachine = async (machineId) => {
    if (!confirm("Delete this machine?")) return;
    try {
      await api.delete(`/admin/machines/${machineId}`);
      toast.success("Machine deleted");
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to delete machine");
    }
  };
  
  // Upload image
  const uploadMachineImage = async (machineId, file) => {
    setUploadingImage(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await api.post(`/admin/machines/${machineId}/images`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setMachineImages(res.data.images || []);
      toast.success("Image uploaded");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to upload image");
    } finally {
      setUploadingImage(false);
    }
  };
  
  // Delete image
  const deleteMachineImage = async (machineId, imageUrl) => {
    try {
      const res = await api.delete(`/admin/machines/${machineId}/images`, {
        params: { image_url: imageUrl }
      });
      setMachineImages(res.data.images || []);
      toast.success("Image deleted");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to delete image");
    }
  };
  
  // Get vendor name by ID
  const getVendorName = (vendorId) => {
    const vendor = vendors?.find(v => v.vendor_id === vendorId);
    return vendor?.company_name || vendorId || "Unknown";
  };
  
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-heading">All Machines ({machines.length})</CardTitle>
          <div className="flex gap-2">
            {canCreate && (
              <Button size="sm" className="bg-orange-600 hover:bg-orange-700" onClick={openCreateDialog} data-testid="machines-tab-add-btn">
                <Plus className="w-4 h-4 mr-1" /> Add Machine
              </Button>
            )}
            <Button variant="outline" size="sm" onClick={onRefresh}>
              <RefreshCw className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {/* Filters */}
        <div className="flex gap-4 mb-4 flex-wrap">
          <div className="flex-1 min-w-[200px]">
            <Input
              placeholder="Search machines..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="h-9"
            />
          </div>
          <Select value={categoryFilter} onValueChange={setCategoryFilter}>
            <SelectTrigger className="w-48 h-9">
              <SelectValue placeholder="All Categories" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Categories</SelectItem>
              {uniqueCategories.map(cat => (
                <SelectItem key={cat} value={cat}>{cat}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={vendorFilter} onValueChange={setVendorFilter}>
            <SelectTrigger className="w-48 h-9">
              <SelectValue placeholder="All Vendors" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Vendors</SelectItem>
              {vendors?.map(v => (
                <SelectItem key={v.vendor_id} value={v.vendor_id}>{v.company_name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        
        {/* Machines Table */}
        {loading ? (
          <div className="text-center py-8"><Loader2 className="w-8 h-8 animate-spin mx-auto text-orange-600" /></div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-50 border-b">
                <tr>
                  <th className="text-left p-3 text-xs font-bold uppercase text-slate-600">Machine</th>
                  <th className="text-left p-3 text-xs font-bold uppercase text-slate-600">Vendor</th>
                  <th className="text-left p-3 text-xs font-bold uppercase text-slate-600">Category</th>
                  <th className="text-left p-3 text-xs font-bold uppercase text-slate-600">Specs</th>
                  <th className="text-left p-3 text-xs font-bold uppercase text-slate-600">Images</th>
                  {(canEdit || canDelete) && (
                    <th className="text-right p-3 text-xs font-bold uppercase text-slate-600">Actions</th>
                  )}
                </tr>
              </thead>
              <tbody className="divide-y">
                {filteredMachines.map((machine) => (
                  <tr key={machine.machine_id} className="hover:bg-slate-50">
                    <td className="p-3">
                      <div>
                        <p className="font-medium text-slate-900">{machine.name || machine.model || machine.machine_type}</p>
                        <p className="text-xs text-slate-500">{machine.brand} {machine.model}</p>
                      </div>
                    </td>
                    <td className="p-3 text-sm">{getVendorName(machine.vendor_id)}</td>
                    <td className="p-3">
                      <span className="text-xs bg-orange-100 text-orange-700 px-2 py-1 rounded">
                        {machine.machine_category || machine.machine_type || 'N/A'}
                      </span>
                    </td>
                    <td className="p-3 text-xs text-slate-500">
                      {machine.max_x || machine.max_diameter ? (
                        <span>
                          {machine.max_x ? `${machine.max_x}×${machine.max_y}×${machine.max_z}mm` : ''}
                          {machine.max_diameter ? ` Ø${machine.max_diameter}mm` : ''}
                        </span>
                      ) : '-'}
                    </td>
                    <td className="p-3">
                      <span className="text-sm">{machine.images?.length || 0}</span>
                    </td>
                    {(canEdit || canDelete) && (
                      <td className="p-3 text-right">
                        <div className="flex gap-1 justify-end">
                          {canEdit && (
                            <Button variant="ghost" size="sm" onClick={() => openEditDialog(machine)}>
                              <Edit className="w-4 h-4" />
                            </Button>
                          )}
                          {canDelete && (
                            <Button variant="ghost" size="sm" className="text-red-600" onClick={() => deleteMachine(machine.machine_id)}>
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          )}
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
            {filteredMachines.length === 0 && (
              <div className="text-center py-8 text-slate-500">No machines found</div>
            )}
          </div>
        )}
        
        {/* Edit Machine Dialog */}
        <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Edit Machine</DialogTitle>
            </DialogHeader>
            <div className="grid grid-cols-2 gap-4 py-4">
              <div>
                <Label>Category</Label>
                <Select value={machineForm.machine_category || ""} onValueChange={(v) => setMachineForm(f => ({...f, machine_category: v}))}>
                  <SelectTrigger><SelectValue placeholder="Select category" /></SelectTrigger>
                  <SelectContent>
                    {Object.keys(machineCategories).sort().map(cat => (
                      <SelectItem key={cat} value={cat}>{cat}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Type</Label>
                <Select value={machineForm.machine_type || ""} onValueChange={(v) => setMachineForm(f => ({...f, machine_type: v}))}>
                  <SelectTrigger><SelectValue placeholder="Select type" /></SelectTrigger>
                  <SelectContent>
                    {(machineCategories[machineForm.machine_category]?.types || []).map(t => (
                      <SelectItem key={t} value={t}>{t}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Brand</Label>
                <Input value={machineForm.brand || ""} onChange={(e) => setMachineForm(f => ({...f, brand: e.target.value}))} />
              </div>
              <div>
                <Label>Model</Label>
                <Input value={machineForm.model || ""} onChange={(e) => setMachineForm(f => ({...f, model: e.target.value}))} />
              </div>
              <div>
                <Label>Tolerance (mm)</Label>
                <Input type="number" step="0.001" value={machineForm.tolerance || 0} onChange={(e) => setMachineForm(f => ({...f, tolerance: parseFloat(e.target.value)}))} />
              </div>
              <div>
                <Label>Max Diameter (mm)</Label>
                <Input type="number" value={machineForm.max_diameter || 0} onChange={(e) => setMachineForm(f => ({...f, max_diameter: parseFloat(e.target.value)}))} />
              </div>
              <div className="col-span-2">
                <Label>Materials (comma-separated)</Label>
                <Input value={machineForm.materials || ""} onChange={(e) => setMachineForm(f => ({...f, materials: e.target.value}))} placeholder="Steel, Aluminum, Titanium" />
              </div>
              
              {/* Images Section */}
              {canManageImages && editMachine && (
                <div className="col-span-2 border-t pt-4 mt-2">
                  <Label className="flex items-center gap-2 mb-3">
                    <Camera className="w-4 h-4 text-orange-600" />
                    Machine Images ({machineImages.length})
                  </Label>
                  {machineImages.length > 0 && (
                    <div className="grid grid-cols-4 gap-2 mb-3">
                      {machineImages.map((img, idx) => (
                        <div key={idx} className="relative group rounded-lg overflow-hidden border bg-slate-50">
                          <img src={img} alt={`Machine ${idx + 1}`} className="w-full h-16 object-cover" onError={(e) => { e.target.src = '/placeholder.png'; }} />
                          <button onClick={() => deleteMachineImage(editMachine.machine_id, img)} className="absolute top-1 right-1 p-1 bg-red-500 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity">
                            <XCircle className="w-3 h-3" />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                  <div className="flex items-center gap-2">
                    <input type="file" id="machine-img-upload" accept="image/*" className="hidden" onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) { uploadMachineImage(editMachine.machine_id, file); e.target.value = ''; }
                    }} />
                    <Button type="button" variant="outline" size="sm" disabled={uploadingImage} onClick={() => document.getElementById('machine-img-upload').click()} className="w-full">
                      {uploadingImage ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Uploading...</> : <><Upload className="w-4 h-4 mr-2" />Upload Image</>}
                    </Button>
                  </div>
                </div>
              )}
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setEditDialogOpen(false)}>Cancel</Button>
              <Button onClick={saveMachine} disabled={saving} className="bg-orange-600 hover:bg-orange-700">
                {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                Save Changes
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
        
        {/* Create Machine Dialog */}
        <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Add New Machine</DialogTitle>
            </DialogHeader>
            <div className="grid grid-cols-2 gap-4 py-4">
              {/* Vendor Selection - Required */}
              <div className="col-span-2">
                <Label className="text-orange-600 font-medium">Select Vendor *</Label>
                <Select value={machineForm.vendor_id || ""} onValueChange={(v) => setMachineForm(f => ({...f, vendor_id: v}))}>
                  <SelectTrigger className="border-orange-200 focus:ring-orange-500"><SelectValue placeholder="Select vendor first" /></SelectTrigger>
                  <SelectContent>
                    {vendors?.filter(v => v.is_approved).map(v => (
                      <SelectItem key={v.vendor_id} value={v.vendor_id}>{v.company_name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              {/* Machine Name */}
              <div className="col-span-2">
                <Label>Machine Name</Label>
                <Input value={machineForm.name || ""} onChange={(e) => setMachineForm(f => ({...f, name: e.target.value}))} placeholder="e.g. Haas VF-2SS" />
              </div>
              
              {/* Category */}
              <div className="col-span-2">
                <Label className="text-orange-600 font-medium">Machine Category *</Label>
                <Select value={machineForm.machine_category || ""} onValueChange={(v) => setMachineForm(f => ({...f, machine_category: v, machine_type: ""}))}>
                  <SelectTrigger className="border-orange-200 focus:ring-orange-500"><SelectValue placeholder="Select category" /></SelectTrigger>
                  <SelectContent>
                    {Object.keys(machineCategories).sort().map(cat => (
                      <SelectItem key={cat} value={cat}>{cat}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              {/* Type */}
              <div>
                <Label>Machine Type</Label>
                <Select value={machineForm.machine_type || ""} onValueChange={(v) => setMachineForm(f => ({...f, machine_type: v}))} disabled={!machineForm.machine_category}>
                  <SelectTrigger><SelectValue placeholder={machineForm.machine_category ? "Select type" : "Select category first"} /></SelectTrigger>
                  <SelectContent>
                    {getMachineTypes().map(t => (
                      <SelectItem key={t} value={t}>{t}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              {/* Brand */}
              <div>
                <Label>Brand</Label>
                <Input value={machineForm.brand || ""} onChange={(e) => setMachineForm(f => ({...f, brand: e.target.value}))} placeholder="e.g. Haas, DMG Mori" />
              </div>
              
              {/* Model */}
              <div>
                <Label>Model</Label>
                <Input value={machineForm.model || ""} onChange={(e) => setMachineForm(f => ({...f, model: e.target.value}))} placeholder="e.g. VF-2SS" />
              </div>
              
              {/* Tolerance */}
              <div>
                <Label>Tolerance (mm)</Label>
                <Input type="number" step="0.001" value={machineForm.tolerance || 0.01} onChange={(e) => setMachineForm(f => ({...f, tolerance: parseFloat(e.target.value) || 0}))} />
              </div>
              
              {/* Dynamic Dimension Fields Based on Category */}
              {machineForm.machine_category && getDimensionFields().length > 0 && (
                <>
                  <div className="col-span-2 border-t pt-4 mt-2">
                    <p className="text-sm font-medium text-slate-700 mb-3">{machineForm.machine_category} Dimensions</p>
                  </div>
                  {getDimensionFields().map(field => (
                    <div key={field.key}>
                      <Label>{field.label}</Label>
                      <Input 
                        type="number" 
                        step={field.key.includes("angle") ? "0.1" : "1"}
                        value={machineForm[field.key] || 0} 
                        onChange={(e) => setMachineForm(f => ({...f, [field.key]: parseFloat(e.target.value) || 0}))} 
                      />
                    </div>
                  ))}
                </>
              )}
              
              {/* Materials */}
              <div className="col-span-2 border-t pt-4 mt-2">
                <Label>Materials (comma-separated)</Label>
                <Input value={machineForm.materials || ""} onChange={(e) => setMachineForm(f => ({...f, materials: e.target.value}))} placeholder="Steel, Aluminum, Titanium, Brass" />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
              <Button onClick={createMachine} disabled={saving || !machineForm.vendor_id || !machineForm.machine_category} className="bg-orange-600 hover:bg-orange-700">
                {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Plus className="w-4 h-4 mr-2" />}
                Create Machine
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </CardContent>
    </Card>
  );
};

// ============== MAIN ADMIN DASHBOARD ==============
const AdminDashboard = () => {
  const { user } = useAuth();
  const { hasAnyPermission } = usePermissions();
  const location = useLocation();
  const navigate = useNavigate();
  
  // Check if user is admin (full access) or staff (permission-based)
  const isAdmin = user?.role === 'admin';
  
  // Get permitted tabs based on user permissions
  const getPermittedTabs = () => {
    return Object.entries(TAB_CONFIG).filter(([tabId, config]) => {
      // Admin gets all tabs
      if (isAdmin) return true;
      // Staff users need required permissions
      if (config.permissions.length === 0) return true;
      return hasAnyPermission(config.permissions);
    }).map(([tabId]) => tabId);
  };
  
  const permittedTabs = getPermittedTabs();
  
  // Determine dashboard type for actions - use custom_role if available, otherwise "admin"
  const dashboardType = user?.custom_role || 'admin';
  
  // Get initial tab from URL query parameter
  const searchParams = new URLSearchParams(location.search);
  const urlTab = searchParams.get('tab') || 'overview';
  // If URL tab is not permitted, default to first permitted tab
  const initialTab = permittedTabs.includes(urlTab) ? urlTab : permittedTabs[0] || 'overview';
  
  const [activeTab, setActiveTab] = useState(initialTab);
  const [loading, setLoading] = useState(true);
  
  // Data states
  const [stats, setStats] = useState(null);
  const [pendingVendors, setPendingVendors] = useState([]);
  const [users, setUsers] = useState([]);
  const [rfqs, setRfqs] = useState([]);
  const [quotes, setQuotes] = useState([]);
  const [orders, setOrders] = useState([]);
  const [drawings, setDrawings] = useState([]);
  const [ndas, setNdas] = useState([]);
  const [vendors, setVendors] = useState([]);
  const [allMachines, setAllMachines] = useState([]);

  // Update tab when URL changes
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const tabFromUrl = params.get('tab');
    if (tabFromUrl && tabFromUrl !== activeTab && permittedTabs.includes(tabFromUrl)) {
      setActiveTab(tabFromUrl);
    }
  }, [location.search, permittedTabs]);

  // Update URL when tab changes
  const handleTabChange = (tab) => {
    if (!permittedTabs.includes(tab)) return;
    setActiveTab(tab);
    navigate(`/admin/dashboard?tab=${tab}`, { replace: true });
  };

  useEffect(() => {
    fetchInitialData();
  }, []);

  const fetchInitialData = async () => {
    try {
      const [statsRes, pendingRes] = await Promise.all([
        api.get("/admin/stats"),
        api.get("/admin/vendors/pending")
      ]);
      setStats(statsRes.data);
      setPendingVendors(pendingRes.data);
    } catch (error) {
      toast.error("Failed to load admin data");
    } finally {
      setLoading(false);
    }
  };

  const fetchUsers = async () => {
    try {
      const res = await api.get("/admin/users");
      setUsers(res.data);
    } catch (error) {
      toast.error("Failed to load users");
    }
  };

  const fetchRFQs = async () => {
    try {
      const res = await api.get("/admin/rfqs");
      setRfqs(res.data);
    } catch (error) {
      toast.error("Failed to load RFQs");
    }
  };

  const fetchQuotes = async () => {
    try {
      const res = await api.get("/admin/quotes");
      setQuotes(res.data);
    } catch (error) {
      toast.error("Failed to load quotes");
    }
  };

  const fetchOrders = async () => {
    try {
      const res = await api.get("/admin/orders");
      setOrders(res.data);
    } catch (error) {
      toast.error("Failed to load orders");
    }
  };

  const fetchDrawings = async () => {
    try {
      const res = await api.get("/admin/drawings");
      setDrawings(res.data);
    } catch (error) {
      toast.error("Failed to load drawings");
    }
  };

  const fetchNDAs = async () => {
    try {
      const res = await api.get("/admin/ndas");
      setNdas(res.data);
    } catch (error) {
      toast.error("Failed to load NDAs");
    }
  };

  const fetchVendors = async () => {
    try {
      const res = await api.get("/admin/vendors");
      setVendors(res.data);
    } catch (error) {
      toast.error("Failed to load vendors");
    }
  };

  const fetchAllMachines = async () => {
    try {
      const res = await api.get("/admin/machines");
      setAllMachines(res.data);
    } catch (error) {
      toast.error("Failed to load machines");
    }
  };

  // Tab change handler - fetch data for tab
  useEffect(() => {
    if (activeTab === "users" && users.length === 0) fetchUsers();
    if (activeTab === "rfqs" && rfqs.length === 0) fetchRFQs();
    if (activeTab === "quotes" && quotes.length === 0) fetchQuotes();
    if (activeTab === "orders" && orders.length === 0) fetchOrders();
    if (activeTab === "drawings" && drawings.length === 0) fetchDrawings();
    if (activeTab === "ndas") {
      fetchNDAs();
      if (users.length === 0) fetchUsers();
      if (vendors.length === 0) fetchVendors();
    }
    if (activeTab === "vendors" && vendors.length === 0) fetchVendors();
    if (activeTab === "machines") {
      if (allMachines.length === 0) fetchAllMachines();
      if (vendors.length === 0) fetchVendors();
    }
  }, [activeTab]);

  // Action handlers
  const approveVendor = async (vendorId) => {
    try {
      await api.post(`/admin/vendors/${vendorId}/approve`);
      toast.success("Vendor approved");
      fetchInitialData();
      if (vendors.length > 0) fetchVendors();
    } catch (error) {
      toast.error("Failed to approve vendor");
    }
  };

  const rejectVendor = async (vendorId) => {
    try {
      await api.post(`/admin/vendors/${vendorId}/reject`);
      toast.success("Vendor rejected");
      fetchInitialData();
      if (vendors.length > 0) fetchVendors();
    } catch (error) {
      toast.error("Failed to reject vendor");
    }
  };

  const updateUser = async (userId, data) => {
    try {
      await api.put(`/admin/users/${userId}`, data);
      toast.success("User updated");
      fetchUsers();
    } catch (error) {
      toast.error("Failed to update user");
    }
  };

  const createUser = async (data) => {
    try {
      await api.post("/admin/users", data);
      toast.success("User created successfully");
      fetchUsers();
      fetchInitialData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to create user");
      throw error;
    }
  };

  const createVendor = async (data) => {
    try {
      await api.post("/admin/vendors", data);
      toast.success("Vendor created successfully");
      fetchVendors();
      fetchInitialData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to create vendor");
      throw error;
    }
  };

  const deleteUser = async (userId) => {
    if (!confirm("Are you sure you want to delete this user?")) return;
    try {
      await api.delete(`/admin/users/${userId}`);
      toast.success("User deleted");
      fetchUsers();
      fetchInitialData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to delete user");
    }
  };

  const updateRFQ = async (rfqId, data) => {
    try {
      await api.put(`/admin/rfqs/${rfqId}`, data);
      toast.success("RFQ updated");
      fetchRFQs();
    } catch (error) {
      toast.error("Failed to update RFQ");
    }
  };

  const deleteRFQ = async (rfqId) => {
    if (!confirm("Are you sure you want to delete this RFQ?")) return;
    try {
      await api.delete(`/admin/rfqs/${rfqId}`);
      toast.success("RFQ deleted");
      fetchRFQs();
      fetchInitialData();
    } catch (error) {
      toast.error("Failed to delete RFQ");
    }
  };

  const updateQuote = async (quoteId, data) => {
    try {
      await api.put(`/admin/quotes/${quoteId}`, data);
      toast.success("Quote updated");
      fetchQuotes();
    } catch (error) {
      toast.error("Failed to update quote");
    }
  };

  const deleteQuote = async (quoteId) => {
    if (!confirm("Are you sure you want to delete this quote?")) return;
    try {
      await api.delete(`/admin/quotes/${quoteId}`);
      toast.success("Quote deleted");
      fetchQuotes();
    } catch (error) {
      toast.error("Failed to delete quote");
    }
  };

  const updateOrder = async (orderId, data) => {
    try {
      await api.put(`/admin/orders/${orderId}`, data);
      toast.success("Order updated");
      fetchOrders();
    } catch (error) {
      toast.error("Failed to update order");
    }
  };

  const deleteOrder = async (orderId) => {
    if (!confirm("Are you sure you want to delete this order?")) return;
    try {
      await api.delete(`/admin/orders/${orderId}`);
      toast.success("Order deleted");
      fetchOrders();
      fetchInitialData();
    } catch (error) {
      toast.error("Failed to delete order");
    }
  };

  const deleteDrawing = async (drawingId) => {
    if (!confirm("Are you sure you want to delete this drawing?")) return;
    try {
      await api.delete(`/admin/drawings/${drawingId}`);
      toast.success("Drawing deleted");
      fetchDrawings();
    } catch (error) {
      toast.error("Failed to delete drawing");
    }
  };

  const createNDA = async (data) => {
    try {
      await api.post("/admin/ndas", data);
      toast.success("NDA created");
      fetchNDAs();
      fetchInitialData();
    } catch (error) {
      toast.error("Failed to create NDA");
    }
  };

  const updateNDA = async (ndaId, data) => {
    try {
      await api.put(`/admin/ndas/${ndaId}`, data);
      toast.success("NDA updated");
      fetchNDAs();
    } catch (error) {
      toast.error("Failed to update NDA");
    }
  };

  const sendNDA = async (ndaId) => {
    try {
      await api.post(`/admin/ndas/${ndaId}/send`);
      toast.success("NDA sent for signing");
      fetchNDAs();
    } catch (error) {
      toast.error("Failed to send NDA");
    }
  };

  const deleteNDA = async (ndaId) => {
    if (!confirm("Are you sure you want to delete this NDA?")) return;
    try {
      await api.delete(`/admin/ndas/${ndaId}`);
      toast.success("NDA deleted");
      fetchNDAs();
      fetchInitialData();
    } catch (error) {
      toast.error("Failed to delete NDA");
    }
  };

  const updateVendor = async (vendorId, data) => {
    try {
      await api.put(`/admin/vendors/${vendorId}`, data);
      toast.success("Vendor updated");
      fetchVendors();
    } catch (error) {
      toast.error("Failed to update vendor");
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
      <div className="space-y-6" data-testid="admin-dashboard">
        {/* Header */}
        <div>
          <h1 className="font-heading text-2xl font-bold text-slate-900">Admin Dashboard</h1>
          <p className="text-slate-500">Platform management and operations</p>
        </div>

        {/* Tabs - Only show permitted tabs */}
        <div className="border-b border-slate-200 overflow-x-auto">
          <div className="flex min-w-max">
            {permittedTabs.includes('overview') && (
              <TabButton 
                active={activeTab === "overview"} 
                onClick={() => handleTabChange("overview")} 
                icon={Package} 
                label="Overview" 
              />
            )}
            {permittedTabs.includes('users') && (
              <TabButton 
                active={activeTab === "users"} 
                onClick={() => handleTabChange("users")} 
                icon={Users} 
                label="Users"
                count={stats?.total_users}
              />
            )}
            {permittedTabs.includes('vendors') && (
              <TabButton 
                active={activeTab === "vendors"} 
                onClick={() => handleTabChange("vendors")} 
                icon={Building2} 
                label="Vendors"
                count={stats?.total_vendors}
              />
            )}
            {permittedTabs.includes('machines') && (
              <TabButton 
                active={activeTab === "machines"} 
                onClick={() => handleTabChange("machines")} 
                icon={Wrench} 
                label="Machines"
                count={allMachines.length || stats?.total_machines}
              />
            )}
            {permittedTabs.includes('rfqs') && (
              <TabButton 
                active={activeTab === "rfqs"} 
                onClick={() => handleTabChange("rfqs")} 
                icon={FileText} 
                label="RFQs"
                count={stats?.total_rfqs}
              />
            )}
            {permittedTabs.includes('quotes') && (
              <TabButton 
                active={activeTab === "quotes"} 
                onClick={() => handleTabChange("quotes")} 
                icon={DollarSign} 
                label="Quotes"
                count={stats?.total_quotes}
              />
            )}
            {permittedTabs.includes('orders') && (
              <TabButton 
                active={activeTab === "orders"} 
                onClick={() => handleTabChange("orders")} 
                icon={Package} 
                label="Orders"
                count={stats?.total_orders}
              />
            )}
            {permittedTabs.includes('drawings') && (
              <TabButton 
                active={activeTab === "drawings"} 
                onClick={() => handleTabChange("drawings")} 
                icon={Wrench} 
                label="Drawings"
              />
            )}
            {permittedTabs.includes('ndas') && (
              <TabButton 
                active={activeTab === "ndas"} 
                onClick={() => handleTabChange("ndas")} 
                icon={FileCheck} 
                label="NDAs"
                count={stats?.total_ndas}
              />
            )}
          </div>
        </div>

        {/* Tab Content - Only render if tab is permitted */}
        {activeTab === "overview" && permittedTabs.includes('overview') && (
          <OverviewTab 
            stats={stats} 
            pendingVendors={pendingVendors}
            onApproveVendor={approveVendor}
            onRejectVendor={rejectVendor}
            onRefresh={fetchInitialData}
            dashboardType={dashboardType}
          />
        )}
        {activeTab === "users" && permittedTabs.includes('users') && (
          <UsersTab 
            users={users} 
            loading={loading}
            onRefresh={fetchUsers}
            onUpdateUser={updateUser}
            onDeleteUser={deleteUser}
            onCreateUser={createUser}
            canEdit={isAdmin || hasAnyPermission(['users.edit'])}
            canDelete={isAdmin || hasAnyPermission(['users.delete'])}
            canCreate={isAdmin || hasAnyPermission(['users.create'])}
          />
        )}
        {activeTab === "vendors" && permittedTabs.includes('vendors') && (
          <VendorsTab
            vendors={vendors}
            loading={loading}
            onRefresh={fetchVendors}
            onApprove={approveVendor}
            onReject={rejectVendor}
            onUpdateVendor={updateVendor}
            onCreateVendor={createVendor}
            canEdit={isAdmin || hasAnyPermission(['vendors.edit'])}
            canDelete={isAdmin || hasAnyPermission(['vendors.delete'])}
            canCreate={isAdmin || hasAnyPermission(['vendors.create'])}
            canApprove={isAdmin || hasAnyPermission(['vendors.approve'])}
            canSearchMachines={isAdmin || hasAnyPermission(['vendors.search_machines'])}
            canViewMachines={isAdmin || hasAnyPermission(['machines.view'])}
            canCreateMachines={isAdmin || hasAnyPermission(['machines.create'])}
            canEditMachines={isAdmin || hasAnyPermission(['machines.edit'])}
            canDeleteMachines={isAdmin || hasAnyPermission(['machines.delete'])}
            canManageMachineImages={isAdmin || hasAnyPermission(['machines.manage_images'])}
          />
        )}
        {activeTab === "machines" && permittedTabs.includes('machines') && (
          <MachinesTab
            machines={allMachines}
            loading={loading}
            onRefresh={fetchAllMachines}
            vendors={vendors}
            canCreate={isAdmin || hasAnyPermission(['machines.create'])}
            canEdit={isAdmin || hasAnyPermission(['machines.edit'])}
            canDelete={isAdmin || hasAnyPermission(['machines.delete'])}
            canManageImages={isAdmin || hasAnyPermission(['machines.manage_images'])}
          />
        )}
        {activeTab === "rfqs" && permittedTabs.includes('rfqs') && (
          <RFQsTab 
            rfqs={rfqs} 
            loading={loading}
            onRefresh={fetchRFQs}
            onUpdateRFQ={updateRFQ}
            onDeleteRFQ={deleteRFQ}
            canEdit={isAdmin || hasAnyPermission(['rfqs.edit'])}
            canDelete={isAdmin || hasAnyPermission(['rfqs.delete'])}
            canMatchVendors={isAdmin || hasAnyPermission(['rfqs.match_vendors'])}
          />
        )}
        {activeTab === "quotes" && permittedTabs.includes('quotes') && (
          <QuotesTab 
            quotes={quotes} 
            loading={loading}
            onRefresh={fetchQuotes}
            onUpdateQuote={updateQuote}
            onDeleteQuote={deleteQuote}
          />
        )}
        {activeTab === "orders" && permittedTabs.includes('orders') && (
          <OrdersTab 
            orders={orders} 
            loading={loading}
            onRefresh={fetchOrders}
            onUpdateOrder={updateOrder}
            onDeleteOrder={deleteOrder}
          />
        )}
        {activeTab === "drawings" && permittedTabs.includes('drawings') && (
          <DrawingsTab 
            drawings={drawings} 
            loading={loading}
            onRefresh={fetchDrawings}
            onDeleteDrawing={deleteDrawing}
          />
        )}
        {activeTab === "ndas" && permittedTabs.includes('ndas') && (
          <NDAsTab 
            ndas={ndas}
            users={users}
            vendors={vendors}
            loading={loading}
            onRefresh={fetchNDAs}
            onCreateNDA={createNDA}
            onUpdateNDA={updateNDA}
            onSendNDA={sendNDA}
            onDeleteNDA={deleteNDA}
          />
        )}
      </div>
    </DashboardLayout>
  );
};

export default AdminDashboard;
