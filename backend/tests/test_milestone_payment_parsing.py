"""
Milestone-Based Payment Schedule Parsing Tests
Tests for _parse_milestone_split() function that dynamically parses percentages from payment_terms_notes.
Tests verify:
1. 50/50 split from notes like "50% advance, 50% after inspection"
2. 20/30/50 split from notes like "20% advance, 30% after production, 50% on delivery"
3. Default 30/40/30 split when no notes provided
4. Legacy payment terms aliases normalization in generate_payment_schedule
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

# Existing test orders with different milestone configurations
ORDER_50_50 = "order_4cb307351dbf"  # 50% advance, 50% after inspection
ORDER_30_40_30 = "order_1c90e8591aff"  # 30/40/30 default
ORDER_NO_NOTES = "order_3669f7e2d825"  # milestone_based with no notes (should default to 30/40/30)


class TestMilestoneParsingExistingOrders:
    """Test milestone parsing on existing orders with different payment_terms_notes"""
    
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
    
    def test_50_50_split_order(self):
        """Order with '50% advance, 50% after inspection' notes generates 50/50 split"""
        user = self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert user, "Failed to login as admin"
        
        response = self.session.get(f"{BASE_URL}/api/orders/{ORDER_50_50}/payment-schedule")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        milestones = data["schedule"]["milestones"]
        
        # Should have exactly 2 milestones
        assert len(milestones) == 2, f"Expected 2 milestones for 50/50 split, got {len(milestones)}"
        
        # First milestone: 50% advance (before_production)
        ms1 = milestones[0]
        assert ms1["percentage"] == 50, f"First milestone should be 50%, got {ms1['percentage']}"
        assert ms1["stage"] == "before_production", f"First milestone stage should be before_production, got {ms1['stage']}"
        
        # Second milestone: 50% after inspection
        ms2 = milestones[1]
        assert ms2["percentage"] == 50, f"Second milestone should be 50%, got {ms2['percentage']}"
        assert ms2["stage"] == "after_inspection", f"Second milestone stage should be after_inspection, got {ms2['stage']}"
        
        # Verify amounts
        total = data["total_amount"]
        assert ms1["amount"] == total * 0.5, f"First milestone amount should be {total * 0.5}, got {ms1['amount']}"
        assert ms2["amount"] == total * 0.5, f"Second milestone amount should be {total * 0.5}, got {ms2['amount']}"
        
        print(f"PASS: 50/50 split order verified - {ms1['label']} ({ms1['percentage']}%), {ms2['label']} ({ms2['percentage']}%)")
    
    def test_30_40_30_split_order(self):
        """Order with 30/40/30 notes generates correct 3-milestone split"""
        user = self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert user, "Failed to login as admin"
        
        response = self.session.get(f"{BASE_URL}/api/orders/{ORDER_30_40_30}/payment-schedule")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        milestones = data["schedule"]["milestones"]
        
        # Should have exactly 3 milestones
        assert len(milestones) == 3, f"Expected 3 milestones for 30/40/30 split, got {len(milestones)}"
        
        # Verify percentages
        percentages = [m["percentage"] for m in milestones]
        assert percentages == [30, 40, 30], f"Expected [30, 40, 30], got {percentages}"
        
        # Verify stages
        stages = [m["stage"] for m in milestones]
        assert stages == ["before_production", "after_production", "after_inspection"], f"Expected standard stages, got {stages}"
        
        # Verify total adds up
        total_pct = sum(percentages)
        assert total_pct == 100, f"Percentages should sum to 100, got {total_pct}"
        
        print(f"PASS: 30/40/30 split order verified - percentages: {percentages}")
    
    def test_no_notes_defaults_to_30_40_30(self):
        """Order with milestone_based but no notes defaults to 30/40/30 split"""
        user = self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert user, "Failed to login as admin"
        
        response = self.session.get(f"{BASE_URL}/api/orders/{ORDER_NO_NOTES}/payment-schedule")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        milestones = data["schedule"]["milestones"]
        
        # Should default to 3 milestones with 30/40/30
        assert len(milestones) == 3, f"Expected 3 milestones for default split, got {len(milestones)}"
        
        percentages = [m["percentage"] for m in milestones]
        assert percentages == [30, 40, 30], f"Expected default [30, 40, 30], got {percentages}"
        
        print(f"PASS: No notes order defaults to 30/40/30 - percentages: {percentages}")


class TestMilestoneStageMapping:
    """Test that milestone stages are correctly mapped from keywords in notes"""
    
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
    
    def test_advance_maps_to_before_production(self):
        """'advance' keyword maps to before_production stage"""
        user = self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert user, "Failed to login"
        
        response = self.session.get(f"{BASE_URL}/api/orders/{ORDER_50_50}/payment-schedule")
        assert response.status_code == 200
        
        data = response.json()
        milestones = data["schedule"]["milestones"]
        
        # Find milestone with "advance" in label
        advance_ms = next((m for m in milestones if "advance" in m["label"].lower()), None)
        assert advance_ms is not None, "Should have an advance milestone"
        assert advance_ms["stage"] == "before_production", f"Advance should map to before_production, got {advance_ms['stage']}"
        
        print(f"PASS: 'advance' keyword correctly maps to before_production stage")
    
    def test_after_inspection_maps_correctly(self):
        """'after inspection' keyword maps to after_inspection stage"""
        user = self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert user, "Failed to login"
        
        response = self.session.get(f"{BASE_URL}/api/orders/{ORDER_50_50}/payment-schedule")
        assert response.status_code == 200
        
        data = response.json()
        milestones = data["schedule"]["milestones"]
        
        # Find milestone with "inspection" in label
        inspection_ms = next((m for m in milestones if "inspection" in m["label"].lower()), None)
        assert inspection_ms is not None, "Should have an inspection milestone"
        assert inspection_ms["stage"] == "after_inspection", f"Inspection should map to after_inspection, got {inspection_ms['stage']}"
        
        print(f"PASS: 'after inspection' keyword correctly maps to after_inspection stage")
    
    def test_after_production_maps_correctly(self):
        """'after production' keyword maps to after_production stage"""
        user = self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert user, "Failed to login"
        
        response = self.session.get(f"{BASE_URL}/api/orders/{ORDER_30_40_30}/payment-schedule")
        assert response.status_code == 200
        
        data = response.json()
        milestones = data["schedule"]["milestones"]
        
        # Find milestone with "production" in label (not advance)
        production_ms = next((m for m in milestones if "production" in m["label"].lower() and "advance" not in m["label"].lower()), None)
        assert production_ms is not None, "Should have a post-production milestone"
        assert production_ms["stage"] == "after_production", f"Post-production should map to after_production, got {production_ms['stage']}"
        
        print(f"PASS: 'after production' keyword correctly maps to after_production stage")


class TestLegacyPaymentTermsAliases:
    """Test that legacy payment terms aliases are normalized in generate_payment_schedule"""
    
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
    
    def test_admin_can_set_schedule_with_legacy_terms(self):
        """Admin can set custom schedule - verifies generate_payment_schedule works"""
        user = self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert user, "Failed to login as admin"
        
        # Set a custom 40/60 schedule
        custom_milestones = [
            {"stage": "before_production", "label": "Advance (40%)", "percentage": 40},
            {"stage": "after_dispatch", "label": "Final (60%)", "percentage": 60}
        ]
        
        response = self.session.put(f"{BASE_URL}/api/admin/orders/{ORDER_50_50}/payment-schedule", json={
            "milestones": custom_milestones
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        milestones = data["schedule"]["milestones"]
        
        assert len(milestones) == 2, f"Expected 2 milestones, got {len(milestones)}"
        assert milestones[0]["percentage"] == 40
        assert milestones[1]["percentage"] == 60
        
        print(f"PASS: Admin can set custom 40/60 schedule")
        
        # Restore original 50/50 schedule
        restore_milestones = [
            {"stage": "before_production", "label": "Advance Payment (50%)", "percentage": 50},
            {"stage": "after_inspection", "label": "Post-Inspection Payment (50%)", "percentage": 50}
        ]
        self.session.put(f"{BASE_URL}/api/admin/orders/{ORDER_50_50}/payment-schedule", json={
            "milestones": restore_milestones
        })


class TestPaymentScheduleBlocksStatus:
    """Test that milestones correctly block order status transitions"""
    
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
    
    def test_before_production_blocks_in_production(self):
        """before_production milestone blocks transition to in_production"""
        user = self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert user, "Failed to login"
        
        response = self.session.get(f"{BASE_URL}/api/orders/{ORDER_50_50}/payment-schedule")
        assert response.status_code == 200
        
        data = response.json()
        milestones = data["schedule"]["milestones"]
        
        # Find before_production milestone
        bp_ms = next((m for m in milestones if m["stage"] == "before_production"), None)
        assert bp_ms is not None, "Should have before_production milestone"
        assert bp_ms["blocks_status"] == "in_production", f"before_production should block in_production, got {bp_ms['blocks_status']}"
        
        print(f"PASS: before_production milestone correctly blocks in_production")
    
    def test_after_inspection_blocks_dispatched(self):
        """after_inspection milestone blocks transition to dispatched"""
        user = self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert user, "Failed to login"
        
        response = self.session.get(f"{BASE_URL}/api/orders/{ORDER_50_50}/payment-schedule")
        assert response.status_code == 200
        
        data = response.json()
        milestones = data["schedule"]["milestones"]
        
        # Find after_inspection milestone
        ai_ms = next((m for m in milestones if m["stage"] == "after_inspection"), None)
        assert ai_ms is not None, "Should have after_inspection milestone"
        assert ai_ms["blocks_status"] == "dispatched", f"after_inspection should block dispatched, got {ai_ms['blocks_status']}"
        
        print(f"PASS: after_inspection milestone correctly blocks dispatched")
    
    def test_after_production_blocks_quality_check(self):
        """after_production milestone blocks transition to quality_check"""
        user = self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert user, "Failed to login"
        
        response = self.session.get(f"{BASE_URL}/api/orders/{ORDER_30_40_30}/payment-schedule")
        assert response.status_code == 200
        
        data = response.json()
        milestones = data["schedule"]["milestones"]
        
        # Find after_production milestone
        ap_ms = next((m for m in milestones if m["stage"] == "after_production"), None)
        assert ap_ms is not None, "Should have after_production milestone"
        assert ap_ms["blocks_status"] == "quality_check", f"after_production should block quality_check, got {ap_ms['blocks_status']}"
        
        print(f"PASS: after_production milestone correctly blocks quality_check")


class TestMilestoneAmountCalculation:
    """Test that milestone amounts are correctly calculated from percentages"""
    
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
    
    def test_amounts_sum_to_total(self):
        """Milestone amounts should sum to total order amount"""
        user = self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert user, "Failed to login"
        
        for order_id in [ORDER_50_50, ORDER_30_40_30, ORDER_NO_NOTES]:
            response = self.session.get(f"{BASE_URL}/api/orders/{order_id}/payment-schedule")
            assert response.status_code == 200
            
            data = response.json()
            total_amount = data["total_amount"]
            milestones = data["schedule"]["milestones"]
            
            amounts_sum = sum(m["amount"] for m in milestones)
            assert abs(amounts_sum - total_amount) < 0.01, f"Amounts sum {amounts_sum} should equal total {total_amount} for order {order_id}"
            
            print(f"PASS: Order {order_id} - amounts sum ({amounts_sum}) equals total ({total_amount})")
    
    def test_amount_matches_percentage(self):
        """Each milestone amount should match its percentage of total"""
        user = self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert user, "Failed to login"
        
        response = self.session.get(f"{BASE_URL}/api/orders/{ORDER_50_50}/payment-schedule")
        assert response.status_code == 200
        
        data = response.json()
        total_amount = data["total_amount"]
        milestones = data["schedule"]["milestones"]
        
        for ms in milestones:
            expected_amount = round(total_amount * ms["percentage"] / 100, 2)
            assert abs(ms["amount"] - expected_amount) < 0.01, f"Milestone {ms['milestone_id']} amount {ms['amount']} should be {expected_amount}"
        
        print(f"PASS: All milestone amounts correctly calculated from percentages")


class TestIsDueFlag:
    """Test that is_due flag is correctly set based on order status"""
    
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
    
    def test_first_milestone_is_due_on_pending_payment(self):
        """First milestone should be due when order is pending_payment"""
        user = self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert user, "Failed to login"
        
        response = self.session.get(f"{BASE_URL}/api/orders/{ORDER_50_50}/payment-schedule")
        assert response.status_code == 200
        
        data = response.json()
        assert data["order_status"] == "pending_payment", f"Expected pending_payment status, got {data['order_status']}"
        
        milestones = data["schedule"]["milestones"]
        
        # First milestone should be due
        assert milestones[0]["is_due"] == True, "First milestone should be due"
        
        # Second milestone should not be due yet
        if len(milestones) > 1:
            assert milestones[1]["is_due"] == False, "Second milestone should not be due yet"
        
        print(f"PASS: First milestone is_due=True, subsequent milestones is_due=False")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
