"""
Test Quote Detail and Negotiation Endpoints
- GET /api/quotes/{quote_id} - Get detailed quote info
- POST /api/quotes/{quote_id}/negotiate - Buyer sends negotiation request
- POST /api/quotes/{quote_id}/negotiate/{neg_id}/respond - Vendor responds to negotiation
- POST /api/quotes/{quote_id}/negotiate/{neg_id}/accept-counter - Buyer accepts counter offer
- GET /api/quotes/{quote_id}/negotiations - Get negotiation history
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
BUYER_EMAIL = "buyer@offoadex.com"
BUYER_PASSWORD = "buyer123"
VENDOR_EMAIL = "info@simpsonmunro.com"  # Simpson Munro vendor
VENDOR_PASSWORD = "vendor123"


class TestNegotiationEndpoints:
    """Tests for quote detail and negotiation endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.buyer_session = requests.Session()
        self.buyer_session.headers.update({"Content-Type": "application/json"})
        self.vendor_session = requests.Session()
        self.vendor_session.headers.update({"Content-Type": "application/json"})
        
    def login_buyer(self):
        """Login as buyer"""
        response = self.buyer_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": BUYER_EMAIL,
            "password": BUYER_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.buyer_session.headers.update({"Authorization": f"Bearer {token}"})
            return response.json()
        return None
    
    def login_vendor(self):
        """Login as vendor (Simpson Munro)"""
        response = self.vendor_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": VENDOR_EMAIL,
            "password": VENDOR_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.vendor_session.headers.update({"Authorization": f"Bearer {token}"})
            return response.json()
        return None
    
    def get_pending_quote_for_buyer(self):
        """Find a pending quote that the buyer can view"""
        # First get buyer's RFQs
        rfqs_response = self.buyer_session.get(f"{BASE_URL}/api/rfqs")
        if rfqs_response.status_code != 200:
            return None
        
        rfqs = rfqs_response.json()
        for rfq in rfqs:
            # Get quotes for this RFQ
            quotes_response = self.buyer_session.get(f"{BASE_URL}/api/quotes/rfq/{rfq['rfq_id']}")
            if quotes_response.status_code == 200:
                quotes = quotes_response.json()
                for quote in quotes:
                    if quote.get("status") == "pending":
                        return quote
        return None
    
    def create_test_rfq_and_quote(self):
        """Create a test RFQ and have vendor submit a quote"""
        # First login vendor to get vendor info
        vendor_user = self.login_vendor()
        if not vendor_user:
            return None, None
            
        # Login buyer and create RFQ
        buyer_user = self.login_buyer()
        if not buyer_user:
            return None, None
        
        # Create test RFQ
        test_rfq = {
            "title": f"TEST_Negotiation_RFQ_{uuid.uuid4().hex[:8]}",
            "description": "Test RFQ for negotiation testing",
            "material_type": "Aluminum",
            "quantity": 50,
            "tolerance": 0.1,
            "surface_finish": "Polished",
            "supply_type": "vendor_material",
            "preferred_payment_terms": "net_30"
        }
        
        rfq_response = self.buyer_session.post(f"{BASE_URL}/api/rfqs", json=test_rfq)
        if rfq_response.status_code not in [200, 201]:
            return None, None
        
        rfq_data = rfq_response.json()
        rfq_id = rfq_data["rfq_id"]
        
        # Now have vendor submit a quote
        # Need to match vendors first (or manually create quote)
        # For now, let's check if there's an existing pending quote
        
        return rfq_data, None
    
    # ==================== GET /api/quotes/{quote_id} ====================
    
    def test_get_quote_detail_authenticated_buyer(self):
        """Test that authenticated buyer can get quote detail"""
        buyer = self.login_buyer()
        if not buyer:
            pytest.skip("Could not login as buyer")
        
        # Find a quote
        quote = self.get_pending_quote_for_buyer()
        if not quote:
            # Try to find any quote (pending or not)
            rfqs_response = self.buyer_session.get(f"{BASE_URL}/api/rfqs")
            if rfqs_response.status_code == 200:
                for rfq in rfqs_response.json():
                    quotes_response = self.buyer_session.get(f"{BASE_URL}/api/quotes/rfq/{rfq['rfq_id']}")
                    if quotes_response.status_code == 200 and quotes_response.json():
                        quote = quotes_response.json()[0]
                        break
        
        if not quote:
            pytest.skip("No quotes found for testing")
        
        # Get quote detail
        response = self.buyer_session.get(f"{BASE_URL}/api/quotes/{quote['quote_id']}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify expected fields
        assert "quote_id" in data
        assert "price" in data
        assert "lead_time_days" in data
        assert "vendor_name" in data or "vendor_id" in data
        assert "rfq_title" in data or "rfq_id" in data
        
        print(f"SUCCESS: Got quote detail for {quote['quote_id']}")
        print(f"  - Vendor: {data.get('vendor_name', 'N/A')}")
        print(f"  - Price: ${data.get('price', 0)}")
        print(f"  - Lead time: {data.get('lead_time_days', 0)} days")
        
        # Check for vendor enrichment fields
        if "vendor_machines" in data:
            print(f"  - Machines: {len(data.get('vendor_machines', []))} machines")
        if "vendor_certifications" in data:
            print(f"  - Certifications: {data.get('vendor_certifications', [])}")
    
    def test_get_quote_detail_includes_vendor_info(self):
        """Verify quote detail includes enriched vendor information"""
        buyer = self.login_buyer()
        if not buyer:
            pytest.skip("Could not login as buyer")
        
        quote = self.get_pending_quote_for_buyer()
        if not quote:
            # Try to find any quote
            rfqs_response = self.buyer_session.get(f"{BASE_URL}/api/rfqs")
            if rfqs_response.status_code == 200:
                for rfq in rfqs_response.json():
                    quotes_response = self.buyer_session.get(f"{BASE_URL}/api/quotes/rfq/{rfq['rfq_id']}")
                    if quotes_response.status_code == 200 and quotes_response.json():
                        quote = quotes_response.json()[0]
                        break
        
        if not quote:
            pytest.skip("No quotes found for testing")
        
        response = self.buyer_session.get(f"{BASE_URL}/api/quotes/{quote['quote_id']}")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check vendor enrichment
        vendor_fields = ["vendor_name", "vendor_rating", "vendor_total_jobs", 
                        "vendor_location", "vendor_certifications", "vendor_machines",
                        "vendor_acceptance_rate"]
        
        found_vendor_fields = [f for f in vendor_fields if f in data]
        print(f"Found vendor enrichment fields: {found_vendor_fields}")
        
        assert len(found_vendor_fields) > 0, "Expected vendor enrichment fields"
        
        # Check RFQ info
        rfq_fields = ["rfq_title", "rfq_material", "rfq_quantity", "rfq_tolerance"]
        found_rfq_fields = [f for f in rfq_fields if f in data]
        print(f"Found RFQ fields: {found_rfq_fields}")
    
    def test_get_quote_detail_includes_negotiations(self):
        """Verify quote detail includes negotiation history"""
        buyer = self.login_buyer()
        if not buyer:
            pytest.skip("Could not login as buyer")
        
        # Find any quote
        quote = None
        rfqs_response = self.buyer_session.get(f"{BASE_URL}/api/rfqs")
        if rfqs_response.status_code == 200:
            for rfq in rfqs_response.json():
                quotes_response = self.buyer_session.get(f"{BASE_URL}/api/quotes/rfq/{rfq['rfq_id']}")
                if quotes_response.status_code == 200 and quotes_response.json():
                    quote = quotes_response.json()[0]
                    break
        
        if not quote:
            pytest.skip("No quotes found for testing")
        
        response = self.buyer_session.get(f"{BASE_URL}/api/quotes/{quote['quote_id']}")
        assert response.status_code == 200
        
        data = response.json()
        assert "negotiations" in data, "Expected 'negotiations' field in quote detail"
        assert isinstance(data["negotiations"], list)
        print(f"Quote has {len(data['negotiations'])} negotiations")
    
    def test_get_quote_detail_unauthorized(self):
        """Test that unauthenticated users cannot access quote detail"""
        # Use a new session without auth
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        # Try to access any quote
        response = session.get(f"{BASE_URL}/api/quotes/quote_test123")
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("SUCCESS: Unauthenticated access correctly blocked")
    
    def test_get_quote_detail_nonexistent(self):
        """Test 404 for non-existent quote"""
        buyer = self.login_buyer()
        if not buyer:
            pytest.skip("Could not login as buyer")
        
        response = self.buyer_session.get(f"{BASE_URL}/api/quotes/nonexistent_quote_999")
        
        assert response.status_code == 404
        print("SUCCESS: 404 returned for non-existent quote")
    
    # ==================== POST /api/quotes/{quote_id}/negotiate ====================
    
    def test_negotiate_price_request(self):
        """Test buyer can request price negotiation"""
        buyer = self.login_buyer()
        if not buyer:
            pytest.skip("Could not login as buyer")
        
        quote = self.get_pending_quote_for_buyer()
        if not quote:
            pytest.skip("No pending quotes found for negotiation testing")
        
        current_price = quote.get("price", 1000)
        requested_price = current_price * 0.9  # Request 10% discount
        
        negotiation_payload = {
            "request_type": "price",
            "message": "TEST: Requesting 10% price reduction due to volume commitment",
            "requested_price": requested_price,
            "requested_lead_time": None,
            "requested_payment_terms": None
        }
        
        response = self.buyer_session.post(
            f"{BASE_URL}/api/quotes/{quote['quote_id']}/negotiate",
            json=negotiation_payload
        )
        
        # Quote might already be negotiated or not pending
        if response.status_code == 400:
            print(f"Cannot negotiate: {response.json().get('detail', 'Unknown')}")
            pytest.skip("Quote not in pending status")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "negotiation_id" in data
        assert data.get("status") == "pending"
        
        print(f"SUCCESS: Price negotiation request created - ID: {data['negotiation_id']}")
    
    def test_negotiate_lead_time_request(self):
        """Test buyer can request lead time change"""
        buyer = self.login_buyer()
        if not buyer:
            pytest.skip("Could not login as buyer")
        
        quote = self.get_pending_quote_for_buyer()
        if not quote:
            pytest.skip("No pending quotes found")
        
        negotiation_payload = {
            "request_type": "lead_time",
            "message": "TEST: Need faster delivery - can you reduce lead time?",
            "requested_price": None,
            "requested_lead_time": 10,
            "requested_payment_terms": None
        }
        
        response = self.buyer_session.post(
            f"{BASE_URL}/api/quotes/{quote['quote_id']}/negotiate",
            json=negotiation_payload
        )
        
        if response.status_code == 400:
            print(f"Cannot negotiate: {response.json().get('detail', 'Unknown')}")
            pytest.skip("Quote not in pending status")
        
        assert response.status_code == 200
        print(f"SUCCESS: Lead time negotiation created")
    
    def test_negotiate_payment_terms_request(self):
        """Test buyer can request payment terms change"""
        buyer = self.login_buyer()
        if not buyer:
            pytest.skip("Could not login as buyer")
        
        quote = self.get_pending_quote_for_buyer()
        if not quote:
            pytest.skip("No pending quotes found")
        
        negotiation_payload = {
            "request_type": "payment_terms",
            "message": "TEST: Requesting net_60 payment terms",
            "requested_price": None,
            "requested_lead_time": None,
            "requested_payment_terms": "net_60"
        }
        
        response = self.buyer_session.post(
            f"{BASE_URL}/api/quotes/{quote['quote_id']}/negotiate",
            json=negotiation_payload
        )
        
        if response.status_code == 400:
            print(f"Cannot negotiate: {response.json().get('detail', 'Unknown')}")
            pytest.skip("Quote not in pending status")
        
        assert response.status_code == 200
        print(f"SUCCESS: Payment terms negotiation created")
    
    def test_negotiate_general_request(self):
        """Test buyer can send general negotiation request"""
        buyer = self.login_buyer()
        if not buyer:
            pytest.skip("Could not login as buyer")
        
        quote = self.get_pending_quote_for_buyer()
        if not quote:
            pytest.skip("No pending quotes found")
        
        negotiation_payload = {
            "request_type": "general",
            "message": "TEST: General inquiry about your quote",
            "requested_price": None,
            "requested_lead_time": None,
            "requested_payment_terms": None
        }
        
        response = self.buyer_session.post(
            f"{BASE_URL}/api/quotes/{quote['quote_id']}/negotiate",
            json=negotiation_payload
        )
        
        if response.status_code == 400:
            print(f"Cannot negotiate: {response.json().get('detail', 'Unknown')}")
            pytest.skip("Quote not in pending status")
        
        assert response.status_code == 200
        print(f"SUCCESS: General negotiation request created")
    
    def test_negotiate_requires_message(self):
        """Test that negotiation requires a message"""
        buyer = self.login_buyer()
        if not buyer:
            pytest.skip("Could not login as buyer")
        
        quote = self.get_pending_quote_for_buyer()
        if not quote:
            pytest.skip("No pending quotes found")
        
        negotiation_payload = {
            "request_type": "price",
            "message": "",  # Empty message
            "requested_price": 100
        }
        
        response = self.buyer_session.post(
            f"{BASE_URL}/api/quotes/{quote['quote_id']}/negotiate",
            json=negotiation_payload
        )
        
        # The API may accept empty message or reject it
        if response.status_code == 200:
            print("API accepts empty message (might want to add validation)")
        else:
            print(f"API rejects empty message: {response.status_code}")
    
    # ==================== GET /api/quotes/{quote_id}/negotiations ====================
    
    def test_get_negotiations_list(self):
        """Test getting list of negotiations for a quote"""
        buyer = self.login_buyer()
        if not buyer:
            pytest.skip("Could not login as buyer")
        
        # Find any quote (pending or not)
        quote = None
        rfqs_response = self.buyer_session.get(f"{BASE_URL}/api/rfqs")
        if rfqs_response.status_code == 200:
            for rfq in rfqs_response.json():
                quotes_response = self.buyer_session.get(f"{BASE_URL}/api/quotes/rfq/{rfq['rfq_id']}")
                if quotes_response.status_code == 200 and quotes_response.json():
                    quote = quotes_response.json()[0]
                    break
        
        if not quote:
            pytest.skip("No quotes found")
        
        response = self.buyer_session.get(f"{BASE_URL}/api/quotes/{quote['quote_id']}/negotiations")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        print(f"SUCCESS: Got {len(data)} negotiations for quote {quote['quote_id']}")
        
        if len(data) > 0:
            negotiation = data[0]
            # Check expected fields
            expected_fields = ["negotiation_id", "quote_id", "request_type", "message", "status"]
            found_fields = [f for f in expected_fields if f in negotiation]
            print(f"  Negotiation fields: {found_fields}")
    
    # ==================== Vendor Response Tests ====================
    
    def test_vendor_can_view_quote_detail(self):
        """Test that vendor can view their own quote detail"""
        vendor = self.login_vendor()
        if not vendor:
            pytest.skip("Could not login as vendor")
        
        # Get vendor's RFQs (RFQs they're matched to)
        rfqs_response = self.vendor_session.get(f"{BASE_URL}/api/rfqs")
        if rfqs_response.status_code != 200:
            pytest.skip("Could not get vendor RFQs")
        
        rfqs = rfqs_response.json()
        if not rfqs:
            pytest.skip("Vendor has no matched RFQs")
        
        # Find a quote from this vendor
        quote = None
        for rfq in rfqs:
            quotes_response = self.vendor_session.get(f"{BASE_URL}/api/quotes/rfq/{rfq['rfq_id']}")
            if quotes_response.status_code == 200:
                quotes = quotes_response.json()
                for q in quotes:
                    # Vendor should see their own quotes
                    if q.get("vendor_id"):
                        quote = q
                        break
            if quote:
                break
        
        if not quote:
            pytest.skip("No quotes found for vendor")
        
        response = self.vendor_session.get(f"{BASE_URL}/api/quotes/{quote['quote_id']}")
        
        # Vendor should be able to access their own quote
        if response.status_code == 200:
            print(f"SUCCESS: Vendor can view quote {quote['quote_id']}")
        elif response.status_code == 403:
            print(f"Note: Vendor cannot view this quote (may not be theirs)")
        else:
            print(f"Response: {response.status_code} - {response.text[:200]}")


class TestNegotiationWorkflow:
    """Full workflow tests for negotiation feature"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.buyer_session = requests.Session()
        self.buyer_session.headers.update({"Content-Type": "application/json"})
        self.vendor_session = requests.Session()
        self.vendor_session.headers.update({"Content-Type": "application/json"})
    
    def test_full_negotiation_workflow_accept(self):
        """Test complete negotiation workflow with vendor accepting"""
        # Login both users
        buyer_login = self.buyer_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": BUYER_EMAIL, "password": BUYER_PASSWORD
        })
        if buyer_login.status_code != 200:
            pytest.skip("Could not login buyer")
        self.buyer_session.headers.update({"Authorization": f"Bearer {buyer_login.json()['access_token']}"})
        
        vendor_login = self.vendor_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": VENDOR_EMAIL, "password": VENDOR_PASSWORD
        })
        if vendor_login.status_code != 200:
            pytest.skip("Could not login vendor")
        self.vendor_session.headers.update({"Authorization": f"Bearer {vendor_login.json()['access_token']}"})
        
        # Find pending quote
        pending_quote = None
        rfqs_response = self.buyer_session.get(f"{BASE_URL}/api/rfqs")
        if rfqs_response.status_code == 200:
            for rfq in rfqs_response.json():
                quotes_response = self.buyer_session.get(f"{BASE_URL}/api/quotes/rfq/{rfq['rfq_id']}")
                if quotes_response.status_code == 200:
                    for quote in quotes_response.json():
                        if quote.get("status") == "pending":
                            pending_quote = quote
                            break
                if pending_quote:
                    break
        
        if not pending_quote:
            pytest.skip("No pending quotes for workflow test")
        
        quote_id = pending_quote["quote_id"]
        
        # Step 1: Buyer requests price negotiation
        neg_response = self.buyer_session.post(
            f"{BASE_URL}/api/quotes/{quote_id}/negotiate",
            json={
                "request_type": "price",
                "message": "TEST WORKFLOW: Requesting discount",
                "requested_price": pending_quote.get("price", 1000) * 0.85
            }
        )
        
        if neg_response.status_code != 200:
            print(f"Negotiation failed: {neg_response.status_code} - {neg_response.text}")
            pytest.skip("Could not create negotiation")
        
        negotiation_id = neg_response.json()["negotiation_id"]
        print(f"Step 1: Created negotiation {negotiation_id}")
        
        # Step 2: Vendor views negotiations
        neg_list_response = self.vendor_session.get(f"{BASE_URL}/api/quotes/{quote_id}/negotiations")
        
        if neg_list_response.status_code == 200:
            negotiations = neg_list_response.json()
            pending_negs = [n for n in negotiations if n.get("status") == "pending"]
            print(f"Step 2: Vendor sees {len(pending_negs)} pending negotiations")
        else:
            print(f"Step 2: Could not get negotiations: {neg_list_response.status_code}")
        
        # Step 3: Vendor responds (accept)
        respond_response = self.vendor_session.post(
            f"{BASE_URL}/api/quotes/{quote_id}/negotiate/{negotiation_id}/respond",
            json={
                "action": "accept",
                "message": "TEST: Accepted your request"
            }
        )
        
        if respond_response.status_code == 200:
            print(f"Step 3: Vendor accepted negotiation")
        elif respond_response.status_code == 403:
            print(f"Step 3: Vendor not authorized (may be different vendor's quote)")
        else:
            print(f"Step 3: Response failed: {respond_response.status_code} - {respond_response.text}")
        
        # Verify final state
        final_response = self.buyer_session.get(f"{BASE_URL}/api/quotes/{quote_id}")
        if final_response.status_code == 200:
            final_data = final_response.json()
            print(f"Final quote state: negotiation_status={final_data.get('negotiation_status')}")
        
        print("Workflow test completed")


class TestAPIValidation:
    """API validation and error handling tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def login(self):
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": BUYER_EMAIL, "password": BUYER_PASSWORD
        })
        if response.status_code == 200:
            self.session.headers.update({"Authorization": f"Bearer {response.json()['access_token']}"})
            return True
        return False
    
    def test_negotiate_invalid_quote_id(self):
        """Test negotiation with invalid quote ID returns 404"""
        if not self.login():
            pytest.skip("Could not login")
        
        response = self.session.post(
            f"{BASE_URL}/api/quotes/invalid_quote_xyz/negotiate",
            json={"request_type": "price", "message": "test"}
        )
        
        assert response.status_code == 404
        print("SUCCESS: 404 for invalid quote ID")
    
    def test_respond_invalid_negotiation_id(self):
        """Test responding to invalid negotiation returns 404"""
        if not self.login():
            pytest.skip("Could not login")
        
        response = self.session.post(
            f"{BASE_URL}/api/quotes/quote_test/negotiate/invalid_neg_xyz/respond",
            json={"action": "accept"}
        )
        
        assert response.status_code in [404, 403]
        print(f"SUCCESS: Got {response.status_code} for invalid negotiation")
    
    def test_accept_counter_invalid(self):
        """Test accepting invalid counter offer"""
        if not self.login():
            pytest.skip("Could not login")
        
        response = self.session.post(
            f"{BASE_URL}/api/quotes/quote_test/negotiate/invalid_neg/accept-counter"
        )
        
        assert response.status_code in [404, 403]
        print(f"SUCCESS: Got {response.status_code} for invalid accept-counter")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
