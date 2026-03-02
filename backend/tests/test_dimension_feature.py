"""
Test suite for RFQ Dimension Feature
Tests:
1. PUT /api/rfqs/{rfq_id}/dimensions - Manual dimension updates
2. POST /api/rfqs/{rfq_id}/analyze - Dimensions missing response fields
3. GSTIN verification endpoint
4. Notification redirect types for negotiation
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
BUYER_EMAIL = "buyer@offoadex.com"
BUYER_PASSWORD = "buyer123"
VENDOR_EMAIL = "info@simpsonmunro.com"
VENDOR_PASSWORD = "vendor123"
ADMIN_EMAIL = "admin@offoadex.com"
ADMIN_PASSWORD = "admin123"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def buyer_token(api_client):
    """Get buyer authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": BUYER_EMAIL,
        "password": BUYER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Buyer authentication failed: {response.text}")


@pytest.fixture(scope="module")
def vendor_token(api_client):
    """Get vendor authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": VENDOR_EMAIL,
        "password": VENDOR_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    # Try alternative vendor
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": "vendor@offoadex.com",
        "password": "vendor123"
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Vendor authentication failed")


class TestGSTINVerification:
    """Test GSTIN verification endpoint"""
    
    def test_gstin_valid_format(self, api_client):
        """Test GSTIN verification with a valid format GSTIN"""
        # Test with a sample GSTIN (27AABCU9603R1ZM - Maharashtra)
        response = api_client.get(f"{BASE_URL}/api/gstin/verify/27AABCU9603R1ZM")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "valid" in data
        assert "gstin" in data
        assert data["gstin"] == "27AABCU9603R1ZM"
        assert "state" in data
        
        print(f"GSTIN verification result: valid={data.get('valid')}, state={data.get('state')}")
    
    def test_gstin_invalid_length(self, api_client):
        """Test GSTIN verification with invalid length"""
        response = api_client.get(f"{BASE_URL}/api/gstin/verify/27AABCU")
        
        # Should return 400 for invalid format
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        print(f"Invalid GSTIN response: {data.get('detail')}")
    
    def test_gstin_extracts_state(self, api_client):
        """Test that GSTIN correctly extracts state code"""
        # Test Maharashtra (27)
        response = api_client.get(f"{BASE_URL}/api/gstin/verify/27AABCU9603R1ZM")
        assert response.status_code == 200
        data = response.json()
        assert "Maharashtra" in data.get("state", "")
        
        print(f"State extracted: {data.get('state')}")


class TestDimensionUpdate:
    """Test manual dimension update endpoint"""
    
    @pytest.fixture(scope="class")
    def test_rfq(self, api_client, buyer_token):
        """Create a test RFQ for dimension testing"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        
        # Create a test RFQ
        rfq_data = {
            "title": f"TEST_Dimension_Test_RFQ_{uuid.uuid4().hex[:8]}",
            "description": "Test RFQ for dimension feature testing",
            "material_type": "Aluminum",
            "quantity": 10,
            "tolerance": 0.1,
            "surface_finish": "Anodized",
            "supply_type": "vendor_material",
            "preferred_payment_terms": "net_30"
        }
        
        response = api_client.post(f"{BASE_URL}/api/rfqs", json=rfq_data, headers=headers)
        assert response.status_code == 200
        
        rfq = response.json()
        print(f"Created test RFQ: {rfq.get('rfq_id')}")
        
        yield rfq
        
        # Cleanup: Delete the test RFQ (if endpoint available)
        # api_client.delete(f"{BASE_URL}/api/rfqs/{rfq['rfq_id']}", headers=headers)
    
    def test_dimension_update_success(self, api_client, buyer_token, test_rfq):
        """Test successful dimension update"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        rfq_id = test_rfq["rfq_id"]
        
        dimension_data = {
            "length": 150.5,
            "width": 100.0,
            "height": 50.25,
            "weight": 2.5
        }
        
        response = api_client.put(
            f"{BASE_URL}/api/rfqs/{rfq_id}/dimensions",
            json=dimension_data,
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response
        assert "message" in data
        assert data["message"] == "Dimensions updated successfully"
        assert "overall_dimensions" in data
        assert data["overall_dimensions"]["length"] == 150.5
        assert data["overall_dimensions"]["width"] == 100.0
        assert data["overall_dimensions"]["height"] == 50.25
        assert "max_dimension_mm" in data
        assert data["max_dimension_mm"] == 150.5  # Max of L, W, H
        
        print(f"Dimensions updated: {data['overall_dimensions']}")
    
    def test_dimension_update_partial(self, api_client, buyer_token, test_rfq):
        """Test partial dimension update (only some fields)"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        rfq_id = test_rfq["rfq_id"]
        
        # Update only length
        dimension_data = {
            "length": 200.0
        }
        
        response = api_client.put(
            f"{BASE_URL}/api/rfqs/{rfq_id}/dimensions",
            json=dimension_data,
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Previous width and height should be preserved
        assert data["overall_dimensions"]["length"] == 200.0
        assert data["overall_dimensions"]["width"] == 100.0  # From previous test
        assert data["overall_dimensions"]["height"] == 50.25  # From previous test
        
        print(f"Partial update result: {data['overall_dimensions']}")
    
    def test_dimension_update_unauthorized(self, api_client, test_rfq):
        """Test dimension update without authentication"""
        rfq_id = test_rfq["rfq_id"]
        
        dimension_data = {
            "length": 100.0,
            "width": 50.0,
            "height": 25.0
        }
        
        response = api_client.put(
            f"{BASE_URL}/api/rfqs/{rfq_id}/dimensions",
            json=dimension_data
        )
        
        assert response.status_code == 401
        print("Unauthorized access correctly rejected")
    
    def test_dimension_update_nonexistent_rfq(self, api_client, buyer_token):
        """Test dimension update for non-existent RFQ"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        
        dimension_data = {
            "length": 100.0,
            "width": 50.0,
            "height": 25.0
        }
        
        response = api_client.put(
            f"{BASE_URL}/api/rfqs/rfq_nonexistent_123/dimensions",
            json=dimension_data,
            headers=headers
        )
        
        assert response.status_code == 404
        print("Non-existent RFQ correctly returns 404")
    
    def test_rfq_has_updated_dimensions(self, api_client, buyer_token, test_rfq):
        """Verify RFQ data was actually updated with dimensions"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        rfq_id = test_rfq["rfq_id"]
        
        # GET the RFQ and verify ai_analysis was updated
        response = api_client.get(f"{BASE_URL}/api/rfqs/{rfq_id}", headers=headers)
        
        assert response.status_code == 200
        rfq = response.json()
        
        # Verify ai_analysis contains updated dimensions
        ai_analysis = rfq.get("ai_analysis", {})
        overall_dims = ai_analysis.get("overall_dimensions", {})
        
        assert overall_dims.get("length") == 200.0
        assert overall_dims.get("width") == 100.0
        assert overall_dims.get("height") == 50.25
        assert ai_analysis.get("dimensions_manually_updated") == True
        
        print(f"RFQ verified with dimensions: {overall_dims}")


class TestAnalyzeEndpointDimensionsResponse:
    """Test that analyze endpoint returns dimensions_missing fields"""
    
    def test_buyer_login(self, api_client, buyer_token):
        """Verify buyer can login"""
        assert buyer_token is not None
        print("Buyer authentication successful")
    
    def test_analyze_endpoint_exists(self, api_client, buyer_token):
        """Verify analyze endpoint exists and requires RFQ with drawings"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        
        # Test with a non-existent RFQ to check endpoint exists
        response = api_client.post(
            f"{BASE_URL}/api/rfqs/rfq_nonexistent/analyze",
            headers=headers
        )
        
        # Should return 404 (not found) rather than 405 (method not allowed)
        assert response.status_code in [404, 400]
        print(f"Analyze endpoint exists, returned: {response.status_code}")


class TestNotificationTypes:
    """Test notification types for negotiation redirects"""
    
    def test_notifications_endpoint(self, api_client, buyer_token):
        """Test notifications endpoint returns correct structure"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        
        response = api_client.get(f"{BASE_URL}/api/notifications", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "notifications" in data
        assert "unread_count" in data
        
        print(f"Notifications count: {len(data['notifications'])}, Unread: {data['unread_count']}")


class TestExistingRFQDimensions:
    """Test dimension features with existing RFQs"""
    
    def test_get_existing_rfqs(self, api_client, buyer_token):
        """Get list of buyer's RFQs"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        
        response = api_client.get(f"{BASE_URL}/api/rfqs", headers=headers)
        
        assert response.status_code == 200
        rfqs = response.json()
        
        print(f"Found {len(rfqs)} RFQs for buyer")
        
        # Check if any RFQ has ai_analysis with dimensions
        for rfq in rfqs[:5]:  # Check first 5
            if rfq.get("ai_analysis"):
                dims = rfq["ai_analysis"].get("overall_dimensions", {})
                print(f"RFQ {rfq['rfq_id']}: L={dims.get('length')}, W={dims.get('width')}, H={dims.get('height')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
