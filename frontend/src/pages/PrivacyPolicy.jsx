import React from 'react';
import { Link } from 'react-router-dom';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Shield, Lock, Database, Trash2, Mail, Phone, Globe, FileText } from 'lucide-react';

export default function PrivacyPolicy() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <img src="/logo.png" alt="OEMLinker" className="h-8" onError={(e) => e.target.style.display = 'none'} />
            <span className="text-xl font-bold text-slate-800">OEMLinker</span>
          </Link>
          <Link to="/data-deletion">
            <Button variant="outline" size="sm">
              <Trash2 className="w-4 h-4 mr-2" />
              Request Data Deletion
            </Button>
          </Link>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-slate-800 mb-2">Privacy Policy</h1>
          <p className="text-slate-600">Last updated: March 2026</p>
        </div>

        <div className="space-y-6">
          {/* Introduction */}
          <Card>
            <CardContent className="p-6">
              <div className="flex items-start gap-4">
                <Shield className="w-8 h-8 text-orange-600 flex-shrink-0 mt-1" />
                <div>
                  <h2 className="text-xl font-semibold text-slate-800 mb-3">Introduction</h2>
                  <p className="text-slate-600 leading-relaxed">
                    OEMLinker ("we," "our," or "us") is committed to protecting your privacy. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our on-demand manufacturing marketplace platform, including our website and WhatsApp Business integration.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Information We Collect */}
          <Card>
            <CardContent className="p-6">
              <div className="flex items-start gap-4">
                <Database className="w-8 h-8 text-blue-600 flex-shrink-0 mt-1" />
                <div>
                  <h2 className="text-xl font-semibold text-slate-800 mb-3">Information We Collect</h2>
                  
                  <h3 className="font-medium text-slate-700 mb-2">Personal Information:</h3>
                  <ul className="list-disc list-inside text-slate-600 mb-4 space-y-1">
                    <li>Name and contact information (email, phone number)</li>
                    <li>Business information (company name, GST number, address)</li>
                    <li>Profile information (certifications, industries served)</li>
                    <li>Machine and equipment details (for vendors)</li>
                  </ul>
                  
                  <h3 className="font-medium text-slate-700 mb-2">WhatsApp Data:</h3>
                  <ul className="list-disc list-inside text-slate-600 mb-4 space-y-1">
                    <li>Phone number used for WhatsApp communication</li>
                    <li>Messages exchanged through our WhatsApp Business integration</li>
                    <li>Images, documents, and media shared via WhatsApp</li>
                    <li>Voice messages and transcriptions</li>
                  </ul>
                  
                  <h3 className="font-medium text-slate-700 mb-2">Usage Data:</h3>
                  <ul className="list-disc list-inside text-slate-600 space-y-1">
                    <li>RFQ submissions and quotations</li>
                    <li>Order history and transactions</li>
                    <li>Platform usage patterns and preferences</li>
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* How We Use Your Information */}
          <Card>
            <CardContent className="p-6">
              <div className="flex items-start gap-4">
                <Globe className="w-8 h-8 text-green-600 flex-shrink-0 mt-1" />
                <div>
                  <h2 className="text-xl font-semibold text-slate-800 mb-3">How We Use Your Information</h2>
                  <ul className="list-disc list-inside text-slate-600 space-y-2">
                    <li>To match buyers with suitable manufacturing vendors</li>
                    <li>To facilitate RFQ submissions, quotations, and orders</li>
                    <li>To communicate via WhatsApp for vendor onboarding and notifications</li>
                    <li>To analyze machine capabilities using AI for better matching</li>
                    <li>To send transactional notifications and updates</li>
                    <li>To improve our platform and services</li>
                    <li>To comply with legal obligations</li>
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* WhatsApp Business Integration */}
          <Card className="border-green-200 bg-green-50/50">
            <CardContent className="p-6">
              <div className="flex items-start gap-4">
                <Phone className="w-8 h-8 text-green-600 flex-shrink-0 mt-1" />
                <div>
                  <h2 className="text-xl font-semibold text-slate-800 mb-3">WhatsApp Business Integration</h2>
                  <p className="text-slate-600 mb-4">
                    We use WhatsApp Business API (via Gupshup) for vendor communication. By interacting with us on WhatsApp, you acknowledge:
                  </p>
                  <ul className="list-disc list-inside text-slate-600 space-y-2">
                    <li>Messages are stored securely for customer support and service delivery</li>
                    <li>Your phone number is used to identify your vendor account</li>
                    <li>Media files (images, documents) shared are processed to extract relevant information</li>
                    <li>Voice messages may be transcribed for processing your requests</li>
                    <li>Message history is retained for service continuity</li>
                  </ul>
                  <p className="text-slate-600 mt-4">
                    <strong>Note:</strong> We comply with Meta's Platform Terms and WhatsApp Business Policy.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Data Retention */}
          <Card>
            <CardContent className="p-6">
              <div className="flex items-start gap-4">
                <Lock className="w-8 h-8 text-purple-600 flex-shrink-0 mt-1" />
                <div>
                  <h2 className="text-xl font-semibold text-slate-800 mb-3">Data Retention</h2>
                  <p className="text-slate-600 mb-4">
                    We retain your personal information for as long as necessary to:
                  </p>
                  <ul className="list-disc list-inside text-slate-600 space-y-2">
                    <li>Provide our services to you</li>
                    <li>Comply with legal obligations (tax records, transaction history)</li>
                    <li>Resolve disputes and enforce agreements</li>
                  </ul>
                  <p className="text-slate-600 mt-4">
                    WhatsApp message history is retained for 2 years for service continuity. 
                    You can request deletion at any time.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Your Rights */}
          <Card className="border-orange-200 bg-orange-50/50">
            <CardContent className="p-6">
              <div className="flex items-start gap-4">
                <Trash2 className="w-8 h-8 text-orange-600 flex-shrink-0 mt-1" />
                <div>
                  <h2 className="text-xl font-semibold text-slate-800 mb-3">Your Rights & Data Deletion</h2>
                  <p className="text-slate-600 mb-4">
                    You have the right to:
                  </p>
                  <ul className="list-disc list-inside text-slate-600 space-y-2 mb-4">
                    <li>Access your personal data</li>
                    <li>Correct inaccurate data</li>
                    <li>Request deletion of your data</li>
                    <li>Object to data processing</li>
                    <li>Data portability</li>
                  </ul>
                  <div className="bg-white rounded-lg p-4 border border-orange-200">
                    <p className="text-slate-700 font-medium mb-2">Request Data Deletion:</p>
                    <p className="text-slate-600 mb-3">
                      To delete your data from OEMLinker, including all WhatsApp messages and account information:
                    </p>
                    <Link to="/data-deletion">
                      <Button className="bg-orange-600 hover:bg-orange-700">
                        <Trash2 className="w-4 h-4 mr-2" />
                        Request Data Deletion
                      </Button>
                    </Link>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Contact Us */}
          <Card>
            <CardContent className="p-6">
              <div className="flex items-start gap-4">
                <Mail className="w-8 h-8 text-slate-600 flex-shrink-0 mt-1" />
                <div>
                  <h2 className="text-xl font-semibold text-slate-800 mb-3">Contact Us</h2>
                  <p className="text-slate-600 mb-4">
                    For privacy-related inquiries or to exercise your rights, contact us at:
                  </p>
                  <div className="space-y-2 text-slate-600">
                    <p><strong>Email:</strong> privacy@oemlinker.com</p>
                    <p><strong>WhatsApp:</strong> +91 98315 09919</p>
                    <p><strong>Address:</strong> OEMLinker, India</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Footer Links */}
          <div className="flex flex-wrap gap-4 justify-center pt-6 border-t border-slate-200">
            <Link to="/data-deletion" className="text-orange-600 hover:underline flex items-center gap-1">
              <Trash2 className="w-4 h-4" /> Data Deletion Request
            </Link>
            <Link to="/terms" className="text-slate-600 hover:underline flex items-center gap-1">
              <FileText className="w-4 h-4" /> Terms of Service
            </Link>
            <Link to="/" className="text-slate-600 hover:underline">
              Back to Home
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}
