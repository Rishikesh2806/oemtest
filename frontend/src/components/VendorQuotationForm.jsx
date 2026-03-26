import { useState, useEffect } from "react";
import { api } from "../App";
import { Button } from "./ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "./ui/card";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Textarea } from "./ui/textarea";
import { Switch } from "./ui/switch";
import { Checkbox } from "./ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { toast } from "sonner";
import { 
  DollarSign, Package, Plus, Trash2, Loader2, Calculator, 
  HelpCircle, CheckCircle2, Info, FileText, ChevronDown, ChevronUp,
  Image as ImageIcon, AlertTriangle, CheckSquare, Square
} from "lucide-react";

const VendorQuotationForm = ({ rfq, onSubmitSuccess, existingQuote = null }) => {
  const [loading, setLoading] = useState(false);
  const [loadingItems, setLoadingItems] = useState(false);
  const [items, setItems] = useState([]);
  const [isItemwiseMode, setIsItemwiseMode] = useState(false);
  const [expandedItems, setExpandedItems] = useState({});
  
  // Partial quoting - selected items
  const [selectedItems, setSelectedItems] = useState({});
  
  // Single item form state (for non-itemwise mode)
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
  const [paymentTermsNotes, setPaymentTermsNotes] = useState(existingQuote?.payment_terms_notes || "");

  // Item-wise quotation state
  const [itemQuotes, setItemQuotes] = useState({});

  useEffect(() => {
    if (rfq?.rfq_id) {
      fetchRFQItems();
    }
  }, [rfq?.rfq_id]);

  const fetchRFQItems = async () => {
    setLoadingItems(true);
    try {
      const res = await api.get(`/rfqs/${rfq.rfq_id}/items`);
      const fetchedItems = res.data.items || [];
      setItems(fetchedItems);
      
      // Initialize item quotes and selections
      const initialQuotes = {};
      const initialSelections = {};
      fetchedItems.forEach(item => {
        initialQuotes[item.item_id] = {
          material_provided_by_buyer: res.data.raw_material_provided || false,
          material_cost: "",
          labour_cost: "",
          additional_costs: [],
          remarks: ""
        };
        // Default: all items selected
        initialSelections[item.item_id] = true;
      });
      setItemQuotes(initialQuotes);
      setSelectedItems(initialSelections);
      
      // If multiple items, default to itemwise mode
      if (fetchedItems.length > 1) {
        setIsItemwiseMode(true);
        // Expand first item by default
        setExpandedItems({ [fetchedItems[0]?.item_id]: true });
      }
    } catch (error) {
      console.error("Failed to fetch RFQ items:", error);
    } finally {
      setLoadingItems(false);
    }
  };

  // Calculate totals for single item mode
  const materialCostNum = parseFloat(materialCost) || 0;
  const machiningCostNum = parseFloat(machiningCost) || 0;
  const additionalCostsTotal = additionalCosts.reduce((sum, item) => sum + (parseFloat(item.cost) || 0), 0);
  const totalCost = (materialProvidedByBuyer ? 0 : materialCostNum) + machiningCostNum + additionalCostsTotal;

  // Calculate grand total for item-wise mode (only selected items)
  const calculateItemTotal = (itemId) => {
    const quote = itemQuotes[itemId];
    if (!quote) return 0;
    const material = quote.material_provided_by_buyer ? 0 : (parseFloat(quote.material_cost) || 0);
    const labour = parseFloat(quote.labour_cost) || 0;
    const additional = quote.additional_costs.reduce((sum, item) => sum + (parseFloat(item.cost) || 0), 0);
    return material + labour + additional;
  };

  // Count selected items
  const selectedItemsCount = Object.values(selectedItems).filter(Boolean).length;
  const isPartialQuote = selectedItemsCount < items.length && selectedItemsCount > 0;

  const grandTotal = isItemwiseMode 
    ? Object.keys(itemQuotes)
        .filter(itemId => selectedItems[itemId])
        .reduce((sum, itemId) => sum + calculateItemTotal(itemId), 0)
    : totalCost;

  const toggleItemExpand = (itemId) => {
    setExpandedItems(prev => ({ ...prev, [itemId]: !prev[itemId] }));
  };

  const toggleItemSelection = (itemId) => {
    setSelectedItems(prev => ({ ...prev, [itemId]: !prev[itemId] }));
  };

  const selectAllItems = () => {
    const newSelections = {};
    items.forEach(item => { newSelections[item.item_id] = true; });
    setSelectedItems(newSelections);
  };

  const deselectAllItems = () => {
    const newSelections = {};
    items.forEach(item => { newSelections[item.item_id] = false; });
    setSelectedItems(newSelections);
  };

  const updateItemQuote = (itemId, field, value) => {
    setItemQuotes(prev => ({
      ...prev,
      [itemId]: { ...prev[itemId], [field]: value }
    }));
  };

  const addItemAdditionalCost = (itemId) => {
    setItemQuotes(prev => ({
      ...prev,
      [itemId]: {
        ...prev[itemId],
        additional_costs: [...(prev[itemId]?.additional_costs || []), { name: "", cost: "" }]
      }
    }));
  };

  const removeItemAdditionalCost = (itemId, index) => {
    setItemQuotes(prev => ({
      ...prev,
      [itemId]: {
        ...prev[itemId],
        additional_costs: prev[itemId]?.additional_costs.filter((_, i) => i !== index)
      }
    }));
  };

  const updateItemAdditionalCost = (itemId, index, field, value) => {
    setItemQuotes(prev => {
      const updated = [...(prev[itemId]?.additional_costs || [])];
      updated[index] = { ...updated[index], [field]: value };
      return {
        ...prev,
        [itemId]: { ...prev[itemId], additional_costs: updated }
      };
    });
  };

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
    if (isItemwiseMode) {
      // Check if at least one item is selected
      if (selectedItemsCount === 0) {
        toast.error("Please select at least one item to quote");
        return false;
      }
      
      // Validate only selected items
      for (const item of items) {
        if (!selectedItems[item.item_id]) continue; // Skip unselected items
        
        const quote = itemQuotes[item.item_id];
        if (!quote?.labour_cost || parseFloat(quote.labour_cost) <= 0) {
          toast.error(`Labour cost is required for item: ${item.title}`);
          return false;
        }
        if (!quote?.material_provided_by_buyer && (!quote?.material_cost || parseFloat(quote.material_cost) <= 0)) {
          toast.error(`Material cost is required for item: ${item.title}`);
          return false;
        }
      }
    } else {
      if (!machiningCost || parseFloat(machiningCost) <= 0) {
        toast.error("Machining cost is required and must be greater than 0");
        return false;
      }
      if (!materialProvidedByBuyer && (!materialCost || parseFloat(materialCost) <= 0)) {
        toast.error("Material cost is required when you are providing the material");
        return false;
      }
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
      if (isItemwiseMode) {
        // Item-wise quotation (supports partial)
        const itemsPayload = items
          .filter(item => selectedItems[item.item_id]) // Only include selected items
          .map(item => {
            const quote = itemQuotes[item.item_id];
            const additionalCostsObj = {};
            (quote?.additional_costs || []).forEach(cost => {
              if (cost.name && cost.cost) {
                additionalCostsObj[cost.name.toLowerCase().replace(/\s+/g, '_')] = parseFloat(cost.cost);
              }
            });

            return {
              item_id: item.item_id,
              drawing_id: item.drawing_id,
              title: item.title,
              material_provided_by_buyer: quote?.material_provided_by_buyer || false,
              material_cost: quote?.material_provided_by_buyer ? 0 : parseFloat(quote?.material_cost || 0),
              labour_cost: parseFloat(quote?.labour_cost || 0),
              additional_costs: additionalCostsObj,
              remarks: quote?.remarks || ""
            };
          });

        await api.post("/vendor/quotation/itemwise", {
          rfq_id: rfq.rfq_id,
          items: itemsPayload,
          lead_time_days: parseInt(leadTimeDays),
          notes: notes,
          cost_breakdown_remarks: costBreakdownRemarks,
          proposed_payment_terms: paymentTerms,
          payment_terms_notes: paymentTermsNotes
        });
      } else {
        // Single/flat quotation
        const additionalCostsObj = {};
        additionalCosts.forEach(item => {
          if (item.name && item.cost) {
            additionalCostsObj[item.name.toLowerCase().replace(/\s+/g, '_')] = parseFloat(item.cost);
          }
        });

        await api.post("/vendor/quotation", {
          rfq_id: rfq.rfq_id,
          material_provided_by_buyer: materialProvidedByBuyer,
          material_cost: materialProvidedByBuyer ? 0 : parseFloat(materialCost),
          machining_cost: parseFloat(machiningCost),
          additional_costs: additionalCostsObj,
          lead_time_days: parseInt(leadTimeDays),
          notes: notes,
          cost_breakdown_remarks: costBreakdownRemarks,
          proposed_payment_terms: paymentTerms,
          payment_terms_notes: paymentTermsNotes
        });
      }

      const quoteType = isPartialQuote ? "Partial quotation" : "Quotation";
      toast.success(`${quoteType} submitted successfully!`);
      if (onSubmitSuccess) {
        onSubmitSuccess();
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to submit quotation");
    } finally {
      setLoading(false);
    }
  };

  // Single item form (non-itemwise mode)
  const renderSingleItemForm = () => (
    <div className="space-y-4">
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
      </div>
    </div>
  );

  // Item-wise form (for multiple drawings) with partial selection
  const renderItemwiseForm = () => {
    // Determine quote status: none, partial, or full
    const noItemsSelected = selectedItemsCount === 0;
    const quoteStatus = noItemsSelected ? 'none' : (isPartialQuote ? 'partial' : 'full');
    
    return (
    <div className="space-y-4">
      {/* Partial Quote Notice */}
      {items.length > 1 && (
        <div className={`p-3 rounded-lg border flex items-center justify-between ${
          quoteStatus === 'none' 
            ? 'bg-red-50 border-red-200'
            : quoteStatus === 'partial'
              ? 'bg-amber-50 border-amber-200' 
              : 'bg-green-50 border-green-200'
        }`}>
          <div className="flex items-center gap-2">
            {quoteStatus === 'none' ? (
              <AlertTriangle className="w-4 h-4 text-red-600" />
            ) : quoteStatus === 'partial' ? (
              <AlertTriangle className="w-4 h-4 text-amber-600" />
            ) : (
              <CheckCircle2 className="w-4 h-4 text-green-600" />
            )}
            <span className={`text-sm font-medium ${
              quoteStatus === 'none' 
                ? 'text-red-800'
                : quoteStatus === 'partial' 
                  ? 'text-amber-800' 
                  : 'text-green-800'
            }`}>
              {quoteStatus === 'none' 
                ? 'No items selected - Please select at least one item to quote'
                : quoteStatus === 'partial'
                  ? `Partial Quote: ${selectedItemsCount} of ${items.length} items selected`
                  : `Full Quote: All ${items.length} items selected`
              }
            </span>
          </div>
          <div className="flex gap-2">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={selectAllItems}
              className="text-xs h-7"
              data-testid="select-all-items"
            >
              <CheckSquare className="w-3 h-3 mr-1" /> Select All
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={deselectAllItems}
              className="text-xs h-7"
              data-testid="deselect-all-items"
            >
              <Square className="w-3 h-3 mr-1" /> Deselect All
            </Button>
          </div>
        </div>
      )}

      {/* Items Header */}
      <div className="flex items-center justify-between">
        <h4 className="font-medium text-slate-700 flex items-center gap-2">
          <FileText className="w-4 h-4" /> Quote per Drawing/Item ({items.length} items)
        </h4>
        <span className="text-xs text-slate-500">Select items and expand to enter costs</span>
      </div>

      {/* Items List */}
      <div className="space-y-3">
        {items.map((item, idx) => {
          const quote = itemQuotes[item.item_id] || {};
          const isExpanded = expandedItems[item.item_id];
          const isSelected = selectedItems[item.item_id];
          const itemTotal = calculateItemTotal(item.item_id);

          return (
            <Card 
              key={item.item_id} 
              className={`border transition-all ${
                !isSelected 
                  ? 'border-slate-200 bg-slate-50 opacity-60' 
                  : isExpanded 
                    ? 'border-orange-300' 
                    : 'border-slate-200'
              }`}
              data-testid={`item-card-${item.item_id}`}
            >
              {/* Item Header */}
              <div className="p-4 flex items-center gap-3">
                {/* Selection Checkbox */}
                <Checkbox
                  checked={isSelected}
                  onCheckedChange={() => toggleItemSelection(item.item_id)}
                  data-testid={`select-item-${item.item_id}`}
                />

                {/* Item Info (Expandable) */}
                <div 
                  className="flex-1 cursor-pointer flex items-center justify-between"
                  onClick={() => isSelected && toggleItemExpand(item.item_id)}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-slate-100 rounded-lg flex items-center justify-center">
                      {item.drawing_url ? (
                        <ImageIcon className="w-5 h-5 text-slate-500" />
                      ) : (
                        <FileText className="w-5 h-5 text-slate-500" />
                      )}
                    </div>
                    <div>
                      <p className="font-medium text-slate-900">
                        Item {idx + 1}: {item.title || item.filename || `Drawing ${idx + 1}`}
                      </p>
                      <p className="text-xs text-slate-500">
                        {item.material_type && `Material: ${item.material_type}`}
                        {item.quantity && ` | Qty: ${item.quantity}`}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    {isSelected && itemTotal > 0 && (
                      <span className="text-sm font-medium text-green-700">
                        ₹{itemTotal.toLocaleString('en-IN')}
                      </span>
                    )}
                    {!isSelected && (
                      <span className="text-xs text-slate-400 italic">Not quoting</span>
                    )}
                    {isSelected && (
                      isExpanded ? (
                        <ChevronUp className="w-5 h-5 text-slate-400" />
                      ) : (
                        <ChevronDown className="w-5 h-5 text-slate-400" />
                      )
                    )}
                  </div>
                </div>
              </div>

              {/* Item Details (Expanded) - Only show if selected */}
              {isSelected && isExpanded && (
                <CardContent className="pt-0 border-t">
                  <div className="space-y-4 pt-4">
                    {/* Drawing Preview */}
                    {item.drawing_url && (
                      <div className="mb-4">
                        <a 
                          href={item.drawing_url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="text-sm text-orange-600 hover:underline flex items-center gap-1"
                        >
                          <ImageIcon className="w-4 h-4" /> View Drawing
                        </a>
                      </div>
                    )}

                    {/* Material Toggle */}
                    <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                      <div className="flex items-center gap-2">
                        <Package className="w-4 h-4 text-slate-600" />
                        <span className="text-sm">Buyer provides material for this item</span>
                      </div>
                      <Switch
                        checked={quote.material_provided_by_buyer || false}
                        onCheckedChange={(val) => updateItemQuote(item.item_id, 'material_provided_by_buyer', val)}
                        data-testid={`material-toggle-${item.item_id}`}
                      />
                    </div>

                    {/* Material Cost */}
                    {!quote.material_provided_by_buyer && (
                      <div>
                        <Label className="text-xs">Material Cost (₹) *</Label>
                        <Input
                          type="number"
                          placeholder="e.g., 5000"
                          value={quote.material_cost || ""}
                          onChange={(e) => updateItemQuote(item.item_id, 'material_cost', e.target.value)}
                          className="mt-1"
                          data-testid={`material-cost-${item.item_id}`}
                        />
                      </div>
                    )}

                    {/* Labour Cost */}
                    <div>
                      <Label className="text-xs">Labour / Machining Cost (₹) *</Label>
                      <Input
                        type="number"
                        placeholder="e.g., 3000"
                        value={quote.labour_cost || ""}
                        onChange={(e) => updateItemQuote(item.item_id, 'labour_cost', e.target.value)}
                        className="mt-1"
                        data-testid={`labour-cost-${item.item_id}`}
                      />
                    </div>

                    {/* Additional Costs */}
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <Label className="text-xs">Additional Costs</Label>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => addItemAdditionalCost(item.item_id)}
                          className="h-6 text-xs"
                        >
                          <Plus className="w-3 h-3 mr-1" /> Add
                        </Button>
                      </div>
                      {(quote.additional_costs || []).map((cost, costIdx) => (
                        <div key={costIdx} className="flex gap-2 items-center mb-2">
                          <Input
                            placeholder="e.g., Heat Treatment"
                            value={cost.name}
                            onChange={(e) => updateItemAdditionalCost(item.item_id, costIdx, 'name', e.target.value)}
                            className="flex-1 h-8 text-sm"
                          />
                          <Input
                            type="number"
                            placeholder="₹"
                            value={cost.cost}
                            onChange={(e) => updateItemAdditionalCost(item.item_id, costIdx, 'cost', e.target.value)}
                            className="w-24 h-8 text-sm"
                          />
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() => removeItemAdditionalCost(item.item_id, costIdx)}
                            className="h-8 text-red-500"
                          >
                            <Trash2 className="w-3 h-3" />
                          </Button>
                        </div>
                      ))}
                    </div>

                    {/* Item Remarks */}
                    <div>
                      <Label className="text-xs">Remarks for this item</Label>
                      <Textarea
                        placeholder="Any specific notes for this drawing..."
                        value={quote.remarks || ""}
                        onChange={(e) => updateItemQuote(item.item_id, 'remarks', e.target.value)}
                        className="mt-1"
                        rows={2}
                      />
                    </div>

                    {/* Item Total */}
                    <div className="p-3 bg-green-50 rounded-lg flex justify-between items-center">
                      <span className="text-sm font-medium text-green-700">Item Total</span>
                      <span className="text-lg font-bold text-green-700">
                        ₹{itemTotal.toLocaleString('en-IN')}
                      </span>
                    </div>
                  </div>
                </CardContent>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
  };

  if (loadingItems) {
    return (
      <Card className="border-slate-200">
        <CardContent className="py-12 flex items-center justify-center">
          <Loader2 className="w-6 h-6 animate-spin text-orange-600" />
          <span className="ml-2 text-slate-500">Loading RFQ items...</span>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-slate-200">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <DollarSign className="w-5 h-5 text-orange-600" />
          Submit Quotation
        </CardTitle>
        <CardDescription>
          Provide detailed cost breakdown for: <span className="font-medium">{rfq?.title}</span>
          {items.length > 1 && (
            <span className="ml-2 text-orange-600 font-medium">({items.length} items)</span>
          )}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Mode Toggle (only if multiple items) */}
          {items.length > 1 && (
            <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg border border-blue-200">
              <div className="flex items-center gap-2">
                <Info className="w-4 h-4 text-blue-600" />
                <span className="text-sm text-blue-800">
                  This RFQ has {items.length} drawings. You can quote all or selected items.
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-blue-600">Item-wise</span>
                <Switch
                  checked={isItemwiseMode}
                  onCheckedChange={setIsItemwiseMode}
                  data-testid="itemwise-toggle"
                />
              </div>
            </div>
          )}

          {/* Form Content */}
          {isItemwiseMode ? renderItemwiseForm() : renderSingleItemForm()}

          {/* Grand Total Display */}
          <div className={`p-4 rounded-lg border ${
            isPartialQuote 
              ? 'bg-amber-50 border-amber-200' 
              : 'bg-green-50 border-green-200'
          }`}>
            <div className="flex justify-between items-center">
              <div>
                <span className={`font-medium ${isPartialQuote ? 'text-amber-700' : 'text-green-700'}`}>
                  {isItemwiseMode 
                    ? isPartialQuote 
                      ? `Partial Total (${selectedItemsCount}/${items.length} items)` 
                      : `Grand Total (All ${items.length} Items)`
                    : 'Total Cost'
                  }
                </span>
                {isPartialQuote && (
                  <p className="text-xs text-amber-600 mt-1">
                    This is a partial quote. Buyer may receive quotes from other vendors for remaining items.
                  </p>
                )}
              </div>
              <span 
                className={`text-2xl font-bold ${isPartialQuote ? 'text-amber-700' : 'text-green-700'}`} 
                data-testid="total-cost"
              >
                ₹{grandTotal.toLocaleString('en-IN')}
              </span>
            </div>
            {!isItemwiseMode && (
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
            )}
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
              <SelectTrigger className="mt-1" data-testid="payment-terms-select">
                <SelectValue placeholder="Select payment terms" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="net_30">Net 30 Days</SelectItem>
                <SelectItem value="net_45">Net 45 Days</SelectItem>
                <SelectItem value="net_60">Net 60 Days</SelectItem>
                <SelectItem value="50_advance_50_delivery">50% Advance, 50% on Delivery</SelectItem>
                <SelectItem value="100_advance">100% Advance</SelectItem>
                <SelectItem value="against_delivery">Payment Against Delivery</SelectItem>
                <SelectItem value="milestone_based">Milestone-Based Payment</SelectItem>
                <SelectItem value="letter_of_credit">Letter of Credit (LC)</SelectItem>
                <SelectItem value="custom">Custom Terms</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Payment Terms Notes - shown for milestone/custom */}
          {(paymentTerms === "milestone_based" || paymentTerms === "custom") && (
            <div>
              <Label htmlFor="paymentTermsNotes">
                {paymentTerms === "milestone_based" ? "Milestone Details" : "Custom Terms Details"}
              </Label>
              <Textarea
                id="paymentTermsNotes"
                placeholder={paymentTerms === "milestone_based" 
                  ? "e.g., 50% advance, 50% after inspection" 
                  : "Describe your custom payment terms..."}
                value={paymentTermsNotes}
                onChange={(e) => setPaymentTermsNotes(e.target.value)}
                className="mt-1"
                rows={2}
                data-testid="payment-terms-notes-input"
              />
              <p className="text-xs text-slate-400 mt-1">
                {paymentTerms === "milestone_based" 
                  ? "Specify percentages and stages (e.g., 30% advance, 40% after production, 30% after inspection)"
                  : "Describe the payment schedule, due dates, and conditions"}
              </p>
            </div>
          )}

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
            className={`w-full ${isPartialQuote ? 'bg-amber-600 hover:bg-amber-700' : 'bg-orange-600 hover:bg-orange-700'}`}
            disabled={loading || (isItemwiseMode && selectedItemsCount === 0)}
            data-testid="submit-quotation-btn"
          >
            {loading ? (
              <><Loader2 className="w-4 h-4 animate-spin mr-2" /> Submitting...</>
            ) : (
              <>
                <CheckCircle2 className="w-4 h-4 mr-2" /> 
                Submit {isPartialQuote ? 'Partial ' : ''}{isItemwiseMode ? 'Item-wise ' : ''}Quotation
              </>
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
};

export default VendorQuotationForm;
