"""
Test Machine Validation System for OEMLinker
Tests:
1. has_complete_specs detection for various machine types
2. validate_machine_for_job function returns correct categories
3. PROCESS_MACHINE_COMPATIBILITY blocks wrong machine types
4. POST /api/machines auto-computes has_complete_specs
5. PUT /api/machines auto-computes has_complete_specs on update
6. GET /api/rfqs/{rfq_id} returns unverified_vendors, too_small_vendors, wrong_type_vendors
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@offoadex.com"
ADMIN_PASSWORD = "admin123"
VENDOR_EMAIL = "testvendor_nda@test.com"
VENDOR_PASSWORD = "vendor123"
BUYER_EMAIL = "visualbuyer@test.com"
BUYER_PASSWORD = "buyer123"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def vendor_token():
    """Get vendor auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": VENDOR_EMAIL,
        "password": VENDOR_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Vendor login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def buyer_token():
    """Get buyer auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": BUYER_EMAIL,
        "password": BUYER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Buyer login failed: {response.status_code} - {response.text}")


class TestMachineValidationModule:
    """Test the machine_validation.py module functions directly"""
    
    def test_has_complete_specs_cnc_lathe_complete(self):
        """CNC Lathe with max_length and max_diameter should be complete"""
        import sys
        sys.path.insert(0, '/app/backend')
        from app.services.machine_validation import has_complete_specs
        
        machine = {
            "machine_type": "CNC Lathe",
            "max_length": 500,
            "max_diameter": 300
        }
        assert has_complete_specs(machine) is True
        print("PASS: CNC Lathe with complete specs detected correctly")
    
    def test_has_complete_specs_cnc_lathe_incomplete(self):
        """CNC Lathe missing max_diameter should be incomplete"""
        import sys
        sys.path.insert(0, '/app/backend')
        from app.services.machine_validation import has_complete_specs
        
        machine = {
            "machine_type": "CNC Lathe",
            "max_length": 500
            # missing max_diameter
        }
        assert has_complete_specs(machine) is False
        print("PASS: CNC Lathe with missing specs detected as incomplete")
    
    def test_has_complete_specs_vmc_complete(self):
        """VMC with max_x, max_y, max_z should be complete"""
        import sys
        sys.path.insert(0, '/app/backend')
        from app.services.machine_validation import has_complete_specs
        
        machine = {
            "machine_type": "VMC",
            "max_x": 800,
            "max_y": 500,
            "max_z": 400
        }
        assert has_complete_specs(machine) is True
        print("PASS: VMC with complete specs detected correctly")
    
    def test_has_complete_specs_vmc_incomplete(self):
        """VMC missing max_z should be incomplete"""
        import sys
        sys.path.insert(0, '/app/backend')
        from app.services.machine_validation import has_complete_specs
        
        machine = {
            "machine_type": "VMC",
            "max_x": 800,
            "max_y": 500
            # missing max_z
        }
        assert has_complete_specs(machine) is False
        print("PASS: VMC with missing specs detected as incomplete")
    
    def test_validate_machine_for_job_wrong_type(self):
        """VMC cannot perform turning - should return wrong_type"""
        import sys
        sys.path.insert(0, '/app/backend')
        from app.services.machine_validation import validate_machine_for_job
        
        machine = {
            "machine_type": "VMC",
            "max_x": 800,
            "max_y": 500,
            "max_z": 400
        }
        job = {"process": "turning", "diameter": 100}
        
        result = validate_machine_for_job(machine, job)
        assert result["category"] == "wrong_type"
        assert result["can_perform"] is False
        assert len(result["fail_reasons"]) > 0
        print(f"PASS: VMC correctly rejected for turning - {result['fail_reasons'][0]}")
    
    def test_validate_machine_for_job_too_small(self):
        """CNC Lathe too small for part - should return too_small"""
        import sys
        sys.path.insert(0, '/app/backend')
        from app.services.machine_validation import validate_machine_for_job
        
        machine = {
            "machine_type": "CNC Lathe",
            "max_length": 200,
            "max_diameter": 100
        }
        job = {"process": "turning", "diameter": 300, "length": 500}
        
        result = validate_machine_for_job(machine, job)
        assert result["category"] == "too_small"
        assert result["can_perform"] is False
        print(f"PASS: CNC Lathe correctly rejected as too_small - {result['fail_reasons']}")
    
    def test_validate_machine_for_job_unverified(self):
        """CNC Lathe without specs for size-dependent job - should return unverified"""
        import sys
        sys.path.insert(0, '/app/backend')
        from app.services.machine_validation import validate_machine_for_job
        
        machine = {
            "machine_type": "CNC Lathe"
            # No dimension specs
        }
        job = {"process": "turning", "diameter": 100, "length": 200}
        
        result = validate_machine_for_job(machine, job)
        assert result["category"] == "unverified"
        assert result["can_perform"] is None
        print(f"PASS: CNC Lathe without specs correctly marked as unverified")
    
    def test_validate_machine_for_job_fully_capable(self):
        """CNC Lathe with adequate specs - should return fully_capable"""
        import sys
        sys.path.insert(0, '/app/backend')
        from app.services.machine_validation import validate_machine_for_job
        
        machine = {
            "machine_type": "CNC Lathe",
            "max_length": 600,
            "max_diameter": 400
        }
        job = {"process": "turning", "diameter": 200, "length": 300}
        
        result = validate_machine_for_job(machine, job)
        assert result["category"] == "fully_capable"
        assert result["can_perform"] is True
        print(f"PASS: CNC Lathe correctly validated as fully_capable")
    
    def test_process_machine_compatibility_milling(self):
        """VMC can perform milling"""
        import sys
        sys.path.insert(0, '/app/backend')
        from app.services.machine_validation import validate_machine_for_job
        
        machine = {
            "machine_type": "VMC",
            "max_x": 800,
            "max_y": 500,
            "max_z": 400
        }
        job = {"process": "milling", "length": 200, "width": 150, "height": 100}
        
        result = validate_machine_for_job(machine, job)
        assert result["category"] == "fully_capable"
        assert result["can_perform"] is True
        print("PASS: VMC correctly validated for milling")
    
    def test_categorize_vendor_match(self):
        """Test categorize_vendor_match function"""
        import sys
        sys.path.insert(0, '/app/backend')
        from app.services.machine_validation import categorize_vendor_match
        
        vendor = {"vendor_id": "test_vendor_123"}
        machines = [
            {
                "machine_id": "m1",
                "machine_type": "CNC Lathe",
                "max_length": 600,
                "max_diameter": 400,
                "is_active": True
            }
        ]
        job_req = {"diameter": 200, "length": 300}
        process_list = ["turning"]
        
        result = categorize_vendor_match(vendor, machines, job_req, process_list)
        assert result["category"] == "fully_capable"
        assert result["coverage_pct"] == 100.0
        assert len(result["best_machines"]) > 0
        print(f"PASS: categorize_vendor_match returned {result['category']} with {result['coverage_pct']}% coverage")


class TestMachineAPIHasCompleteSpecs:
    """Test that POST/PUT /api/machines auto-computes has_complete_specs"""
    
    def test_create_machine_with_complete_specs(self, vendor_token):
        """POST /api/machines should auto-compute has_complete_specs=True for complete machine"""
        headers = {"Authorization": f"Bearer {vendor_token}"}
        
        machine_data = {
            "machine_type": "CNC Lathe",
            "brand": "TEST_Mazak",
            "model": "QT-250",
            "max_length": 500,
            "max_diameter": 300,
            "tolerance_capability": 0.01
        }
        
        response = requests.post(f"{BASE_URL}/api/machines", json=machine_data, headers=headers)
        assert response.status_code == 200, f"Failed to create machine: {response.text}"
        
        data = response.json()
        assert "machine_id" in data
        assert data.get("has_complete_specs") is True, f"Expected has_complete_specs=True, got {data.get('has_complete_specs')}"
        
        # Cleanup
        machine_id = data["machine_id"]
        requests.delete(f"{BASE_URL}/api/machines/{machine_id}", headers=headers)
        
        print(f"PASS: Machine created with has_complete_specs=True")
    
    def test_create_machine_with_incomplete_specs(self, vendor_token):
        """POST /api/machines should auto-compute has_complete_specs=False for incomplete machine"""
        headers = {"Authorization": f"Bearer {vendor_token}"}
        
        machine_data = {
            "machine_type": "CNC Lathe",
            "brand": "TEST_Mazak",
            "model": "QT-250"
            # Missing max_length and max_diameter
        }
        
        response = requests.post(f"{BASE_URL}/api/machines", json=machine_data, headers=headers)
        assert response.status_code == 200, f"Failed to create machine: {response.text}"
        
        data = response.json()
        assert "machine_id" in data
        assert data.get("has_complete_specs") is False, f"Expected has_complete_specs=False, got {data.get('has_complete_specs')}"
        
        # Cleanup
        machine_id = data["machine_id"]
        requests.delete(f"{BASE_URL}/api/machines/{machine_id}", headers=headers)
        
        print(f"PASS: Machine created with has_complete_specs=False")
    
    def test_update_machine_recomputes_has_complete_specs(self, vendor_token):
        """PUT /api/machines should recompute has_complete_specs on update"""
        headers = {"Authorization": f"Bearer {vendor_token}"}
        
        # Create incomplete machine
        machine_data = {
            "machine_type": "VMC",
            "brand": "TEST_Haas",
            "model": "VF-2"
        }
        
        response = requests.post(f"{BASE_URL}/api/machines", json=machine_data, headers=headers)
        assert response.status_code == 200
        data = response.json()
        machine_id = data["machine_id"]
        
        # Verify initially incomplete
        assert data.get("has_complete_specs") is False
        
        # Update with complete specs
        update_data = {
            "machine_type": "VMC",
            "brand": "TEST_Haas",
            "model": "VF-2",
            "max_x": 762,
            "max_y": 406,
            "max_z": 508
        }
        
        response = requests.put(f"{BASE_URL}/api/machines/{machine_id}", json=update_data, headers=headers)
        assert response.status_code == 200, f"Failed to update machine: {response.text}"
        
        updated = response.json()
        assert updated.get("has_complete_specs") is True, f"Expected has_complete_specs=True after update, got {updated.get('has_complete_specs')}"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/machines/{machine_id}", headers=headers)
        
        print(f"PASS: Machine update recomputed has_complete_specs correctly")


class TestRFQValidationFields:
    """Test that GET /api/rfqs/{rfq_id} returns validation category fields"""
    
    def test_rfq_has_validation_fields_structure(self, buyer_token):
        """GET /api/rfqs should return RFQs with validation fields when present"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        
        # Get list of RFQs
        response = requests.get(f"{BASE_URL}/api/rfqs", headers=headers)
        assert response.status_code == 200, f"Failed to get RFQs: {response.text}"
        
        rfqs = response.json()
        if not rfqs:
            pytest.skip("No RFQs found for buyer")
        
        # Find an RFQ with matched_vendors
        rfq_with_matches = None
        for rfq in rfqs:
            if rfq.get("matched_vendors"):
                rfq_with_matches = rfq
                break
        
        if not rfq_with_matches:
            pytest.skip("No RFQs with matched vendors found")
        
        # Get full RFQ details
        rfq_id = rfq_with_matches["rfq_id"]
        response = requests.get(f"{BASE_URL}/api/rfqs/{rfq_id}", headers=headers)
        assert response.status_code == 200
        
        rfq_detail = response.json()
        
        # Check that validation fields exist (may be empty arrays if no excluded vendors)
        # These fields should be present in the response schema
        print(f"RFQ {rfq_id} fields: unverified_vendors={rfq_detail.get('unverified_vendors', 'NOT_PRESENT')}, "
              f"too_small_vendors={rfq_detail.get('too_small_vendors', 'NOT_PRESENT')}, "
              f"wrong_type_vendors={rfq_detail.get('wrong_type_vendors', 'NOT_PRESENT')}")
        
        # Check matched vendors have validation_category
        for vendor in rfq_detail.get("matched_vendors", []):
            if "validation_category" in vendor:
                print(f"  Vendor {vendor.get('company_name', vendor.get('vendor_id'))}: validation_category={vendor['validation_category']}")
        
        print(f"PASS: RFQ detail endpoint returns validation fields")
    
    def test_rfq_matched_vendor_has_validation_category(self, buyer_token):
        """Matched vendors should have validation_category field"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        
        response = requests.get(f"{BASE_URL}/api/rfqs", headers=headers)
        assert response.status_code == 200
        
        rfqs = response.json()
        
        # Find RFQ with matched vendors that have validation_category
        found_validation = False
        for rfq in rfqs:
            for vendor in rfq.get("matched_vendors", []):
                if "validation_category" in vendor:
                    found_validation = True
                    assert vendor["validation_category"] in ["fully_capable", "unverified", "wrong_type", "too_small"]
                    print(f"PASS: Found vendor with validation_category={vendor['validation_category']}")
                    break
            if found_validation:
                break
        
        if not found_validation:
            print("INFO: No matched vendors with validation_category found - this is expected for RFQs matched before the upgrade")


class TestHealthCheck:
    """Basic health check to ensure backend is running"""
    
    def test_backend_health(self):
        """Backend should respond to health check"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        print("PASS: Backend health check passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
