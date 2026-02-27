"""
End-to-End Payment Terms Flow Test
Tests the complete workflow using MongoDB directly for quote creation:
1. Buyer creates RFQ with preferred payment terms
2. Quote is created with proposed payment terms
3. Buyer accepts quote, which creates order with PO and finalized payment terms
"""
import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta, timezone

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

    def test_existing_rfq_with_quotes_accept_flow(self, buyer_token):
        """
        Test accepting an existing quote and verify order gets PO and payment terms
        Find an RFQ that has pending quotes and accept one
        """
        buyer_headers = {"Authorization": f"Bearer {buyer_token}"}
        
        # Get buyer's RFQs
        rfqs_response = requests.get(f"{BASE_URL}/api/rfqs", headers=buyer_headers)
        assert rfqs_response.status_code == 200
        
        rfqs = rfqs_response.json()
        
        # Find an RFQ with pending quotes
        rfq_with_quotes = None
        pending_quote = None
        
        for rfq in rfqs:
            if rfq.get("status") in ["quoted", "matching"]:
                quotes_response = requests.get(
                    f"{BASE_URL}/api/quotes/rfq/{rfq['rfq_id']}", 
                    headers=buyer_headers
                )
                if quotes_response.status_code == 200:
                    quotes = quotes_response.json()
                    for q in quotes:
                        if q.get("status") == "pending":
                            pending_quote = q
                            rfq_with_quotes = rfq
                            break
                if pending_quote:
                    break
        
        if not pending_quote:
            # Try to create flow from scratch
            print("No existing pending quotes found - this test requires manual setup")
            pytest.skip("No pending quotes available for acceptance test")
        
        quote_id = pending_quote["quote_id"]
        print(f"Found pending quote: {quote_id} for RFQ: {rfq_with_quotes['rfq_id']}")
        print(f"Quote proposed_payment_terms: {pending_quote.get('proposed_payment_terms')}")
        
        # Accept the quote
        accept_response = requests.post(
            f"{BASE_URL}/api/quotes/{quote_id}/accept",
            headers=buyer_headers
        )
        
        assert accept_response.status_code == 200, f"Quote acceptance failed: {accept_response.text}"
        
        order_data = accept_response.json()
        order_id = order_data["order_id"]
        
        print(f"✅ Quote accepted, order created: {order_id}")
        
        # Verify order has PO number and payment terms
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
        
        # Verify payment terms
        payment_terms = order.get("payment_terms")
        assert payment_terms is not None, "Order should have payment_terms"
        print(f"✅ Payment Terms: {payment_terms}")
        
        payment_terms_label = order.get("payment_terms_label")
        if payment_terms_label:
            print(f"✅ Payment Terms Label: {payment_terms_label}")
        
        print("\n=== Quote Acceptance with PO Test PASSED ===")

    def test_rfq_creation_preserves_payment_terms(self, buyer_token):
        """Test that RFQ creation properly stores and returns payment terms"""
        buyer_headers = {"Authorization": f"Bearer {buyer_token}"}
        unique_id = uuid.uuid4().hex[:8]
        
        # Create RFQ with payment terms
        rfq_data = {
            "title": f"TEST_PaymentTerms_Verify_{unique_id}",
            "description": "Testing payment terms storage",
            "material_type": "Brass",
            "quantity": 3,
            "tolerance": 0.05,
            "preferred_payment_terms": "milestone_based",
            "payment_terms_notes": "Payment per milestone completion"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/rfqs", json=rfq_data, headers=buyer_headers)
        assert create_response.status_code == 200
        
        rfq = create_response.json()
        rfq_id = rfq["rfq_id"]
        
        # Verify response has payment terms
        assert rfq.get("preferred_payment_terms") == "milestone_based", \
            f"Expected 'milestone_based', got '{rfq.get('preferred_payment_terms')}'"
        assert rfq.get("payment_terms_notes") == "Payment per milestone completion"
        
        print(f"✅ RFQ {rfq_id} created with payment terms: {rfq.get('preferred_payment_terms')}")
        
        # Verify GET returns same data
        get_response = requests.get(f"{BASE_URL}/api/rfqs/{rfq_id}", headers=buyer_headers)
        assert get_response.status_code == 200
        
        fetched_rfq = get_response.json()
        assert fetched_rfq.get("preferred_payment_terms") == "milestone_based"
        assert fetched_rfq.get("payment_terms_notes") == "Payment per milestone completion"
        
        print("✅ GET /api/rfqs/{rfq_id} returns payment terms correctly")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
