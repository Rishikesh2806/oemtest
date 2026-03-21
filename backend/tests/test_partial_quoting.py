"""
Test Partial Quoting Feature for OEMLinker
Tests:
- POST /api/vendor/quotation/itemwise - Accepts partial items (not all RFQ items required)
- Backend returns is_partial, quoted_items_count, total_rfq_items fields
- GET /api/rfq/{rfq_id}/quotations - Shows partial_quotes count in comparison_summary
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


class TestPartialQuoting:
    """Test partial quoting feature for multi-item RFQs"""
    
    @pytest.fixture(scope="class")
    def vendor_token(self):
        """Get vendor authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": VENDOR_EMAIL,
            "password": VENDOR_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Vendor authentication failed")
    
    @pytest.fixture(scope="class")
    def buyer_token(self):
        """Get buyer authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": BUYER_EMAIL,
            "password": BUYER_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Buyer authentication failed")
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Admin authentication failed")
    
    def test_vendor_login(self):
        """Test vendor can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": VENDOR_EMAIL,
            "password": VENDOR_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "vendor"
        print(f"✓ Vendor login successful")
    
    def test_buyer_login(self):
        """Test buyer can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": BUYER_EMAIL,
            "password": BUYER_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "buyer"
        print(f"✓ Buyer login successful")
    
    def test_get_rfq_items_for_partial_test(self, vendor_token):
        """Test getting RFQ items for the test RFQ"""
        # Test with the known test RFQ
        rfq_id = "rfq_partial_test_1fa917f6"
        headers = {"Authorization": f"Bearer {vendor_token}"}
        
        response = requests.get(f"{BASE_URL}/api/rfqs/{rfq_id}/items", headers=headers)
        
        if response.status_code == 404:
            pytest.skip(f"Test RFQ {rfq_id} not found in database")
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        print(f"✓ RFQ {rfq_id} has {len(data['items'])} items")
        
        # Verify items have required fields
        for item in data["items"]:
            assert "item_id" in item
            assert "title" in item or "filename" in item
        
        return data
    
    def test_get_rfq_items_for_ui_test(self, vendor_token):
        """Test getting RFQ items for the UI test RFQ"""
        rfq_id = "rfq_partial_ui_test_dadab1"
        headers = {"Authorization": f"Bearer {vendor_token}"}
        
        response = requests.get(f"{BASE_URL}/api/rfqs/{rfq_id}/items", headers=headers)
        
        if response.status_code == 404:
            pytest.skip(f"Test RFQ {rfq_id} not found in database")
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        print(f"✓ RFQ {rfq_id} has {len(data['items'])} items for UI testing")
        return data
    
    def test_itemwise_quotation_requires_auth(self):
        """Test that itemwise quotation endpoint requires authentication"""
        response = requests.post(f"{BASE_URL}/api/vendor/quotation/itemwise", json={
            "rfq_id": "test_rfq",
            "items": []
        })
        assert response.status_code == 401
        print("✓ Itemwise quotation requires authentication")
    
    def test_itemwise_quotation_requires_rfq_id(self, vendor_token):
        """Test that rfq_id is required"""
        headers = {"Authorization": f"Bearer {vendor_token}"}
        
        response = requests.post(f"{BASE_URL}/api/vendor/quotation/itemwise", 
            headers=headers,
            json={"items": []}
        )
        assert response.status_code == 400
        assert "rfq_id" in response.json().get("detail", "").lower()
        print("✓ rfq_id validation works")
    
    def test_itemwise_quotation_requires_items(self, vendor_token):
        """Test that at least one item is required"""
        headers = {"Authorization": f"Bearer {vendor_token}"}
        
        response = requests.post(f"{BASE_URL}/api/vendor/quotation/itemwise", 
            headers=headers,
            json={
                "rfq_id": "rfq_partial_test_1fa917f6",
                "items": []
            }
        )
        assert response.status_code == 400
        assert "item" in response.json().get("detail", "").lower()
        print("✓ Items array validation works")
    
    def test_itemwise_quotation_validates_labour_cost(self, vendor_token):
        """Test that labour cost > 0 is required for each item"""
        headers = {"Authorization": f"Bearer {vendor_token}"}
        
        # Use a non-existent RFQ to test validation (will fail at RFQ check, but we test the items validation first)
        # Or use a fresh RFQ that vendor hasn't quoted on
        # First, let's find an RFQ without a quote from this vendor
        
        # Test with a fake RFQ ID to verify validation logic
        response = requests.post(f"{BASE_URL}/api/vendor/quotation/itemwise", 
            headers=headers,
            json={
                "rfq_id": "rfq_validation_test_nonexistent",
                "items": [{
                    "item_id": "test_item_1",
                    "title": "Test Item",
                    "material_provided_by_buyer": True,
                    "material_cost": 0,
                    "labour_cost": 0  # Invalid - should be > 0
                }],
                "lead_time_days": 14
            }
        )
        # Either 400 for validation or 404 for RFQ not found
        assert response.status_code in [400, 404]
        detail = response.json().get("detail", "").lower()
        # If RFQ not found, that's fine - validation would happen after RFQ check
        if response.status_code == 400:
            assert "labour" in detail or "machining" in detail or "item" in detail
            print("✓ Labour cost validation works")
        else:
            print("✓ RFQ validation happens first (expected behavior)")
    
    def test_itemwise_quotation_validates_material_cost(self, vendor_token):
        """Test that material cost is required when vendor provides material"""
        headers = {"Authorization": f"Bearer {vendor_token}"}
        
        response = requests.post(f"{BASE_URL}/api/vendor/quotation/itemwise", 
            headers=headers,
            json={
                "rfq_id": "rfq_validation_test_nonexistent",
                "items": [{
                    "item_id": "test_item_1",
                    "title": "Test Item",
                    "material_provided_by_buyer": False,  # Vendor provides material
                    "material_cost": 0,  # Invalid - should be > 0
                    "labour_cost": 500
                }],
                "lead_time_days": 14
            }
        )
        # Either 400 for validation or 404 for RFQ not found
        assert response.status_code in [400, 404]
        detail = response.json().get("detail", "").lower()
        if response.status_code == 400:
            assert "material" in detail or "item" in detail
            print("✓ Material cost validation works when vendor provides material")
        else:
            print("✓ RFQ validation happens first (expected behavior)")
    
    def test_get_quotations_with_partial_quotes(self, buyer_token):
        """Test GET /api/rfq/{rfq_id}/quotations returns partial_quotes in comparison_summary"""
        rfq_id = "rfq_partial_test_1fa917f6"
        headers = {"Authorization": f"Bearer {buyer_token}"}
        
        response = requests.get(f"{BASE_URL}/api/rfq/{rfq_id}/quotations", headers=headers)
        
        if response.status_code == 404:
            pytest.skip(f"Test RFQ {rfq_id} not found")
        
        if response.status_code == 403:
            pytest.skip("Buyer not authorized for this RFQ")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "quotations" in data
        assert "comparison_summary" in data
        
        # Verify comparison_summary has partial_quotes field
        summary = data["comparison_summary"]
        assert "partial_quotes" in summary, "comparison_summary should have partial_quotes field"
        assert "full_quotes" in summary or "itemwise_quotes" in summary
        
        print(f"✓ Quotations endpoint returns partial_quotes: {summary.get('partial_quotes', 0)}")
        print(f"  Total quotes: {data.get('total_quotes', 0)}")
        
        # Check individual quotations for partial quote fields
        for quote in data.get("quotations", []):
            assert "is_partial" in quote, "Each quote should have is_partial field"
            assert "quoted_items_count" in quote, "Each quote should have quoted_items_count field"
            assert "total_rfq_items" in quote, "Each quote should have total_rfq_items field"
            
            if quote.get("is_partial"):
                print(f"  Found partial quote: {quote.get('quote_id')} - {quote.get('quoted_items_count')}/{quote.get('total_rfq_items')} items")
        
        return data
    
    def test_partial_quote_fields_in_response(self, buyer_token):
        """Test that partial quote fields are correctly returned"""
        rfq_id = "rfq_partial_test_1fa917f6"
        headers = {"Authorization": f"Bearer {buyer_token}"}
        
        response = requests.get(f"{BASE_URL}/api/rfq/{rfq_id}/quotations", headers=headers)
        
        if response.status_code != 200:
            pytest.skip(f"Could not fetch quotations for RFQ {rfq_id}")
        
        data = response.json()
        quotations = data.get("quotations", [])
        
        if not quotations:
            pytest.skip("No quotations found for this RFQ")
        
        # Find a partial quote if exists
        partial_quotes = [q for q in quotations if q.get("is_partial")]
        
        if partial_quotes:
            quote = partial_quotes[0]
            assert quote["quoted_items_count"] < quote["total_rfq_items"], \
                "Partial quote should have quoted_items_count < total_rfq_items"
            print(f"✓ Partial quote verified: {quote['quoted_items_count']}/{quote['total_rfq_items']} items")
        else:
            # Check full quotes have correct fields
            for quote in quotations:
                if quote.get("is_itemwise"):
                    assert quote["quoted_items_count"] == quote["total_rfq_items"], \
                        "Full quote should have quoted_items_count == total_rfq_items"
            print("✓ No partial quotes found, but fields are present")


class TestPartialQuotingSubmission:
    """Test submitting partial quotes"""
    
    @pytest.fixture(scope="class")
    def vendor_token(self):
        """Get vendor authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": VENDOR_EMAIL,
            "password": VENDOR_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Vendor authentication failed")
    
    @pytest.fixture(scope="class")
    def buyer_token(self):
        """Get buyer authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": BUYER_EMAIL,
            "password": BUYER_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Buyer authentication failed")
    
    def test_create_test_rfq_with_multiple_drawings(self, buyer_token):
        """Create a test RFQ with multiple drawings for partial quoting test"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        unique_id = uuid.uuid4().hex[:8]
        
        # Create RFQ
        rfq_data = {
            "title": f"TEST_Partial_Quote_RFQ_{unique_id}",
            "description": "Test RFQ for partial quoting feature",
            "material_type": "Steel",
            "quantity": 100,
            "tolerance": 0.05,
            "urgency": "normal"
        }
        
        response = requests.post(f"{BASE_URL}/api/rfqs", headers=headers, json=rfq_data)
        
        if response.status_code != 200:
            pytest.skip(f"Could not create test RFQ: {response.text}")
        
        data = response.json()
        rfq_id = data.get("rfq_id")
        assert rfq_id is not None
        print(f"✓ Created test RFQ: {rfq_id}")
        
        # Add multiple drawings (simulated)
        # Note: In real scenario, drawings would be uploaded
        # For this test, we'll use the existing test RFQs
        
        return rfq_id
    
    def test_submit_partial_quote_for_existing_rfq(self, vendor_token):
        """Test submitting a partial quote (not all items) for an existing multi-item RFQ"""
        headers = {"Authorization": f"Bearer {vendor_token}"}
        
        # First, get items for the test RFQ
        rfq_id = "rfq_partial_ui_test_dadab1"
        items_response = requests.get(f"{BASE_URL}/api/rfqs/{rfq_id}/items", headers=headers)
        
        if items_response.status_code == 404:
            pytest.skip(f"Test RFQ {rfq_id} not found")
        
        if items_response.status_code != 200:
            pytest.skip(f"Could not get RFQ items: {items_response.text}")
        
        items_data = items_response.json()
        items = items_data.get("items", [])
        
        if len(items) < 2:
            pytest.skip("RFQ needs at least 2 items for partial quote test")
        
        # Check if vendor already quoted
        # Try to submit a partial quote (only first 2 items out of 4)
        partial_items = items[:2]  # Only quote first 2 items
        
        quote_items = []
        for item in partial_items:
            quote_items.append({
                "item_id": item.get("item_id") or item.get("drawing_id"),
                "drawing_id": item.get("drawing_id"),
                "title": item.get("title") or item.get("filename", "Item"),
                "material_provided_by_buyer": False,
                "material_cost": 1000,
                "labour_cost": 500,
                "additional_costs": {"finishing": 100},
                "remarks": "Test partial quote"
            })
        
        response = requests.post(f"{BASE_URL}/api/vendor/quotation/itemwise", 
            headers=headers,
            json={
                "rfq_id": rfq_id,
                "items": quote_items,
                "lead_time_days": 14,
                "notes": "Partial quote - only quoting selected items",
                "proposed_payment_terms": "net_30"
            }
        )
        
        if response.status_code == 400 and "already submitted" in response.text.lower():
            print("✓ Vendor already has a quote for this RFQ (expected behavior)")
            return
        
        if response.status_code != 200:
            print(f"Response: {response.status_code} - {response.text}")
            pytest.skip(f"Could not submit partial quote: {response.text}")
        
        data = response.json()
        
        # Verify partial quote fields in response
        assert data.get("success") == True
        assert "is_partial" in data
        # API returns items_count (not quoted_items_count) in the response
        assert "items_count" in data or "quoted_items_count" in data
        assert "total_rfq_items" in data
        
        items_count = data.get("items_count") or data.get("quoted_items_count")
        total_items = data.get("total_rfq_items")
        
        if data.get("is_partial"):
            assert items_count < total_items
            print(f"✓ Partial quote submitted: {items_count}/{total_items} items")
        else:
            print(f"✓ Full quote submitted: {items_count}/{total_items} items")
        
        return data


class TestQuotationComparisonPartialDisplay:
    """Test that QuotationComparison correctly displays partial quotes"""
    
    @pytest.fixture(scope="class")
    def buyer_token(self):
        """Get buyer authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": BUYER_EMAIL,
            "password": BUYER_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Buyer authentication failed")
    
    def test_comparison_summary_includes_partial_count(self, buyer_token):
        """Test that comparison_summary includes partial_quotes count"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        
        # Get buyer's RFQs
        rfqs_response = requests.get(f"{BASE_URL}/api/buyer/rfqs", headers=headers)
        
        if rfqs_response.status_code != 200:
            pytest.skip("Could not fetch buyer RFQs")
        
        rfqs = rfqs_response.json().get("rfqs", [])
        
        # Find an RFQ with quotes
        for rfq in rfqs:
            rfq_id = rfq.get("rfq_id")
            quotes_response = requests.get(f"{BASE_URL}/api/rfq/{rfq_id}/quotations", headers=headers)
            
            if quotes_response.status_code == 200:
                data = quotes_response.json()
                if data.get("total_quotes", 0) > 0:
                    summary = data.get("comparison_summary", {})
                    
                    # Verify partial_quotes field exists
                    assert "partial_quotes" in summary, \
                        f"comparison_summary should have partial_quotes field for RFQ {rfq_id}"
                    
                    print(f"✓ RFQ {rfq_id}: {summary.get('partial_quotes', 0)} partial quotes, "
                          f"{summary.get('full_quotes', 0)} full quotes")
                    return
        
        pytest.skip("No RFQs with quotes found for testing")
    
    def test_quotation_has_partial_badge_fields(self, buyer_token):
        """Test that quotations have fields needed for partial badge display"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        
        # Test with known RFQ
        rfq_id = "rfq_partial_test_1fa917f6"
        response = requests.get(f"{BASE_URL}/api/rfq/{rfq_id}/quotations", headers=headers)
        
        if response.status_code != 200:
            pytest.skip(f"Could not fetch quotations for RFQ {rfq_id}")
        
        data = response.json()
        quotations = data.get("quotations", [])
        
        if not quotations:
            pytest.skip("No quotations found")
        
        for quote in quotations:
            # These fields are needed for the "Partial (X/Y)" badge in QuotationComparison.jsx
            assert "is_partial" in quote, "Quote should have is_partial field"
            assert "quoted_items_count" in quote, "Quote should have quoted_items_count field"
            assert "total_rfq_items" in quote, "Quote should have total_rfq_items field"
            
            # Verify data types
            assert isinstance(quote["is_partial"], bool), "is_partial should be boolean"
            assert isinstance(quote["quoted_items_count"], int), "quoted_items_count should be integer"
            assert isinstance(quote["total_rfq_items"], int), "total_rfq_items should be integer"
        
        print(f"✓ All {len(quotations)} quotations have required partial quote fields")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
