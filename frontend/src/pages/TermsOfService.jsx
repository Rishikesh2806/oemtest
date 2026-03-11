import { useEffect } from "react";
import { Link } from "react-router-dom";
import { Button } from "../components/ui/button";
import { ArrowLeft, Shield, FileText, Scale, AlertTriangle, CreditCard, Truck, MessageSquare } from "lucide-react";

const TermsOfService = () => {
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
              <Scale className="w-7 h-7 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-bold">Terms of Service</h1>
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
              <FileText className="w-5 h-5 text-orange-500" />
              1. Introduction
            </h2>
            <p className="text-slate-600 leading-relaxed">
              Welcome to OEMLinker, operated by <strong>Simpson & Munro (I) Pvt Ltd</strong> ("Platform", "we", "us", or "our"). These Terms of Service ("Terms") govern your access to and use of our AI-powered on-demand manufacturing marketplace platform, including our website, mobile applications, and related services (collectively, the "Services").
            </p>
            <p className="text-slate-600 leading-relaxed mt-4">
              By accessing or using our Services, you agree to be bound by these Terms. If you do not agree to these Terms, please do not use our Services. These Terms constitute a legally binding agreement between you and OEMLinker.
            </p>
          </section>

          {/* Definitions */}
          <section>
            <h2 className="text-xl font-bold text-slate-900 mb-4">2. Definitions</h2>
            <ul className="space-y-3 text-slate-600">
              <li><strong>"Buyer"</strong> refers to any user who creates Request for Quotations (RFQs) to procure manufacturing services.</li>
              <li><strong>"Vendor"</strong> refers to any manufacturing company or service provider registered on the Platform to offer manufacturing services.</li>
              <li><strong>"RFQ"</strong> refers to Request for Quotation, a document submitted by Buyers detailing their manufacturing requirements.</li>
              <li><strong>"Quote"</strong> refers to the pricing and terms submitted by Vendors in response to an RFQ.</li>
              <li><strong>"Order"</strong> refers to a confirmed transaction between a Buyer and Vendor following acceptance of a Quote.</li>
              <li><strong>"Platform Commission"</strong> refers to the service fee charged by OEMLinker on successful transactions.</li>
            </ul>
          </section>

          {/* Eligibility */}
          <section>
            <h2 className="text-xl font-bold text-slate-900 mb-4">3. Eligibility and Registration</h2>
            <div className="space-y-4 text-slate-600">
              <p><strong>3.1 Eligibility:</strong> To use our Services, you must be at least 18 years of age and have the legal capacity to enter into binding contracts. If you are using the Services on behalf of a business entity, you represent that you have the authority to bind that entity to these Terms.</p>
              <p><strong>3.2 Account Registration:</strong> To access certain features of the Platform, you must create an account. You agree to provide accurate, current, and complete information during registration and to update such information to keep it accurate.</p>
              <p><strong>3.3 Vendor Verification:</strong> Vendors must provide valid GSTIN (Goods and Services Tax Identification Number), company registration details, and other verification documents as required. We reserve the right to verify this information and reject or suspend accounts that fail verification.</p>
              <p><strong>3.4 Account Security:</strong> You are responsible for maintaining the confidentiality of your account credentials. You agree to notify us immediately of any unauthorized use of your account.</p>
            </div>
          </section>

          {/* Platform Services */}
          <section>
            <h2 className="text-xl font-bold text-slate-900 mb-4 flex items-center gap-2">
              <Shield className="w-5 h-5 text-orange-500" />
              4. Platform Services
            </h2>
            <div className="space-y-4 text-slate-600">
              <p><strong>4.1 Marketplace Services:</strong> OEMLinker provides a platform connecting Buyers with Vendors for manufacturing services. We facilitate the creation of RFQs, AI-powered vendor matching, quotation submission, order management, and communication between parties.</p>
              <p><strong>4.2 AI-Powered Matching:</strong> Our Platform uses artificial intelligence to analyze engineering drawings and technical specifications to match Buyers with suitable Vendors. While we strive for accuracy, we do not guarantee the suitability of matches and recommend Buyers conduct their own due diligence.</p>
              <p><strong>4.3 Platform Role:</strong> OEMLinker acts solely as an intermediary platform. We are not a party to any transaction between Buyers and Vendors. We do not manufacture, inspect, or guarantee any products or services exchanged through the Platform.</p>
            </div>
          </section>

          {/* Buyer Terms */}
          <section>
            <h2 className="text-xl font-bold text-slate-900 mb-4">5. Terms for Buyers</h2>
            <div className="space-y-4 text-slate-600">
              <p><strong>5.1 RFQ Submission:</strong> Buyers must provide accurate and complete information in their RFQs, including technical specifications, drawings, quantity requirements, and delivery timelines.</p>
              <p><strong>5.2 Quote Acceptance:</strong> Accepting a Quote creates a binding agreement between the Buyer and Vendor. Buyers should carefully review all Quote details before acceptance.</p>
              <p><strong>5.3 Payment Obligations:</strong> Buyers agree to pay the agreed amount as per the payment terms specified in the accepted Quote. Late payments may incur additional charges.</p>
              <p><strong>5.4 Intellectual Property:</strong> Buyers represent that they own or have the right to use all designs, drawings, and specifications submitted through the Platform.</p>
            </div>
          </section>

          {/* Vendor Terms */}
          <section>
            <h2 className="text-xl font-bold text-slate-900 mb-4">6. Terms for Vendors</h2>
            <div className="space-y-4 text-slate-600">
              <p><strong>6.1 Accurate Information:</strong> Vendors must provide accurate information about their capabilities, machines, certifications, and capacity. Misrepresentation may result in account suspension.</p>
              <p><strong>6.2 Quote Submission:</strong> Quotes submitted by Vendors are binding offers. Vendors must honor accepted Quotes at the quoted price and terms.</p>
              <p><strong>6.3 Quality Standards:</strong> Vendors agree to deliver products that meet the specifications outlined in the RFQ and maintain consistent quality standards.</p>
              <p><strong>6.4 Delivery Commitments:</strong> Vendors must meet agreed delivery timelines. Delays must be communicated promptly to Buyers through the Platform.</p>
              <p><strong>6.5 Platform Commission:</strong> Vendors agree to pay the applicable Platform Commission on successful transactions as per the fee schedule.</p>
            </div>
          </section>

          {/* Payments */}
          <section>
            <h2 className="text-xl font-bold text-slate-900 mb-4 flex items-center gap-2">
              <CreditCard className="w-5 h-5 text-orange-500" />
              7. Payments and Fees
            </h2>
            <div className="space-y-4 text-slate-600">
              <p><strong>7.1 Payment Processing:</strong> All payments are processed through our secure payment partners. We support multiple payment methods as displayed on the Platform.</p>
              <p><strong>7.2 Escrow Services:</strong> For certain transactions, payments may be held in escrow until delivery confirmation. Release of funds is subject to our escrow policy.</p>
              <p><strong>7.3 Platform Fees:</strong> OEMLinker charges a commission on successful transactions. Current fee schedules are available on the Platform and may be updated with notice.</p>
              <p><strong>7.4 Taxes:</strong> Users are responsible for all applicable taxes on their transactions. Prices displayed may be exclusive of GST and other taxes unless specified.</p>
              <p><strong>7.5 Refunds:</strong> Refund requests are handled through our dispute resolution process. Refunds are subject to our Refund Policy and the nature of the dispute.</p>
            </div>
          </section>

          {/* Dispute Resolution */}
          <section>
            <h2 className="text-xl font-bold text-slate-900 mb-4 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-orange-500" />
              8. Dispute Resolution
            </h2>
            <div className="space-y-4 text-slate-600">
              <p><strong>8.1 Raising Disputes:</strong> Users may raise disputes through the Platform's dispute resolution system for issues including quality concerns, delivery delays, payment disputes, and specification mismatches.</p>
              <p><strong>8.2 Resolution Process:</strong> OEMLinker will review disputes and may request evidence from both parties. We aim to resolve disputes within 5-7 business days.</p>
              <p><strong>8.3 Resolution Options:</strong> Based on our review, resolutions may include full refunds, partial refunds, replacements, rework, or other remedies as appropriate.</p>
              <p><strong>8.4 Final Decision:</strong> While we strive for fair resolutions, users acknowledge that our dispute resolution decisions are final and binding for Platform-related matters.</p>
              <p><strong>8.5 Legal Recourse:</strong> Nothing in these Terms prevents users from seeking legal remedies for matters outside the Platform's dispute resolution scope.</p>
            </div>
          </section>

          {/* Intellectual Property */}
          <section>
            <h2 className="text-xl font-bold text-slate-900 mb-4">9. Intellectual Property</h2>
            <div className="space-y-4 text-slate-600">
              <p><strong>9.1 Platform IP:</strong> All content, features, and functionality of the Platform (including software, algorithms, text, graphics, logos, and trademarks) are owned by OEMLinker and protected by intellectual property laws.</p>
              <p><strong>9.2 User Content:</strong> Users retain ownership of content they submit (drawings, specifications, etc.). By submitting content, users grant OEMLinker a limited license to use such content solely for providing the Services.</p>
              <p><strong>9.3 Confidentiality:</strong> Technical drawings and specifications shared through the Platform are treated as confidential. Vendors agree not to use Buyer designs for purposes other than fulfilling the specific order.</p>
            </div>
          </section>

          {/* Limitation of Liability */}
          <section>
            <h2 className="text-xl font-bold text-slate-900 mb-4">10. Limitation of Liability</h2>
            <div className="space-y-4 text-slate-600">
              <p><strong>10.1 Platform Liability:</strong> OEMLinker is not liable for the quality, safety, or legality of products manufactured through the Platform. We do not guarantee the accuracy of Vendor capabilities or Buyer specifications.</p>
              <p><strong>10.2 Indirect Damages:</strong> To the maximum extent permitted by law, OEMLinker shall not be liable for any indirect, incidental, special, consequential, or punitive damages arising from your use of the Services.</p>
              <p><strong>10.3 Maximum Liability:</strong> Our total liability for any claims arising from these Terms or your use of the Services shall not exceed the Platform fees paid by you in the 12 months preceding the claim.</p>
              <p><strong>10.4 Force Majeure:</strong> We are not liable for delays or failures in performance resulting from circumstances beyond our reasonable control.</p>
            </div>
          </section>

          {/* Termination */}
          <section>
            <h2 className="text-xl font-bold text-slate-900 mb-4">11. Termination</h2>
            <div className="space-y-4 text-slate-600">
              <p><strong>11.1 User Termination:</strong> You may terminate your account at any time by contacting us. Termination does not relieve you of obligations for ongoing transactions.</p>
              <p><strong>11.2 Platform Termination:</strong> We may suspend or terminate accounts that violate these Terms, engage in fraudulent activity, or for other reasons at our discretion.</p>
              <p><strong>11.3 Effect of Termination:</strong> Upon termination, your right to use the Services ceases. Provisions that by their nature should survive termination shall remain in effect.</p>
            </div>
          </section>

          {/* Governing Law */}
          <section>
            <h2 className="text-xl font-bold text-slate-900 mb-4">12. Governing Law and Jurisdiction</h2>
            <div className="space-y-4 text-slate-600">
              <p><strong>12.1 Governing Law:</strong> These Terms are governed by and construed in accordance with the laws of India.</p>
              <p><strong>12.2 Jurisdiction:</strong> Any disputes arising from these Terms shall be subject to the exclusive jurisdiction of the courts in Kolkata, West Bengal, India.</p>
              <p><strong>12.3 Arbitration:</strong> For commercial disputes, parties may opt for arbitration under the Arbitration and Conciliation Act, 1996.</p>
            </div>
          </section>

          {/* Changes to Terms */}
          <section>
            <h2 className="text-xl font-bold text-slate-900 mb-4">13. Changes to Terms</h2>
            <p className="text-slate-600 leading-relaxed">
              We reserve the right to modify these Terms at any time. We will notify users of material changes through the Platform or via email. Continued use of the Services after changes constitutes acceptance of the modified Terms.
            </p>
          </section>

          {/* Contact */}
          <section className="bg-slate-50 rounded-lg p-6">
            <h2 className="text-xl font-bold text-slate-900 mb-4 flex items-center gap-2">
              <MessageSquare className="w-5 h-5 text-orange-500" />
              14. Contact Us
            </h2>
            <p className="text-slate-600 leading-relaxed">
              If you have any questions about these Terms of Service, please contact us:
            </p>
            <div className="mt-4 space-y-2 text-slate-600">
              <p><strong>Business Entity:</strong> Simpson & Munro (I) Pvt Ltd</p>
              <p><strong>Email:</strong> legal@oemlinker.com</p>
              <p><strong>Address:</strong> Kolkata, West Bengal, India</p>
              <p><strong>Support:</strong> support@oemlinker.com</p>
            </div>
          </section>

        </div>

        {/* Footer Links */}
        <div className="mt-8 text-center text-slate-500 text-sm">
          <Link to="/privacy-policy" className="hover:text-orange-600 transition-colors">
            Privacy Policy
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

export default TermsOfService;
