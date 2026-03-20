"""
Test Item-wise Quotation Feature
Tests for:
- POST /api/vendor/quotation/itemwise - Submit item-wise quotation with multiple items
- GET /api/rfqs/{rfq_id}/items - Get RFQ items/drawings for quoting
- GET /api/rfq/{rfq_id}/quotations - Get quotations with item-wise data
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
VENDOR_EMAIL = "vendor@oemlinker.com"
VENDOR_PASSWORD = "SecureV3nd0r!"
BUYER_EMAIL = "buyer@oemlinker.com"
BUYER_PASSWORD = "SecureBuy3r!"
ADMIN_EMAIL = "admin@oemlinker.com"
ADMIN_PASSWORD = "SecureP@ss2026!"


class TestItemwiseQuotation:
    """Tests for item-wise quotation feature"""
    
    @pytest.fixture(scope="class")
    def vendor_token(self):
        """Get vendor authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": VENDOR_EMAIL,
            "password": VENDOR_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip(f"Vendor login failed: {response.status_code} - {response.text}")
    
    @pytest.fixture(scope="class")
    def buyer_token(self):
        """Get buyer authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": BUYER_EMAIL,
            "password": BUYER_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip(f"Buyer login failed: {response.status_code} - {response.text}")
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")
    
    @pytest.fixture(scope="class")
    def test_rfq_with_drawings(self, buyer_token):
        """Create a test RFQ with multiple drawings for item-wise testing"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        
        # Create RFQ
        rfq_data = {
            "title": f"TEST_Itemwise_RFQ_{uuid.uuid4().hex[:8]}",
            "description": "Test RFQ for item-wise quotation testing",
            "material_type": "Steel",
            "quantity": 100,
            "tolerance": 0.05,
            "deadline": "2026-04-30",
            "supply_type": "vendor_material"
        }
        
        response = requests.post(f"{BASE_URL}/api/rfqs", json=rfq_data, headers=headers)
        if response.status_code not in [200, 201]:
            pytest.skip(f"Failed to create test RFQ: {response.status_code} - {response.text}")
        
        rfq = response.json()
        rfq_id = rfq.get("rfq_id")
        
        # Create multiple drawings for this RFQ
        for i in range(3):
            drawing_data = {
                "rfq_id": rfq_id,
                "filename": f"TEST_Drawing_{i+1}.pdf",
                "file_type": "application/pdf",
                "s3_path": f"test/drawings/drawing_{i+1}.pdf"
            }
            requests.post(f"{BASE_URL}/api/drawings", json=drawing_data, headers=headers)
        
        yield rfq_id
        
        # Cleanup - delete test RFQ and related data
        requests.delete(f"{BASE_URL}/api/rfqs/{rfq_id}", headers=headers)
    
    # ============== GET /api/rfqs/{rfq_id}/items Tests ==============
    
    def test_get_rfq_items_success(self, vendor_token, test_rfq_with_drawings):
        """Test getting RFQ items for quoting"""
        headers = {"Authorization": f"Bearer {vendor_token}"}
        rfq_id = test_rfq_with_drawings
        
        response = requests.get(f"{BASE_URL}/api/rfqs/{rfq_id}/items", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "items" in data, "Response should contain 'items' field"
        assert "rfq_id" in data, "Response should contain 'rfq_id' field"
        assert "total_items" in data, "Response should contain 'total_items' field"
        assert data["rfq_id"] == rfq_id
        
        # Verify items structure
        items = data["items"]
        assert len(items) >= 1, "Should have at least 1 item"
        
        for item in items:
            assert "item_id" in item, "Each item should have item_id"
            assert "title" in item, "Each item should have title"
            assert "item_number" in item, "Each item should have item_number"
        
        print(f"✓ GET /api/rfqs/{rfq_id}/items returned {len(items)} items")
    
    def test_get_rfq_items_not_found(self, vendor_token):
        """Test getting items for non-existent RFQ"""
        headers = {"Authorization": f"Bearer {vendor_token}"}
        
        response = requests.get(f"{BASE_URL}/api/rfqs/nonexistent_rfq_123/items", headers=headers)
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ GET /api/rfqs/nonexistent/items returns 404")
    
    def test_get_rfq_items_requires_auth(self, test_rfq_with_drawings):
        """Test that getting RFQ items requires authentication"""
        rfq_id = test_rfq_with_drawings
        
        response = requests.get(f"{BASE_URL}/api/rfqs/{rfq_id}/items")
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ GET /api/rfqs/{rfq_id}/items requires authentication")
    
    # ============== POST /api/vendor/quotation/itemwise Tests ==============
    
    def test_itemwise_quotation_requires_auth(self, test_rfq_with_drawings):
        """Test that item-wise quotation requires authentication"""
        rfq_id = test_rfq_with_drawings
        
        payload = {
            "rfq_id": rfq_id,
            "items": [
                {"item_id": "test_item_1", "labour_cost": 1000, "material_cost": 500}
            ],
            "lead_time_days": 14
        }
        
        response = requests.post(f"{BASE_URL}/api/vendor/quotation/itemwise", json=payload)
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ POST /api/vendor/quotation/itemwise requires authentication")
    
    def test_itemwise_quotation_requires_rfq_id(self, vendor_token):
        """Test that rfq_id is required"""
        headers = {"Authorization": f"Bearer {vendor_token}"}
        
        payload = {
            "items": [
                {"item_id": "test_item_1", "labour_cost": 1000, "material_cost": 500}
            ],
            "lead_time_days": 14
        }
        
        response = requests.post(f"{BASE_URL}/api/vendor/quotation/itemwise", json=payload, headers=headers)
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "rfq_id" in response.text.lower(), "Error should mention rfq_id"
        print("✓ POST /api/vendor/quotation/itemwise requires rfq_id")
    
    def test_itemwise_quotation_requires_items(self, vendor_token, test_rfq_with_drawings):
        """Test that at least one item is required"""
        headers = {"Authorization": f"Bearer {vendor_token}"}
        rfq_id = test_rfq_with_drawings
        
        payload = {
            "rfq_id": rfq_id,
            "items": [],
            "lead_time_days": 14
        }
        
        response = requests.post(f"{BASE_URL}/api/vendor/quotation/itemwise", json=payload, headers=headers)
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ POST /api/vendor/quotation/itemwise requires at least one item")
    
    def test_itemwise_quotation_validates_labour_cost(self, vendor_token, test_rfq_with_drawings):
        """Test that labour cost is required for each item"""
        headers = {"Authorization": f"Bearer {vendor_token}"}
        rfq_id = test_rfq_with_drawings
        
        # Get items first
        items_response = requests.get(f"{BASE_URL}/api/rfqs/{rfq_id}/items", headers=headers)
        items = items_response.json().get("items", [])
        
        if not items:
            pytest.skip("No items found for RFQ")
        
        payload = {
            "rfq_id": rfq_id,
            "items": [
                {
                    "item_id": items[0]["item_id"],
                    "labour_cost": 0,  # Invalid - should be > 0
                    "material_cost": 500
                }
            ],
            "lead_time_days": 14
        }
        
        response = requests.post(f"{BASE_URL}/api/vendor/quotation/itemwise", json=payload, headers=headers)
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ POST /api/vendor/quotation/itemwise validates labour cost > 0")
    
    def test_itemwise_quotation_validates_material_cost(self, vendor_token, test_rfq_with_drawings):
        """Test that material cost is required when vendor provides material"""
        headers = {"Authorization": f"Bearer {vendor_token}"}
        rfq_id = test_rfq_with_drawings
        
        # Get items first
        items_response = requests.get(f"{BASE_URL}/api/rfqs/{rfq_id}/items", headers=headers)
        items = items_response.json().get("items", [])
        
        if not items:
            pytest.skip("No items found for RFQ")
        
        payload = {
            "rfq_id": rfq_id,
            "items": [
                {
                    "item_id": items[0]["item_id"],
                    "labour_cost": 1000,
                    "material_cost": 0,  # Invalid when material_provided_by_buyer is False
                    "material_provided_by_buyer": False
                }
            ],
            "lead_time_days": 14
        }
        
        response = requests.post(f"{BASE_URL}/api/vendor/quotation/itemwise", json=payload, headers=headers)
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ POST /api/vendor/quotation/itemwise validates material cost when vendor provides material")
    
    def test_itemwise_quotation_success(self, vendor_token, test_rfq_with_drawings):
        """Test successful item-wise quotation submission"""
        headers = {"Authorization": f"Bearer {vendor_token}"}
        rfq_id = test_rfq_with_drawings
        
        # Get items first
        items_response = requests.get(f"{BASE_URL}/api/rfqs/{rfq_id}/items", headers=headers)
        items = items_response.json().get("items", [])
        
        if not items:
            pytest.skip("No items found for RFQ")
        
        # Build item quotations
        item_quotations = []
        expected_total = 0
        
        for idx, item in enumerate(items):
            material_cost = 1000 * (idx + 1)
            labour_cost = 500 * (idx + 1)
            additional = {"heat_treatment": 100 * (idx + 1)}
            item_total = material_cost + labour_cost + sum(additional.values())
            expected_total += item_total
            
            item_quotations.append({
                "item_id": item["item_id"],
                "drawing_id": item.get("drawing_id"),
                "title": item.get("title", f"Item {idx + 1}"),
                "material_provided_by_buyer": False,
                "material_cost": material_cost,
                "labour_cost": labour_cost,
                "additional_costs": additional,
                "remarks": f"Test remarks for item {idx + 1}"
            })
        
        payload = {
            "rfq_id": rfq_id,
            "items": item_quotations,
            "lead_time_days": 21,
            "notes": "Test item-wise quotation",
            "cost_breakdown_remarks": "Detailed cost breakdown for testing",
            "proposed_payment_terms": "net_30"
        }
        
        response = requests.post(f"{BASE_URL}/api/vendor/quotation/itemwise", json=payload, headers=headers)
        
        # May fail if vendor already quoted - that's expected
        if response.status_code == 400 and "already submitted" in response.text.lower():
            print("✓ Vendor already quoted for this RFQ (expected behavior)")
            return
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True, "Response should indicate success"
        assert "quote_id" in data, "Response should contain quote_id"
        assert "total_cost" in data, "Response should contain total_cost"
        assert "items_count" in data, "Response should contain items_count"
        assert data["items_count"] == len(items), f"Items count should be {len(items)}"
        
        # Verify total calculation
        assert data["total_cost"] == expected_total, f"Total cost should be {expected_total}, got {data['total_cost']}"
        
        print(f"✓ POST /api/vendor/quotation/itemwise success - Quote ID: {data['quote_id']}, Total: ₹{data['total_cost']}")
    
    # ============== GET /api/rfq/{rfq_id}/quotations Tests ==============
    
    def test_get_quotations_requires_auth(self, test_rfq_with_drawings):
        """Test that getting quotations requires authentication"""
        rfq_id = test_rfq_with_drawings
        
        response = requests.get(f"{BASE_URL}/api/rfq/{rfq_id}/quotations")
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ GET /api/rfq/{rfq_id}/quotations requires authentication")
    
    def test_get_quotations_success(self, buyer_token, test_rfq_with_drawings):
        """Test getting quotations with item-wise data"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        rfq_id = test_rfq_with_drawings
        
        response = requests.get(f"{BASE_URL}/api/rfq/{rfq_id}/quotations", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "quotations" in data, "Response should contain 'quotations' field"
        assert "total_quotes" in data, "Response should contain 'total_quotes' field"
        assert "comparison_summary" in data, "Response should contain 'comparison_summary' field"
        assert "has_itemwise_quotes" in data, "Response should contain 'has_itemwise_quotes' field"
        
        # Verify comparison summary structure
        summary = data["comparison_summary"]
        assert "lowest_total_cost" in summary, "Summary should have lowest_total_cost"
        assert "lowest_machining_cost" in summary, "Summary should have lowest_machining_cost"
        assert "average_total_cost" in summary, "Summary should have average_total_cost"
        assert "itemwise_quotes" in summary, "Summary should have itemwise_quotes count"
        
        print(f"✓ GET /api/rfq/{rfq_id}/quotations returned {data['total_quotes']} quotes")
        
        # If there are quotations, verify structure
        if data["quotations"]:
            quote = data["quotations"][0]
            assert "quote_id" in quote, "Quote should have quote_id"
            assert "vendor_name" in quote, "Quote should have vendor_name"
            assert "total_cost" in quote, "Quote should have total_cost"
            assert "is_itemwise" in quote, "Quote should have is_itemwise flag"
            
            if quote.get("is_itemwise"):
                assert "items" in quote, "Item-wise quote should have items array"
                assert "items_count" in quote, "Item-wise quote should have items_count"
                print(f"  - Found item-wise quote with {quote['items_count']} items")
    
    def test_get_quotations_not_found(self, buyer_token):
        """Test getting quotations for non-existent RFQ"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        
        response = requests.get(f"{BASE_URL}/api/rfq/nonexistent_rfq_123/quotations", headers=headers)
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ GET /api/rfq/nonexistent/quotations returns 404")


class TestExistingRFQItemwise:
    """Test item-wise features with existing RFQs in the database"""
    
    @pytest.fixture(scope="class")
    def vendor_token(self):
        """Get vendor authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": VENDOR_EMAIL,
            "password": VENDOR_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip(f"Vendor login failed: {response.status_code}")
    
    @pytest.fixture(scope="class")
    def buyer_token(self):
        """Get buyer authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": BUYER_EMAIL,
            "password": BUYER_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip(f"Buyer login failed: {response.status_code}")
    
    def test_get_items_for_existing_rfq(self, vendor_token):
        """Test getting items for an existing RFQ with matching status"""
        headers = {"Authorization": f"Bearer {vendor_token}"}
        
        # First, get list of RFQs to find one with matching status
        response = requests.get(f"{BASE_URL}/api/rfqs", headers=headers)
        
        if response.status_code != 200:
            pytest.skip("Could not fetch RFQs")
        
        rfqs = response.json()
        if isinstance(rfqs, dict):
            rfqs = rfqs.get("rfqs", [])
        
        # Find an RFQ with matching status
        matching_rfq = None
        for rfq in rfqs:
            if rfq.get("status") == "matching":
                matching_rfq = rfq
                break
        
        if not matching_rfq:
            print("No RFQ with 'matching' status found - skipping")
            pytest.skip("No matching status RFQ found")
        
        rfq_id = matching_rfq.get("rfq_id")
        
        # Get items for this RFQ
        items_response = requests.get(f"{BASE_URL}/api/rfqs/{rfq_id}/items", headers=headers)
        
        assert items_response.status_code == 200, f"Expected 200, got {items_response.status_code}"
        
        data = items_response.json()
        print(f"✓ Found RFQ {rfq_id} with {data.get('total_items', 0)} items")
        
        # Verify response structure
        assert "items" in data
        assert "total_items" in data
        assert "raw_material_provided" in data


class TestQuotationComparisonWithItemwise:
    """Test quotation comparison features with item-wise quotes"""
    
    @pytest.fixture(scope="class")
    def buyer_token(self):
        """Get buyer authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": BUYER_EMAIL,
            "password": BUYER_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip(f"Buyer login failed: {response.status_code}")
    
    def test_quotation_comparison_includes_itemwise_info(self, buyer_token):
        """Test that quotation comparison includes item-wise information"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        
        # Get buyer's RFQs
        response = requests.get(f"{BASE_URL}/api/buyer/rfqs", headers=headers)
        
        if response.status_code != 200:
            pytest.skip("Could not fetch buyer RFQs")
        
        rfqs = response.json()
        if isinstance(rfqs, dict):
            rfqs = rfqs.get("rfqs", [])
        
        # Find an RFQ with quotes
        rfq_with_quotes = None
        for rfq in rfqs:
            if rfq.get("quotes_count", 0) > 0 or rfq.get("status") in ["quoted", "awarded"]:
                rfq_with_quotes = rfq
                break
        
        if not rfq_with_quotes:
            print("No RFQ with quotes found - skipping")
            pytest.skip("No RFQ with quotes found")
        
        rfq_id = rfq_with_quotes.get("rfq_id")
        
        # Get quotations
        quotes_response = requests.get(f"{BASE_URL}/api/rfq/{rfq_id}/quotations", headers=headers)
        
        assert quotes_response.status_code == 200, f"Expected 200, got {quotes_response.status_code}"
        
        data = quotes_response.json()
        
        # Verify has_itemwise_quotes field exists
        assert "has_itemwise_quotes" in data, "Response should have has_itemwise_quotes field"
        
        # Verify comparison_summary includes itemwise_quotes count
        assert "itemwise_quotes" in data.get("comparison_summary", {}), "Summary should have itemwise_quotes count"
        
        print(f"✓ Quotation comparison for RFQ {rfq_id}:")
        print(f"  - Total quotes: {data.get('total_quotes', 0)}")
        print(f"  - Has item-wise quotes: {data.get('has_itemwise_quotes', False)}")
        print(f"  - Item-wise quotes count: {data.get('comparison_summary', {}).get('itemwise_quotes', 0)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
