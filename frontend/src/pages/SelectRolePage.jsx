import { useState } from "react";
import { api } from "../App";
import { toast } from "sonner";
import { Building2, ShoppingCart, Loader2 } from "lucide-react";

const SelectRolePage = () => {
  const [selecting, setSelecting] = useState(false);

  const handleSelectRole = async (role) => {
    setSelecting(true);
    try {
      await api.put("/auth/role", { role });
      toast.success(`Welcome! You're registered as a ${role}.`);
      
      if (role === "vendor") {
        window.location.href = "/vendor/dashboard";
      } else {
        window.location.href = "/buyer/dashboard";
      }
    } catch (err) {
      console.error("Role selection error:", err);
      toast.error(err.response?.data?.detail || "Failed to set role. Please try again.");
      setSelecting(false);
    }
  };

  return (
    <div data-testid="select-role-page" className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="max-w-lg w-full">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-slate-900 mb-2">Choose Your Role</h1>
          <p className="text-slate-500">How would you like to use OEMLinker?</p>
        </div>

        <div className="space-y-4">
          <button
            data-testid="select-role-buyer"
            onClick={() => handleSelectRole("buyer")}
            disabled={selecting}
            className="w-full bg-white border-2 border-slate-200 hover:border-orange-500 rounded-xl p-6 text-left transition-all group disabled:opacity-50"
          >
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center group-hover:bg-orange-200 transition-colors">
                <ShoppingCart className="w-6 h-6 text-orange-600" />
              </div>
              <div>
                <h3 className="font-semibold text-slate-900 text-lg">I'm a Buyer</h3>
                <p className="text-slate-500 text-sm mt-1">I need manufacturing services. I want to submit RFQs and get quotes from vendors.</p>
              </div>
            </div>
          </button>

          <button
            data-testid="select-role-vendor"
            onClick={() => handleSelectRole("vendor")}
            disabled={selecting}
            className="w-full bg-white border-2 border-slate-200 hover:border-orange-500 rounded-xl p-6 text-left transition-all group disabled:opacity-50"
          >
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center group-hover:bg-blue-200 transition-colors">
                <Building2 className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <h3 className="font-semibold text-slate-900 text-lg">I'm a Vendor</h3>
                <p className="text-slate-500 text-sm mt-1">I provide manufacturing services. I want to receive RFQs and submit quotes.</p>
              </div>
            </div>
          </button>
        </div>

        {selecting && (
          <div className="flex items-center justify-center mt-6 gap-2 text-slate-500">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Setting up your account...</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default SelectRolePage;
