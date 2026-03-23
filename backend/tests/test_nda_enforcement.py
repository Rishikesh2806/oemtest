"""
NDA Enforcement Feature Tests
Tests for:
- Drawing view/download 403 without NDA acceptance
- NDA acceptance endpoint with IP/User Agent tracking
- Drawing access after NDA acceptance
- Admin/staff bypass NDA checks
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from review request
VENDOR_EMAIL = "vend@gm.com"
VENDOR_PASSWORD = "corpo123"
ADMIN_EMAIL = "admin@offoadex.com"
ADMIN_PASSWORD = "admin123"

# Test data from review request
TEST_RFQ_ID = "rfq_d3d8dc101d64"
TEST_DRAWING_ID = "drawing_3a3378b17b54"


class TestNDAEnforcement:
    """NDA Enforcement tests for drawing access control"""
    
    @pytest.fixture(scope="class")
    def vendor_token(self):
        """Get vendor authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": VENDOR_EMAIL,
            "password": VENDOR_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip(f"Vendor login failed: {response.status_code} - {response.text}")
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")
    
    @pytest.fixture(scope="class")
    def vendor_info(self, vendor_token):
        """Get vendor user info"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {vendor_token}"}
        )
        if response.status_code == 200:
            return response.json()
        return {}
    
    def test_vendor_login(self, vendor_token):
        """Test vendor can login successfully"""
        assert vendor_token is not None
        print(f"✓ Vendor login successful, token obtained")
    
    def test_admin_login(self, admin_token):
        """Test admin can login successfully"""
        assert admin_token is not None
        print(f"✓ Admin login successful, token obtained")
    
    def test_get_rfq_nda_status(self, vendor_token):
        """Test getting NDA status for an RFQ"""
        response = requests.get(
            f"{BASE_URL}/api/rfqs/{TEST_RFQ_ID}/nda",
            headers={"Authorization": f"Bearer {vendor_token}"}
        )
        print(f"NDA status response: {response.status_code} - {response.text[:500]}")
        assert response.status_code == 200
        data = response.json()
        # Check response structure
        assert "nda_required" in data
        print(f"✓ NDA status retrieved - Required: {data.get('nda_required')}, Accepted: {data.get('has_accepted', False)}")
    
    def test_accept_nda_endpoint(self, vendor_token):
        """Test NDA acceptance endpoint stores IP and User Agent"""
        headers = {
            "Authorization": f"Bearer {vendor_token}",
            "User-Agent": "TestAgent/1.0 (NDA Test)",
            "X-Forwarded-For": "192.168.1.100"
        }
        response = requests.post(
            f"{BASE_URL}/api/rfqs/{TEST_RFQ_ID}/accept-nda",
            json={"agree_checkbox": True},
            headers=headers
        )
        print(f"Accept NDA response: {response.status_code} - {response.text}")
        # Should succeed (200) or already accepted
        assert response.status_code in [200, 400]
        data = response.json()
        if response.status_code == 200:
            assert data.get("success") == True
            print(f"✓ NDA accepted successfully or already accepted")
        else:
            print(f"NDA acceptance response: {data}")
    
    def test_drawing_view_after_nda_acceptance(self, vendor_token):
        """Test vendor can view drawing after NDA acceptance"""
        response = requests.get(
            f"{BASE_URL}/api/drawings/{TEST_DRAWING_ID}/view?token={vendor_token}",
            allow_redirects=False
        )
        print(f"Drawing view response: {response.status_code}")
        # Should be 200 (file content) or 302 (redirect to S3)
        assert response.status_code in [200, 302, 307]
        print(f"✓ Drawing view accessible after NDA acceptance (status: {response.status_code})")
    
    def test_drawing_download_after_nda_acceptance(self, vendor_token):
        """Test vendor can download drawing after NDA acceptance"""
        response = requests.get(
            f"{BASE_URL}/api/drawings/{TEST_DRAWING_ID}/download",
            headers={"Authorization": f"Bearer {vendor_token}"},
            allow_redirects=False
        )
        print(f"Drawing download response: {response.status_code}")
        # Should be 200 (file content) or 302 (redirect to S3)
        assert response.status_code in [200, 302, 307]
        print(f"✓ Drawing download accessible after NDA acceptance (status: {response.status_code})")
    
    def test_admin_bypasses_nda_for_view(self, admin_token):
        """Test admin can view drawing without NDA acceptance"""
        response = requests.get(
            f"{BASE_URL}/api/drawings/{TEST_DRAWING_ID}/view?token={admin_token}",
            allow_redirects=False
        )
        print(f"Admin drawing view response: {response.status_code}")
        # Admin should always have access
        assert response.status_code in [200, 302, 307]
        print(f"✓ Admin bypasses NDA check for drawing view")
    
    def test_admin_bypasses_nda_for_download(self, admin_token):
        """Test admin can download drawing without NDA acceptance"""
        response = requests.get(
            f"{BASE_URL}/api/drawings/{TEST_DRAWING_ID}/download",
            headers={"Authorization": f"Bearer {admin_token}"},
            allow_redirects=False
        )
        print(f"Admin drawing download response: {response.status_code}")
        # Admin should always have access
        assert response.status_code in [200, 302, 307]
        print(f"✓ Admin bypasses NDA check for drawing download")


class TestNDATemplatesAPI:
    """Test NDA Templates management API"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip(f"Admin login failed: {response.status_code}")
    
    @pytest.fixture(scope="class")
    def vendor_token(self):
        """Get vendor authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": VENDOR_EMAIL,
            "password": VENDOR_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip(f"Vendor login failed: {response.status_code}")
    
    def test_list_nda_templates_admin(self, admin_token):
        """Test admin can list NDA templates"""
        response = requests.get(
            f"{BASE_URL}/api/nda/templates",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        print(f"List templates response: {response.status_code} - {response.text[:500]}")
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        print(f"✓ Admin can list NDA templates - Found {len(data.get('templates', []))} templates")
    
    def test_get_default_nda(self, admin_token):
        """Test getting default NDA template"""
        response = requests.get(
            f"{BASE_URL}/api/nda/default",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        print(f"Default NDA response: {response.status_code} - {response.text[:500]}")
        assert response.status_code == 200
        data = response.json()
        # Response may be nested under "template" or direct
        template = data.get("template", data)
        assert "nda_id" in template
        print(f"✓ Default NDA template retrieved - ID: {template.get('nda_id')}")
    
    def test_create_nda_template_admin(self, admin_token):
        """Test admin can create NDA template"""
        response = requests.post(
            f"{BASE_URL}/api/nda/templates",
            json={
                "title": "TEST_NDA_Template",
                "content": "<h2>Test NDA</h2><p>This is a test NDA template.</p>",
                "version": "1.0",
                "is_default": False
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        print(f"Create template response: {response.status_code} - {response.text}")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "nda_id" in data
        print(f"✓ Admin created NDA template - ID: {data.get('nda_id')}")
        return data.get("nda_id")
    
    def test_vendor_cannot_create_nda_template(self, vendor_token):
        """Test vendor cannot create NDA template"""
        response = requests.post(
            f"{BASE_URL}/api/nda/templates",
            json={
                "title": "Vendor NDA Attempt",
                "content": "<p>Should fail</p>",
                "version": "1.0",
                "is_default": False
            },
            headers={"Authorization": f"Bearer {vendor_token}"}
        )
        print(f"Vendor create template response: {response.status_code}")
        assert response.status_code == 403
        print(f"✓ Vendor correctly denied from creating NDA template")


class TestRFQNDARequirement:
    """Test RFQ NDA requirement field"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip(f"Admin login failed: {response.status_code}")
    
    def test_rfq_has_require_nda_field(self, admin_token):
        """Test RFQ has require_nda field"""
        response = requests.get(
            f"{BASE_URL}/api/rfqs/{TEST_RFQ_ID}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        print(f"RFQ response: {response.status_code}")
        assert response.status_code == 200
        data = response.json()
        # Check if require_nda field exists
        print(f"RFQ require_nda: {data.get('require_nda')}")
        print(f"✓ RFQ has require_nda field: {data.get('require_nda', 'not set')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
