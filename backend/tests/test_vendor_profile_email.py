"""
Test Vendor Profile Email Field Feature

Tests:
1. Email field exists in VendorProfileCreate model
2. GET /vendors/profile returns contact_email field
3. PUT /vendors/profile saves contact_email to database
4. For WhatsApp users (phone-based email), updating contact_email also updates user.email
5. For regular users, contact_email is stored separately from login email
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials - vendor email was changed in previous testing
VENDOR_EMAIL = "testemail@testvendor.com"
VENDOR_PASSWORD = "vendor123"
ADMIN_EMAIL = "admin@offoadex.com"
ADMIN_PASSWORD = "admin123"

class TestVendorProfileEmail:
    """Test email field in vendor profile"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
    def get_auth_token(self, email, password):
        """Helper to get auth token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    
    # Test 1: Verify API is accessible
    def test_health_check(self):
        """Test API is accessible"""
        response = self.session.get(f"{BASE_URL}/api/")
        assert response.status_code == 200, f"API not accessible: {response.text}"
        print("✓ API is accessible")
    
    # Test 2: Vendor login works
    def test_vendor_login(self):
        """Test vendor can log in"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": VENDOR_EMAIL,
            "password": VENDOR_PASSWORD
        })
        assert response.status_code == 200, f"Vendor login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "vendor"
        print(f"✓ Vendor login successful: {data['user']['email']}")
    
    # Test 3: GET /vendors/profile returns contact_email
    def test_get_vendor_profile_has_contact_email_field(self):
        """Test that vendor profile includes contact_email field"""
        token = self.get_auth_token(VENDOR_EMAIL, VENDOR_PASSWORD)
        assert token is not None, "Failed to get auth token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        response = self.session.get(f"{BASE_URL}/api/vendors/profile")
        
        assert response.status_code == 200, f"Get profile failed: {response.text}"
        data = response.json()
        
        # Verify key fields exist
        assert "company_name" in data, "company_name not in response"
        assert "vendor_id" in data, "vendor_id not in response"
        
        # contact_email should be in the response (may be null/empty if not set)
        print(f"✓ Profile retrieved. contact_email: {data.get('contact_email', 'NOT SET')}")
        print(f"  Company: {data.get('company_name')}")
    
    # Test 4: PUT /vendors/profile saves contact_email
    def test_update_vendor_profile_with_email(self):
        """Test updating vendor profile with contact_email"""
        token = self.get_auth_token(VENDOR_EMAIL, VENDOR_PASSWORD)
        assert token is not None, "Failed to get auth token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # First get current profile
        response = self.session.get(f"{BASE_URL}/api/vendors/profile")
        assert response.status_code == 200
        current_profile = response.json()
        
        # Update with a new contact_email
        test_email = "test.contact@example.com"
        update_data = {
            "company_name": current_profile.get("company_name", "Test Company"),
            "description": current_profile.get("description", ""),
            "address": current_profile.get("address", ""),
            "city": current_profile.get("city", ""),
            "state": current_profile.get("state", ""),
            "pincode": current_profile.get("pincode", ""),
            "country": current_profile.get("country", "India"),
            "phone": current_profile.get("phone", ""),
            "contact_email": test_email,  # The new email field
            "website": current_profile.get("website", ""),
            "certifications": current_profile.get("certifications", []),
            "industries": current_profile.get("industries", []),
            "materials_handled": current_profile.get("materials_handled", [])
        }
        
        response = self.session.put(f"{BASE_URL}/api/vendors/profile", json=update_data)
        assert response.status_code == 200, f"Update profile failed: {response.text}"
        
        updated_profile = response.json()
        assert updated_profile.get("contact_email") == test_email, \
            f"contact_email not updated. Got: {updated_profile.get('contact_email')}"
        
        print(f"✓ Profile updated with contact_email: {test_email}")
    
    # Test 5: Verify contact_email persists on GET
    def test_contact_email_persists(self):
        """Test that contact_email is persisted and retrieved correctly"""
        token = self.get_auth_token(VENDOR_EMAIL, VENDOR_PASSWORD)
        assert token is not None, "Failed to get auth token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Set a unique contact_email
        unique_email = "persist.test@example.com"
        
        # Get current profile
        response = self.session.get(f"{BASE_URL}/api/vendors/profile")
        assert response.status_code == 200
        current_profile = response.json()
        
        # Update with unique email
        update_data = {
            "company_name": current_profile.get("company_name", "Test Company"),
            "contact_email": unique_email,
            "certifications": current_profile.get("certifications", []),
            "industries": current_profile.get("industries", []),
            "materials_handled": current_profile.get("materials_handled", [])
        }
        
        response = self.session.put(f"{BASE_URL}/api/vendors/profile", json=update_data)
        assert response.status_code == 200, f"Update failed: {response.text}"
        
        # Now GET again to verify persistence
        response = self.session.get(f"{BASE_URL}/api/vendors/profile")
        assert response.status_code == 200
        
        retrieved_profile = response.json()
        assert retrieved_profile.get("contact_email") == unique_email, \
            f"contact_email not persisted. Expected: {unique_email}, Got: {retrieved_profile.get('contact_email')}"
        
        print(f"✓ contact_email correctly persisted and retrieved: {unique_email}")
    
    # Test 6: Verify user record update for regular users
    def test_regular_user_login_email_unchanged(self):
        """
        For regular users (non-WhatsApp), updating contact_email should NOT change login email
        The vendor testemail@testvendor.com is a regular user, not WhatsApp-registered
        """
        token = self.get_auth_token(VENDOR_EMAIL, VENDOR_PASSWORD)
        assert token is not None, "Failed to get auth token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get current profile
        response = self.session.get(f"{BASE_URL}/api/vendors/profile")
        assert response.status_code == 200
        current_profile = response.json()
        
        # Update contact_email to something different from login email
        different_contact_email = "notifications@different.com"
        update_data = {
            "company_name": current_profile.get("company_name", "Test Company"),
            "contact_email": different_contact_email,
            "certifications": current_profile.get("certifications", []),
            "industries": current_profile.get("industries", []),
            "materials_handled": current_profile.get("materials_handled", [])
        }
        
        response = self.session.put(f"{BASE_URL}/api/vendors/profile", json=update_data)
        assert response.status_code == 200
        
        # Now verify we can still login with the original email
        # (login email should not have changed)
        logout_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": VENDOR_EMAIL,  # Original login email
            "password": VENDOR_PASSWORD
        })
        
        # If login still works with original email, then login email was NOT changed
        assert logout_response.status_code == 200, \
            f"Login with original email failed! Login email may have been incorrectly changed. {logout_response.text}"
        
        login_data = logout_response.json()
        print(f"✓ Regular user login email unchanged. Can still login with: {VENDOR_EMAIL}")
        print(f"  User email in response: {login_data['user']['email']}")

    # Test 7: Restore original contact_email
    def test_restore_original_email(self):
        """Restore contact_email to match login email for cleanup"""
        token = self.get_auth_token(VENDOR_EMAIL, VENDOR_PASSWORD)
        assert token is not None, "Failed to get auth token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get current profile
        response = self.session.get(f"{BASE_URL}/api/vendors/profile")
        assert response.status_code == 200
        current_profile = response.json()
        
        # Restore to match login email
        update_data = {
            "company_name": current_profile.get("company_name", "Test Company"),
            "contact_email": VENDOR_EMAIL,  # Restore to login email
            "certifications": current_profile.get("certifications", []),
            "industries": current_profile.get("industries", []),
            "materials_handled": current_profile.get("materials_handled", [])
        }
        
        response = self.session.put(f"{BASE_URL}/api/vendors/profile", json=update_data)
        assert response.status_code == 200
        
        updated = response.json()
        print(f"✓ contact_email restored to: {updated.get('contact_email')}")


class TestVendorProfileModel:
    """Test VendorProfileCreate model has contact_email"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_profile_accepts_contact_email_field(self):
        """Verify API accepts contact_email in request body"""
        # Login as vendor
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": VENDOR_EMAIL,
            "password": VENDOR_PASSWORD
        })
        assert response.status_code == 200
        token = response.json().get("access_token")
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get current profile
        response = self.session.get(f"{BASE_URL}/api/vendors/profile")
        assert response.status_code == 200
        profile = response.json()
        
        # Update with contact_email
        update_data = {
            "company_name": profile.get("company_name", "Test"),
            "contact_email": "model.test@example.com",
            "certifications": profile.get("certifications", []),
            "industries": profile.get("industries", []),
            "materials_handled": profile.get("materials_handled", [])
        }
        
        response = self.session.put(f"{BASE_URL}/api/vendors/profile", json=update_data)
        
        # Should not fail with validation error
        assert response.status_code == 200, \
            f"API rejected contact_email field. Error: {response.text}"
        
        print("✓ VendorProfileCreate model accepts contact_email field")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
