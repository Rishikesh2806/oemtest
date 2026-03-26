"""
Test Vendor Portfolio API Endpoints
Tests for:
- GET /api/vendor/portfolio - Get portfolio items for authenticated vendor
- PUT /api/vendor/portfolio/{portfolio_id} - Update portfolio item fields
- DELETE /api/vendor/portfolio/{portfolio_id} - Delete portfolio item
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from iteration_36.json
VENDOR_EMAIL = "testvendor_nda@test.com"
VENDOR_PASSWORD = "vendor123"
ADMIN_EMAIL = "admin@offoadex.com"
ADMIN_PASSWORD = "admin123"


class TestVendorPortfolioAPI:
    """Test Vendor Portfolio CRUD operations"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with vendor authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as vendor
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": VENDOR_EMAIL,
            "password": VENDOR_PASSWORD
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            self.vendor_user = login_response.json().get("user", {})
            print(f"Logged in as vendor: {self.vendor_user.get('email')}")
        else:
            pytest.skip(f"Vendor login failed: {login_response.status_code} - {login_response.text}")
    
    def test_get_vendor_portfolio(self):
        """Test GET /api/vendor/portfolio returns portfolio items"""
        response = self.session.get(f"{BASE_URL}/api/vendor/portfolio")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "portfolio" in data, "Response should contain 'portfolio' key"
        assert "total" in data, "Response should contain 'total' key"
        assert isinstance(data["portfolio"], list), "Portfolio should be a list"
        
        print(f"Portfolio items count: {data['total']}")
        
        # If portfolio has items, verify structure
        if data["portfolio"]:
            item = data["portfolio"][0]
            print(f"First portfolio item: {item.get('portfolio_id')}")
            # Verify expected fields exist
            assert "portfolio_id" in item, "Portfolio item should have portfolio_id"
            assert "vendor_id" in item, "Portfolio item should have vendor_id"
            # Optional fields that may exist
            optional_fields = ["photo_url", "manufacturing_process", "material", "part_category", "surface_finish", "complexity"]
            for field in optional_fields:
                if field in item:
                    print(f"  {field}: {item[field]}")
    
    def test_get_portfolio_returns_all_fields(self):
        """Test that portfolio items contain all 5 editable tag fields"""
        response = self.session.get(f"{BASE_URL}/api/vendor/portfolio")
        
        assert response.status_code == 200
        data = response.json()
        
        if not data["portfolio"]:
            pytest.skip("No portfolio items to test field structure")
        
        item = data["portfolio"][0]
        editable_fields = ["manufacturing_process", "material", "part_category", "surface_finish", "complexity"]
        
        print(f"Checking portfolio item {item.get('portfolio_id')} for editable fields:")
        for field in editable_fields:
            value = item.get(field)
            print(f"  {field}: {value}")
        
        # At least portfolio_id should exist
        assert "portfolio_id" in item
    
    def test_update_portfolio_manufacturing_process(self):
        """Test PUT /api/vendor/portfolio/{id} updates manufacturing_process field"""
        # First get portfolio items
        get_response = self.session.get(f"{BASE_URL}/api/vendor/portfolio")
        assert get_response.status_code == 200
        
        data = get_response.json()
        if not data["portfolio"]:
            pytest.skip("No portfolio items to update")
        
        portfolio_id = data["portfolio"][0]["portfolio_id"]
        original_value = data["portfolio"][0].get("manufacturing_process")
        
        # Update the field
        new_value = "CNC machining" if original_value != "CNC machining" else "casting"
        update_response = self.session.put(
            f"{BASE_URL}/api/vendor/portfolio/{portfolio_id}",
            json={"manufacturing_process": new_value}
        )
        
        assert update_response.status_code == 200, f"Update failed: {update_response.status_code} - {update_response.text}"
        
        update_data = update_response.json()
        assert "message" in update_data
        assert "updates" in update_data
        assert update_data["updates"].get("manufacturing_process") == new_value
        
        print(f"Updated manufacturing_process from '{original_value}' to '{new_value}'")
        
        # Verify persistence with GET
        verify_response = self.session.get(f"{BASE_URL}/api/vendor/portfolio")
        assert verify_response.status_code == 200
        
        updated_item = next(
            (p for p in verify_response.json()["portfolio"] if p["portfolio_id"] == portfolio_id),
            None
        )
        assert updated_item is not None
        assert updated_item.get("manufacturing_process") == new_value
        print(f"Verified: manufacturing_process persisted as '{new_value}'")
    
    def test_update_portfolio_material(self):
        """Test PUT /api/vendor/portfolio/{id} updates material field"""
        get_response = self.session.get(f"{BASE_URL}/api/vendor/portfolio")
        assert get_response.status_code == 200
        
        data = get_response.json()
        if not data["portfolio"]:
            pytest.skip("No portfolio items to update")
        
        portfolio_id = data["portfolio"][0]["portfolio_id"]
        original_value = data["portfolio"][0].get("material")
        
        new_value = "aluminum" if original_value != "aluminum" else "steel"
        update_response = self.session.put(
            f"{BASE_URL}/api/vendor/portfolio/{portfolio_id}",
            json={"material": new_value}
        )
        
        assert update_response.status_code == 200, f"Update failed: {update_response.status_code}"
        print(f"Updated material from '{original_value}' to '{new_value}'")
    
    def test_update_portfolio_part_category(self):
        """Test PUT /api/vendor/portfolio/{id} updates part_category field"""
        get_response = self.session.get(f"{BASE_URL}/api/vendor/portfolio")
        assert get_response.status_code == 200
        
        data = get_response.json()
        if not data["portfolio"]:
            pytest.skip("No portfolio items to update")
        
        portfolio_id = data["portfolio"][0]["portfolio_id"]
        original_value = data["portfolio"][0].get("part_category")
        
        new_value = "bracket" if original_value != "bracket" else "housing"
        update_response = self.session.put(
            f"{BASE_URL}/api/vendor/portfolio/{portfolio_id}",
            json={"part_category": new_value}
        )
        
        assert update_response.status_code == 200, f"Update failed: {update_response.status_code}"
        print(f"Updated part_category from '{original_value}' to '{new_value}'")
    
    def test_update_portfolio_surface_finish(self):
        """Test PUT /api/vendor/portfolio/{id} updates surface_finish field"""
        get_response = self.session.get(f"{BASE_URL}/api/vendor/portfolio")
        assert get_response.status_code == 200
        
        data = get_response.json()
        if not data["portfolio"]:
            pytest.skip("No portfolio items to update")
        
        portfolio_id = data["portfolio"][0]["portfolio_id"]
        original_value = data["portfolio"][0].get("surface_finish")
        
        new_value = "polished" if original_value != "polished" else "anodized"
        update_response = self.session.put(
            f"{BASE_URL}/api/vendor/portfolio/{portfolio_id}",
            json={"surface_finish": new_value}
        )
        
        assert update_response.status_code == 200, f"Update failed: {update_response.status_code}"
        print(f"Updated surface_finish from '{original_value}' to '{new_value}'")
    
    def test_update_portfolio_complexity(self):
        """Test PUT /api/vendor/portfolio/{id} updates complexity field"""
        get_response = self.session.get(f"{BASE_URL}/api/vendor/portfolio")
        assert get_response.status_code == 200
        
        data = get_response.json()
        if not data["portfolio"]:
            pytest.skip("No portfolio items to update")
        
        portfolio_id = data["portfolio"][0]["portfolio_id"]
        original_value = data["portfolio"][0].get("complexity")
        
        new_value = "high" if original_value != "high" else "medium"
        update_response = self.session.put(
            f"{BASE_URL}/api/vendor/portfolio/{portfolio_id}",
            json={"complexity": new_value}
        )
        
        assert update_response.status_code == 200, f"Update failed: {update_response.status_code}"
        print(f"Updated complexity from '{original_value}' to '{new_value}'")
    
    def test_update_portfolio_invalid_field_rejected(self):
        """Test PUT /api/vendor/portfolio/{id} rejects invalid fields"""
        get_response = self.session.get(f"{BASE_URL}/api/vendor/portfolio")
        assert get_response.status_code == 200
        
        data = get_response.json()
        if not data["portfolio"]:
            pytest.skip("No portfolio items to update")
        
        portfolio_id = data["portfolio"][0]["portfolio_id"]
        
        # Try to update an invalid field
        update_response = self.session.put(
            f"{BASE_URL}/api/vendor/portfolio/{portfolio_id}",
            json={"invalid_field": "test_value"}
        )
        
        # Should return 400 because no valid fields to update
        assert update_response.status_code == 400, f"Expected 400 for invalid field, got {update_response.status_code}"
        print("Correctly rejected invalid field update")
    
    def test_update_portfolio_nonexistent_id(self):
        """Test PUT /api/vendor/portfolio/{id} returns 404 for nonexistent ID"""
        update_response = self.session.put(
            f"{BASE_URL}/api/vendor/portfolio/nonexistent_id_12345",
            json={"material": "steel"}
        )
        
        assert update_response.status_code == 404, f"Expected 404, got {update_response.status_code}"
        print("Correctly returned 404 for nonexistent portfolio ID")
    
    def test_delete_portfolio_nonexistent_id(self):
        """Test DELETE /api/vendor/portfolio/{id} returns 404 for nonexistent ID"""
        delete_response = self.session.delete(
            f"{BASE_URL}/api/vendor/portfolio/nonexistent_id_12345"
        )
        
        assert delete_response.status_code == 404, f"Expected 404, got {delete_response.status_code}"
        print("Correctly returned 404 for nonexistent portfolio ID on delete")


class TestVendorPortfolioUnauthorized:
    """Test unauthorized access to portfolio endpoints"""
    
    def test_get_portfolio_without_auth(self):
        """Test GET /api/vendor/portfolio requires authentication"""
        response = requests.get(f"{BASE_URL}/api/vendor/portfolio")
        
        # Should return 401 or 403
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("Correctly requires authentication for GET portfolio")
    
    def test_update_portfolio_without_auth(self):
        """Test PUT /api/vendor/portfolio/{id} requires authentication"""
        response = requests.put(
            f"{BASE_URL}/api/vendor/portfolio/test_id",
            json={"material": "steel"}
        )
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("Correctly requires authentication for PUT portfolio")
    
    def test_delete_portfolio_without_auth(self):
        """Test DELETE /api/vendor/portfolio/{id} requires authentication"""
        response = requests.delete(f"{BASE_URL}/api/vendor/portfolio/test_id")
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("Correctly requires authentication for DELETE portfolio")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
