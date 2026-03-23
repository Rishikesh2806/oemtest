import { useState, useEffect } from "react";
import { api } from "../../App";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Textarea } from "../ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "../ui/dialog";
import { Badge } from "../ui/badge";
import { Checkbox } from "../ui/checkbox";
import { toast } from "sonner";
import { 
  Shield, FileText, Plus, Edit, Trash2, Loader2, 
  RefreshCw, Star, Eye, CheckCircle2
} from "lucide-react";

const NDATemplatesTab = () => {
  const [loading, setLoading] = useState(true);
  const [templates, setTemplates] = useState([]);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  
  const [form, setForm] = useState({
    title: "",
    content: "",
    version: "1.0",
    is_default: false
  });

  useEffect(() => {
    fetchTemplates();
  }, []);

  const fetchTemplates = async () => {
    setLoading(true);
    try {
      const response = await api.get("/nda/templates");
      setTemplates(response.data.templates || []);
    } catch (error) {
      console.error("Failed to fetch templates:", error);
      toast.error("Failed to load NDA templates");
    } finally {
      setLoading(false);
    }
  };

  const openCreateModal = (template = null) => {
    if (template) {
      setSelectedTemplate(template);
      setForm({
        title: template.title,
        content: template.content,
        version: template.version,
        is_default: template.is_default
      });
    } else {
      setSelectedTemplate(null);
      setForm({
        title: "",
        content: getDefaultContent(),
        version: "1.0",
        is_default: false
      });
    }
    setShowCreateModal(true);
  };

  const getDefaultContent = () => {
    return `<h2>Non-Disclosure Agreement</h2>
<p>By accepting this agreement, you ("Receiving Party") agree to the following terms:</p>
<ol>
<li><strong>Confidential Information:</strong> All drawings, specifications, technical data, and business information shared through this platform are considered confidential.</li>
<li><strong>Non-Disclosure:</strong> You agree not to disclose, share, or distribute any confidential information to third parties without prior written consent from the disclosing party.</li>
<li><strong>Use Restriction:</strong> Confidential information shall only be used for the purpose of evaluating and responding to the Request for Quotation (RFQ).</li>
<li><strong>No Copying:</strong> You shall not copy, reproduce, or store confidential information except as necessary for the permitted purpose.</li>
<li><strong>Return/Destruction:</strong> Upon request or completion of the RFQ process, you agree to return or destroy all confidential materials.</li>
<li><strong>Duration:</strong> This agreement remains in effect for 3 years from the date of acceptance.</li>
<li><strong>Legal Compliance:</strong> You acknowledge that breach of this agreement may result in legal action and liability for damages.</li>
</ol>
<p><strong>By checking "I Agree" below, you confirm that you have read, understood, and agree to be bound by the terms of this Non-Disclosure Agreement.</strong></p>`;
  };

  const handleSave = async () => {
    if (!form.title || !form.content) {
      toast.error("Title and content are required");
      return;
    }

    setSubmitting(true);
    try {
      if (selectedTemplate) {
        await api.put(`/nda/templates/${selectedTemplate.nda_id}`, form);
        toast.success("Template updated successfully");
      } else {
        await api.post("/nda/templates", form);
        toast.success("Template created successfully");
      }
      setShowCreateModal(false);
      fetchTemplates();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to save template");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (ndaId) => {
    if (!confirm("Are you sure you want to delete this template?")) return;

    try {
      await api.delete(`/nda/templates/${ndaId}`);
      toast.success("Template deleted");
      fetchTemplates();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to delete template");
    }
  };

  const openPreview = (template) => {
    setSelectedTemplate(template);
    setShowPreviewModal(true);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-orange-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
            <Shield className="w-5 h-5 text-orange-600" />
            NDA Templates
          </h2>
          <p className="text-sm text-slate-500 mt-1">
            Manage non-disclosure agreement templates for RFQ protection
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={fetchTemplates}>
            <RefreshCw className="w-4 h-4 mr-1" /> Refresh
          </Button>
          <Button onClick={() => openCreateModal()} className="bg-orange-600 hover:bg-orange-700">
            <Plus className="w-4 h-4 mr-1" /> Create Template
          </Button>
        </div>
      </div>

      {/* Templates Grid */}
      {templates.length === 0 ? (
        <Card className="border-slate-200">
          <CardContent className="py-12 text-center">
            <Shield className="w-16 h-16 text-slate-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-slate-900 mb-2">No NDA Templates</h3>
            <p className="text-slate-500 mb-4">
              Create your first NDA template to protect buyer IP in RFQs.
            </p>
            <Button onClick={() => openCreateModal()} className="bg-orange-600 hover:bg-orange-700">
              <Plus className="w-4 h-4 mr-1" /> Create First Template
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {templates.map((template) => (
            <Card 
              key={template.nda_id}
              className={`border-slate-200 hover:shadow-md transition-all ${template.is_default ? 'ring-2 ring-orange-500' : ''}`}
            >
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <FileText className="w-5 h-5 text-slate-400" />
                    <CardTitle className="text-base">{template.title}</CardTitle>
                  </div>
                  {template.is_default && (
                    <Badge className="bg-orange-100 text-orange-700">
                      <Star className="w-3 h-3 mr-1" /> Default
                    </Badge>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-slate-500">Version</span>
                    <span className="font-mono">{template.version}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-slate-500">Created</span>
                    <span>{new Date(template.created_at).toLocaleDateString()}</span>
                  </div>
                  
                  <div className="flex gap-2 pt-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => openPreview(template)}
                      className="flex-1"
                    >
                      <Eye className="w-4 h-4 mr-1" /> Preview
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => openCreateModal(template)}
                    >
                      <Edit className="w-4 h-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDelete(template.nda_id)}
                      className="text-red-600 hover:bg-red-50"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create/Edit Modal */}
      <Dialog open={showCreateModal} onOpenChange={setShowCreateModal}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle>
              {selectedTemplate ? "Edit NDA Template" : "Create NDA Template"}
            </DialogTitle>
          </DialogHeader>

          <div className="flex-1 overflow-y-auto space-y-4 pr-2">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Title *</Label>
                <Input
                  placeholder="e.g., Standard NDA"
                  value={form.title}
                  onChange={(e) => setForm(prev => ({ ...prev, title: e.target.value }))}
                  className="mt-1"
                />
              </div>
              <div>
                <Label>Version</Label>
                <Input
                  placeholder="1.0"
                  value={form.version}
                  onChange={(e) => setForm(prev => ({ ...prev, version: e.target.value }))}
                  className="mt-1"
                />
              </div>
            </div>

            <div>
              <Label>Content (HTML) *</Label>
              <Textarea
                placeholder="Enter NDA content in HTML format..."
                value={form.content}
                onChange={(e) => setForm(prev => ({ ...prev, content: e.target.value }))}
                className="mt-1 font-mono text-sm"
                rows={15}
              />
              <p className="text-xs text-slate-500 mt-1">
                Use HTML tags like &lt;h2&gt;, &lt;p&gt;, &lt;ol&gt;, &lt;li&gt;, &lt;strong&gt; for formatting.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <Checkbox
                id="is-default"
                checked={form.is_default}
                onCheckedChange={(checked) => setForm(prev => ({ ...prev, is_default: checked }))}
              />
              <Label htmlFor="is-default" className="cursor-pointer">
                Set as default template (used when buyer doesn't specify a custom NDA)
              </Label>
            </div>

            {/* Preview */}
            <div>
              <Label className="flex items-center gap-2">
                <Eye className="w-4 h-4" /> Preview
              </Label>
              <div 
                className="mt-1 p-4 border rounded-lg bg-white prose prose-sm max-w-none max-h-48 overflow-y-auto"
                dangerouslySetInnerHTML={{ __html: form.content }}
              />
            </div>
          </div>

          <DialogFooter className="mt-4">
            <Button variant="outline" onClick={() => setShowCreateModal(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleSave}
              disabled={submitting}
              className="bg-orange-600 hover:bg-orange-700"
            >
              {submitting ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : null}
              {selectedTemplate ? "Update Template" : "Create Template"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Preview Modal */}
      <Dialog open={showPreviewModal} onOpenChange={setShowPreviewModal}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileText className="w-5 h-5 text-orange-600" />
              {selectedTemplate?.title}
              <Badge variant="outline" className="ml-2">v{selectedTemplate?.version}</Badge>
            </DialogTitle>
          </DialogHeader>

          <div 
            className="flex-1 overflow-y-auto p-4 border rounded-lg bg-white prose prose-sm max-w-none"
            dangerouslySetInnerHTML={{ __html: selectedTemplate?.content || "" }}
          />

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowPreviewModal(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default NDATemplatesTab;
