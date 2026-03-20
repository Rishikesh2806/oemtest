import { useState } from "react";
import { api } from "../App";
import { Button } from "./ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "./ui/card";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Textarea } from "./ui/textarea";
import { Switch } from "./ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { toast } from "sonner";
import { 
  DollarSign, Package, Plus, Trash2, Loader2, Calculator, 
  HelpCircle, CheckCircle2, Info
} from "lucide-react";

const VendorQuotationForm = ({ rfq, onSubmitSuccess, existingQuote = null }) => {
  const [loading, setLoading] = useState(false);
  const [materialProvidedByBuyer, setMaterialProvidedByBuyer] = useState(
    existingQuote?.material_provided_by_buyer || rfq?.raw_material_provided || false
  );
  const [materialCost, setMaterialCost] = useState(existingQuote?.material_cost || "");
  const [machiningCost, setMachiningCost] = useState(existingQuote?.machining_cost || "");
  const [additionalCosts, setAdditionalCosts] = useState(
    existingQuote?.additional_costs ? 
      Object.entries(existingQuote.additional_costs).map(([name, cost]) => ({ name, cost: cost.toString() })) :
      []
  );
  const [leadTimeDays, setLeadTimeDays] = useState(existingQuote?.lead_time_days || "");
  const [notes, setNotes] = useState(existingQuote?.notes || "");
  const [costBreakdownRemarks, setCostBreakdownRemarks] = useState(existingQuote?.cost_breakdown_remarks || "");
  const [paymentTerms, setPaymentTerms] = useState(existingQuote?.proposed_payment_terms || "net_30");

  // Calculate totals
  const materialCostNum = parseFloat(materialCost) || 0;
  const machiningCostNum = parseFloat(machiningCost) || 0;
  const additionalCostsTotal = additionalCosts.reduce((sum, item) => sum + (parseFloat(item.cost) || 0), 0);
  const totalCost = (materialProvidedByBuyer ? 0 : materialCostNum) + machiningCostNum + additionalCostsTotal;

  const addAdditionalCost = () => {
    setAdditionalCosts([...additionalCosts, { name: "", cost: "" }]);
  };

  const removeAdditionalCost = (index) => {
    setAdditionalCosts(additionalCosts.filter((_, i) => i !== index));
  };

  const updateAdditionalCost = (index, field, value) => {
    const updated = [...additionalCosts];
    updated[index][field] = value;
    setAdditionalCosts(updated);
  };

  const validateForm = () => {
    if (!machiningCost || parseFloat(machiningCost) <= 0) {
      toast.error("Machining cost is required and must be greater than 0");
      return false;
    }
    if (!materialProvidedByBuyer && (!materialCost || parseFloat(materialCost) <= 0)) {
      toast.error("Material cost is required when you are providing the material");
      return false;
    }
    if (!leadTimeDays || parseInt(leadTimeDays) <= 0) {
      toast.error("Lead time is required");
      return false;
    }
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validateForm()) return;

    setLoading(true);
    try {
      const additionalCostsObj = {};
      additionalCosts.forEach(item => {
        if (item.name && item.cost) {
          additionalCostsObj[item.name.toLowerCase().replace(/\s+/g, '_')] = parseFloat(item.cost);
        }
      });

      const payload = {
        rfq_id: rfq.rfq_id,
        material_provided_by_buyer: materialProvidedByBuyer,
        material_cost: materialProvidedByBuyer ? 0 : parseFloat(materialCost),
        machining_cost: parseFloat(machiningCost),
        additional_costs: additionalCostsObj,
        lead_time_days: parseInt(leadTimeDays),
        notes: notes,
        cost_breakdown_remarks: costBreakdownRemarks,
        proposed_payment_terms: paymentTerms
      };

      await api.post("/vendor/quotation", payload);
      toast.success("Quotation submitted successfully!");
      if (onSubmitSuccess) {
        onSubmitSuccess();
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to submit quotation");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="border-slate-200">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <DollarSign className="w-5 h-5 text-orange-600" />
          Submit Quotation
        </CardTitle>
        <CardDescription>
          Provide detailed cost breakdown for: <span className="font-medium">{rfq?.title}</span>
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* RFQ Summary */}
          <div className="p-4 bg-slate-50 rounded-lg">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <p className="text-slate-500">Material</p>
                <p className="font-medium">{rfq?.material_type || "N/A"}</p>
              </div>
              <div>
                <p className="text-slate-500">Quantity</p>
                <p className="font-medium">{rfq?.quantity || "N/A"}</p>
              </div>
              <div>
                <p className="text-slate-500">Tolerance</p>
                <p className="font-medium">{rfq?.tolerance ? `${rfq.tolerance} mm` : "N/A"}</p>
              </div>
              <div>
                <p className="text-slate-500">Process</p>
                <p className="font-medium capitalize">{rfq?.process_detected || "Machining"}</p>
              </div>
            </div>
          </div>

          {/* Material Supply Toggle */}
          <div className="flex items-center justify-between p-4 bg-orange-50 rounded-lg border border-orange-200">
            <div className="flex items-center gap-3">
              <Package className="w-5 h-5 text-orange-600" />
              <div>
                <p className="font-medium text-slate-900">Buyer provides raw material</p>
                <p className="text-sm text-slate-500">Toggle ON if buyer will supply the raw material</p>
              </div>
            </div>
            <Switch
              checked={materialProvidedByBuyer}
              onCheckedChange={setMaterialProvidedByBuyer}
              data-testid="material-toggle"
            />
          </div>

          {/* Cost Breakdown */}
          <div className="space-y-4">
            <h4 className="font-medium text-slate-700 flex items-center gap-2">
              <Calculator className="w-4 h-4" /> Cost Breakdown
            </h4>

            {/* Material Cost */}
            {!materialProvidedByBuyer && (
              <div>
                <Label htmlFor="materialCost" className="flex items-center gap-1">
                  Material Cost (₹) <span className="text-red-500">*</span>
                  <HelpCircle className="w-3 h-3 text-slate-400" />
                </Label>
                <Input
                  id="materialCost"
                  type="number"
                  placeholder="e.g., 15000"
                  value={materialCost}
                  onChange={(e) => setMaterialCost(e.target.value)}
                  className="mt-1"
                  required={!materialProvidedByBuyer}
                  data-testid="material-cost-input"
                />
                <p className="text-xs text-slate-500 mt-1">Cost of raw material if you're providing it</p>
              </div>
            )}

            {/* Machining Cost */}
            <div>
              <Label htmlFor="machiningCost" className="flex items-center gap-1">
                Machining / Labor Cost (₹) <span className="text-red-500">*</span>
              </Label>
              <Input
                id="machiningCost"
                type="number"
                placeholder="e.g., 8500"
                value={machiningCost}
                onChange={(e) => setMachiningCost(e.target.value)}
                className="mt-1"
                required
                data-testid="machining-cost-input"
              />
              <p className="text-xs text-slate-500 mt-1">Cost of machining, labor, and manufacturing</p>
            </div>

            {/* Additional Costs */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <Label>Additional Costs (Optional)</Label>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={addAdditionalCost}
                  data-testid="add-additional-cost"
                >
                  <Plus className="w-4 h-4 mr-1" /> Add Cost
                </Button>
              </div>
              
              {additionalCosts.length > 0 ? (
                <div className="space-y-2">
                  {additionalCosts.map((item, index) => (
                    <div key={index} className="flex gap-2 items-center">
                      <Input
                        placeholder="e.g., Heat Treatment"
                        value={item.name}
                        onChange={(e) => updateAdditionalCost(index, 'name', e.target.value)}
                        className="flex-1"
                      />
                      <Input
                        type="number"
                        placeholder="Cost (₹)"
                        value={item.cost}
                        onChange={(e) => updateAdditionalCost(index, 'cost', e.target.value)}
                        className="w-32"
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => removeAdditionalCost(index)}
                        className="text-red-500 hover:bg-red-50"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-400 p-3 bg-slate-50 rounded">
                  Add heat treatment, surface finishing, or other additional costs
                </p>
              )}
            </div>

            {/* Total Display */}
            <div className="p-4 bg-green-50 rounded-lg border border-green-200">
              <div className="flex justify-between items-center">
                <span className="font-medium text-green-700">Total Cost</span>
                <span className="text-2xl font-bold text-green-700" data-testid="total-cost">
                  ₹{totalCost.toLocaleString('en-IN')}
                </span>
              </div>
              <div className="text-xs text-green-600 mt-2 space-y-1">
                {!materialProvidedByBuyer && materialCostNum > 0 && (
                  <p>Material: ₹{materialCostNum.toLocaleString('en-IN')}</p>
                )}
                {materialProvidedByBuyer && (
                  <p className="italic">Material provided by buyer</p>
                )}
                {machiningCostNum > 0 && (
                  <p>Machining: ₹{machiningCostNum.toLocaleString('en-IN')}</p>
                )}
                {additionalCostsTotal > 0 && (
                  <p>Additional: ₹{additionalCostsTotal.toLocaleString('en-IN')}</p>
                )}
              </div>
            </div>
          </div>

          {/* Lead Time */}
          <div>
            <Label htmlFor="leadTime" className="flex items-center gap-1">
              Lead Time (days) <span className="text-red-500">*</span>
            </Label>
            <Input
              id="leadTime"
              type="number"
              placeholder="e.g., 14"
              value={leadTimeDays}
              onChange={(e) => setLeadTimeDays(e.target.value)}
              className="mt-1"
              required
              min="1"
              data-testid="lead-time-input"
            />
          </div>

          {/* Payment Terms */}
          <div>
            <Label htmlFor="paymentTerms">Payment Terms</Label>
            <Select value={paymentTerms} onValueChange={setPaymentTerms}>
              <SelectTrigger className="mt-1">
                <SelectValue placeholder="Select payment terms" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="advance_100">100% Advance</SelectItem>
                <SelectItem value="advance_50">50% Advance, 50% on Delivery</SelectItem>
                <SelectItem value="net_15">Net 15 days</SelectItem>
                <SelectItem value="net_30">Net 30 days</SelectItem>
                <SelectItem value="cod">Cash on Delivery</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Cost Breakdown Remarks */}
          <div>
            <Label htmlFor="costRemarks">Cost Breakdown Remarks</Label>
            <Textarea
              id="costRemarks"
              placeholder="Explain the cost breakdown, material specifications, machining processes..."
              value={costBreakdownRemarks}
              onChange={(e) => setCostBreakdownRemarks(e.target.value)}
              className="mt-1"
              rows={3}
              data-testid="cost-remarks-input"
            />
          </div>

          {/* Additional Notes */}
          <div>
            <Label htmlFor="notes">Additional Notes</Label>
            <Textarea
              id="notes"
              placeholder="Any additional information about your quotation..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="mt-1"
              rows={2}
            />
          </div>

          {/* Submit Button */}
          <Button 
            type="submit" 
            className="w-full bg-orange-600 hover:bg-orange-700"
            disabled={loading}
            data-testid="submit-quotation-btn"
          >
            {loading ? (
              <><Loader2 className="w-4 h-4 animate-spin mr-2" /> Submitting...</>
            ) : (
              <><CheckCircle2 className="w-4 h-4 mr-2" /> Submit Quotation</>
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
};

export default VendorQuotationForm;
