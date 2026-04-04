import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { 
  AlertTriangle, XCircle, ChevronDown, ChevronUp, 
  Building2, MapPin, Star, Cpu, Eye, HelpCircle,
  CheckCircle, Wrench, Shield
} from "lucide-react";
import { Link } from "react-router-dom";

const CATEGORY_CONFIG = {
  confirmed_capable: {
    bg: "bg-emerald-100 text-emerald-800 border-emerald-200",
    label: "Confirmed Capable",
    icon: <CheckCircle className="w-3.5 h-3.5" />,
  },
  likely_capable: {
    bg: "bg-amber-100 text-amber-800 border-amber-200",
    label: "Likely Capable",
    icon: <AlertTriangle className="w-3.5 h-3.5" />,
  },
  partial_match: {
    bg: "bg-blue-100 text-blue-800 border-blue-200",
    label: "Partial Match",
    icon: <Wrench className="w-3.5 h-3.5" />,
  },
  excluded_too_small: {
    bg: "bg-red-100 text-red-800 border-red-200",
    label: "Machine Too Small",
    icon: <XCircle className="w-3.5 h-3.5" />,
  },
  excluded_wrong_type: {
    bg: "bg-slate-200 text-slate-700 border-slate-300",
    label: "Wrong Machine Type",
    icon: <HelpCircle className="w-3.5 h-3.5" />,
  },
  // Backward compat
  fully_capable: {
    bg: "bg-emerald-100 text-emerald-800 border-emerald-200",
    label: "Confirmed Capable",
    icon: <CheckCircle className="w-3.5 h-3.5" />,
  },
  unverified: {
    bg: "bg-amber-100 text-amber-800 border-amber-200",
    label: "Likely Capable",
    icon: <AlertTriangle className="w-3.5 h-3.5" />,
  },
  too_small: {
    bg: "bg-red-100 text-red-800 border-red-200",
    label: "Machine Too Small",
    icon: <XCircle className="w-3.5 h-3.5" />,
  },
  wrong_type: {
    bg: "bg-slate-200 text-slate-700 border-slate-300",
    label: "Wrong Machine Type",
    icon: <HelpCircle className="w-3.5 h-3.5" />,
  },
};

export const ValidationBadge = ({ category }) => {
  const c = CATEGORY_CONFIG[category] || CATEGORY_CONFIG.excluded_wrong_type;
  return (
    <span data-testid={`validation-badge-${category}`} className={`inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full border ${c.bg}`}>
      {c.icon} {c.label}
    </span>
  );
};

const OperationsSummary = ({ summary, capableOps, failedOps, unverifiedOps }) => {
  if (!summary || Object.keys(summary).length === 0) return null;
  return (
    <div className="mt-2 flex flex-wrap gap-1" data-testid="operations-summary">
      {Object.entries(summary).map(([op, detail]) => {
        const status = detail?.status || "wrong_type";
        const colors = {
          capable: "bg-emerald-50 text-emerald-700 border-emerald-200",
          unverified: "bg-amber-50 text-amber-700 border-amber-200",
          too_small: "bg-red-50 text-red-700 border-red-200",
          tolerance_fail: "bg-red-50 text-red-700 border-red-200",
          wrong_type: "bg-slate-100 text-slate-600 border-slate-200",
        };
        const icons = {
          capable: <CheckCircle className="w-2.5 h-2.5" />,
          unverified: <AlertTriangle className="w-2.5 h-2.5" />,
          too_small: <XCircle className="w-2.5 h-2.5" />,
          tolerance_fail: <XCircle className="w-2.5 h-2.5" />,
          wrong_type: <HelpCircle className="w-2.5 h-2.5" />,
        };
        return (
          <span
            key={op}
            className={`inline-flex items-center gap-1 text-[10px] font-medium px-2 py-0.5 rounded border ${colors[status] || colors.wrong_type}`}
            title={detail?.best_machine?.machine_name || "No machine found"}
          >
            {icons[status] || icons.wrong_type}
            {op.replace(/_/g, " ")}
          </span>
        );
      })}
    </div>
  );
};

const FailReasonList = ({ machines }) => {
  if (!machines?.length) return null;
  return (
    <div className="mt-2 space-y-1" data-testid="fail-reasons">
      {machines.map((m, i) => (
        <div key={i} className="text-xs text-red-600 bg-red-50 border border-red-100 rounded px-2 py-1">
          <span className="font-medium">{m.machine_name || m.machine_type}:</span>{" "}
          {m.fail_reasons?.join("; ") || `Cannot perform ${m.operation}`}
        </div>
      ))}
    </div>
  );
};

const MachineSpecsDisplay = ({ machines, type }) => {
  if (!machines?.length) return null;
  return (
    <div className="mt-2 flex flex-wrap gap-1">
      {machines.map((m, i) => (
        <div key={i} className="text-xs bg-slate-100 border border-slate-200 rounded px-2 py-1">
          <span className="font-medium">{m.machine_name || m.machine_type}</span>
          {m.operations_covered && (
            <span className="ml-1 text-emerald-600">({m.operations_covered.join(", ")})</span>
          )}
          {m.operations && (
            <span className="ml-1 text-amber-600">({m.operations.join(", ")})</span>
          )}
          {type === "unverified" && m.unverified_reasons?.map((w, j) => (
            <span key={j} className="ml-1 text-amber-600 italic text-[10px]"> {w}</span>
          ))}
        </div>
      ))}
    </div>
  );
};

const VendorRow = ({ vendor, type }) => {
  return (
    <div className="p-3 bg-white rounded-lg border border-slate-200" data-testid={`${type}-vendor-${vendor.vendor_id}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 min-w-0">
          <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
            type === "likely" ? "bg-amber-100" : type === "partial" ? "bg-blue-100" : type === "too_small" ? "bg-red-100" : "bg-slate-100"
          }`}>
            <Building2 className={`w-4 h-4 ${
              type === "likely" ? "text-amber-600" : type === "partial" ? "text-blue-600" : type === "too_small" ? "text-red-600" : "text-slate-500"
            }`} />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-medium text-slate-900 truncate">{vendor.company_name}</p>
            <div className="flex items-center gap-2 text-xs text-slate-500">
              {vendor.location && <span className="flex items-center gap-0.5"><MapPin className="w-3 h-3" />{vendor.location}</span>}
              {vendor.rating > 0 && <span className="flex items-center gap-0.5"><Star className="w-3 h-3 text-amber-500" />{vendor.rating}</span>}
              {vendor.total_jobs > 0 && <span>{vendor.total_jobs} jobs</span>}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {vendor.validation_coverage > 0 && (
            <span className="text-xs font-medium text-slate-500">{vendor.validation_coverage}% ops</span>
          )}
          <Link to={`/vendor-profile/${vendor.vendor_id}`}>
            <Button variant="outline" size="sm" className="text-xs h-7" data-testid={`profile-btn-${vendor.vendor_id}`}>
              <Eye className="w-3 h-3 mr-1" /> Profile
            </Button>
          </Link>
        </div>
      </div>
      {/* Operations summary for likely/partial */}
      {(type === "likely" || type === "partial") && vendor.operations_summary && (
        <OperationsSummary
          summary={vendor.operations_summary}
          capableOps={vendor.capable_operations}
          failedOps={vendor.failed_operations}
          unverifiedOps={vendor.unverified_operations}
        />
      )}
      {type === "likely" && <MachineSpecsDisplay machines={vendor.unverified_machines} type="unverified" />}
      {type === "partial" && <MachineSpecsDisplay machines={vendor.validated_machines} type="capable" />}
      {(type === "too_small" || type === "wrong_type") && <FailReasonList machines={vendor.failed_machines} />}
    </div>
  );
};

export const ExcludedVendorsSection = ({ 
  likelyVendors, partialVendors, 
  unverifiedVendors, tooSmallVendors, wrongTypeVendors,
  requiredOperations 
}) => {
  const [openSection, setOpenSection] = useState(null);

  // Support both new and legacy prop names
  const likely = likelyVendors || unverifiedVendors || [];
  const partial = partialVendors || [];
  const tooSmall = tooSmallVendors || [];
  const wrongType = wrongTypeVendors || [];

  const sections = [
    {
      key: "likely",
      vendors: likely,
      icon: <AlertTriangle className="w-4 h-4 text-amber-500" />,
      title: "Likely Capable",
      subtitle: "Right machine types found but dimension specs not provided. Contact vendor to verify capacity before quoting.",
      bgHeader: "bg-amber-50 border-amber-200",
      textColor: "text-amber-700",
    },
    {
      key: "partial",
      vendors: partial,
      icon: <Wrench className="w-4 h-4 text-blue-500" />,
      title: "Partial Match",
      subtitle: "Can handle some required operations but not all. May need to outsource remaining steps.",
      bgHeader: "bg-blue-50 border-blue-200",
      textColor: "text-blue-700",
    },
    {
      key: "too_small",
      vendors: tooSmall,
      icon: <XCircle className="w-4 h-4 text-red-500" />,
      title: "Machine Too Small",
      subtitle: "Right machine type but dimensions are insufficient for this part.",
      bgHeader: "bg-red-50 border-red-200",
      textColor: "text-red-700",
    },
    {
      key: "wrong_type",
      vendors: wrongType,
      icon: <HelpCircle className="w-4 h-4 text-slate-400" />,
      title: "No Compatible Machine",
      subtitle: "Vendor's machines cannot perform the required operations for this job.",
      bgHeader: "bg-slate-50 border-slate-200",
      textColor: "text-slate-600",
    },
  ];

  const activeSections = sections.filter(s => s.vendors.length > 0);
  if (activeSections.length === 0) return null;

  return (
    <Card className="border-slate-200 mt-4" data-testid="excluded-vendors-section">
      <CardHeader className="pb-2">
        <CardTitle className="font-heading text-sm flex items-center gap-2 text-slate-500">
          <Shield className="w-4 h-4" /> Physics-Based Validation Results
        </CardTitle>
        <p className="text-xs text-slate-400">
          Vendors below didn't qualify as "Confirmed Capable" — grouped by validation result
        </p>
        {requiredOperations?.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-1">
            <span className="text-[10px] text-slate-400 mr-1">Required ops:</span>
            {requiredOperations.map(op => (
              <span key={op} className="text-[10px] bg-slate-100 text-slate-600 border border-slate-200 rounded px-1.5 py-0.5">
                {op.replace(/_/g, " ")}
              </span>
            ))}
          </div>
        )}
      </CardHeader>
      <CardContent className="space-y-2">
        {activeSections.map(section => {
          const isOpen = openSection === section.key;
          return (
            <div key={section.key} className={`rounded-lg border ${section.bgHeader}`} data-testid={`section-${section.key}`}>
              <button
                onClick={() => setOpenSection(isOpen ? null : section.key)}
                className="w-full flex items-center justify-between p-3 text-left"
                data-testid={`toggle-${section.key}`}
              >
                <div className="flex items-center gap-2">
                  {section.icon}
                  <span className={`text-sm font-semibold ${section.textColor}`}>{section.title}</span>
                  <span className="text-xs bg-white border border-slate-200 rounded-full px-2 py-0.5 text-slate-500 font-medium">
                    {section.vendors.length}
                  </span>
                </div>
                {isOpen ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
              </button>
              {isOpen && (
                <div className="px-3 pb-3 space-y-2">
                  <p className="text-xs text-slate-500 mb-2">{section.subtitle}</p>
                  {section.vendors.map(v => (
                    <VendorRow key={v.vendor_id} vendor={v} type={section.key} />
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
};

export default ExcludedVendorsSection;
