"""
Test suite for Role-Based Access Control (RBAC) module
Tests all RBAC endpoints including permissions, roles, and user assignment
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL')

# Test credentials
ADMIN_EMAIL = "admin@offoadex.com"
ADMIN_PASSWORD = "admin123"
TEST_ROLE_NAME = "TEST_Quality_Manager"


class TestRBACBackend:
    """Test RBAC API endpoints"""
    
    admin_token = None
    created_role_id = None
    
    @pytest.fixture(autouse=True)
    def setup_session(self):
        """Setup requests session with admin auth"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        if not TestRBACBackend.admin_token:
            response = self.session.post(f"{BASE_URL}/api/auth/login", json={
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD
            })
            if response.status_code == 200:
                TestRBACBackend.admin_token = response.json().get("access_token")
            else:
                pytest.skip(f"Admin login failed: {response.status_code}")
        
        self.session.headers.update({"Authorization": f"Bearer {TestRBACBackend.admin_token}"})
    
    # ============== GET /api/admin/permissions ==============
    def test_get_permissions_returns_all_permissions(self):
        """Test GET /api/admin/permissions returns all 47 permissions grouped by 11 modules"""
        response = self.session.get(f"{BASE_URL}/api/admin/permissions")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "permissions" in data, "Response should contain 'permissions'"
        assert "permissions_list" in data, "Response should contain 'permissions_list'"
        
        # Verify grouped permissions
        permissions = data["permissions"]
        assert isinstance(permissions, dict), "Permissions should be grouped by module"
        
        # Verify expected modules exist (11 modules)
        expected_modules = [
            "User Management", "Vendor Management", "Buyer Management",
            "RFQ Management", "Quote Management", "Order Management",
            "Payments & Finance", "WhatsApp", "Analytics",
            "Disputes", "System Admin"
        ]
        for module in expected_modules:
            assert module in permissions, f"Module '{module}' should exist in permissions"
        
        # Verify permissions_list is flat list with 47 permissions
        permissions_list = data["permissions_list"]
        assert isinstance(permissions_list, list), "permissions_list should be a list"
        assert len(permissions_list) == 47, f"Expected 47 permissions, got {len(permissions_list)}"
        
        # Verify permission structure
        if permissions_list:
            perm = permissions_list[0]
            assert "id" in perm, "Permission should have 'id'"
            assert "label" in perm, "Permission should have 'label'"
            assert "module" in perm, "Permission should have 'module'"
            assert "description" in perm, "Permission should have 'description'"
        
        print(f"PASS: GET /api/admin/permissions returns {len(permissions_list)} permissions across {len(permissions)} modules")
    
    def test_get_permissions_requires_admin(self):
        """Test GET /api/admin/permissions returns 403 for non-admin"""
        # Create session without auth
        no_auth_session = requests.Session()
        response = no_auth_session.get(f"{BASE_URL}/api/admin/permissions")
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: GET /api/admin/permissions requires authentication")
    
    # ============== GET /api/admin/roles ==============
    def test_get_roles_returns_all_roles(self):
        """Test GET /api/admin/roles returns all roles including system and custom"""
        response = self.session.get(f"{BASE_URL}/api/admin/roles")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "roles" in data, "Response should contain 'roles'"
        assert "total" in data, "Response should contain 'total'"
        
        roles = data["roles"]
        assert isinstance(roles, list), "Roles should be a list"
        assert len(roles) >= 7, f"Expected at least 7 default roles, got {len(roles)}"
        
        # Verify role structure
        if roles:
            role = roles[0]
            assert "role_id" in role, "Role should have 'role_id'"
            assert "name" in role, "Role should have 'name'"
            assert "permissions" in role, "Role should have 'permissions'"
        
        # Verify default system roles exist
        role_ids = [r["role_id"] for r in roles]
        expected_system_roles = ["super_admin", "admin", "sales_manager", "support_agent", "finance_admin", "vendor", "buyer"]
        for role_id in expected_system_roles:
            assert role_id in role_ids, f"System role '{role_id}' should exist"
        
        print(f"PASS: GET /api/admin/roles returns {len(roles)} roles")
    
    def test_get_roles_exclude_base_roles(self):
        """Test GET /api/admin/roles with include_base_roles=false"""
        response = self.session.get(f"{BASE_URL}/api/admin/roles?include_base_roles=false")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        roles = data["roles"]
        
        # Verify base roles are excluded
        for role in roles:
            if role.get("is_base_role"):
                pytest.fail(f"Base role '{role['role_id']}' should be excluded")
        
        print(f"PASS: GET /api/admin/roles with include_base_roles=false returns {len(roles)} roles")
    
    # ============== POST /api/admin/roles ==============
    def test_create_custom_role(self):
        """Test POST /api/admin/roles creates a new custom role"""
        # Cleanup - delete if exists
        cleanup_response = self.session.delete(f"{BASE_URL}/api/admin/roles/{TEST_ROLE_NAME.lower().replace(' ', '_')}")
        
        role_data = {
            "name": TEST_ROLE_NAME,
            "description": "Test role for quality management",
            "permissions": ["rfqs.view", "quotes.view", "orders.view", "orders.update_status"],
            "color": "#059669"
        }
        
        response = self.session.post(f"{BASE_URL}/api/admin/roles", json=role_data)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True, "Response should indicate success"
        assert "role" in data, "Response should contain 'role'"
        
        role = data["role"]
        assert role["name"] == TEST_ROLE_NAME, f"Role name should be '{TEST_ROLE_NAME}'"
        assert role["is_system"] == False, "Custom role should not be a system role"
        assert len(role["permissions"]) == 4, "Role should have 4 permissions"
        
        TestRBACBackend.created_role_id = role["role_id"]
        print(f"PASS: POST /api/admin/roles created role '{role['role_id']}'")
    
    def test_create_role_duplicate_name_fails(self):
        """Test POST /api/admin/roles fails for duplicate name"""
        role_data = {
            "name": "Admin",  # System role name
            "description": "Duplicate role",
            "permissions": ["rfqs.view"]
        }
        
        response = self.session.post(f"{BASE_URL}/api/admin/roles", json=role_data)
        
        assert response.status_code == 400, f"Expected 400 for duplicate, got {response.status_code}"
        print("PASS: POST /api/admin/roles rejects duplicate role names")
    
    # ============== PUT /api/admin/roles/{role_id} ==============
    def test_update_custom_role(self):
        """Test PUT /api/admin/roles/{role_id} updates role permissions"""
        if not TestRBACBackend.created_role_id:
            pytest.skip("No custom role created")
        
        update_data = {
            "description": "Updated test role description",
            "permissions": ["rfqs.view", "quotes.view", "orders.view", "orders.update_status", "disputes.view"]
        }
        
        response = self.session.put(
            f"{BASE_URL}/api/admin/roles/{TestRBACBackend.created_role_id}",
            json=update_data
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True, "Response should indicate success"
        
        role = data["role"]
        assert len(role["permissions"]) == 5, "Role should now have 5 permissions"
        assert "disputes.view" in role["permissions"], "Role should have disputes.view permission"
        
        print(f"PASS: PUT /api/admin/roles/{TestRBACBackend.created_role_id} updated permissions")
    
    def test_update_system_role_permissions(self):
        """Test PUT /api/admin/roles/{role_id} can update system role permissions"""
        update_data = {
            "permissions": ["users.view", "vendors.view"]  # Minimal permissions for test
        }
        
        response = self.session.put(
            f"{BASE_URL}/api/admin/roles/support_agent",
            json=update_data
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Verify original permissions can be restored
        restore_data = {
            "permissions": [
                "users.view", "vendors.view", "buyers.view",
                "rfqs.view", "quotes.view", "orders.view",
                "whatsapp.view_messages", "whatsapp.send_messages",
                "disputes.view", "disputes.manage"
            ]
        }
        
        restore_response = self.session.put(
            f"{BASE_URL}/api/admin/roles/support_agent",
            json=restore_data
        )
        assert restore_response.status_code == 200, "Should restore permissions"
        
        print("PASS: PUT /api/admin/roles allows updating system role permissions")
    
    # ============== GET /api/admin/roles/{role_id} ==============
    def test_get_single_role(self):
        """Test GET /api/admin/roles/{role_id} returns specific role"""
        response = self.session.get(f"{BASE_URL}/api/admin/roles/admin")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        role = response.json()
        assert role["role_id"] == "admin", "Should return admin role"
        assert role["name"] == "Admin", "Role name should be 'Admin'"
        assert role["is_system"] == True, "Admin should be a system role"
        assert len(role["permissions"]) > 0, "Admin should have permissions"
        
        print(f"PASS: GET /api/admin/roles/admin returns role with {len(role['permissions'])} permissions")
    
    def test_get_nonexistent_role(self):
        """Test GET /api/admin/roles/{role_id} returns 404 for invalid role"""
        response = self.session.get(f"{BASE_URL}/api/admin/roles/nonexistent_role_xyz")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: GET /api/admin/roles returns 404 for nonexistent role")
    
    # ============== POST /api/admin/roles/assign ==============
    def test_assign_role_to_user(self):
        """Test POST /api/admin/roles/assign assigns role to user"""
        # First, get a user to assign role to
        users_response = self.session.get(f"{BASE_URL}/api/admin/users")
        
        if users_response.status_code != 200:
            pytest.skip("Cannot get users list")
        
        # API returns list directly, not wrapped in object
        users_data = users_response.json()
        users = users_data if isinstance(users_data, list) else users_data.get("users", [])
        if not users:
            pytest.skip("No users available for assignment")
        
        # Find a non-admin user
        test_user = None
        for user in users:
            if user.get("role") != "admin":
                test_user = user
                break
        
        if not test_user:
            pytest.skip("No non-admin user available")
        
        # Create a role to assign if needed
        if not TestRBACBackend.created_role_id:
            role_data = {
                "name": "TEST_Temp_Role",
                "description": "Temporary test role",
                "permissions": ["rfqs.view"]
            }
            create_response = self.session.post(f"{BASE_URL}/api/admin/roles", json=role_data)
            if create_response.status_code == 200:
                TestRBACBackend.created_role_id = create_response.json()["role"]["role_id"]
            else:
                # Try using an existing system role
                TestRBACBackend.created_role_id = "sales_manager"
        
        assign_data = {
            "user_id": test_user["user_id"],
            "role_id": TestRBACBackend.created_role_id
        }
        
        response = self.session.post(f"{BASE_URL}/api/admin/roles/assign", json=assign_data)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True, "Response should indicate success"
        
        # Cleanup - remove role assignment
        cleanup_response = self.session.delete(f"{BASE_URL}/api/admin/roles/assign/{test_user['user_id']}")
        
        print(f"PASS: POST /api/admin/roles/assign assigned role to user '{test_user['user_id']}'")
    
    def test_assign_nonexistent_role_fails(self):
        """Test POST /api/admin/roles/assign fails for invalid role"""
        assign_data = {
            "user_id": "user_test",
            "role_id": "nonexistent_role_xyz"
        }
        
        response = self.session.post(f"{BASE_URL}/api/admin/roles/assign", json=assign_data)
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("PASS: POST /api/admin/roles/assign rejects nonexistent role")
    
    # ============== DELETE /api/admin/roles/{role_id} ==============
    def test_delete_system_role_fails(self):
        """Test DELETE /api/admin/roles/{role_id} fails for system roles"""
        response = self.session.delete(f"{BASE_URL}/api/admin/roles/admin")
        
        assert response.status_code == 400, f"Expected 400 for system role, got {response.status_code}"
        print("PASS: DELETE /api/admin/roles rejects deletion of system roles")
    
    def test_delete_custom_role(self):
        """Test DELETE /api/admin/roles/{role_id} deletes custom role"""
        # Create a role to delete
        role_data = {
            "name": "TEST_Delete_Role",
            "description": "Role to be deleted",
            "permissions": ["rfqs.view"]
        }
        
        create_response = self.session.post(f"{BASE_URL}/api/admin/roles", json=role_data)
        
        if create_response.status_code != 200:
            pytest.skip("Could not create role to delete")
        
        role_id = create_response.json()["role"]["role_id"]
        
        # Delete the role
        response = self.session.delete(f"{BASE_URL}/api/admin/roles/{role_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("success") == True, "Response should indicate success"
        
        # Verify role is deleted
        get_response = self.session.get(f"{BASE_URL}/api/admin/roles/{role_id}")
        assert get_response.status_code == 404, "Deleted role should return 404"
        
        print(f"PASS: DELETE /api/admin/roles/{role_id} deleted custom role")
    
    # ============== GET /api/user/permissions ==============
    def test_get_user_permissions(self):
        """Test GET /api/user/permissions returns current user's permissions"""
        response = self.session.get(f"{BASE_URL}/api/user/permissions")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "permissions" in data, "Response should contain 'permissions'"
        assert "total" in data, "Response should contain 'total'"
        
        permissions = data["permissions"]
        assert isinstance(permissions, list), "Permissions should be a list"
        assert len(permissions) > 0, "Admin should have permissions"
        
        print(f"PASS: GET /api/user/permissions returns {len(permissions)} permissions for current user")
    
    # ============== GET /api/admin/roles/{role_id}/users ==============
    def test_get_users_by_role(self):
        """Test GET /api/admin/roles/{role_id}/users returns users with role"""
        # Get users with admin role
        response = self.session.get(f"{BASE_URL}/api/admin/roles/admin/users")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "users" in data, "Response should contain 'users'"
        assert "total" in data, "Response should contain 'total'"
        
        print(f"PASS: GET /api/admin/roles/admin/users returns {data['total']} users")
    
    # ============== Cleanup ==============
    def test_zz_cleanup(self):
        """Cleanup: Delete test role created during tests"""
        if TestRBACBackend.created_role_id:
            # First remove any user assignments
            users_response = self.session.get(f"{BASE_URL}/api/admin/roles/{TestRBACBackend.created_role_id}/users")
            if users_response.status_code == 200:
                users = users_response.json().get("users", [])
                for user in users:
                    self.session.delete(f"{BASE_URL}/api/admin/roles/assign/{user['user_id']}")
            
            # Delete the role
            response = self.session.delete(f"{BASE_URL}/api/admin/roles/{TestRBACBackend.created_role_id}")
            print(f"Cleanup: Deleted test role '{TestRBACBackend.created_role_id}'")
        
        print("PASS: Cleanup completed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
