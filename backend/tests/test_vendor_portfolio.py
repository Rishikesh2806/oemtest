"""
Vendor Portfolio API Tests
Tests for portfolio CRUD operations including:
- Public GET /api/vendors/{vendor_id}/portfolio (no auth)
- Admin POST /api/vendor/portfolio?vendor_id=xxx (admin creates for vendor)
- Admin DELETE /api/vendor/portfolio/{portfolio_id} (admin deletes any)
- Admin PUT /api/vendor/portfolio/{portfolio_id} (admin updates any)
"""

import pytest
import requests
import os
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from review request
ADMIN_EMAIL = "admin@offoadex.com"
ADMIN_PASSWORD = "admin123"
VENDOR_EMAIL = "testvendor_nda@test.com"
VENDOR_PASSWORD = "vendor123"
BUYER_EMAIL = "visualbuyer@test.com"
BUYER_PASSWORD = "buyer123"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def admin_token(api_client):
    """Get admin authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("access_token")
    pytest.skip(f"Admin authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def vendor_token(api_client):
    """Get vendor authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": VENDOR_EMAIL,
        "password": VENDOR_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("access_token")
    pytest.skip(f"Vendor authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def buyer_token(api_client):
    """Get buyer authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": BUYER_EMAIL,
        "password": BUYER_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("access_token")
    pytest.skip(f"Buyer authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def vendor_id(api_client, admin_token):
    """Get a vendor ID for testing"""
    response = api_client.get(
        f"{BASE_URL}/api/admin/vendors",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    if response.status_code == 200:
        data = response.json()
        # API returns array directly, not {"vendors": [...]}
        vendors = data if isinstance(data, list) else data.get("vendors", [])
        if vendors:
            return vendors[0].get("vendor_id")
    pytest.skip("No vendors found for testing")


class TestPublicPortfolioEndpoint:
    """Test GET /api/vendors/{vendor_id}/portfolio - Public endpoint (no auth)"""
    
    def test_get_vendor_portfolio_public_no_auth(self, api_client, vendor_id):
        """Public portfolio endpoint should work without authentication"""
        response = api_client.get(f"{BASE_URL}/api/vendors/{vendor_id}/portfolio")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "portfolio" in data, "Response should contain 'portfolio' key"
        assert "total" in data, "Response should contain 'total' key"
        assert isinstance(data["portfolio"], list), "Portfolio should be a list"
        print(f"PASS: Public portfolio endpoint returned {data['total']} items for vendor {vendor_id}")
    
    def test_get_vendor_portfolio_nonexistent_vendor(self, api_client):
        """Public portfolio endpoint should return empty for non-existent vendor"""
        response = api_client.get(f"{BASE_URL}/api/vendors/nonexistent_vendor_123/portfolio")
        
        # Should return 200 with empty portfolio, not 404
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["portfolio"] == [], "Portfolio should be empty for non-existent vendor"
        assert data["total"] == 0, "Total should be 0 for non-existent vendor"
        print("PASS: Non-existent vendor returns empty portfolio")


class TestAdminPortfolioUpload:
    """Test POST /api/vendor/portfolio with admin token and vendor_id query param"""
    
    def test_admin_upload_portfolio_for_vendor(self, api_client, admin_token, vendor_id):
        """Admin should be able to upload portfolio photo for any vendor"""
        # Create a simple test image (1x1 pixel PNG)
        test_image = io.BytesIO()
        # Minimal valid PNG
        test_image.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82')
        test_image.seek(0)
        
        files = {
            'file': ('test_image.png', test_image, 'image/png')
        }
        
        response = requests.post(
            f"{BASE_URL}/api/vendor/portfolio?vendor_id={vendor_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            files=files
        )
        
        # Accept 200 or 201 for successful upload
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "portfolio_id" in data, "Response should contain portfolio_id"
        assert data["portfolio_id"].startswith("port_"), "Portfolio ID should start with 'port_'"
        assert data["vendor_id"] == vendor_id, f"Vendor ID should match: expected {vendor_id}, got {data.get('vendor_id')}"
        
        # Store for cleanup
        TestAdminPortfolioUpload.created_portfolio_id = data["portfolio_id"]
        print(f"PASS: Admin uploaded portfolio {data['portfolio_id']} for vendor {vendor_id}")
    
    def test_admin_upload_without_vendor_id_fails(self, api_client, admin_token):
        """Admin upload without vendor_id should fail (admin has no vendor profile)"""
        test_image = io.BytesIO()
        test_image.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82')
        test_image.seek(0)
        
        files = {
            'file': ('test_image.png', test_image, 'image/png')
        }
        
        response = requests.post(
            f"{BASE_URL}/api/vendor/portfolio",
            headers={"Authorization": f"Bearer {admin_token}"},
            files=files
        )
        
        # Should fail because admin has no vendor profile
        assert response.status_code in [400, 403, 404], f"Expected 400/403/404, got {response.status_code}"
        print(f"PASS: Admin upload without vendor_id correctly rejected with {response.status_code}")
    
    def test_buyer_cannot_upload_portfolio(self, api_client, buyer_token, vendor_id):
        """Buyer should not be able to upload portfolio photos"""
        test_image = io.BytesIO()
        test_image.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82')
        test_image.seek(0)
        
        files = {
            'file': ('test_image.png', test_image, 'image/png')
        }
        
        response = requests.post(
            f"{BASE_URL}/api/vendor/portfolio?vendor_id={vendor_id}",
            headers={"Authorization": f"Bearer {buyer_token}"},
            files=files
        )
        
        # Buyer should be rejected
        assert response.status_code in [403, 401], f"Expected 403/401, got {response.status_code}"
        print(f"PASS: Buyer correctly rejected from uploading portfolio with {response.status_code}")


class TestAdminPortfolioUpdate:
    """Test PUT /api/vendor/portfolio/{portfolio_id} with admin token"""
    
    def test_admin_update_portfolio_item(self, api_client, admin_token, vendor_id):
        """Admin should be able to update any portfolio item's AI-detected fields"""
        # First, get existing portfolio items
        response = api_client.get(f"{BASE_URL}/api/vendors/{vendor_id}/portfolio")
        assert response.status_code == 200
        
        portfolio = response.json().get("portfolio", [])
        if not portfolio:
            pytest.skip("No portfolio items to update")
        
        portfolio_id = portfolio[0]["portfolio_id"]
        
        # Update the portfolio item
        update_data = {
            "part_category": "TEST_bracket",
            "manufacturing_process": "CNC machining",
            "material": "aluminum",
            "surface_finish": "anodized"
        }
        
        response = api_client.put(
            f"{BASE_URL}/api/vendor/portfolio/{portfolio_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=update_data
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True or "updated" in str(data).lower(), "Update should succeed"
        print(f"PASS: Admin updated portfolio item {portfolio_id}")
        
        # Verify the update persisted
        response = api_client.get(f"{BASE_URL}/api/vendors/{vendor_id}/portfolio")
        assert response.status_code == 200
        
        updated_portfolio = response.json().get("portfolio", [])
        updated_item = next((p for p in updated_portfolio if p["portfolio_id"] == portfolio_id), None)
        
        if updated_item:
            assert updated_item.get("part_category") == "TEST_bracket", "Part category should be updated"
            print(f"PASS: Verified portfolio update persisted")


class TestAdminPortfolioDelete:
    """Test DELETE /api/vendor/portfolio/{portfolio_id} with admin token"""
    
    def test_admin_delete_portfolio_item(self, api_client, admin_token, vendor_id):
        """Admin should be able to delete any portfolio item"""
        # First, upload a test item to delete
        test_image = io.BytesIO()
        test_image.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82')
        test_image.seek(0)
        
        files = {
            'file': ('test_delete.png', test_image, 'image/png')
        }
        
        upload_response = requests.post(
            f"{BASE_URL}/api/vendor/portfolio?vendor_id={vendor_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            files=files
        )
        
        if upload_response.status_code not in [200, 201]:
            pytest.skip(f"Could not upload test item: {upload_response.status_code}")
        
        portfolio_id = upload_response.json().get("portfolio_id")
        
        # Now delete it
        delete_response = api_client.delete(
            f"{BASE_URL}/api/vendor/portfolio/{portfolio_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert delete_response.status_code in [200, 204], f"Expected 200/204, got {delete_response.status_code}: {delete_response.text}"
        print(f"PASS: Admin deleted portfolio item {portfolio_id}")
        
        # Verify deletion
        verify_response = api_client.get(f"{BASE_URL}/api/vendors/{vendor_id}/portfolio")
        assert verify_response.status_code == 200
        
        remaining = verify_response.json().get("portfolio", [])
        deleted_item = next((p for p in remaining if p["portfolio_id"] == portfolio_id), None)
        assert deleted_item is None, "Deleted item should not exist in portfolio"
        print(f"PASS: Verified portfolio item {portfolio_id} was deleted")
    
    def test_buyer_cannot_delete_portfolio(self, api_client, buyer_token, vendor_id):
        """Buyer should not be able to delete portfolio items"""
        # Get a portfolio item
        response = api_client.get(f"{BASE_URL}/api/vendors/{vendor_id}/portfolio")
        portfolio = response.json().get("portfolio", [])
        
        if not portfolio:
            pytest.skip("No portfolio items to test delete")
        
        portfolio_id = portfolio[0]["portfolio_id"]
        
        delete_response = api_client.delete(
            f"{BASE_URL}/api/vendor/portfolio/{portfolio_id}",
            headers={"Authorization": f"Bearer {buyer_token}"}
        )
        
        # Buyer should be rejected
        assert delete_response.status_code in [403, 401, 404], f"Expected 403/401/404, got {delete_response.status_code}"
        print(f"PASS: Buyer correctly rejected from deleting portfolio with {delete_response.status_code}")


class TestPortfolioAITags:
    """Test that portfolio items have AI-detected tags"""
    
    def test_portfolio_items_have_expected_fields(self, api_client, vendor_id):
        """Portfolio items should have AI-detected tag fields"""
        response = api_client.get(f"{BASE_URL}/api/vendors/{vendor_id}/portfolio")
        assert response.status_code == 200
        
        portfolio = response.json().get("portfolio", [])
        
        if not portfolio:
            pytest.skip("No portfolio items to verify fields")
        
        # Check first item has expected fields
        item = portfolio[0]
        
        expected_fields = ["portfolio_id", "vendor_id", "photo_url", "created_at"]
        ai_tag_fields = ["part_category", "manufacturing_process", "material", "surface_finish", "complexity"]
        
        for field in expected_fields:
            assert field in item, f"Portfolio item should have '{field}' field"
        
        # AI tag fields may or may not be present depending on AI analysis
        present_tags = [f for f in ai_tag_fields if f in item and item[f]]
        print(f"PASS: Portfolio item has {len(present_tags)} AI-detected tags: {present_tags}")


class TestVendorOwnPortfolio:
    """Test vendor's own portfolio operations"""
    
    def test_vendor_get_own_portfolio(self, api_client, vendor_token):
        """Vendor should be able to get their own portfolio"""
        response = api_client.get(
            f"{BASE_URL}/api/vendor/portfolio",
            headers={"Authorization": f"Bearer {vendor_token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "portfolio" in data, "Response should contain 'portfolio' key"
        assert "total" in data, "Response should contain 'total' key"
        print(f"PASS: Vendor retrieved own portfolio with {data['total']} items")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
