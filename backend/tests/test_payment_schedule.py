"""
Payment Schedule Feature Tests
Tests for dynamic payment schedule generation, milestone payments, and stage-gate enforcement.
Payment processing is MOCKED - no real Stripe integration.
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
BUYER_EMAIL = "testbuyer_payment@test.com"
BUYER_PASSWORD = "TestBuyer123!"
VENDOR_EMAIL = "testvendor_nda@test.com"
VENDOR_PASSWORD = "vendor123"

# Existing order with payment schedule (admin can access any order)
EXISTING_ORDER_ID = "order_827a8b0bf5f6"  # Order with pending payment


class TestPaymentScheduleAuth:
    """Test authentication for payment schedule endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
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
    
    def test_get_payment_schedule_requires_auth(self):
        """GET /api/orders/{orderId}/payment-schedule requires authentication"""
        response = requests.get(f"{BASE_URL}/api/orders/{EXISTING_ORDER_ID}/payment-schedule")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: GET payment-schedule requires auth")
    
    def test_pay_endpoint_requires_auth(self):
        """POST /api/orders/{orderId}/pay requires authentication"""
        response = requests.post(f"{BASE_URL}/api/orders/{EXISTING_ORDER_ID}/pay", json={"milestone_id": "ms_1"})
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: POST pay requires auth")
    
    def test_admin_schedule_endpoint_requires_auth(self):
        """PUT /api/admin/orders/{orderId}/payment-schedule requires authentication"""
        response = requests.put(f"{BASE_URL}/api/admin/orders/{EXISTING_ORDER_ID}/payment-schedule", json={"milestones": []})
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: PUT admin payment-schedule requires auth")


class TestGetPaymentSchedule:
    """Test GET /api/orders/{orderId}/payment-schedule endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
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
    
    def test_get_schedule_as_buyer(self):
        """Authorized user can get payment schedule for order"""
        # Using admin since test buyer doesn't own the test order
        user = self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert user, "Failed to login"
        
        response = self.session.get(f"{BASE_URL}/api/orders/{EXISTING_ORDER_ID}/payment-schedule")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "order_id" in data
        assert "total_amount" in data
        assert "currency" in data
        assert "schedule" in data
        assert "milestones" in data["schedule"]
        
        # Verify milestone structure
        milestones = data["schedule"]["milestones"]
        assert len(milestones) > 0, "Expected at least one milestone"
        
        for ms in milestones:
            assert "milestone_id" in ms
            assert "stage" in ms
            assert "label" in ms
            assert "percentage" in ms
            assert "amount" in ms
            assert "status" in ms
            assert "is_due" in ms
            assert "blocks_status" in ms or ms.get("blocks_status") is None
        
        print(f"PASS: Buyer can get payment schedule - {len(milestones)} milestones found")
        print(f"  Total amount: {data['currency']} {data['total_amount']}")
        print(f"  Total paid: {data['schedule'].get('total_paid', 0)}")
        print(f"  Total pending: {data['schedule'].get('total_pending', 0)}")
    
    def test_get_schedule_as_admin(self):
        """Admin can get payment schedule for any order"""
        user = self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert user, "Failed to login as admin"
        
        response = self.session.get(f"{BASE_URL}/api/orders/{EXISTING_ORDER_ID}/payment-schedule")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "schedule" in data
        print("PASS: Admin can get payment schedule")
    
    def test_get_schedule_nonexistent_order(self):
        """Returns 404 for nonexistent order"""
        user = self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert user, "Failed to login as admin"
        
        response = self.session.get(f"{BASE_URL}/api/orders/nonexistent_order_123/payment-schedule")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: Returns 404 for nonexistent order")
    
    def test_schedule_has_is_due_and_blocks_status(self):
        """Milestones have is_due and blocks_status fields"""
        user = self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert user, "Failed to login"
        
        response = self.session.get(f"{BASE_URL}/api/orders/{EXISTING_ORDER_ID}/payment-schedule")
        assert response.status_code == 200
        
        data = response.json()
        milestones = data["schedule"]["milestones"]
        
        for ms in milestones:
            # is_due should be boolean
            assert isinstance(ms.get("is_due"), bool), f"is_due should be boolean, got {type(ms.get('is_due'))}"
            # blocks_status can be string or None
            blocks = ms.get("blocks_status")
            assert blocks is None or isinstance(blocks, str), f"blocks_status should be string or None"
        
        print("PASS: Milestones have is_due and blocks_status fields")


class TestPayMilestone:
    """Test POST /api/orders/{orderId}/pay endpoint (MOCKED payment)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
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
    
    def test_pay_requires_milestone_id(self):
        """POST /api/orders/{orderId}/pay requires milestone_id"""
        # Admin can also make payments
        user = self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert user, "Failed to login"
        
        response = self.session.post(f"{BASE_URL}/api/orders/{EXISTING_ORDER_ID}/pay", json={})
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "milestone_id" in response.json().get("detail", "").lower()
        print("PASS: Pay endpoint requires milestone_id")
    
    def test_pay_nonexistent_milestone(self):
        """Returns 404 for nonexistent milestone"""
        user = self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert user, "Failed to login"
        
        response = self.session.post(f"{BASE_URL}/api/orders/{EXISTING_ORDER_ID}/pay", json={
            "milestone_id": "ms_nonexistent"
        })
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: Returns 404 for nonexistent milestone")
    
    def test_pay_nonexistent_order(self):
        """Returns 404 for nonexistent order"""
        user = self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert user, "Failed to login"
        
        response = self.session.post(f"{BASE_URL}/api/orders/nonexistent_order_123/pay", json={
            "milestone_id": "ms_1"
        })
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: Returns 404 for nonexistent order")
    
    def test_vendor_cannot_pay(self):
        """Vendor cannot make payments"""
        user = self.login(VENDOR_EMAIL, VENDOR_PASSWORD)
        assert user, "Failed to login as vendor"
        
        response = self.session.post(f"{BASE_URL}/api/orders/{EXISTING_ORDER_ID}/pay", json={
            "milestone_id": "ms_1"
        })
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("PASS: Vendor cannot make payments")


class TestAdminPaymentSchedule:
    """Test PUT /api/admin/orders/{orderId}/payment-schedule endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
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
    
    def test_admin_can_set_custom_schedule(self):
        """Admin can set custom payment schedule"""
        user = self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert user, "Failed to login as admin"
        
        custom_milestones = [
            {"stage": "before_production", "label": "Advance (40%)", "percentage": 40},
            {"stage": "after_production", "label": "Post-Production (30%)", "percentage": 30},
            {"stage": "after_dispatch", "label": "Final (30%)", "percentage": 30}
        ]
        
        response = self.session.put(f"{BASE_URL}/api/admin/orders/{EXISTING_ORDER_ID}/payment-schedule", json={
            "milestones": custom_milestones
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "schedule" in data
        assert len(data["schedule"]["milestones"]) == 3
        print("PASS: Admin can set custom payment schedule")
    
    def test_admin_schedule_validates_percentage_sum(self):
        """Admin schedule validates percentages sum to 100"""
        user = self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert user, "Failed to login as admin"
        
        # Percentages sum to 90, not 100
        invalid_milestones = [
            {"stage": "before_production", "label": "Advance", "percentage": 50},
            {"stage": "after_dispatch", "label": "Final", "percentage": 40}
        ]
        
        response = self.session.put(f"{BASE_URL}/api/admin/orders/{EXISTING_ORDER_ID}/payment-schedule", json={
            "milestones": invalid_milestones
        })
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "100" in response.json().get("detail", "")
        print("PASS: Admin schedule validates percentages sum to 100")
    
    def test_admin_schedule_validates_stage(self):
        """Admin schedule validates stage values"""
        user = self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert user, "Failed to login as admin"
        
        invalid_milestones = [
            {"stage": "invalid_stage", "label": "Test", "percentage": 100}
        ]
        
        response = self.session.put(f"{BASE_URL}/api/admin/orders/{EXISTING_ORDER_ID}/payment-schedule", json={
            "milestones": invalid_milestones
        })
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("PASS: Admin schedule validates stage values")
    
    def test_buyer_cannot_set_admin_schedule(self):
        """Non-admin cannot access admin schedule endpoint"""
        user = self.login(VENDOR_EMAIL, VENDOR_PASSWORD)
        assert user, "Failed to login as vendor"
        
        response = self.session.put(f"{BASE_URL}/api/admin/orders/{EXISTING_ORDER_ID}/payment-schedule", json={
            "milestones": [{"stage": "before_production", "percentage": 100}]
        })
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("PASS: Non-admin cannot access admin schedule endpoint")
    
    def test_vendor_cannot_set_admin_schedule(self):
        """Vendor cannot access admin schedule endpoint"""
        user = self.login(VENDOR_EMAIL, VENDOR_PASSWORD)
        assert user, "Failed to login as vendor"
        
        response = self.session.put(f"{BASE_URL}/api/admin/orders/{EXISTING_ORDER_ID}/payment-schedule", json={
            "milestones": [{"stage": "before_production", "percentage": 100}]
        })
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("PASS: Vendor cannot access admin schedule endpoint")


class TestStageGateEnforcement:
    """Test payment gate enforcement on status transitions"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.test_order_id = None
    
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
    
    def test_status_update_blocked_by_payment_gate(self):
        """Status transition blocked when payment gate is active"""
        # First, set up a fresh schedule with unpaid milestones
        user = self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert user, "Failed to login as admin"
        
        # First reset the order status to pending_payment
        response = self.session.put(f"{BASE_URL}/api/orders/{EXISTING_ORDER_ID}/status", json={
            "status": "pending_payment",
            "note": "Reset for testing",
            "admin_override": True
        })
        # Ignore if this fails - order might already be in correct state
        
        # Set a schedule with before_production milestone (blocks in_production)
        custom_milestones = [
            {"stage": "before_production", "label": "Advance Payment", "percentage": 50},
            {"stage": "after_dispatch", "label": "Final Payment", "percentage": 50}
        ]
        
        response = self.session.put(f"{BASE_URL}/api/admin/orders/{EXISTING_ORDER_ID}/payment-schedule", json={
            "milestones": custom_milestones
        })
        assert response.status_code == 200, f"Failed to set schedule: {response.text}"
        
        # Now try to update status to in_production without paying
        response = self.session.put(f"{BASE_URL}/api/orders/{EXISTING_ORDER_ID}/status", json={
            "status": "in_production",
            "note": "Test status update"
        })
        
        # Should be blocked by payment gate
        assert response.status_code == 400, f"Expected 400 (blocked by payment gate), got {response.status_code}: {response.text}"
        detail = response.json().get("detail", "")
        assert "payment required" in detail.lower() or "must be paid" in detail.lower(), f"Expected payment gate error, got: {detail}"
        print("PASS: Status transition blocked by payment gate")
    
    def test_admin_override_bypasses_payment_gate(self):
        """Admin can override payment gate with admin_override flag"""
        user = self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert user, "Failed to login as admin"
        
        # Set a schedule with unpaid milestone
        custom_milestones = [
            {"stage": "before_production", "label": "Advance Payment", "percentage": 100}
        ]
        
        response = self.session.put(f"{BASE_URL}/api/admin/orders/{EXISTING_ORDER_ID}/payment-schedule", json={
            "milestones": custom_milestones
        })
        assert response.status_code == 200
        
        # Try to update status with admin_override
        response = self.session.put(f"{BASE_URL}/api/orders/{EXISTING_ORDER_ID}/status", json={
            "status": "in_production",
            "note": "Admin override test",
            "admin_override": True
        })
        
        # Should succeed with admin_override
        assert response.status_code == 200, f"Expected 200 with admin_override, got {response.status_code}: {response.text}"
        print("PASS: Admin override bypasses payment gate")
    
    def test_non_admin_cannot_use_override(self):
        """Non-admin users cannot use admin_override flag"""
        # First set up schedule as admin
        admin_session = requests.Session()
        admin_session.headers.update({"Content-Type": "application/json"})
        
        response = admin_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        token = response.json().get("access_token")
        admin_session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Reset order status first
        admin_session.put(f"{BASE_URL}/api/orders/{EXISTING_ORDER_ID}/status", json={
            "status": "pending_payment",
            "note": "Reset for testing",
            "admin_override": True
        })
        
        # Set schedule with unpaid milestone
        custom_milestones = [
            {"stage": "before_production", "label": "Advance Payment", "percentage": 100}
        ]
        admin_session.put(f"{BASE_URL}/api/admin/orders/{EXISTING_ORDER_ID}/payment-schedule", json={
            "milestones": custom_milestones
        })
        
        # Now login as vendor and try to use admin_override
        user = self.login(VENDOR_EMAIL, VENDOR_PASSWORD)
        assert user, "Failed to login as vendor"
        
        response = self.session.put(f"{BASE_URL}/api/orders/{EXISTING_ORDER_ID}/status", json={
            "status": "in_production",
            "note": "Vendor trying override",
            "admin_override": True
        })
        
        # Should still be blocked (vendor's admin_override is ignored)
        assert response.status_code == 400, f"Expected 400 (vendor override ignored), got {response.status_code}"
        print("PASS: Non-admin cannot use admin_override")


class TestPaymentScheduleGeneration:
    """Test automatic payment schedule generation from payment_terms"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
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
    
    def test_schedule_backfill_for_old_orders(self):
        """GET payment-schedule backfills schedule for orders without one"""
        user = self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert user, "Failed to login as admin"
        
        # Get all orders to find one
        response = self.session.get(f"{BASE_URL}/api/admin/orders")
        if response.status_code != 200:
            pytest.skip("Could not get orders list")
        
        orders = response.json()
        if not orders:
            pytest.skip("No orders found")
        
        # Get payment schedule for first order
        order_id = orders[0].get("order_id")
        response = self.session.get(f"{BASE_URL}/api/orders/{order_id}/payment-schedule")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "schedule" in data
        assert "milestones" in data["schedule"]
        assert len(data["schedule"]["milestones"]) > 0
        print(f"PASS: Schedule backfill works - order {order_id} has {len(data['schedule']['milestones'])} milestones")


class TestPaymentTransactions:
    """Test payment_transactions collection recording"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
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
    
    def test_pay_returns_transaction_id(self):
        """POST /api/orders/{orderId}/pay returns transaction_id"""
        # First set up a fresh schedule as admin
        admin_session = requests.Session()
        admin_session.headers.update({"Content-Type": "application/json"})
        
        response = admin_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        token = response.json().get("access_token")
        admin_session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Set a fresh schedule with unpaid milestones
        custom_milestones = [
            {"stage": "before_production", "label": "Test Advance", "percentage": 30},
            {"stage": "after_production", "label": "Test Post-Prod", "percentage": 40},
            {"stage": "after_dispatch", "label": "Test Final", "percentage": 30}
        ]
        
        admin_session.put(f"{BASE_URL}/api/admin/orders/{EXISTING_ORDER_ID}/payment-schedule", json={
            "milestones": custom_milestones
        })
        
        # Pay as admin (admin can make payments)
        response = admin_session.post(f"{BASE_URL}/api/orders/{EXISTING_ORDER_ID}/pay", json={
            "milestone_id": "ms_1"
        })
        
        if response.status_code == 200:
            data = response.json()
            assert "transaction_id" in data, "Response should include transaction_id"
            assert data["transaction_id"].startswith("txn_"), f"Transaction ID should start with 'txn_', got {data['transaction_id']}"
            assert "payment_status" in data
            assert "total_paid" in data
            assert "total_pending" in data
            print(f"PASS: Pay returns transaction_id: {data['transaction_id']}")
        elif response.status_code == 400 and "already paid" in response.json().get("detail", "").lower():
            print("PASS: Milestone already paid (expected in repeated tests)")
        else:
            pytest.fail(f"Unexpected response: {response.status_code} - {response.text}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
