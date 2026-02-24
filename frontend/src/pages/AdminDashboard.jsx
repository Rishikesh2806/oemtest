import { useState, useEffect } from "react";
import { useAuth, api } from "../App";
import DashboardLayout from "../components/layout/DashboardLayout";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { toast } from "sonner";
import { 
  Users, FileText, Package, DollarSign, 
  CheckCircle2, XCircle, Loader2, Building2
} from "lucide-react";

const AdminDashboard = () => {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [pendingVendors, setPendingVendors] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [statsRes, vendorsRes] = await Promise.all([
        api.get("/admin/stats"),
        api.get("/admin/vendors/pending")
      ]);
      setStats(statsRes.data);
      setPendingVendors(vendorsRes.data);
    } catch (error) {
      toast.error("Failed to load admin data");
    } finally {
      setLoading(false);
    }
  };

  const approveVendor = async (vendorId) => {
    try {
      await api.post(`/admin/vendors/${vendorId}/approve`);
      toast.success("Vendor approved successfully");
      fetchData();
    } catch (error) {
      toast.error("Failed to approve vendor");
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
      <div className="space-y-8" data-testid="admin-dashboard">
        {/* Header */}
        <div>
          <h1 className="font-heading text-2xl font-bold text-slate-900">Admin Dashboard</h1>
          <p className="text-slate-500">Platform overview and management</p>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card className="border-slate-200">
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-slate-100 rounded-lg flex items-center justify-center">
                  <Users className="w-6 h-6 text-slate-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-slate-900">{stats?.total_users || 0}</p>
                  <p className="text-sm text-slate-500">Total Users</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-200">
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center">
                  <Building2 className="w-6 h-6 text-orange-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-slate-900">{stats?.approved_vendors || 0}</p>
                  <p className="text-sm text-slate-500">Active Vendors</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-200">
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                  <FileText className="w-6 h-6 text-blue-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-slate-900">{stats?.total_rfqs || 0}</p>
                  <p className="text-sm text-slate-500">Total RFQs</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-200">
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                  <Package className="w-6 h-6 text-green-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-slate-900">{stats?.total_orders || 0}</p>
                  <p className="text-sm text-slate-500">Total Orders</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Pending Vendors */}
        <Card className="border-slate-200">
          <CardHeader>
            <CardTitle className="font-heading text-lg flex items-center gap-2">
              <Building2 className="w-5 h-5 text-orange-600" />
              Pending Vendor Approvals ({stats?.pending_vendors || 0})
            </CardTitle>
          </CardHeader>
          <CardContent>
            {pendingVendors.length > 0 ? (
              <div className="space-y-4">
                {pendingVendors.map((vendor) => (
                  <div
                    key={vendor.vendor_id}
                    className="flex items-center justify-between p-4 bg-slate-50 rounded-lg"
                    data-testid={`vendor-item-${vendor.vendor_id}`}
                  >
                    <div>
                      <p className="font-medium text-slate-900">{vendor.company_name}</p>
                      <p className="text-sm text-slate-500">
                        {vendor.city}, {vendor.country} • {vendor.industries?.join(", ")}
                      </p>
                      <div className="flex flex-wrap gap-2 mt-2">
                        {vendor.certifications?.map((cert, i) => (
                          <span key={i} className="text-xs bg-slate-200 text-slate-600 px-2 py-1 rounded">
                            {cert}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        onClick={() => approveVendor(vendor.vendor_id)}
                        className="bg-green-600 hover:bg-green-700"
                        size="sm"
                        data-testid={`approve-vendor-${vendor.vendor_id}`}
                      >
                        <CheckCircle2 className="w-4 h-4 mr-1" /> Approve
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
    </DashboardLayout>
  );
};

export default AdminDashboard;
