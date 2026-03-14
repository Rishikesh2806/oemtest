"""
Test Permission-Based Dashboard Quick Actions
Tests GET /api/user/permissions endpoint for each user role
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestPermissionsAPI:
    """Test /api/user/permissions endpoint for different user roles"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@offoadex.com",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def buyer_token(self):
        """Get buyer auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "buyer@offoadex.com",
            "password": "buyer123"
        })
        assert response.status_code == 200, f"Buyer login failed: {response.text}"
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def vendor_token(self):
        """Register and get vendor auth token"""
        # Try login first (user might exist)
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "testpermvendor@test.com",
            "password": "Secure@Vendor99"
        })
        if response.status_code == 200:
            return response.json()["access_token"]
        
        # Register new vendor if login fails
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "name": "TEST_Permission Vendor",
            "email": f"TEST_permvendor_{os.urandom(4).hex()}@test.com",
            "password": "Secure@Vendor99",
            "role": "vendor",
            "company_name": "TEST Manufacturing"
        })
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip(f"Could not create vendor: {response.text}")
    
    def test_permissions_endpoint_requires_auth(self):
        """Test that /api/user/permissions returns 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/user/permissions")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Permissions endpoint requires authentication")
    
    def test_admin_permissions_returned(self, admin_token):
        """Test admin user gets correct permissions"""
        response = requests.get(
            f"{BASE_URL}/api/user/permissions",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "permissions" in data, "Missing 'permissions' field"
        assert "total" in data, "Missing 'total' field"
        assert isinstance(data["permissions"], list), "Permissions should be a list"
        
        # Admin should have significant permissions (>20)
        assert data["total"] >= 20, f"Admin should have 20+ permissions, got {data['total']}"
        
        # Verify key admin permissions exist
        admin_key_permissions = [
            "users.view", "users.edit", "vendors.view", "vendors.approve",
            "rfqs.view", "analytics.view_dashboard", "admin.file_manager"
        ]
        missing = [p for p in admin_key_permissions if p not in data["permissions"]]
        assert len(missing) == 0, f"Admin missing key permissions: {missing}"
        
        print(f"✓ Admin has {data['total']} permissions")
        print(f"  Key permissions verified: {admin_key_permissions}")
    
    def test_buyer_permissions_returned(self, buyer_token):
        """Test buyer user gets correct permissions (should enable 10 dashboard actions)"""
        response = requests.get(
            f"{BASE_URL}/api/user/permissions",
            headers={"Authorization": f"Bearer {buyer_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "permissions" in data, "Missing 'permissions' field"
        assert "total" in data, "Missing 'total' field"
        
        # Buyer should have permissions matching dashboard actions
        buyer_expected_permissions = [
            "rfqs.create", "rfqs.view", "rfqs.analyze", "rfqs.match_vendors",
            "quotes.view", "quotes.approve", "quotes.negotiate",
            "orders.view", "orders.create", "disputes.view"
        ]
        
        # Check buyer has most of these permissions
        matching = [p for p in buyer_expected_permissions if p in data["permissions"]]
        assert len(matching) >= 8, f"Buyer should have at least 8 of expected permissions, got {len(matching)}"
        
        print(f"✓ Buyer has {data['total']} permissions")
        print(f"  Matching dashboard action permissions: {len(matching)}/10")
        print(f"  Permissions: {data['permissions']}")
    
    def test_vendor_permissions_returned(self, vendor_token):
        """Test vendor user gets correct permissions"""
        response = requests.get(
            f"{BASE_URL}/api/user/permissions",
            headers={"Authorization": f"Bearer {vendor_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "permissions" in data, "Missing 'permissions' field"
        assert "total" in data, "Missing 'total' field"
        
        # Vendor expected permissions
        vendor_expected_permissions = [
            "rfqs.view", "quotes.view", "quotes.create", "quotes.edit",
            "orders.view", "orders.update_status", "disputes.view"
        ]
        
        # Check vendor has most of these permissions
        matching = [p for p in vendor_expected_permissions if p in data["permissions"]]
        assert len(matching) >= 5, f"Vendor should have at least 5 of expected permissions, got {len(matching)}"
        
        print(f"✓ Vendor has {data['total']} permissions")
        print(f"  Matching dashboard action permissions: {len(matching)}/7")
        print(f"  Permissions: {data['permissions']}")
    
    def test_permissions_response_is_array_of_strings(self, buyer_token):
        """Verify permissions are returned as string array for frontend consumption"""
        response = requests.get(
            f"{BASE_URL}/api/user/permissions",
            headers={"Authorization": f"Bearer {buyer_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # All items should be strings
        assert all(isinstance(p, str) for p in data["permissions"]), "All permissions should be strings"
        
        # Permissions should follow format: module.action
        for perm in data["permissions"]:
            assert "." in perm, f"Permission '{perm}' should have format 'module.action'"
        
        print("✓ Permissions format verified (module.action)")


class TestDashboardActionMapping:
    """Test that permissions map correctly to dashboard actions"""
    
    # Dashboard action configurations from frontend
    BUYER_ACTIONS = [
        {"id": "create_rfq", "permissions": ["rfqs.create"]},
        {"id": "my_rfqs", "permissions": ["rfqs.view"]},
        {"id": "analyze_drawings", "permissions": ["rfqs.analyze"]},
        {"id": "find_vendors", "permissions": ["rfqs.match_vendors"]},
        {"id": "view_quotes", "permissions": ["quotes.view"]},
        {"id": "approve_quotes", "permissions": ["quotes.approve"]},
        {"id": "negotiate", "permissions": ["quotes.negotiate"]},
        {"id": "my_orders", "permissions": ["orders.view"]},
        {"id": "create_order", "permissions": ["orders.create"]},
        {"id": "disputes", "permissions": ["disputes.view"]},
    ]
    
    VENDOR_ACTIONS = [
        {"id": "view_rfqs", "permissions": ["rfqs.view"]},
        {"id": "my_quotes", "permissions": ["quotes.view"]},
        {"id": "submit_quote", "permissions": ["quotes.create"]},
        {"id": "my_orders", "permissions": ["orders.view"]},
        {"id": "update_delivery", "permissions": ["orders.update_status"]},
        {"id": "manage_machines", "permissions": []},  # No permission needed
        {"id": "my_profile", "permissions": []},  # No permission needed
        {"id": "disputes", "permissions": ["disputes.view"]},
    ]
    
    @pytest.fixture(scope="class")
    def buyer_token(self):
        """Get buyer auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "buyer@offoadex.com",
            "password": "buyer123"
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def vendor_token(self):
        """Get vendor auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "testpermvendor@test.com",
            "password": "Secure@Vendor99"
        })
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Vendor login failed")
    
    def test_buyer_actions_count(self, buyer_token):
        """Verify buyer should see 10 actions based on permissions"""
        response = requests.get(
            f"{BASE_URL}/api/user/permissions",
            headers={"Authorization": f"Bearer {buyer_token}"}
        )
        assert response.status_code == 200
        permissions = response.json()["permissions"]
        
        # Count how many buyer actions are enabled
        enabled_actions = []
        for action in self.BUYER_ACTIONS:
            if not action["permissions"]:  # No permission needed
                enabled_actions.append(action["id"])
            elif any(p in permissions for p in action["permissions"]):
                enabled_actions.append(action["id"])
        
        print(f"✓ Buyer enabled actions: {len(enabled_actions)}/10")
        print(f"  Enabled: {enabled_actions}")
        
        # Buyer should have 10 actions based on requirement
        assert len(enabled_actions) >= 10, f"Buyer should have at least 10 actions, got {len(enabled_actions)}"
    
    def test_vendor_actions_count(self, vendor_token):
        """Verify vendor actions based on permissions"""
        response = requests.get(
            f"{BASE_URL}/api/user/permissions",
            headers={"Authorization": f"Bearer {vendor_token}"}
        )
        assert response.status_code == 200
        permissions = response.json()["permissions"]
        
        # Count how many vendor actions are enabled
        enabled_actions = []
        for action in self.VENDOR_ACTIONS:
            if not action["permissions"]:  # No permission needed
                enabled_actions.append(action["id"])
            elif any(p in permissions for p in action["permissions"]):
                enabled_actions.append(action["id"])
        
        print(f"✓ Vendor enabled actions: {len(enabled_actions)}/8")
        print(f"  Enabled: {enabled_actions}")
        
        # Vendor should have at least 6 actions (some need no permissions)
        assert len(enabled_actions) >= 6, f"Vendor should have at least 6 actions, got {len(enabled_actions)}"
