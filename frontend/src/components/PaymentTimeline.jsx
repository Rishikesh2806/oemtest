import { useState, useEffect, useCallback } from "react";
import { api } from "../App";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import {
  CreditCard, CheckCircle2, Clock, Loader2, AlertCircle,
  CircleDot, ArrowRight, Banknote, Lock, ChevronRight
} from "lucide-react";

const STAGE_ORDER = [
  "before_production",
  "after_production",
  "after_inspection",
  "after_dispatch",
  "on_delivery",
  "net_due"
];

const PaymentTimeline = ({ orderId, orderStatus, isBuyer, isAdmin, onPaymentComplete }) => {
  const [schedule, setSchedule] = useState(null);
  const [loading, setLoading] = useState(true);
  const [payingMilestone, setPayingMilestone] = useState(null);

  const fetchSchedule = useCallback(async () => {
    try {
      const res = await api.get(`/orders/${orderId}/payment-schedule`);
      setSchedule(res.data);
    } catch {
      // Order may not have schedule
    } finally {
      setLoading(false);
    }
  }, [orderId]);

  useEffect(() => { fetchSchedule(); }, [fetchSchedule]);

  const handlePay = async (milestoneId) => {
    setPayingMilestone(milestoneId);
    try {
      const res = await api.post(`/orders/${orderId}/pay`, { milestone_id: milestoneId });
      toast.success(res.data.message);
      fetchSchedule();
      if (onPaymentComplete) onPaymentComplete();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Payment failed");
    } finally {
      setPayingMilestone(null);
    }
  };

  if (loading) {
    return (
      <Card className="border-slate-200">
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="w-5 h-5 animate-spin text-slate-400" />
        </CardContent>
      </Card>
    );
  }

  if (!schedule?.schedule?.milestones?.length) return null;

  const { milestones, total_paid, total_pending } = schedule.schedule;
  const currency = schedule.currency || "INR";
  const totalAmount = schedule.total_amount || 0;
  const paidPct = totalAmount > 0 ? Math.round((total_paid / totalAmount) * 100) : 0;

  const allPaid = milestones.every(m => m.status === "paid");
  const hasPartialPaid = milestones.some(m => m.status === "paid") && !allPaid;

  return (
    <Card className="border-slate-200" data-testid="payment-timeline-card">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="font-heading text-lg flex items-center gap-2">
            <CreditCard className="w-5 h-5 text-orange-600" />
            Payment Schedule
          </CardTitle>
          <Badge
            variant="outline"
            className={
              allPaid ? "border-green-300 text-green-700 bg-green-50" :
              hasPartialPaid ? "border-amber-300 text-amber-700 bg-amber-50" :
              "border-slate-300 text-slate-600"
            }
            data-testid="payment-schedule-status"
          >
            {allPaid ? "Fully Paid" : hasPartialPaid ? "Partially Paid" : "Payment Pending"}
          </Badge>
        </div>
        {/* Progress bar */}
        <div className="mt-3">
          <div className="flex items-center justify-between text-xs text-slate-500 mb-1.5">
            <span>Paid: {currency} {total_paid?.toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
            <span>Remaining: {currency} {total_pending?.toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
          </div>
          <div className="w-full bg-slate-100 rounded-full h-2.5">
            <div
              className={`h-2.5 rounded-full transition-all duration-500 ${allPaid ? "bg-green-500" : "bg-orange-500"}`}
              style={{ width: `${paidPct}%` }}
            />
          </div>
          <p className="text-right text-xs text-slate-400 mt-1">{paidPct}% of {currency} {totalAmount?.toLocaleString(undefined, {minimumFractionDigits: 2})}</p>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        {/* Milestones */}
        <div className="space-y-0">
          {milestones.map((ms, idx) => {
            const isPaid = ms.status === "paid";
            const isDue = ms.is_due;
            const isBlocking = ms.blocks_status && !isPaid;
            const isLast = idx === milestones.length - 1;

            return (
              <div key={ms.milestone_id} data-testid={`milestone-${ms.milestone_id}`}>
                <div className={`flex items-start gap-3 py-3 ${!isLast ? "border-b border-slate-100" : ""}`}>
                  {/* Timeline dot */}
                  <div className="flex flex-col items-center pt-0.5">
                    {isPaid ? (
                      <div className="w-7 h-7 rounded-full bg-green-100 flex items-center justify-center">
                        <CheckCircle2 className="w-4 h-4 text-green-600" />
                      </div>
                    ) : isDue ? (
                      <div className="w-7 h-7 rounded-full bg-orange-100 flex items-center justify-center animate-pulse">
                        <CircleDot className="w-4 h-4 text-orange-600" />
                      </div>
                    ) : (
                      <div className="w-7 h-7 rounded-full bg-slate-100 flex items-center justify-center">
                        <Clock className="w-4 h-4 text-slate-400" />
                      </div>
                    )}
                  </div>

                  {/* Milestone details */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`font-medium text-sm ${isPaid ? "text-green-700" : isDue ? "text-orange-800" : "text-slate-600"}`}>
                        {ms.label}
                      </span>
                      <span className={`text-xs px-1.5 py-0.5 rounded ${isPaid ? "bg-green-50 text-green-600" : "bg-slate-50 text-slate-500"}`}>
                        {ms.percentage}%
                      </span>
                      {isBlocking && (
                        <span className="inline-flex items-center gap-1 text-[11px] text-red-600 bg-red-50 px-1.5 py-0.5 rounded">
                          <Lock className="w-3 h-3" />
                          Blocks {ms.blocks_status?.replace(/_/g, " ")}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-3 mt-1">
                      <span className={`text-base font-semibold ${isPaid ? "text-green-700" : "text-slate-800"}`}>
                        {currency} {ms.amount?.toLocaleString(undefined, {minimumFractionDigits: 2})}
                      </span>
                      {isPaid && ms.paid_at && (
                        <span className="text-xs text-green-600">
                          Paid {new Date(ms.paid_at).toLocaleDateString()}
                        </span>
                      )}
                      {!isPaid && ms.due_date && (
                        <span className={`text-xs ${new Date(ms.due_date) < new Date() ? "text-red-600 font-medium" : "text-slate-500"}`}>
                          Due: {new Date(ms.due_date).toLocaleDateString()}
                          {new Date(ms.due_date) < new Date() && " (Overdue)"}
                        </span>
                      )}
                      {!isPaid && ms.stage && ms.stage !== "net_due" && (
                        <span className="text-xs text-slate-400 capitalize">
                          {ms.stage.replace(/_/g, " ")}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Pay button */}
                  <div className="flex-shrink-0">
                    {isPaid ? (
                      <Badge variant="outline" className="border-green-200 text-green-700 bg-green-50" data-testid={`milestone-paid-${ms.milestone_id}`}>
                        Paid
                      </Badge>
                    ) : isDue && (isBuyer || isAdmin) ? (
                      <Button
                        size="sm"
                        className="bg-orange-600 hover:bg-orange-700 text-white h-8"
                        disabled={payingMilestone === ms.milestone_id}
                        onClick={() => handlePay(ms.milestone_id)}
                        data-testid={`pay-milestone-${ms.milestone_id}`}
                      >
                        {payingMilestone === ms.milestone_id ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin mr-1" />
                        ) : (
                          <Banknote className="w-3.5 h-3.5 mr-1" />
                        )}
                        Pay Now
                      </Button>
                    ) : (
                      <Badge variant="outline" className="border-slate-200 text-slate-500" data-testid={`milestone-pending-${ms.milestone_id}`}>
                        Upcoming
                      </Badge>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Enforcement notice */}
        {milestones.some(m => m.status === "pending" && m.blocks_status) && (isBuyer || isAdmin) && (
          <div className="mt-3 p-3 bg-amber-50 border border-amber-200 rounded-lg flex items-start gap-2" data-testid="payment-gate-notice">
            <AlertCircle className="w-4 h-4 text-amber-600 mt-0.5 flex-shrink-0" />
            <p className="text-xs text-amber-700">
              Some order stages are blocked until the corresponding payment milestones are completed.
              {isAdmin && " As admin, you can use the override option when updating order status."}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default PaymentTimeline;
