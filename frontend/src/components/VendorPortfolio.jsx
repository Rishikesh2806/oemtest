import { useState, useEffect, useRef, useCallback } from "react";
import { api } from "../App";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import {
  Upload, Loader2, X, Camera, CheckCircle2, Pencil, Trash2, Image as ImageIcon, Shield
} from "lucide-react";

const MAX_PHOTOS = 20;

const FIELD_OPTIONS = {
  manufacturing_process: ["CNC machining", "casting", "welding", "sheet metal", "3D printing", "injection molding", "forging", "stamping", "laser cutting", "turning", "milling", "grinding", "EDM"],
  material: ["aluminum", "steel", "stainless steel", "plastic", "rubber", "brass", "titanium", "copper", "carbon fiber", "cast iron", "zinc", "nickel alloy"],
  part_category: ["bracket", "housing", "shaft", "enclosure", "gear", "panel", "tube", "fitting", "plate", "flange", "bushing", "valve", "coupling", "frame"],
  surface_finish: ["raw", "polished", "anodized", "powder coated", "painted", "plated", "brushed", "sandblasted", "chrome", "galvanized"],
  complexity: ["low", "medium", "high"]
};

const PortfolioStrength = ({ portfolio }) => {
  const categories = new Set(portfolio.map(p => p.part_category).filter(Boolean));
  const processes = new Set(portfolio.map(p => p.manufacturing_process).filter(Boolean));
  const materials = new Set(portfolio.map(p => p.material).filter(Boolean));

  const totalUnique = categories.size + processes.size + materials.size;
  const maxPossible = 15;
  const strength = Math.min(100, Math.round((totalUnique / maxPossible) * 100));

  const getColor = () => {
    if (strength >= 70) return "bg-green-500";
    if (strength >= 40) return "bg-orange-500";
    return "bg-red-500";
  };

  const getLabel = () => {
    if (strength >= 70) return "Strong";
    if (strength >= 40) return "Growing";
    return "Getting Started";
  };

  return (
    <div data-testid="portfolio-strength" className="bg-white border border-slate-200 rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Shield className="w-4 h-4 text-slate-600" />
          <span className="text-sm font-semibold text-slate-700">Portfolio Strength</span>
        </div>
        <span className={`text-xs font-bold px-2 py-0.5 rounded-full text-white ${getColor()}`}>
          {getLabel()}
        </span>
      </div>
      <div className="w-full bg-slate-100 rounded-full h-2 mb-3">
        <div className={`h-2 rounded-full transition-all duration-500 ${getColor()}`} style={{ width: `${strength}%` }} />
      </div>
      <div className="grid grid-cols-3 gap-2 text-xs">
        <div className="text-center p-2 bg-slate-50 rounded-lg">
          <p className="font-bold text-slate-900 text-base">{categories.size}</p>
          <p className="text-slate-500">Categories</p>
        </div>
        <div className="text-center p-2 bg-slate-50 rounded-lg">
          <p className="font-bold text-slate-900 text-base">{processes.size}</p>
          <p className="text-slate-500">Processes</p>
        </div>
        <div className="text-center p-2 bg-slate-50 rounded-lg">
          <p className="font-bold text-slate-900 text-base">{materials.size}</p>
          <p className="text-slate-500">Materials</p>
        </div>
      </div>
    </div>
  );
};

const EditBadgePopover = ({ field, value, onSave, onClose }) => {
  const [selected, setSelected] = useState(value);
  const [custom, setCustom] = useState("");
  const options = FIELD_OPTIONS[field] || [];

  return (
    <div className="absolute z-50 top-full left-0 mt-1 bg-white border border-slate-200 rounded-lg shadow-xl p-3 min-w-[220px]" onClick={e => e.stopPropagation()}>
      <p className="text-xs font-semibold text-slate-500 uppercase mb-2">{field.replace("_", " ")}</p>
      <div className="flex flex-wrap gap-1.5 mb-2 max-h-32 overflow-y-auto">
        {options.map(opt => (
          <button
            key={opt}
            onClick={() => { setSelected(opt); setCustom(""); }}
            className={`text-xs px-2 py-1 rounded-full border transition-colors ${
              selected === opt ? "bg-orange-100 border-orange-400 text-orange-700" : "bg-slate-50 border-slate-200 text-slate-600 hover:border-slate-300"
            }`}
          >
            {opt}
          </button>
        ))}
      </div>
      <Input
        placeholder="Custom value..."
        value={custom}
        onChange={e => { setCustom(e.target.value); setSelected(e.target.value); }}
        className="text-xs h-7 mb-2"
      />
      <div className="flex gap-2">
        <Button size="sm" className="h-7 text-xs bg-orange-600 hover:bg-orange-700 flex-1" onClick={() => onSave(selected)}>Save</Button>
        <Button size="sm" variant="outline" className="h-7 text-xs" onClick={onClose}>Cancel</Button>
      </div>
    </div>
  );
};

const PortfolioCard = ({ item, onDelete, onUpdate }) => {
  const [editingField, setEditingField] = useState(null);
  const [deleting, setDeleting] = useState(false);

  const handleSave = async (field, value) => {
    try {
      await api.put(`/vendor/portfolio/${item.portfolio_id}`, { [field]: value });
      onUpdate(item.portfolio_id, { [field]: value });
      toast.success("Updated successfully");
    } catch {
      toast.error("Failed to update");
    }
    setEditingField(null);
  };

  const handleDelete = async () => {
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

  const Badge = ({ field, label }) => (
    <div className="relative">
      <button
        data-testid={`badge-${field}-${item.portfolio_id}`}
        onClick={(e) => { e.stopPropagation(); setEditingField(editingField === field ? null : field); }}
        className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full bg-slate-800/70 text-white backdrop-blur-sm hover:bg-slate-700/80 transition-colors cursor-pointer"
      >
        {label || "Unknown"}
        <Pencil className="w-2.5 h-2.5 opacity-60" />
      </button>
      {editingField === field && (
        <EditBadgePopover
          field={field}
          value={item[field] || ""}
          onSave={(val) => handleSave(field, val)}
          onClose={() => setEditingField(null)}
        />
      )}
    </div>
  );

  return (
    <div data-testid={`portfolio-card-${item.portfolio_id}`} className="group relative bg-white border border-slate-200 rounded-xl overflow-hidden hover:shadow-md transition-shadow">
      <div className="relative aspect-square bg-slate-100">
        <img src={item.photo_url} alt={item.part_category || "Portfolio"} className="w-full h-full object-cover" loading="lazy" />
        <button
          onClick={handleDelete}
          disabled={deleting}
          className="absolute top-2 right-2 w-7 h-7 bg-red-500/80 hover:bg-red-600 text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
          data-testid={`delete-${item.portfolio_id}`}
        >
          {deleting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
        </button>
        <div className="absolute bottom-2 left-2 right-2 flex flex-wrap gap-1">
          <Badge field="part_category" label={item.part_category} />
          <Badge field="manufacturing_process" label={item.manufacturing_process} />
        </div>
      </div>
      <div className="p-2.5 space-y-1.5">
        <div className="flex flex-wrap gap-1">
          <Badge field="material" label={item.material} />
          <Badge field="surface_finish" label={item.surface_finish} />
          <Badge field="complexity" label={item.complexity} />
        </div>
        {item.industry_fit?.length > 0 && (
          <p className="text-[10px] text-slate-400 truncate">{item.industry_fit.join(" / ")}</p>
        )}
      </div>
    </div>
  );
};

const IndexingCard = () => (
  <div className="bg-white border border-slate-200 rounded-xl overflow-hidden animate-pulse">
    <div className="aspect-square bg-slate-100 flex items-center justify-center">
      <div className="text-center">
        <Loader2 className="w-8 h-8 text-orange-500 animate-spin mx-auto mb-2" />
        <p className="text-xs text-slate-500 font-medium">Indexing...</p>
        <p className="text-[10px] text-slate-400">AI analyzing photo</p>
      </div>
    </div>
    <div className="p-2.5">
      <div className="h-4 bg-slate-100 rounded w-3/4" />
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
      // Silently handle - might not have portfolio yet
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchPortfolio(); }, [fetchPortfolio]);

  const handleUpload = async (e) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;

    const remaining = MAX_PHOTOS - portfolio.length;
    if (remaining <= 0) {
      toast.error(`Maximum ${MAX_PHOTOS} photos allowed`);
      return;
    }

    const validFiles = files.slice(0, remaining).filter(f => {
      if (!["image/jpeg", "image/png", "image/webp"].includes(f.type)) {
        toast.error(`${f.name}: Only JPG, PNG, WEBP allowed`);
        return false;
      }
      if (f.size > 10 * 1024 * 1024) {
        toast.error(`${f.name}: Must be under 10MB`);
        return false;
      }
      return true;
    });

    if (!validFiles.length) return;
    setUploading(validFiles.length);

    for (const file of validFiles) {
      try {
        const formData = new FormData();
        formData.append("file", file);
        const res = await api.post("/vendor/portfolio", formData, {
          headers: { "Content-Type": "multipart/form-data" }
        });
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

  const handleUpdate = (id, updates) => {
    setPortfolio(prev => prev.map(p => p.portfolio_id === id ? { ...p, ...updates } : p));
  };

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
          <input
            ref={fileRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            multiple
            onChange={handleUpload}
            className="hidden"
          />
        </CardHeader>
        <CardContent>
          <PortfolioStrength portfolio={portfolio} />

          {portfolio.length === 0 && uploading === 0 ? (
            <div
              className="mt-4 border-2 border-dashed border-slate-200 rounded-xl p-8 text-center cursor-pointer hover:border-orange-300 transition-colors"
              onClick={() => fileRef.current?.click()}
              data-testid="portfolio-dropzone"
            >
              <ImageIcon className="w-10 h-10 text-slate-300 mx-auto mb-3" />
              <p className="text-sm font-medium text-slate-600">Upload photos of your past work</p>
              <p className="text-xs text-slate-400 mt-1">JPG, PNG, or WEBP up to 10MB each. AI will auto-analyze each photo.</p>
            </div>
          ) : (
            <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
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
