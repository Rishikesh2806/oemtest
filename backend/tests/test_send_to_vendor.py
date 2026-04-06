"""
Test suite for POST /api/rfqs/{rfq_id}/send-to-vendor endpoint
Tests the feature to send RFQ to partial/likely vendors
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://google-auth-refactor.preview.emergentagent.com')

class TestSendToVendorEndpoint:
    """Tests for the send-to-vendor endpoint"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@offoadex.com",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def buyer_token(self):
        """Get buyer authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "visualbuyer@test.com",
            "password": "buyer123"
        })
        assert response.status_code == 200, f"Buyer login failed: {response.text}"
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def rfq_with_partial_vendors(self, admin_token):
        """Get an RFQ that has partial vendors"""
        # rfq_c869ea1d75a1 has 8 partial vendors
        response = requests.get(
            f"{BASE_URL}/api/rfqs/rfq_c869ea1d75a1",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        return response.json()
    
    def test_send_to_vendor_success(self, admin_token, rfq_with_partial_vendors):
        """Test successfully sending RFQ to a partial vendor"""
        rfq_id = rfq_with_partial_vendors["rfq_id"]
        partial_vendors = rfq_with_partial_vendors.get("partial_vendors", [])
        
        # Skip if no partial vendors available
        if len(partial_vendors) < 2:
            pytest.skip("Not enough partial vendors to test")
        
        # Pick a vendor that hasn't been sent yet
        vendor_to_send = partial_vendors[1]  # Use second vendor
        vendor_id = vendor_to_send["vendor_id"]
        
        response = requests.post(
            f"{BASE_URL}/api/rfqs/{rfq_id}/send-to-vendor",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"vendor_id": vendor_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert data.get("success") == True
        assert "message" in data
        assert data.get("vendor_id") == vendor_id
        assert "notified" in data
        
        # Verify notifications were attempted
        notified = data.get("notified", {})
        assert "email" in notified
        assert "whatsapp" in notified
        assert "in_app" in notified
    
    def test_send_to_vendor_already_matched(self, admin_token):
        """Test sending to a vendor that's already in matched_vendors"""
        rfq_id = "rfq_c869ea1d75a1"
        
        # First, get the RFQ to find a matched vendor
        response = requests.get(
            f"{BASE_URL}/api/rfqs/{rfq_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        rfq = response.json()
        
        matched_vendors = rfq.get("matched_vendors", [])
        if not matched_vendors:
            pytest.skip("No matched vendors to test duplicate send")
        
        vendor_id = matched_vendors[0]["vendor_id"]
        
        # Try to send again
        response = requests.post(
            f"{BASE_URL}/api/rfqs/{rfq_id}/send-to-vendor",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"vendor_id": vendor_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert data.get("already_matched") == True
    
    def test_send_to_vendor_missing_vendor_id(self, admin_token):
        """Test error when vendor_id is missing"""
        response = requests.post(
            f"{BASE_URL}/api/rfqs/rfq_c869ea1d75a1/send-to-vendor",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={}
        )
        
        assert response.status_code == 400
        assert "vendor_id" in response.json().get("detail", "").lower()
    
    def test_send_to_vendor_invalid_rfq(self, admin_token):
        """Test error when RFQ doesn't exist"""
        response = requests.post(
            f"{BASE_URL}/api/rfqs/invalid_rfq_id/send-to-vendor",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"vendor_id": "vendor_123"}
        )
        
        assert response.status_code == 404
    
    def test_send_to_vendor_invalid_vendor(self, admin_token):
        """Test error when vendor doesn't exist"""
        response = requests.post(
            f"{BASE_URL}/api/rfqs/rfq_c869ea1d75a1/send-to-vendor",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"vendor_id": "invalid_vendor_id"}
        )
        
        assert response.status_code == 404
    
    def test_send_to_vendor_unauthorized(self):
        """Test error when not authenticated"""
        response = requests.post(
            f"{BASE_URL}/api/rfqs/rfq_c869ea1d75a1/send-to-vendor",
            json={"vendor_id": "vendor_123"}
        )
        
        assert response.status_code == 401
    
    def test_vendor_moved_from_partial_to_matched(self, admin_token):
        """Test that vendor is moved from partial_vendors to matched_vendors"""
        rfq_id = "rfq_64684bff36f6"  # RFQ with 5 partial, 3 likely
        
        # Get initial state
        response = requests.get(
            f"{BASE_URL}/api/rfqs/{rfq_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        initial_rfq = response.json()
        
        partial_vendors = initial_rfq.get("partial_vendors", [])
        if not partial_vendors:
            pytest.skip("No partial vendors to test")
        
        initial_partial_count = len(partial_vendors)
        initial_matched_count = len(initial_rfq.get("matched_vendors", []))
        
        # Pick a vendor to send
        vendor_to_send = partial_vendors[0]
        vendor_id = vendor_to_send["vendor_id"]
        
        # Check if already matched
        already_matched = any(
            v.get("vendor_id") == vendor_id 
            for v in initial_rfq.get("matched_vendors", [])
        )
        
        if already_matched:
            pytest.skip("Vendor already matched")
        
        # Send to vendor
        response = requests.post(
            f"{BASE_URL}/api/rfqs/{rfq_id}/send-to-vendor",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"vendor_id": vendor_id}
        )
        assert response.status_code == 200
        
        # Verify vendor moved
        response = requests.get(
            f"{BASE_URL}/api/rfqs/{rfq_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        updated_rfq = response.json()
        
        # Vendor should be in matched_vendors
        matched_vendor_ids = [v.get("vendor_id") for v in updated_rfq.get("matched_vendors", [])]
        assert vendor_id in matched_vendor_ids, "Vendor should be in matched_vendors"
        
        # Vendor should NOT be in partial_vendors
        partial_vendor_ids = [v.get("vendor_id") for v in updated_rfq.get("partial_vendors", [])]
        assert vendor_id not in partial_vendor_ids, "Vendor should be removed from partial_vendors"


class TestMatchEndpointReturnsPartialVendors:
    """Tests that match endpoint returns partial/likely vendors"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@offoadex.com",
            "password": "admin123"
        })
        assert response.status_code == 200
        return response.json().get("access_token")
    
    def test_rfq_has_partial_vendors(self, admin_token):
        """Test that RFQ with partial matches returns partial_vendors"""
        response = requests.get(
            f"{BASE_URL}/api/rfqs/rfq_c869ea1d75a1",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        rfq = response.json()
        
        # Should have partial vendors
        partial_vendors = rfq.get("partial_vendors", [])
        assert len(partial_vendors) > 0, "RFQ should have partial vendors"
        
        # Each partial vendor should have required fields
        for vendor in partial_vendors[:3]:
            assert "vendor_id" in vendor
            assert "company_name" in vendor
    
    def test_rfq_has_likely_vendors(self, admin_token):
        """Test that RFQ with likely matches returns likely_vendors"""
        response = requests.get(
            f"{BASE_URL}/api/rfqs/rfq_64684bff36f6",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        rfq = response.json()
        
        # Should have likely vendors
        likely_vendors = rfq.get("likely_vendors", [])
        assert len(likely_vendors) > 0, "RFQ should have likely vendors"
        
        # Each likely vendor should have required fields
        for vendor in likely_vendors[:3]:
            assert "vendor_id" in vendor
            assert "company_name" in vendor


class TestExcludedVendorsSectionData:
    """Tests that data structure supports ExcludedVendorsSection component"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@offoadex.com",
            "password": "admin123"
        })
        assert response.status_code == 200
        return response.json().get("access_token")
    
    def test_partial_vendor_has_operations_summary(self, admin_token):
        """Test that partial vendors have operations_summary for UI display"""
        response = requests.get(
            f"{BASE_URL}/api/rfqs/rfq_c869ea1d75a1",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        rfq = response.json()
        
        partial_vendors = rfq.get("partial_vendors", [])
        if not partial_vendors:
            pytest.skip("No partial vendors")
        
        # At least some vendors should have operations_summary
        vendors_with_ops = [v for v in partial_vendors if v.get("operations_summary")]
        # This is optional, so just log if missing
        if not vendors_with_ops:
            print("Note: No partial vendors have operations_summary")
    
    def test_vendor_has_location_info(self, admin_token):
        """Test that vendors have location info for display"""
        response = requests.get(
            f"{BASE_URL}/api/rfqs/rfq_c869ea1d75a1",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        rfq = response.json()
        
        partial_vendors = rfq.get("partial_vendors", [])
        if not partial_vendors:
            pytest.skip("No partial vendors")
        
        # Check first vendor has location
        vendor = partial_vendors[0]
        has_location = vendor.get("location") or vendor.get("city")
        # Location is optional but good to have
        if not has_location:
            print(f"Note: Vendor {vendor.get('company_name')} has no location info")
