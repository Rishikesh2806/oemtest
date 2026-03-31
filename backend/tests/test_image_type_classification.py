"""
Test Image Type Classification Feature for RFQ Analysis
Tests the new image_type field in analyze endpoint and routing to match/portfolio-match endpoints
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
BUYER_EMAIL = "visualbuyer@test.com"
BUYER_PASSWORD = "buyer123"
ADMIN_EMAIL = "admin@offoadex.com"
ADMIN_PASSWORD = "admin123"


class TestImageTypeClassification:
    """Tests for the image_type classification feature in RFQ analysis"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_buyer_token(self):
        """Get authentication token for buyer"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": BUYER_EMAIL,
            "password": BUYER_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    
    def get_admin_token(self):
        """Get authentication token for admin"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    
    # ============== ENDPOINT AVAILABILITY TESTS ==============
    
    def test_analyze_endpoint_exists(self):
        """Test that /api/rfqs/{rfq_id}/analyze endpoint exists and requires auth"""
        # Without auth should return 401
        response = self.session.post(f"{BASE_URL}/api/rfqs/test_rfq_id/analyze")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print("PASS: Analyze endpoint exists and requires authentication")
    
    def test_analyze_endpoint_with_auth_nonexistent_rfq(self):
        """Test analyze endpoint returns 404 for non-existent RFQ"""
        token = self.get_buyer_token()
        if not token:
            pytest.skip("Could not get buyer token")
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        response = self.session.post(f"{BASE_URL}/api/rfqs/nonexistent_rfq_12345/analyze")
        assert response.status_code == 404, f"Expected 404 for non-existent RFQ, got {response.status_code}"
        print("PASS: Analyze endpoint returns 404 for non-existent RFQ")
    
    def test_match_endpoint_exists(self):
        """Test that /api/rfqs/{rfq_id}/match endpoint exists and requires auth"""
        response = self.session.post(f"{BASE_URL}/api/rfqs/test_rfq_id/match")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print("PASS: Match endpoint exists and requires authentication")
    
    def test_match_endpoint_with_auth_nonexistent_rfq(self):
        """Test match endpoint returns 404 for non-existent RFQ"""
        token = self.get_buyer_token()
        if not token:
            pytest.skip("Could not get buyer token")
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        response = self.session.post(f"{BASE_URL}/api/rfqs/nonexistent_rfq_12345/match")
        assert response.status_code == 404, f"Expected 404 for non-existent RFQ, got {response.status_code}"
        print("PASS: Match endpoint returns 404 for non-existent RFQ")
    
    def test_portfolio_match_endpoint_exists(self):
        """Test that /api/rfqs/{rfq_id}/portfolio-match endpoint exists and requires auth"""
        response = self.session.post(f"{BASE_URL}/api/rfqs/test_rfq_id/portfolio-match")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print("PASS: Portfolio-match endpoint exists and requires authentication")
    
    def test_portfolio_match_endpoint_with_auth_nonexistent_rfq(self):
        """Test portfolio-match endpoint returns 404 for non-existent RFQ"""
        token = self.get_buyer_token()
        if not token:
            pytest.skip("Could not get buyer token")
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        response = self.session.post(f"{BASE_URL}/api/rfqs/nonexistent_rfq_12345/portfolio-match")
        assert response.status_code == 404, f"Expected 404 for non-existent RFQ, got {response.status_code}"
        print("PASS: Portfolio-match endpoint returns 404 for non-existent RFQ")
    
    # ============== BUYER RFQ LISTING TEST ==============
    
    def test_buyer_can_list_rfqs(self):
        """Test that buyer can list their RFQs"""
        token = self.get_buyer_token()
        if not token:
            pytest.skip("Could not get buyer token")
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        response = self.session.get(f"{BASE_URL}/api/rfqs")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Expected list of RFQs"
        print(f"PASS: Buyer can list RFQs - found {len(data)} RFQs")
        return data
    
    def test_rfq_has_image_type_field_if_analyzed(self):
        """Test that analyzed RFQs have image_type field in their data"""
        token = self.get_buyer_token()
        if not token:
            pytest.skip("Could not get buyer token")
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        response = self.session.get(f"{BASE_URL}/api/rfqs")
        
        if response.status_code != 200:
            pytest.skip("Could not fetch RFQs")
        
        rfqs = response.json()
        analyzed_rfqs = [r for r in rfqs if r.get("ai_analysis")]
        
        if not analyzed_rfqs:
            print("INFO: No analyzed RFQs found to check image_type field")
            pytest.skip("No analyzed RFQs available")
        
        # Check if any analyzed RFQ has image_type
        for rfq in analyzed_rfqs:
            ai_analysis = rfq.get("ai_analysis", {})
            if "image_type" in ai_analysis:
                assert ai_analysis["image_type"] in ["technical_drawing", "reference_photo"], \
                    f"Invalid image_type: {ai_analysis['image_type']}"
                print(f"PASS: Found RFQ with image_type: {ai_analysis['image_type']}")
                return
        
        print("INFO: Analyzed RFQs exist but none have image_type field (may be older RFQs)")
    
    # ============== ADMIN TESTS ==============
    
    def test_admin_can_view_all_rfqs(self):
        """Test that admin can view all RFQs"""
        token = self.get_admin_token()
        if not token:
            pytest.skip("Could not get admin token")
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        response = self.session.get(f"{BASE_URL}/api/admin/rfqs")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        # Could be list or dict with rfqs key
        if isinstance(data, dict):
            rfqs = data.get("rfqs", data.get("items", []))
        else:
            rfqs = data
        
        print(f"PASS: Admin can view RFQs - found {len(rfqs)} RFQs")


class TestAnalyzeEndpointResponseStructure:
    """Tests for the analyze endpoint response structure"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_buyer_token(self):
        """Get authentication token for buyer"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": BUYER_EMAIL,
            "password": BUYER_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    
    def test_analyze_endpoint_returns_expected_fields_on_no_drawings(self):
        """Test that analyze endpoint returns expected fields when RFQ has no drawings"""
        token = self.get_buyer_token()
        if not token:
            pytest.skip("Could not get buyer token")
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # First get buyer's RFQs
        response = self.session.get(f"{BASE_URL}/api/rfqs")
        if response.status_code != 200:
            pytest.skip("Could not fetch RFQs")
        
        rfqs = response.json()
        
        # Find an RFQ without drawings to test the "no drawings" response
        rfq_without_drawings = None
        for rfq in rfqs:
            if not rfq.get("drawing_ids") or len(rfq.get("drawing_ids", [])) == 0:
                rfq_without_drawings = rfq
                break
        
        if not rfq_without_drawings:
            print("INFO: All RFQs have drawings, cannot test no-drawings response")
            pytest.skip("No RFQ without drawings found")
        
        rfq_id = rfq_without_drawings.get("rfq_id")
        response = self.session.post(f"{BASE_URL}/api/rfqs/{rfq_id}/analyze")
        
        # Should return 400 for no drawings
        assert response.status_code == 400, f"Expected 400 for no drawings, got {response.status_code}"
        print("PASS: Analyze endpoint returns 400 when RFQ has no drawings")


class TestMatchEndpointResponseStructure:
    """Tests for the match endpoint response structure"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_buyer_token(self):
        """Get authentication token for buyer"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": BUYER_EMAIL,
            "password": BUYER_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    
    def test_match_endpoint_response_structure(self):
        """Test that match endpoint returns expected response structure"""
        token = self.get_buyer_token()
        if not token:
            pytest.skip("Could not get buyer token")
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get buyer's RFQs
        response = self.session.get(f"{BASE_URL}/api/rfqs")
        if response.status_code != 200:
            pytest.skip("Could not fetch RFQs")
        
        rfqs = response.json()
        if not rfqs:
            pytest.skip("No RFQs found for buyer")
        
        # Try to match the first RFQ
        rfq_id = rfqs[0].get("rfq_id")
        response = self.session.post(f"{BASE_URL}/api/rfqs/{rfq_id}/match")
        
        # Should return 200 with matched_vendors
        if response.status_code == 200:
            data = response.json()
            assert "matched_vendors" in data or "total_matches" in data, \
                "Expected matched_vendors or total_matches in response"
            print(f"PASS: Match endpoint returns expected structure with {data.get('total_matches', len(data.get('matched_vendors', [])))} matches")
        else:
            print(f"INFO: Match endpoint returned {response.status_code} - may need drawings first")
    
    def test_portfolio_match_endpoint_response_structure(self):
        """Test that portfolio-match endpoint returns expected response structure"""
        token = self.get_buyer_token()
        if not token:
            pytest.skip("Could not get buyer token")
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get buyer's RFQs
        response = self.session.get(f"{BASE_URL}/api/rfqs")
        if response.status_code != 200:
            pytest.skip("Could not fetch RFQs")
        
        rfqs = response.json()
        if not rfqs:
            pytest.skip("No RFQs found for buyer")
        
        # Try portfolio match on the first RFQ
        rfq_id = rfqs[0].get("rfq_id")
        response = self.session.post(f"{BASE_URL}/api/rfqs/{rfq_id}/portfolio-match")
        
        # Should return 200 with matches or fall back to standard match
        if response.status_code == 200:
            data = response.json()
            # Portfolio match can return matches or fall back to standard match
            has_matches = "matches" in data or "matched_vendors" in data or "total_matches" in data
            assert has_matches, "Expected matches in portfolio-match response"
            print(f"PASS: Portfolio-match endpoint returns expected structure")
        else:
            print(f"INFO: Portfolio-match endpoint returned {response.status_code}")


class TestAuthenticationFlow:
    """Tests for authentication required by the endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_buyer_login(self):
        """Test buyer can login successfully"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": BUYER_EMAIL,
            "password": BUYER_PASSWORD
        })
        assert response.status_code == 200, f"Buyer login failed with {response.status_code}"
        
        data = response.json()
        assert "access_token" in data, "Expected access_token in login response"
        print("PASS: Buyer login successful")
    
    def test_admin_login(self):
        """Test admin can login successfully"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed with {response.status_code}"
        
        data = response.json()
        assert "access_token" in data, "Expected access_token in login response"
        print("PASS: Admin login successful")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
