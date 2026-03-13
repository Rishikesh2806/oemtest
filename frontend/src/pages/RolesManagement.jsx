import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Checkbox } from '../components/ui/checkbox';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { toast } from 'sonner';
import { 
  Shield, 
  Plus, 
  Edit2, 
  Trash2, 
  Users, 
  Lock,
  RefreshCw,
  Search,
  ChevronDown,
  ChevronRight,
  Save,
  X,
  UserPlus,
  Check
} from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '../components/ui/collapsible';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Color options for roles
const ROLE_COLORS = [
  { value: '#dc2626', label: 'Red' },
  { value: '#ea580c', label: 'Orange' },
  { value: '#ca8a04', label: 'Yellow' },
  { value: '#16a34a', label: 'Green' },
  { value: '#0891b2', label: 'Cyan' },
  { value: '#2563eb', label: 'Blue' },
  { value: '#7c3aed', label: 'Violet' },
  { value: '#9333ea', label: 'Purple' },
  { value: '#db2777', label: 'Pink' },
  { value: '#6b7280', label: 'Gray' },
];

export default function RolesManagement() {
  const [roles, setRoles] = useState([]);
  const [permissions, setPermissions] = useState({});
  const [permissionsList, setPermissionsList] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedRole, setSelectedRole] = useState(null);
  
  // Dialog states
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [showAssignDialog, setShowAssignDialog] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  
  // Form states
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    permissions: [],
    color: '#6b7280'
  });
  
  // Expanded permission modules
  const [expandedModules, setExpandedModules] = useState({});
  
  // Search/filter
  const [searchQuery, setSearchQuery] = useState('');
  const [assignUserSearch, setAssignUserSearch] = useState('');
  
  const getToken = () => localStorage.getItem('token');
  
  // Fetch roles
  const fetchRoles = useCallback(async () => {
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/api/admin/roles`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setRoles(data.roles || []);
      }
    } catch (error) {
      console.error('Failed to fetch roles:', error);
      toast.error('Failed to load roles');
    }
  }, []);
  
  // Fetch permissions
  const fetchPermissions = useCallback(async () => {
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/api/admin/permissions`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setPermissions(data.permissions || {});
        setPermissionsList(data.permissions_list || []);
      }
    } catch (error) {
      console.error('Failed to fetch permissions:', error);
    }
  }, []);
  
  // Fetch users for assignment
  const fetchUsers = useCallback(async () => {
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/api/admin/users`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        // API returns array directly, not wrapped in object
        setUsers(Array.isArray(data) ? data : (data.users || []));
      }
    } catch (error) {
      console.error('Failed to fetch users:', error);
    }
  }, []);
  
  // Initial load
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([fetchRoles(), fetchPermissions(), fetchUsers()]);
      setLoading(false);
    };
    loadData();
  }, [fetchRoles, fetchPermissions, fetchUsers]);
  
  // Toggle permission in form
  const togglePermission = (permId) => {
    setFormData(prev => ({
      ...prev,
      permissions: prev.permissions.includes(permId)
        ? prev.permissions.filter(p => p !== permId)
        : [...prev.permissions, permId]
    }));
  };
  
  // Toggle all permissions in a module
  const toggleModule = (moduleName) => {
    const modulePerms = permissions[moduleName]?.map(p => p.id) || [];
    const allSelected = modulePerms.every(p => formData.permissions.includes(p));
    
    if (allSelected) {
      setFormData(prev => ({
        ...prev,
        permissions: prev.permissions.filter(p => !modulePerms.includes(p))
      }));
    } else {
      setFormData(prev => ({
        ...prev,
        permissions: [...new Set([...prev.permissions, ...modulePerms])]
      }));
    }
  };
  
  // Create role
  const handleCreateRole = async () => {
    if (!formData.name.trim()) {
      toast.error('Role name is required');
      return;
    }
    
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/api/admin/roles`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
      });
      
      if (response.ok) {
        toast.success('Role created successfully');
        setShowCreateDialog(false);
        resetForm();
        fetchRoles();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to create role');
      }
    } catch (error) {
      toast.error('Failed to create role');
    }
  };
  
  // Update role
  const handleUpdateRole = async () => {
    if (!selectedRole) return;
    
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/api/admin/roles/${selectedRole.role_id}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
      });
      
      if (response.ok) {
        toast.success('Role updated successfully');
        setShowEditDialog(false);
        resetForm();
        fetchRoles();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to update role');
      }
    } catch (error) {
      toast.error('Failed to update role');
    }
  };
  
  // Delete role
  const handleDeleteRole = async () => {
    if (!selectedRole) return;
    
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/api/admin/roles/${selectedRole.role_id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        toast.success('Role deleted successfully');
        setShowDeleteDialog(false);
        setSelectedRole(null);
        fetchRoles();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to delete role');
      }
    } catch (error) {
      toast.error('Failed to delete role');
    }
  };
  
  // Assign role to user
  const handleAssignRole = async (userId) => {
    if (!selectedRole) return;
    
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/api/admin/roles/assign`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          user_id: userId,
          role_id: selectedRole.role_id
        })
      });
      
      if (response.ok) {
        toast.success('Role assigned successfully');
        fetchUsers();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to assign role');
      }
    } catch (error) {
      toast.error('Failed to assign role');
    }
  };
  
  // Remove role from user
  const handleRemoveRole = async (userId) => {
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/api/admin/roles/assign/${userId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        toast.success('Role removed from user');
        fetchUsers();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to remove role');
      }
    } catch (error) {
      toast.error('Failed to remove role');
    }
  };
  
  // Open edit dialog
  const openEditDialog = (role) => {
    setSelectedRole(role);
    setFormData({
      name: role.name,
      description: role.description || '',
      permissions: role.permissions || [],
      color: role.color || '#6b7280'
    });
    setShowEditDialog(true);
  };
  
  // Open assign dialog
  const openAssignDialog = (role) => {
    setSelectedRole(role);
    setAssignUserSearch('');
    setShowAssignDialog(true);
  };
  
  // Open delete dialog
  const openDeleteDialog = (role) => {
    setSelectedRole(role);
    setShowDeleteDialog(true);
  };
  
  // Reset form
  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      permissions: [],
      color: '#6b7280'
    });
    setSelectedRole(null);
  };
  
  // Filter roles
  const filteredRoles = roles.filter(role =>
    role.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    role.description?.toLowerCase().includes(searchQuery.toLowerCase())
  );
  
  // Filter users for assignment
  const filteredUsers = users.filter(user =>
    user.name?.toLowerCase().includes(assignUserSearch.toLowerCase()) ||
    user.email?.toLowerCase().includes(assignUserSearch.toLowerCase())
  );
  
  // Permission selector component
  const PermissionSelector = () => (
    <div className="space-y-2 max-h-[400px] overflow-y-auto">
      {Object.entries(permissions).map(([module, perms]) => {
        const modulePerms = perms.map(p => p.id);
        const selectedCount = modulePerms.filter(p => formData.permissions.includes(p)).length;
        const allSelected = selectedCount === modulePerms.length;
        
        return (
          <Collapsible
            key={module}
            open={expandedModules[module]}
            onOpenChange={(open) => setExpandedModules(prev => ({ ...prev, [module]: open }))}
          >
            <div className="flex items-center justify-between p-2 bg-muted/50 rounded">
              <CollapsibleTrigger className="flex items-center gap-2 flex-1">
                {expandedModules[module] ? (
                  <ChevronDown className="h-4 w-4" />
                ) : (
                  <ChevronRight className="h-4 w-4" />
                )}
                <span className="font-medium">{module}</span>
                <Badge variant="secondary" className="ml-2">
                  {selectedCount}/{modulePerms.length}
                </Badge>
              </CollapsibleTrigger>
              <Checkbox
                checked={allSelected}
                onCheckedChange={() => toggleModule(module)}
                className="mr-2"
              />
            </div>
            <CollapsibleContent className="pl-6 pt-2 space-y-2">
              {perms.map(perm => (
                <div key={perm.id} className="flex items-center gap-2">
                  <Checkbox
                    id={perm.id}
                    checked={formData.permissions.includes(perm.id)}
                    onCheckedChange={() => togglePermission(perm.id)}
                  />
                  <Label htmlFor={perm.id} className="flex-1 cursor-pointer">
                    <span className="font-medium">{perm.label}</span>
                    <span className="text-xs text-muted-foreground block">{perm.description}</span>
                  </Label>
                </div>
              ))}
            </CollapsibleContent>
          </Collapsible>
        );
      })}
    </div>
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6" data-testid="roles-management-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Shield className="h-6 w-6" />
            Roles & Permissions
          </h1>
          <p className="text-muted-foreground">Manage user roles and access permissions</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => { fetchRoles(); fetchUsers(); }}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          <Button onClick={() => { resetForm(); setShowCreateDialog(true); }} data-testid="create-role-btn">
            <Plus className="h-4 w-4 mr-2" />
            Create Role
          </Button>
        </div>
      </div>
      
      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search roles..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-9"
          data-testid="search-roles"
        />
      </div>
      
      {/* Roles Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredRoles.map(role => (
          <Card key={role.role_id} className="relative overflow-hidden">
            <div 
              className="absolute top-0 left-0 w-1 h-full" 
              style={{ backgroundColor: role.color || '#6b7280' }}
            />
            <CardHeader className="pb-2">
              <div className="flex items-start justify-between">
                <div>
                  <CardTitle className="text-lg flex items-center gap-2">
                    {role.name}
                    {role.is_system && (
                      <Badge variant="secondary" className="text-xs">
                        <Lock className="h-3 w-3 mr-1" />
                        System
                      </Badge>
                    )}
                  </CardTitle>
                  <CardDescription className="mt-1">
                    {role.description || 'No description'}
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2 mb-3">
                <Badge variant="outline">
                  {role.permissions?.length || 0} permissions
                </Badge>
              </div>
              
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => openEditDialog(role)}
                  data-testid={`edit-role-${role.role_id}`}
                >
                  <Edit2 className="h-3 w-3 mr-1" />
                  Edit
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => openAssignDialog(role)}
                  data-testid={`assign-role-${role.role_id}`}
                >
                  <UserPlus className="h-3 w-3 mr-1" />
                  Assign
                </Button>
                {!role.is_system && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="text-red-500 hover:text-red-600"
                    onClick={() => openDeleteDialog(role)}
                    data-testid={`delete-role-${role.role_id}`}
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
      
      {filteredRoles.length === 0 && (
        <div className="text-center py-12 text-muted-foreground">
          <Shield className="h-12 w-12 mx-auto mb-3 opacity-50" />
          <p>No roles found</p>
        </div>
      )}
      
      {/* Create Role Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Create New Role</DialogTitle>
            <DialogDescription>
              Define a new role with specific permissions
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="name">Role Name</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                  placeholder="e.g., Regional Manager"
                  data-testid="role-name-input"
                />
              </div>
              <div>
                <Label htmlFor="color">Color</Label>
                <Select
                  value={formData.color}
                  onValueChange={(value) => setFormData(prev => ({ ...prev, color: value }))}
                >
                  <SelectTrigger>
                    <SelectValue>
                      <div className="flex items-center gap-2">
                        <div className="w-4 h-4 rounded" style={{ backgroundColor: formData.color }} />
                        {ROLE_COLORS.find(c => c.value === formData.color)?.label || 'Select color'}
                      </div>
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    {ROLE_COLORS.map(color => (
                      <SelectItem key={color.value} value={color.value}>
                        <div className="flex items-center gap-2">
                          <div className="w-4 h-4 rounded" style={{ backgroundColor: color.value }} />
                          {color.label}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            
            <div>
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={formData.description}
                onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                placeholder="Brief description of this role's responsibilities"
                rows={2}
              />
            </div>
            
            <div>
              <Label className="mb-2 block">Permissions ({formData.permissions.length} selected)</Label>
              <PermissionSelector />
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreateRole} data-testid="save-role-btn">
              <Save className="h-4 w-4 mr-2" />
              Create Role
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* Edit Role Dialog */}
      <Dialog open={showEditDialog} onOpenChange={setShowEditDialog}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Edit Role: {selectedRole?.name}</DialogTitle>
            <DialogDescription>
              {selectedRole?.is_system 
                ? 'System role - only permissions can be modified'
                : 'Modify role settings and permissions'
              }
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="edit-name">Role Name</Label>
                <Input
                  id="edit-name"
                  value={formData.name}
                  onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                  disabled={selectedRole?.is_system}
                />
              </div>
              <div>
                <Label htmlFor="edit-color">Color</Label>
                <Select
                  value={formData.color}
                  onValueChange={(value) => setFormData(prev => ({ ...prev, color: value }))}
                >
                  <SelectTrigger>
                    <SelectValue>
                      <div className="flex items-center gap-2">
                        <div className="w-4 h-4 rounded" style={{ backgroundColor: formData.color }} />
                        {ROLE_COLORS.find(c => c.value === formData.color)?.label || 'Select color'}
                      </div>
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    {ROLE_COLORS.map(color => (
                      <SelectItem key={color.value} value={color.value}>
                        <div className="flex items-center gap-2">
                          <div className="w-4 h-4 rounded" style={{ backgroundColor: color.value }} />
                          {color.label}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            
            <div>
              <Label htmlFor="edit-description">Description</Label>
              <Textarea
                id="edit-description"
                value={formData.description}
                onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                rows={2}
              />
            </div>
            
            <div>
              <Label className="mb-2 block">Permissions ({formData.permissions.length} selected)</Label>
              <PermissionSelector />
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowEditDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleUpdateRole}>
              <Save className="h-4 w-4 mr-2" />
              Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* Assign Role Dialog */}
      <Dialog open={showAssignDialog} onOpenChange={setShowAssignDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Assign Role: {selectedRole?.name}</DialogTitle>
            <DialogDescription>
              Select users to assign this role
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            <div className="relative">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search users..."
                value={assignUserSearch}
                onChange={(e) => setAssignUserSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            
            <div className="max-h-[300px] overflow-y-auto space-y-2">
              {filteredUsers.map(user => {
                const hasRole = user.custom_role === selectedRole?.role_id;
                
                return (
                  <div
                    key={user.user_id}
                    className="flex items-center justify-between p-3 border rounded hover:bg-muted/50"
                  >
                    <div>
                      <p className="font-medium">{user.name || 'Unknown'}</p>
                      <p className="text-sm text-muted-foreground">{user.email}</p>
                      <div className="flex gap-1 mt-1">
                        <Badge variant="outline" className="text-xs">{user.role}</Badge>
                        {user.custom_role && (
                          <Badge variant="secondary" className="text-xs">{user.custom_role}</Badge>
                        )}
                      </div>
                    </div>
                    {hasRole ? (
                      <Button
                        variant="outline"
                        size="sm"
                        className="text-red-500"
                        onClick={() => handleRemoveRole(user.user_id)}
                      >
                        <X className="h-4 w-4 mr-1" />
                        Remove
                      </Button>
                    ) : (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleAssignRole(user.user_id)}
                      >
                        <Check className="h-4 w-4 mr-1" />
                        Assign
                      </Button>
                    )}
                  </div>
                );
              })}
              
              {filteredUsers.length === 0 && (
                <p className="text-center py-4 text-muted-foreground">No users found</p>
              )}
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAssignDialog(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* Delete Confirmation Dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Role</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete the role "{selectedRole?.name}"? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeleteDialog(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDeleteRole}>
              <Trash2 className="h-4 w-4 mr-2" />
              Delete Role
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
