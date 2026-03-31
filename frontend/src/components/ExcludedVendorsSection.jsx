import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { 
  AlertTriangle, XCircle, ChevronDown, ChevronUp, 
  Building2, MapPin, Star, Cpu, Eye, HelpCircle
} from "lucide-react";
import { Link } from "react-router-dom";

const VendorValidationBadge = ({ category }) => {
  const config = {
    fully_capable: { bg: "bg-green-100 text-green-800 border-green-200", label: "Verified Capable" },
    unverified:    { bg: "bg-amber-100 text-amber-800 border-amber-200", label: "Specs Unverified" },
    too_small:     { bg: "bg-red-100 text-red-800 border-red-200", label: "Machine Too Small" },
    wrong_type:    { bg: "bg-slate-200 text-slate-700 border-slate-300", label: "Wrong Machine Type" },
  };
  const c = config[category] || config.wrong_type;
  return (
    <span data-testid={`validation-badge-${category}`} className={`inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full border ${c.bg}`}>
      {c.label}
    </span>
  );
};

const FailReasonList = ({ machines }) => {
  if (!machines?.length) return null;
  return (
    <div className="mt-2 space-y-1" data-testid="fail-reasons">
      {machines.map((m, i) => (
        <div key={i} className="text-xs text-red-600 bg-red-50 border border-red-100 rounded px-2 py-1">
          <span className="font-medium">{m.machine_name || m.machine_type}:</span>{" "}
          {m.fail_reasons?.join("; ") || `Cannot perform ${m.process}`}
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
          {m.specs && Object.entries(m.specs).filter(([k]) => k !== "machine_name" && k !== "availability").map(([k, v]) => (
            <span key={k} className="ml-1 text-slate-500">
              {k.replace(/_/g, " ").replace(/mm$/, "")}: {v}mm
            </span>
          )).slice(0, 3)}
          {type === "unverified" && m.warnings?.map((w, j) => (
            <span key={j} className="ml-1 text-amber-600 italic">{w}</span>
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
            type === "unverified" ? "bg-amber-100" : type === "too_small" ? "bg-red-100" : "bg-slate-100"
          }`}>
            <Building2 className={`w-4 h-4 ${
              type === "unverified" ? "text-amber-600" : type === "too_small" ? "text-red-600" : "text-slate-500"
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
            <span className="text-xs font-medium text-slate-500">{vendor.validation_coverage}% coverage</span>
          )}
          <Link to={`/vendor-profile/${vendor.vendor_id}`}>
            <Button variant="outline" size="sm" className="text-xs h-7">
              <Eye className="w-3 h-3 mr-1" /> Profile
            </Button>
          </Link>
        </div>
      </div>
      {type === "unverified" && <MachineSpecsDisplay machines={vendor.unverified_machines} type="unverified" />}
      {type === "too_small" && <FailReasonList machines={vendor.failed_machines} />}
      {type === "wrong_type" && <FailReasonList machines={vendor.failed_machines} />}
    </div>
  );
};

export const ExcludedVendorsSection = ({ unverifiedVendors, tooSmallVendors, wrongTypeVendors }) => {
  const [openSection, setOpenSection] = useState(null);

  const sections = [
    {
      key: "unverified",
      vendors: unverifiedVendors || [],
      icon: <AlertTriangle className="w-4 h-4 text-amber-500" />,
      title: "Capable but Unverified",
      subtitle: "These vendors have the right machine type but have not provided size specifications. Contact to verify before quoting.",
      bgHeader: "bg-amber-50 border-amber-200",
      textColor: "text-amber-700",
    },
    {
      key: "too_small",
      vendors: tooSmallVendors || [],
      icon: <XCircle className="w-4 h-4 text-red-500" />,
      title: "Machine Too Small",
      subtitle: "These vendors have the right machine type but their machines are too small for this job.",
      bgHeader: "bg-red-50 border-red-200",
      textColor: "text-red-700",
    },
    {
      key: "wrong_type",
      vendors: wrongTypeVendors || [],
      icon: <HelpCircle className="w-4 h-4 text-slate-400" />,
      title: "Other Vendors",
      subtitle: "These vendors have manufacturing capability but not the specific machines needed for this job.",
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
          <Cpu className="w-4 h-4" /> Machine Validation Results
        </CardTitle>
        <p className="text-xs text-slate-400">
          Vendors that didn't qualify for the main results — grouped by reason
        </p>
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
