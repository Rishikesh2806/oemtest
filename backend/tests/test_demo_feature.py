"""
Test Demo Feature - Seed demo data and demo login endpoints
Tests: POST /api/demo/seed, POST /api/demo/login for buyer/vendor/admin roles
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestDemoSeed:
    """Test demo data seeding endpoint"""
    
    def test_demo_seed_endpoint_exists(self):
        """POST /api/demo/seed should exist and return success"""
        response = requests.post(f"{BASE_URL}/api/demo/seed")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response should contain 'message' field"
        assert "accounts" in data, "Response should contain 'accounts' field"
        print(f"✓ Demo seed successful: {data['message']}")
    
    def test_demo_seed_returns_account_info(self):
        """Seed response should include buyer, vendor, admin account info"""
        response = requests.post(f"{BASE_URL}/api/demo/seed")
        assert response.status_code == 200
        
        data = response.json()
        accounts = data.get("accounts", {})
        
        # Verify buyer account info
        assert "buyer" in accounts, "Should have buyer account info"
        assert accounts["buyer"]["email"] == "demo.buyer@oemlinker.com"
        assert accounts["buyer"]["password"] == "demo123"
        print(f"✓ Buyer account: {accounts['buyer']['email']}")
        
        # Verify vendor account info
        assert "vendor" in accounts, "Should have vendor account info"
        assert accounts["vendor"]["email"] == "demo.vendor@oemlinker.com"
        assert accounts["vendor"]["password"] == "demo123"
        print(f"✓ Vendor account: {accounts['vendor']['email']}")
        
        # Verify admin account info
        assert "admin" in accounts, "Should have admin account info"
        assert accounts["admin"]["email"] == "admin@offoadex.com"
        assert accounts["admin"]["password"] == "admin123"
        print(f"✓ Admin account: {accounts['admin']['email']}")
    
    def test_demo_seed_is_idempotent(self):
        """Calling seed multiple times should not fail"""
        # First call
        response1 = requests.post(f"{BASE_URL}/api/demo/seed")
        assert response1.status_code == 200
        
        # Second call - should also succeed (idempotent)
        response2 = requests.post(f"{BASE_URL}/api/demo/seed")
        assert response2.status_code == 200
        print("✓ Demo seed is idempotent")


class TestDemoLogin:
    """Test demo login endpoint for all roles"""
    
    @pytest.fixture(autouse=True)
    def seed_demo_data(self):
        """Ensure demo data is seeded before login tests"""
        requests.post(f"{BASE_URL}/api/demo/seed")
    
    def test_demo_login_buyer(self):
        """POST /api/demo/login with role=buyer should return valid token"""
        response = requests.post(
            f"{BASE_URL}/api/demo/login",
            json={"role": "buyer"},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "access_token" in data, "Response should contain 'access_token'"
        assert "user" in data, "Response should contain 'user'"
        
        user = data["user"]
        assert user["email"] == "demo.buyer@oemlinker.com"
        assert user["role"] == "buyer"
        assert "user_id" in user
        assert "name" in user
        print(f"✓ Buyer login successful: {user['name']} ({user['email']})")
        
        return data["access_token"]
    
    def test_demo_login_vendor(self):
        """POST /api/demo/login with role=vendor should return valid token"""
        response = requests.post(
            f"{BASE_URL}/api/demo/login",
            json={"role": "vendor"},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        
        user = data["user"]
        assert user["email"] == "demo.vendor@oemlinker.com"
        assert user["role"] == "vendor"
        print(f"✓ Vendor login successful: {user['name']} ({user['email']})")
        
        return data["access_token"]
    
    def test_demo_login_admin(self):
        """POST /api/demo/login with role=admin should return valid token"""
        response = requests.post(
            f"{BASE_URL}/api/demo/login",
            json={"role": "admin"},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        
        user = data["user"]
        assert user["email"] == "admin@offoadex.com"
        assert user["role"] == "admin"
        print(f"✓ Admin login successful: {user['name']} ({user['email']})")
        
        return data["access_token"]
    
    def test_demo_login_invalid_role(self):
        """POST /api/demo/login with invalid role should return 400"""
        response = requests.post(
            f"{BASE_URL}/api/demo/login",
            json={"role": "invalid_role"},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Invalid role correctly rejected")


class TestDemoBuyerData:
    """Test that demo buyer has expected data after seeding"""
    
    @pytest.fixture
    def buyer_token(self):
        """Get buyer token after seeding"""
        requests.post(f"{BASE_URL}/api/demo/seed")
        response = requests.post(
            f"{BASE_URL}/api/demo/login",
            json={"role": "buyer"},
            headers={"Content-Type": "application/json"}
        )
        return response.json()["access_token"]
    
    def test_buyer_has_rfqs(self, buyer_token):
        """Demo buyer should have 3 RFQs visible"""
        response = requests.get(
            f"{BASE_URL}/api/rfqs",
            headers={"Authorization": f"Bearer {buyer_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Check if response is a list or has 'rfqs' key
        rfqs = data if isinstance(data, list) else data.get("rfqs", [])
        
        # Demo buyer should have at least 3 RFQs
        demo_rfqs = [r for r in rfqs if r.get("buyer_id") == "user_demo_buyer_001"]
        assert len(demo_rfqs) >= 3, f"Expected at least 3 demo RFQs, found {len(demo_rfqs)}"
        print(f"✓ Buyer has {len(demo_rfqs)} demo RFQs")
        
        # Verify RFQ titles
        titles = [r.get("title", "") for r in demo_rfqs]
        print(f"  RFQ titles: {titles}")


class TestDemoVendorData:
    """Test that demo vendor has expected data after seeding"""
    
    @pytest.fixture
    def vendor_token(self):
        """Get vendor token after seeding"""
        requests.post(f"{BASE_URL}/api/demo/seed")
        response = requests.post(
            f"{BASE_URL}/api/demo/login",
            json={"role": "vendor"},
            headers={"Content-Type": "application/json"}
        )
        return response.json()["access_token"]
    
    def test_vendor_has_machines(self, vendor_token):
        """Demo vendor should have machines visible"""
        response = requests.get(
            f"{BASE_URL}/api/machines",
            headers={"Authorization": f"Bearer {vendor_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        machines = data if isinstance(data, list) else data.get("machines", [])
        
        # Demo vendor should have at least 3 machines
        assert len(machines) >= 3, f"Expected at least 3 machines, found {len(machines)}"
        print(f"✓ Vendor has {len(machines)} machines")
        
        # Verify machine names
        names = [m.get("name", "") for m in machines]
        print(f"  Machine names: {names}")


class TestDemoTokenValidity:
    """Test that demo tokens work for authenticated endpoints"""
    
    @pytest.fixture
    def tokens(self):
        """Get all demo tokens"""
        requests.post(f"{BASE_URL}/api/demo/seed")
        
        buyer_resp = requests.post(f"{BASE_URL}/api/demo/login", json={"role": "buyer"})
        vendor_resp = requests.post(f"{BASE_URL}/api/demo/login", json={"role": "vendor"})
        admin_resp = requests.post(f"{BASE_URL}/api/demo/login", json={"role": "admin"})
        
        return {
            "buyer": buyer_resp.json()["access_token"],
            "vendor": vendor_resp.json()["access_token"],
            "admin": admin_resp.json()["access_token"]
        }
    
    def test_buyer_token_works_for_auth_me(self, tokens):
        """Buyer token should work for /api/auth/me"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {tokens['buyer']}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["email"] == "demo.buyer@oemlinker.com"
        print("✓ Buyer token valid for /api/auth/me")
    
    def test_vendor_token_works_for_auth_me(self, tokens):
        """Vendor token should work for /api/auth/me"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {tokens['vendor']}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["email"] == "demo.vendor@oemlinker.com"
        print("✓ Vendor token valid for /api/auth/me")
    
    def test_admin_token_works_for_auth_me(self, tokens):
        """Admin token should work for /api/auth/me"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {tokens['admin']}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["email"] == "admin@offoadex.com"
        print("✓ Admin token valid for /api/auth/me")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
