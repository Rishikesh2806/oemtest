import React, { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { api } from '../App';
import { 
  CheckCircle, Clock, AlertCircle, RefreshCw, 
  ArrowLeft, Shield, Trash2
} from 'lucide-react';

export default function DataDeletionStatus() {
  const [searchParams] = useSearchParams();
  const code = searchParams.get('code');
  
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (code) {
      fetchStatus();
    } else {
      setLoading(false);
      setError('No confirmation code provided');
    }
  }, [code]);

  const fetchStatus = async () => {
    try {
      const response = await api.get(`/data-deletion/status/${code}`);
      setStatus(response.data);
    } catch (err) {
      setError('Deletion request not found');
    } finally {
      setLoading(false);
    }
  };

  const getStatusDisplay = (statusValue) => {
    switch (statusValue) {
      case 'completed':
        return {
          icon: <CheckCircle className="w-16 h-16 text-green-500" />,
          title: 'Deletion Complete',
          color: 'bg-green-50 border-green-200',
          textColor: 'text-green-800'
        };
      case 'in_progress':
        return {
          icon: <RefreshCw className="w-16 h-16 text-blue-500 animate-spin" />,
          title: 'Deletion In Progress',
          color: 'bg-blue-50 border-blue-200',
          textColor: 'text-blue-800'
        };
      case 'pending':
        return {
          icon: <Clock className="w-16 h-16 text-amber-500" />,
          title: 'Request Pending',
          color: 'bg-amber-50 border-amber-200',
          textColor: 'text-amber-800'
        };
      case 'failed':
        return {
          icon: <AlertCircle className="w-16 h-16 text-red-500" />,
          title: 'Deletion Failed',
          color: 'bg-red-50 border-red-200',
          textColor: 'text-red-800'
        };
      default:
        return {
          icon: <Clock className="w-16 h-16 text-slate-400" />,
          title: 'Unknown Status',
          color: 'bg-slate-50 border-slate-200',
          textColor: 'text-slate-800'
        };
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
      {/* Header */}
      <header className="bg-white border-b border-slate-200">
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
        <Link to="/data-deletion" className="inline-flex items-center text-slate-600 hover:text-slate-800 mb-6">
          <ArrowLeft className="w-4 h-4 mr-1" />
          Back to Data Deletion
        </Link>

        <h1 className="text-2xl font-bold text-slate-800 mb-6 flex items-center gap-3">
          <Trash2 className="w-7 h-7 text-orange-600" />
          Data Deletion Status
        </h1>

        {loading ? (
          <Card>
            <CardContent className="p-12 text-center">
              <RefreshCw className="w-12 h-12 text-slate-400 animate-spin mx-auto mb-4" />
              <p className="text-slate-600">Loading status...</p>
            </CardContent>
          </Card>
        ) : error ? (
          <Card className="border-red-200 bg-red-50">
            <CardContent className="p-8 text-center">
              <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-slate-800 mb-2">Request Not Found</h2>
              <p className="text-slate-600 mb-4">{error}</p>
              <Link to="/data-deletion">
                <Button>Submit New Request</Button>
              </Link>
            </CardContent>
          </Card>
        ) : status ? (
          <Card className={`border ${getStatusDisplay(status.status).color}`}>
            <CardContent className="p-8 text-center">
              <div className="mb-4">
                {getStatusDisplay(status.status).icon}
              </div>
              <h2 className={`text-2xl font-bold mb-2 ${getStatusDisplay(status.status).textColor}`}>
                {getStatusDisplay(status.status).title}
              </h2>
              <p className="text-slate-600 mb-6">{status.message}</p>
              
              <div className="bg-white rounded-lg p-4 border text-left space-y-3">
                <div>
                  <p className="text-sm text-slate-500">Confirmation Code</p>
                  <p className="font-mono font-bold text-slate-800">{status.confirmation_code}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-500">Requested On</p>
                  <p className="text-slate-800">
                    {new Date(status.requested_at).toLocaleDateString('en-US', {
                      weekday: 'long',
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </p>
                </div>
                {status.completed_at && (
                  <div>
                    <p className="text-sm text-slate-500">Completed On</p>
                    <p className="text-slate-800">
                      {new Date(status.completed_at).toLocaleDateString('en-US', {
                        weekday: 'long',
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit'
                      })}
                    </p>
                  </div>
                )}
              </div>

              <div className="mt-6 flex gap-2 justify-center">
                <Button variant="outline" onClick={fetchStatus}>
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Refresh Status
                </Button>
                <Link to="/privacy-policy">
                  <Button variant="outline">
                    <Shield className="w-4 h-4 mr-2" />
                    Privacy Policy
                  </Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        ) : null}

        {/* Contact Info */}
        <Card className="mt-6">
          <CardContent className="p-6">
            <h3 className="font-semibold text-slate-800 mb-2">Need Help?</h3>
            <p className="text-sm text-slate-600">
              If you have questions about your data deletion request, please contact us at{' '}
              <a href="mailto:privacy@oemlinker.com" className="text-orange-600 hover:underline">
                privacy@oemlinker.com
              </a>
            </p>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
