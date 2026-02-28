import requests
import sys
import time
import base64
from datetime import datetime
import json

class OffoadexAPITester:
    def __init__(self):
        self.base_url = "https://rfq-forge.preview.emergentagent.com/api"
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        self.token = None
        self.user_data = None
        self.rfq_id = None
        self.vendor_id = None
        self.tests_run = 0
        self.tests_passed = 0
        
    def log_test(self, test_name, success, response_data=None, error=None):
        """Log test results"""
        self.tests_run += 1
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} | {test_name}")
        
        if success:
            self.tests_passed += 1
            if response_data and isinstance(response_data, dict):
                print(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")
        else:
            print(f"   Error: {error}")
        print()
        
    def test_health_check(self):
        """Test API health check"""
        try:
            response = self.session.get(f"{self.base_url}/health")
            success = response.status_code == 200
            data = response.json() if success else None
            self.log_test("Health Check", success, data, 
                         f"Status: {response.status_code}" if not success else None)
            return success
        except Exception as e:
            self.log_test("Health Check", False, error=str(e))
            return False
    
    def test_user_registration(self):
        """Test user registration"""
        timestamp = int(time.time())
        try:
            user_data = {
                "name": "Test Buyer",
                "email": f"test.buyer.{timestamp}@example.com",
                "password": "TestPass123!",
                "role": "buyer"
            }
            
            response = self.session.post(f"{self.base_url}/auth/register", json=user_data)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                self.token = data.get("access_token")
                self.user_data = data.get("user")
                # Set authorization header for future requests
                self.session.headers.update({'Authorization': f'Bearer {self.token}'})
                
            self.log_test("User Registration", success, 
                         response.json() if success else None,
                         f"Status: {response.status_code}, Response: {response.text}" if not success else None)
            return success
        except Exception as e:
            self.log_test("User Registration", False, error=str(e))
            return False
    
    def test_user_login(self):
        """Test user login (using same credentials from registration)"""
        if not self.user_data:
            self.log_test("User Login", False, error="No user data from registration")
            return False
            
        try:
            login_data = {
                "email": self.user_data["email"],
                "password": "TestPass123!"
            }
            
            response = self.session.post(f"{self.base_url}/auth/login", json=login_data)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                self.token = data.get("access_token")
                self.session.headers.update({'Authorization': f'Bearer {self.token}'})
                
            self.log_test("User Login", success, 
                         response.json() if success else None,
                         f"Status: {response.status_code}" if not success else None)
            return success
        except Exception as e:
            self.log_test("User Login", False, error=str(e))
            return False
    
    def test_get_current_user(self):
        """Test getting current user info"""
        try:
            response = self.session.get(f"{self.base_url}/auth/me")
            success = response.status_code == 200
            
            self.log_test("Get Current User", success, 
                         response.json() if success else None,
                         f"Status: {response.status_code}" if not success else None)
            return success
        except Exception as e:
            self.log_test("Get Current User", False, error=str(e))
            return False
    
    def test_create_rfq(self):
        """Test RFQ creation"""
        try:
            rfq_data = {
                "title": "Test CNC Bracket",
                "description": "Test bracket for API testing",
                "material_type": "Aluminum",
                "quantity": 10,
                "tolerance": 0.1,
                "surface_finish": "Anodized",
                "supply_type": "vendor_material"
            }
            
            response = self.session.post(f"{self.base_url}/rfqs", json=rfq_data)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                self.rfq_id = data.get("rfq_id")
                
            self.log_test("Create RFQ", success, 
                         response.json() if success else None,
                         f"Status: {response.status_code}" if not success else None)
            return success
        except Exception as e:
            self.log_test("Create RFQ", False, error=str(e))
            return False
    
    def test_list_rfqs(self):
        """Test listing RFQs"""
        try:
            response = self.session.get(f"{self.base_url}/rfqs")
            success = response.status_code == 200
            
            self.log_test("List RFQs", success, 
                         response.json() if success else None,
                         f"Status: {response.status_code}" if not success else None)
            return success
        except Exception as e:
            self.log_test("List RFQs", False, error=str(e))
            return False
    
    def test_get_rfq_details(self):
        """Test getting RFQ details"""
        if not self.rfq_id:
            self.log_test("Get RFQ Details", False, error="No RFQ ID available")
            return False
            
        try:
            response = self.session.get(f"{self.base_url}/rfqs/{self.rfq_id}")
            success = response.status_code == 200
            
            self.log_test("Get RFQ Details", success, 
                         response.json() if success else None,
                         f"Status: {response.status_code}" if not success else None)
            return success
        except Exception as e:
            self.log_test("Get RFQ Details", False, error=str(e))
            return False
    
    def test_upload_drawing(self):
        """Test drawing upload"""
        if not self.rfq_id:
            self.log_test("Upload Drawing", False, error="No RFQ ID available")
            return False
            
        try:
            # Create a simple test file content
            test_content = b"Test drawing file content for API testing"
            
            files = {'file': ('test_drawing.pdf', test_content, 'application/pdf')}
            # Remove Content-Type header for file upload
            headers = {k: v for k, v in self.session.headers.items() if k != 'Content-Type'}
            
            response = requests.post(
                f"{self.base_url}/rfqs/{self.rfq_id}/drawings",
                files=files,
                headers=headers
            )
            
            success = response.status_code == 200
            
            self.log_test("Upload Drawing", success, 
                         response.json() if success else None,
                         f"Status: {response.status_code}" if not success else None)
            return success
        except Exception as e:
            self.log_test("Upload Drawing", False, error=str(e))
            return False
    
    def test_ai_analysis(self):
        """Test AI drawing analysis"""
        if not self.rfq_id:
            self.log_test("AI Analysis", False, error="No RFQ ID available")
            return False
            
        try:
            response = self.session.post(f"{self.base_url}/rfqs/{self.rfq_id}/analyze")
            success = response.status_code == 200
            
            # AI analysis might take longer, so we wait a bit
            if success:
                time.sleep(2)
                
            self.log_test("AI Analysis", success, 
                         response.json() if success else None,
                         f"Status: {response.status_code}" if not success else None)
            return success
        except Exception as e:
            self.log_test("AI Analysis", False, error=str(e))
            return False
    
    def test_vendor_matching(self):
        """Test vendor matching"""
        if not self.rfq_id:
            self.log_test("Vendor Matching", False, error="No RFQ ID available")
            return False
            
        try:
            response = self.session.post(f"{self.base_url}/rfqs/{self.rfq_id}/match")
            success = response.status_code == 200
            
            self.log_test("Vendor Matching", success, 
                         response.json() if success else None,
                         f"Status: {response.status_code}" if not success else None)
            return success
        except Exception as e:
            self.log_test("Vendor Matching", False, error=str(e))
            return False
    
    def test_buyer_dashboard(self):
        """Test buyer dashboard data"""
        try:
            response = self.session.get(f"{self.base_url}/dashboard/buyer")
            success = response.status_code == 200
            
            self.log_test("Buyer Dashboard", success, 
                         response.json() if success else None,
                         f"Status: {response.status_code}" if not success else None)
            return success
        except Exception as e:
            self.log_test("Buyer Dashboard", False, error=str(e))
            return False
    
    def test_vendor_registration_and_profile(self):
        """Test vendor user registration and profile creation"""
        timestamp = int(time.time())
        try:
            # Register vendor user
            vendor_user_data = {
                "name": "Test Vendor",
                "email": f"test.vendor.{timestamp}@example.com",
                "password": "TestPass123!",
                "role": "vendor"
            }
            
            response = self.session.post(f"{self.base_url}/auth/register", json=vendor_user_data)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                vendor_token = data.get("access_token")
                vendor_headers = {'Authorization': f'Bearer {vendor_token}', 'Content-Type': 'application/json'}
                
                # Create vendor profile
                vendor_profile_data = {
                    "company_name": "Test Manufacturing Co",
                    "description": "Test manufacturing company",
                    "city": "Test City",
                    "country": "Test Country",
                    "industries": ["Automotive", "Aerospace"],
                    "materials_handled": ["Aluminum", "Steel"]
                }
                
                profile_response = requests.post(
                    f"{self.base_url}/vendors/profile",
                    json=vendor_profile_data,
                    headers=vendor_headers
                )
                
                profile_success = profile_response.status_code == 200
                if profile_success:
                    profile_data = profile_response.json()
                    self.vendor_id = profile_data.get("vendor_id")
                
                self.log_test("Vendor Registration + Profile", profile_success, 
                             profile_response.json() if profile_success else None,
                             f"Profile Status: {profile_response.status_code}" if not profile_success else None)
                return profile_success
            else:
                self.log_test("Vendor Registration + Profile", False, 
                             error=f"Registration failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Vendor Registration + Profile", False, error=str(e))
            return False
    
    def run_all_tests(self):
        """Run all API tests"""
        print("🧪 Starting Offoadex API Tests")
        print("=" * 50)
        
        # Core API tests
        self.test_health_check()
        self.test_user_registration()
        self.test_user_login()
        self.test_get_current_user()
        
        # RFQ workflow tests
        self.test_create_rfq()
        self.test_list_rfqs()
        self.test_get_rfq_details()
        self.test_upload_drawing()
        
        # AI and matching tests (these might fail if services are not configured)
        self.test_ai_analysis()
        self.test_vendor_matching()
        
        # Dashboard tests
        self.test_buyer_dashboard()
        
        # Vendor tests
        self.test_vendor_registration_and_profile()
        
        # Summary
        print("=" * 50)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} tests passed")
        success_rate = (self.tests_passed / self.tests_run) * 100 if self.tests_run > 0 else 0
        print(f"📈 Success Rate: {success_rate:.1f}%")
        
        return self.tests_passed, self.tests_run

def main():
    tester = OffoadexAPITester()
    passed, total = tester.run_all_tests()
    
    # Return appropriate exit code
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())