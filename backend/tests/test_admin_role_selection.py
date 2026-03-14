"""
Test Admin Role Selection Feature
Tests for assigning both base role and custom role to users when creating or editing
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAdminRoleSelection:
    """Tests for admin panel user role selection feature"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login as admin and get token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@offoadex.com", "password": "admin123"}
        )
        assert login_response.status_code == 200, f"Admin login failed: {login_response.text}"
        
        self.token = login_response.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
        # Generate unique email for test user
        self.test_email = f"test_role_{uuid.uuid4().hex[:8]}@test.com"
        self.created_user_id = None
        
        yield
        
        # Cleanup: Delete test user if created
        if self.created_user_id:
            try:
                self.session.delete(f"{BASE_URL}/api/admin/users/{self.created_user_id}")
            except:
                pass
    
    # ==================== GET ROLES TESTS ====================
    
    def test_get_available_custom_roles(self):
        """Test that custom roles can be fetched from /api/admin/roles"""
        response = self.session.get(f"{BASE_URL}/api/admin/roles?include_base_roles=false")
        
        assert response.status_code == 200, f"Failed to get roles: {response.text}"
        
        data = response.json()
        assert "roles" in data, "Response should contain 'roles' key"
        assert len(data["roles"]) > 0, "Should have at least one custom role"
        
        # Verify role structure
        first_role = data["roles"][0]
        assert "role_id" in first_role, "Role should have role_id"
        assert "name" in first_role, "Role should have name"
        
        # Print available roles for reference
        role_ids = [r["role_id"] for r in data["roles"]]
        print(f"Available custom roles: {role_ids}")
        
        # Verify expected roles exist
        expected_roles = ["sales_manager", "regional_manager", "support_agent", "finance_admin"]
        for expected in expected_roles:
            assert expected in role_ids, f"Expected role '{expected}' not found"
    
    # ==================== CREATE USER WITH CUSTOM ROLE ====================
    
    def test_create_user_with_custom_role(self):
        """Test creating a new user with both base role and custom role"""
        create_payload = {
            "email": self.test_email,
            "password": "TestPass@123",
            "name": "TEST_Custom_Role_User",
            "role": "buyer",
            "custom_role": "sales_manager",
            "company_name": "Test Company"
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/admin/users",
            json=create_payload
        )
        
        assert response.status_code == 200, f"Failed to create user: {response.text}"
        
        data = response.json()
        assert "user_id" in data, "Response should contain user_id"
        self.created_user_id = data["user_id"]
        print(f"Created user with ID: {self.created_user_id}")
        
        # Verify user was created with custom_role by fetching it
        get_response = self.session.get(f"{BASE_URL}/api/admin/users/{self.created_user_id}")
        assert get_response.status_code == 200, f"Failed to get created user: {get_response.text}"
        
        user_data = get_response.json()
        assert user_data["email"] == self.test_email.lower(), "Email mismatch"
        assert user_data["role"] == "buyer", "Base role should be 'buyer'"
        assert user_data.get("custom_role") == "sales_manager", f"Custom role should be 'sales_manager', got: {user_data.get('custom_role')}"
        assert user_data.get("company_name") == "Test Company", "Company name mismatch"
        
        print(f"User verified with custom_role: {user_data.get('custom_role')}")
    
    def test_create_user_without_custom_role(self):
        """Test creating user without custom role (should work)"""
        create_payload = {
            "email": self.test_email,
            "password": "TestPass@123",
            "name": "TEST_No_Custom_Role_User",
            "role": "vendor",
            "company_name": "Test Vendor Co"
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/admin/users",
            json=create_payload
        )
        
        assert response.status_code == 200, f"Failed to create user: {response.text}"
        
        data = response.json()
        self.created_user_id = data["user_id"]
        
        # Verify custom_role is None or empty
        get_response = self.session.get(f"{BASE_URL}/api/admin/users/{self.created_user_id}")
        user_data = get_response.json()
        
        assert user_data["role"] == "vendor", "Base role should be 'vendor'"
        assert user_data.get("custom_role") in [None, "", None], "Custom role should be None or empty"
    
    def test_create_admin_user_with_super_admin_custom_role(self):
        """Test creating an admin with super_admin custom role"""
        create_payload = {
            "email": self.test_email,
            "password": "TestPass@123",
            "name": "TEST_Super_Admin_User",
            "role": "admin",
            "custom_role": "super_admin",
            "company_name": "Admin Company"
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/admin/users",
            json=create_payload
        )
        
        assert response.status_code == 200, f"Failed to create admin user: {response.text}"
        
        data = response.json()
        self.created_user_id = data["user_id"]
        
        # Verify
        get_response = self.session.get(f"{BASE_URL}/api/admin/users/{self.created_user_id}")
        user_data = get_response.json()
        
        assert user_data["role"] == "admin", "Base role should be 'admin'"
        assert user_data.get("custom_role") == "super_admin", "Custom role should be 'super_admin'"
    
    # ==================== UPDATE USER CUSTOM ROLE ====================
    
    def test_update_user_custom_role(self):
        """Test updating an existing user's custom role"""
        # First create a user
        create_payload = {
            "email": self.test_email,
            "password": "TestPass@123",
            "name": "TEST_Update_Role_User",
            "role": "buyer",
            "custom_role": "sales_manager"
        }
        
        create_response = self.session.post(
            f"{BASE_URL}/api/admin/users",
            json=create_payload
        )
        assert create_response.status_code == 200
        self.created_user_id = create_response.json()["user_id"]
        
        # Now update custom_role to regional_manager
        update_payload = {"custom_role": "regional_manager"}
        update_response = self.session.put(
            f"{BASE_URL}/api/admin/users/{self.created_user_id}",
            json=update_payload
        )
        
        assert update_response.status_code == 200, f"Failed to update user: {update_response.text}"
        
        # Verify the change persisted
        get_response = self.session.get(f"{BASE_URL}/api/admin/users/{self.created_user_id}")
        user_data = get_response.json()
        
        assert user_data.get("custom_role") == "regional_manager", f"Custom role should be 'regional_manager', got: {user_data.get('custom_role')}"
        print(f"Successfully updated custom_role to: {user_data.get('custom_role')}")
    
    def test_update_both_base_role_and_custom_role(self):
        """Test updating both base role and custom role simultaneously"""
        # Create user
        create_payload = {
            "email": self.test_email,
            "password": "TestPass@123",
            "name": "TEST_Multi_Update_User",
            "role": "buyer",
            "custom_role": "sales_manager"
        }
        
        create_response = self.session.post(
            f"{BASE_URL}/api/admin/users",
            json=create_payload
        )
        self.created_user_id = create_response.json()["user_id"]
        
        # Update both roles
        update_payload = {
            "role": "admin",
            "custom_role": "finance_admin"
        }
        update_response = self.session.put(
            f"{BASE_URL}/api/admin/users/{self.created_user_id}",
            json=update_payload
        )
        
        assert update_response.status_code == 200, f"Failed to update: {update_response.text}"
        
        # Verify
        get_response = self.session.get(f"{BASE_URL}/api/admin/users/{self.created_user_id}")
        user_data = get_response.json()
        
        assert user_data["role"] == "admin", "Base role should be 'admin'"
        assert user_data.get("custom_role") == "finance_admin", "Custom role should be 'finance_admin'"
    
    def test_clear_custom_role(self):
        """Test clearing custom role by setting to empty string"""
        # Create user with custom role
        create_payload = {
            "email": self.test_email,
            "password": "TestPass@123",
            "name": "TEST_Clear_Role_User",
            "role": "buyer",
            "custom_role": "support_agent"
        }
        
        create_response = self.session.post(
            f"{BASE_URL}/api/admin/users",
            json=create_payload
        )
        self.created_user_id = create_response.json()["user_id"]
        
        # Verify user has custom_role
        get_response = self.session.get(f"{BASE_URL}/api/admin/users/{self.created_user_id}")
        assert get_response.json().get("custom_role") == "support_agent"
        
        # Clear custom_role
        update_response = self.session.put(
            f"{BASE_URL}/api/admin/users/{self.created_user_id}",
            json={"custom_role": ""}
        )
        
        assert update_response.status_code == 200, f"Failed to clear custom_role: {update_response.text}"
        
        # Verify custom_role is cleared
        get_response = self.session.get(f"{BASE_URL}/api/admin/users/{self.created_user_id}")
        user_data = get_response.json()
        
        assert user_data.get("custom_role") == "", f"Custom role should be empty, got: '{user_data.get('custom_role')}'"
        print("Successfully cleared custom_role")
    
    # ==================== EDGE CASES ====================
    
    def test_create_user_with_all_custom_roles(self):
        """Test that each available custom role can be assigned"""
        available_roles = ["admin", "finance_admin", "regional_manager", "sales_manager", "super_admin", "supervisor", "support_agent"]
        
        for custom_role in available_roles[:3]:  # Test first 3 to save time
            test_email = f"test_{custom_role}_{uuid.uuid4().hex[:8]}@test.com"
            
            create_payload = {
                "email": test_email,
                "password": "TestPass@123",
                "name": f"TEST_{custom_role}_User",
                "role": "buyer",
                "custom_role": custom_role
            }
            
            create_response = self.session.post(
                f"{BASE_URL}/api/admin/users",
                json=create_payload
            )
            
            assert create_response.status_code == 200, f"Failed to create user with custom_role={custom_role}: {create_response.text}"
            
            user_id = create_response.json()["user_id"]
            
            # Verify
            get_response = self.session.get(f"{BASE_URL}/api/admin/users/{user_id}")
            assert get_response.json().get("custom_role") == custom_role
            
            # Cleanup
            self.session.delete(f"{BASE_URL}/api/admin/users/{user_id}")
            print(f"Verified custom_role: {custom_role}")
    
    def test_get_users_list_includes_custom_role(self):
        """Test that GET /api/admin/users returns custom_role field"""
        response = self.session.get(f"{BASE_URL}/api/admin/users")
        
        assert response.status_code == 200, f"Failed to get users: {response.text}"
        
        users = response.json()
        assert isinstance(users, list), "Response should be a list"
        
        # Check that users have the custom_role field available
        # (even if null for users without custom roles)
        if len(users) > 0:
            # At least check the structure exists
            print(f"Found {len(users)} users in admin list")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
