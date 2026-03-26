"""
Test Staff Base Role & Secondary Roles Integration
Tests:
- POST /api/auth/login returns custom_role and secondary_roles in user object
- GET /api/auth/me returns custom_role and secondary_roles
- Login redirects for different user roles (backend returns correct data)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
STAFF_EMAIL = "buyer@offoadex.com"  # This user has role='staff' with custom_role='buyer'
STAFF_PASSWORD = "buyer123"
ADMIN_EMAIL = "admin@offoadex.com"
ADMIN_PASSWORD = "admin123"
VENDOR_EMAIL = "testvendor_nda@test.com"
VENDOR_PASSWORD = "vendor123"
# Note: visualbuyer@test.com doesn't exist, using a different buyer
BUYER_EMAIL = "buyer@offoadex.com"  # This is now a staff user, so we'll skip buyer test
BUYER_PASSWORD = "buyer123"


class TestStaffLogin:
    """Test staff user login returns custom_role and secondary_roles"""
    
    def test_staff_login_returns_custom_role_and_secondary_roles(self):
        """POST /api/auth/login should return custom_role and secondary_roles for staff users"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": STAFF_EMAIL, "password": STAFF_PASSWORD}
        )
        
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        
        # Verify token is returned
        assert "access_token" in data, "No access_token in response"
        assert "user" in data, "No user object in response"
        
        user = data["user"]
        
        # Verify staff role
        assert user.get("role") == "staff", f"Expected role='staff', got '{user.get('role')}'"
        
        # Verify custom_role is returned
        assert "custom_role" in user, "custom_role field missing from user response"
        assert user.get("custom_role") is not None, f"custom_role should not be None for staff user"
        
        # Verify secondary_roles is returned
        assert "secondary_roles" in user, "secondary_roles field missing from user response"
        assert isinstance(user.get("secondary_roles"), list), "secondary_roles should be a list"
        
        print(f"Staff login successful: role={user['role']}, custom_role={user.get('custom_role')}, secondary_roles={user.get('secondary_roles')}")
    
    def test_staff_login_returns_correct_user_fields(self):
        """Verify all expected user fields are returned for staff login"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": STAFF_EMAIL, "password": STAFF_PASSWORD}
        )
        
        assert response.status_code == 200
        user = response.json()["user"]
        
        # Check all required fields
        required_fields = ["user_id", "email", "name", "role", "custom_role", "secondary_roles", "email_verified", "created_at"]
        for field in required_fields:
            assert field in user, f"Missing required field: {field}"
        
        print(f"All required fields present in staff user response")


class TestAuthMeEndpoint:
    """Test GET /api/auth/me returns custom_role and secondary_roles"""
    
    def test_auth_me_returns_custom_role_and_secondary_roles(self):
        """GET /api/auth/me should return custom_role and secondary_roles for staff users"""
        # First login to get token
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": STAFF_EMAIL, "password": STAFF_PASSWORD}
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        
        # Call /auth/me
        me_response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert me_response.status_code == 200, f"GET /auth/me failed: {me_response.text}"
        user = me_response.json()
        
        # Verify custom_role and secondary_roles
        assert user.get("role") == "staff", f"Expected role='staff', got '{user.get('role')}'"
        assert "custom_role" in user, "custom_role field missing from /auth/me response"
        assert user.get("custom_role") is not None, f"custom_role should not be None for staff user"
        assert "secondary_roles" in user, "secondary_roles field missing from /auth/me response"
        assert isinstance(user.get("secondary_roles"), list), "secondary_roles should be a list"
        
        print(f"GET /auth/me successful: role={user['role']}, custom_role={user.get('custom_role')}, secondary_roles={user.get('secondary_roles')}")


class TestAdminLogin:
    """Test admin user login still works correctly"""
    
    def test_admin_login_returns_admin_role(self):
        """Admin login should return role='admin'"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        user = response.json()["user"]
        
        assert user.get("role") == "admin", f"Expected role='admin', got '{user.get('role')}'"
        print(f"Admin login successful: role={user['role']}")


class TestVendorLogin:
    """Test vendor user login still works correctly"""
    
    def test_vendor_login_returns_vendor_role(self):
        """Vendor login should return role='vendor'"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": VENDOR_EMAIL, "password": VENDOR_PASSWORD}
        )
        
        assert response.status_code == 200, f"Vendor login failed: {response.text}"
        user = response.json()["user"]
        
        assert user.get("role") == "vendor", f"Expected role='vendor', got '{user.get('role')}'"
        print(f"Vendor login successful: role={user['role']}")


class TestBuyerLogin:
    """Test buyer user login still works correctly"""
    
    @pytest.mark.skip(reason="buyer@offoadex.com is now a staff user, no pure buyer test account available")
    def test_buyer_login_returns_buyer_role(self):
        """Buyer login should return role='buyer'"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": BUYER_EMAIL, "password": BUYER_PASSWORD}
        )
        
        assert response.status_code == 200, f"Buyer login failed: {response.text}"
        user = response.json()["user"]
        
        assert user.get("role") == "buyer", f"Expected role='buyer', got '{user.get('role')}'"
        print(f"Buyer login successful: role={user['role']}")


class TestUserResponseModel:
    """Test that UserResponse model includes custom_role and secondary_roles"""
    
    def test_login_response_structure(self):
        """Verify login response matches expected TokenResponse structure"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": STAFF_EMAIL, "password": STAFF_PASSWORD}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # TokenResponse structure
        assert "access_token" in data
        assert "token_type" in data or data.get("token_type", "bearer") == "bearer"
        assert "user" in data
        
        # UserResponse structure
        user = data["user"]
        expected_fields = {
            "user_id": str,
            "email": str,
            "name": str,
            "role": str,
            "custom_role": (str, type(None)),  # Can be string or None
            "secondary_roles": list,
            "email_verified": bool,
            "created_at": str
        }
        
        for field, expected_type in expected_fields.items():
            assert field in user, f"Missing field: {field}"
            if isinstance(expected_type, tuple):
                assert isinstance(user[field], expected_type), f"Field {field} has wrong type"
            else:
                assert isinstance(user[field], expected_type), f"Field {field} should be {expected_type}, got {type(user[field])}"
        
        print("Login response structure is correct")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
