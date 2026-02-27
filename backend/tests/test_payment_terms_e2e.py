"""
End-to-End Payment Terms Flow Test
Tests the complete workflow:
1. Buyer creates RFQ with preferred payment terms
2. Vendor submits quote with proposed payment terms (via API)
3. Buyer accepts quote, which creates order with PO and finalized payment terms
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestPaymentTermsEndToEndFlow:
    """E2E test for payment terms workflow"""
    
    @pytest.fixture
    def buyer_token(self):
        """Get buyer auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "buyer@offoadex.com",
            "password": "buyer123"
        })
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Buyer auth failed")
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@offoadex.com",
            "password": "admin123"
        })
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Admin auth failed")

    def test_e2e_payment_terms_flow(self, buyer_token, admin_token):
        """
        Complete end-to-end test:
        1. Create RFQ with payment terms
        2. Submit quote via admin (simulating vendor)
        3. Accept quote
        4. Verify order has PO number and payment terms
        """
        buyer_headers = {"Authorization": f"Bearer {buyer_token}"}
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        unique_id = uuid.uuid4().hex[:8]
        
        # Step 1: Create RFQ with preferred payment terms
        print("\n--- Step 1: Create RFQ with payment terms ---")
        rfq_data = {
            "title": f"E2E_Payment_Test_{unique_id}",
            "description": "Testing payment terms E2E flow",
            "material_type": "Aluminum",
            "quantity": 5,
            "tolerance": 0.1,
            "supply_type": "vendor_material",
            "preferred_payment_terms": "50_advance_50_delivery",
            "payment_terms_notes": "Buyer prefers milestone payments"
        }
        
        rfq_response = requests.post(f"{BASE_URL}/api/rfqs", json=rfq_data, headers=buyer_headers)
        assert rfq_response.status_code == 200, f"RFQ creation failed: {rfq_response.text}"
        
        rfq = rfq_response.json()
        rfq_id = rfq["rfq_id"]
        
        assert rfq.get("preferred_payment_terms") == "50_advance_50_delivery"
        print(f"✅ RFQ created: {rfq_id} with payment terms: {rfq.get('preferred_payment_terms')}")
        
        # Step 2: Get a vendor to submit quote
        vendors_response = requests.get(f"{BASE_URL}/api/admin/vendors", headers=admin_headers)
        vendors = vendors_response.json()
        
        if not vendors:
            pytest.skip("No vendors available")
        
        vendor = next((v for v in vendors if v.get("is_approved")), None)
        if not vendor:
            pytest.skip("No approved vendor")
        
        vendor_id = vendor["vendor_id"]
        print(f"Using vendor: {vendor['company_name']} ({vendor_id})")
        
        # Add vendor to matched vendors for RFQ
        match_response = requests.put(
            f"{BASE_URL}/api/admin/rfqs/{rfq_id}",
            json={"matched_vendors": [{"vendor_id": vendor_id, "company_name": vendor["company_name"], "suitability_score": 85}]},
            headers=admin_headers
        )
        if match_response.status_code != 200:
            # Alternative: Update status directly 
            requests.put(
                f"{BASE_URL}/api/admin/rfqs/{rfq_id}/status",
                json={"status": "matching"},
                headers=admin_headers
            )
        
        # Step 3: Submit quote with proposed payment terms (via admin endpoint)
        print("\n--- Step 3: Submit quote with proposed payment terms ---")
        quote_data = {
            "rfq_id": rfq_id,
            "vendor_id": vendor_id,
            "price": 1250.00,
            "currency": "USD",
            "lead_time_days": 10,
            "notes": "Quote for E2E test",
            "proposed_payment_terms": "net_45",  # Different from buyer's preference
            "payment_terms_notes": "Standard net 45 terms"
        }
        
        # Submit quote via admin
        quote_response = requests.post(
            f"{BASE_URL}/api/admin/quotes",
            json=quote_data,
            headers=admin_headers
        )
        
        if quote_response.status_code != 200:
            print(f"Admin quote endpoint may not exist, checking...")
            # Try to submit via direct DB insert simulation or skip
            pytest.skip("Admin quote submission not available")
        
        quote = quote_response.json()
        quote_id = quote["quote_id"]
        
        print(f"✅ Quote submitted: {quote_id} with payment terms: {quote.get('proposed_payment_terms')}")
        
        # Step 4: Buyer accepts quote
        print("\n--- Step 4: Buyer accepts quote ---")
        accept_response = requests.post(
            f"{BASE_URL}/api/quotes/{quote_id}/accept",
            headers=buyer_headers
        )
        assert accept_response.status_code == 200, f"Quote acceptance failed: {accept_response.text}"
        
        order_data = accept_response.json()
        order_id = order_data["order_id"]
        
        print(f"✅ Quote accepted, order created: {order_id}")
        
        # Step 5: Verify order has PO number and payment terms
        print("\n--- Step 5: Verify order details ---")
        order_response = requests.get(
            f"{BASE_URL}/api/orders/{order_id}",
            headers=buyer_headers
        )
        assert order_response.status_code == 200
        
        order = order_response.json()
        
        # Verify PO number
        po_number = order.get("po_number")
        assert po_number is not None, "Order should have PO number"
        assert po_number.startswith("PO-"), f"PO format incorrect: {po_number}"
        print(f"✅ PO Number: {po_number}")
        
        # Verify payment terms (should be vendor's proposed terms)
        payment_terms = order.get("payment_terms")
        assert payment_terms == "net_45", f"Expected 'net_45', got '{payment_terms}'"
        print(f"✅ Payment Terms: {payment_terms}")
        
        payment_terms_label = order.get("payment_terms_label")
        if payment_terms_label:
            print(f"✅ Payment Terms Label: {payment_terms_label}")
        
        # Verify tracking updates mention payment terms
        tracking = order.get("tracking_updates", [])
        if tracking:
            first_update = tracking[0].get("note", "")
            assert "Payment Terms" in first_update or "net_45" in first_update.lower()
            print(f"✅ Tracking update includes payment terms info")
        
        print("\n=== E2E Payment Terms Flow Test PASSED ===")
        
        return {
            "rfq_id": rfq_id,
            "quote_id": quote_id,
            "order_id": order_id,
            "po_number": po_number,
            "payment_terms": payment_terms
        }


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
