import { useState, useRef } from "react";
import { api } from "../App";
import { toast } from "sonner";
import { Button } from "../components/ui/button";
import {
  Upload, Loader2, Camera, AlertTriangle, CheckCircle2, Building2, Eye, Image as ImageIcon
} from "lucide-react";
import { Link } from "react-router-dom";

const MATCH_MODES = [
  { key: "drawing", label: "Drawing Specs" },
  { key: "visual", label: "Visual Similarity" },
  { key: "both", label: "Both Combined" }
];

const ScoreBar = ({ score }) => {
  const color = score >= 70 ? "bg-green-500" : score >= 40 ? "bg-orange-500" : "bg-slate-400";
  const textColor = score >= 70 ? "text-green-600" : score >= 40 ? "text-orange-600" : "text-slate-500";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2.5 bg-slate-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-700 ${color}`} style={{ width: `${score}%` }} />
      </div>
      <span className={`text-lg font-bold min-w-[48px] text-right ${textColor}`}>{score}%</span>
    </div>
  );
};

const VendorVisualCard = ({ vendor }) => (
  <div data-testid={`visual-match-${vendor.vendor_id}`} className="p-4 bg-white border border-slate-200 rounded-xl hover:shadow-sm transition-shadow">
    <div className="flex items-start gap-4">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <Building2 className="w-4 h-4 text-slate-400 shrink-0" />
          <p className="font-semibold text-slate-900 truncate">{vendor.company_name || vendor.vendor_id}</p>
        </div>
        <ScoreBar score={vendor.score} />

        {/* Portfolio Photos */}
        {vendor.portfolio_photos?.length > 0 && (
          <div className="flex gap-2 mt-3">
            {vendor.portfolio_photos.slice(0, 3).map((photo, i) => (
              <div key={i} className="w-20 h-20 rounded-lg overflow-hidden border border-slate-200 bg-slate-50 shrink-0">
                <img src={photo.photo_url} alt={photo.part_category || "Portfolio"} className="w-full h-full object-cover" loading="lazy" />
              </div>
            ))}
          </div>
        )}

        {/* Match Reasons - Green Tags */}
        {vendor.match_reasons?.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-3">
            {vendor.match_reasons.map((reason, i) => (
              <span key={i} className="inline-flex items-center gap-1 text-xs bg-green-50 text-green-700 border border-green-200 px-2 py-0.5 rounded-full">
                <CheckCircle2 className="w-3 h-3" />{reason}
              </span>
            ))}
          </div>
        )}

        {/* Gaps - Yellow Tags */}
        {vendor.gaps?.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-2">
            {vendor.gaps.map((gap, i) => (
              <span key={i} className="inline-flex items-center gap-1 text-xs bg-amber-50 text-amber-700 border border-amber-200 px-2 py-0.5 rounded-full">
                <AlertTriangle className="w-3 h-3" />{gap}
              </span>
            ))}
          </div>
        )}
      </div>

      <Link to={`/vendor-profile/${vendor.vendor_id}`}>
        <Button variant="outline" size="sm" className="shrink-0">
          <Eye className="w-3.5 h-3.5 mr-1" /> Profile
        </Button>
      </Link>
    </div>
  </div>
);

const VisualMatchSection = ({ rfq, drawingVendors }) => {
  const [mode, setMode] = useState("drawing");
  const [visualMatches, setVisualMatches] = useState(null);
  const [buyerReqs, setBuyerReqs] = useState(null);
  const [loading, setLoading] = useState(false);
  const [uploadedFile, setUploadedFile] = useState(null);
  const fileRef = useRef(null);

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      toast.error("Only JPG, PNG, WEBP allowed");
      return;
    }

    setUploadedFile(URL.createObjectURL(file));
    setLoading(true);

    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await api.post("/match/visual", formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });

      // Enrich visual matches with portfolio photos
      const enriched = await Promise.all(
        (res.data.matches || []).map(async (m) => {
          try {
            const pRes = await api.get(`/vendors/${m.vendor_id}/portfolio`);
            return { ...m, portfolio_photos: pRes.data.portfolio?.slice(0, 3) || [] };
          } catch {
            return { ...m, portfolio_photos: [] };
          }
        })
      );

      setVisualMatches(enriched);
      setBuyerReqs(res.data.buyer_requirements);
      setMode("visual");
      toast.success(`Analyzed & matched against ${res.data.total_vendors_evaluated} vendors`);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Visual matching failed");
      setUploadedFile(null);
    } finally {
      setLoading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  // Combine scores for "both" mode
  const getCombinedResults = () => {
    if (!visualMatches || !drawingVendors?.length) return [];

    const drawingMap = {};
    drawingVendors.forEach(v => {
      drawingMap[v.vendor_id] = v.suitability_score || 0;
    });

    const allVendorIds = new Set([
      ...visualMatches.map(v => v.vendor_id),
      ...drawingVendors.map(v => v.vendor_id)
    ]);

    return Array.from(allVendorIds).map(vid => {
      const visual = visualMatches.find(v => v.vendor_id === vid);
      const drawing = drawingVendors.find(v => v.vendor_id === vid);
      const vScore = visual?.score || 0;
      const dScore = drawing?.suitability_score || 0;
      const combined = Math.round((vScore + dScore) / 2);

      return {
        vendor_id: vid,
        company_name: visual?.company_name || drawing?.company_name || vid,
        score: combined,
        match_reasons: [
          ...(visual?.match_reasons || []),
          ...(drawing?.process_matches?.map(p => `Process: ${p}`) || []),
          drawing?.materials_match ? "Material match" : null,
          drawing?.tolerance_capable ? "Tolerance capable" : null
        ].filter(Boolean),
        gaps: visual?.gaps || [],
        portfolio_photos: visual?.portfolio_photos || []
      };
    }).sort((a, b) => b.score - a.score);
  };

  const getDisplayResults = () => {
    if (mode === "visual") return visualMatches || [];
    if (mode === "both") return getCombinedResults();
    return null; // drawing mode uses the existing UI
  };

  const showVisualUI = mode === "visual" || mode === "both";
  const results = getDisplayResults();

  return (
    <div data-testid="visual-match-section" className="space-y-4">
      {/* Mode Toggle */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-sm font-medium text-slate-500">Match by:</span>
        <div className="flex bg-slate-100 rounded-lg p-0.5">
          {MATCH_MODES.map(m => (
            <button
              key={m.key}
              data-testid={`match-mode-${m.key}`}
              onClick={() => setMode(m.key)}
              disabled={m.key !== "drawing" && !visualMatches}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                mode === m.key
                  ? "bg-white text-slate-900 shadow-sm"
                  : "text-slate-500 hover:text-slate-700 disabled:opacity-40 disabled:cursor-not-allowed"
              }`}
            >
              {m.label}
            </button>
          ))}
        </div>

        {/* Upload Button */}
        <Button
          size="sm"
          variant={visualMatches ? "outline" : "default"}
          className={visualMatches ? "" : "bg-orange-600 hover:bg-orange-700"}
          onClick={() => fileRef.current?.click()}
          disabled={loading}
          data-testid="visual-upload-btn"
        >
          {loading ? <Loader2 className="w-4 h-4 mr-1 animate-spin" /> : <Camera className="w-4 h-4 mr-1" />}
          {loading ? "Analyzing..." : visualMatches ? "Re-upload" : "Upload Photo for Visual Match"}
        </Button>
        <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp" onChange={handleUpload} className="hidden" />
      </div>

      {/* Buyer Requirements Preview */}
      {showVisualUI && buyerReqs && (
        <div className="bg-slate-50 rounded-lg p-3 flex items-start gap-3">
          {uploadedFile && (
            <img src={uploadedFile} alt="Uploaded" className="w-16 h-16 rounded-lg object-cover border border-slate-200 shrink-0" />
          )}
          <div className="text-xs space-y-1">
            <p className="font-semibold text-slate-700">AI-Detected Requirements:</p>
            <div className="flex flex-wrap gap-1.5">
              {buyerReqs.manufacturing_process && <span className="bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full border border-blue-200">{buyerReqs.manufacturing_process}</span>}
              {buyerReqs.material && <span className="bg-green-50 text-green-700 px-2 py-0.5 rounded-full border border-green-200">{buyerReqs.material}</span>}
              {buyerReqs.part_category && <span className="bg-purple-50 text-purple-700 px-2 py-0.5 rounded-full border border-purple-200">{buyerReqs.part_category}</span>}
              {buyerReqs.surface_finish && <span className="bg-orange-50 text-orange-700 px-2 py-0.5 rounded-full border border-orange-200">{buyerReqs.surface_finish}</span>}
              {buyerReqs.complexity && <span className="bg-slate-100 text-slate-700 px-2 py-0.5 rounded-full border border-slate-200">Complexity: {buyerReqs.complexity}</span>}
            </div>
          </div>
        </div>
      )}

      {/* Visual / Combined Results */}
      {showVisualUI && results && (
        <div className="space-y-3">
          {results.length === 0 ? (
            <div className="text-center py-8 text-slate-400">
              <ImageIcon className="w-10 h-10 mx-auto mb-2 opacity-50" />
              <p className="text-sm">No visual matches found. Vendors need portfolio photos to be matched.</p>
            </div>
          ) : (
            results.map(vendor => <VendorVisualCard key={vendor.vendor_id} vendor={vendor} />)
          )}
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="text-center py-12">
          <Loader2 className="w-8 h-8 text-orange-600 animate-spin mx-auto mb-3" />
          <p className="text-sm text-slate-600 font-medium">Analyzing your photo with AI...</p>
          <p className="text-xs text-slate-400 mt-1">Matching against vendor portfolios</p>
        </div>
      )}
    </div>
  );
};

export default VisualMatchSection;
