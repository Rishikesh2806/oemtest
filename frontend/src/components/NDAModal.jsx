import { useState, useEffect } from "react";
import { api } from "../App";
import { Button } from "./ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "./ui/dialog";
import { Checkbox } from "./ui/checkbox";
import { Label } from "./ui/label";
import { Card, CardContent } from "./ui/card";
import { toast } from "sonner";
import { Shield, FileText, Loader2, AlertTriangle, CheckCircle2 } from "lucide-react";

const NDAModal = ({ 
  rfqId, 
  isOpen, 
  onClose, 
  onAccept,
  title = "Non-Disclosure Agreement Required"
}) => {
  const [loading, setLoading] = useState(true);
  const [ndaData, setNdaData] = useState(null);
  const [agreed, setAgreed] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (isOpen && rfqId) {
      fetchNDA();
    }
  }, [isOpen, rfqId]);

  const fetchNDA = async () => {
    setLoading(true);
    try {
      const response = await api.get(`/rfqs/${rfqId}/nda`);
      setNdaData(response.data);
      
      // If already accepted, call onAccept
      if (response.data.has_accepted) {
        onAccept?.();
      }
    } catch (error) {
      console.error("Failed to fetch NDA:", error);
      toast.error("Failed to load NDA");
    } finally {
      setLoading(false);
    }
  };

  const handleAccept = async () => {
    if (!agreed) {
      toast.error("Please check the agreement checkbox to proceed");
      return;
    }

    setSubmitting(true);
    try {
      await api.post(`/rfqs/${rfqId}/accept-nda`, { agree_checkbox: true });
      toast.success("NDA accepted successfully!");
      onAccept?.();
      onClose();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to accept NDA");
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen) return null;

  // Already accepted
  if (ndaData?.has_accepted) {
    return (
      <Dialog open={isOpen} onOpenChange={onClose}>
        <DialogContent className="max-w-md">
          <div className="text-center py-8">
            <CheckCircle2 className="w-16 h-16 text-green-500 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-slate-900">NDA Already Accepted</h3>
            <p className="text-slate-500 mt-2">
              You accepted the NDA on {new Date(ndaData.acceptance?.accepted_at).toLocaleDateString()}
            </p>
            <Button onClick={onClose} className="mt-4">Continue</Button>
          </div>
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-lg">
            <Shield className="w-5 h-5 text-orange-600" />
            {title}
          </DialogTitle>
        </DialogHeader>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-orange-600" />
          </div>
        ) : !ndaData?.nda_required ? (
          <div className="text-center py-8">
            <CheckCircle2 className="w-16 h-16 text-green-500 mx-auto mb-4" />
            <h3 className="text-lg font-semibold">No NDA Required</h3>
            <p className="text-slate-500 mt-2">You can access the drawings directly.</p>
            <Button onClick={() => { onAccept?.(); onClose(); }} className="mt-4">
              Continue
            </Button>
          </div>
        ) : (
          <>
            {/* Warning Banner */}
            <Card className="border-amber-200 bg-amber-50">
              <CardContent className="py-3 flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                <div className="text-sm">
                  <p className="font-medium text-amber-800">IP Protection Notice</p>
                  <p className="text-amber-700">
                    The buyer requires you to accept this Non-Disclosure Agreement before accessing 
                    any drawings, specifications, or technical documents for this RFQ.
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* NDA Content */}
            <div className="flex-1 overflow-y-auto my-4 border rounded-lg">
              <div className="sticky top-0 bg-slate-100 px-4 py-2 border-b">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-slate-700">
                    {ndaData?.template?.title || "Non-Disclosure Agreement"}
                  </span>
                  <span className="text-xs text-slate-500">
                    Version {ndaData?.template?.version || "1.0"}
                  </span>
                </div>
              </div>
              <div 
                className="p-4 prose prose-sm max-w-none"
                dangerouslySetInnerHTML={{ __html: ndaData?.template?.content || "" }}
              />
            </div>

            {/* Agreement Checkbox */}
            <div className="flex items-start gap-3 p-4 bg-slate-50 rounded-lg border">
              <Checkbox 
                id="nda-agree" 
                checked={agreed}
                onCheckedChange={setAgreed}
                data-testid="nda-agree-checkbox"
              />
              <Label htmlFor="nda-agree" className="text-sm cursor-pointer leading-relaxed">
                I have read, understood, and agree to be bound by the terms of this Non-Disclosure Agreement. 
                I understand that I am legally responsible for maintaining the confidentiality of all 
                information accessed through this RFQ.
              </Label>
            </div>

            <DialogFooter className="mt-4">
              <Button variant="outline" onClick={onClose}>
                Cancel
              </Button>
              <Button
                onClick={handleAccept}
                disabled={!agreed || submitting}
                className="bg-orange-600 hover:bg-orange-700"
                data-testid="accept-nda-btn"
              >
                {submitting ? (
                  <Loader2 className="w-4 h-4 animate-spin mr-2" />
                ) : (
                  <Shield className="w-4 h-4 mr-2" />
                )}
                Accept & View Drawings
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default NDAModal;
