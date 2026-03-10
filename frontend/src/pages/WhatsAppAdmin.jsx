import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Badge } from '../components/ui/badge';
import { toast } from 'sonner';
import { MessageSquare, Send, CheckCircle, XCircle, Phone, RefreshCw, Bell, Inbox } from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function WhatsAppAdmin() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [sendingVoice, setSendingVoice] = useState(false);
  const [testNumber, setTestNumber] = useState('');
  const [testMessage, setTestMessage] = useState('Hello from OEMLinker! This is a test message.');
  const [sendResult, setSendResult] = useState(null);

  useEffect(() => {
    fetchStatus();
  }, []);

  const fetchStatus = async () => {
    try {
      const response = await fetch(`${API_URL}/api/whatsapp/status`);
      const data = await response.json();
      setStatus(data);
    } catch (error) {
      console.error('Failed to fetch WhatsApp status:', error);
      toast.error('Failed to fetch WhatsApp status');
    } finally {
      setLoading(false);
    }
  };

  const sendTestMessage = async () => {
    if (!testNumber || !testMessage) {
      toast.error('Please enter both phone number and message');
      return;
    }

    setSending(true);
    setSendResult(null);

    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/whatsapp/send`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          to_number: testNumber,
          message: testMessage
        })
      });

      let data;
      const text = await response.text();
      try {
        data = JSON.parse(text);
      } catch {
        data = { error: text || 'Invalid response from server' };
      }

      if (response.ok && data.success) {
        setSendResult({ success: true, messageId: data.message_id });
        toast.success(`Message sent! ID: ${data.message_id}`);
      } else {
        setSendResult({ success: false, error: data.detail || data.error || 'Failed to send' });
        toast.error(data.detail || data.error || 'Failed to send message');
      }
    } catch (error) {
      setSendResult({ success: false, error: error.message });
      toast.error(error.message);
    } finally {
      setSending(false);
    }
  };

  const sendVoiceMessage = async () => {
    if (!testNumber || !testMessage) {
      toast.error('Please enter both phone number and message');
      return;
    }

    setSendingVoice(true);
    setSendResult(null);

    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/whatsapp/send-voice`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          to_number: testNumber,
          message: testMessage
        })
      });

      let data;
      const text = await response.text();
      try {
        data = JSON.parse(text);
      } catch {
        data = { error: text || 'Invalid response from server' };
      }

      if (response.ok && data.success) {
        setSendResult({ success: true, messageId: data.message_id, isVoice: true, audioSize: data.audio_size_bytes });
        toast.success(`Voice message sent! Size: ${Math.round(data.audio_size_bytes / 1024)}KB`);
      } else {
        setSendResult({ success: false, error: data.detail || data.error || 'Failed to send' });
        toast.error(data.detail || data.error || 'Failed to send voice message');
      }
    } catch (error) {
      setSendResult({ success: false, error: error.message });
      toast.error(error.message);
    } finally {
      setSendingVoice(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-orange-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="whatsapp-admin-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">WhatsApp Integration</h1>
          <p className="text-slate-500">Manage WhatsApp Business messaging via Gupshup</p>
        </div>
        <div className="flex gap-2">
          <Link to="/admin/whatsapp/inbox">
            <Button className="bg-green-600 hover:bg-green-700" data-testid="open-inbox-btn">
              <Inbox className="w-4 h-4 mr-2" />
              Open Inbox
            </Button>
          </Link>
          <Button variant="outline" onClick={fetchStatus} data-testid="refresh-status-btn">
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh Status
          </Button>
        </div>
      </div>

      {/* Status Card */}
      <Card data-testid="whatsapp-status-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-green-600" />
            Integration Status
          </CardTitle>
          <CardDescription>Gupshup WhatsApp Business API connection status</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex items-center gap-3 p-4 bg-slate-50 rounded-lg">
              <div className={`w-3 h-3 rounded-full ${status?.configured ? 'bg-green-500' : 'bg-red-500'}`} />
              <div>
                <p className="text-sm text-slate-500">Status</p>
                <div className="font-medium">
                  {status?.configured ? (
                    <Badge className="bg-green-100 text-green-700">Connected</Badge>
                  ) : (
                    <Badge variant="destructive">Not Configured</Badge>
                  )}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3 p-4 bg-slate-50 rounded-lg">
              <Phone className="w-5 h-5 text-slate-400" />
              <div>
                <p className="text-sm text-slate-500">App Name</p>
                <p className="font-medium">{status?.app_name || 'N/A'}</p>
              </div>
            </div>
            <div className="flex items-center gap-3 p-4 bg-slate-50 rounded-lg">
              <Phone className="w-5 h-5 text-slate-400" />
              <div>
                <p className="text-sm text-slate-500">Source Number</p>
                <p className="font-medium font-mono">{status?.source_number || 'N/A'}</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Send Test Message */}
      <Card data-testid="send-message-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Send className="w-5 h-5 text-orange-500" />
            Send Test Message
          </CardTitle>
          <CardDescription>Send a test WhatsApp message to verify the integration</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Recipient Phone Number
            </label>
            <Input
              placeholder="e.g., 919876543210 (with country code, no +)"
              value={testNumber}
              onChange={(e) => setTestNumber(e.target.value)}
              data-testid="test-phone-input"
            />
            <p className="text-xs text-slate-500 mt-1">Enter phone number with country code (e.g., 91 for India)</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Message
            </label>
            <Textarea
              placeholder="Enter your test message..."
              value={testMessage}
              onChange={(e) => setTestMessage(e.target.value)}
              rows={4}
              data-testid="test-message-input"
            />
            <p className="text-xs text-slate-500 mt-1">Use *text* for bold, _text_ for italic</p>
          </div>
          <div className="flex gap-2">
            <Button 
              onClick={sendTestMessage} 
              disabled={sending || sendingVoice || !status?.configured}
              className="bg-green-600 hover:bg-green-700"
              data-testid="send-test-btn"
            >
              {sending ? (
                <>
                  <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                  Sending...
                </>
              ) : (
                <>
                  <Send className="w-4 h-4 mr-2" />
                  Send Text
                </>
              )}
            </Button>
            <Button 
              onClick={sendVoiceMessage} 
              disabled={sending || sendingVoice || !status?.configured}
              variant="outline"
              className="border-purple-200 text-purple-600 hover:bg-purple-50"
              data-testid="send-voice-btn"
            >
              {sendingVoice ? (
                <>
                  <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  🎤 Send Voice
                </>
              )}
            </Button>
          </div>

          {sendResult && (
            <div className={`p-4 rounded-lg ${sendResult.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
              <div className="flex items-center gap-2">
                {sendResult.success ? (
                  <>
                    <CheckCircle className="w-5 h-5 text-green-600" />
                    <span className="font-medium text-green-700">
                      {sendResult.isVoice ? 'Voice Message Sent!' : 'Message Sent Successfully!'}
                    </span>
                  </>
                ) : (
                  <>
                    <XCircle className="w-5 h-5 text-red-600" />
                    <span className="font-medium text-red-700">Failed to Send</span>
                  </>
                )}
              </div>
              {sendResult.success && (
                <p className="text-sm text-green-600 mt-1">
                  Message ID: {sendResult.messageId}
                  {sendResult.audioSize && ` • Audio: ${Math.round(sendResult.audioSize / 1024)}KB`}
                </p>
              )}
              {sendResult.error && (
                <p className="text-sm text-red-600 mt-1">Error: {sendResult.error}</p>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Webhook Information */}
      <Card data-testid="webhook-info-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="w-5 h-5 text-blue-500" />
            Webhook Configuration
          </CardTitle>
          <CardDescription>Configure this webhook URL in your Gupshup dashboard to receive messages</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="p-4 bg-slate-900 rounded-lg">
            <code className="text-green-400 text-sm break-all">
              {API_URL}/api/whatsapp/webhook
            </code>
          </div>
          <div className="mt-4 space-y-2 text-sm text-slate-600">
            <p><strong>Steps to configure:</strong></p>
            <ol className="list-decimal list-inside space-y-1 ml-2">
              <li>Go to Gupshup Developer Dashboard</li>
              <li>Select your OEMLinker WhatsApp app</li>
              <li>Navigate to Webhooks / Callback URL settings</li>
              <li>Paste the webhook URL above</li>
              <li>Save and test the connection</li>
            </ol>
          </div>
        </CardContent>
      </Card>

      {/* Features Documentation */}
      <Card>
        <CardHeader>
          <CardTitle>Available Features</CardTitle>
          <CardDescription>WhatsApp capabilities for OEMLinker vendors</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 border rounded-lg">
              <h4 className="font-medium text-slate-800 mb-2">Vendor Commands</h4>
              <ul className="text-sm text-slate-600 space-y-1">
                <li><code className="bg-slate-100 px-1 rounded">help</code> - Show all commands</li>
                <li><code className="bg-slate-100 px-1 rounded">rfqs</code> - List matched RFQs</li>
                <li><code className="bg-slate-100 px-1 rounded">details &lt;id&gt;</code> - RFQ details</li>
                <li><code className="bg-slate-100 px-1 rounded">my quotes</code> - View quotes</li>
                <li><code className="bg-slate-100 px-1 rounded">my orders</code> - View orders</li>
                <li><code className="bg-slate-100 px-1 rounded">profile</code> - Vendor profile</li>
              </ul>
            </div>
            <div className="p-4 border rounded-lg">
              <h4 className="font-medium text-slate-800 mb-2">Automated Notifications</h4>
              <ul className="text-sm text-slate-600 space-y-1">
                <li>New RFQ matches</li>
                <li>Quote acceptance/rejection</li>
                <li>Order status updates</li>
                <li>AI-powered natural language queries</li>
              </ul>
            </div>
            <div className="p-4 border rounded-lg bg-green-50 border-green-200">
              <h4 className="font-medium text-green-800 mb-2">🎤 Voice Search</h4>
              <ul className="text-sm text-green-700 space-y-1">
                <li>Send voice messages to search</li>
                <li>AI transcribes and processes query</li>
                <li>Responds with text + voice</li>
                <li>Supports all Indian languages</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
