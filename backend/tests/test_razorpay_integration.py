"""
Test Razorpay Integration for OEMLinker
Tests the new Razorpay payment endpoints:
- POST /api/payments/create-order - Create Razorpay order for milestone
- POST /api/payments/verify - Verify payment (validation errors only - real signature cannot be tested)
- POST /api/payments/webhook - Webhook endpoint
- POST /api/orders/{order_id}/pay - Admin-only manual payment override
- GET /api/orders/{order_id}/payment-schedule - Payment schedule retrieval
"""

import pytest
import requests
import os
import json

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
ADMIN_EMAIL = "admin@offoadex.com"
ADMIN_PASSWORD = "admin123"
BUYER_EMAIL = "visualbuyer@test.com"
BUYER_PASSWORD = "buyer123"
VENDOR_EMAIL = "testvendor_nda@test.com"
VENDOR_PASSWORD = "vendor123"

# Test order with pending milestones
TEST_ORDER_ID = "order_fa5d51ccb2ac"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def buyer_token():
    """Get buyer authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": BUYER_EMAIL,
        "password": BUYER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Buyer login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def vendor_token():
    """Get vendor authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": VENDOR_EMAIL,
        "password": VENDOR_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Vendor login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def test_order_with_milestones(admin_token):
    """Find or create an order with pending milestones for testing"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # First try the specified test order
    response = requests.get(f"{BASE_URL}/api/orders/{TEST_ORDER_ID}/payment-schedule", headers=headers)
    if response.status_code == 200:
        data = response.json()
        milestones = data.get("schedule", {}).get("milestones", [])
        pending = [m for m in milestones if m.get("status") == "pending"]
        if pending:
            return {"order_id": TEST_ORDER_ID, "milestone_id": pending[0]["milestone_id"], "schedule": data}
    
    # If not found, get any order with pending milestones
    response = requests.get(f"{BASE_URL}/api/orders", headers=headers)
    if response.status_code == 200:
        orders = response.json()
        for order in orders:
            order_id = order.get("order_id")
            sched_resp = requests.get(f"{BASE_URL}/api/orders/{order_id}/payment-schedule", headers=headers)
            if sched_resp.status_code == 200:
                sched_data = sched_resp.json()
                milestones = sched_data.get("schedule", {}).get("milestones", [])
                pending = [m for m in milestones if m.get("status") == "pending"]
                if pending:
                    return {"order_id": order_id, "milestone_id": pending[0]["milestone_id"], "schedule": sched_data}
    
    pytest.skip("No order with pending milestones found for testing")


class TestPaymentScheduleEndpoint:
    """Tests for GET /api/orders/{order_id}/payment-schedule"""
    
    def test_get_payment_schedule_as_admin(self, admin_token, test_order_with_milestones):
        """Admin can retrieve payment schedule"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        order_id = test_order_with_milestones["order_id"]
        
        response = requests.get(f"{BASE_URL}/api/orders/{order_id}/payment-schedule", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "order_id" in data
        assert "total_amount" in data
        assert "currency" in data
        assert "schedule" in data
        assert "milestones" in data["schedule"]
        
        # Verify milestones have required fields
        milestones = data["schedule"]["milestones"]
        assert len(milestones) > 0, "Expected at least one milestone"
        
        for ms in milestones:
            assert "milestone_id" in ms
            assert "label" in ms
            assert "percentage" in ms
            assert "amount" in ms
            assert "status" in ms
        
        print(f"Payment schedule retrieved: {len(milestones)} milestones, total={data['total_amount']} {data['currency']}")
    
    def test_get_payment_schedule_unauthorized(self):
        """Unauthenticated request should fail"""
        response = requests.get(f"{BASE_URL}/api/orders/{TEST_ORDER_ID}/payment-schedule")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    
    def test_get_payment_schedule_nonexistent_order(self, admin_token):
        """Non-existent order should return 404"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/orders/nonexistent_order_xyz/payment-schedule", headers=headers)
        assert response.status_code == 404


class TestCreateRazorpayOrder:
    """Tests for POST /api/payments/create-order"""
    
    def test_create_order_missing_fields(self, buyer_token):
        """Should reject request with missing fields"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        
        # Missing milestone_id
        response = requests.post(f"{BASE_URL}/api/payments/create-order", 
            headers=headers, 
            json={"order_id": TEST_ORDER_ID}
        )
        assert response.status_code == 400
        assert "milestone_id" in response.json().get("detail", "").lower() or "required" in response.json().get("detail", "").lower()
        
        # Missing order_id
        response = requests.post(f"{BASE_URL}/api/payments/create-order", 
            headers=headers, 
            json={"milestone_id": "ms_1"}
        )
        assert response.status_code == 400
        print("Create order correctly rejects missing fields")
    
    def test_create_order_nonexistent_order(self, buyer_token):
        """Should reject for non-existent order"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        
        response = requests.post(f"{BASE_URL}/api/payments/create-order", 
            headers=headers, 
            json={"order_id": "nonexistent_order", "milestone_id": "ms_1"}
        )
        assert response.status_code == 404
        print("Create order correctly rejects non-existent order")
    
    def test_create_order_vendor_forbidden(self, vendor_token, test_order_with_milestones):
        """Vendor should not be able to create payment order"""
        headers = {"Authorization": f"Bearer {vendor_token}"}
        order_id = test_order_with_milestones["order_id"]
        milestone_id = test_order_with_milestones["milestone_id"]
        
        response = requests.post(f"{BASE_URL}/api/payments/create-order", 
            headers=headers, 
            json={"order_id": order_id, "milestone_id": milestone_id}
        )
        # Vendor is not buyer or admin, should be forbidden
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("Create order correctly forbids vendor access")
    
    def test_create_order_success_structure(self, admin_token, test_order_with_milestones):
        """Admin can create Razorpay order - verify response structure"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        order_id = test_order_with_milestones["order_id"]
        milestone_id = test_order_with_milestones["milestone_id"]
        
        response = requests.post(f"{BASE_URL}/api/payments/create-order", 
            headers=headers, 
            json={"order_id": order_id, "milestone_id": milestone_id}
        )
        
        # This should succeed if Razorpay is configured
        if response.status_code == 500 and "not configured" in response.json().get("detail", "").lower():
            pytest.skip("Razorpay not configured on server")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "razorpay_order_id" in data, "Missing razorpay_order_id"
        assert "amount" in data, "Missing amount"
        assert "currency" in data, "Missing currency"
        assert "key_id" in data, "Missing key_id"
        assert "milestone" in data, "Missing milestone"
        assert "prefill" in data, "Missing prefill"
        assert "order_ref" in data, "Missing order_ref"
        
        # Verify milestone details
        assert data["milestone"]["milestone_id"] == milestone_id
        assert "label" in data["milestone"]
        assert "amount" in data["milestone"]
        assert "percentage" in data["milestone"]
        
        # Verify amount is in paise (integer)
        assert isinstance(data["amount"], int), "Amount should be in paise (integer)"
        
        # Verify key_id matches expected
        assert data["key_id"] == "rzp_live_SW8TUyI589xgT6", f"Unexpected key_id: {data['key_id']}"
        
        print(f"Razorpay order created: {data['razorpay_order_id']}, amount={data['amount']} paise")


class TestVerifyRazorpayPayment:
    """Tests for POST /api/payments/verify"""
    
    def test_verify_missing_fields(self, buyer_token):
        """Should reject request with missing fields"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        
        # Missing all required fields
        response = requests.post(f"{BASE_URL}/api/payments/verify", 
            headers=headers, 
            json={}
        )
        assert response.status_code == 400
        assert "missing" in response.json().get("detail", "").lower() or "required" in response.json().get("detail", "").lower()
        
        # Missing signature
        response = requests.post(f"{BASE_URL}/api/payments/verify", 
            headers=headers, 
            json={
                "razorpay_order_id": "order_test",
                "razorpay_payment_id": "pay_test",
                "order_id": TEST_ORDER_ID,
                "milestone_id": "ms_1"
            }
        )
        assert response.status_code == 400
        print("Verify payment correctly rejects missing fields")
    
    def test_verify_invalid_signature(self, buyer_token, test_order_with_milestones):
        """Should reject invalid signature"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        order_id = test_order_with_milestones["order_id"]
        milestone_id = test_order_with_milestones["milestone_id"]
        
        response = requests.post(f"{BASE_URL}/api/payments/verify", 
            headers=headers, 
            json={
                "razorpay_order_id": "order_fake123",
                "razorpay_payment_id": "pay_fake456",
                "razorpay_signature": "invalid_signature_abc123",
                "order_id": order_id,
                "milestone_id": milestone_id
            }
        )
        
        # Should fail signature verification
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        assert "signature" in response.json().get("detail", "").lower()
        print("Verify payment correctly rejects invalid signature")


class TestRazorpayWebhook:
    """Tests for POST /api/payments/webhook"""
    
    def test_webhook_accepts_post(self):
        """Webhook should accept POST requests"""
        # Send a minimal valid payload
        payload = {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_test123",
                        "order_id": "order_test123"
                    }
                }
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/payments/webhook", json=payload)
        
        # Should return ok (webhook secret not configured, so no signature check)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("status") == "ok"
        print("Webhook accepts POST and returns {status: 'ok'}")
    
    def test_webhook_invalid_json(self):
        """Webhook should reject invalid JSON"""
        response = requests.post(
            f"{BASE_URL}/api/payments/webhook", 
            data="not valid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 400
        print("Webhook correctly rejects invalid JSON")


class TestAdminPaymentOverride:
    """Tests for POST /api/orders/{order_id}/pay - Admin-only endpoint"""
    
    def test_buyer_forbidden(self, buyer_token, test_order_with_milestones):
        """Buyer should be rejected with 403"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        order_id = test_order_with_milestones["order_id"]
        milestone_id = test_order_with_milestones["milestone_id"]
        
        response = requests.post(f"{BASE_URL}/api/orders/{order_id}/pay", 
            headers=headers, 
            json={"milestone_id": milestone_id}
        )
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        detail = response.json().get("detail", "")
        assert "admin" in detail.lower() or "razorpay" in detail.lower()
        print(f"Buyer correctly rejected: {detail}")
    
    def test_vendor_forbidden(self, vendor_token, test_order_with_milestones):
        """Vendor should be rejected with 403"""
        headers = {"Authorization": f"Bearer {vendor_token}"}
        order_id = test_order_with_milestones["order_id"]
        milestone_id = test_order_with_milestones["milestone_id"]
        
        response = requests.post(f"{BASE_URL}/api/orders/{order_id}/pay", 
            headers=headers, 
            json={"milestone_id": milestone_id}
        )
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("Vendor correctly rejected from admin pay endpoint")
    
    def test_admin_missing_milestone_id(self, admin_token, test_order_with_milestones):
        """Admin request without milestone_id should fail"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        order_id = test_order_with_milestones["order_id"]
        
        response = requests.post(f"{BASE_URL}/api/orders/{order_id}/pay", 
            headers=headers, 
            json={}
        )
        
        assert response.status_code == 400
        assert "milestone_id" in response.json().get("detail", "").lower()
        print("Admin pay correctly requires milestone_id")
    
    def test_admin_nonexistent_order(self, admin_token):
        """Admin request for non-existent order should fail"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.post(f"{BASE_URL}/api/orders/nonexistent_order_xyz/pay", 
            headers=headers, 
            json={"milestone_id": "ms_1"}
        )
        
        assert response.status_code == 404
        print("Admin pay correctly rejects non-existent order")


class TestRazorpayKeyConfiguration:
    """Verify Razorpay key is correctly configured"""
    
    def test_razorpay_key_in_create_order_response(self, admin_token, test_order_with_milestones):
        """Verify the correct Razorpay key is returned"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        order_id = test_order_with_milestones["order_id"]
        milestone_id = test_order_with_milestones["milestone_id"]
        
        response = requests.post(f"{BASE_URL}/api/payments/create-order", 
            headers=headers, 
            json={"order_id": order_id, "milestone_id": milestone_id}
        )
        
        if response.status_code == 500 and "not configured" in response.json().get("detail", "").lower():
            pytest.skip("Razorpay not configured")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify the live key is being used
        assert data["key_id"] == "rzp_live_SW8TUyI589xgT6", f"Expected live key, got: {data['key_id']}"
        print(f"Razorpay key verified: {data['key_id']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
