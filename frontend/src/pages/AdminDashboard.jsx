import { useState, useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth, api } from "../App";
import DashboardLayout from "../components/layout/DashboardLayout";
import PermittedActions from "../components/PermittedActions";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "../components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { toast } from "sonner";
import { 
  Users, FileText, Package, DollarSign, Building2, Wrench, FileCheck,
  CheckCircle2, XCircle, Loader2, Search, Plus, Edit, Trash2,
  Eye, Send, AlertCircle, RefreshCw, ChevronRight, Clock
} from "lucide-react";

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
const OverviewTab = ({ stats, pendingVendors, onApproveVendor, onRejectVendor, onRefresh }) => (
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
      dashboardType="admin" 
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
const UsersTab = ({ users, loading, onRefresh, onUpdateUser, onDeleteUser, onCreateUser }) => {
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
        <Button onClick={() => setShowAddDialog(true)} className="bg-orange-600 hover:bg-orange-700">
          <Plus className="w-4 h-4 mr-2" /> Add User
        </Button>
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
                <th className="text-right p-4 text-xs font-bold uppercase text-slate-500">Actions</th>
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
                  <td className="p-4 text-right">
                    <div className="flex justify-end gap-2">
                      <Button variant="ghost" size="sm" onClick={() => handleEdit(user)}>
                        <Edit className="w-4 h-4" />
                      </Button>
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        className="text-red-600 hover:bg-red-50"
                        onClick={() => onDeleteUser(user.user_id)}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </td>
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
const RFQsTab = ({ rfqs, loading, onRefresh, onUpdateRFQ, onDeleteRFQ }) => {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [editRFQ, setEditRFQ] = useState(null);
  const [editForm, setEditForm] = useState({});
  
  const filteredRFQs = rfqs.filter(r => {
    const matchesSearch = r.title?.toLowerCase().includes(search.toLowerCase()) ||
                          r.rfq_id?.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = statusFilter === "all" || r.status === statusFilter;
    return matchesSearch && matchesStatus;
  });
  
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
                  <td className="p-4"><StatusBadge status={rfq.status} /></td>
                  <td className="p-4 text-sm text-slate-500">
                    {new Date(rfq.created_at).toLocaleDateString()}
                  </td>
                  <td className="p-4 text-right">
                    <div className="flex justify-end gap-2">
                      <Button variant="ghost" size="sm" onClick={() => handleEdit(rfq)}>
                        <Edit className="w-4 h-4" />
                      </Button>
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        className="text-red-600 hover:bg-red-50"
                        onClick={() => onDeleteRFQ(rfq.rfq_id)}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
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
const VendorsTab = ({ vendors, loading, onRefresh, onApprove, onReject, onUpdateVendor, onCreateVendor }) => {
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
  };
  
  const resetMachineForm = () => {
    setMachineForm({
      name: "", machine_category: "", machine_type: "", brand: "", model: "", 
      tolerance: 0.01, max_x: 0, max_y: 0, max_z: 0,
      max_diameter: 0, max_length: 0, max_swing: 0,
      bore_diameter: 0, outer_diameter: 0, max_thickness: 0, tonnage: 0,
      max_taper_angle: 0, materials: ""
    });
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
            <Button size="sm" className="bg-orange-600 hover:bg-orange-700" onClick={() => { setCreateMachineOpen(true); setEditMachine(null); resetMachineForm(); }}>
              <Plus className="w-4 h-4 mr-1" /> Add Machine
            </Button>
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
                    <div className="flex gap-2">
                      <Button variant="ghost" size="sm" onClick={() => openEditMachine(machine)}>
                        <Edit className="w-4 h-4" />
                      </Button>
                      <Button variant="ghost" size="sm" className="text-red-600 hover:bg-red-50" onClick={() => deleteMachine(machine.machine_id)}>
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
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
      {/* Filters */}
      <div className="flex gap-4 items-center justify-between">
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
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={onRefresh}>
            <RefreshCw className="w-4 h-4" />
          </Button>
          <Button onClick={() => setShowAddVendorDialog(true)} className="bg-orange-600 hover:bg-orange-700">
            <Plus className="w-4 h-4 mr-2" /> Add Vendor
          </Button>
        </div>
      </div>
      
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
                <th className="text-right p-4 text-xs font-bold uppercase text-slate-500">Actions</th>
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
                  <td className="p-4 text-right">
                    <div className="flex justify-end gap-2">
                      <Button variant="ghost" size="sm" onClick={() => loadVendorProfile(vendor.vendor_id)} title="Manage Profile & Machines">
                        <Eye className="w-4 h-4" />
                      </Button>
                      {!vendor.is_approved && (
                        <Button variant="ghost" size="sm" className="text-green-600 hover:bg-green-50" onClick={() => onApprove(vendor.vendor_id)}>
                          <CheckCircle2 className="w-4 h-4" />
                        </Button>
                      )}
                      {vendor.is_approved && (
                        <Button variant="ghost" size="sm" className="text-amber-600 hover:bg-amber-50" onClick={() => onReject(vendor.vendor_id)}>
                          <XCircle className="w-4 h-4" />
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {filteredVendors.length === 0 && (
            <div className="text-center py-12 text-slate-500">No vendors found</div>
          )}
        </CardContent>
      </Card>

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

// ============== MAIN ADMIN DASHBOARD ==============
const AdminDashboard = () => {
  const { user } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  
  // Get initial tab from URL query parameter
  const searchParams = new URLSearchParams(location.search);
  const initialTab = searchParams.get('tab') || 'overview';
  
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

  // Update tab when URL changes
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const tabFromUrl = params.get('tab');
    if (tabFromUrl && tabFromUrl !== activeTab) {
      setActiveTab(tabFromUrl);
    }
  }, [location.search]);

  // Update URL when tab changes
  const handleTabChange = (tab) => {
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

        {/* Tabs */}
        <div className="border-b border-slate-200 overflow-x-auto">
          <div className="flex min-w-max">
            <TabButton 
              active={activeTab === "overview"} 
              onClick={() => handleTabChange("overview")} 
              icon={Package} 
              label="Overview" 
            />
            <TabButton 
              active={activeTab === "users"} 
              onClick={() => handleTabChange("users")} 
              icon={Users} 
              label="Users"
              count={stats?.total_users}
            />
            <TabButton 
              active={activeTab === "vendors"} 
              onClick={() => handleTabChange("vendors")} 
              icon={Building2} 
              label="Vendors"
              count={stats?.total_vendors}
            />
            <TabButton 
              active={activeTab === "rfqs"} 
              onClick={() => handleTabChange("rfqs")} 
              icon={FileText} 
              label="RFQs"
              count={stats?.total_rfqs}
            />
            <TabButton 
              active={activeTab === "quotes"} 
              onClick={() => handleTabChange("quotes")} 
              icon={DollarSign} 
              label="Quotes"
              count={stats?.total_quotes}
            />
            <TabButton 
              active={activeTab === "orders"} 
              onClick={() => handleTabChange("orders")} 
              icon={Package} 
              label="Orders"
              count={stats?.total_orders}
            />
            <TabButton 
              active={activeTab === "drawings"} 
              onClick={() => handleTabChange("drawings")} 
              icon={Wrench} 
              label="Drawings"
            />
            <TabButton 
              active={activeTab === "ndas"} 
              onClick={() => handleTabChange("ndas")} 
              icon={FileCheck} 
              label="NDAs"
              count={stats?.total_ndas}
            />
          </div>
        </div>

        {/* Tab Content */}
        {activeTab === "overview" && (
          <OverviewTab 
            stats={stats} 
            pendingVendors={pendingVendors}
            onApproveVendor={approveVendor}
            onRejectVendor={rejectVendor}
            onRefresh={fetchInitialData}
          />
        )}
        {activeTab === "users" && (
          <UsersTab 
            users={users} 
            loading={loading}
            onRefresh={fetchUsers}
            onUpdateUser={updateUser}
            onDeleteUser={deleteUser}
            onCreateUser={createUser}
          />
        )}
        {activeTab === "vendors" && (
          <VendorsTab
            vendors={vendors}
            loading={loading}
            onRefresh={fetchVendors}
            onApprove={approveVendor}
            onReject={rejectVendor}
            onUpdateVendor={updateVendor}
            onCreateVendor={createVendor}
          />
        )}
        {activeTab === "rfqs" && (
          <RFQsTab 
            rfqs={rfqs} 
            loading={loading}
            onRefresh={fetchRFQs}
            onUpdateRFQ={updateRFQ}
            onDeleteRFQ={deleteRFQ}
          />
        )}
        {activeTab === "quotes" && (
          <QuotesTab 
            quotes={quotes} 
            loading={loading}
            onRefresh={fetchQuotes}
            onUpdateQuote={updateQuote}
            onDeleteQuote={deleteQuote}
          />
        )}
        {activeTab === "orders" && (
          <OrdersTab 
            orders={orders} 
            loading={loading}
            onRefresh={fetchOrders}
            onUpdateOrder={updateOrder}
            onDeleteOrder={deleteOrder}
          />
        )}
        {activeTab === "drawings" && (
          <DrawingsTab 
            drawings={drawings} 
            loading={loading}
            onRefresh={fetchDrawings}
            onDeleteDrawing={deleteDrawing}
          />
        )}
        {activeTab === "ndas" && (
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
