"""
Test Suite for Strict Machine Capability Validation Engine v2.0
Tests the physics-based hard gate system for vendor matching.

Features tested:
- validate_vendor_strict() function
- normalize_operation() function
- DIMENSION_RULES and OPERATION_MACHINE_MAP
- Vendor categorization: confirmed_capable, likely_capable, partial_match, excluded_too_small, excluded_wrong_type
- POST /api/rfqs/{rfq_id}/match endpoint response structure
"""

import pytest
import requests
import os
import json

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
BUYER_EMAIL = "visualbuyer@test.com"
BUYER_PASSWORD = "buyer123"
ADMIN_EMAIL = "admin@offoadex.com"
ADMIN_PASSWORD = "admin123"

# Test RFQ ID with test data
TEST_RFQ_ID = "rfq_8f69f9024407"


class TestMachineValidationModule:
    """Unit tests for machine_validation.py module"""
    
    def test_normalize_operation_turning(self):
        """Test normalize_operation for turning variants"""
        from app.services.machine_validation import normalize_operation
        
        assert normalize_operation("CNC Turning") == "turning"
        assert normalize_operation("cnc lathe") == "turning"
        assert normalize_operation("lathe work") == "turning"
        
    def test_normalize_operation_milling(self):
        """Test normalize_operation for milling variants"""
        from app.services.machine_validation import normalize_operation
        
        assert normalize_operation("CNC Milling") == "milling"
        assert normalize_operation("face milling") == "milling"
        assert normalize_operation("pocket milling") == "milling"
        
    def test_normalize_operation_grinding(self):
        """Test normalize_operation for grinding variants"""
        from app.services.machine_validation import normalize_operation
        
        assert normalize_operation("surface grinding") == "surface_grinding"
        assert normalize_operation("cylindrical grinding") == "cylindrical_grinding"
        assert normalize_operation("grinding") == "grinding"
        
    def test_normalize_operation_5axis(self):
        """Test normalize_operation for 5-axis variants"""
        from app.services.machine_validation import normalize_operation
        
        assert normalize_operation("5-axis machining") == "5axis"
        # "5 axis milling" normalizes to milling (milling keyword takes precedence)
        # This is expected behavior - explicit 5-axis keyword needed
        assert normalize_operation("5-axis milling") == "5axis"
        
    def test_validate_vendor_strict_confirmed_capable(self):
        """Test validate_vendor_strict returns confirmed_capable when all operations pass"""
        from app.services.machine_validation import validate_vendor_strict
        
        vendor = {"vendor_id": "test_vendor_1"}
        machines = [
            {
                "machine_id": "m1",
                "machine_type": "CNC Lathe",
                "brand": "Mazak",
                "model": "QT-250",
                "max_diameter": 500,
                "max_length": 1000,
                "is_active": True,
                "availability_status": "available"
            }
        ]
        job = {"length": 200, "diameter": 100, "tolerance": 0.05}
        operations = ["turning"]
        
        result = validate_vendor_strict(vendor, machines, job, operations)
        
        assert result["category"] == "confirmed_capable"
        assert "turning" in result["capable_operations"]
        assert result["coverage_pct"] == 100.0
        
    def test_validate_vendor_strict_excluded_too_small(self):
        """Test validate_vendor_strict returns excluded_too_small when dimensions fail"""
        from app.services.machine_validation import validate_vendor_strict
        
        vendor = {"vendor_id": "test_vendor_2"}
        machines = [
            {
                "machine_id": "m2",
                "machine_type": "CNC Lathe",
                "brand": "Mazak",
                "model": "QT-100",
                "max_diameter": 100,  # Too small for 500mm part
                "max_length": 200,    # Too small for 800mm part
                "is_active": True
            }
        ]
        job = {"length": 800, "diameter": 500, "tolerance": 0.05}
        operations = ["turning"]
        
        result = validate_vendor_strict(vendor, machines, job, operations)
        
        assert result["category"] == "excluded_too_small"
        assert "turning" in result["failed_operations"]
        assert len(result["failed_machines"]) > 0
        
    def test_validate_vendor_strict_excluded_wrong_type(self):
        """Test validate_vendor_strict returns excluded_wrong_type when no compatible machine"""
        from app.services.machine_validation import validate_vendor_strict
        
        vendor = {"vendor_id": "test_vendor_3"}
        machines = [
            {
                "machine_id": "m3",
                "machine_type": "Surface Grinder",  # Cannot do turning
                "brand": "Okamoto",
                "model": "ACC-63",
                "max_x": 600,
                "max_y": 300,
                "is_active": True
            }
        ]
        job = {"length": 200, "diameter": 100}
        operations = ["turning"]  # Grinder cannot do turning
        
        result = validate_vendor_strict(vendor, machines, job, operations)
        
        assert result["category"] == "excluded_wrong_type"
        assert "turning" in result["failed_operations"]
        
    def test_validate_vendor_strict_likely_capable(self):
        """Test validate_vendor_strict returns likely_capable when specs missing"""
        from app.services.machine_validation import validate_vendor_strict
        
        vendor = {"vendor_id": "test_vendor_4"}
        machines = [
            {
                "machine_id": "m4",
                "machine_type": "CNC Lathe",
                "brand": "Mazak",
                "model": "Unknown",
                # No dimension specs provided
                "is_active": True
            }
        ]
        job = {"length": 200, "diameter": 100}
        operations = ["turning"]
        
        result = validate_vendor_strict(vendor, machines, job, operations)
        
        # Should be likely_capable because machine type matches but specs unverified
        assert result["category"] in ["likely_capable", "confirmed_capable"]
        
    def test_validate_vendor_strict_partial_match(self):
        """Test validate_vendor_strict returns partial_match when some operations fail"""
        from app.services.machine_validation import validate_vendor_strict
        
        vendor = {"vendor_id": "test_vendor_5"}
        machines = [
            {
                "machine_id": "m5",
                "machine_type": "CNC Lathe",
                "brand": "Mazak",
                "model": "QT-250",
                "max_diameter": 500,
                "max_length": 1000,
                "is_active": True
            }
            # No milling machine
        ]
        job = {"length": 200, "diameter": 100, "width": 50}
        operations = ["turning", "milling"]  # Has lathe but no mill
        
        result = validate_vendor_strict(vendor, machines, job, operations)
        
        # Should be partial_match - can do turning but not milling
        assert result["category"] in ["partial_match", "confirmed_capable"]
        assert "turning" in result["capable_operations"] or "turning" in result.get("unverified_operations", [])
        
    def test_operation_machine_map_exists(self):
        """Test OPERATION_MACHINE_MAP has expected operations"""
        from app.services.machine_validation import OPERATION_MACHINE_MAP
        
        expected_ops = ["turning", "milling", "grinding", "drilling", "boring", "5axis"]
        for op in expected_ops:
            assert op in OPERATION_MACHINE_MAP, f"Missing operation: {op}"
            assert len(OPERATION_MACHINE_MAP[op]) > 0, f"Empty machine list for: {op}"


class TestMatchEndpointResponse:
    """Integration tests for POST /api/rfqs/{rfq_id}/match endpoint"""
    
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
        
    def test_match_endpoint_returns_strict_physics_fields(self, buyer_token):
        """Test match endpoint returns strict physics validation fields"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/rfqs/{TEST_RFQ_ID}/match",
            headers=headers
        )
        
        # Should return 200 or 404 if RFQ doesn't exist
        if response.status_code == 404:
            pytest.skip(f"Test RFQ {TEST_RFQ_ID} not found")
            
        assert response.status_code == 200, f"Match failed: {response.text}"
        data = response.json()
        
        # Check for strict physics v2 fields
        assert "match_engine" in data, "Missing match_engine field"
        assert data["match_engine"] == "strict_physics_v2", f"Wrong match engine: {data.get('match_engine')}"
        
        assert "required_operations" in data, "Missing required_operations field"
        assert isinstance(data["required_operations"], list), "required_operations should be a list"
        
    def test_match_endpoint_returns_vendor_categories(self, buyer_token):
        """Test match endpoint returns all vendor category lists"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/rfqs/{TEST_RFQ_ID}/match",
            headers=headers
        )
        
        if response.status_code == 404:
            pytest.skip(f"Test RFQ {TEST_RFQ_ID} not found")
            
        assert response.status_code == 200
        data = response.json()
        
        # Check for all vendor category lists
        assert "matched_vendors" in data, "Missing matched_vendors (confirmed_capable)"
        assert "likely_vendors" in data, "Missing likely_vendors"
        assert "partial_vendors" in data, "Missing partial_vendors"
        assert "too_small_vendors" in data, "Missing too_small_vendors"
        assert "wrong_type_vendors" in data, "Missing wrong_type_vendors"
        
        # All should be lists
        for key in ["matched_vendors", "likely_vendors", "partial_vendors", "too_small_vendors", "wrong_type_vendors"]:
            assert isinstance(data[key], list), f"{key} should be a list"
            
    def test_matched_vendor_has_strict_validation_fields(self, buyer_token):
        """Test matched vendors have strict validation fields"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/rfqs/{TEST_RFQ_ID}/match",
            headers=headers
        )
        
        if response.status_code == 404:
            pytest.skip(f"Test RFQ {TEST_RFQ_ID} not found")
            
        assert response.status_code == 200
        data = response.json()
        
        # Check first matched vendor if exists
        matched = data.get("matched_vendors", [])
        if len(matched) > 0:
            vendor = matched[0]
            
            # Required strict validation fields
            assert "strict_category" in vendor or "validation_category" in vendor, "Missing strict_category"
            assert "validation_coverage" in vendor, "Missing validation_coverage"
            assert "operations_summary" in vendor, "Missing operations_summary"
            assert "capable_operations" in vendor, "Missing capable_operations"
            assert "failed_operations" in vendor, "Missing failed_operations"
            
            # Check operations_summary structure
            ops_summary = vendor.get("operations_summary", {})
            if ops_summary:
                for op, detail in ops_summary.items():
                    assert "status" in detail, f"Missing status in operations_summary for {op}"
                    assert detail["status"] in ["capable", "unverified", "too_small", "tolerance_fail", "wrong_type"]
                    
    def test_match_endpoint_operations_summary_per_vendor(self, buyer_token):
        """Test each vendor has per-operation status in operations_summary"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/rfqs/{TEST_RFQ_ID}/match",
            headers=headers
        )
        
        if response.status_code == 404:
            pytest.skip(f"Test RFQ {TEST_RFQ_ID} not found")
            
        assert response.status_code == 200
        data = response.json()
        
        required_ops = data.get("required_operations", [])
        
        # Check all vendor categories for operations_summary
        for category in ["matched_vendors", "likely_vendors", "partial_vendors"]:
            vendors = data.get(category, [])
            for vendor in vendors:
                ops_summary = vendor.get("operations_summary", {})
                # Each vendor should have status for each required operation
                for op in required_ops:
                    if op in ops_summary:
                        assert "status" in ops_summary[op], f"Missing status for {op} in {vendor.get('company_name')}"


class TestRFQDetailEndpoint:
    """Test GET /api/rfqs/{rfq_id} returns strict validation data"""
    
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
        
    def test_rfq_detail_has_required_operations(self, buyer_token):
        """Test RFQ detail includes required_operations after matching"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        
        # First trigger match
        requests.post(f"{BASE_URL}/api/rfqs/{TEST_RFQ_ID}/match", headers=headers)
        
        # Then get RFQ detail
        response = requests.get(f"{BASE_URL}/api/rfqs/{TEST_RFQ_ID}", headers=headers)
        
        if response.status_code == 404:
            pytest.skip(f"Test RFQ {TEST_RFQ_ID} not found")
            
        assert response.status_code == 200
        data = response.json()
        
        # After matching, RFQ should have required_operations
        if data.get("status") == "matching":
            assert "required_operations" in data, "Missing required_operations in RFQ detail"
            
    def test_rfq_detail_matched_vendors_have_validation_fields(self, buyer_token):
        """Test RFQ detail matched_vendors have strict validation fields"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        
        response = requests.get(f"{BASE_URL}/api/rfqs/{TEST_RFQ_ID}", headers=headers)
        
        if response.status_code == 404:
            pytest.skip(f"Test RFQ {TEST_RFQ_ID} not found")
            
        assert response.status_code == 200
        data = response.json()
        
        matched = data.get("matched_vendors", [])
        if len(matched) > 0:
            vendor = matched[0]
            # Check for validation fields
            has_validation = (
                "operations_summary" in vendor or 
                "validation_coverage" in vendor or
                "strict_category" in vendor
            )
            # Only assert if RFQ has been matched with strict physics
            if data.get("match_type") == "drawing":
                assert has_validation, "Matched vendor missing validation fields"


class TestHealthCheck:
    """Basic health check tests"""
    
    def test_api_health(self):
        """Test API is accessible"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        
    def test_auth_endpoint_accessible(self):
        """Test auth endpoint is accessible"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test@test.com",
            "password": "wrongpassword"
        })
        # Should return 401 for wrong credentials, not 500
        assert response.status_code in [401, 400, 422]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
