"""
E2E Payment Terms Tests - Custom and Milestone-Based Payment Terms
Tests the full flow: Create RFQ -> Submit Quote with payment terms -> Accept Quote -> Verify Payment Schedule

Tests verify:
1. Custom payment terms with notes (e.g., '25% advance, 75% on delivery') are correctly parsed
2. Milestone-based payment terms with notes generate correct milestones
3. Custom terms with NO notes fall back to 30/40/30 default
4. Standard payment terms (50_advance_50_delivery, net_30) work correctly
5. accept_quote response includes payment_schedule field with correct milestones
6. GET /api/orders/{order_id}/payment-schedule returns matching schedule
"""
import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@offoadex.com"
ADMIN_PASSWORD = "admin123"
BUYER_EMAIL = "visualbuyer@test.com"
BUYER_PASSWORD = "buyer123"
VENDOR_EMAIL = "testvendor_nda@test.com"
VENDOR_PASSWORD = "vendor123"


class TestCustomPaymentTermsE2E:
    """E2E tests for custom payment terms with notes parsing"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.created_rfqs = []
        self.created_quotes = []
        self.created_orders = []
    
    def login(self, email, password):
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            return response.json()
        return None
    
    def create_rfq(self, title_suffix=""):
        """Create an RFQ as buyer"""
        unique_id = uuid.uuid4().hex[:8]
        rfq_data = {
            "title": f"TEST_PaymentTerms_{title_suffix}_{unique_id}",
            "description": "Test RFQ for payment terms E2E testing",
            "material_type": "Steel",
            "quantity": 100,
            "tolerance": 0.1,
            "surface_finish": "Ra 1.6",
            "deadline": "2026-03-01",
            "urgency": "normal"
        }
        response = self.session.post(f"{BASE_URL}/api/rfqs", json=rfq_data)
        if response.status_code in [200, 201]:
            data = response.json()
            rfq_id = data.get("rfq_id") or data.get("id")
            self.created_rfqs.append(rfq_id)
            return rfq_id
        return None
    
    def submit_quote(self, rfq_id, payment_terms, payment_terms_notes=None, price=10000):
        """Submit a quote as vendor"""
        quote_data = {
            "rfq_id": rfq_id,
            "material_cost": price * 0.4,
            "machining_cost": price * 0.6,
            "lead_time_days": 14,
            "proposed_payment_terms": payment_terms,
            "notes": "Test quotation for payment terms testing"
        }
        if payment_terms_notes:
            quote_data["payment_terms_notes"] = payment_terms_notes
        
        response = self.session.post(f"{BASE_URL}/api/vendor/quotation", json=quote_data)
        if response.status_code in [200, 201]:
            data = response.json()
            quote_id = data.get("quote_id")
            self.created_quotes.append(quote_id)
            return quote_id, data
        return None, response.json() if response.status_code != 500 else {"error": response.text}
    
    def accept_quote(self, quote_id):
        """Accept a quote as buyer"""
        response = self.session.post(f"{BASE_URL}/api/quotes/{quote_id}/accept")
        if response.status_code == 200:
            data = response.json()
            order_id = data.get("order_id")
            if order_id:
                self.created_orders.append(order_id)
            return data
        return {"error": response.text, "status_code": response.status_code}
    
    def get_payment_schedule(self, order_id):
        """Get payment schedule for an order"""
        response = self.session.get(f"{BASE_URL}/api/orders/{order_id}/payment-schedule")
        if response.status_code == 200:
            return response.json()
        return {"error": response.text, "status_code": response.status_code}
    
    # ==================== TEST: Custom Payment Terms with Notes ====================
    
    def test_custom_25_75_split_e2e(self):
        """
        E2E: Custom payment terms '25% advance, 75% on delivery' 
        Should generate 2 milestones: 25% before_production, 75% after_dispatch
        """
        # Step 1: Login as buyer and create RFQ
        buyer = self.login(BUYER_EMAIL, BUYER_PASSWORD)
        assert buyer, "Failed to login as buyer"
        
        rfq_id = self.create_rfq("Custom_25_75")
        assert rfq_id, "Failed to create RFQ"
        print(f"Created RFQ: {rfq_id}")
        
        # Step 2: Login as vendor and submit quote with custom terms
        vendor = self.login(VENDOR_EMAIL, VENDOR_PASSWORD)
        assert vendor, "Failed to login as vendor"
        
        quote_id, quote_response = self.submit_quote(
            rfq_id=rfq_id,
            payment_terms="custom",
            payment_terms_notes="25% advance, 75% on delivery",
            price=10000
        )
        assert quote_id, f"Failed to submit quote: {quote_response}"
        print(f"Submitted quote: {quote_id}")
        
        # Step 3: Login as buyer and accept quote
        buyer = self.login(BUYER_EMAIL, BUYER_PASSWORD)
        assert buyer, "Failed to login as buyer"
        
        accept_response = self.accept_quote(quote_id)
        assert "order_id" in accept_response, f"Failed to accept quote: {accept_response}"
        order_id = accept_response["order_id"]
        print(f"Accepted quote, created order: {order_id}")
        
        # Step 4: Verify accept_quote response includes payment_schedule
        assert "payment_schedule" in accept_response, "accept_quote response should include payment_schedule"
        payment_schedule = accept_response["payment_schedule"]
        assert "milestones" in payment_schedule, "payment_schedule should have milestones"
        
        milestones = payment_schedule["milestones"]
        print(f"Milestones from accept_quote: {milestones}")
        
        # Verify 2 milestones with 25/75 split
        assert len(milestones) == 2, f"Expected 2 milestones for 25/75 split, got {len(milestones)}"
        
        percentages = [m["percentage"] for m in milestones]
        assert 25 in percentages, f"Should have 25% milestone, got {percentages}"
        assert 75 in percentages, f"Should have 75% milestone, got {percentages}"
        
        # Verify stages
        stages = [m["stage"] for m in milestones]
        assert "before_production" in stages, f"Should have before_production stage for advance, got {stages}"
        assert "after_dispatch" in stages or "on_delivery" in stages, f"Should have delivery stage, got {stages}"
        
        # Step 5: Verify GET payment-schedule returns same data
        schedule_response = self.get_payment_schedule(order_id)
        assert "schedule" in schedule_response, f"Failed to get payment schedule: {schedule_response}"
        
        schedule_milestones = schedule_response["schedule"]["milestones"]
        schedule_percentages = [m["percentage"] for m in schedule_milestones]
        assert schedule_percentages == percentages, f"GET schedule percentages {schedule_percentages} should match accept response {percentages}"
        
        print(f"PASS: Custom 25/75 split E2E - milestones: {percentages}, stages: {stages}")
    
    def test_custom_no_notes_defaults_to_30_40_30(self):
        """
        E2E: Custom payment terms with NO notes should default to 30/40/30
        """
        # Step 1: Login as buyer and create RFQ
        buyer = self.login(BUYER_EMAIL, BUYER_PASSWORD)
        assert buyer, "Failed to login as buyer"
        
        rfq_id = self.create_rfq("Custom_NoNotes")
        assert rfq_id, "Failed to create RFQ"
        print(f"Created RFQ: {rfq_id}")
        
        # Step 2: Login as vendor and submit quote with custom terms but NO notes
        vendor = self.login(VENDOR_EMAIL, VENDOR_PASSWORD)
        assert vendor, "Failed to login as vendor"
        
        quote_id, quote_response = self.submit_quote(
            rfq_id=rfq_id,
            payment_terms="custom",
            payment_terms_notes="",  # Empty notes
            price=15000
        )
        assert quote_id, f"Failed to submit quote: {quote_response}"
        print(f"Submitted quote: {quote_id}")
        
        # Step 3: Login as buyer and accept quote
        buyer = self.login(BUYER_EMAIL, BUYER_PASSWORD)
        assert buyer, "Failed to login as buyer"
        
        accept_response = self.accept_quote(quote_id)
        assert "order_id" in accept_response, f"Failed to accept quote: {accept_response}"
        order_id = accept_response["order_id"]
        print(f"Accepted quote, created order: {order_id}")
        
        # Step 4: Verify payment_schedule defaults to 30/40/30
        assert "payment_schedule" in accept_response, "accept_quote response should include payment_schedule"
        milestones = accept_response["payment_schedule"]["milestones"]
        
        percentages = [m["percentage"] for m in milestones]
        assert percentages == [30, 40, 30], f"Expected default [30, 40, 30], got {percentages}"
        
        # Verify stages
        stages = [m["stage"] for m in milestones]
        assert stages == ["before_production", "after_production", "after_inspection"], f"Expected standard stages, got {stages}"
        
        print(f"PASS: Custom with no notes defaults to 30/40/30 - percentages: {percentages}")


class TestMilestoneBasedPaymentTermsE2E:
    """E2E tests for milestone_based payment terms with notes parsing"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.created_rfqs = []
        self.created_quotes = []
        self.created_orders = []
    
    def login(self, email, password):
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            return response.json()
        return None
    
    def create_rfq(self, title_suffix=""):
        unique_id = uuid.uuid4().hex[:8]
        rfq_data = {
            "title": f"TEST_MilestoneTerms_{title_suffix}_{unique_id}",
            "description": "Test RFQ for milestone payment terms E2E testing",
            "material_type": "Aluminum",
            "quantity": 50,
            "tolerance": 0.05,
            "surface_finish": "Ra 0.8",
            "deadline": "2026-03-15",
            "urgency": "normal"
        }
        response = self.session.post(f"{BASE_URL}/api/rfqs", json=rfq_data)
        if response.status_code in [200, 201]:
            data = response.json()
            rfq_id = data.get("rfq_id") or data.get("id")
            self.created_rfqs.append(rfq_id)
            return rfq_id
        return None
    
    def submit_quote(self, rfq_id, payment_terms, payment_terms_notes=None, price=10000):
        quote_data = {
            "rfq_id": rfq_id,
            "material_cost": price * 0.4,
            "machining_cost": price * 0.6,
            "lead_time_days": 14,
            "proposed_payment_terms": payment_terms,
            "notes": "Test quotation"
        }
        if payment_terms_notes:
            quote_data["payment_terms_notes"] = payment_terms_notes
        
        response = self.session.post(f"{BASE_URL}/api/vendor/quotation", json=quote_data)
        if response.status_code in [200, 201]:
            data = response.json()
            quote_id = data.get("quote_id")
            self.created_quotes.append(quote_id)
            return quote_id, data
        return None, response.json() if response.status_code != 500 else {"error": response.text}
    
    def accept_quote(self, quote_id):
        response = self.session.post(f"{BASE_URL}/api/quotes/{quote_id}/accept")
        if response.status_code == 200:
            data = response.json()
            order_id = data.get("order_id")
            if order_id:
                self.created_orders.append(order_id)
            return data
        return {"error": response.text, "status_code": response.status_code}
    
    def get_payment_schedule(self, order_id):
        response = self.session.get(f"{BASE_URL}/api/orders/{order_id}/payment-schedule")
        if response.status_code == 200:
            return response.json()
        return {"error": response.text, "status_code": response.status_code}
    
    def test_milestone_30_40_30_e2e(self):
        """
        E2E: Milestone-based '30% advance, 40% after production, 30% after inspection'
        Should generate 3 milestones with correct stages
        """
        # Step 1: Login as buyer and create RFQ
        buyer = self.login(BUYER_EMAIL, BUYER_PASSWORD)
        assert buyer, "Failed to login as buyer"
        
        rfq_id = self.create_rfq("Milestone_30_40_30")
        assert rfq_id, "Failed to create RFQ"
        print(f"Created RFQ: {rfq_id}")
        
        # Step 2: Login as vendor and submit quote
        vendor = self.login(VENDOR_EMAIL, VENDOR_PASSWORD)
        assert vendor, "Failed to login as vendor"
        
        quote_id, quote_response = self.submit_quote(
            rfq_id=rfq_id,
            payment_terms="milestone_based",
            payment_terms_notes="30% advance, 40% after production, 30% after inspection",
            price=20000
        )
        assert quote_id, f"Failed to submit quote: {quote_response}"
        print(f"Submitted quote: {quote_id}")
        
        # Step 3: Login as buyer and accept quote
        buyer = self.login(BUYER_EMAIL, BUYER_PASSWORD)
        assert buyer, "Failed to login as buyer"
        
        accept_response = self.accept_quote(quote_id)
        assert "order_id" in accept_response, f"Failed to accept quote: {accept_response}"
        order_id = accept_response["order_id"]
        print(f"Accepted quote, created order: {order_id}")
        
        # Step 4: Verify payment_schedule
        assert "payment_schedule" in accept_response, "accept_quote response should include payment_schedule"
        milestones = accept_response["payment_schedule"]["milestones"]
        
        # Verify 3 milestones with 30/40/30 split
        assert len(milestones) == 3, f"Expected 3 milestones, got {len(milestones)}"
        
        percentages = [m["percentage"] for m in milestones]
        assert percentages == [30, 40, 30], f"Expected [30, 40, 30], got {percentages}"
        
        # Verify stages
        stages = [m["stage"] for m in milestones]
        assert "before_production" in stages, f"Should have before_production stage, got {stages}"
        assert "after_production" in stages, f"Should have after_production stage, got {stages}"
        assert "after_inspection" in stages, f"Should have after_inspection stage, got {stages}"
        
        # Verify amounts
        total = 20000
        amounts = [m["amount"] for m in milestones]
        expected_amounts = [6000, 8000, 6000]  # 30%, 40%, 30% of 20000
        assert amounts == expected_amounts, f"Expected amounts {expected_amounts}, got {amounts}"
        
        print(f"PASS: Milestone 30/40/30 E2E - percentages: {percentages}, stages: {stages}, amounts: {amounts}")
    
    def test_milestone_no_notes_defaults(self):
        """
        E2E: Milestone-based with NO notes should default to 30/40/30
        """
        # Step 1: Login as buyer and create RFQ
        buyer = self.login(BUYER_EMAIL, BUYER_PASSWORD)
        assert buyer, "Failed to login as buyer"
        
        rfq_id = self.create_rfq("Milestone_NoNotes")
        assert rfq_id, "Failed to create RFQ"
        print(f"Created RFQ: {rfq_id}")
        
        # Step 2: Login as vendor and submit quote with milestone_based but no notes
        vendor = self.login(VENDOR_EMAIL, VENDOR_PASSWORD)
        assert vendor, "Failed to login as vendor"
        
        quote_id, quote_response = self.submit_quote(
            rfq_id=rfq_id,
            payment_terms="milestone_based",
            payment_terms_notes=None,  # No notes
            price=12000
        )
        assert quote_id, f"Failed to submit quote: {quote_response}"
        print(f"Submitted quote: {quote_id}")
        
        # Step 3: Login as buyer and accept quote
        buyer = self.login(BUYER_EMAIL, BUYER_PASSWORD)
        assert buyer, "Failed to login as buyer"
        
        accept_response = self.accept_quote(quote_id)
        assert "order_id" in accept_response, f"Failed to accept quote: {accept_response}"
        order_id = accept_response["order_id"]
        print(f"Accepted quote, created order: {order_id}")
        
        # Step 4: Verify defaults to 30/40/30
        milestones = accept_response["payment_schedule"]["milestones"]
        percentages = [m["percentage"] for m in milestones]
        assert percentages == [30, 40, 30], f"Expected default [30, 40, 30], got {percentages}"
        
        print(f"PASS: Milestone with no notes defaults to 30/40/30")


class TestStandardPaymentTermsE2E:
    """E2E tests for standard payment terms (50_advance_50_delivery, net_30, etc.)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.created_rfqs = []
        self.created_quotes = []
        self.created_orders = []
    
    def login(self, email, password):
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            return response.json()
        return None
    
    def create_rfq(self, title_suffix=""):
        unique_id = uuid.uuid4().hex[:8]
        rfq_data = {
            "title": f"TEST_StandardTerms_{title_suffix}_{unique_id}",
            "description": "Test RFQ for standard payment terms E2E testing",
            "material_type": "Brass",
            "quantity": 200,
            "tolerance": 0.1,
            "deadline": "2026-04-01",
            "urgency": "normal"
        }
        response = self.session.post(f"{BASE_URL}/api/rfqs", json=rfq_data)
        if response.status_code in [200, 201]:
            data = response.json()
            rfq_id = data.get("rfq_id") or data.get("id")
            self.created_rfqs.append(rfq_id)
            return rfq_id
        return None
    
    def submit_quote(self, rfq_id, payment_terms, payment_terms_notes=None, price=10000):
        quote_data = {
            "rfq_id": rfq_id,
            "material_cost": price * 0.4,
            "machining_cost": price * 0.6,
            "lead_time_days": 14,
            "proposed_payment_terms": payment_terms,
            "notes": "Test quotation"
        }
        if payment_terms_notes:
            quote_data["payment_terms_notes"] = payment_terms_notes
        
        response = self.session.post(f"{BASE_URL}/api/vendor/quotation", json=quote_data)
        if response.status_code in [200, 201]:
            data = response.json()
            quote_id = data.get("quote_id")
            self.created_quotes.append(quote_id)
            return quote_id, data
        return None, response.json() if response.status_code != 500 else {"error": response.text}
    
    def accept_quote(self, quote_id):
        response = self.session.post(f"{BASE_URL}/api/quotes/{quote_id}/accept")
        if response.status_code == 200:
            data = response.json()
            order_id = data.get("order_id")
            if order_id:
                self.created_orders.append(order_id)
            return data
        return {"error": response.text, "status_code": response.status_code}
    
    def get_payment_schedule(self, order_id):
        response = self.session.get(f"{BASE_URL}/api/orders/{order_id}/payment-schedule")
        if response.status_code == 200:
            return response.json()
        return {"error": response.text, "status_code": response.status_code}
    
    def test_50_advance_50_delivery_e2e(self):
        """
        E2E: 50_advance_50_delivery generates 50/50 split
        """
        # Step 1: Login as buyer and create RFQ
        buyer = self.login(BUYER_EMAIL, BUYER_PASSWORD)
        assert buyer, "Failed to login as buyer"
        
        rfq_id = self.create_rfq("50_50")
        assert rfq_id, "Failed to create RFQ"
        print(f"Created RFQ: {rfq_id}")
        
        # Step 2: Login as vendor and submit quote
        vendor = self.login(VENDOR_EMAIL, VENDOR_PASSWORD)
        assert vendor, "Failed to login as vendor"
        
        quote_id, quote_response = self.submit_quote(
            rfq_id=rfq_id,
            payment_terms="50_advance_50_delivery",
            price=8000
        )
        assert quote_id, f"Failed to submit quote: {quote_response}"
        print(f"Submitted quote: {quote_id}")
        
        # Step 3: Login as buyer and accept quote
        buyer = self.login(BUYER_EMAIL, BUYER_PASSWORD)
        assert buyer, "Failed to login as buyer"
        
        accept_response = self.accept_quote(quote_id)
        assert "order_id" in accept_response, f"Failed to accept quote: {accept_response}"
        order_id = accept_response["order_id"]
        print(f"Accepted quote, created order: {order_id}")
        
        # Step 4: Verify payment_schedule
        assert "payment_schedule" in accept_response, "accept_quote response should include payment_schedule"
        milestones = accept_response["payment_schedule"]["milestones"]
        
        # Verify 2 milestones with 50/50 split
        assert len(milestones) == 2, f"Expected 2 milestones, got {len(milestones)}"
        
        percentages = [m["percentage"] for m in milestones]
        assert percentages == [50, 50], f"Expected [50, 50], got {percentages}"
        
        # Verify stages
        stages = [m["stage"] for m in milestones]
        assert "before_production" in stages, f"Should have before_production stage, got {stages}"
        assert "after_dispatch" in stages, f"Should have after_dispatch stage, got {stages}"
        
        # Verify amounts
        amounts = [m["amount"] for m in milestones]
        assert amounts == [4000, 4000], f"Expected [4000, 4000], got {amounts}"
        
        print(f"PASS: 50_advance_50_delivery E2E - percentages: {percentages}, stages: {stages}")
    
    def test_net_30_e2e(self):
        """
        E2E: net_30 generates single net_due milestone
        """
        # Step 1: Login as buyer and create RFQ
        buyer = self.login(BUYER_EMAIL, BUYER_PASSWORD)
        assert buyer, "Failed to login as buyer"
        
        rfq_id = self.create_rfq("Net30")
        assert rfq_id, "Failed to create RFQ"
        print(f"Created RFQ: {rfq_id}")
        
        # Step 2: Login as vendor and submit quote
        vendor = self.login(VENDOR_EMAIL, VENDOR_PASSWORD)
        assert vendor, "Failed to login as vendor"
        
        quote_id, quote_response = self.submit_quote(
            rfq_id=rfq_id,
            payment_terms="net_30",
            price=5000
        )
        assert quote_id, f"Failed to submit quote: {quote_response}"
        print(f"Submitted quote: {quote_id}")
        
        # Step 3: Login as buyer and accept quote
        buyer = self.login(BUYER_EMAIL, BUYER_PASSWORD)
        assert buyer, "Failed to login as buyer"
        
        accept_response = self.accept_quote(quote_id)
        assert "order_id" in accept_response, f"Failed to accept quote: {accept_response}"
        order_id = accept_response["order_id"]
        print(f"Accepted quote, created order: {order_id}")
        
        # Step 4: Verify payment_schedule
        assert "payment_schedule" in accept_response, "accept_quote response should include payment_schedule"
        milestones = accept_response["payment_schedule"]["milestones"]
        
        # Verify single milestone
        assert len(milestones) == 1, f"Expected 1 milestone for net_30, got {len(milestones)}"
        
        ms = milestones[0]
        assert ms["percentage"] == 100, f"Expected 100%, got {ms['percentage']}"
        assert ms["stage"] == "net_due", f"Expected net_due stage, got {ms['stage']}"
        assert ms["due_days"] == 30, f"Expected due_days=30, got {ms.get('due_days')}"
        assert ms["amount"] == 5000, f"Expected amount=5000, got {ms['amount']}"
        
        # Verify schedule type
        schedule_type = accept_response["payment_schedule"]["type"]
        assert schedule_type == "credit_terms", f"Expected credit_terms type, got {schedule_type}"
        
        print(f"PASS: net_30 E2E - single net_due milestone with 30 days")
    
    def test_100_advance_e2e(self):
        """
        E2E: 100_advance generates single before_production milestone
        """
        # Step 1: Login as buyer and create RFQ
        buyer = self.login(BUYER_EMAIL, BUYER_PASSWORD)
        assert buyer, "Failed to login as buyer"
        
        rfq_id = self.create_rfq("100Advance")
        assert rfq_id, "Failed to create RFQ"
        print(f"Created RFQ: {rfq_id}")
        
        # Step 2: Login as vendor and submit quote
        vendor = self.login(VENDOR_EMAIL, VENDOR_PASSWORD)
        assert vendor, "Failed to login as vendor"
        
        quote_id, quote_response = self.submit_quote(
            rfq_id=rfq_id,
            payment_terms="100_advance",
            price=7500
        )
        assert quote_id, f"Failed to submit quote: {quote_response}"
        print(f"Submitted quote: {quote_id}")
        
        # Step 3: Login as buyer and accept quote
        buyer = self.login(BUYER_EMAIL, BUYER_PASSWORD)
        assert buyer, "Failed to login as buyer"
        
        accept_response = self.accept_quote(quote_id)
        assert "order_id" in accept_response, f"Failed to accept quote: {accept_response}"
        order_id = accept_response["order_id"]
        print(f"Accepted quote, created order: {order_id}")
        
        # Step 4: Verify payment_schedule
        milestones = accept_response["payment_schedule"]["milestones"]
        
        # Verify single milestone
        assert len(milestones) == 1, f"Expected 1 milestone for 100_advance, got {len(milestones)}"
        
        ms = milestones[0]
        assert ms["percentage"] == 100, f"Expected 100%, got {ms['percentage']}"
        assert ms["stage"] == "before_production", f"Expected before_production stage, got {ms['stage']}"
        assert ms["amount"] == 7500, f"Expected amount=7500, got {ms['amount']}"
        
        print(f"PASS: 100_advance E2E - single before_production milestone")
    
    def test_against_delivery_e2e(self):
        """
        E2E: against_delivery generates single on_delivery milestone
        """
        # Step 1: Login as buyer and create RFQ
        buyer = self.login(BUYER_EMAIL, BUYER_PASSWORD)
        assert buyer, "Failed to login as buyer"
        
        rfq_id = self.create_rfq("AgainstDelivery")
        assert rfq_id, "Failed to create RFQ"
        print(f"Created RFQ: {rfq_id}")
        
        # Step 2: Login as vendor and submit quote
        vendor = self.login(VENDOR_EMAIL, VENDOR_PASSWORD)
        assert vendor, "Failed to login as vendor"
        
        quote_id, quote_response = self.submit_quote(
            rfq_id=rfq_id,
            payment_terms="against_delivery",
            price=6000
        )
        assert quote_id, f"Failed to submit quote: {quote_response}"
        print(f"Submitted quote: {quote_id}")
        
        # Step 3: Login as buyer and accept quote
        buyer = self.login(BUYER_EMAIL, BUYER_PASSWORD)
        assert buyer, "Failed to login as buyer"
        
        accept_response = self.accept_quote(quote_id)
        assert "order_id" in accept_response, f"Failed to accept quote: {accept_response}"
        order_id = accept_response["order_id"]
        print(f"Accepted quote, created order: {order_id}")
        
        # Step 4: Verify payment_schedule
        milestones = accept_response["payment_schedule"]["milestones"]
        
        # Verify single milestone
        assert len(milestones) == 1, f"Expected 1 milestone for against_delivery, got {len(milestones)}"
        
        ms = milestones[0]
        assert ms["percentage"] == 100, f"Expected 100%, got {ms['percentage']}"
        assert ms["stage"] == "on_delivery", f"Expected on_delivery stage, got {ms['stage']}"
        assert ms["amount"] == 6000, f"Expected amount=6000, got {ms['amount']}"
        
        print(f"PASS: against_delivery E2E - single on_delivery milestone")


class TestAcceptQuoteResponseStructure:
    """Test that accept_quote response has correct structure"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.created_rfqs = []
        self.created_quotes = []
        self.created_orders = []
    
    def login(self, email, password):
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            return response.json()
        return None
    
    def create_rfq(self, title_suffix=""):
        unique_id = uuid.uuid4().hex[:8]
        rfq_data = {
            "title": f"TEST_ResponseStructure_{title_suffix}_{unique_id}",
            "description": "Test RFQ for response structure testing",
            "material_type": "Copper",
            "quantity": 75,
            "tolerance": 0.05,
            "deadline": "2026-04-15",
            "urgency": "normal"
        }
        response = self.session.post(f"{BASE_URL}/api/rfqs", json=rfq_data)
        if response.status_code in [200, 201]:
            data = response.json()
            rfq_id = data.get("rfq_id") or data.get("id")
            self.created_rfqs.append(rfq_id)
            return rfq_id
        return None
    
    def submit_quote(self, rfq_id, payment_terms, payment_terms_notes=None, price=10000):
        quote_data = {
            "rfq_id": rfq_id,
            "material_cost": price * 0.4,
            "machining_cost": price * 0.6,
            "lead_time_days": 14,
            "proposed_payment_terms": payment_terms,
            "notes": "Test quotation"
        }
        if payment_terms_notes:
            quote_data["payment_terms_notes"] = payment_terms_notes
        
        response = self.session.post(f"{BASE_URL}/api/vendor/quotation", json=quote_data)
        if response.status_code in [200, 201]:
            data = response.json()
            quote_id = data.get("quote_id")
            self.created_quotes.append(quote_id)
            return quote_id, data
        return None, response.json() if response.status_code != 500 else {"error": response.text}
    
    def accept_quote(self, quote_id):
        response = self.session.post(f"{BASE_URL}/api/quotes/{quote_id}/accept")
        if response.status_code == 200:
            data = response.json()
            order_id = data.get("order_id")
            if order_id:
                self.created_orders.append(order_id)
            return data
        return {"error": response.text, "status_code": response.status_code}
    
    def test_accept_quote_response_has_all_fields(self):
        """
        Verify accept_quote response includes all required fields:
        - order_id, po_number, payment_terms, payment_terms_label, payment_terms_notes
        - payment_schedule with type, milestones, total_paid, total_pending
        """
        # Step 1: Login as buyer and create RFQ
        buyer = self.login(BUYER_EMAIL, BUYER_PASSWORD)
        assert buyer, "Failed to login as buyer"
        
        rfq_id = self.create_rfq("ResponseFields")
        assert rfq_id, "Failed to create RFQ"
        
        # Step 2: Login as vendor and submit quote
        vendor = self.login(VENDOR_EMAIL, VENDOR_PASSWORD)
        assert vendor, "Failed to login as vendor"
        
        quote_id, _ = self.submit_quote(
            rfq_id=rfq_id,
            payment_terms="custom",
            payment_terms_notes="40% advance, 60% on delivery",
            price=10000
        )
        assert quote_id, "Failed to submit quote"
        
        # Step 3: Login as buyer and accept quote
        buyer = self.login(BUYER_EMAIL, BUYER_PASSWORD)
        assert buyer, "Failed to login as buyer"
        
        accept_response = self.accept_quote(quote_id)
        assert "order_id" in accept_response, f"Failed to accept quote: {accept_response}"
        
        # Verify top-level fields
        required_fields = ["order_id", "po_number", "payment_terms", "payment_terms_label", 
                          "payment_terms_notes", "payment_schedule", "total_amount", "currency"]
        for field in required_fields:
            assert field in accept_response, f"Missing required field: {field}"
        
        # Verify payment_schedule structure
        ps = accept_response["payment_schedule"]
        assert "type" in ps, "payment_schedule missing 'type'"
        assert "milestones" in ps, "payment_schedule missing 'milestones'"
        assert "total_paid" in ps, "payment_schedule missing 'total_paid'"
        assert "total_pending" in ps, "payment_schedule missing 'total_pending'"
        
        # Verify milestone structure
        for ms in ps["milestones"]:
            ms_required = ["milestone_id", "stage", "label", "percentage", "amount", "status"]
            for field in ms_required:
                assert field in ms, f"Milestone missing required field: {field}"
        
        print(f"PASS: accept_quote response has all required fields")
        print(f"  - Top-level: {list(accept_response.keys())}")
        print(f"  - payment_schedule: {list(ps.keys())}")
        print(f"  - milestone fields: {list(ps['milestones'][0].keys())}")


class TestPaymentScheduleEndpointConsistency:
    """Test that GET /api/orders/{order_id}/payment-schedule matches accept_quote response"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.created_rfqs = []
        self.created_quotes = []
        self.created_orders = []
    
    def login(self, email, password):
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            return response.json()
        return None
    
    def create_rfq(self, title_suffix=""):
        unique_id = uuid.uuid4().hex[:8]
        rfq_data = {
            "title": f"TEST_Consistency_{title_suffix}_{unique_id}",
            "description": "Test RFQ for consistency testing",
            "material_type": "Titanium",
            "quantity": 25,
            "tolerance": 0.02,
            "deadline": "2026-05-01",
            "urgency": "high"
        }
        response = self.session.post(f"{BASE_URL}/api/rfqs", json=rfq_data)
        if response.status_code in [200, 201]:
            data = response.json()
            rfq_id = data.get("rfq_id") or data.get("id")
            self.created_rfqs.append(rfq_id)
            return rfq_id
        return None
    
    def submit_quote(self, rfq_id, payment_terms, payment_terms_notes=None, price=10000):
        quote_data = {
            "rfq_id": rfq_id,
            "material_cost": price * 0.4,
            "machining_cost": price * 0.6,
            "lead_time_days": 14,
            "proposed_payment_terms": payment_terms,
            "notes": "Test quotation"
        }
        if payment_terms_notes:
            quote_data["payment_terms_notes"] = payment_terms_notes
        
        response = self.session.post(f"{BASE_URL}/api/vendor/quotation", json=quote_data)
        if response.status_code in [200, 201]:
            data = response.json()
            quote_id = data.get("quote_id")
            self.created_quotes.append(quote_id)
            return quote_id, data
        return None, response.json() if response.status_code != 500 else {"error": response.text}
    
    def accept_quote(self, quote_id):
        response = self.session.post(f"{BASE_URL}/api/quotes/{quote_id}/accept")
        if response.status_code == 200:
            data = response.json()
            order_id = data.get("order_id")
            if order_id:
                self.created_orders.append(order_id)
            return data
        return {"error": response.text, "status_code": response.status_code}
    
    def get_payment_schedule(self, order_id):
        response = self.session.get(f"{BASE_URL}/api/orders/{order_id}/payment-schedule")
        if response.status_code == 200:
            return response.json()
        return {"error": response.text, "status_code": response.status_code}
    
    def test_get_schedule_matches_accept_response(self):
        """
        GET /api/orders/{order_id}/payment-schedule should return same milestones
        as accept_quote response
        """
        # Step 1: Login as buyer and create RFQ
        buyer = self.login(BUYER_EMAIL, BUYER_PASSWORD)
        assert buyer, "Failed to login as buyer"
        
        rfq_id = self.create_rfq("Consistency")
        assert rfq_id, "Failed to create RFQ"
        
        # Step 2: Login as vendor and submit quote
        vendor = self.login(VENDOR_EMAIL, VENDOR_PASSWORD)
        assert vendor, "Failed to login as vendor"
        
        quote_id, _ = self.submit_quote(
            rfq_id=rfq_id,
            payment_terms="custom",
            payment_terms_notes="20% advance, 30% after production, 50% on delivery",
            price=25000
        )
        assert quote_id, "Failed to submit quote"
        
        # Step 3: Login as buyer and accept quote
        buyer = self.login(BUYER_EMAIL, BUYER_PASSWORD)
        assert buyer, "Failed to login as buyer"
        
        accept_response = self.accept_quote(quote_id)
        assert "order_id" in accept_response, f"Failed to accept quote: {accept_response}"
        order_id = accept_response["order_id"]
        
        accept_milestones = accept_response["payment_schedule"]["milestones"]
        accept_percentages = [m["percentage"] for m in accept_milestones]
        accept_stages = [m["stage"] for m in accept_milestones]
        
        # Step 4: Get payment schedule via GET endpoint
        schedule_response = self.get_payment_schedule(order_id)
        assert "schedule" in schedule_response, f"Failed to get schedule: {schedule_response}"
        
        get_milestones = schedule_response["schedule"]["milestones"]
        get_percentages = [m["percentage"] for m in get_milestones]
        get_stages = [m["stage"] for m in get_milestones]
        
        # Verify consistency
        assert accept_percentages == get_percentages, f"Percentages mismatch: accept={accept_percentages}, get={get_percentages}"
        assert accept_stages == get_stages, f"Stages mismatch: accept={accept_stages}, get={get_stages}"
        
        print(f"PASS: GET payment-schedule matches accept_quote response")
        print(f"  - Percentages: {accept_percentages}")
        print(f"  - Stages: {accept_stages}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
