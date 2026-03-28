import { useState } from "react";
import { Copy, Check } from "lucide-react";

const RefNumber = ({ value, fallback, className = "" }) => {
  const [copied, setCopied] = useState(false);
  const display = value || fallback || "—";

  const handleCopy = (e) => {
    e.preventDefault();
    e.stopPropagation();
    navigator.clipboard.writeText(display);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  if (!value && !fallback) return null;

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-mono text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded cursor-pointer hover:bg-slate-200 transition-colors ${className}`}
      onClick={handleCopy}
      title="Click to copy"
      data-testid={`ref-number-${display}`}
    >
      {display}
      {copied ? (
        <Check className="w-3 h-3 text-emerald-500" />
      ) : (
        <Copy className="w-3 h-3 text-slate-400" />
      )}
    </span>
  );
};

export default RefNumber;
