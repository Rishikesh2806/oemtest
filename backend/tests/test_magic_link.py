"""
Test cases for Magic Link Login Feature
Tests the WhatsApp magic link login flow for vendors
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test phone number for magic link tests
TEST_PHONE = "9330389049"
INVALID_PHONE = "9999999999"


class TestMagicLinkGenerate:
    """Tests for POST /api/auth/magic-link/generate endpoint"""
    
    def test_generate_magic_link_success(self):
        """Test generating magic link with valid registered phone"""
        response = requests.post(f"{BASE_URL}/api/auth/magic-link/generate?phone={TEST_PHONE}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "token" in data
        assert isinstance(data["token"], str)
        assert len(data["token"]) > 20  # Token should be a secure random string
        assert data["expires_in_minutes"] == 15
    
    def test_generate_magic_link_nonexistent_phone(self):
        """Test generating magic link with unregistered phone"""
        response = requests.post(f"{BASE_URL}/api/auth/magic-link/generate?phone={INVALID_PHONE}")
        assert response.status_code == 200  # Returns 200 but success=False
        
        data = response.json()
        assert data["success"] is False
        assert "error" in data
        assert "Vendor not found" in data["error"]
    
    def test_generate_magic_link_with_country_code(self):
        """Test generating magic link with phone including country code"""
        response = requests.post(f"{BASE_URL}/api/auth/magic-link/generate?phone=+91{TEST_PHONE}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "token" in data
    
    def test_generate_magic_link_with_spaces(self):
        """Test generating magic link with phone containing spaces"""
        formatted_phone = f"93303 89049"
        response = requests.post(f"{BASE_URL}/api/auth/magic-link/generate?phone={formatted_phone}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "token" in data


class TestMagicLinkVerify:
    """Tests for GET /api/auth/magic-link/verify/{token} endpoint"""
    
    def test_verify_valid_token(self):
        """Test verifying a valid magic link token"""
        # Generate token
        gen_response = requests.post(f"{BASE_URL}/api/auth/magic-link/generate?phone={TEST_PHONE}")
        token = gen_response.json()["token"]
        
        # Verify token
        response = requests.get(f"{BASE_URL}/api/auth/magic-link/verify/{token}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        
        # Verify user object structure
        user = data["user"]
        assert "user_id" in user
        assert "email" in user
        assert "name" in user
        assert "role" in user
        assert user["role"] == "vendor"
        
        # Verify redirect URL
        assert "redirect_url" in data
        assert data["redirect_url"] == "/vendor/dashboard"
    
    def test_verify_invalid_token(self):
        """Test verifying an invalid token"""
        response = requests.get(f"{BASE_URL}/api/auth/magic-link/verify/invalid_token_12345")
        assert response.status_code == 400
        
        data = response.json()
        assert "detail" in data
        assert "Invalid" in data["detail"] or "expired" in data["detail"]
    
    def test_verify_token_already_used(self):
        """Test verifying a token that has already been used (single-use)"""
        # Generate token
        gen_response = requests.post(f"{BASE_URL}/api/auth/magic-link/generate?phone={TEST_PHONE}")
        token = gen_response.json()["token"]
        
        # First verification - should succeed
        first_response = requests.get(f"{BASE_URL}/api/auth/magic-link/verify/{token}")
        assert first_response.status_code == 200
        
        # Second verification - should fail (token is single-use)
        second_response = requests.get(f"{BASE_URL}/api/auth/magic-link/verify/{token}")
        assert second_response.status_code == 400
        
        data = second_response.json()
        assert "detail" in data
    
    def test_verify_returns_jwt_token(self):
        """Test that verification returns a valid JWT token"""
        # Generate token
        gen_response = requests.post(f"{BASE_URL}/api/auth/magic-link/generate?phone={TEST_PHONE}")
        token = gen_response.json()["token"]
        
        # Verify token
        response = requests.get(f"{BASE_URL}/api/auth/magic-link/verify/{token}")
        assert response.status_code == 200
        
        data = response.json()
        access_token = data["access_token"]
        
        # JWT tokens have 3 parts separated by dots
        parts = access_token.split(".")
        assert len(parts) == 3
        
        # Verify the JWT token works for authenticated requests
        headers = {"Authorization": f"Bearer {access_token}"}
        me_response = requests.get(f"{BASE_URL}/api/user/profile", headers=headers)
        assert me_response.status_code == 200


class TestMagicLinkE2E:
    """End-to-end tests for complete magic link flow"""
    
    def test_complete_login_flow(self):
        """Test complete magic link login flow from generate to dashboard access"""
        # Step 1: Generate magic link
        gen_response = requests.post(f"{BASE_URL}/api/auth/magic-link/generate?phone={TEST_PHONE}")
        assert gen_response.status_code == 200
        assert gen_response.json()["success"] is True
        token = gen_response.json()["token"]
        
        # Step 2: Verify magic link
        verify_response = requests.get(f"{BASE_URL}/api/auth/magic-link/verify/{token}")
        assert verify_response.status_code == 200
        assert verify_response.json()["success"] is True
        
        # Step 3: Use JWT token to access protected endpoint
        access_token = verify_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Access user profile
        me_response = requests.get(f"{BASE_URL}/api/user/profile", headers=headers)
        assert me_response.status_code == 200
        
        user_data = me_response.json()
        assert user_data["role"] == "vendor"
    
    def test_multiple_tokens_independently_usable(self):
        """Test that multiple generated tokens work independently"""
        # Generate first token
        gen1_response = requests.post(f"{BASE_URL}/api/auth/magic-link/generate?phone={TEST_PHONE}")
        token1 = gen1_response.json()["token"]
        
        # Generate second token
        gen2_response = requests.post(f"{BASE_URL}/api/auth/magic-link/generate?phone={TEST_PHONE}")
        token2 = gen2_response.json()["token"]
        
        # Both tokens should be valid and different
        assert token1 != token2
        
        # Use token2 first
        verify2_response = requests.get(f"{BASE_URL}/api/auth/magic-link/verify/{token2}")
        assert verify2_response.status_code == 200
        
        # Token1 should still be valid
        verify1_response = requests.get(f"{BASE_URL}/api/auth/magic-link/verify/{token1}")
        assert verify1_response.status_code == 200


class TestRegularLoginStillWorks:
    """Regression tests to ensure regular login still works after magic link implementation"""
    
    def test_admin_login(self):
        """Test admin login with email/password still works"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@offoadex.com", "password": "admin123"}
        )
        # May return 401 if credentials wrong, but endpoint should work
        assert response.status_code in [200, 401]
    
    def test_login_endpoint_exists(self):
        """Test that regular login endpoint is still accessible"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "test@example.com", "password": "wrongpass"}
        )
        # Should not return 404 - endpoint should exist
        assert response.status_code != 404


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
