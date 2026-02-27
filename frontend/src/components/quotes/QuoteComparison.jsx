import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../ui/dialog";
import { Button } from "../ui/button";
import { Checkbox } from "../ui/checkbox";
import { 
  DollarSign, Clock, Star, MapPin, Building2, CheckCircle2, 
  Trophy, TrendingDown, Zap, Award, Wrench, MessageSquare, Eye, CreditCard
} from "lucide-react";
import { Link } from "react-router-dom";

const PAYMENT_TERMS_LABELS = {
  "net_30": "Net 30 Days",
  "net_45": "Net 45 Days",
  "net_60": "Net 60 Days",
  "50_advance_50_delivery": "50% Advance, 50% on Delivery",
  "100_advance": "100% Advance",
  "against_delivery": "Against Delivery",
  "milestone_based": "Milestone-Based",
  "letter_of_credit": "Letter of Credit",
  "custom": "Custom Terms"
};

const QuoteComparison = ({ quotes, open, onOpenChange, onAcceptQuote, rfqId }) => {
  const [selectedQuotes, setSelectedQuotes] = useState([]);
  
  // Filter to only pending quotes for comparison
  const pendingQuotes = quotes.filter(q => q.status === "pending");
  
  // Calculate best values
  const lowestPrice = Math.min(...pendingQuotes.map(q => q.price));
  const fastestDelivery = Math.min(...pendingQuotes.map(q => q.lead_time_days));
  const highestRating = Math.max(...pendingQuotes.map(q => q.vendor_rating || 0));
  
  const toggleQuoteSelection = (quoteId) => {
    setSelectedQuotes(prev => 
      prev.includes(quoteId) 
        ? prev.filter(id => id !== quoteId)
        : [...prev, quoteId]
    );
  };
  
  const quotesToCompare = selectedQuotes.length >= 2 
    ? pendingQuotes.filter(q => selectedQuotes.includes(q.quote_id))
    : pendingQuotes.slice(0, 4);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-6xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-xl">
            <Trophy className="w-5 h-5 text-orange-600" />
            Compare Quotes
          </DialogTitle>
          <p className="text-sm text-slate-500 mt-1">
            Compare vendor quotes side-by-side to make the best decision
          </p>
        </DialogHeader>
        
        {/* Quote Selection (if more than 4 quotes) */}
        {pendingQuotes.length > 4 && (
          <div className="mb-4 p-3 bg-slate-50 rounded-lg">
            <p className="text-sm font-medium text-slate-700 mb-2">
              Select quotes to compare (max 4):
            </p>
            <div className="flex flex-wrap gap-2">
              {pendingQuotes.map(quote => (
                <label 
                  key={quote.quote_id}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg border cursor-pointer transition-all ${
                    selectedQuotes.includes(quote.quote_id)
                      ? "bg-orange-50 border-orange-300"
                      : "bg-white border-slate-200 hover:border-orange-200"
                  }`}
                >
                  <Checkbox 
                    checked={selectedQuotes.includes(quote.quote_id)}
                    onCheckedChange={() => toggleQuoteSelection(quote.quote_id)}
                    disabled={!selectedQuotes.includes(quote.quote_id) && selectedQuotes.length >= 4}
                  />
                  <span className="text-sm">{quote.vendor_name}</span>
                </label>
              ))}
            </div>
          </div>
        )}
        
        {/* Comparison Grid */}
        <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${Math.min(quotesToCompare.length, 4)}, 1fr)` }}>
          {quotesToCompare.map((quote, index) => {
            const isBestPrice = quote.price === lowestPrice;
            const isFastest = quote.lead_time_days === fastestDelivery;
            const isTopRated = quote.vendor_rating === highestRating && highestRating > 0;
            const hasBadge = isBestPrice || isFastest || isTopRated;
            
            return (
              <div 
                key={quote.quote_id}
                className={`relative rounded-xl border-2 overflow-hidden ${
                  index === 0 ? "border-orange-300 bg-orange-50/30" : "border-slate-200 bg-white"
                }`}
                data-testid={`compare-quote-${quote.quote_id}`}
              >
                {/* Badge Row */}
                {hasBadge && (
                  <div className="flex flex-wrap gap-1 p-2 bg-gradient-to-r from-slate-50 to-white border-b">
                    {isBestPrice && (
                      <span className="inline-flex items-center gap-1 text-xs font-semibold bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
                        <TrendingDown className="w-3 h-3" /> Best Price
                      </span>
                    )}
                    {isFastest && (
                      <span className="inline-flex items-center gap-1 text-xs font-semibold bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
                        <Zap className="w-3 h-3" /> Fastest
                      </span>
                    )}
                    {isTopRated && (
                      <span className="inline-flex items-center gap-1 text-xs font-semibold bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full">
                        <Award className="w-3 h-3" /> Top Rated
                      </span>
                    )}
                  </div>
                )}
                
                {/* Vendor Header */}
                <div className="p-4 border-b bg-white">
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                      index === 0 ? "bg-orange-600 text-white" : "bg-slate-200 text-slate-600"
                    }`}>
                      <Building2 className="w-5 h-5" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-semibold text-slate-900 truncate">{quote.vendor_name}</p>
                      {quote.vendor_location && (
                        <p className="text-xs text-slate-500 flex items-center gap-1 truncate">
                          <MapPin className="w-3 h-3 flex-shrink-0" /> {quote.vendor_location}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
                
                {/* Price - Main Highlight */}
                <div className={`p-4 text-center ${isBestPrice ? "bg-green-50" : "bg-slate-50"}`}>
                  <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-1">Price</p>
                  <div className={`flex items-center justify-center gap-1 text-3xl font-bold ${
                    isBestPrice ? "text-green-600" : "text-slate-900"
                  }`}>
                    <DollarSign className="w-6 h-6" />
                    {quote.price?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </div>
                  <p className="text-xs text-slate-500 mt-1">{quote.currency}</p>
                </div>
                
                {/* Lead Time */}
                <div className={`p-3 text-center border-t ${isFastest ? "bg-blue-50" : ""}`}>
                  <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-1">Lead Time</p>
                  <div className={`flex items-center justify-center gap-1 text-xl font-bold ${
                    isFastest ? "text-blue-600" : "text-slate-900"
                  }`}>
                    <Clock className="w-4 h-4" />
                    {quote.lead_time_days} days
                  </div>
                </div>
                
                {/* Vendor Stats */}
                <div className="p-3 border-t bg-white">
                  <div className="grid grid-cols-2 gap-2 text-center">
                    <div>
                      <p className="text-xs text-slate-500">Rating</p>
                      <div className={`flex items-center justify-center gap-1 font-semibold ${
                        isTopRated ? "text-amber-600" : "text-slate-900"
                      }`}>
                        <Star className={`w-4 h-4 ${isTopRated ? "fill-amber-400 text-amber-400" : "text-slate-300"}`} />
                        {quote.vendor_rating?.toFixed(1) || "N/A"}
                      </div>
                    </div>
                    <div>
                      <p className="text-xs text-slate-500">Jobs Done</p>
                      <p className="font-semibold text-slate-900">{quote.vendor_total_jobs || 0}</p>
                    </div>
                  </div>
                </div>
                
                {/* Acceptance Rate */}
                {quote.vendor_acceptance_rate !== undefined && (
                  <div className="px-3 pb-2 bg-white">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-500">Acceptance Rate</span>
                      <span className="font-medium text-slate-700">{quote.vendor_acceptance_rate}%</span>
                    </div>
                    <div className="w-full h-1.5 bg-slate-200 rounded-full mt-1 overflow-hidden">
                      <div 
                        className="h-full bg-green-500 rounded-full transition-all"
                        style={{ width: `${quote.vendor_acceptance_rate}%` }}
                      />
                    </div>
                  </div>
                )}
                
                {/* Certifications */}
                {quote.vendor_certifications?.length > 0 && (
                  <div className="p-3 border-t bg-white">
                    <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Certifications</p>
                    <div className="flex flex-wrap gap-1">
                      {quote.vendor_certifications.map((cert, i) => (
                        <span key={i} className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded">
                          {cert}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                
                {/* Machines */}
                {quote.vendor_machines?.length > 0 && (
                  <div className="p-3 border-t bg-white">
                    <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                      <Wrench className="w-3 h-3 inline mr-1" />
                      Machines
                    </p>
                    <div className="space-y-1">
                      {quote.vendor_machines.slice(0, 3).map((machine, i) => (
                        <p key={i} className="text-xs text-slate-600 truncate font-mono">
                          {machine}
                        </p>
                      ))}
                    </div>
                  </div>
                )}
                
                {/* Notes */}
                {quote.notes && (
                  <div className="p-3 border-t bg-slate-50">
                    <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-1">Vendor Notes</p>
                    <p className="text-xs text-slate-600 italic">"{quote.notes}"</p>
                  </div>
                )}
                
                {/* Actions */}
                <div className="p-3 border-t bg-white space-y-2">
                  <Button
                    onClick={() => onAcceptQuote(quote.quote_id)}
                    className="w-full bg-green-600 hover:bg-green-700"
                    data-testid={`accept-quote-compare-${quote.quote_id}`}
                  >
                    <CheckCircle2 className="w-4 h-4 mr-2" />
                    Accept Quote
                  </Button>
                  <div className="flex gap-2">
                    <Link to={`/vendor-profile/${quote.vendor_id_ref}`} className="flex-1">
                      <Button variant="outline" size="sm" className="w-full">
                        <Eye className="w-3 h-3 mr-1" /> Profile
                      </Button>
                    </Link>
                    <Link to={`/chat?with=${quote.vendor_user_id}&rfq=${rfqId}`} className="flex-1">
                      <Button variant="outline" size="sm" className="w-full">
                        <MessageSquare className="w-3 h-3 mr-1" /> Chat
                      </Button>
                    </Link>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
        
        {/* Summary Legend */}
        <div className="mt-4 p-3 bg-slate-50 rounded-lg">
          <p className="text-xs font-medium text-slate-700 mb-2">Legend:</p>
          <div className="flex flex-wrap gap-3 text-xs">
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 rounded-full bg-green-500"></span>
              Best Price: ${lowestPrice?.toLocaleString()}
            </span>
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 rounded-full bg-blue-500"></span>
              Fastest: {fastestDelivery} days
            </span>
            {highestRating > 0 && (
              <span className="flex items-center gap-1">
                <span className="w-3 h-3 rounded-full bg-amber-500"></span>
                Top Rated: {highestRating?.toFixed(1)}
              </span>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default QuoteComparison;
