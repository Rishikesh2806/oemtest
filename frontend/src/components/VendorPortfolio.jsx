import { useState, useEffect, useRef, useCallback } from "react";
import { api } from "../App";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Badge } from "../components/ui/badge";
import {
  Upload, Loader2, X, Camera, Pencil, Trash2, Image as ImageIcon,
  Shield, Check, ChevronDown, Sparkles, Layers, Wrench, Palette, BarChart3
} from "lucide-react";

const MAX_PHOTOS = 20;

const FIELD_OPTIONS = {
  manufacturing_process: ["CNC machining", "casting", "welding", "sheet metal", "3D printing", "injection molding", "forging", "stamping", "laser cutting", "turning", "milling", "grinding", "EDM"],
  material: ["aluminum", "steel", "stainless steel", "plastic", "rubber", "brass", "titanium", "copper", "carbon fiber", "cast iron", "zinc", "nickel alloy"],
  part_category: ["bracket", "housing", "shaft", "enclosure", "gear", "panel", "tube", "fitting", "plate", "flange", "bushing", "valve", "coupling", "frame"],
  surface_finish: ["raw", "polished", "anodized", "powder coated", "painted", "plated", "brushed", "sandblasted", "chrome", "galvanized"],
  complexity: ["low", "medium", "high"]
};

const FIELD_META = {
  manufacturing_process: { label: "Process", icon: Wrench, color: "bg-blue-50 text-blue-700 border-blue-200 hover:bg-blue-100" },
  material: { label: "Material", icon: Layers, color: "bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100" },
  part_category: { label: "Category", icon: Sparkles, color: "bg-violet-50 text-violet-700 border-violet-200 hover:bg-violet-100" },
  surface_finish: { label: "Finish", icon: Palette, color: "bg-amber-50 text-amber-700 border-amber-200 hover:bg-amber-100" },
  complexity: { label: "Complexity", icon: BarChart3, color: "bg-rose-50 text-rose-700 border-rose-200 hover:bg-rose-100" }
};

const PortfolioStrength = ({ portfolio }) => {
  const categories = new Set(portfolio.map(p => p.part_category).filter(Boolean));
  const processes = new Set(portfolio.map(p => p.manufacturing_process).filter(Boolean));
  const materials = new Set(portfolio.map(p => p.material).filter(Boolean));
  const totalUnique = categories.size + processes.size + materials.size;
  const strength = Math.min(100, Math.round((totalUnique / 15) * 100));
  const color = strength >= 70 ? "bg-green-500" : strength >= 40 ? "bg-orange-500" : "bg-red-500";
  const label = strength >= 70 ? "Strong" : strength >= 40 ? "Growing" : "Getting Started";

  return (
    <div data-testid="portfolio-strength" className="bg-slate-50 border border-slate-200 rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Shield className="w-4 h-4 text-slate-600" />
          <span className="text-sm font-semibold text-slate-700">Portfolio Strength</span>
        </div>
        <span className={`text-xs font-bold px-2.5 py-1 rounded-full text-white ${color}`}>{label}</span>
      </div>
      <div className="w-full bg-slate-200 rounded-full h-2 mb-3">
        <div className={`h-2 rounded-full transition-all duration-500 ${color}`} style={{ width: `${strength}%` }} />
      </div>
      <div className="grid grid-cols-3 gap-2 text-xs">
        {[
          { val: categories.size, label: "Categories" },
          { val: processes.size, label: "Processes" },
          { val: materials.size, label: "Materials" }
        ].map(s => (
          <div key={s.label} className="text-center p-2 bg-white rounded-lg border border-slate-100">
            <p className="font-bold text-slate-900 text-base">{s.val}</p>
            <p className="text-slate-500">{s.label}</p>
          </div>
        ))}
      </div>
    </div>
  );
};

const TagEditor = ({ field, value, options, onSave, onClose }) => {
  const [selected, setSelected] = useState(value || "");
  const [custom, setCustom] = useState("");
  const ref = useRef(null);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (ref.current && !ref.current.contains(e.target)) onClose();
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [onClose]);

  const meta = FIELD_META[field];

  return (
    <div ref={ref} className="fixed inset-0 z-[60] flex items-center justify-center bg-black/30 backdrop-blur-[2px]" onClick={e => e.stopPropagation()}>
      <div className="bg-white rounded-xl shadow-2xl border border-slate-200 w-[340px] max-h-[80vh] overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            {meta?.icon && <meta.icon className="w-4 h-4 text-slate-500" />}
            <h3 className="text-sm font-semibold text-slate-800">Edit {meta?.label || field.replace(/_/g, " ")}</h3>
          </div>
          <button onClick={onClose} className="p-1 rounded-md hover:bg-slate-100 text-slate-400"><X className="w-4 h-4" /></button>
        </div>
        <div className="p-4 space-y-3 max-h-[50vh] overflow-y-auto">
          <div className="flex flex-wrap gap-2">
            {options.map(opt => (
              <button
                key={opt}
                onClick={() => { setSelected(opt); setCustom(""); }}
                className={`text-xs px-3 py-1.5 rounded-lg border font-medium transition-all ${
                  selected === opt
                    ? "bg-orange-50 border-orange-400 text-orange-700 ring-1 ring-orange-300"
                    : "bg-slate-50 border-slate-200 text-slate-600 hover:border-slate-300 hover:bg-slate-100"
                }`}
              >
                {selected === opt && <Check className="w-3 h-3 inline mr-1" />}
                {opt}
              </button>
            ))}
          </div>
          <div className="relative">
            <Input
              placeholder="Or type a custom value..."
              value={custom}
              onChange={e => { setCustom(e.target.value); setSelected(e.target.value); }}
              className="text-sm h-9 pr-8"
            />
          </div>
        </div>
        <div className="px-4 py-3 border-t border-slate-100 flex gap-2">
          <Button size="sm" className="flex-1 bg-orange-600 hover:bg-orange-700 h-9" disabled={!selected.trim()} onClick={() => onSave(selected)}>
            Save
          </Button>
          <Button size="sm" variant="outline" className="h-9" onClick={onClose}>Cancel</Button>
        </div>
      </div>
    </div>
  );
};

const EditableTag = ({ field, value, portfolioId, onUpdate }) => {
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const meta = FIELD_META[field];
  const options = FIELD_OPTIONS[field] || [];
  const FieldIcon = meta?.icon;

  const handleSave = async (newValue) => {
    setSaving(true);
    try {
      await api.put(`/vendor/portfolio/${portfolioId}`, { [field]: newValue });
      onUpdate(portfolioId, { [field]: newValue });
      toast.success(`${meta?.label || field} updated`);
    } catch {
      toast.error("Failed to update");
    }
    setSaving(false);
    setEditing(false);
  };

  return (
    <>
      <button
        data-testid={`tag-${field}-${portfolioId}`}
        onClick={() => setEditing(true)}
        className={`group/tag inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1.5 rounded-lg border transition-all cursor-pointer ${meta?.color || "bg-slate-50 text-slate-700 border-slate-200"}`}
      >
        {FieldIcon && <FieldIcon className="w-3 h-3 opacity-70" />}
        <span className="truncate max-w-[120px]">{value || "Set " + (meta?.label || field)}</span>
        {saving ? <Loader2 className="w-3 h-3 animate-spin ml-0.5" /> : <Pencil className="w-3 h-3 opacity-0 group-hover/tag:opacity-60 transition-opacity ml-0.5" />}
      </button>
      {editing && (
        <TagEditor
          field={field}
          value={value}
          options={options}
          onSave={handleSave}
          onClose={() => setEditing(false)}
        />
      )}
    </>
  );
};

const PortfolioCard = ({ item, onDelete, onUpdate }) => {
  const [deleting, setDeleting] = useState(false);
  const [imgError, setImgError] = useState(false);

  const handleDelete = async () => {
    if (!window.confirm("Remove this portfolio photo?")) return;
    setDeleting(true);
    try {
      await api.delete(`/vendor/portfolio/${item.portfolio_id}`);
      onDelete(item.portfolio_id);
      toast.success("Photo removed");
    } catch {
      toast.error("Failed to delete");
      setDeleting(false);
    }
  };

  const complexityColor = {
    low: "bg-green-50 text-green-700 border-green-200",
    medium: "bg-amber-50 text-amber-700 border-amber-200",
    high: "bg-red-50 text-red-700 border-red-200"
  };

  return (
    <div data-testid={`portfolio-card-${item.portfolio_id}`} className="group bg-white border border-slate-200 rounded-xl overflow-hidden hover:shadow-lg hover:border-slate-300 transition-all duration-200">
      {/* Image */}
      <div className="relative aspect-[4/3] bg-slate-100 overflow-hidden">
        {imgError ? (
          <div className="w-full h-full flex items-center justify-center bg-slate-50">
            <ImageIcon className="w-10 h-10 text-slate-300" />
          </div>
        ) : (
          <img
            src={item.photo_url}
            alt={item.part_category || "Portfolio item"}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            loading="lazy"
            onError={() => setImgError(true)}
          />
        )}
        {/* Delete button */}
        <button
          onClick={handleDelete}
          disabled={deleting}
          className="absolute top-2 right-2 w-8 h-8 bg-white/90 hover:bg-red-500 hover:text-white text-slate-500 rounded-lg flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all shadow-sm border border-slate-200"
          data-testid={`delete-${item.portfolio_id}`}
        >
          {deleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
        </button>
        {/* Complexity badge on image */}
        {item.complexity && (
          <div className={`absolute top-2 left-2 text-[10px] font-bold uppercase px-2 py-0.5 rounded-md border ${complexityColor[item.complexity] || "bg-slate-50 text-slate-600 border-slate-200"}`}>
            {item.complexity}
          </div>
        )}
      </div>

      {/* Tags section */}
      <div className="p-3 space-y-2.5">
        {/* Primary tags row */}
        <div className="flex flex-wrap gap-1.5">
          <EditableTag field="part_category" value={item.part_category} portfolioId={item.portfolio_id} onUpdate={onUpdate} />
          <EditableTag field="manufacturing_process" value={item.manufacturing_process} portfolioId={item.portfolio_id} onUpdate={onUpdate} />
        </div>
        {/* Secondary tags row */}
        <div className="flex flex-wrap gap-1.5">
          <EditableTag field="material" value={item.material} portfolioId={item.portfolio_id} onUpdate={onUpdate} />
          <EditableTag field="surface_finish" value={item.surface_finish} portfolioId={item.portfolio_id} onUpdate={onUpdate} />
          <EditableTag field="complexity" value={item.complexity} portfolioId={item.portfolio_id} onUpdate={onUpdate} />
        </div>

        {/* Notable features */}
        {item.notable_features?.length > 0 && (
          <div className="pt-1.5 border-t border-slate-100">
            <p className="text-[10px] font-medium text-slate-400 uppercase tracking-wide mb-1">Features</p>
            <div className="flex flex-wrap gap-1">
              {item.notable_features.map((f, i) => (
                <span key={i} className="text-[11px] text-slate-500 bg-slate-50 border border-slate-100 px-2 py-0.5 rounded-md">{f}</span>
              ))}
            </div>
          </div>
        )}

        {/* Industry fit */}
        {item.industry_fit?.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {item.industry_fit.map((ind, i) => (
              <Badge key={i} variant="outline" className="text-[10px] px-1.5 py-0 h-5 font-normal text-slate-500 border-slate-200">
                {ind}
              </Badge>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

const IndexingCard = () => (
  <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
    <div className="aspect-[4/3] bg-slate-50 flex items-center justify-center">
      <div className="text-center">
        <Loader2 className="w-8 h-8 text-orange-500 animate-spin mx-auto mb-2" />
        <p className="text-xs text-slate-600 font-medium">AI Analyzing...</p>
        <p className="text-[11px] text-slate-400 mt-0.5">Detecting properties</p>
      </div>
    </div>
    <div className="p-3 space-y-2">
      <div className="flex gap-1.5">
        <div className="h-6 bg-slate-100 rounded-lg w-20 animate-pulse" />
        <div className="h-6 bg-slate-100 rounded-lg w-24 animate-pulse" />
      </div>
      <div className="flex gap-1.5">
        <div className="h-6 bg-slate-100 rounded-lg w-16 animate-pulse" />
        <div className="h-6 bg-slate-100 rounded-lg w-14 animate-pulse" />
      </div>
    </div>
  </div>
);

const VendorPortfolio = () => {
  const [portfolio, setPortfolio] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(0);
  const fileRef = useRef(null);

  const fetchPortfolio = useCallback(async () => {
    try {
      const res = await api.get("/vendor/portfolio");
      setPortfolio(res.data.portfolio || []);
    } catch {
      // Silently handle
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchPortfolio(); }, [fetchPortfolio]);

  const handleUpload = async (e) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    const remaining = MAX_PHOTOS - portfolio.length;
    if (remaining <= 0) { toast.error(`Maximum ${MAX_PHOTOS} photos allowed`); return; }

    const validFiles = files.slice(0, remaining).filter(f => {
      if (!["image/jpeg", "image/png", "image/webp"].includes(f.type)) { toast.error(`${f.name}: Only JPG, PNG, WEBP allowed`); return false; }
      if (f.size > 10 * 1024 * 1024) { toast.error(`${f.name}: Must be under 10MB`); return false; }
      return true;
    });
    if (!validFiles.length) return;
    setUploading(validFiles.length);

    for (const file of validFiles) {
      try {
        const formData = new FormData();
        formData.append("file", file);
        const res = await api.post("/vendor/portfolio", formData, { headers: { "Content-Type": "multipart/form-data" } });
        setPortfolio(prev => [res.data, ...prev]);
        setUploading(prev => prev - 1);
      } catch {
        toast.error(`Failed to upload ${file.name}`);
        setUploading(prev => prev - 1);
      }
    }
    if (fileRef.current) fileRef.current.value = "";
  };

  const handleDelete = (id) => setPortfolio(prev => prev.filter(p => p.portfolio_id !== id));
  const handleUpdate = (id, updates) => setPortfolio(prev => prev.map(p => p.portfolio_id === id ? { ...p, ...updates } : p));

  if (loading) {
    return (
      <Card className="border-slate-200">
        <CardContent className="flex items-center justify-center h-32">
          <Loader2 className="w-6 h-6 animate-spin text-orange-600" />
        </CardContent>
      </Card>
    );
  }

  return (
    <div data-testid="vendor-portfolio-section" className="space-y-4">
      <Card className="border-slate-200">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="font-heading text-lg flex items-center gap-2">
            <Camera className="w-5 h-5 text-orange-600" /> Portfolio
            <span className="text-sm font-normal text-slate-400">({portfolio.length}/{MAX_PHOTOS})</span>
          </CardTitle>
          <Button
            size="sm"
            className="bg-orange-600 hover:bg-orange-700"
            onClick={() => fileRef.current?.click()}
            disabled={uploading > 0 || portfolio.length >= MAX_PHOTOS}
            data-testid="upload-portfolio-btn"
          >
            <Upload className="w-4 h-4 mr-1" />
            {uploading > 0 ? `Uploading ${uploading}...` : "Upload Photos"}
          </Button>
          <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp" multiple onChange={handleUpload} className="hidden" />
        </CardHeader>
        <CardContent className="space-y-4">
          <PortfolioStrength portfolio={portfolio} />

          {/* Hint about editing */}
          {portfolio.length > 0 && (
            <p className="text-xs text-slate-400 flex items-center gap-1.5">
              <Pencil className="w-3 h-3" /> Click any tag to edit AI-detected properties
            </p>
          )}

          {portfolio.length === 0 && uploading === 0 ? (
            <div
              className="border-2 border-dashed border-slate-200 rounded-xl p-8 text-center cursor-pointer hover:border-orange-300 hover:bg-orange-50/30 transition-all"
              onClick={() => fileRef.current?.click()}
              data-testid="portfolio-dropzone"
            >
              <ImageIcon className="w-10 h-10 text-slate-300 mx-auto mb-3" />
              <p className="text-sm font-medium text-slate-600">Upload photos of your past work</p>
              <p className="text-xs text-slate-400 mt-1">JPG, PNG, or WEBP up to 10MB each. AI will auto-analyze each photo.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {Array.from({ length: uploading }).map((_, i) => <IndexingCard key={`indexing-${i}`} />)}
              {portfolio.map(item => (
                <PortfolioCard key={item.portfolio_id} item={item} onDelete={handleDelete} onUpdate={handleUpdate} />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default VendorPortfolio;
