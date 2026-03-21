import { useState, useEffect } from "react";
import { api } from "../App";
import { Button } from "./ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "./ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { toast } from "sonner";
import { 
  DollarSign, Building2, Clock, CheckCircle2, ArrowUpDown, 
  TrendingUp, Star, Loader2, Info, Package, FileText,
  ChevronDown, ChevronUp, Layers, AlertTriangle
} from "lucide-react";

const QuotationComparison = ({ rfqId, isAdmin = false, onQuoteSelect }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sortBy, setSortBy] = useState("total_cost");
  const [selectedQuote, setSelectedQuote] = useState(null);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [expandedItemwise, setExpandedItemwise] = useState({});

  useEffect(() => {
    if (rfqId) {
      fetchQuotations();
    }
  }, [rfqId]);

  const fetchQuotations = async () => {
    setLoading(true);
    try {
      const res = await api.get(`/rfq/${rfqId}/quotations`);
      setData(res.data);
    } catch (error) {
      toast.error("Failed to load quotations");
    } finally {
      setLoading(false);
    }
  };

  const sortedQuotations = data?.quotations ? [...data.quotations].sort((a, b) => {
    if (sortBy === "total_cost") return a.total_cost - b.total_cost;
    if (sortBy === "machining_cost") return a.machining_cost - b.machining_cost;
    if (sortBy === "lead_time") return a.lead_time_days - b.lead_time_days;
    if (sortBy === "rating") return (b.vendor_rating || 0) - (a.vendor_rating || 0);
    return 0;
  }) : [];

  const openDetails = (quote) => {
    setSelectedQuote(quote);
    setDetailsOpen(true);
  };

  const handleSelectQuote = async (quoteId) => {
    if (onQuoteSelect) {
      onQuoteSelect(quoteId);
    }
  };

  const toggleItemwiseExpand = (quoteId) => {
    setExpandedItemwise(prev => ({ ...prev, [quoteId]: !prev[quoteId] }));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-orange-600" />
      </div>
    );
  }

  if (!data || !data.quotations || data.quotations.length === 0) {
    return (
      <Card className="border-slate-200">
        <CardContent className="py-12 text-center">
          <DollarSign className="w-12 h-12 text-slate-300 mx-auto mb-4" />
          <p className="text-slate-500">No quotations received yet</p>
          <p className="text-sm text-slate-400 mt-2">
            Vendors will submit their quotations soon
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="border-slate-200">
          <CardContent className="pt-4 pb-4">
            <p className="text-xs text-slate-500 uppercase mb-1">Total Quotes</p>
            <p className="text-2xl font-bold text-slate-900">{data.total_quotes}</p>
          </CardContent>
        </Card>
        <Card className="border-green-200 bg-green-50">
          <CardContent className="pt-4 pb-4">
            <p className="text-xs text-green-600 uppercase mb-1">Lowest Total</p>
            <p className="text-2xl font-bold text-green-700">
              ₹{data.comparison_summary.lowest_total_cost?.toLocaleString('en-IN')}
            </p>
          </CardContent>
        </Card>
        <Card className="border-blue-200 bg-blue-50">
          <CardContent className="pt-4 pb-4">
            <p className="text-xs text-blue-600 uppercase mb-1">Lowest Labour</p>
            <p className="text-2xl font-bold text-blue-700">
              ₹{data.comparison_summary.lowest_machining_cost?.toLocaleString('en-IN')}
            </p>
          </CardContent>
        </Card>
        <Card className="border-slate-200">
          <CardContent className="pt-4 pb-4">
            <p className="text-xs text-slate-500 uppercase mb-1">Average Cost</p>
            <p className="text-2xl font-bold text-slate-900">
              ₹{data.comparison_summary.average_total_cost?.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Sort Controls */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2 text-sm text-slate-500 flex-wrap">
          <span>
            {data.comparison_summary.quotes_with_material} quotes include material, {data.comparison_summary.quotes_without_material} buyer-supplied
          </span>
          {data.has_itemwise_quotes && (
            <span className="px-2 py-0.5 bg-purple-100 text-purple-700 rounded-full text-xs font-medium flex items-center gap-1">
              <Layers className="w-3 h-3" />
              {data.comparison_summary.itemwise_quotes} item-wise
            </span>
          )}
          {data.comparison_summary.partial_quotes > 0 && (
            <span className="px-2 py-0.5 bg-amber-100 text-amber-700 rounded-full text-xs font-medium flex items-center gap-1">
              <AlertTriangle className="w-3 h-3" />
              {data.comparison_summary.partial_quotes} partial
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <ArrowUpDown className="w-4 h-4 text-slate-400" />
          <Select value={sortBy} onValueChange={setSortBy}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Sort by" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="total_cost">Total Cost (Low to High)</SelectItem>
              <SelectItem value="machining_cost">Labour Cost</SelectItem>
              <SelectItem value="lead_time">Lead Time</SelectItem>
              <SelectItem value="rating">Vendor Rating</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Quotation Comparison Table */}
      <Card className="border-slate-200">
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full" data-testid="quotation-comparison-table">
              <thead className="bg-slate-50 border-b">
                <tr>
                  <th className="text-left p-4 text-xs font-bold uppercase text-slate-500">Vendor</th>
                  <th className="text-right p-4 text-xs font-bold uppercase text-slate-500">Material</th>
                  <th className="text-right p-4 text-xs font-bold uppercase text-slate-500">Labour</th>
                  <th className="text-right p-4 text-xs font-bold uppercase text-slate-500">Additional</th>
                  <th className="text-right p-4 text-xs font-bold uppercase text-slate-500">Total</th>
                  <th className="text-center p-4 text-xs font-bold uppercase text-slate-500">Lead Time</th>
                  <th className="text-center p-4 text-xs font-bold uppercase text-slate-500">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {sortedQuotations.map((quote, index) => {
                  const isLowest = quote.total_cost === data.comparison_summary.lowest_total_cost;
                  const additionalTotal = quote.additional_costs_total || 
                    (quote.additional_costs ? Object.values(quote.additional_costs).reduce((a, b) => a + b, 0) : 0);
                  const isExpanded = expandedItemwise[quote.quote_id];
                  
                  return (
                    <>
                      <tr 
                        key={quote.quote_id} 
                        className={`hover:bg-slate-50 ${isLowest ? 'bg-green-50' : ''} ${quote.is_partial ? 'bg-amber-50/50' : ''}`}
                        data-testid={`quote-row-${quote.quote_id}`}
                      >
                        <td className="p-4">
                          <div className="flex items-center gap-3">
                            <div>
                              <div className="flex items-center gap-2 flex-wrap">
                                {isLowest && (
                                  <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded-full font-medium">
                                    Best Price
                                  </span>
                                )}
                                {quote.is_partial && (
                                  <span className="px-2 py-0.5 bg-amber-100 text-amber-700 text-xs rounded-full font-medium flex items-center gap-1">
                                    <AlertTriangle className="w-3 h-3" />
                                    Partial ({quote.quoted_items_count}/{quote.total_rfq_items})
                                  </span>
                                )}
                                {quote.is_itemwise && !quote.is_partial && (
                                  <span className="px-2 py-0.5 bg-purple-100 text-purple-700 text-xs rounded-full font-medium flex items-center gap-1">
                                    <Layers className="w-3 h-3" />
                                    {quote.items_count} items
                                  </span>
                                )}
                              </div>
                              <p className="font-medium text-slate-900 mt-1">{quote.vendor_name}</p>
                              <p className="text-xs text-slate-500">{quote.vendor_location}</p>
                              {quote.vendor_rating > 0 && (
                                <div className="flex items-center gap-1 mt-1">
                                  <Star className="w-3 h-3 text-yellow-500 fill-yellow-500" />
                                  <span className="text-xs text-slate-600">{quote.vendor_rating.toFixed(1)}</span>
                                </div>
                              )}
                            </div>
                          </div>
                        </td>
                        <td className="p-4 text-right">
                          {quote.material_provided_by_buyer ? (
                            <span className="text-xs text-slate-400 italic">Buyer provides</span>
                          ) : (
                            <span className="font-medium text-slate-900">
                              ₹{quote.material_cost?.toLocaleString('en-IN')}
                            </span>
                          )}
                        </td>
                        <td className="p-4 text-right">
                          <span className="font-medium text-slate-900">
                            ₹{(quote.labour_cost || quote.machining_cost)?.toLocaleString('en-IN')}
                          </span>
                        </td>
                        <td className="p-4 text-right">
                          {additionalTotal > 0 ? (
                            <button 
                              className="text-orange-600 hover:underline text-sm"
                              onClick={() => openDetails(quote)}
                            >
                              ₹{additionalTotal.toLocaleString('en-IN')}
                            </button>
                          ) : (
                            <span className="text-slate-400">-</span>
                          )}
                        </td>
                        <td className="p-4 text-right">
                          <span className={`text-lg font-bold ${isLowest ? 'text-green-700' : 'text-slate-900'}`}>
                            ₹{quote.total_cost?.toLocaleString('en-IN')}
                          </span>
                        </td>
                        <td className="p-4 text-center">
                          <div className="flex items-center justify-center gap-1">
                            <Clock className="w-4 h-4 text-slate-400" />
                            <span className="text-slate-700">{quote.lead_time_days} days</span>
                          </div>
                        </td>
                        <td className="p-4 text-center">
                          <div className="flex items-center justify-center gap-2">
                            {quote.is_itemwise && (
                              <Button 
                                variant="ghost" 
                                size="sm"
                                onClick={() => toggleItemwiseExpand(quote.quote_id)}
                                data-testid={`expand-items-${quote.quote_id}`}
                              >
                                {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                              </Button>
                            )}
                            <Button 
                              variant="ghost" 
                              size="sm"
                              onClick={() => openDetails(quote)}
                              data-testid={`view-quote-${quote.quote_id}`}
                            >
                              <Info className="w-4 h-4" />
                            </Button>
                            {!quote.is_selected && (
                              <Button 
                                size="sm"
                                className="bg-orange-600 hover:bg-orange-700"
                                onClick={() => handleSelectQuote(quote.quote_id)}
                                data-testid={`select-quote-${quote.quote_id}`}
                              >
                                <CheckCircle2 className="w-4 h-4 mr-1" /> Select
                              </Button>
                            )}
                            {quote.is_selected && (
                              <span className="px-3 py-1 bg-green-100 text-green-700 text-sm rounded-full font-medium">
                                Selected
                              </span>
                            )}
                          </div>
                        </td>
                      </tr>

                      {/* Item-wise breakdown row */}
                      {quote.is_itemwise && isExpanded && (
                        <tr key={`${quote.quote_id}-items`} className="bg-slate-50">
                          <td colSpan={7} className="p-4">
                            <div className="space-y-2">
                              <h5 className="text-sm font-medium text-slate-700 flex items-center gap-2">
                                <FileText className="w-4 h-4" /> Item-wise Cost Breakdown
                              </h5>
                              <div className="overflow-x-auto">
                                <table className="w-full text-sm">
                                  <thead className="bg-slate-100">
                                    <tr>
                                      <th className="text-left p-2 text-xs font-medium text-slate-500">#</th>
                                      <th className="text-left p-2 text-xs font-medium text-slate-500">Item</th>
                                      <th className="text-right p-2 text-xs font-medium text-slate-500">Material</th>
                                      <th className="text-right p-2 text-xs font-medium text-slate-500">Labour</th>
                                      <th className="text-right p-2 text-xs font-medium text-slate-500">Additional</th>
                                      <th className="text-right p-2 text-xs font-medium text-slate-500">Total</th>
                                    </tr>
                                  </thead>
                                  <tbody className="divide-y divide-slate-200">
                                    {(quote.items || []).map((item, idx) => {
                                      const itemAdditional = item.additional_costs ? 
                                        Object.values(item.additional_costs).reduce((a, b) => a + b, 0) : 0;
                                      return (
                                        <tr key={item.item_id || idx} className="hover:bg-slate-100">
                                          <td className="p-2 text-slate-500">{idx + 1}</td>
                                          <td className="p-2">
                                            <span className="font-medium text-slate-800">
                                              {item.title || `Item ${idx + 1}`}
                                            </span>
                                            {item.remarks && (
                                              <p className="text-xs text-slate-500 truncate max-w-[200px]">
                                                {item.remarks}
                                              </p>
                                            )}
                                          </td>
                                          <td className="p-2 text-right">
                                            {item.material_provided_by_buyer ? (
                                              <span className="text-xs text-slate-400">Buyer</span>
                                            ) : (
                                              `₹${(item.material_cost || 0).toLocaleString('en-IN')}`
                                            )}
                                          </td>
                                          <td className="p-2 text-right">
                                            ₹{(item.labour_cost || 0).toLocaleString('en-IN')}
                                          </td>
                                          <td className="p-2 text-right">
                                            {itemAdditional > 0 ? (
                                              `₹${itemAdditional.toLocaleString('en-IN')}`
                                            ) : '-'}
                                          </td>
                                          <td className="p-2 text-right font-medium">
                                            ₹{(item.total_cost || 0).toLocaleString('en-IN')}
                                          </td>
                                        </tr>
                                      );
                                    })}
                                  </tbody>
                                </table>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </>
                  );
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Quote Details Dialog */}
      <Dialog open={detailsOpen} onOpenChange={setDetailsOpen}>
        <DialogContent className="max-w-lg max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <DollarSign className="w-5 h-5 text-orange-600" />
              Quotation Details
              {selectedQuote?.is_itemwise && (
                <span className="px-2 py-0.5 bg-purple-100 text-purple-700 text-xs rounded-full font-medium">
                  Item-wise
                </span>
              )}
            </DialogTitle>
          </DialogHeader>
          
          {selectedQuote && (
            <div className="space-y-4 mt-4">
              {/* Vendor Info */}
              <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
                <Building2 className="w-8 h-8 text-slate-400" />
                <div>
                  <p className="font-medium text-slate-900">{selectedQuote.vendor_name}</p>
                  <p className="text-sm text-slate-500">{selectedQuote.vendor_location}</p>
                </div>
              </div>

              {/* Item-wise Breakdown */}
              {selectedQuote.is_itemwise && selectedQuote.items && (
                <div className="space-y-3">
                  <h4 className="font-medium text-slate-700 flex items-center gap-2">
                    <FileText className="w-4 h-4" /> Item-wise Breakdown ({selectedQuote.items.length} items)
                  </h4>
                  <div className="space-y-2">
                    {selectedQuote.items.map((item, idx) => {
                      const itemAdditional = item.additional_costs ? 
                        Object.values(item.additional_costs).reduce((a, b) => a + b, 0) : 0;
                      return (
                        <div key={item.item_id || idx} className="p-3 bg-slate-50 rounded-lg">
                          <div className="flex justify-between items-start">
                            <div>
                              <p className="font-medium text-slate-800">
                                {idx + 1}. {item.title || `Item ${idx + 1}`}
                              </p>
                              {item.remarks && (
                                <p className="text-xs text-slate-500 mt-1">{item.remarks}</p>
                              )}
                            </div>
                            <span className="font-bold text-slate-900">
                              ₹{(item.total_cost || 0).toLocaleString('en-IN')}
                            </span>
                          </div>
                          <div className="grid grid-cols-3 gap-2 mt-2 text-xs text-slate-600">
                            <div>
                              <span className="text-slate-400">Material:</span>{' '}
                              {item.material_provided_by_buyer ? 'Buyer' : `₹${(item.material_cost || 0).toLocaleString('en-IN')}`}
                            </div>
                            <div>
                              <span className="text-slate-400">Labour:</span>{' '}
                              ₹{(item.labour_cost || 0).toLocaleString('en-IN')}
                            </div>
                            <div>
                              <span className="text-slate-400">Additional:</span>{' '}
                              {itemAdditional > 0 ? `₹${itemAdditional.toLocaleString('en-IN')}` : '-'}
                            </div>
                          </div>
                          {item.additional_costs && Object.keys(item.additional_costs).length > 0 && (
                            <div className="mt-2 pt-2 border-t border-slate-200">
                              <p className="text-xs text-slate-400 mb-1">Additional Costs:</p>
                              <div className="flex flex-wrap gap-1">
                                {Object.entries(item.additional_costs).map(([key, value]) => (
                                  <span key={key} className="text-xs px-2 py-0.5 bg-orange-50 text-orange-700 rounded">
                                    {key.replace(/_/g, ' ')}: ₹{value.toLocaleString('en-IN')}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Cost Breakdown (for non-itemwise) */}
              {!selectedQuote.is_itemwise && (
                <div className="space-y-3">
                  <h4 className="font-medium text-slate-700">Cost Breakdown</h4>
                  
                  <div className="space-y-2">
                    {/* Material Cost */}
                    <div className="flex justify-between items-center p-2 bg-slate-50 rounded">
                      <span className="text-slate-600">Material Cost</span>
                      {selectedQuote.material_provided_by_buyer ? (
                        <span className="text-slate-400 italic text-sm">Buyer provides material</span>
                      ) : (
                        <span className="font-medium">₹{selectedQuote.material_cost?.toLocaleString('en-IN')}</span>
                      )}
                    </div>

                    {/* Machining Cost */}
                    <div className="flex justify-between items-center p-2 bg-slate-50 rounded">
                      <span className="text-slate-600">Labour / Machining Cost</span>
                      <span className="font-medium">₹{(selectedQuote.labour_cost || selectedQuote.machining_cost)?.toLocaleString('en-IN')}</span>
                    </div>

                    {/* Additional Costs */}
                    {selectedQuote.additional_costs && Object.keys(selectedQuote.additional_costs).length > 0 && (
                      <>
                        <p className="text-sm text-slate-500 pt-2">Additional Costs:</p>
                        {Object.entries(selectedQuote.additional_costs).map(([key, value]) => (
                          <div key={key} className="flex justify-between items-center p-2 bg-orange-50 rounded">
                            <span className="text-slate-600 capitalize">{key.replace(/_/g, ' ')}</span>
                            <span className="font-medium">₹{value?.toLocaleString('en-IN')}</span>
                          </div>
                        ))}
                      </>
                    )}
                  </div>
                </div>
              )}

              {/* Total */}
              <div className="flex justify-between items-center p-3 bg-green-50 rounded-lg border border-green-200">
                <span className="font-medium text-green-700">
                  {selectedQuote.is_itemwise ? 'Grand Total' : 'Total Cost'}
                </span>
                <span className="text-xl font-bold text-green-700">
                  ₹{selectedQuote.total_cost?.toLocaleString('en-IN')}
                </span>
              </div>

              {/* Lead Time & Payment Terms */}
              <div className="grid grid-cols-2 gap-4">
                <div className="p-3 bg-slate-50 rounded">
                  <p className="text-xs text-slate-500 uppercase mb-1">Lead Time</p>
                  <p className="font-medium text-slate-900">{selectedQuote.lead_time_days} days</p>
                </div>
                <div className="p-3 bg-slate-50 rounded">
                  <p className="text-xs text-slate-500 uppercase mb-1">Currency</p>
                  <p className="font-medium text-slate-900">{selectedQuote.currency}</p>
                </div>
              </div>

              {/* Notes */}
              {selectedQuote.notes && (
                <div>
                  <p className="text-sm text-slate-500 mb-1">Vendor Notes</p>
                  <p className="text-slate-700 bg-slate-50 p-3 rounded">{selectedQuote.notes}</p>
                </div>
              )}

              {/* Cost Breakdown Remarks */}
              {selectedQuote.cost_breakdown_remarks && (
                <div>
                  <p className="text-sm text-slate-500 mb-1">Cost Breakdown Remarks</p>
                  <p className="text-slate-700 bg-blue-50 p-3 rounded text-sm">{selectedQuote.cost_breakdown_remarks}</p>
                </div>
              )}
            </div>
          )}

          <DialogFooter className="mt-4">
            <Button variant="outline" onClick={() => setDetailsOpen(false)}>Close</Button>
            {selectedQuote && !selectedQuote.is_selected && (
              <Button 
                className="bg-orange-600 hover:bg-orange-700"
                onClick={() => {
                  handleSelectQuote(selectedQuote.quote_id);
                  setDetailsOpen(false);
                }}
              >
                <CheckCircle2 className="w-4 h-4 mr-1" /> Select This Quote
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default QuotationComparison;
