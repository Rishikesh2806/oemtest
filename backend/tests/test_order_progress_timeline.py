"""
Test Order Progress Timeline - Dynamic Payment Milestone Positioning
Tests the dynamic Order Progress timeline that adapts based on payment terms:
- Net 30: Payment appears at end (after delivered)
- 50/50: Payment split before production and before delivery
- Milestone 30/40/30: Payment steps interleaved at correct lifecycle positions
- Payment gate enforcement blocks status transitions
- Admin override bypasses payment gates
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@offoadex.com"
ADMIN_PASSWORD = "admin123"
VENDOR_EMAIL = "testvendor_nda@test.com"
VENDOR_PASSWORD = "vendor123"
TEST_ORDER_ID = "order_8d45a1ea88d1"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip(f"Admin login failed: {response.text}")
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def vendor_token():
    """Get vendor authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": VENDOR_EMAIL,
        "password": VENDOR_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip(f"Vendor login failed: {response.text}")
    return response.json()["access_token"]


class TestPaymentScheduleTypes:
    """Test different payment schedule types and their milestone positioning"""
    
    def test_get_current_order_schedule(self, admin_token):
        """Verify we can get the current payment schedule"""
        response = requests.get(
            f"{BASE_URL}/api/orders/{TEST_ORDER_ID}/payment-schedule",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "schedule" in data
        assert "milestones" in data["schedule"]
        print(f"Current schedule type: {data['schedule'].get('type')}")
        print(f"Milestones: {len(data['schedule']['milestones'])}")
    
    def test_set_net30_schedule(self, admin_token):
        """Test Net 30 schedule - payment appears at end (net_due stage)"""
        # Set Net 30 schedule
        response = requests.put(
            f"{BASE_URL}/api/admin/orders/{TEST_ORDER_ID}/payment-schedule",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "milestones": [
                    {"stage": "net_due", "label": "Payment Due (Net 30)", "percentage": 100}
                ]
            }
        )
        assert response.status_code == 200
        
        # Verify the schedule
        response = requests.get(
            f"{BASE_URL}/api/orders/{TEST_ORDER_ID}/payment-schedule",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        milestones = data["schedule"]["milestones"]
        
        assert len(milestones) == 1
        assert milestones[0]["stage"] == "net_due"
        assert milestones[0]["percentage"] == 100
        print("Net 30 schedule set successfully - payment at net_due stage (after delivered)")
    
    def test_set_50_50_schedule(self, admin_token):
        """Test 50/50 schedule - 50% advance, 50% on delivery"""
        response = requests.put(
            f"{BASE_URL}/api/admin/orders/{TEST_ORDER_ID}/payment-schedule",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "milestones": [
                    {"stage": "before_production", "label": "50% Advance", "percentage": 50},
                    {"stage": "after_dispatch", "label": "50% on Delivery", "percentage": 50}
                ]
            }
        )
        assert response.status_code == 200
        
        # Verify the schedule
        response = requests.get(
            f"{BASE_URL}/api/orders/{TEST_ORDER_ID}/payment-schedule",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        milestones = data["schedule"]["milestones"]
        
        assert len(milestones) == 2
        assert milestones[0]["stage"] == "before_production"
        assert milestones[0]["percentage"] == 50
        assert milestones[1]["stage"] == "after_dispatch"
        assert milestones[1]["percentage"] == 50
        print("50/50 schedule set successfully")
    
    def test_set_milestone_30_40_30_schedule(self, admin_token):
        """Test Milestone 30/40/30 schedule - interleaved at correct positions"""
        response = requests.put(
            f"{BASE_URL}/api/admin/orders/{TEST_ORDER_ID}/payment-schedule",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "milestones": [
                    {"stage": "before_production", "label": "30% Advance", "percentage": 30},
                    {"stage": "after_production", "label": "40% Post-Production", "percentage": 40},
                    {"stage": "after_inspection", "label": "30% Final", "percentage": 30}
                ]
            }
        )
        assert response.status_code == 200
        
        # Verify the schedule
        response = requests.get(
            f"{BASE_URL}/api/orders/{TEST_ORDER_ID}/payment-schedule",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        milestones = data["schedule"]["milestones"]
        
        assert len(milestones) == 3
        assert milestones[0]["stage"] == "before_production"
        assert milestones[0]["percentage"] == 30
        assert milestones[1]["stage"] == "after_production"
        assert milestones[1]["percentage"] == 40
        assert milestones[2]["stage"] == "after_inspection"
        assert milestones[2]["percentage"] == 30
        print("Milestone 30/40/30 schedule set successfully")
    
    def test_set_cash_on_delivery_schedule(self, admin_token):
        """Test Cash on Delivery schedule - payment at on_delivery stage"""
        response = requests.put(
            f"{BASE_URL}/api/admin/orders/{TEST_ORDER_ID}/payment-schedule",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "milestones": [
                    {"stage": "on_delivery", "label": "Payment on Delivery", "percentage": 100}
                ]
            }
        )
        assert response.status_code == 200
        
        # Verify the schedule
        response = requests.get(
            f"{BASE_URL}/api/orders/{TEST_ORDER_ID}/payment-schedule",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        milestones = data["schedule"]["milestones"]
        
        assert len(milestones) == 1
        assert milestones[0]["stage"] == "on_delivery"
        assert milestones[0]["percentage"] == 100
        print("Cash on Delivery schedule set successfully - payment at on_delivery stage")


class TestPaymentGateEnforcement:
    """Test payment gate enforcement blocks status transitions"""
    
    def test_payment_gate_blocks_status_transition(self, admin_token, vendor_token):
        """Test that unpaid milestone blocks status transition"""
        # First, set a schedule with before_production milestone
        requests.put(
            f"{BASE_URL}/api/admin/orders/{TEST_ORDER_ID}/payment-schedule",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "milestones": [
                    {"stage": "before_production", "label": "Advance Payment", "percentage": 100}
                ]
            }
        )
        
        # Reset order status to pending_payment
        requests.put(
            f"{BASE_URL}/api/orders/{TEST_ORDER_ID}/status",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"status": "pending_payment", "admin_override": True}
        )
        
        # Try to move to in_production without paying - should be blocked
        response = requests.put(
            f"{BASE_URL}/api/orders/{TEST_ORDER_ID}/status",
            headers={"Authorization": f"Bearer {vendor_token}"},
            json={"status": "in_production"}
        )
        
        # Should be blocked (400) because payment is required
        assert response.status_code == 400
        assert "Payment required" in response.json().get("detail", "")
        print("Payment gate correctly blocks status transition when milestone unpaid")
    
    def test_admin_override_bypasses_payment_gate(self, admin_token):
        """Test that admin can bypass payment gate with override"""
        # Set a schedule with before_production milestone
        requests.put(
            f"{BASE_URL}/api/admin/orders/{TEST_ORDER_ID}/payment-schedule",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "milestones": [
                    {"stage": "before_production", "label": "Advance Payment", "percentage": 100}
                ]
            }
        )
        
        # Reset order status to pending_payment
        requests.put(
            f"{BASE_URL}/api/orders/{TEST_ORDER_ID}/status",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"status": "pending_payment", "admin_override": True}
        )
        
        # Admin uses override to bypass payment gate
        response = requests.put(
            f"{BASE_URL}/api/orders/{TEST_ORDER_ID}/status",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"status": "in_production", "admin_override": True}
        )
        
        assert response.status_code == 200
        print("Admin override successfully bypasses payment gate")
    
    def test_milestone_is_due_calculation(self, admin_token):
        """Test that is_due is correctly calculated for milestones"""
        # Set milestone schedule
        requests.put(
            f"{BASE_URL}/api/admin/orders/{TEST_ORDER_ID}/payment-schedule",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "milestones": [
                    {"stage": "before_production", "label": "30% Advance", "percentage": 30},
                    {"stage": "after_production", "label": "40% Post-Production", "percentage": 40},
                    {"stage": "after_inspection", "label": "30% Final", "percentage": 30}
                ]
            }
        )
        
        # Set order to in_production (admin override)
        requests.put(
            f"{BASE_URL}/api/orders/{TEST_ORDER_ID}/status",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"status": "in_production", "admin_override": True}
        )
        
        # Get payment schedule - check is_due flags
        response = requests.get(
            f"{BASE_URL}/api/orders/{TEST_ORDER_ID}/payment-schedule",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        milestones = data["schedule"]["milestones"]
        
        # At in_production status:
        # - before_production milestone should be is_due=True (past due)
        # - after_production milestone should be is_due=True (current)
        # - after_inspection milestone should be is_due=False (not yet)
        
        assert milestones[0]["is_due"] == True, "before_production should be due"
        assert milestones[1]["is_due"] == True, "after_production should be due at in_production"
        assert milestones[2]["is_due"] == False, "after_inspection should not be due yet"
        print("is_due calculation correct for milestones based on order status")


class TestPaymentScheduleValidation:
    """Test payment schedule validation rules"""
    
    def test_percentages_must_sum_to_100(self, admin_token):
        """Test that milestone percentages must sum to 100"""
        response = requests.put(
            f"{BASE_URL}/api/admin/orders/{TEST_ORDER_ID}/payment-schedule",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "milestones": [
                    {"stage": "before_production", "label": "Advance", "percentage": 50},
                    {"stage": "after_production", "label": "Post-Production", "percentage": 30}
                ]
            }
        )
        assert response.status_code == 400
        assert "sum to 100" in response.json().get("detail", "").lower()
        print("Validation correctly rejects percentages not summing to 100")
    
    def test_invalid_stage_rejected(self, admin_token):
        """Test that invalid stage values are rejected"""
        response = requests.put(
            f"{BASE_URL}/api/admin/orders/{TEST_ORDER_ID}/payment-schedule",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "milestones": [
                    {"stage": "invalid_stage", "label": "Invalid", "percentage": 100}
                ]
            }
        )
        assert response.status_code == 400
        assert "invalid stage" in response.json().get("detail", "").lower()
        print("Validation correctly rejects invalid stage values")


class TestVendorStatusButtons:
    """Test vendor status update buttons based on order status"""
    
    def test_vendor_can_start_production_when_paid(self, admin_token, vendor_token):
        """Test vendor can start production when advance is paid"""
        # Set 100% advance schedule
        requests.put(
            f"{BASE_URL}/api/admin/orders/{TEST_ORDER_ID}/payment-schedule",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "milestones": [
                    {"stage": "before_production", "label": "Full Advance", "percentage": 100}
                ]
            }
        )
        
        # Reset to pending_payment
        requests.put(
            f"{BASE_URL}/api/orders/{TEST_ORDER_ID}/status",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"status": "pending_payment", "admin_override": True}
        )
        
        # Pay the milestone (as admin acting as buyer)
        response = requests.post(
            f"{BASE_URL}/api/orders/{TEST_ORDER_ID}/pay",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"milestone_id": "ms_1"}
        )
        assert response.status_code == 200
        
        # Now vendor should be able to start production
        response = requests.put(
            f"{BASE_URL}/api/orders/{TEST_ORDER_ID}/status",
            headers={"Authorization": f"Bearer {vendor_token}"},
            json={"status": "in_production"}
        )
        assert response.status_code == 200
        print("Vendor can start production after advance payment")


class TestCleanup:
    """Restore order to a known state after tests"""
    
    def test_restore_order_state(self, admin_token):
        """Restore order to milestone 30/40/30 schedule with pending_payment status"""
        # Set milestone 30/40/30 schedule
        response = requests.put(
            f"{BASE_URL}/api/admin/orders/{TEST_ORDER_ID}/payment-schedule",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "milestones": [
                    {"stage": "before_production", "label": "30% Advance", "percentage": 30},
                    {"stage": "after_production", "label": "40% Post-Production", "percentage": 40},
                    {"stage": "after_inspection", "label": "30% Final", "percentage": 30}
                ]
            }
        )
        assert response.status_code == 200
        
        # Reset to pending_payment
        response = requests.put(
            f"{BASE_URL}/api/orders/{TEST_ORDER_ID}/status",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"status": "pending_payment", "admin_override": True}
        )
        assert response.status_code == 200
        print("Order restored to milestone 30/40/30 schedule with pending_payment status")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
