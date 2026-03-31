import { useState, useEffect, useRef, useCallback } from "react";
import { CheckCircle2, XCircle, Loader2, AlertTriangle } from "lucide-react";

const API_URL = process.env.REACT_APP_BACKEND_URL;

export const usePhoneCheck = (currentUserId = null) => {
  const [phoneStatus, setPhoneStatus] = useState(null); // null | "checking" | "available" | "taken" | "invalid"
  const [phoneMessage, setPhoneMessage] = useState("");
  const timerRef = useRef(null);

  const checkPhone = useCallback((phone) => {
    if (timerRef.current) clearTimeout(timerRef.current);
    
    const cleaned = (phone || "").replace(/[\s\-\(\)\.]/g, "");
    if (!cleaned || cleaned.length < 10) {
      setPhoneStatus(null);
      setPhoneMessage("");
      return;
    }

    setPhoneStatus("checking");
    timerRef.current = setTimeout(async () => {
      try {
        const res = await fetch(`${API_URL}/api/auth/check-phone`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ phone: cleaned, current_user_id: currentUserId }),
        });
        const data = await res.json();
        if (data.available) {
          setPhoneStatus("available");
          setPhoneMessage("Phone number available");
        } else if (data.code === "INVALID_PHONE") {
          setPhoneStatus("invalid");
          setPhoneMessage(data.message);
        } else {
          setPhoneStatus("taken");
          setPhoneMessage(data.message || "This number is already registered.");
        }
      } catch {
        setPhoneStatus(null);
        setPhoneMessage("");
      }
    }, 600);
  }, [currentUserId]);

  useEffect(() => {
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, []);

  return { phoneStatus, phoneMessage, checkPhone };
};

export const PhoneStatusIndicator = ({ status, message }) => {
  if (!status || status === "checking") {
    return status === "checking" ? (
      <div className="flex items-center gap-1 mt-1" data-testid="phone-checking">
        <Loader2 className="w-3 h-3 animate-spin text-slate-400" />
        <span className="text-xs text-slate-400">Checking...</span>
      </div>
    ) : null;
  }
  if (status === "available") {
    return (
      <div className="flex items-center gap-1 mt-1" data-testid="phone-available">
        <CheckCircle2 className="w-3 h-3 text-green-500" />
        <span className="text-xs text-green-600">{message}</span>
      </div>
    );
  }
  if (status === "taken") {
    return (
      <div className="mt-1 space-y-1" data-testid="phone-taken">
        <div className="flex items-center gap-1">
          <XCircle className="w-3 h-3 text-red-500" />
          <span className="text-xs text-red-600">{message}</span>
        </div>
      </div>
    );
  }
  if (status === "invalid") {
    return (
      <div className="flex items-center gap-1 mt-1" data-testid="phone-invalid">
        <AlertTriangle className="w-3 h-3 text-amber-500" />
        <span className="text-xs text-amber-600">{message}</span>
      </div>
    );
  }
  return null;
};
