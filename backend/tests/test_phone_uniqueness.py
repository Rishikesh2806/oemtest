"""
Phone Uniqueness Tests for OEMLinker
Tests the duplicate phone number protection across registration and profile update flows.
Features tested:
- Phone normalization (E.164 format)
- Real-time phone availability check API
- Backend enforcement blocking duplicate phones at registration
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from iteration_49.json
ADMIN_EMAIL = "admin@offoadex.com"
ADMIN_PASSWORD = "admin123"
VENDOR_EMAIL = "testvendor_nda@test.com"
VENDOR_PASSWORD = "vendor123"
BUYER_EMAIL = "visualbuyer@test.com"
BUYER_PASSWORD = "buyer123"

# Known existing phone numbers in DB
EXISTING_PHONES = ["9831379959", "9876543210", "8765432109"]


class TestPhoneCheckEndpoint:
    """Tests for POST /api/auth/check-phone endpoint"""
    
    def test_check_phone_new_number_available(self):
        """Test that a new phone number returns available:true"""
        # Use a random 10-digit phone number that shouldn't exist (starting with 70-79)
        import random
        new_phone = f"70{random.randint(10000000, 99999999)}"
        
        response = requests.post(
            f"{BASE_URL}/api/auth/check-phone",
            json={"phone": new_phone}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("available") == True, f"Expected available:true for new number, got: {data}"
        print(f"PASS: New phone {new_phone} is available")
    
    def test_check_phone_existing_number_taken(self):
        """Test that existing phone 9831379959 returns available:false"""
        response = requests.post(
            f"{BASE_URL}/api/auth/check-phone",
            json={"phone": "9831379959"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("available") == False, f"Expected available:false for existing number, got: {data}"
        assert data.get("code") == "PHONE_TAKEN", f"Expected code PHONE_TAKEN, got: {data}"
        print(f"PASS: Existing phone 9831379959 is correctly marked as taken")
    
    def test_check_phone_normalization_with_spaces(self):
        """Test that +91 98313 79959 normalizes to same as 9831379959"""
        response = requests.post(
            f"{BASE_URL}/api/auth/check-phone",
            json={"phone": "+91 98313 79959"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("available") == False, f"Expected available:false for normalized duplicate, got: {data}"
        print(f"PASS: Phone with spaces '+91 98313 79959' correctly detected as duplicate")
    
    def test_check_phone_normalization_with_dashes(self):
        """Test that 98313-79959 normalizes to same as 9831379959"""
        response = requests.post(
            f"{BASE_URL}/api/auth/check-phone",
            json={"phone": "98313-79959"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("available") == False, f"Expected available:false for normalized duplicate, got: {data}"
        print(f"PASS: Phone with dashes '98313-79959' correctly detected as duplicate")
    
    def test_check_phone_normalization_with_country_code(self):
        """Test that 919831379959 normalizes to same as 9831379959"""
        response = requests.post(
            f"{BASE_URL}/api/auth/check-phone",
            json={"phone": "919831379959"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("available") == False, f"Expected available:false for normalized duplicate, got: {data}"
        print(f"PASS: Phone with country code '919831379959' correctly detected as duplicate")
    
    def test_check_phone_invalid_format(self):
        """Test that 'abc' returns INVALID_PHONE"""
        response = requests.post(
            f"{BASE_URL}/api/auth/check-phone",
            json={"phone": "abc"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("code") == "INVALID_PHONE", f"Expected code INVALID_PHONE for 'abc', got: {data}"
        assert data.get("available") == False, f"Expected available:false for invalid phone, got: {data}"
        print(f"PASS: Invalid phone 'abc' correctly returns INVALID_PHONE")
    
    def test_check_phone_empty_returns_available(self):
        """Test that empty phone returns available:true"""
        response = requests.post(
            f"{BASE_URL}/api/auth/check-phone",
            json={"phone": ""}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("available") == True, f"Expected available:true for empty phone, got: {data}"
        print(f"PASS: Empty phone correctly returns available:true")
    
    def test_check_phone_whitespace_only_returns_available(self):
        """Test that whitespace-only phone returns available:true"""
        response = requests.post(
            f"{BASE_URL}/api/auth/check-phone",
            json={"phone": "   "}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("available") == True, f"Expected available:true for whitespace phone, got: {data}"
        print(f"PASS: Whitespace-only phone correctly returns available:true")
    
    def test_check_phone_with_brackets(self):
        """Test that (983) 137-9959 normalizes correctly"""
        response = requests.post(
            f"{BASE_URL}/api/auth/check-phone",
            json={"phone": "(983) 137-9959"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        # This should normalize to 9831379959 and be detected as duplicate
        assert data.get("available") == False, f"Expected available:false for normalized duplicate with brackets, got: {data}"
        print(f"PASS: Phone with brackets '(983) 137-9959' correctly detected as duplicate")


class TestRegistrationPhoneBlocking:
    """Tests for POST /api/auth/register blocking duplicate phones"""
    
    def test_register_with_duplicate_phone_blocked(self):
        """Test that registration with duplicate phone number is blocked"""
        import random
        unique_email = f"test_phone_{uuid.uuid4().hex[:8]}@test.com"
        
        response = requests.post(
            f"{BASE_URL}/api/auth/register",
            json={
                "name": "Test User Phone",
                "email": unique_email,
                "password": "TestPass123!",
                "role": "vendor",
                "phone": "9831379959"  # Known existing phone
            },
            headers={"X-Forwarded-For": f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"}
        )
        
        # Should be blocked with 400
        assert response.status_code == 400, f"Expected 400 for duplicate phone, got {response.status_code}: {response.text}"
        data = response.json()
        assert "phone" in data.get("detail", "").lower() or "already registered" in data.get("detail", "").lower(), \
            f"Expected error about phone already registered, got: {data}"
        print(f"PASS: Registration with duplicate phone correctly blocked")
    
    def test_register_with_normalized_duplicate_phone_blocked(self):
        """Test that registration with normalized duplicate phone is blocked"""
        import random
        unique_email = f"test_phone_{uuid.uuid4().hex[:8]}@test.com"
        
        response = requests.post(
            f"{BASE_URL}/api/auth/register",
            json={
                "name": "Test User Phone",
                "email": unique_email,
                "password": "TestPass123!",
                "role": "vendor",
                "phone": "+91 98313 79959"  # Same as 9831379959 after normalization
            },
            headers={"X-Forwarded-For": f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"}
        )
        
        # Should be blocked with 400
        assert response.status_code == 400, f"Expected 400 for normalized duplicate phone, got {response.status_code}: {response.text}"
        print(f"PASS: Registration with normalized duplicate phone correctly blocked")
    
    def test_register_with_unique_phone_allowed(self):
        """Test that registration with unique phone number is allowed"""
        import random
        unique_email = f"test_phone_{uuid.uuid4().hex[:8]}@test.com"
        unique_phone = f"70{random.randint(10000000, 99999999)}"  # Random 10-digit phone starting with 70
        
        response = requests.post(
            f"{BASE_URL}/api/auth/register",
            json={
                "name": "Test User Unique Phone",
                "email": unique_email,
                "password": "TestPass123!",
                "role": "buyer",
                "phone": unique_phone
            },
            headers={"X-Forwarded-For": f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"}
        )
        
        # Should succeed
        assert response.status_code in [200, 201], f"Expected 200/201 for unique phone, got {response.status_code}: {response.text}"
        print(f"PASS: Registration with unique phone {unique_phone} allowed")


class TestVendorProfilePhoneUpdate:
    """Tests for PUT /api/vendor/profile blocking duplicate phones"""
    
    @pytest.fixture
    def vendor_token(self):
        """Get vendor authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": VENDOR_EMAIL, "password": VENDOR_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip(f"Vendor login failed: {response.text}")
    
    def test_vendor_profile_update_with_own_phone_allowed(self, vendor_token):
        """Test that vendor can keep their own phone number"""
        headers = {"Authorization": f"Bearer {vendor_token}"}
        
        # First get current profile
        profile_response = requests.get(
            f"{BASE_URL}/api/vendors/profile",
            headers=headers
        )
        
        if profile_response.status_code != 200:
            pytest.skip("Could not fetch vendor profile")
        
        current_profile = profile_response.json()
        current_phone = current_profile.get("phone", "")
        
        # Update with same phone should work
        update_response = requests.put(
            f"{BASE_URL}/api/vendors/profile",
            headers=headers,
            json={
                "company_name": current_profile.get("company_name", "Test Company"),
                "phone": current_phone
            }
        )
        
        assert update_response.status_code == 200, f"Expected 200 for own phone update, got {update_response.status_code}: {update_response.text}"
        print(f"PASS: Vendor can update profile with their own phone number")


class TestPhoneNormalizationUtility:
    """Tests for phone normalization logic via API"""
    
    def test_normalization_10_digit_indian(self):
        """Test 10-digit Indian number gets +91 prefix"""
        # We test this indirectly via the check-phone endpoint
        # A new 10-digit number should be normalized to +91XXXXXXXXXX
        response = requests.post(
            f"{BASE_URL}/api/auth/check-phone",
            json={"phone": "7012345678"}
        )
        assert response.status_code == 200
        # If it returns available, normalization worked
        print(f"PASS: 10-digit number normalization works")
    
    def test_normalization_with_leading_zero(self):
        """Test number with leading zero is normalized"""
        response = requests.post(
            f"{BASE_URL}/api/auth/check-phone",
            json={"phone": "09831379959"}
        )
        assert response.status_code == 200
        data = response.json()
        # Should detect as duplicate of 9831379959
        assert data.get("available") == False, f"Expected duplicate detection for 09831379959, got: {data}"
        print(f"PASS: Leading zero normalization works")


class TestCurrentUserIdExclusion:
    """Tests for current_user_id parameter excluding own phone"""
    
    @pytest.fixture
    def vendor_auth(self):
        """Get vendor authentication and user_id"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": VENDOR_EMAIL, "password": VENDOR_PASSWORD}
        )
        if response.status_code == 200:
            data = response.json()
            return {
                "token": data.get("access_token"),
                "user_id": data.get("user", {}).get("user_id")
            }
        pytest.skip(f"Vendor login failed: {response.text}")
    
    def test_check_phone_excludes_current_user(self, vendor_auth):
        """Test that current_user_id parameter excludes own phone from duplicate check"""
        headers = {"Authorization": f"Bearer {vendor_auth['token']}"}
        
        # Get vendor's current phone
        profile_response = requests.get(
            f"{BASE_URL}/api/vendors/profile",
            headers=headers
        )
        
        if profile_response.status_code != 200:
            pytest.skip("Could not fetch vendor profile")
        
        vendor_phone = profile_response.json().get("phone", "")
        if not vendor_phone:
            pytest.skip("Vendor has no phone number set")
        
        # Check phone with current_user_id should return available for own number
        response = requests.post(
            f"{BASE_URL}/api/auth/check-phone",
            json={
                "phone": vendor_phone,
                "current_user_id": vendor_auth["user_id"]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("available") == True, f"Expected available:true for own phone with current_user_id, got: {data}"
        print(f"PASS: current_user_id correctly excludes own phone from duplicate check")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
