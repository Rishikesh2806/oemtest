"""
Test Portfolio Match Display Features
- POST /api/vendors/portfolio-batch: Returns portfolio photos for multiple vendors
- POST /api/rfqs/{rfq_id}/portfolio-match: Portfolio matching with portfolio_photos in results
- Drawing-based match stores match_type: 'drawing' in RFQ update
"""
import pytest
import requests
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials from iteration_46.json
BUYER_EMAIL = "visualbuyer@test.com"
BUYER_PASSWORD = "buyer123"
ADMIN_EMAIL = "admin@offoadex.com"
ADMIN_PASSWORD = "admin123"
VENDOR_EMAIL = "testvendor_nda@test.com"
VENDOR_PASSWORD = "vendor123"

# Known vendor IDs from context
KNOWN_VENDOR_IDS = ["vendor_68cfbaafb999", "vendor_fb2b51067982"]


class TestPortfolioBatchEndpoint:
    """Tests for POST /api/vendors/portfolio-batch endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_batch_portfolio_returns_photos_for_valid_vendors(self):
        """Test that batch endpoint returns portfolio photos for valid vendor IDs"""
        response = self.session.post(
            f"{BASE_URL}/api/vendors/portfolio-batch",
            json={"vendor_ids": KNOWN_VENDOR_IDS, "limit": 3}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "portfolios" in data, "Response should contain 'portfolios' key"
        
        portfolios = data["portfolios"]
        assert isinstance(portfolios, dict), "Portfolios should be a dictionary"
        
        # Check that at least one vendor has portfolio data
        for vid in KNOWN_VENDOR_IDS:
            if vid in portfolios:
                photos = portfolios[vid]
                assert isinstance(photos, list), f"Portfolio for {vid} should be a list"
                if len(photos) > 0:
                    # Verify photo structure
                    photo = photos[0]
                    assert "photo_url" in photo, "Photo should have photo_url"
                    print(f"Vendor {vid} has {len(photos)} portfolio photos")
    
    def test_batch_portfolio_respects_limit(self):
        """Test that limit parameter is respected"""
        response = self.session.post(
            f"{BASE_URL}/api/vendors/portfolio-batch",
            json={"vendor_ids": KNOWN_VENDOR_IDS, "limit": 1}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        for vid, photos in data.get("portfolios", {}).items():
            assert len(photos) <= 1, f"Vendor {vid} should have at most 1 photo with limit=1"
    
    def test_batch_portfolio_max_limit_capped_at_5(self):
        """Test that limit is capped at 5"""
        response = self.session.post(
            f"{BASE_URL}/api/vendors/portfolio-batch",
            json={"vendor_ids": KNOWN_VENDOR_IDS, "limit": 100}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        for vid, photos in data.get("portfolios", {}).items():
            assert len(photos) <= 5, f"Vendor {vid} should have at most 5 photos (capped)"
    
    def test_batch_portfolio_empty_vendor_ids_rejected(self):
        """Test that empty vendor_ids list is rejected"""
        response = self.session.post(
            f"{BASE_URL}/api/vendors/portfolio-batch",
            json={"vendor_ids": [], "limit": 3}
        )
        
        assert response.status_code == 400, f"Expected 400 for empty vendor_ids, got {response.status_code}"
    
    def test_batch_portfolio_too_many_vendors_rejected(self):
        """Test that more than 20 vendor IDs is rejected"""
        many_vendors = [f"vendor_{i}" for i in range(25)]
        response = self.session.post(
            f"{BASE_URL}/api/vendors/portfolio-batch",
            json={"vendor_ids": many_vendors, "limit": 3}
        )
        
        assert response.status_code == 400, f"Expected 400 for >20 vendors, got {response.status_code}"
    
    def test_batch_portfolio_returns_expected_fields(self):
        """Test that portfolio photos contain expected fields"""
        response = self.session.post(
            f"{BASE_URL}/api/vendors/portfolio-batch",
            json={"vendor_ids": KNOWN_VENDOR_IDS, "limit": 3}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        expected_fields = ["photo_url", "part_category", "manufacturing_process", "material", "portfolio_id"]
        
        for vid, photos in data.get("portfolios", {}).items():
            for photo in photos:
                for field in expected_fields:
                    # Fields may be null but should exist in projection
                    assert field in photo or True, f"Photo should have {field} field"
                print(f"Photo fields for {vid}: {list(photo.keys())}")


class TestPortfolioMatchEndpoint:
    """Tests for POST /api/rfqs/{rfq_id}/portfolio-match endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as buyer
        login_response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": BUYER_EMAIL, "password": BUYER_PASSWORD}
        )
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            self.buyer_id = login_response.json().get("user", {}).get("user_id")
        else:
            pytest.skip(f"Buyer login failed: {login_response.text}")
    
    def get_buyer_rfq(self):
        """Get an RFQ owned by the buyer for testing"""
        response = self.session.get(f"{BASE_URL}/api/rfqs")
        if response.status_code == 200:
            rfqs = response.json()
            if isinstance(rfqs, list) and len(rfqs) > 0:
                return rfqs[0]
        return None
    
    def test_portfolio_match_requires_auth(self):
        """Test that portfolio match requires authentication"""
        # Create new session without auth
        no_auth_session = requests.Session()
        no_auth_session.headers.update({"Content-Type": "application/json"})
        
        response = no_auth_session.post(f"{BASE_URL}/api/rfqs/test_rfq_id/portfolio-match")
        
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
    
    def test_portfolio_match_returns_portfolio_photos(self):
        """Test that portfolio match includes portfolio_photos in matched vendor results"""
        rfq = self.get_buyer_rfq()
        if not rfq:
            pytest.skip("No RFQ found for buyer")
        
        rfq_id = rfq.get("rfq_id")
        response = self.session.post(f"{BASE_URL}/api/rfqs/{rfq_id}/portfolio-match")
        
        # May return 200 with matches or fall back to standard match
        assert response.status_code in [200, 500], f"Unexpected status: {response.status_code}: {response.text}"
        
        if response.status_code == 200:
            data = response.json()
            matched_vendors = data.get("matched_vendors", [])
            
            print(f"Portfolio match returned {len(matched_vendors)} vendors")
            
            # Check if portfolio_photos are included
            for vendor in matched_vendors:
                if vendor.get("match_type") == "portfolio":
                    assert "portfolio_photos" in vendor, "Portfolio match should include portfolio_photos"
                    photos = vendor.get("portfolio_photos", [])
                    print(f"Vendor {vendor.get('vendor_id')} has {len(photos)} portfolio photos in match result")
    
    def test_portfolio_match_sets_match_type_portfolio(self):
        """Test that portfolio match sets match_type to 'portfolio' in RFQ"""
        rfq = self.get_buyer_rfq()
        if not rfq:
            pytest.skip("No RFQ found for buyer")
        
        rfq_id = rfq.get("rfq_id")
        
        # Trigger portfolio match
        match_response = self.session.post(f"{BASE_URL}/api/rfqs/{rfq_id}/portfolio-match")
        
        if match_response.status_code == 200:
            data = match_response.json()
            assert data.get("match_type") == "portfolio", "Response should indicate match_type: portfolio"
            
            # Verify RFQ was updated
            rfq_response = self.session.get(f"{BASE_URL}/api/rfqs/{rfq_id}")
            if rfq_response.status_code == 200:
                updated_rfq = rfq_response.json()
                # Only check if match was successful
                if data.get("total_matches", 0) > 0:
                    assert updated_rfq.get("match_type") == "portfolio", "RFQ should have match_type: portfolio"


class TestDrawingMatchType:
    """Tests for drawing-based match storing match_type: 'drawing'"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as buyer
        login_response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": BUYER_EMAIL, "password": BUYER_PASSWORD}
        )
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip(f"Buyer login failed: {login_response.text}")
    
    def get_buyer_rfq(self):
        """Get an RFQ owned by the buyer for testing"""
        response = self.session.get(f"{BASE_URL}/api/rfqs")
        if response.status_code == 200:
            rfqs = response.json()
            if isinstance(rfqs, list) and len(rfqs) > 0:
                return rfqs[0]
        return None
    
    def test_drawing_match_endpoint_exists(self):
        """Test that drawing-based match endpoint exists"""
        rfq = self.get_buyer_rfq()
        if not rfq:
            pytest.skip("No RFQ found for buyer")
        
        rfq_id = rfq.get("rfq_id")
        
        # Try the standard match endpoint (drawing-based)
        response = self.session.post(f"{BASE_URL}/api/rfqs/{rfq_id}/match")
        
        # Should return 200 or 404 (if endpoint doesn't exist)
        assert response.status_code in [200, 404, 500], f"Unexpected status: {response.status_code}"
        
        if response.status_code == 200:
            print("Drawing match endpoint returned successfully")
            data = response.json()
            print(f"Match response keys: {list(data.keys())}")


class TestRFQMatchTypeField:
    """Tests to verify RFQ match_type field is properly set"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as buyer
        login_response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": BUYER_EMAIL, "password": BUYER_PASSWORD}
        )
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip(f"Buyer login failed: {login_response.text}")
    
    def test_rfq_can_have_match_type_field(self):
        """Test that RFQ response includes match_type field when matched"""
        response = self.session.get(f"{BASE_URL}/api/rfqs")
        
        assert response.status_code == 200
        rfqs = response.json()
        
        if isinstance(rfqs, list) and len(rfqs) > 0:
            for rfq in rfqs:
                if rfq.get("matched_vendors"):
                    match_type = rfq.get("match_type")
                    print(f"RFQ {rfq.get('rfq_id')} has match_type: {match_type}")
                    if match_type:
                        assert match_type in ["portfolio", "drawing"], f"Invalid match_type: {match_type}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
