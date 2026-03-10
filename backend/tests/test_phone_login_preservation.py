"""
Test that phone login is preserved after updating contact_email
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# WhatsApp-registered vendor with phone_login=True
PHONE_NUMBER = "919999888877"
PASSWORD = "123456"

class TestPhoneLoginPreservation:
    """Test phone login works after email update"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_phone_login_works(self):
        """Test phone number login works"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PHONE_NUMBER,
            "password": PASSWORD
        })
        assert response.status_code == 200, f"Phone login failed: {response.text}"
        data = response.json()
        assert data["user"]["email"] == PHONE_NUMBER
        print(f"✓ Phone login works: {PHONE_NUMBER}")
    
    def test_update_contact_email_preserves_phone_login(self):
        """Test that updating contact_email does NOT break phone login"""
        # Login with phone
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PHONE_NUMBER,
            "password": PASSWORD
        })
        assert response.status_code == 200
        token = response.json()["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get current profile
        response = self.session.get(f"{BASE_URL}/api/vendors/profile")
        assert response.status_code == 200
        profile = response.json()
        
        # Update contact_email
        new_email = "phone.user.test@example.com"
        update_data = {
            "company_name": profile.get("company_name", "Phone Test Company"),
            "contact_email": new_email,
            "certifications": profile.get("certifications", []),
            "industries": profile.get("industries", []),
            "materials_handled": profile.get("materials_handled", [])
        }
        
        response = self.session.put(f"{BASE_URL}/api/vendors/profile", json=update_data)
        assert response.status_code == 200
        
        # Verify contact_email was updated
        updated = response.json()
        assert updated.get("contact_email") == new_email
        print(f"✓ Contact email updated to: {new_email}")
        
        # NOW verify phone login STILL works
        # Create new session to ensure no cached auth
        new_session = requests.Session()
        new_session.headers.update({"Content-Type": "application/json"})
        
        response = new_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PHONE_NUMBER,
            "password": PASSWORD
        })
        
        assert response.status_code == 200, f"Phone login broken after email update! {response.text}"
        data = response.json()
        assert data["user"]["email"] == PHONE_NUMBER, "Login email changed unexpectedly"
        print(f"✓ Phone login PRESERVED after contact_email update!")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
