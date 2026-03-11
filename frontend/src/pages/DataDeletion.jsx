import React, { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import { api } from '../App';
import { 
  Trash2, Shield, CheckCircle, Clock, AlertCircle, 
  ArrowLeft, Mail, Phone, RefreshCw, Search
} from 'lucide-react';

export default function DataDeletion() {
  const [searchParams] = useSearchParams();
  const codeFromUrl = searchParams.get('code');
  
  const [mode, setMode] = useState(codeFromUrl ? 'status' : 'request'); // 'request' or 'status'
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [confirmationCode, setConfirmationCode] = useState(codeFromUrl || '');
  const [statusResult, setStatusResult] = useState(null);
  
  // Form state
  const [formData, setFormData] = useState({
    phone: '',
    email: '',
    reason: ''
  });

  useEffect(() => {
    if (codeFromUrl) {
      checkStatus(codeFromUrl);
    }
  }, [codeFromUrl]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.phone && !formData.email) {
      toast.error('Please provide either phone number or email');
      return;
    }
    
    setLoading(true);
    try {
      const response = await api.post('/data-deletion/request', formData);
      setConfirmationCode(response.data.confirmation_code);
      setSubmitted(true);
      toast.success('Data deletion request submitted');
    } catch (error) {
      console.error('Error submitting request:', error);
      toast.error(error.response?.data?.detail || 'Failed to submit request');
    } finally {
      setLoading(false);
    }
  };

  const checkStatus = async (code) => {
    if (!code) {
      toast.error('Please enter a confirmation code');
      return;
    }
    
    setLoading(true);
    try {
      const response = await api.get(`/data-deletion/status/${code}`);
      setStatusResult(response.data);
    } catch (error) {
      console.error('Error checking status:', error);
      toast.error('Deletion request not found');
      setStatusResult(null);
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-12 h-12 text-green-500" />;
      case 'in_progress':
        return <RefreshCw className="w-12 h-12 text-blue-500 animate-spin" />;
      case 'pending':
        return <Clock className="w-12 h-12 text-amber-500" />;
      case 'failed':
        return <AlertCircle className="w-12 h-12 text-red-500" />;
      default:
        return <Clock className="w-12 h-12 text-slate-400" />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed':
        return 'bg-green-50 border-green-200';
      case 'in_progress':
        return 'bg-blue-50 border-blue-200';
      case 'pending':
        return 'bg-amber-50 border-amber-200';
      case 'failed':
        return 'bg-red-50 border-red-200';
      default:
        return 'bg-slate-50 border-slate-200';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <img src="/logo.png" alt="OEMLinker" className="h-8" onError={(e) => e.target.style.display = 'none'} />
            <span className="text-xl font-bold text-slate-800">OEMLinker</span>
          </Link>
          <Link to="/privacy-policy">
            <Button variant="outline" size="sm">
              <Shield className="w-4 h-4 mr-2" />
              Privacy Policy
            </Button>
          </Link>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-8">
        {/* Back Link */}
        <Link to="/privacy-policy" className="inline-flex items-center text-slate-600 hover:text-slate-800 mb-6">
          <ArrowLeft className="w-4 h-4 mr-1" />
          Back to Privacy Policy
        </Link>

        <div className="mb-8">
          <h1 className="text-3xl font-bold text-slate-800 mb-2 flex items-center gap-3">
            <Trash2 className="w-8 h-8 text-orange-600" />
            Data Deletion Request
          </h1>
          <p className="text-slate-600">
            Request deletion of your personal data from OEMLinker
          </p>
        </div>

        {/* Mode Toggle */}
        <div className="flex gap-2 mb-6">
          <Button
            variant={mode === 'request' ? 'default' : 'outline'}
            onClick={() => { setMode('request'); setStatusResult(null); }}
            className={mode === 'request' ? 'bg-orange-600 hover:bg-orange-700' : ''}
          >
            <Trash2 className="w-4 h-4 mr-2" />
            New Request
          </Button>
          <Button
            variant={mode === 'status' ? 'default' : 'outline'}
            onClick={() => setMode('status')}
            className={mode === 'status' ? 'bg-orange-600 hover:bg-orange-700' : ''}
          >
            <Search className="w-4 h-4 mr-2" />
            Check Status
          </Button>
        </div>

        {mode === 'request' ? (
          <>
            {!submitted ? (
              <Card>
                <CardHeader>
                  <CardTitle>Request Data Deletion</CardTitle>
                </CardHeader>
                <CardContent>
                  <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                      <Label htmlFor="phone">Phone Number (WhatsApp)</Label>
                      <div className="relative mt-1">
                        <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                        <Input
                          id="phone"
                          type="tel"
                          placeholder="+91 98765 43210"
                          value={formData.phone}
                          onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                          className="pl-10"
                        />
                      </div>
                      <p className="text-xs text-slate-500 mt-1">
                        Enter the phone number used for WhatsApp communication
                      </p>
                    </div>

                    <div className="relative">
                      <div className="absolute inset-0 flex items-center">
                        <span className="w-full border-t" />
                      </div>
                      <div className="relative flex justify-center text-xs uppercase">
                        <span className="bg-white px-2 text-slate-500">Or</span>
                      </div>
                    </div>

                    <div>
                      <Label htmlFor="email">Email Address</Label>
                      <div className="relative mt-1">
                        <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                        <Input
                          id="email"
                          type="email"
                          placeholder="you@company.com"
                          value={formData.email}
                          onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                          className="pl-10"
                        />
                      </div>
                    </div>

                    <div>
                      <Label htmlFor="reason">Reason for Deletion (Optional)</Label>
                      <Textarea
                        id="reason"
                        placeholder="Let us know why you're requesting data deletion..."
                        value={formData.reason}
                        onChange={(e) => setFormData({ ...formData, reason: e.target.value })}
                        rows={3}
                        className="mt-1"
                      />
                    </div>

                    <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                      <h4 className="font-medium text-amber-800 mb-2">What will be deleted:</h4>
                      <ul className="text-sm text-amber-700 space-y-1">
                        <li>• Your account and profile information</li>
                        <li>• All WhatsApp messages and media</li>
                        <li>• Machine listings (for vendors)</li>
                        <li>• Quotes and order history</li>
                      </ul>
                      <p className="text-sm text-amber-800 mt-3 font-medium">
                        This action cannot be undone.
                      </p>
                    </div>

                    <Button
                      type="submit"
                      className="w-full bg-red-600 hover:bg-red-700"
                      disabled={loading}
                    >
                      {loading ? (
                        <>
                          <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                          Processing...
                        </>
                      ) : (
                        <>
                          <Trash2 className="w-4 h-4 mr-2" />
                          Submit Deletion Request
                        </>
                      )}
                    </Button>
                  </form>
                </CardContent>
              </Card>
            ) : (
              <Card className="border-green-200 bg-green-50">
                <CardContent className="p-8 text-center">
                  <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
                  <h2 className="text-2xl font-bold text-slate-800 mb-2">
                    Request Submitted
                  </h2>
                  <p className="text-slate-600 mb-4">
                    Your data deletion request has been received.
                  </p>
                  <div className="bg-white rounded-lg p-4 border border-green-200 mb-4">
                    <p className="text-sm text-slate-500 mb-1">Your confirmation code:</p>
                    <p className="text-2xl font-mono font-bold text-slate-800">
                      {confirmationCode}
                    </p>
                  </div>
                  <p className="text-sm text-slate-600 mb-4">
                    Save this code to check the status of your request. 
                    You will receive confirmation once your data has been deleted.
                  </p>
                  <div className="flex gap-2 justify-center">
                    <Button
                      variant="outline"
                      onClick={() => {
                        setMode('status');
                        checkStatus(confirmationCode);
                      }}
                    >
                      Check Status
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => {
                        setSubmitted(false);
                        setFormData({ phone: '', email: '', reason: '' });
                      }}
                    >
                      New Request
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}
          </>
        ) : (
          <Card>
            <CardHeader>
              <CardTitle>Check Deletion Status</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <Label htmlFor="code">Confirmation Code</Label>
                  <div className="flex gap-2 mt-1">
                    <Input
                      id="code"
                      placeholder="DEL_XXXXXXXXXXXX"
                      value={confirmationCode}
                      onChange={(e) => setConfirmationCode(e.target.value.toUpperCase())}
                      className="font-mono"
                    />
                    <Button 
                      onClick={() => checkStatus(confirmationCode)}
                      disabled={loading}
                    >
                      {loading ? (
                        <RefreshCw className="w-4 h-4 animate-spin" />
                      ) : (
                        <Search className="w-4 h-4" />
                      )}
                    </Button>
                  </div>
                </div>

                {statusResult && (
                  <div className={`rounded-lg border p-6 ${getStatusColor(statusResult.status)}`}>
                    <div className="flex items-center gap-4">
                      {getStatusIcon(statusResult.status)}
                      <div>
                        <h3 className="text-lg font-semibold text-slate-800 capitalize">
                          {statusResult.status.replace('_', ' ')}
                        </h3>
                        <p className="text-slate-600">{statusResult.message}</p>
                      </div>
                    </div>
                    
                    <div className="mt-4 pt-4 border-t border-slate-200 space-y-2 text-sm">
                      <p className="text-slate-600">
                        <strong>Confirmation Code:</strong> {statusResult.confirmation_code}
                      </p>
                      <p className="text-slate-600">
                        <strong>Requested:</strong> {new Date(statusResult.requested_at).toLocaleString()}
                      </p>
                      {statusResult.completed_at && (
                        <p className="text-slate-600">
                          <strong>Completed:</strong> {new Date(statusResult.completed_at).toLocaleString()}
                        </p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Info Section */}
        <Card className="mt-6">
          <CardContent className="p-6">
            <h3 className="font-semibold text-slate-800 mb-3">Data Deletion Information</h3>
            <div className="space-y-3 text-sm text-slate-600">
              <p>
                <strong>Processing Time:</strong> Data deletion requests are typically processed within 30 days.
              </p>
              <p>
                <strong>What's Deleted:</strong> All personal data including account information, 
                WhatsApp messages, machine listings, quotes, and order history.
              </p>
              <p>
                <strong>Retained Data:</strong> Some data may be retained for legal compliance 
                (e.g., tax records, transaction history) as required by law.
              </p>
              <p>
                <strong>Questions?</strong> Contact us at privacy@oemlinker.com
              </p>
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
