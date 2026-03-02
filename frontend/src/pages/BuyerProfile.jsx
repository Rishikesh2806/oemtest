import { useState, useEffect } from "react";
import { useAuth, api } from "../App";
import DashboardLayout from "../components/layout/DashboardLayout";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { toast } from "sonner";
import { 
  User, Building2, Mail, Phone, MapPin, Globe, 
  FileText, Shield, Save, Loader2, CheckCircle2,
  Lock, Bell, Eye, EyeOff
} from "lucide-react";

const BuyerProfile = () => {
  const { user, updateUser } = useAuth();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [profile, setProfile] = useState({
    name: "",
    email: "",
    phone: "",
    company_name: "",
    company_address: "",
    city: "",
    state: "",
    country: "",
    pincode: "",
    gstin: "",
    pan: "",
    website: "",
    designation: "",
    department: ""
  });
  
  // Security settings
  const [securitySettings, setSecuritySettings] = useState({
    two_factor_enabled: false,
    password_changed_at: null
  });
  const [changingPassword, setChangingPassword] = useState(false);
  const [passwordData, setPasswordData] = useState({
    current_password: "",
    new_password: "",
    confirm_password: ""
  });
  const [showPasswords, setShowPasswords] = useState(false);
  const [toggling2FA, setToggling2FA] = useState(false);
  const [twoFAPassword, setTwoFAPassword] = useState("");

  useEffect(() => {
    fetchProfile();
    fetch2FAStatus();
  }, []);

  const fetchProfile = async () => {
    try {
      const response = await api.get("/user/profile");
      setProfile(prev => ({
        ...prev,
        ...response.data
      }));
    } catch (error) {
      // Use user data from auth context as fallback
      if (user) {
        setProfile(prev => ({
          ...prev,
          name: user.name || "",
          email: user.email || "",
          company_name: user.company_name || ""
        }));
      }
    } finally {
      setLoading(false);
    }
  };

  const fetch2FAStatus = async () => {
    try {
      const response = await api.get("/auth/2fa/status");
      setSecuritySettings(response.data);
    } catch (error) {
      console.error("Failed to fetch 2FA status");
    }
  };

  const handleSaveProfile = async () => {
    setSaving(true);
    try {
      await api.put("/user/profile", profile);
      toast.success("Profile updated successfully!");
      
      // Update user context if name changed
      if (profile.name !== user?.name) {
        updateUser({ ...user, name: profile.name, company_name: profile.company_name });
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to update profile");
    } finally {
      setSaving(false);
    }
  };

  const handleChangePassword = async () => {
    if (passwordData.new_password !== passwordData.confirm_password) {
      toast.error("New passwords do not match");
      return;
    }
    
    if (passwordData.new_password.length < 8) {
      toast.error("Password must be at least 8 characters");
      return;
    }

    setChangingPassword(true);
    try {
      await api.post("/auth/change-password", {
        current_password: passwordData.current_password,
        new_password: passwordData.new_password
      });
      toast.success("Password changed successfully!");
      setPasswordData({ current_password: "", new_password: "", confirm_password: "" });
      fetch2FAStatus(); // Refresh to get new password_changed_at
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to change password");
    } finally {
      setChangingPassword(false);
    }
  };

  const handleToggle2FA = async () => {
    if (!twoFAPassword) {
      toast.error("Please enter your password to change 2FA settings");
      return;
    }

    setToggling2FA(true);
    try {
      const newStatus = !securitySettings.two_factor_enabled;
      await api.post("/auth/2fa/toggle", {
        enable: newStatus,
        password: twoFAPassword
      });
      setSecuritySettings(prev => ({ ...prev, two_factor_enabled: newStatus }));
      toast.success(`Two-factor authentication ${newStatus ? "enabled" : "disabled"}`);
      setTwoFAPassword("");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to update 2FA settings");
    } finally {
      setToggling2FA(false);
    }
  };

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-orange-600" />
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h1 className="font-heading text-2xl font-bold text-slate-900">My Profile</h1>
          <p className="text-slate-500">Manage your account details and company information</p>
        </div>

        <Tabs defaultValue="profile" className="space-y-6">
          <TabsList>
            <TabsTrigger value="profile" className="flex items-center gap-2">
              <User className="w-4 h-4" />
              Profile
            </TabsTrigger>
            <TabsTrigger value="company" className="flex items-center gap-2">
              <Building2 className="w-4 h-4" />
              Company
            </TabsTrigger>
            <TabsTrigger value="security" className="flex items-center gap-2">
              <Shield className="w-4 h-4" />
              Security
            </TabsTrigger>
          </TabsList>

          {/* Profile Tab */}
          <TabsContent value="profile">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <User className="w-5 h-5 text-orange-600" />
                  Personal Information
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                      Full Name
                    </Label>
                    <Input
                      value={profile.name}
                      onChange={(e) => setProfile(prev => ({ ...prev, name: e.target.value }))}
                      placeholder="Your full name"
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                      Email Address
                    </Label>
                    <div className="relative mt-1">
                      <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                      <Input
                        value={profile.email}
                        className="pl-10 bg-slate-50"
                        disabled
                      />
                    </div>
                    <p className="text-xs text-slate-400 mt-1">Email cannot be changed</p>
                  </div>
                  <div>
                    <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                      Phone Number
                    </Label>
                    <div className="relative mt-1">
                      <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                      <Input
                        value={profile.phone}
                        onChange={(e) => setProfile(prev => ({ ...prev, phone: e.target.value }))}
                        placeholder="+91 98765 43210"
                        className="pl-10"
                      />
                    </div>
                  </div>
                  <div>
                    <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                      Designation
                    </Label>
                    <Input
                      value={profile.designation}
                      onChange={(e) => setProfile(prev => ({ ...prev, designation: e.target.value }))}
                      placeholder="e.g., Procurement Manager"
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                      Department
                    </Label>
                    <Input
                      value={profile.department}
                      onChange={(e) => setProfile(prev => ({ ...prev, department: e.target.value }))}
                      placeholder="e.g., Supply Chain"
                      className="mt-1"
                    />
                  </div>
                </div>

                <div className="flex justify-end pt-4 border-t">
                  <Button onClick={handleSaveProfile} disabled={saving} className="bg-orange-600 hover:bg-orange-700">
                    {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Save className="w-4 h-4 mr-2" />}
                    Save Changes
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Company Tab */}
          <TabsContent value="company">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Building2 className="w-5 h-5 text-orange-600" />
                  Company Information
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="md:col-span-2">
                    <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                      Company Name
                    </Label>
                    <div className="relative mt-1">
                      <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                      <Input
                        value={profile.company_name}
                        onChange={(e) => setProfile(prev => ({ ...prev, company_name: e.target.value }))}
                        placeholder="Your company name"
                        className="pl-10"
                      />
                    </div>
                  </div>
                  <div className="md:col-span-2">
                    <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                      Company Address
                    </Label>
                    <Textarea
                      value={profile.company_address}
                      onChange={(e) => setProfile(prev => ({ ...prev, company_address: e.target.value }))}
                      placeholder="Full address including street, building, floor"
                      className="mt-1"
                      rows={3}
                    />
                  </div>
                  <div>
                    <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                      City
                    </Label>
                    <Input
                      value={profile.city}
                      onChange={(e) => setProfile(prev => ({ ...prev, city: e.target.value }))}
                      placeholder="City"
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                      State
                    </Label>
                    <Input
                      value={profile.state}
                      onChange={(e) => setProfile(prev => ({ ...prev, state: e.target.value }))}
                      placeholder="State"
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                      Country
                    </Label>
                    <Input
                      value={profile.country}
                      onChange={(e) => setProfile(prev => ({ ...prev, country: e.target.value }))}
                      placeholder="Country"
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                      PIN Code
                    </Label>
                    <Input
                      value={profile.pincode}
                      onChange={(e) => setProfile(prev => ({ ...prev, pincode: e.target.value }))}
                      placeholder="PIN/ZIP Code"
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                      GSTIN (Optional)
                    </Label>
                    <div className="relative mt-1">
                      <FileText className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                      <Input
                        value={profile.gstin}
                        onChange={(e) => setProfile(prev => ({ ...prev, gstin: e.target.value.toUpperCase() }))}
                        placeholder="22AAAAA0000A1Z5"
                        className="pl-10 uppercase"
                        maxLength={15}
                      />
                    </div>
                  </div>
                  <div>
                    <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                      PAN (Optional)
                    </Label>
                    <Input
                      value={profile.pan}
                      onChange={(e) => setProfile(prev => ({ ...prev, pan: e.target.value.toUpperCase() }))}
                      placeholder="AAAAA0000A"
                      className="mt-1 uppercase"
                      maxLength={10}
                    />
                  </div>
                  <div>
                    <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                      Website (Optional)
                    </Label>
                    <div className="relative mt-1">
                      <Globe className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                      <Input
                        value={profile.website}
                        onChange={(e) => setProfile(prev => ({ ...prev, website: e.target.value }))}
                        placeholder="https://www.yourcompany.com"
                        className="pl-10"
                      />
                    </div>
                  </div>
                </div>

                <div className="flex justify-end pt-4 border-t">
                  <Button onClick={handleSaveProfile} disabled={saving} className="bg-orange-600 hover:bg-orange-700">
                    {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Save className="w-4 h-4 mr-2" />}
                    Save Changes
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Security Tab */}
          <TabsContent value="security">
            <div className="space-y-6">
              {/* 2FA Card */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Shield className="w-5 h-5 text-orange-600" />
                    Two-Factor Authentication
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg">
                    <div>
                      <p className="font-medium text-slate-900">Email OTP Verification</p>
                      <p className="text-sm text-slate-500">
                        {securitySettings.two_factor_enabled 
                          ? "A verification code will be sent to your email when you log in"
                          : "Add an extra layer of security to your account"
                        }
                      </p>
                    </div>
                    <div className={`px-3 py-1 rounded-full text-sm font-medium ${
                      securitySettings.two_factor_enabled 
                        ? "bg-green-100 text-green-700" 
                        : "bg-slate-200 text-slate-600"
                    }`}>
                      {securitySettings.two_factor_enabled ? "Enabled" : "Disabled"}
                    </div>
                  </div>
                  
                  <div className="mt-4 flex items-end gap-4">
                    <div className="flex-1">
                      <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                        Enter Password to {securitySettings.two_factor_enabled ? "Disable" : "Enable"} 2FA
                      </Label>
                      <Input
                        type="password"
                        value={twoFAPassword}
                        onChange={(e) => setTwoFAPassword(e.target.value)}
                        placeholder="Your current password"
                        className="mt-1"
                      />
                    </div>
                    <Button 
                      onClick={handleToggle2FA}
                      disabled={toggling2FA || !twoFAPassword}
                      variant={securitySettings.two_factor_enabled ? "outline" : "default"}
                      className={!securitySettings.two_factor_enabled ? "bg-green-600 hover:bg-green-700" : ""}
                    >
                      {toggling2FA && <Loader2 className="w-4 h-4 animate-spin mr-2" />}
                      {securitySettings.two_factor_enabled ? "Disable 2FA" : "Enable 2FA"}
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {/* Change Password Card */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Lock className="w-5 h-5 text-orange-600" />
                    Change Password
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {securitySettings.password_changed_at && (
                    <p className="text-sm text-slate-500">
                      Last changed: {new Date(securitySettings.password_changed_at).toLocaleDateString()}
                    </p>
                  )}
                  
                  <div className="space-y-4">
                    <div>
                      <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                        Current Password
                      </Label>
                      <div className="relative mt-1">
                        <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                        <Input
                          type={showPasswords ? "text" : "password"}
                          value={passwordData.current_password}
                          onChange={(e) => setPasswordData(prev => ({ ...prev, current_password: e.target.value }))}
                          placeholder="Enter current password"
                          className="pl-10"
                        />
                      </div>
                    </div>
                    <div>
                      <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                        New Password
                      </Label>
                      <div className="relative mt-1">
                        <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                        <Input
                          type={showPasswords ? "text" : "password"}
                          value={passwordData.new_password}
                          onChange={(e) => setPasswordData(prev => ({ ...prev, new_password: e.target.value }))}
                          placeholder="Enter new password"
                          className="pl-10"
                        />
                      </div>
                    </div>
                    <div>
                      <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                        Confirm New Password
                      </Label>
                      <div className="relative mt-1">
                        <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                        <Input
                          type={showPasswords ? "text" : "password"}
                          value={passwordData.confirm_password}
                          onChange={(e) => setPasswordData(prev => ({ ...prev, confirm_password: e.target.value }))}
                          placeholder="Confirm new password"
                          className="pl-10"
                        />
                        <button
                          type="button"
                          onClick={() => setShowPasswords(!showPasswords)}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                        >
                          {showPasswords ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                      </div>
                    </div>
                  </div>

                  <div className="flex justify-end pt-4 border-t">
                    <Button 
                      onClick={handleChangePassword} 
                      disabled={changingPassword || !passwordData.current_password || !passwordData.new_password}
                      className="bg-orange-600 hover:bg-orange-700"
                    >
                      {changingPassword ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Lock className="w-4 h-4 mr-2" />}
                      Change Password
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </DashboardLayout>
  );
};

export default BuyerProfile;
