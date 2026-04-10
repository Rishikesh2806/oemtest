"""
Test suite for AI-powered cost estimation feature
Tests:
- GET /api/admin/cost-config - Admin cost configuration retrieval
- PUT /api/admin/cost-config - Admin cost configuration update
- POST /api/rfqs/{rfq_id}/estimate-cost - Cost estimation for RFQ parts
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@offoadex.com"
ADMIN_PASSWORD = "admin123"
BUYER_EMAIL = "buyer5@oemlinker.com"
BUYER_PASSWORD = "buyer123"
TEST_RFQ_ID = "rfq_c10b60fd41ae"  # Steel Flange Assembly with AI analysis


class TestCostConfigEndpoints:
    """Tests for admin cost configuration endpoints"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")
    
    @pytest.fixture(scope="class")
    def buyer_token(self):
        """Get buyer authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": BUYER_EMAIL,
            "password": BUYER_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip(f"Buyer login failed: {response.status_code} - {response.text}")
    
    def test_get_cost_config_returns_default_structure(self, admin_token):
        """GET /api/admin/cost-config returns default cost configuration"""
        response = requests.get(
            f"{BASE_URL}/api/admin/cost-config",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify all required sections exist
        assert "material_rates" in data, "Missing material_rates section"
        assert "machine_hourly_rates" in data, "Missing machine_hourly_rates section"
        assert "finishing_rates" in data, "Missing finishing_rates section"
        assert "tooling_rates" in data, "Missing tooling_rates section"
        assert "heat_treatment_rates" in data, "Missing heat_treatment_rates section"
        
        # Verify material_rates structure
        material_rates = data["material_rates"]
        assert len(material_rates) > 0, "material_rates should not be empty"
        # Check a sample material
        if "mild_steel" in material_rates:
            ms = material_rates["mild_steel"]
            assert "name" in ms, "Material should have name"
            assert "rate_per_kg" in ms, "Material should have rate_per_kg"
            assert "unit" in ms, "Material should have unit"
            assert isinstance(ms["rate_per_kg"], (int, float)), "rate_per_kg should be numeric"
        
        # Verify machine_hourly_rates structure
        machine_rates = data["machine_hourly_rates"]
        assert len(machine_rates) > 0, "machine_hourly_rates should not be empty"
        if "cnc_turning" in machine_rates:
            cnc = machine_rates["cnc_turning"]
            assert "name" in cnc, "Machine should have name"
            assert "rate_per_hour" in cnc, "Machine should have rate_per_hour"
            assert isinstance(cnc["rate_per_hour"], (int, float)), "rate_per_hour should be numeric"
        
        print(f"✓ Cost config has {len(material_rates)} materials, {len(machine_rates)} machines")
    
    def test_get_cost_config_requires_admin_auth(self, buyer_token):
        """GET /api/admin/cost-config returns 403 for non-admin users"""
        response = requests.get(
            f"{BASE_URL}/api/admin/cost-config",
            headers={"Authorization": f"Bearer {buyer_token}"}
        )
        
        assert response.status_code == 403, f"Expected 403 for buyer, got {response.status_code}"
        print("✓ Non-admin correctly denied access to cost config")
    
    def test_get_cost_config_requires_auth(self):
        """GET /api/admin/cost-config returns 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/admin/cost-config")
        
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print("✓ Unauthenticated request correctly denied")
    
    def test_put_cost_config_updates_rates(self, admin_token):
        """PUT /api/admin/cost-config updates rates and persists them"""
        # First get current config
        get_response = requests.get(
            f"{BASE_URL}/api/admin/cost-config",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert get_response.status_code == 200
        original_config = get_response.json()
        
        # Modify a rate
        updated_material_rates = original_config.get("material_rates", {}).copy()
        if "mild_steel" in updated_material_rates:
            original_rate = updated_material_rates["mild_steel"]["rate_per_kg"]
            test_rate = original_rate + 1  # Increment by 1
            updated_material_rates["mild_steel"]["rate_per_kg"] = test_rate
        
        # Update config
        update_response = requests.put(
            f"{BASE_URL}/api/admin/cost-config",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"material_rates": updated_material_rates}
        )
        
        assert update_response.status_code == 200, f"Update failed: {update_response.text}"
        update_data = update_response.json()
        assert update_data.get("status") == "updated", "Expected status 'updated'"
        assert "material_rates" in update_data.get("sections_updated", []), "material_rates should be in updated sections"
        
        # Verify persistence by fetching again
        verify_response = requests.get(
            f"{BASE_URL}/api/admin/cost-config",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert verify_response.status_code == 200
        verified_config = verify_response.json()
        
        if "mild_steel" in verified_config.get("material_rates", {}):
            assert verified_config["material_rates"]["mild_steel"]["rate_per_kg"] == test_rate, \
                "Rate update was not persisted"
        
        # Restore original rate
        requests.put(
            f"{BASE_URL}/api/admin/cost-config",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"material_rates": original_config.get("material_rates", {})}
        )
        
        print("✓ Cost config update and persistence verified")
    
    def test_put_cost_config_requires_admin(self, buyer_token):
        """PUT /api/admin/cost-config returns 403 for non-admin users"""
        response = requests.put(
            f"{BASE_URL}/api/admin/cost-config",
            headers={"Authorization": f"Bearer {buyer_token}"},
            json={"material_rates": {}}
        )
        
        assert response.status_code == 403, f"Expected 403 for buyer, got {response.status_code}"
        print("✓ Non-admin correctly denied update access")


class TestCostEstimationEndpoint:
    """Tests for POST /api/rfqs/{rfq_id}/estimate-cost endpoint"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip(f"Admin login failed: {response.status_code}")
    
    @pytest.fixture(scope="class")
    def buyer_token(self):
        """Get buyer authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": BUYER_EMAIL,
            "password": BUYER_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip(f"Buyer login failed: {response.status_code}")
    
    def test_estimate_cost_returns_breakdown(self, admin_token):
        """POST /api/rfqs/{rfq_id}/estimate-cost returns cost breakdown with all required fields"""
        response = requests.post(
            f"{BASE_URL}/api/rfqs/{TEST_RFQ_ID}/estimate-cost",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"quantities": [1, 10, 50, 100]},
            timeout=60  # AI call may take time
        )
        
        # Check for 404 if RFQ doesn't exist
        if response.status_code == 404:
            pytest.skip(f"Test RFQ {TEST_RFQ_ID} not found - need to create test data")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Check for error response
        if data.get("method") == "failed":
            pytest.skip(f"AI estimation failed: {data.get('error')}")
        
        if data.get("method") == "unavailable":
            pytest.skip("AI estimation not available (missing EMERGENT_LLM_KEY)")
        
        # Verify response structure
        assert "rfq_id" in data, "Response should include rfq_id"
        assert data["rfq_id"] == TEST_RFQ_ID, "rfq_id should match request"
        assert "cost_breakdown" in data, "Response should include cost_breakdown"
        assert "quantity_pricing" in data, "Response should include quantity_pricing"
        assert "currency" in data, "Response should include currency"
        assert data["currency"] == "INR", "Currency should be INR"
        assert "method" in data, "Response should include method"
        assert data["method"] == "ai_estimation", "Method should be ai_estimation"
        
        # Verify cost_breakdown structure
        breakdown = data["cost_breakdown"]
        assert "material_cost" in breakdown, "Breakdown should include material_cost"
        assert "operations" in breakdown, "Breakdown should include operations"
        assert "setup_cost" in breakdown, "Breakdown should include setup_cost"
        assert "tooling_cost" in breakdown, "Breakdown should include tooling_cost"
        assert "total_per_piece" in breakdown, "Breakdown should include total_per_piece"
        
        # Verify material_cost structure
        material_cost = breakdown["material_cost"]
        assert "material_type" in material_cost, "material_cost should have material_type"
        assert "estimated_weight_kg" in material_cost, "material_cost should have estimated_weight_kg"
        assert "rate_per_kg" in material_cost, "material_cost should have rate_per_kg"
        assert "total" in material_cost, "material_cost should have total"
        
        # Verify operations is an array
        operations = breakdown["operations"]
        assert isinstance(operations, list), "operations should be a list"
        if len(operations) > 0:
            op = operations[0]
            assert "process" in op, "Operation should have process"
            assert "estimated_time_minutes" in op, "Operation should have estimated_time_minutes"
            assert "rate_per_hour" in op, "Operation should have rate_per_hour"
            assert "cost" in op, "Operation should have cost"
        
        print(f"✓ Cost breakdown received: ₹{breakdown.get('total_per_piece', 0):.2f}/piece")
        print(f"  - Material: ₹{material_cost.get('total', 0):.2f}")
        print(f"  - Operations: {len(operations)}")
    
    def test_estimate_cost_quantity_pricing_structure(self, admin_token):
        """POST /api/rfqs/{rfq_id}/estimate-cost quantity_pricing has 4 entries with volume discounts"""
        response = requests.post(
            f"{BASE_URL}/api/rfqs/{TEST_RFQ_ID}/estimate-cost",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"quantities": [1, 10, 50, 100]},
            timeout=60
        )
        
        if response.status_code == 404:
            pytest.skip(f"Test RFQ {TEST_RFQ_ID} not found")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        
        if data.get("method") in ["failed", "unavailable"]:
            pytest.skip(f"AI estimation not available: {data.get('method')}")
        
        quantity_pricing = data.get("quantity_pricing", [])
        
        # Verify 4 entries for quantities 1, 10, 50, 100
        assert len(quantity_pricing) == 4, f"Expected 4 quantity pricing entries, got {len(quantity_pricing)}"
        
        quantities = [qp["quantity"] for qp in quantity_pricing]
        assert quantities == [1, 10, 50, 100], f"Expected quantities [1, 10, 50, 100], got {quantities}"
        
        # Verify each entry structure
        for qp in quantity_pricing:
            assert "quantity" in qp, "Entry should have quantity"
            assert "price_per_piece" in qp, "Entry should have price_per_piece"
            assert "total_cost" in qp, "Entry should have total_cost"
            assert "discount_pct" in qp, "Entry should have discount_pct"
            
            # Verify discount percentages
            qty = qp["quantity"]
            expected_discount = 0 if qty == 1 else 5 if qty == 10 else 10 if qty == 50 else 15
            assert qp["discount_pct"] == expected_discount, \
                f"Expected {expected_discount}% discount for qty {qty}, got {qp['discount_pct']}%"
        
        # Verify price decreases with quantity (due to setup amortization + volume discount)
        prices = [qp["price_per_piece"] for qp in quantity_pricing]
        for i in range(1, len(prices)):
            assert prices[i] <= prices[i-1], \
                f"Price should decrease with quantity: {prices[i-1]} -> {prices[i]}"
        
        print("✓ Quantity pricing verified:")
        for qp in quantity_pricing:
            print(f"  - {qp['quantity']} pcs: ₹{qp['price_per_piece']:.2f}/pc (total: ₹{qp['total_cost']:.2f}, -{qp['discount_pct']}%)")
    
    def test_estimate_cost_rfq_not_found(self, admin_token):
        """POST /api/rfqs/{rfq_id}/estimate-cost returns 404 for non-existent RFQ"""
        response = requests.post(
            f"{BASE_URL}/api/rfqs/nonexistent_rfq_12345/estimate-cost",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"quantities": [1, 10, 50, 100]}
        )
        
        assert response.status_code == 404, f"Expected 404 for non-existent RFQ, got {response.status_code}"
        print("✓ Non-existent RFQ correctly returns 404")
    
    def test_estimate_cost_requires_auth(self):
        """POST /api/rfqs/{rfq_id}/estimate-cost requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/rfqs/{TEST_RFQ_ID}/estimate-cost",
            json={"quantities": [1, 10, 50, 100]}
        )
        
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print("✓ Unauthenticated request correctly denied")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
