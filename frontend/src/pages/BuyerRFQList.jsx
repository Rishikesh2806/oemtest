import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useAuth, api } from "../App";
import DashboardLayout from "../components/layout/DashboardLayout";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { 
  FileText, Plus, Search, ArrowRight, Loader2, 
  Filter, Calendar, Package
} from "lucide-react";
import RefNumber from "../components/RefNumber";

const BuyerRFQList = () => {
  const { user } = useAuth();
  const [rfqs, setRfqs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterStatus, setFilterStatus] = useState("all");

  useEffect(() => {
    fetchRFQs();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const fetchRFQs = async () => {
    try {
      const response = await api.get("/rfqs");
      setRfqs(response.data);
    } catch (error) {
      console.error("Failed to load RFQs:", error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    const badges = {
      draft: "bg-slate-100 text-slate-600",
      submitted: "bg-blue-100 text-blue-600",
      matching: "bg-purple-100 text-purple-600",
      quoted: "bg-amber-100 text-amber-600",
      accepted: "bg-green-100 text-green-600",
      in_progress: "bg-indigo-100 text-indigo-600",
      completed: "bg-teal-100 text-teal-600",
      cancelled: "bg-red-100 text-red-600"
    };
    return badges[status] || "bg-slate-100 text-slate-600";
  };

  const filteredRFQs = rfqs.filter(rfq => {
    const term = searchTerm.toLowerCase();
    const matchesSearch = rfq.title.toLowerCase().includes(term) ||
                         rfq.rfq_number?.toLowerCase().includes(term) ||
                         rfq.material_type?.toLowerCase().includes(term);
    const matchesStatus = filterStatus === "all" || rfq.status === filterStatus;
    return matchesSearch && matchesStatus;
  });

  const statuses = ["all", "draft", "submitted", "matching", "quoted", "accepted", "in_progress", "completed"];

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
      <div className="space-y-6" data-testid="buyer-rfq-list">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="font-heading text-2xl font-bold text-slate-900">My RFQs</h1>
            <p className="text-slate-500 mt-1">{rfqs.length} total requests</p>
          </div>
          <Link to="/buyer/rfq/new">
            <Button className="bg-orange-600 hover:bg-orange-700" data-testid="create-rfq-btn">
              <Plus className="w-4 h-4 mr-2" /> Create New RFQ
            </Button>
          </Link>
        </div>

        {/* Filters */}
        <Card className="border-slate-200">
          <CardContent className="pt-6">
            <div className="flex flex-col md:flex-row gap-4">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input
                  placeholder="Search RFQs..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                  data-testid="search-rfqs"
                />
              </div>
              <div className="flex gap-2 flex-wrap">
                {statuses.map(status => (
                  <Button
                    key={status}
                    variant={filterStatus === status ? "default" : "outline"}
                    size="sm"
                    onClick={() => setFilterStatus(status)}
                    className={filterStatus === status ? "bg-orange-600" : ""}
                    data-testid={`filter-${status}`}
                  >
                    {status === "all" ? "All" : status.replace("_", " ")}
                  </Button>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* RFQ List */}
        {filteredRFQs.length > 0 ? (
          <div className="grid gap-4">
            {filteredRFQs.map((rfq) => (
              <Link
                key={rfq.rfq_id}
                to={`/buyer/rfq/${rfq.rfq_id}`}
                className="block"
                data-testid={`rfq-card-${rfq.rfq_id}`}
              >
                <Card className="border-slate-200 hover:border-orange-300 hover:shadow-md transition-all cursor-pointer">
                  <CardContent className="p-6">
                    <div className="flex items-start justify-between">
                      <div className="flex items-start gap-4">
                        <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center">
                          <FileText className="w-6 h-6 text-orange-600" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <h3 className="font-semibold text-slate-900 text-lg">{rfq.title}</h3>
                            <RefNumber value={rfq.rfq_number} />
                          </div>
                          <div className="flex items-center gap-4 mt-2 text-sm text-slate-500">
                            <span className="flex items-center gap-1">
                              <Package className="w-4 h-4" /> {rfq.material_type}
                            </span>
                            <span>Qty: {rfq.quantity}</span>
                            <span>Tolerance: {rfq.tolerance ? `±${rfq.tolerance}mm` : "As per drawing"}</span>
                            <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                              rfq.supply_type === "buyer_material" 
                                ? "bg-blue-100 text-blue-700" 
                                : "bg-orange-100 text-orange-700"
                            }`}>
                              {rfq.supply_type === "buyer_material" ? "I Supply Material" : "Vendor Supplies"}
                            </span>
                          </div>
                          {rfq.description && (
                            <p className="text-sm text-slate-500 mt-2 line-clamp-2">{rfq.description}</p>
                          )}
                        </div>
                      </div>
                      <div className="text-right">
                        <span className={`status-badge ${getStatusBadge(rfq.status)}`}>
                          {rfq.status.replace("_", " ")}
                        </span>
                        <p className="text-xs text-slate-400 mt-2 flex items-center gap-1 justify-end">
                          <Calendar className="w-3 h-3" />
                          {new Date(rfq.created_at).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        ) : (
          <Card className="border-slate-200">
            <CardContent className="py-16 text-center">
              <FileText className="w-16 h-16 text-slate-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-slate-900 mb-2">No RFQs Found</h3>
              <p className="text-slate-500 mb-6">
                {searchTerm || filterStatus !== "all" 
                  ? "Try adjusting your search or filters"
                  : "Create your first RFQ to get started"}
              </p>
              <Link to="/buyer/rfq/new">
                <Button className="bg-orange-600 hover:bg-orange-700">
                  <Plus className="w-4 h-4 mr-2" /> Create New RFQ
                </Button>
              </Link>
            </CardContent>
          </Card>
        )}
      </div>
    </DashboardLayout>
  );
};

export default BuyerRFQList;
