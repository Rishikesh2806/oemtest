"""
Backend tests for Meta Data Deletion Policy feature
Tests:
- Data deletion request endpoint
- Data deletion status check endpoint  
- Meta data deletion callback endpoint
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://rfq-marketplace-test.preview.emergentagent.com').rstrip('/')


class TestDataDeletionRequest:
    """Test data deletion request submission"""
    
    def test_submit_deletion_request_with_phone(self):
        """Test submitting a deletion request with phone number"""
        response = requests.post(f"{BASE_URL}/api/data-deletion/request", json={
            "phone": "+919876543210",
            "email": "",
            "reason": "Testing data deletion"
        })
        
        # Should return 200 with confirmation code
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "confirmation_code" in data, "Response should contain confirmation_code"
        assert data["confirmation_code"].startswith("DEL_"), f"Confirmation code should start with DEL_, got {data['confirmation_code']}"
        assert "message" in data, "Response should contain message"
        
        # Save confirmation code for status check test
        TestDataDeletionRequest.confirmation_code_phone = data["confirmation_code"]
        print(f"✓ Deletion request submitted with phone, code: {data['confirmation_code']}")
    
    def test_submit_deletion_request_with_email(self):
        """Test submitting a deletion request with email"""
        response = requests.post(f"{BASE_URL}/api/data-deletion/request", json={
            "phone": "",
            "email": "test_deletion@example.com",
            "reason": "Testing email deletion"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "confirmation_code" in data
        assert data["confirmation_code"].startswith("DEL_")
        
        TestDataDeletionRequest.confirmation_code_email = data["confirmation_code"]
        print(f"✓ Deletion request submitted with email, code: {data['confirmation_code']}")
    
    def test_submit_deletion_request_with_both(self):
        """Test submitting a deletion request with both phone and email"""
        response = requests.post(f"{BASE_URL}/api/data-deletion/request", json={
            "phone": "+919876543211",
            "email": "test_deletion2@example.com",
            "reason": "Testing both identifiers"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "confirmation_code" in data
        print(f"✓ Deletion request submitted with both, code: {data['confirmation_code']}")
    
    def test_submit_deletion_request_empty_fields(self):
        """Test that request fails without phone or email"""
        response = requests.post(f"{BASE_URL}/api/data-deletion/request", json={
            "phone": "",
            "email": "",
            "reason": "No identifier"
        })
        
        # Should fail with 400 Bad Request
        assert response.status_code == 400, f"Expected 400 for empty fields, got {response.status_code}: {response.text}"
        print("✓ Request correctly rejected without phone or email")


class TestDataDeletionStatus:
    """Test data deletion status check endpoint"""
    
    def test_check_valid_status(self):
        """Test checking status with valid confirmation code"""
        # First create a request to get a valid code
        create_response = requests.post(f"{BASE_URL}/api/data-deletion/request", json={
            "phone": "+919876543299",
            "email": "",
            "reason": "Status check test"
        })
        
        assert create_response.status_code == 200
        code = create_response.json()["confirmation_code"]
        
        # Now check status
        status_response = requests.get(f"{BASE_URL}/api/data-deletion/status/{code}")
        
        assert status_response.status_code == 200, f"Expected 200, got {status_response.status_code}: {status_response.text}"
        
        data = status_response.json()
        assert "status" in data, "Response should contain status"
        assert "confirmation_code" in data, "Response should contain confirmation_code"
        assert "requested_at" in data, "Response should contain requested_at"
        assert "message" in data, "Response should contain message"
        
        # Status should be 'pending' for new requests
        assert data["status"] in ["pending", "in_progress", "completed", "failed"], f"Invalid status: {data['status']}"
        
        print(f"✓ Status check successful: {data['status']} - {data['message']}")
    
    def test_check_invalid_status(self):
        """Test checking status with invalid confirmation code"""
        response = requests.get(f"{BASE_URL}/api/data-deletion/status/DEL_INVALID12345")
        
        # Should return 404 for not found
        assert response.status_code == 404, f"Expected 404 for invalid code, got {response.status_code}: {response.text}"
        print("✓ Invalid code correctly returns 404")


class TestMetaDataDeletionCallback:
    """Test Meta data deletion callback endpoint"""
    
    def test_meta_callback_without_signed_request(self):
        """Test Meta callback without signed_request parameter"""
        response = requests.post(f"{BASE_URL}/api/meta/data-deletion-callback", json={})
        
        # Should still return proper response format (with or without signed_request)
        # Based on the implementation, it generates a deletion request anyway
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "url" in data, "Response should contain url"
        assert "confirmation_code" in data, "Response should contain confirmation_code"
        assert data["confirmation_code"].startswith("DEL_"), "Confirmation code format should be DEL_*"
        
        print(f"✓ Meta callback response: url={data['url']}, code={data['confirmation_code']}")
    
    def test_meta_callback_with_form_data(self):
        """Test Meta callback with form data (as Meta might send)"""
        response = requests.post(
            f"{BASE_URL}/api/meta/data-deletion-callback",
            data={"signed_request": "test_signed_request"}
        )
        
        # Should handle form data as well
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "url" in data
        assert "confirmation_code" in data
        
        print("✓ Meta callback with form data successful")
    
    def test_meta_callback_response_format(self):
        """Test that Meta callback returns proper format per Meta requirements"""
        response = requests.post(f"{BASE_URL}/api/meta/data-deletion-callback", json={
            "signed_request": "encoded.test_data"
        })
        
        assert response.status_code == 200
        
        data = response.json()
        
        # Meta requires these exact fields in response
        assert "url" in data, "Meta requires 'url' field in response"
        assert "confirmation_code" in data, "Meta requires 'confirmation_code' field in response"
        
        # URL should be a valid status check URL
        assert "data-deletion-status" in data["url"], f"URL should point to status page, got: {data['url']}"
        assert data["confirmation_code"] in data["url"], "URL should contain the confirmation code"
        
        print(f"✓ Meta callback response format validated: {data}")


class TestE2EDataDeletionFlow:
    """End-to-end data deletion flow tests"""
    
    def test_complete_deletion_flow(self):
        """Test complete flow: submit request -> check status"""
        # Step 1: Submit deletion request
        submit_response = requests.post(f"{BASE_URL}/api/data-deletion/request", json={
            "phone": "+919876500001",
            "email": "e2e_test@example.com",
            "reason": "E2E flow test"
        })
        
        assert submit_response.status_code == 200, f"Submit failed: {submit_response.text}"
        code = submit_response.json()["confirmation_code"]
        print(f"Step 1: Deletion request submitted, code: {code}")
        
        # Step 2: Check status immediately
        status_response = requests.get(f"{BASE_URL}/api/data-deletion/status/{code}")
        
        assert status_response.status_code == 200, f"Status check failed: {status_response.text}"
        status_data = status_response.json()
        
        assert status_data["status"] == "pending", f"Expected 'pending' status, got: {status_data['status']}"
        assert status_data["confirmation_code"] == code
        
        print(f"Step 2: Status check successful - {status_data['status']}")
        print("✓ E2E flow completed successfully")


class TestResponseDataValidation:
    """Test response data structure and validation"""
    
    def test_deletion_request_response_structure(self):
        """Validate deletion request response structure"""
        response = requests.post(f"{BASE_URL}/api/data-deletion/request", json={
            "phone": "+919876500002",
            "reason": "Structure test"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Check all expected fields
        expected_fields = ["confirmation_code", "message", "status_url"]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
        
        # Validate field types
        assert isinstance(data["confirmation_code"], str)
        assert isinstance(data["message"], str)
        assert isinstance(data["status_url"], str)
        
        print(f"✓ Response structure validated: {list(data.keys())}")
    
    def test_status_response_structure(self):
        """Validate status check response structure"""
        # Create a request first
        create_response = requests.post(f"{BASE_URL}/api/data-deletion/request", json={
            "phone": "+919876500003"
        })
        code = create_response.json()["confirmation_code"]
        
        # Check status
        response = requests.get(f"{BASE_URL}/api/data-deletion/status/{code}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check expected fields
        expected_fields = ["confirmation_code", "status", "message", "requested_at"]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
        
        # Validate status enum
        valid_statuses = ["pending", "in_progress", "completed", "failed"]
        assert data["status"] in valid_statuses, f"Invalid status: {data['status']}"
        
        print(f"✓ Status response structure validated: {data}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
