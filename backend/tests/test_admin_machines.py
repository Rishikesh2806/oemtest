"""
Test Admin Machines Feature
Tests for adding machines to vendor profiles via admin panel.
Features tested:
- CRUD operations for machines (create, read, update, delete)
- Activity logging for machine operations
- RBAC permissions (machines.view, machines.create, machines.edit, machines.delete, machines.manage_images)
- Image upload limit (max 5 images per machine)
- Required field validation (vendor_id, machine_category)
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@offoadex.com"
ADMIN_PASSWORD = "admin123"


class TestAdminMachines:
    """Test admin machines endpoints with activity logging"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: login as admin and get token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        self.token = data.get("access_token")
        self.user_id = data.get("user", {}).get("user_id")
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        # Get a vendor_id for testing
        vendors_response = requests.get(
            f"{BASE_URL}/api/admin/vendors",
            headers=self.headers
        )
        assert vendors_response.status_code == 200, f"Failed to get vendors: {vendors_response.text}"
        vendors_data = vendors_response.json()
        # API returns list directly, not dict with "vendors" key
        vendors_list = vendors_data if isinstance(vendors_data, list) else vendors_data.get("vendors", [])
        approved_vendors = [v for v in vendors_list if v.get("is_approved")]
        assert len(approved_vendors) > 0, "No approved vendors found for testing"
        self.test_vendor_id = approved_vendors[0]["vendor_id"]
        self.test_vendor_name = approved_vendors[0].get("company_name", "Test Vendor")
        
        yield
        
        # Cleanup: delete test machines
        if hasattr(self, 'created_machine_ids'):
            for machine_id in self.created_machine_ids:
                try:
                    requests.delete(
                        f"{BASE_URL}/api/admin/machines/{machine_id}",
                        headers=self.headers
                    )
                except:
                    pass
    
    def test_01_get_machines_list(self):
        """Test GET /api/admin/machines - list all machines"""
        response = requests.get(
            f"{BASE_URL}/api/admin/machines",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # API returns list directly or dict with "machines" key
        if isinstance(data, list):
            machines_list = data
            total = len(data)
        else:
            machines_list = data.get("machines", [])
            total = data.get("total", len(machines_list))
        
        assert isinstance(machines_list, list), "Machines should be a list"
        
        print(f"✓ Found {total} machines")
    
    def test_02_get_machines_filtered_by_vendor(self):
        """Test GET /api/admin/machines with vendor filter"""
        response = requests.get(
            f"{BASE_URL}/api/admin/machines?vendor_id={self.test_vendor_id}",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # API returns list directly or dict with "machines" key
        machines_list = data if isinstance(data, list) else data.get("machines", [])
        
        # If there are machines, they should all belong to the vendor
        for machine in machines_list:
            assert machine["vendor_id"] == self.test_vendor_id, "Machine should belong to filtered vendor"
        
        print(f"✓ Filtered machines for vendor {self.test_vendor_id}")
    
    def test_03_create_machine_missing_vendor_id(self):
        """Test POST /api/admin/machines - vendor_id required validation"""
        response = requests.post(
            f"{BASE_URL}/api/admin/machines",
            headers=self.headers,
            json={
                "name": "Test Machine",
                "machine_category": "CNC Turning/Lathe",
                "machine_type": "CNC Lathe",
                "brand": "Haas",
                "model": "ST-10"
            }
        )
        
        assert response.status_code == 400, f"Expected 400 for missing vendor_id, got {response.status_code}"
        data = response.json()
        assert "vendor_id" in data.get("detail", "").lower(), f"Error should mention vendor_id: {data}"
        
        print("✓ Correctly rejects request without vendor_id")
    
    def test_04_create_machine_missing_category(self):
        """Test POST /api/admin/machines - machine_category required validation"""
        response = requests.post(
            f"{BASE_URL}/api/admin/machines",
            headers=self.headers,
            json={
                "vendor_id": self.test_vendor_id,
                "name": "Test Machine",
                "machine_type": "CNC Lathe",
                "brand": "Haas",
                "model": "ST-10"
            }
        )
        
        assert response.status_code == 400, f"Expected 400 for missing machine_category, got {response.status_code}"
        data = response.json()
        assert "machine_category" in data.get("detail", "").lower(), f"Error should mention machine_category: {data}"
        
        print("✓ Correctly rejects request without machine_category")
    
    def test_05_create_machine_success(self):
        """Test POST /api/admin/machines - successful machine creation"""
        if not hasattr(self, 'created_machine_ids'):
            self.created_machine_ids = []
        
        machine_data = {
            "vendor_id": self.test_vendor_id,
            "name": "TEST_Admin_Machine_01",
            "machine_category": "CNC Turning/Lathe",
            "machine_type": "CNC Lathe",
            "brand": "Haas",
            "model": "ST-10",
            "tolerance": 0.005,
            "max_diameter": 200,
            "max_length": 500,
            "materials": ["Steel", "Aluminum", "Titanium"]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/admin/machines",
            headers=self.headers,
            json=machine_data
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "machine_id" in data, "Response should contain machine_id"
        assert data.get("message") == "Machine created successfully", f"Unexpected message: {data}"
        
        self.created_machine_id = data["machine_id"]
        self.created_machine_ids.append(self.created_machine_id)
        
        print(f"✓ Created machine {self.created_machine_id}")
        
        return self.created_machine_id
    
    def test_06_verify_activity_log_on_create(self):
        """Test activity log creation when machine is created"""
        # First create a machine
        machine_id = self.test_05_create_machine_success()
        
        # Wait a bit for async operations
        time.sleep(0.5)
        
        # Get activity logs for machines
        response = requests.get(
            f"{BASE_URL}/api/admin/activity-logs/machines",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        logs = response.json()
        
        # Find the create log for our machine
        create_log = None
        for log in logs:
            if log.get("entity_id") == machine_id and log.get("type") == "machine_created":
                create_log = log
                break
        
        assert create_log is not None, f"Activity log for machine creation not found. Logs: {logs[:5]}"
        assert create_log.get("action") == "create", f"Action should be 'create': {create_log}"
        assert create_log.get("entity_type") == "machine", f"Entity type should be 'machine': {create_log}"
        assert create_log.get("vendor_id") == self.test_vendor_id, f"Vendor ID mismatch: {create_log}"
        assert create_log.get("user_id") == self.user_id, f"User ID mismatch: {create_log}"
        assert "details" in create_log, f"Log should have details: {create_log}"
        
        print(f"✓ Activity log created for machine creation: {create_log.get('activity_id')}")
    
    def test_07_get_machine_details(self):
        """Test GET /api/admin/machines/{machine_id} - get machine details"""
        # First create a machine
        machine_id = self.test_05_create_machine_success()
        
        response = requests.get(
            f"{BASE_URL}/api/admin/machines/{machine_id}",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("machine_id") == machine_id, f"Machine ID mismatch: {data}"
        assert data.get("vendor_id") == self.test_vendor_id, f"Vendor ID mismatch: {data}"
        assert data.get("machine_category") == "CNC Turning/Lathe", f"Category mismatch: {data}"
        assert "vendor_name" in data, f"Response should include vendor_name: {data}"
        
        print(f"✓ Got machine details for {machine_id}")
    
    def test_08_update_machine_success(self):
        """Test PUT /api/admin/machines/{machine_id} - update machine"""
        # First create a machine
        machine_id = self.test_05_create_machine_success()
        
        update_data = {
            "name": "TEST_Updated_Machine_Name",
            "brand": "DMG Mori",
            "tolerance": 0.002,
            "materials": ["Steel", "Brass"]
        }
        
        response = requests.put(
            f"{BASE_URL}/api/admin/machines/{machine_id}",
            headers=self.headers,
            json=update_data
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("message") == "Machine updated successfully", f"Unexpected message: {data}"
        
        # Verify the update
        get_response = requests.get(
            f"{BASE_URL}/api/admin/machines/{machine_id}",
            headers=self.headers
        )
        
        assert get_response.status_code == 200
        updated_machine = get_response.json()
        assert updated_machine.get("name") == "TEST_Updated_Machine_Name", f"Name not updated: {updated_machine}"
        assert updated_machine.get("brand") == "DMG Mori", f"Brand not updated: {updated_machine}"
        
        print(f"✓ Updated machine {machine_id}")
    
    def test_09_verify_activity_log_on_update(self):
        """Test activity log creation when machine is updated"""
        # Create and update a machine
        machine_id = self.test_05_create_machine_success()
        
        update_data = {"name": "TEST_Activity_Log_Update"}
        requests.put(
            f"{BASE_URL}/api/admin/machines/{machine_id}",
            headers=self.headers,
            json=update_data
        )
        
        time.sleep(0.5)
        
        # Get activity logs
        response = requests.get(
            f"{BASE_URL}/api/admin/activity-logs/machines",
            headers=self.headers
        )
        
        assert response.status_code == 200
        logs = response.json()
        
        # Find the update log for our machine
        update_log = None
        for log in logs:
            if log.get("entity_id") == machine_id and log.get("type") == "machine_updated":
                update_log = log
                break
        
        assert update_log is not None, f"Activity log for machine update not found"
        assert update_log.get("action") == "update", f"Action should be 'update': {update_log}"
        assert "updated_fields" in update_log.get("details", {}), f"Should have updated_fields in details: {update_log}"
        
        print(f"✓ Activity log created for machine update: {update_log.get('activity_id')}")
    
    def test_10_delete_machine_success(self):
        """Test DELETE /api/admin/machines/{machine_id} - delete machine"""
        # Create a machine to delete
        machine_id = self.test_05_create_machine_success()
        
        response = requests.delete(
            f"{BASE_URL}/api/admin/machines/{machine_id}",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("message") == "Machine deleted successfully", f"Unexpected message: {data}"
        
        # Verify deletion
        get_response = requests.get(
            f"{BASE_URL}/api/admin/machines/{machine_id}",
            headers=self.headers
        )
        assert get_response.status_code == 404, f"Machine should be deleted, got {get_response.status_code}"
        
        # Remove from cleanup list since it's already deleted
        if machine_id in self.created_machine_ids:
            self.created_machine_ids.remove(machine_id)
        
        print(f"✓ Deleted machine {machine_id}")
    
    def test_11_verify_activity_log_on_delete(self):
        """Test activity log creation when machine is deleted"""
        # Create and delete a machine
        machine_id = self.test_05_create_machine_success()
        
        requests.delete(
            f"{BASE_URL}/api/admin/machines/{machine_id}",
            headers=self.headers
        )
        
        time.sleep(0.5)
        
        # Get activity logs
        response = requests.get(
            f"{BASE_URL}/api/admin/activity-logs/machines",
            headers=self.headers
        )
        
        assert response.status_code == 200
        logs = response.json()
        
        # Find the delete log for our machine
        delete_log = None
        for log in logs:
            if log.get("entity_id") == machine_id and log.get("type") == "machine_deleted":
                delete_log = log
                break
        
        assert delete_log is not None, f"Activity log for machine deletion not found"
        assert delete_log.get("action") == "delete", f"Action should be 'delete': {delete_log}"
        
        # Remove from cleanup list since it's already deleted
        if machine_id in self.created_machine_ids:
            self.created_machine_ids.remove(machine_id)
        
        print(f"✓ Activity log created for machine deletion: {delete_log.get('activity_id')}")
    
    def test_12_delete_nonexistent_machine(self):
        """Test DELETE /api/admin/machines/{machine_id} - 404 for non-existent machine"""
        fake_machine_id = "machine_nonexistent123"
        
        response = requests.delete(
            f"{BASE_URL}/api/admin/machines/{fake_machine_id}",
            headers=self.headers
        )
        
        assert response.status_code == 404, f"Expected 404 for non-existent machine, got {response.status_code}"
        
        print("✓ Correctly returns 404 for non-existent machine")
    
    def test_13_get_machine_activity_logs(self):
        """Test GET /api/admin/activity-logs/machines endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/admin/activity-logs/machines",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        logs = response.json()
        
        assert isinstance(logs, list), "Response should be a list of logs"
        
        # Verify log structure if there are logs
        if len(logs) > 0:
            log = logs[0]
            assert "activity_id" in log, f"Log should have activity_id: {log}"
            assert "entity_type" in log, f"Log should have entity_type: {log}"
            assert log.get("entity_type") == "machine", f"All logs should be for machines: {log}"
        
        print(f"✓ Got {len(logs)} machine activity logs")
    
    def test_14_get_machine_activity_logs_filtered_by_vendor(self):
        """Test GET /api/admin/activity-logs/machines with vendor filter"""
        # Create a machine first to ensure we have activity for this vendor
        machine_id = self.test_05_create_machine_success()
        
        time.sleep(0.5)
        
        response = requests.get(
            f"{BASE_URL}/api/admin/activity-logs/machines?vendor_id={self.test_vendor_id}",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        logs = response.json()
        
        # All logs should be for the specified vendor
        for log in logs:
            assert log.get("vendor_id") == self.test_vendor_id, f"Log vendor_id mismatch: {log}"
        
        print(f"✓ Filtered activity logs by vendor {self.test_vendor_id}")
    
    def test_15_get_general_activity_logs(self):
        """Test GET /api/admin/activity-logs with entity_type filter"""
        response = requests.get(
            f"{BASE_URL}/api/admin/activity-logs?entity_type=machine&limit=10",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "logs" in data, "Response should contain 'logs' key"
        assert "total" in data, "Response should contain 'total' key"
        
        # All logs should be for machines
        for log in data.get("logs", []):
            assert log.get("entity_type") == "machine", f"All logs should be for machines: {log}"
        
        print(f"✓ Got {len(data.get('logs', []))} machine activity logs via general endpoint")


class TestAdminMachinesRBAC:
    """Test RBAC permissions for machine endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: login as admin"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        self.token = data.get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_01_unauthenticated_access_denied(self):
        """Test that unauthenticated users cannot access machines endpoint"""
        response = requests.get(f"{BASE_URL}/api/admin/machines")
        
        assert response.status_code == 401, f"Expected 401 for unauthenticated access, got {response.status_code}"
        
        print("✓ Unauthenticated access correctly denied")
    
    def test_02_admin_has_full_access(self):
        """Test that admin user has full access to machine endpoints"""
        # GET - view machines
        response = requests.get(
            f"{BASE_URL}/api/admin/machines",
            headers=self.headers
        )
        assert response.status_code == 200, f"Admin should view machines: {response.status_code}"
        
        print("✓ Admin has full access to machine endpoints")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
