import { useState } from "react";
import { api } from "../App";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Textarea } from "../components/ui/textarea";
import { Label } from "../components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { toast } from "sonner";
import { AlertTriangle, X } from "lucide-react";

const DISPUTE_TYPES = [
  { value: "quality_issue", label: "Quality Issue", icon: "🔍", description: "Product doesn't meet quality standards" },
  { value: "delivery_delay", label: "Delivery Delay", icon: "🕐", description: "Order not delivered on time" },
  { value: "wrong_specifications", label: "Wrong Specifications", icon: "📐", description: "Product doesn't match specifications" },
  { value: "payment_issue", label: "Payment Issue", icon: "💰", description: "Problems with payment processing" },
  { value: "communication", label: "Communication Problem", icon: "💬", description: "Lack of response or miscommunication" },
  { value: "damaged_goods", label: "Damaged Goods", icon: "📦", description: "Product arrived damaged" },
  { value: "incomplete_order", label: "Incomplete Order", icon: "❌", description: "Order is missing items" },
  { value: "other", label: "Other", icon: "❓", description: "Other issues not listed above" }
];

const RaiseDisputeForm = ({ orderId, onClose, onSuccess }) => {
  const [formData, setFormData] = useState({
    dispute_type: "",
    subject: "",
    description: "",
    expected_resolution: ""
  });
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.dispute_type || !formData.subject || !formData.description) {
      toast.error("Please fill in all required fields");
      return;
    }
    
    setSubmitting(true);
    try {
      const response = await api.post("/disputes", {
        order_id: orderId,
        dispute_type: formData.dispute_type,
        subject: formData.subject,
        description: formData.description,
        expected_resolution: formData.expected_resolution || null,
        evidence_urls: []
      });
      
      toast.success("Dispute created successfully");
      onSuccess?.(response.data.dispute);
    } catch (error) {
      const errorMsg = error.response?.data?.detail || "Failed to create dispute";
      toast.error(errorMsg);
    } finally {
      setSubmitting(false);
    }
  };

  const selectedType = DISPUTE_TYPES.find(t => t.value === formData.dispute_type);

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-slate-200 p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-red-100 rounded-lg flex items-center justify-center">
              <AlertTriangle className="w-5 h-5 text-red-600" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-900">Raise a Dispute</h2>
              <p className="text-sm text-slate-500">Order #{orderId?.slice(-12)}</p>
            </div>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="w-5 h-5" />
          </Button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          {/* Dispute Type */}
          <div>
            <Label className="text-sm font-medium">Dispute Type *</Label>
            <Select 
              value={formData.dispute_type}
              onValueChange={(value) => setFormData({ ...formData, dispute_type: value })}
            >
              <SelectTrigger className="mt-1" data-testid="dispute-type-select">
                <SelectValue placeholder="Select the type of issue" />
              </SelectTrigger>
              <SelectContent>
                {DISPUTE_TYPES.map((type) => (
                  <SelectItem key={type.value} value={type.value}>
                    <div className="flex items-center gap-2">
                      <span>{type.icon}</span>
                      <span>{type.label}</span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {selectedType && (
              <p className="text-xs text-slate-500 mt-1">{selectedType.description}</p>
            )}
          </div>

          {/* Subject */}
          <div>
            <Label className="text-sm font-medium">Subject *</Label>
            <Input
              placeholder="Brief summary of the issue"
              value={formData.subject}
              onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
              className="mt-1"
              maxLength={100}
              data-testid="dispute-subject-input"
            />
            <p className="text-xs text-slate-400 mt-1">{formData.subject.length}/100 characters</p>
          </div>

          {/* Description */}
          <div>
            <Label className="text-sm font-medium">Description *</Label>
            <Textarea
              placeholder="Provide detailed information about the issue, including any relevant dates, communications, or specifics..."
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="mt-1"
              rows={4}
              data-testid="dispute-description-input"
            />
          </div>

          {/* Expected Resolution */}
          <div>
            <Label className="text-sm font-medium">Expected Resolution (Optional)</Label>
            <Textarea
              placeholder="What outcome would resolve this issue for you? (e.g., refund, replacement, rework)"
              value={formData.expected_resolution}
              onChange={(e) => setFormData({ ...formData, expected_resolution: e.target.value })}
              className="mt-1"
              rows={2}
              data-testid="dispute-resolution-input"
            />
          </div>

          {/* Info Box */}
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
            <p className="text-sm text-amber-800">
              <strong>Note:</strong> Once submitted, your dispute will be reviewed by our team. 
              The other party will be notified and given a chance to respond. 
              Most disputes are resolved within 3-5 business days.
            </p>
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-2">
            <Button 
              type="button" 
              variant="outline" 
              onClick={onClose}
              className="flex-1"
            >
              Cancel
            </Button>
            <Button 
              type="submit" 
              disabled={submitting}
              className="flex-1 bg-red-600 hover:bg-red-700"
              data-testid="submit-dispute-btn"
            >
              {submitting ? "Submitting..." : "Submit Dispute"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default RaiseDisputeForm;
