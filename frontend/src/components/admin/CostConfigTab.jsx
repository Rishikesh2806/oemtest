import { useState, useEffect } from "react";
import { api } from "../../App";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { toast } from "sonner";
import { 
  DollarSign, Save, RefreshCw, Loader2, 
  Layers, Wrench, Paintbrush, Flame, Settings
} from "lucide-react";

const SECTION_CONFIG = {
  material_rates: {
    label: "Material Rates",
    icon: Layers,
    rateKey: "rate_per_kg",
    rateLabel: "Rate/kg (INR)",
    color: "blue",
  },
  machine_hourly_rates: {
    label: "Machine Hourly Rates",
    icon: Wrench,
    rateKey: "rate_per_hour",
    rateLabel: "Rate/hr (INR)",
    color: "orange",
  },
  finishing_rates: {
    label: "Finishing Rates",
    icon: Paintbrush,
    rateKey: "rate_per_sq_dm",
    rateLabel: "Rate/sq dm (INR)",
    color: "purple",
  },
  tooling_rates: {
    label: "Tooling & Setup",
    icon: Settings,
    rateKey: "rate",
    rateLabel: "Rate (INR)",
    color: "slate",
  },
  heat_treatment_rates: {
    label: "Heat Treatment Rates",
    icon: Flame,
    rateKey: "rate_per_kg",
    rateLabel: "Rate/kg (INR)",
    color: "red",
  },
};

const SectionEditor = ({ sectionKey, data, onChange }) => {
  const cfg = SECTION_CONFIG[sectionKey];
  if (!cfg || !data) return null;

  const colorMap = {
    blue: "border-blue-200 bg-blue-50",
    orange: "border-orange-200 bg-orange-50",
    purple: "border-purple-200 bg-purple-50",
    slate: "border-slate-200 bg-slate-50",
    red: "border-red-200 bg-red-50",
  };

  const Icon = cfg.icon;

  return (
    <Card className={`border ${colorMap[cfg.color]}`}>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Icon className="w-4 h-4" />
          {cfg.label}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {Object.entries(data).map(([key, item]) => (
            <div key={key} className="flex items-center gap-2 p-2 bg-white rounded border">
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-slate-700 truncate">{item.name}</p>
                <p className="text-[10px] text-slate-400">{item.unit}</p>
              </div>
              <Input
                type="number"
                value={item[cfg.rateKey] ?? ""}
                onChange={(e) => {
                  const newData = { ...data };
                  newData[key] = { ...item, [cfg.rateKey]: parseFloat(e.target.value) || 0 };
                  onChange(sectionKey, newData);
                }}
                className="w-24 text-right text-sm font-mono"
                data-testid={`cost-rate-${sectionKey}-${key}`}
              />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};

export const CostConfigTab = () => {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);

  const fetchConfig = async () => {
    setLoading(true);
    try {
      const res = await api.get("/admin/cost-config");
      setConfig(res.data);
      setHasChanges(false);
    } catch (err) {
      toast.error("Failed to load cost config");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchConfig(); }, []);

  const handleSectionChange = (sectionKey, newData) => {
    setConfig(prev => ({ ...prev, [sectionKey]: newData }));
    setHasChanges(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.put("/admin/cost-config", {
        material_rates: config.material_rates,
        machine_hourly_rates: config.machine_hourly_rates,
        finishing_rates: config.finishing_rates,
        tooling_rates: config.tooling_rates,
        heat_treatment_rates: config.heat_treatment_rates,
      });
      toast.success("Cost configuration saved");
      setHasChanges(false);
    } catch (err) {
      toast.error("Failed to save config");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-orange-600" />
        <span className="ml-2 text-slate-500">Loading cost configuration...</span>
      </div>
    );
  }

  return (
    <div className="space-y-4" data-testid="cost-config-tab">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <DollarSign className="w-5 h-5 text-orange-600" />
            Cost Configuration
          </h2>
          <p className="text-sm text-slate-500">
            Set rates used for AI cost estimation. Changes apply to all new estimates.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={fetchConfig} data-testid="cost-config-refresh">
            <RefreshCw className="w-3.5 h-3.5 mr-1" /> Refresh
          </Button>
          <Button 
            size="sm" 
            onClick={handleSave} 
            disabled={!hasChanges || saving}
            className="bg-orange-600 hover:bg-orange-700"
            data-testid="cost-config-save"
          >
            {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1" /> : <Save className="w-3.5 h-3.5 mr-1" />}
            Save Changes
          </Button>
        </div>
      </div>

      {config?.updated_at && (
        <p className="text-xs text-slate-400">
          Last updated: {new Date(config.updated_at).toLocaleString()}
        </p>
      )}

      {Object.keys(SECTION_CONFIG).map(sectionKey => (
        <SectionEditor
          key={sectionKey}
          sectionKey={sectionKey}
          data={config?.[sectionKey]}
          onChange={handleSectionChange}
        />
      ))}
    </div>
  );
};

export default CostConfigTab;
