import { useState, useEffect } from "react";
import { api } from "../App";
import { Button } from "./ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "./ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "./ui/dialog";
import { RadioGroup, RadioGroupItem } from "./ui/radio-group";
import { Label } from "./ui/label";
import { Textarea } from "./ui/textarea";
import { toast } from "sonner";
import { 
  ClipboardCheck, Shield, ShieldCheck, Loader2, CreditCard,
  CheckCircle2, Info, BadgeCheck, User
} from "lucide-react";

const INSPECTION_TYPES = {
  basic: {
    label: "Basic Inspection",
    description: "Platform-managed local inspector - Fast turnaround, cost-effective",
    icon: ClipboardCheck,
    color: "text-blue-600",
    bgColor: "bg-blue-50",
    borderColor: "border-blue-200"
  },
  certified: {
    label: "Certified Inspection",
    description: "External certified inspection agency - Highly trusted, premium quality",
    icon: ShieldCheck,
    color: "text-purple-600",
    bgColor: "bg-purple-50",
    borderColor: "border-purple-200"
  }
};

const InspectionRequestModal = ({ orderId, isOpen, onClose, onSuccess }) => {
  const [loading, setLoading] = useState(false);
  const [loadingPricing, setLoadingPricing] = useState(true);
  const [pricing, setPricing] = useState([]);
  const [selectedType, setSelectedType] = useState("basic");
  const [notes, setNotes] = useState("");
  const [step, setStep] = useState(1); // 1: Select type, 2: Confirm & Pay

  useEffect(() => {
    if (isOpen) {
      fetchPricing();
      setStep(1);
      setSelectedType("basic");
      setNotes("");
    }
  }, [isOpen]);

  const fetchPricing = async () => {
    setLoadingPricing(true);
    try {
      const res = await api.get("/inspection/pricing");
      setPricing(res.data.pricing || []);
    } catch (error) {
      console.error("Failed to fetch pricing:", error);
    } finally {
      setLoadingPricing(false);
    }
  };

  const getPriceForType = (type) => {
    const found = pricing.find(p => p.inspection_type === type);
    return found?.base_price || (type === "basic" ? 500 : 2000);
  };

  const handleRequestInspection = async () => {
    setLoading(true);
    try {
      const res = await api.post(`/orders/${orderId}/request-inspection`, {
        inspection_type: selectedType,
        buyer_notes: notes
      });
      
      if (res.data.success) {
        toast.success("Inspection requested successfully!");
        setStep(2);
        
        // Proceed to payment step
        const inspectionId = res.data.inspection_id;
        const fee = res.data.inspection_fee;
        
        // For MVP, show payment confirmation
        toast.info(`Please complete payment of ₹${fee} to proceed`);
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to request inspection");
    } finally {
      setLoading(false);
    }
  };

  const handlePayment = async () => {
    setLoading(true);
    try {
      // Get inspection ID from the order
      const orderRes = await api.get(`/orders/${orderId}/inspection`);
      const inspectionId = orderRes.data.inspection?.inspection_id;
      
      if (!inspectionId) {
        throw new Error("Inspection not found");
      }

      // Simulate payment (integrate with Stripe/Razorpay later)
      const res = await api.post(`/inspections/${inspectionId}/pay`, {
        payment_method: "simulated"
      });
      
      if (res.data.success) {
        toast.success("Payment successful! Inspector will be assigned shortly.");
        onSuccess?.();
        onClose();
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || "Payment failed");
    } finally {
      setLoading(false);
    }
  };

  const selectedTypeConfig = INSPECTION_TYPES[selectedType];
  const selectedPrice = getPriceForType(selectedType);

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-orange-600" />
            Request Inspection
          </DialogTitle>
        </DialogHeader>

        {step === 1 && (
          <div className="space-y-4 mt-4">
            {/* Info Banner */}
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
              <div className="flex items-start gap-2">
                <Info className="w-4 h-4 text-slate-500 mt-0.5" />
                <p className="text-sm text-slate-600">
                  Third-party inspection ensures quality verification before accepting delivery.
                  Choose the inspection type that fits your needs.
                </p>
              </div>
            </div>

            {/* Inspection Type Selection */}
            <div className="space-y-3">
              <Label className="text-sm font-medium">Select Inspection Type</Label>
              
              {loadingPricing ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-orange-600" />
                </div>
              ) : (
                <RadioGroup value={selectedType} onValueChange={setSelectedType} className="space-y-3">
                  {Object.entries(INSPECTION_TYPES).map(([type, config]) => {
                    const Icon = config.icon;
                    const price = getPriceForType(type);
                    const isSelected = selectedType === type;
                    
                    return (
                      <div
                        key={type}
                        className={`relative flex items-start p-4 rounded-lg border-2 cursor-pointer transition-all ${
                          isSelected 
                            ? `${config.borderColor} ${config.bgColor}` 
                            : 'border-slate-200 hover:border-slate-300'
                        }`}
                        onClick={() => setSelectedType(type)}
                        data-testid={`inspection-type-${type}`}
                      >
                        <RadioGroupItem value={type} id={type} className="mt-1" />
                        <div className="ml-3 flex-1">
                          <div className="flex items-center justify-between">
                            <Label htmlFor={type} className="font-medium cursor-pointer flex items-center gap-2">
                              <Icon className={`w-4 h-4 ${config.color}`} />
                              {config.label}
                            </Label>
                            <span className={`font-bold ${config.color}`}>
                              ₹{price.toLocaleString('en-IN')}
                            </span>
                          </div>
                          <p className="text-sm text-slate-500 mt-1">{config.description}</p>
                        </div>
                      </div>
                    );
                  })}
                </RadioGroup>
              )}
            </div>

            {/* Notes */}
            <div>
              <Label htmlFor="notes" className="text-sm font-medium">
                Instructions / Notes (Optional)
              </Label>
              <Textarea
                id="notes"
                placeholder="Any specific areas to inspect, special requirements..."
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                className="mt-1"
                rows={3}
                data-testid="inspection-notes"
              />
            </div>

            {/* Price Summary */}
            <div className={`p-4 rounded-lg ${selectedTypeConfig.bgColor} border ${selectedTypeConfig.borderColor}`}>
              <div className="flex items-center justify-between">
                <span className="font-medium text-slate-700">Inspection Fee</span>
                <span className={`text-xl font-bold ${selectedTypeConfig.color}`}>
                  ₹{selectedPrice.toLocaleString('en-IN')}
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-1">
                Payment required to proceed with inspection
              </p>
            </div>

            {/* Actions */}
            <div className="flex gap-3 pt-2">
              <Button variant="outline" onClick={onClose} className="flex-1">
                Cancel
              </Button>
              <Button 
                onClick={handleRequestInspection}
                disabled={loading}
                className="flex-1 bg-orange-600 hover:bg-orange-700"
                data-testid="confirm-inspection-request"
              >
                {loading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <>Request Inspection</>
                )}
              </Button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4 mt-4">
            {/* Success Message */}
            <div className="p-4 bg-green-50 rounded-lg border border-green-200 text-center">
              <CheckCircle2 className="w-10 h-10 text-green-600 mx-auto mb-2" />
              <h3 className="font-medium text-green-800">Inspection Requested!</h3>
              <p className="text-sm text-green-600 mt-1">
                Complete payment to assign an inspector
              </p>
            </div>

            {/* Payment Summary */}
            <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
              <div className="flex items-center justify-between mb-2">
                <span className="text-slate-600">Inspection Type</span>
                <span className="font-medium">{selectedTypeConfig.label}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-600">Amount Due</span>
                <span className="text-xl font-bold text-slate-900">
                  ₹{selectedPrice.toLocaleString('en-IN')}
                </span>
              </div>
            </div>

            {/* Payment Button */}
            <Button 
              onClick={handlePayment}
              disabled={loading}
              className="w-full bg-green-600 hover:bg-green-700"
              data-testid="pay-inspection-fee"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <>
                  <CreditCard className="w-4 h-4 mr-2" />
                  Pay ₹{selectedPrice.toLocaleString('en-IN')}
                </>
              )}
            </Button>

            <p className="text-xs text-slate-400 text-center">
              Secure payment powered by OEMLinker
            </p>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default InspectionRequestModal;
