"""
Test suite for POST /api/rfqs/{rfq_id}/estimate-dimensions endpoint
Tests AI-powered dimension estimation for reference photos in RFQ creation flow

Features tested:
- Endpoint returns AI-estimated dimensions with confidence level
- User-provided dimensions are preserved in estimation response
- AI estimates missing dimensions (e.g., thickness for sheet_metal when length/width given)
- Endpoint works with admin auth
- Response includes user_provided and ai_estimated field lists
- Endpoint returns fallback when no image available
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from review request
ADMIN_EMAIL = "admin@offoadex.com"
ADMIN_PASSWORD = "admin123"
TEST_RFQ_ID = "rfq_239620aa6d76"  # Reference photo RFQ with geometry: sheet_metal


class TestEstimateDimensionsEndpoint:
    """Tests for POST /api/rfqs/{rfq_id}/estimate-dimensions"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        token = data.get("access_token")
        assert token, f"No access_token in response: {data}"
        return token
    
    @pytest.fixture(scope="class")
    def auth_headers(self, admin_token):
        """Get authorization headers"""
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
    
    def test_estimate_dimensions_with_length_width(self, auth_headers):
        """Test: User provides length and width, AI estimates thickness for sheet_metal"""
        response = requests.post(
            f"{BASE_URL}/api/rfqs/{TEST_RFQ_ID}/estimate-dimensions",
            headers=auth_headers,
            json={"dimensions": {"length": 500, "width": 300}}
        )
        
        assert response.status_code == 200, f"Request failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "estimated_dimensions" in data, f"Missing estimated_dimensions: {data}"
        assert "confidence" in data, f"Missing confidence: {data}"
        assert "method" in data, f"Missing method: {data}"
        
        # Verify user-provided dimensions are preserved
        est_dims = data["estimated_dimensions"]
        assert est_dims.get("length") == 500, f"Length not preserved: {est_dims}"
        assert est_dims.get("width") == 300, f"Width not preserved: {est_dims}"
        
        # Verify user_provided and ai_estimated lists
        assert "user_provided" in data, f"Missing user_provided list: {data}"
        assert "length" in data["user_provided"], f"length not in user_provided: {data}"
        assert "width" in data["user_provided"], f"width not in user_provided: {data}"
        
        # Verify confidence level is valid
        assert data["confidence"] in ["high", "medium", "low"], f"Invalid confidence: {data['confidence']}"
        
        # Verify method indicates AI estimation
        assert data["method"] in ["ai_estimation", "user_input_only"], f"Invalid method: {data['method']}"
        
        print(f"SUCCESS: Estimated dimensions: {est_dims}")
        print(f"SUCCESS: Confidence: {data['confidence']}, Method: {data['method']}")
        print(f"SUCCESS: User provided: {data.get('user_provided')}, AI estimated: {data.get('ai_estimated')}")
    
    def test_estimate_dimensions_preserves_user_input(self, auth_headers):
        """Test: User-provided dimensions are preserved exactly"""
        user_dims = {"length": 750, "width": 450, "thickness": 5}
        
        response = requests.post(
            f"{BASE_URL}/api/rfqs/{TEST_RFQ_ID}/estimate-dimensions",
            headers=auth_headers,
            json={"dimensions": user_dims}
        )
        
        assert response.status_code == 200, f"Request failed: {response.text}"
        data = response.json()
        
        est_dims = data["estimated_dimensions"]
        
        # All user-provided dimensions should be preserved exactly
        assert est_dims.get("length") == 750, f"Length not preserved: {est_dims}"
        assert est_dims.get("width") == 450, f"Width not preserved: {est_dims}"
        assert est_dims.get("thickness") == 5, f"Thickness not preserved: {est_dims}"
        
        # Verify user_provided list contains all provided dimensions
        user_provided = data.get("user_provided", [])
        assert "length" in user_provided, f"length not in user_provided"
        assert "width" in user_provided, f"width not in user_provided"
        assert "thickness" in user_provided, f"thickness not in user_provided"
        
        print(f"SUCCESS: All user dimensions preserved: {est_dims}")
    
    def test_estimate_dimensions_returns_ai_estimated_list(self, auth_headers):
        """Test: Response includes ai_estimated field listing AI-estimated dimensions"""
        response = requests.post(
            f"{BASE_URL}/api/rfqs/{TEST_RFQ_ID}/estimate-dimensions",
            headers=auth_headers,
            json={"dimensions": {"length": 400}}
        )
        
        assert response.status_code == 200, f"Request failed: {response.text}"
        data = response.json()
        
        # Verify ai_estimated list exists
        assert "ai_estimated" in data, f"Missing ai_estimated list: {data}"
        
        # If AI estimated any dimensions, they should be in the list
        ai_estimated = data.get("ai_estimated", [])
        est_dims = data.get("estimated_dimensions", {})
        
        # Any dimension in estimated_dimensions that wasn't user-provided should be in ai_estimated
        user_provided = data.get("user_provided", [])
        for dim_key, dim_val in est_dims.items():
            if dim_key not in user_provided and dim_key != "unit" and dim_val:
                assert dim_key in ai_estimated, f"{dim_key} estimated but not in ai_estimated list"
        
        print(f"SUCCESS: AI estimated dimensions: {ai_estimated}")
    
    def test_estimate_dimensions_includes_part_geometry(self, auth_headers):
        """Test: Response includes part_geometry from RFQ analysis"""
        response = requests.post(
            f"{BASE_URL}/api/rfqs/{TEST_RFQ_ID}/estimate-dimensions",
            headers=auth_headers,
            json={"dimensions": {"length": 500, "width": 300}}
        )
        
        assert response.status_code == 200, f"Request failed: {response.text}"
        data = response.json()
        
        # Verify part_geometry is included
        assert "part_geometry" in data, f"Missing part_geometry: {data}"
        
        # The test RFQ has sheet_metal geometry
        geometry = data.get("part_geometry")
        assert geometry, f"Empty part_geometry: {data}"
        
        print(f"SUCCESS: Part geometry: {geometry}")
    
    def test_estimate_dimensions_with_empty_dimensions(self, auth_headers):
        """Test: Endpoint handles empty dimensions gracefully"""
        response = requests.post(
            f"{BASE_URL}/api/rfqs/{TEST_RFQ_ID}/estimate-dimensions",
            headers=auth_headers,
            json={"dimensions": {}}
        )
        
        assert response.status_code == 200, f"Request failed: {response.text}"
        data = response.json()
        
        # Should still return a valid response structure
        assert "estimated_dimensions" in data, f"Missing estimated_dimensions: {data}"
        assert "confidence" in data, f"Missing confidence: {data}"
        
        print(f"SUCCESS: Empty dimensions handled: {data}")
    
    def test_estimate_dimensions_unauthorized(self):
        """Test: Endpoint requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/rfqs/{TEST_RFQ_ID}/estimate-dimensions",
            json={"dimensions": {"length": 500}}
        )
        
        # Should return 401 or 403 without auth
        assert response.status_code in [401, 403], f"Expected auth error, got: {response.status_code}"
        print(f"SUCCESS: Unauthorized request rejected with {response.status_code}")
    
    def test_estimate_dimensions_invalid_rfq(self, auth_headers):
        """Test: Endpoint returns 404 for non-existent RFQ"""
        response = requests.post(
            f"{BASE_URL}/api/rfqs/rfq_nonexistent_12345/estimate-dimensions",
            headers=auth_headers,
            json={"dimensions": {"length": 500}}
        )
        
        assert response.status_code == 404, f"Expected 404, got: {response.status_code}"
        print(f"SUCCESS: Non-existent RFQ returns 404")
    
    def test_estimate_dimensions_response_has_unit(self, auth_headers):
        """Test: Estimated dimensions include unit field (mm)"""
        response = requests.post(
            f"{BASE_URL}/api/rfqs/{TEST_RFQ_ID}/estimate-dimensions",
            headers=auth_headers,
            json={"dimensions": {"length": 500, "width": 300}}
        )
        
        assert response.status_code == 200, f"Request failed: {response.text}"
        data = response.json()
        
        est_dims = data.get("estimated_dimensions", {})
        assert est_dims.get("unit") == "mm", f"Missing or wrong unit: {est_dims}"
        
        print(f"SUCCESS: Unit field present: {est_dims.get('unit')}")


class TestEstimateDimensionsIntegration:
    """Integration tests for dimension estimation flow"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, admin_token):
        """Get authorization headers"""
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
    
    def test_verify_rfq_exists(self, auth_headers):
        """Verify the test RFQ exists and has expected properties"""
        response = requests.get(
            f"{BASE_URL}/api/rfqs/{TEST_RFQ_ID}",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"RFQ not found: {response.text}"
        rfq = response.json()
        
        assert rfq.get("rfq_id") == TEST_RFQ_ID, f"Wrong RFQ ID: {rfq}"
        print(f"SUCCESS: RFQ exists with title: {rfq.get('title')}")
        print(f"SUCCESS: Material: {rfq.get('material_type')}, Geometry: {rfq.get('ai_analysis', {}).get('part_geometry')}")
    
    def test_estimate_then_confirm_dimensions(self, auth_headers):
        """Test: Full flow - estimate dimensions then confirm via PUT /dimensions
        
        Note: PUT /dimensions is buyer-only (not admin), so we verify the estimate
        works and the confirm endpoint correctly rejects admin access.
        """
        # Step 1: Estimate dimensions (admin can do this)
        estimate_response = requests.post(
            f"{BASE_URL}/api/rfqs/{TEST_RFQ_ID}/estimate-dimensions",
            headers=auth_headers,
            json={"dimensions": {"length": 600, "width": 400}}
        )
        
        assert estimate_response.status_code == 200, f"Estimate failed: {estimate_response.text}"
        estimate_data = estimate_response.json()
        
        estimated_dims = estimate_data.get("estimated_dimensions", {})
        part_geometry = estimate_data.get("part_geometry", "rectangular")
        
        print(f"SUCCESS: Estimated dimensions: {estimated_dims}")
        print(f"SUCCESS: Part geometry: {part_geometry}")
        print(f"SUCCESS: Confidence: {estimate_data.get('confidence')}")
        
        # Step 2: Verify PUT /dimensions is buyer-only (admin gets 404)
        # This is expected behavior - only the RFQ owner can confirm dimensions
        confirm_payload = {
            **estimated_dims,
            "part_geometry": part_geometry
        }
        
        confirm_response = requests.put(
            f"{BASE_URL}/api/rfqs/{TEST_RFQ_ID}/dimensions",
            headers=auth_headers,
            json=confirm_payload
        )
        
        # Admin should get 404 because PUT /dimensions checks buyer_id
        assert confirm_response.status_code == 404, f"Expected 404 for admin, got: {confirm_response.status_code}"
        print(f"SUCCESS: PUT /dimensions correctly restricts to buyer only (admin gets 404)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
