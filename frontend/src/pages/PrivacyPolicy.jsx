import { useEffect } from "react";
import { Link } from "react-router-dom";
import { Button } from "../components/ui/button";
import { ArrowLeft, Shield, Eye, Lock, Database, Globe, UserCheck, Bell, Trash2, Mail } from "lucide-react";

const PrivacyPolicy = () => {
  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  const lastUpdated = "March 6, 2026";

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <div className="bg-gradient-to-r from-slate-900 to-slate-800 text-white">
        <div className="max-w-4xl mx-auto px-4 py-12">
          <Link to="/">
            <Button variant="ghost" className="text-slate-300 hover:text-white mb-6">
              <ArrowLeft className="w-4 h-4 mr-2" /> Back to Home
            </Button>
          </Link>
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 bg-orange-500 rounded-xl flex items-center justify-center">
              <Shield className="w-7 h-7 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-bold">Privacy Policy</h1>
              <p className="text-slate-400 mt-1">Last updated: {lastUpdated}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-4xl mx-auto px-4 py-12">
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-8 space-y-8">
          
          {/* Introduction */}
          <section>
            <h2 className="text-xl font-bold text-slate-900 mb-4 flex items-center gap-2">
              <Eye className="w-5 h-5 text-orange-500" />
              1. Introduction
            </h2>
            <p className="text-slate-600 leading-relaxed">
              OEMLinker ("we", "us", or "our") is committed to protecting your privacy. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our AI-powered manufacturing marketplace platform ("Platform").
            </p>
            <p className="text-slate-600 leading-relaxed mt-4">
              By using our Platform, you consent to the data practices described in this Privacy Policy. If you do not agree with this policy, please do not use our Services.
            </p>
          </section>

          {/* Information We Collect */}
          <section>
            <h2 className="text-xl font-bold text-slate-900 mb-4 flex items-center gap-2">
              <Database className="w-5 h-5 text-orange-500" />
              2. Information We Collect
            </h2>
            
            <h3 className="text-lg font-semibold text-slate-800 mt-6 mb-3">2.1 Information You Provide</h3>
            <ul className="space-y-2 text-slate-600 list-disc list-inside">
              <li><strong>Account Information:</strong> Name, email address, phone number, company name, designation, and password when you register.</li>
              <li><strong>Business Information:</strong> GSTIN, PAN, company address, certifications, and bank account details for vendors.</li>
              <li><strong>Technical Data:</strong> Engineering drawings, CAD files, specifications, and RFQ details submitted through the Platform.</li>
              <li><strong>Communication Data:</strong> Messages, emails, and correspondence exchanged through the Platform.</li>
              <li><strong>Payment Information:</strong> Billing address and payment method details (processed securely by payment partners).</li>
            </ul>

            <h3 className="text-lg font-semibold text-slate-800 mt-6 mb-3">2.2 Information Collected Automatically</h3>
            <ul className="space-y-2 text-slate-600 list-disc list-inside">
              <li><strong>Device Information:</strong> IP address, browser type, operating system, device identifiers.</li>
              <li><strong>Usage Data:</strong> Pages visited, features used, time spent on Platform, click patterns.</li>
              <li><strong>Location Data:</strong> Approximate location based on IP address.</li>
              <li><strong>Cookies:</strong> Session cookies, authentication cookies, and analytics cookies.</li>
            </ul>

            <h3 className="text-lg font-semibold text-slate-800 mt-6 mb-3">2.3 Information from Third Parties</h3>
            <ul className="space-y-2 text-slate-600 list-disc list-inside">
              <li><strong>Verification Services:</strong> GSTIN verification data from government databases.</li>
              <li><strong>Social Login:</strong> Profile information if you sign in using Google OAuth.</li>
              <li><strong>Payment Partners:</strong> Transaction confirmation and payment status.</li>
            </ul>
          </section>

          {/* How We Use Information */}
          <section>
            <h2 className="text-xl font-bold text-slate-900 mb-4 flex items-center gap-2">
              <UserCheck className="w-5 h-5 text-orange-500" />
              3. How We Use Your Information
            </h2>
            <p className="text-slate-600 mb-4">We use collected information for the following purposes:</p>
            <ul className="space-y-2 text-slate-600 list-disc list-inside">
              <li><strong>Service Delivery:</strong> To provide, maintain, and improve our Platform services.</li>
              <li><strong>AI Matching:</strong> To analyze technical requirements and match Buyers with suitable Vendors.</li>
              <li><strong>Account Management:</strong> To create and manage your account, verify identity, and process transactions.</li>
              <li><strong>Communication:</strong> To send notifications, updates, and respond to your inquiries.</li>
              <li><strong>Security:</strong> To detect and prevent fraud, unauthorized access, and other illegal activities.</li>
              <li><strong>Analytics:</strong> To understand usage patterns and improve user experience.</li>
              <li><strong>Legal Compliance:</strong> To comply with applicable laws, regulations, and legal processes.</li>
              <li><strong>Marketing:</strong> To send promotional communications (with your consent) about our services.</li>
            </ul>
          </section>

          {/* AI and Machine Learning */}
          <section>
            <h2 className="text-xl font-bold text-slate-900 mb-4">4. AI and Machine Learning</h2>
            <div className="space-y-4 text-slate-600">
              <p><strong>4.1 Drawing Analysis:</strong> We use AI (including OpenAI's GPT Vision technology) to analyze engineering drawings and extract technical specifications. This analysis is used solely for vendor matching and is not shared with unauthorized parties.</p>
              <p><strong>4.2 Matching Algorithm:</strong> Our AI-powered matching system analyzes RFQ requirements against vendor capabilities to suggest suitable matches. The algorithm considers machine capabilities, materials, tolerances, and past experience.</p>
              <p><strong>4.3 Voice Assistant:</strong> Our voice assistant uses speech-to-text technology to help vendors search for RFQs. Audio data is processed for transcription and not stored permanently.</p>
              <p><strong>4.4 Data Training:</strong> We may use anonymized and aggregated data to improve our AI models. Individual user data is not used for training external AI models without explicit consent.</p>
            </div>
          </section>

          {/* Data Sharing */}
          <section>
            <h2 className="text-xl font-bold text-slate-900 mb-4 flex items-center gap-2">
              <Globe className="w-5 h-5 text-orange-500" />
              5. Information Sharing and Disclosure
            </h2>
            <p className="text-slate-600 mb-4">We may share your information in the following circumstances:</p>
            
            <h3 className="text-lg font-semibold text-slate-800 mt-6 mb-3">5.1 With Other Users</h3>
            <ul className="space-y-2 text-slate-600 list-disc list-inside">
              <li>Buyer information (company name, requirements) is shared with matched Vendors.</li>
              <li>Vendor information (company details, capabilities, quotes) is shared with relevant Buyers.</li>
              <li>Contact details are shared between parties upon order confirmation.</li>
            </ul>

            <h3 className="text-lg font-semibold text-slate-800 mt-6 mb-3">5.2 With Service Providers</h3>
            <ul className="space-y-2 text-slate-600 list-disc list-inside">
              <li>Payment processors for transaction processing.</li>
              <li>Cloud hosting providers for data storage.</li>
              <li>Email service providers for communications.</li>
              <li>Analytics providers for usage analysis.</li>
            </ul>

            <h3 className="text-lg font-semibold text-slate-800 mt-6 mb-3">5.3 Legal Requirements</h3>
            <p className="text-slate-600">We may disclose information when required by law, court order, or government request, or to protect our rights, property, or safety.</p>

            <h3 className="text-lg font-semibold text-slate-800 mt-6 mb-3">5.4 Business Transfers</h3>
            <p className="text-slate-600">In the event of a merger, acquisition, or sale of assets, user information may be transferred as part of the transaction.</p>
          </section>

          {/* Data Security */}
          <section>
            <h2 className="text-xl font-bold text-slate-900 mb-4 flex items-center gap-2">
              <Lock className="w-5 h-5 text-orange-500" />
              6. Data Security
            </h2>
            <div className="space-y-4 text-slate-600">
              <p><strong>6.1 Security Measures:</strong> We implement industry-standard security measures including:</p>
              <ul className="space-y-2 list-disc list-inside ml-4">
                <li>SSL/TLS encryption for data in transit</li>
                <li>Encrypted storage for sensitive data</li>
                <li>Secure password hashing (bcrypt)</li>
                <li>Two-factor authentication (2FA) option</li>
                <li>Rate limiting and account lockout protection</li>
                <li>Regular security audits and monitoring</li>
              </ul>
              <p><strong>6.2 Technical Drawings:</strong> Engineering drawings and specifications are treated as confidential business information. Access is restricted to authorized users only.</p>
              <p><strong>6.3 Payment Security:</strong> Payment information is processed by PCI-DSS compliant payment partners. We do not store complete credit card numbers.</p>
              <p><strong>6.4 Data Breach:</strong> In the event of a data breach affecting your personal information, we will notify you and relevant authorities as required by applicable law.</p>
            </div>
          </section>

          {/* Data Retention */}
          <section>
            <h2 className="text-xl font-bold text-slate-900 mb-4">7. Data Retention</h2>
            <div className="space-y-4 text-slate-600">
              <p><strong>7.1 Retention Period:</strong> We retain personal information for as long as necessary to provide our services and fulfill the purposes described in this policy. Specifically:</p>
              <ul className="space-y-2 list-disc list-inside ml-4">
                <li>Account information: Retained while your account is active and for 3 years after deletion.</li>
                <li>Transaction records: Retained for 7 years for legal and tax compliance.</li>
                <li>Technical drawings: Retained for the duration of the project plus 2 years.</li>
                <li>Communication logs: Retained for 3 years.</li>
              </ul>
              <p><strong>7.2 Deletion:</strong> Upon account deletion request, we will delete or anonymize your personal information within 30 days, except where retention is required by law.</p>
            </div>
          </section>

          {/* Your Rights */}
          <section>
            <h2 className="text-xl font-bold text-slate-900 mb-4 flex items-center gap-2">
              <UserCheck className="w-5 h-5 text-orange-500" />
              8. Your Rights and Choices
            </h2>
            <p className="text-slate-600 mb-4">You have the following rights regarding your personal information:</p>
            <ul className="space-y-2 text-slate-600 list-disc list-inside">
              <li><strong>Access:</strong> Request a copy of your personal information.</li>
              <li><strong>Correction:</strong> Update or correct inaccurate information.</li>
              <li><strong>Deletion:</strong> Request deletion of your personal information.</li>
              <li><strong>Portability:</strong> Request your data in a portable format.</li>
              <li><strong>Opt-out:</strong> Unsubscribe from marketing communications.</li>
              <li><strong>Withdraw Consent:</strong> Withdraw consent for data processing where applicable.</li>
            </ul>
            <p className="text-slate-600 mt-4">To exercise these rights, contact us at privacy@oemlinker.com. We will respond within 30 days.</p>
          </section>

          {/* Cookies */}
          <section>
            <h2 className="text-xl font-bold text-slate-900 mb-4">9. Cookies and Tracking</h2>
            <div className="space-y-4 text-slate-600">
              <p><strong>9.1 Types of Cookies:</strong></p>
              <ul className="space-y-2 list-disc list-inside ml-4">
                <li><strong>Essential Cookies:</strong> Required for Platform functionality and security.</li>
                <li><strong>Authentication Cookies:</strong> Keep you logged in during your session.</li>
                <li><strong>Analytics Cookies:</strong> Help us understand how users interact with the Platform.</li>
                <li><strong>Preference Cookies:</strong> Remember your settings and preferences.</li>
              </ul>
              <p><strong>9.2 Cookie Management:</strong> You can manage cookie preferences through your browser settings. Disabling essential cookies may affect Platform functionality.</p>
            </div>
          </section>

          {/* Third-Party Links */}
          <section>
            <h2 className="text-xl font-bold text-slate-900 mb-4">10. Third-Party Links</h2>
            <p className="text-slate-600 leading-relaxed">
              Our Platform may contain links to third-party websites or services. We are not responsible for the privacy practices of these external sites. We encourage you to review the privacy policies of any third-party sites you visit.
            </p>
          </section>

          {/* Children's Privacy */}
          <section>
            <h2 className="text-xl font-bold text-slate-900 mb-4">11. Children's Privacy</h2>
            <p className="text-slate-600 leading-relaxed">
              Our Platform is intended for business use and is not directed at individuals under 18 years of age. We do not knowingly collect personal information from children. If we become aware that we have collected information from a minor, we will delete it promptly.
            </p>
          </section>

          {/* International Transfers */}
          <section>
            <h2 className="text-xl font-bold text-slate-900 mb-4">12. International Data Transfers</h2>
            <p className="text-slate-600 leading-relaxed">
              Your information may be transferred to and processed in countries other than India, where data protection laws may differ. We ensure appropriate safeguards are in place for such transfers, including standard contractual clauses and data processing agreements.
            </p>
          </section>

          {/* Updates */}
          <section>
            <h2 className="text-xl font-bold text-slate-900 mb-4 flex items-center gap-2">
              <Bell className="w-5 h-5 text-orange-500" />
              13. Changes to This Policy
            </h2>
            <p className="text-slate-600 leading-relaxed">
              We may update this Privacy Policy periodically. We will notify you of material changes by posting a notice on the Platform or sending you an email. Your continued use of the Platform after changes indicates acceptance of the updated policy.
            </p>
          </section>

          {/* Contact */}
          <section className="bg-slate-50 rounded-lg p-6">
            <h2 className="text-xl font-bold text-slate-900 mb-4 flex items-center gap-2">
              <Mail className="w-5 h-5 text-orange-500" />
              14. Contact Us
            </h2>
            <p className="text-slate-600 leading-relaxed">
              If you have questions about this Privacy Policy or our data practices, please contact our Data Protection Officer:
            </p>
            <div className="mt-4 space-y-2 text-slate-600">
              <p><strong>Email:</strong> privacy@oemlinker.com</p>
              <p><strong>Address:</strong> OEMLinker, Data Protection Officer, Kolkata, West Bengal, India</p>
              <p><strong>General Support:</strong> support@oemlinker.com</p>
            </div>
          </section>

          {/* Grievance Officer */}
          <section className="bg-orange-50 rounded-lg p-6 border border-orange-100">
            <h2 className="text-lg font-bold text-slate-900 mb-3">Grievance Officer (As per Indian IT Act)</h2>
            <p className="text-slate-600 text-sm">
              In accordance with the Information Technology Act, 2000 and rules made thereunder, the name and contact details of the Grievance Officer are provided below:
            </p>
            <div className="mt-3 space-y-1 text-slate-600 text-sm">
              <p><strong>Name:</strong> Grievance Officer, OEMLinker</p>
              <p><strong>Email:</strong> grievance@oemlinker.com</p>
              <p><strong>Response Time:</strong> Within 30 days of receiving the complaint</p>
            </div>
          </section>

        </div>

        {/* Footer Links */}
        <div className="mt-8 text-center text-slate-500 text-sm">
          <Link to="/terms-of-service" className="hover:text-orange-600 transition-colors">
            Terms of Service
          </Link>
          <span className="mx-3">•</span>
          <Link to="/" className="hover:text-orange-600 transition-colors">
            Back to Home
          </Link>
        </div>
      </div>
    </div>
  );
};

export default PrivacyPolicy;
