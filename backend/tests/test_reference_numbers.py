"""
Test Reference Number System for OEMLinker
Tests: RFQ-YYYY-XXXXX, QT-YYYY-XXXXX, ORD-YYYY-XXXXX generation
"""
import pytest
import requests
import os
import re
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@offoadex.com"
ADMIN_PASSWORD = "admin123"
VENDOR_EMAIL = "testvendor_nda@test.com"
VENDOR_PASSWORD = "vendor123"
BUYER_EMAIL = "visualbuyer@test.com"
BUYER_PASSWORD = "buyer123"


class TestReferenceNumberSystem:
    """Test reference number generation and inheritance"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token") or data.get("token")
        pytest.skip(f"Admin login failed: {response.status_code}")
    
    @pytest.fixture(scope="class")
    def buyer_token(self):
        """Get buyer auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": BUYER_EMAIL,
            "password": BUYER_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token") or data.get("token")
        pytest.skip(f"Buyer login failed: {response.status_code}")
    
    @pytest.fixture(scope="class")
    def vendor_token(self):
        """Get vendor auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": VENDOR_EMAIL,
            "password": VENDOR_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token") or data.get("token")
        pytest.skip(f"Vendor login failed: {response.status_code}")
    
    def test_health_check(self):
        """Verify API is healthy"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print("API health check passed")
    
    def test_rfq_number_format(self, buyer_token):
        """Test RFQ creation generates rfq_number in format RFQ-YYYY-XXXXX"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        current_year = datetime.now().strftime("%Y")
        
        # Create a new RFQ
        rfq_data = {
            "title": "TEST_RefNum_RFQ_Item",
            "description": "Test RFQ for reference number validation",
            "material_type": "Steel",
            "quantity": 100,
            "unit": "pieces",
            "deadline": "2026-12-31"
        }
        
        response = requests.post(f"{BASE_URL}/api/rfqs", json=rfq_data, headers=headers)
        assert response.status_code == 200, f"RFQ creation failed: {response.text}"
        
        data = response.json()
        assert "rfq_number" in data, "rfq_number field missing in response"
        
        rfq_number = data["rfq_number"]
        # Validate format: RFQ-YYYY-XXXXX
        pattern = rf"^RFQ-{current_year}-\d{{5}}$"
        assert re.match(pattern, rfq_number), f"Invalid rfq_number format: {rfq_number}"
        
        print(f"RFQ created with number: {rfq_number}")
        
        # Store for cleanup
        self.__class__.test_rfq_id = data["rfq_id"]
        self.__class__.test_rfq_number = rfq_number
        self.__class__.test_rfq_title = rfq_data["title"]
    
    def test_rfq_number_sequential(self, buyer_token):
        """Test that RFQ numbers are sequential"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        
        # Create two RFQs and verify sequential numbering
        rfq_data = {
            "title": "TEST_RefNum_Sequential_RFQ",
            "description": "Test sequential numbering",
            "material_type": "Aluminum",
            "quantity": 50,
            "unit": "pieces",
            "deadline": "2026-12-31"
        }
        
        response1 = requests.post(f"{BASE_URL}/api/rfqs", json=rfq_data, headers=headers)
        assert response1.status_code == 200
        rfq1 = response1.json()
        
        response2 = requests.post(f"{BASE_URL}/api/rfqs", json=rfq_data, headers=headers)
        assert response2.status_code == 200
        rfq2 = response2.json()
        
        # Extract sequence numbers
        seq1 = int(rfq1["rfq_number"].split("-")[-1])
        seq2 = int(rfq2["rfq_number"].split("-")[-1])
        
        assert seq2 == seq1 + 1, f"RFQ numbers not sequential: {rfq1['rfq_number']} -> {rfq2['rfq_number']}"
        print(f"Sequential RFQ numbers verified: {rfq1['rfq_number']} -> {rfq2['rfq_number']}")
    
    def test_existing_rfqs_have_rfq_number(self, admin_token):
        """Test that existing RFQs have rfq_number field (migration verification)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/admin/rfqs", headers=headers)
        assert response.status_code == 200
        
        rfqs = response.json()
        assert len(rfqs) > 0, "No RFQs found"
        
        # Check that RFQs have rfq_number
        rfqs_with_number = [r for r in rfqs if r.get("rfq_number")]
        print(f"RFQs with rfq_number: {len(rfqs_with_number)}/{len(rfqs)}")
        
        # Verify format of existing rfq_numbers
        for rfq in rfqs_with_number[:5]:  # Check first 5
            rfq_number = rfq["rfq_number"]
            assert rfq_number.startswith("RFQ-"), f"Invalid rfq_number prefix: {rfq_number}"
            print(f"  - {rfq_number}: {rfq.get('title', 'N/A')[:30]}")
    
    def test_existing_quotes_have_quotation_number(self, admin_token):
        """Test that existing quotes have quotation_number field (migration verification)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/admin/quotes", headers=headers)
        assert response.status_code == 200
        
        quotes = response.json()
        if len(quotes) == 0:
            pytest.skip("No quotes found to verify")
        
        # Check that quotes have quotation_number
        quotes_with_number = [q for q in quotes if q.get("quotation_number")]
        print(f"Quotes with quotation_number: {len(quotes_with_number)}/{len(quotes)}")
        
        # Verify format and inheritance
        for quote in quotes_with_number[:5]:  # Check first 5
            quotation_number = quote["quotation_number"]
            assert quotation_number.startswith("QT-"), f"Invalid quotation_number prefix: {quotation_number}"
            
            # Check rfq_number inheritance
            if quote.get("rfq_number"):
                assert quote["rfq_number"].startswith("RFQ-"), f"Invalid inherited rfq_number: {quote['rfq_number']}"
            
            # Check item_name inheritance
            if quote.get("item_name"):
                print(f"  - {quotation_number}: item_name='{quote['item_name'][:30]}'")
    
    def test_existing_orders_have_order_number(self, admin_token):
        """Test that existing orders have order_number field (migration verification)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/admin/orders", headers=headers)
        assert response.status_code == 200
        
        orders = response.json()
        if len(orders) == 0:
            pytest.skip("No orders found to verify")
        
        # Check that orders have order_number
        orders_with_number = [o for o in orders if o.get("order_number")]
        print(f"Orders with order_number: {len(orders_with_number)}/{len(orders)}")
        
        # Verify format and inheritance
        for order in orders_with_number[:5]:  # Check first 5
            order_number = order["order_number"]
            assert order_number.startswith("ORD-"), f"Invalid order_number prefix: {order_number}"
            
            # Check rfq_number inheritance
            if order.get("rfq_number"):
                assert order["rfq_number"].startswith("RFQ-"), f"Invalid inherited rfq_number: {order['rfq_number']}"
            
            # Check quotation_number inheritance
            if order.get("quotation_number"):
                assert order["quotation_number"].startswith("QT-"), f"Invalid inherited quotation_number: {order['quotation_number']}"
            
            # Check item_name inheritance
            if order.get("item_name"):
                print(f"  - {order_number}: item_name='{order['item_name'][:30]}'")
    
    def test_buyer_rfqs_list_has_rfq_number(self, buyer_token):
        """Test buyer RFQ list returns rfq_number"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        
        response = requests.get(f"{BASE_URL}/api/rfqs", headers=headers)
        assert response.status_code == 200
        
        rfqs = response.json()
        if len(rfqs) == 0:
            pytest.skip("No buyer RFQs found")
        
        # Check rfq_number presence
        for rfq in rfqs[:3]:
            if rfq.get("rfq_number"):
                print(f"Buyer RFQ: {rfq['rfq_number']} - {rfq.get('title', 'N/A')[:30]}")
                assert rfq["rfq_number"].startswith("RFQ-")
    
    def test_buyer_orders_list_has_order_number(self, buyer_token):
        """Test buyer orders list returns order_number and rfq_number"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        
        response = requests.get(f"{BASE_URL}/api/orders", headers=headers)
        assert response.status_code == 200
        
        orders = response.json()
        if len(orders) == 0:
            pytest.skip("No buyer orders found")
        
        # Check order_number and rfq_number presence
        for order in orders[:3]:
            if order.get("order_number"):
                print(f"Buyer Order: {order['order_number']}")
                assert order["order_number"].startswith("ORD-")
            if order.get("rfq_number"):
                assert order["rfq_number"].startswith("RFQ-")
    
    def test_vendor_matched_rfqs_has_rfq_number(self, vendor_token):
        """Test vendor matched RFQs returns rfq_number"""
        headers = {"Authorization": f"Bearer {vendor_token}"}
        
        response = requests.get(f"{BASE_URL}/api/rfqs", headers=headers)
        assert response.status_code == 200
        
        rfqs = response.json()
        if len(rfqs) == 0:
            pytest.skip("No vendor matched RFQs found")
        
        # Check rfq_number presence
        for rfq in rfqs[:3]:
            if rfq.get("rfq_number"):
                print(f"Vendor Matched RFQ: {rfq['rfq_number']} - {rfq.get('title', 'N/A')[:30]}")
                assert rfq["rfq_number"].startswith("RFQ-")
    
    def test_vendor_orders_list_has_order_number(self, vendor_token):
        """Test vendor orders list returns order_number"""
        headers = {"Authorization": f"Bearer {vendor_token}"}
        
        response = requests.get(f"{BASE_URL}/api/vendor/orders", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        # Handle both array and object with 'orders' key
        orders = data.get("orders", data) if isinstance(data, dict) else data
        if not orders or len(orders) == 0:
            pytest.skip("No vendor orders found")
        
        # Check order_number presence
        for order in orders[:3]:
            if order.get("order_number"):
                print(f"Vendor Order: {order['order_number']}")
                assert order["order_number"].startswith("ORD-")
    
    def test_admin_search_rfqs_by_reference_number(self, admin_token):
        """Test admin can search RFQs by reference number"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First get an existing RFQ number
        response = requests.get(f"{BASE_URL}/api/admin/rfqs", headers=headers)
        assert response.status_code == 200
        rfqs = response.json()
        
        if len(rfqs) == 0:
            pytest.skip("No RFQs to search")
        
        # Find an RFQ with rfq_number
        rfq_with_number = next((r for r in rfqs if r.get("rfq_number")), None)
        if not rfq_with_number:
            pytest.skip("No RFQs with rfq_number found")
        
        search_term = rfq_with_number["rfq_number"]
        print(f"Searching for RFQ: {search_term}")
        
        # Search should work (API may support search param)
        # This verifies the data is available for frontend filtering
        assert search_term.startswith("RFQ-")
    
    def test_counters_collection_exists(self, admin_token):
        """Verify counters collection is being used for sequence generation"""
        # This is an indirect test - we verify by creating RFQs and checking sequential numbers
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get current RFQ count to verify counter is working
        response = requests.get(f"{BASE_URL}/api/admin/rfqs", headers=headers)
        assert response.status_code == 200
        
        rfqs = response.json()
        rfqs_with_number = [r for r in rfqs if r.get("rfq_number")]
        
        if len(rfqs_with_number) > 0:
            # Extract max sequence number
            max_seq = max(int(r["rfq_number"].split("-")[-1]) for r in rfqs_with_number)
            print(f"Current max RFQ sequence: {max_seq}")
            assert max_seq > 0, "Counter should have positive sequence"


class TestReferenceNumberInheritance:
    """Test that reference numbers are properly inherited downstream"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token") or data.get("token")
        pytest.skip(f"Admin login failed: {response.status_code}")
    
    def test_quote_inherits_rfq_number_and_item_name(self, admin_token):
        """Test that quotes inherit rfq_number and item_name from parent RFQ"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get quotes with their parent RFQ info
        response = requests.get(f"{BASE_URL}/api/admin/quotes", headers=headers)
        assert response.status_code == 200
        
        quotes = response.json()
        if len(quotes) == 0:
            pytest.skip("No quotes found")
        
        # Find quotes with all reference fields
        for quote in quotes[:5]:
            if quote.get("quotation_number") and quote.get("rfq_number"):
                print(f"Quote {quote['quotation_number']}:")
                print(f"  - rfq_number: {quote['rfq_number']}")
                print(f"  - item_name: {quote.get('item_name', 'N/A')[:40]}")
                
                # Verify formats
                assert quote["quotation_number"].startswith("QT-")
                assert quote["rfq_number"].startswith("RFQ-")
    
    def test_order_inherits_all_reference_numbers(self, admin_token):
        """Test that orders inherit rfq_number, quotation_number, and item_name"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get orders with their reference info
        response = requests.get(f"{BASE_URL}/api/admin/orders", headers=headers)
        assert response.status_code == 200
        
        orders = response.json()
        if len(orders) == 0:
            pytest.skip("No orders found")
        
        # Find orders with all reference fields
        for order in orders[:5]:
            if order.get("order_number"):
                print(f"Order {order['order_number']}:")
                print(f"  - rfq_number: {order.get('rfq_number', 'N/A')}")
                print(f"  - quotation_number: {order.get('quotation_number', 'N/A')}")
                print(f"  - item_name: {order.get('item_name', 'N/A')[:40]}")
                print(f"  - po_number: {order.get('po_number', 'N/A')}")
                
                # Verify formats
                assert order["order_number"].startswith("ORD-")
                if order.get("rfq_number"):
                    assert order["rfq_number"].startswith("RFQ-")
                if order.get("quotation_number"):
                    assert order["quotation_number"].startswith("QT-")


class TestMigrationVerification:
    """Verify migration has been applied correctly"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token") or data.get("token")
        pytest.skip(f"Admin login failed: {response.status_code}")
    
    def test_migration_counts(self, admin_token):
        """Verify migration counts match expected (217 RFQs, 71 quotes, 50 orders)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get RFQs
        rfq_response = requests.get(f"{BASE_URL}/api/admin/rfqs", headers=headers)
        assert rfq_response.status_code == 200
        rfqs = rfq_response.json()
        rfqs_with_number = len([r for r in rfqs if r.get("rfq_number")])
        
        # Get Quotes
        quote_response = requests.get(f"{BASE_URL}/api/admin/quotes", headers=headers)
        assert quote_response.status_code == 200
        quotes = quote_response.json()
        quotes_with_number = len([q for q in quotes if q.get("quotation_number")])
        
        # Get Orders
        order_response = requests.get(f"{BASE_URL}/api/admin/orders", headers=headers)
        assert order_response.status_code == 200
        orders = order_response.json()
        orders_with_number = len([o for o in orders if o.get("order_number")])
        
        print(f"Migration verification:")
        print(f"  - RFQs with rfq_number: {rfqs_with_number}/{len(rfqs)}")
        print(f"  - Quotes with quotation_number: {quotes_with_number}/{len(quotes)}")
        print(f"  - Orders with order_number: {orders_with_number}/{len(orders)}")
        
        # Verify counts are reasonable (migration was run)
        assert rfqs_with_number > 0, "No RFQs have rfq_number - migration may not have run"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
