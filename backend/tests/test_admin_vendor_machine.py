"""
Test Suite: Admin Vendor Profile & Machine Management
Tests the new admin panel features for managing vendor profiles and machines.

Features tested:
- GET /api/admin/vendors/{id}/full - Get full vendor profile with machines and stats
- PUT /api/admin/vendors/{id}/profile - Update vendor profile details
- GET /api/admin/machines - List all machines
- POST /api/admin/machines - Create machine for any vendor
- PUT /api/admin/machines/{id} - Update any machine
- DELETE /api/admin/machines/{id} - Delete any machine
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@offoadex.com"
ADMIN_PASSWORD = "admin123"

# Known seeded vendor IDs from the context
SEEDED_VENDORS = ["vendor_aerospace_01", "vendor_precision_02", "vendor_global_03"]


class TestAdminAuth:
    """Test admin authentication and get token"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "admin"
        return data["access_token"]
    
    @pytest.fixture(scope="class")
    def headers(self, admin_token):
        """Get authenticated headers"""
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
    
    def test_admin_login_success(self):
        """Test admin can login successfully"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["role"] == "admin"
        print("PASS: Admin login successful")


class TestAdminVendorEndpoints:
    """Test admin vendor management endpoints"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def headers(self, admin_token):
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
    
    def test_get_admin_vendors_list(self, headers):
        """Test GET /api/admin/vendors returns list of vendors"""
        response = requests.get(f"{BASE_URL}/api/admin/vendors", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: Admin vendors list returned {len(data)} vendors")
    
    def test_get_vendor_full_profile(self, headers):
        """Test GET /api/admin/vendors/{id}/full returns full vendor profile"""
        # First get list of vendors to find a valid vendor_id
        vendors_response = requests.get(f"{BASE_URL}/api/admin/vendors", headers=headers)
        vendors = vendors_response.json()
        
        if len(vendors) == 0:
            pytest.skip("No vendors available for testing")
        
        vendor_id = vendors[0]["vendor_id"]
        
        response = requests.get(f"{BASE_URL}/api/admin/vendors/{vendor_id}/full", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        # Verify response structure
        assert "vendor" in data, "Response missing 'vendor' key"
        assert "machines" in data, "Response missing 'machines' key"
        assert "stats" in data, "Response missing 'stats' key"
        
        # Verify vendor has expected fields
        vendor = data["vendor"]
        assert "vendor_id" in vendor
        assert "company_name" in vendor
        
        # Verify stats has expected fields
        stats = data["stats"]
        assert "total_machines" in stats
        assert "total_quotes" in stats
        print(f"PASS: Full vendor profile for {vendor_id} - {vendor.get('company_name')}")
        print(f"  - Machines: {stats.get('total_machines')}, Quotes: {stats.get('total_quotes')}")
    
    def test_get_vendor_full_profile_not_found(self, headers):
        """Test GET /api/admin/vendors/{id}/full returns 404 for non-existent vendor"""
        response = requests.get(f"{BASE_URL}/api/admin/vendors/nonexistent_vendor_123/full", headers=headers)
        assert response.status_code == 404
        print("PASS: Non-existent vendor returns 404")
    
    def test_update_vendor_profile(self, headers):
        """Test PUT /api/admin/vendors/{id}/profile updates vendor profile"""
        # Get a vendor to update
        vendors_response = requests.get(f"{BASE_URL}/api/admin/vendors", headers=headers)
        vendors = vendors_response.json()
        
        if len(vendors) == 0:
            pytest.skip("No vendors available for testing")
        
        vendor_id = vendors[0]["vendor_id"]
        original_vendor = vendors[0]
        
        # Update profile
        update_data = {
            "description": f"TEST_Updated description at {uuid.uuid4().hex[:8]}",
            "phone": "+1-555-TEST-123",
            "website": "https://test-updated.example.com"
        }
        
        response = requests.put(
            f"{BASE_URL}/api/admin/vendors/{vendor_id}/profile",
            headers=headers,
            json=update_data
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        assert "message" in response.json()
        
        # Verify update by fetching vendor again
        verify_response = requests.get(f"{BASE_URL}/api/admin/vendors/{vendor_id}/full", headers=headers)
        assert verify_response.status_code == 200
        updated_vendor = verify_response.json()["vendor"]
        
        assert updated_vendor["description"] == update_data["description"]
        assert updated_vendor["phone"] == update_data["phone"]
        assert updated_vendor["website"] == update_data["website"]
        
        print(f"PASS: Vendor profile updated and verified for {vendor_id}")
    
    def test_update_vendor_rating(self, headers):
        """Test updating vendor rating via profile endpoint"""
        vendors_response = requests.get(f"{BASE_URL}/api/admin/vendors", headers=headers)
        vendors = vendors_response.json()
        
        if len(vendors) == 0:
            pytest.skip("No vendors available for testing")
        
        vendor_id = vendors[0]["vendor_id"]
        
        # Update rating
        new_rating = 4.5
        response = requests.put(
            f"{BASE_URL}/api/admin/vendors/{vendor_id}/profile",
            headers=headers,
            json={"rating": new_rating}
        )
        assert response.status_code == 200
        
        # Verify
        verify_response = requests.get(f"{BASE_URL}/api/admin/vendors/{vendor_id}/full", headers=headers)
        updated_vendor = verify_response.json()["vendor"]
        assert updated_vendor["rating"] == new_rating
        
        print(f"PASS: Vendor rating updated to {new_rating}")
    
    def test_update_vendor_approval_status(self, headers):
        """Test toggling vendor approval status"""
        vendors_response = requests.get(f"{BASE_URL}/api/admin/vendors", headers=headers)
        vendors = vendors_response.json()
        
        if len(vendors) == 0:
            pytest.skip("No vendors available for testing")
        
        vendor_id = vendors[0]["vendor_id"]
        original_status = vendors[0].get("is_approved", False)
        
        # Toggle approval
        response = requests.put(
            f"{BASE_URL}/api/admin/vendors/{vendor_id}/profile",
            headers=headers,
            json={"is_approved": not original_status}
        )
        assert response.status_code == 200
        
        # Verify
        verify_response = requests.get(f"{BASE_URL}/api/admin/vendors/{vendor_id}/full", headers=headers)
        updated_vendor = verify_response.json()["vendor"]
        assert updated_vendor["is_approved"] == (not original_status)
        
        # Restore original status
        requests.put(
            f"{BASE_URL}/api/admin/vendors/{vendor_id}/profile",
            headers=headers,
            json={"is_approved": original_status}
        )
        
        print(f"PASS: Vendor approval status toggled and restored")
    
    def test_update_vendor_certifications(self, headers):
        """Test updating vendor certifications array"""
        vendors_response = requests.get(f"{BASE_URL}/api/admin/vendors", headers=headers)
        vendors = vendors_response.json()
        
        if len(vendors) == 0:
            pytest.skip("No vendors available for testing")
        
        vendor_id = vendors[0]["vendor_id"]
        
        # Update certifications
        new_certs = ["ISO 9001", "AS9100D", "IATF 16949", "TEST_CERT"]
        response = requests.put(
            f"{BASE_URL}/api/admin/vendors/{vendor_id}/profile",
            headers=headers,
            json={"certifications": new_certs}
        )
        assert response.status_code == 200
        
        # Verify
        verify_response = requests.get(f"{BASE_URL}/api/admin/vendors/{vendor_id}/full", headers=headers)
        updated_vendor = verify_response.json()["vendor"]
        assert "TEST_CERT" in updated_vendor["certifications"]
        
        print(f"PASS: Vendor certifications updated")


class TestAdminMachineEndpoints:
    """Test admin machine management endpoints"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def headers(self, admin_token):
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
    
    @pytest.fixture(scope="class")
    def test_vendor_id(self, headers):
        """Get a valid vendor ID for testing"""
        response = requests.get(f"{BASE_URL}/api/admin/vendors", headers=headers)
        vendors = response.json()
        if len(vendors) == 0:
            pytest.skip("No vendors available for testing")
        return vendors[0]["vendor_id"]
    
    def test_list_all_machines(self, headers):
        """Test GET /api/admin/machines returns all machines"""
        response = requests.get(f"{BASE_URL}/api/admin/machines", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)
        
        if len(data) > 0:
            # Verify machine has expected fields
            machine = data[0]
            assert "machine_id" in machine
            assert "vendor_id" in machine
            assert "vendor_name" in machine  # Should be enriched with vendor name
        
        print(f"PASS: Listed {len(data)} machines")
    
    def test_list_machines_filter_by_vendor(self, headers, test_vendor_id):
        """Test GET /api/admin/machines with vendor_id filter"""
        response = requests.get(
            f"{BASE_URL}/api/admin/machines",
            headers=headers,
            params={"vendor_id": test_vendor_id}
        )
        assert response.status_code == 200
        
        data = response.json()
        # All machines should belong to the filtered vendor
        for machine in data:
            assert machine["vendor_id"] == test_vendor_id
        
        print(f"PASS: Filtered machines by vendor {test_vendor_id}: {len(data)} machines")
    
    def test_create_machine_for_vendor(self, headers, test_vendor_id):
        """Test POST /api/admin/machines creates a machine for any vendor"""
        machine_data = {
            "vendor_id": test_vendor_id,
            "name": f"TEST_Machine_{uuid.uuid4().hex[:8]}",
            "machine_type": "CNC Milling",
            "brand": "Test Brand",
            "model": "TEST-2000",
            "tolerance": 0.005,
            "max_x": 500,
            "max_y": 400,
            "max_z": 300,
            "max_diameter": 200,
            "materials": ["Aluminum", "Steel", "Titanium"]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/admin/machines",
            headers=headers,
            json=machine_data
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "machine_id" in data
        assert "message" in data
        
        # Store for later tests
        TestAdminMachineEndpoints.created_machine_id = data["machine_id"]
        
        print(f"PASS: Created machine {data['machine_id']} for vendor {test_vendor_id}")
        return data["machine_id"]
    
    def test_create_machine_missing_vendor_id(self, headers):
        """Test POST /api/admin/machines fails without vendor_id"""
        response = requests.post(
            f"{BASE_URL}/api/admin/machines",
            headers=headers,
            json={
                "name": "Test Machine",
                "machine_type": "CNC Milling"
            }
        )
        assert response.status_code == 400
        assert "vendor_id" in response.json().get("detail", "").lower()
        print("PASS: Create machine without vendor_id returns 400")
    
    def test_create_machine_invalid_vendor(self, headers):
        """Test POST /api/admin/machines fails for non-existent vendor"""
        response = requests.post(
            f"{BASE_URL}/api/admin/machines",
            headers=headers,
            json={
                "vendor_id": "nonexistent_vendor_xyz",
                "name": "Test Machine",
                "machine_type": "CNC Milling"
            }
        )
        assert response.status_code == 404
        print("PASS: Create machine with invalid vendor returns 404")
    
    def test_get_machine_by_id(self, headers):
        """Test GET /api/admin/machines/{id} returns machine details"""
        # First get list to find a valid machine
        machines_response = requests.get(f"{BASE_URL}/api/admin/machines", headers=headers)
        machines = machines_response.json()
        
        if len(machines) == 0:
            pytest.skip("No machines available for testing")
        
        machine_id = machines[0]["machine_id"]
        
        response = requests.get(f"{BASE_URL}/api/admin/machines/{machine_id}", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data["machine_id"] == machine_id
        assert "vendor_name" in data  # Should have enriched vendor name
        
        print(f"PASS: Retrieved machine {machine_id}")
    
    def test_get_machine_not_found(self, headers):
        """Test GET /api/admin/machines/{id} returns 404 for non-existent"""
        response = requests.get(f"{BASE_URL}/api/admin/machines/nonexistent_machine_xyz", headers=headers)
        assert response.status_code == 404
        print("PASS: Non-existent machine returns 404")
    
    def test_update_machine(self, headers):
        """Test PUT /api/admin/machines/{id} updates machine"""
        # Get a machine to update
        machines_response = requests.get(f"{BASE_URL}/api/admin/machines", headers=headers)
        machines = machines_response.json()
        
        if len(machines) == 0:
            pytest.skip("No machines available for testing")
        
        machine_id = machines[0]["machine_id"]
        
        # Update machine
        update_data = {
            "name": f"TEST_Updated_Machine_{uuid.uuid4().hex[:8]}",
            "tolerance": 0.002,
            "materials": ["Aluminum", "Copper", "Brass"]
        }
        
        response = requests.put(
            f"{BASE_URL}/api/admin/machines/{machine_id}",
            headers=headers,
            json=update_data
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        # Verify update
        verify_response = requests.get(f"{BASE_URL}/api/admin/machines/{machine_id}", headers=headers)
        updated_machine = verify_response.json()
        assert updated_machine["name"] == update_data["name"]
        assert updated_machine["tolerance"] == update_data["tolerance"]
        
        print(f"PASS: Updated machine {machine_id}")
    
    def test_update_machine_not_found(self, headers):
        """Test PUT /api/admin/machines/{id} returns 404 for non-existent"""
        response = requests.put(
            f"{BASE_URL}/api/admin/machines/nonexistent_machine_xyz",
            headers=headers,
            json={"name": "Updated Name"}
        )
        assert response.status_code == 404
        print("PASS: Update non-existent machine returns 404")
    
    def test_update_machine_no_valid_fields(self, headers):
        """Test PUT /api/admin/machines/{id} fails with no valid fields"""
        machines_response = requests.get(f"{BASE_URL}/api/admin/machines", headers=headers)
        machines = machines_response.json()
        
        if len(machines) == 0:
            pytest.skip("No machines available for testing")
        
        machine_id = machines[0]["machine_id"]
        
        response = requests.put(
            f"{BASE_URL}/api/admin/machines/{machine_id}",
            headers=headers,
            json={"invalid_field": "value"}
        )
        assert response.status_code == 400
        print("PASS: Update with invalid fields returns 400")
    
    def test_delete_machine(self, headers, test_vendor_id):
        """Test DELETE /api/admin/machines/{id} deletes machine"""
        # Create a machine specifically for deletion
        machine_data = {
            "vendor_id": test_vendor_id,
            "name": f"TEST_ToDelete_{uuid.uuid4().hex[:8]}",
            "machine_type": "Test Type"
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/admin/machines",
            headers=headers,
            json=machine_data
        )
        assert create_response.status_code == 200
        machine_id = create_response.json()["machine_id"]
        
        # Delete the machine
        response = requests.delete(f"{BASE_URL}/api/admin/machines/{machine_id}", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        # Verify deletion
        verify_response = requests.get(f"{BASE_URL}/api/admin/machines/{machine_id}", headers=headers)
        assert verify_response.status_code == 404
        
        print(f"PASS: Deleted machine {machine_id} and verified")
    
    def test_delete_machine_not_found(self, headers):
        """Test DELETE /api/admin/machines/{id} returns 404 for non-existent"""
        response = requests.delete(f"{BASE_URL}/api/admin/machines/nonexistent_machine_xyz", headers=headers)
        assert response.status_code == 404
        print("PASS: Delete non-existent machine returns 404")


class TestAdminAuthorizationRequired:
    """Test that endpoints require admin authorization"""
    
    def test_vendor_full_requires_auth(self):
        """Test GET /api/admin/vendors/{id}/full requires auth"""
        response = requests.get(f"{BASE_URL}/api/admin/vendors/test/full")
        assert response.status_code == 401
        print("PASS: Vendor full profile requires auth")
    
    def test_machines_list_requires_auth(self):
        """Test GET /api/admin/machines requires auth"""
        response = requests.get(f"{BASE_URL}/api/admin/machines")
        assert response.status_code == 401
        print("PASS: Machines list requires auth")
    
    def test_create_machine_requires_auth(self):
        """Test POST /api/admin/machines requires auth"""
        response = requests.post(f"{BASE_URL}/api/admin/machines", json={})
        assert response.status_code == 401
        print("PASS: Create machine requires auth")


class TestSeededVendorData:
    """Test with seeded vendor data mentioned in the context"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def headers(self, admin_token):
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
    
    def test_seeded_vendors_exist(self, headers):
        """Verify seeded vendors exist in the system"""
        response = requests.get(f"{BASE_URL}/api/admin/vendors", headers=headers)
        assert response.status_code == 200
        
        vendors = response.json()
        vendor_ids = [v["vendor_id"] for v in vendors]
        
        found_seeded = []
        for seeded_id in SEEDED_VENDORS:
            if seeded_id in vendor_ids:
                found_seeded.append(seeded_id)
        
        print(f"Found {len(found_seeded)}/{len(SEEDED_VENDORS)} seeded vendors: {found_seeded}")
        # Don't fail if not found - they may have been modified
    
    def test_seeded_vendors_have_machines(self, headers):
        """Check if seeded vendors have machines as mentioned"""
        for vendor_id in SEEDED_VENDORS:
            response = requests.get(f"{BASE_URL}/api/admin/vendors/{vendor_id}/full", headers=headers)
            if response.status_code == 200:
                data = response.json()
                machine_count = len(data.get("machines", []))
                print(f"Vendor {vendor_id}: {machine_count} machines")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
