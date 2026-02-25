"""
Admin Panel Backend API Tests
Tests for admin CRUD operations on users, rfqs, quotes, orders, drawings, ndas, vendors
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Admin credentials
ADMIN_EMAIL = "admin@offoadex.com"
ADMIN_PASSWORD = "admin123"

# Test data prefix for cleanup
TEST_PREFIX = "TEST_ADMIN_"


class TestAdminAuth:
    """Admin authentication tests"""
    
    def test_admin_login_success(self):
        """Test admin can log in successfully"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "admin"
        print(f"PASS: Admin login - got token, role={data['user']['role']}")
        return data["access_token"]
    
    def test_admin_login_invalid_credentials(self):
        """Test login fails with wrong password"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        print("PASS: Admin login with wrong password returns 401")


@pytest.fixture(scope="module")
def admin_token():
    """Get admin token for authenticated tests"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json()["access_token"]
    pytest.fail(f"Admin login failed: {response.text}")


@pytest.fixture
def admin_headers(admin_token):
    """Headers with admin auth"""
    return {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }


class TestAdminStats:
    """Test admin stats/overview endpoint"""
    
    def test_get_admin_stats(self, admin_headers):
        """Test GET /admin/stats returns dashboard statistics"""
        response = requests.get(f"{BASE_URL}/api/admin/stats", headers=admin_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Verify all expected fields
        expected_fields = ["total_users", "total_vendors", "approved_vendors", "pending_vendors", "total_rfqs", "total_orders", "total_quotes", "total_ndas"]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
            assert isinstance(data[field], int), f"Field {field} should be int"
        
        print(f"PASS: Admin stats - users={data['total_users']}, vendors={data['total_vendors']}, rfqs={data['total_rfqs']}")
    
    def test_get_pending_vendors(self, admin_headers):
        """Test GET /admin/vendors/pending"""
        response = requests.get(f"{BASE_URL}/api/admin/vendors/pending", headers=admin_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: Pending vendors - count={len(data)}")


class TestAdminUsers:
    """Admin user management tests"""
    
    def test_list_users(self, admin_headers):
        """Test GET /admin/users lists all users"""
        response = requests.get(f"{BASE_URL}/api/admin/users", headers=admin_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0, "Should have at least admin user"
        
        # Verify user structure (without password_hash)
        user = data[0]
        assert "user_id" in user
        assert "email" in user
        assert "name" in user
        assert "role" in user
        assert "password_hash" not in user
        print(f"PASS: List users - count={len(data)}")
    
    def test_list_users_filter_by_role(self, admin_headers):
        """Test users can be filtered by role"""
        response = requests.get(f"{BASE_URL}/api/admin/users?role=admin", headers=admin_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        for user in data:
            assert user["role"] == "admin"
        print(f"PASS: List users by role - admin count={len(data)}")
    
    def test_create_update_delete_user(self, admin_headers):
        """Test user CRUD cycle"""
        # Create a test user first via registration
        test_email = f"{TEST_PREFIX}user_{uuid.uuid4().hex[:8]}@test.com"
        reg_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": test_email,
            "name": f"{TEST_PREFIX}User",
            "password": "TestPass123!",
            "role": "buyer"
        })
        assert reg_response.status_code == 200, f"Registration failed: {reg_response.text}"
        user_id = reg_response.json()["user"]["user_id"]
        
        # GET single user
        get_response = requests.get(f"{BASE_URL}/api/admin/users/{user_id}", headers=admin_headers)
        assert get_response.status_code == 200, f"Get user failed: {get_response.text}"
        user_data = get_response.json()
        assert user_data["email"] == test_email
        print(f"PASS: Get user by ID")
        
        # UPDATE user
        update_response = requests.put(
            f"{BASE_URL}/api/admin/users/{user_id}",
            headers=admin_headers,
            json={"name": f"{TEST_PREFIX}Updated User", "role": "vendor"}
        )
        assert update_response.status_code == 200, f"Update failed: {update_response.text}"
        
        # Verify update
        verify_response = requests.get(f"{BASE_URL}/api/admin/users/{user_id}", headers=admin_headers)
        assert verify_response.json()["name"] == f"{TEST_PREFIX}Updated User"
        assert verify_response.json()["role"] == "vendor"
        print(f"PASS: Update user")
        
        # DELETE user
        delete_response = requests.delete(f"{BASE_URL}/api/admin/users/{user_id}", headers=admin_headers)
        assert delete_response.status_code == 200, f"Delete failed: {delete_response.text}"
        
        # Verify deletion
        verify_delete = requests.get(f"{BASE_URL}/api/admin/users/{user_id}", headers=admin_headers)
        assert verify_delete.status_code == 404
        print(f"PASS: Delete user")
    
    def test_cannot_delete_self(self, admin_headers, admin_token):
        """Test admin cannot delete their own account"""
        # Get admin user_id from token
        me_response = requests.get(f"{BASE_URL}/api/auth/me", headers=admin_headers)
        admin_user_id = me_response.json()["user_id"]
        
        response = requests.delete(f"{BASE_URL}/api/admin/users/{admin_user_id}", headers=admin_headers)
        assert response.status_code == 400
        assert "Cannot delete your own account" in response.text
        print("PASS: Cannot delete self protection works")


class TestAdminRFQs:
    """Admin RFQ management tests"""
    
    def test_list_rfqs(self, admin_headers):
        """Test GET /admin/rfqs lists all RFQs"""
        response = requests.get(f"{BASE_URL}/api/admin/rfqs", headers=admin_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        
        if len(data) > 0:
            rfq = data[0]
            assert "rfq_id" in rfq
            assert "title" in rfq
            assert "status" in rfq
            assert "buyer_info" in rfq  # Enriched data
        print(f"PASS: List RFQs - count={len(data)}")
    
    def test_list_rfqs_filter_by_status(self, admin_headers):
        """Test RFQs can be filtered by status"""
        response = requests.get(f"{BASE_URL}/api/admin/rfqs?status=draft", headers=admin_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        for rfq in data:
            assert rfq["status"] == "draft"
        print(f"PASS: List RFQs by status - draft count={len(data)}")
    
    def test_update_rfq(self, admin_headers):
        """Test updating an existing RFQ"""
        # First get existing RFQs
        list_response = requests.get(f"{BASE_URL}/api/admin/rfqs", headers=admin_headers)
        rfqs = list_response.json()
        
        if len(rfqs) == 0:
            pytest.skip("No RFQs to test update")
        
        rfq_id = rfqs[0]["rfq_id"]
        original_title = rfqs[0]["title"]
        
        # Update RFQ
        response = requests.put(
            f"{BASE_URL}/api/admin/rfqs/{rfq_id}",
            headers=admin_headers,
            json={"title": f"{original_title} (Admin Updated)"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        # Verify update
        get_response = requests.get(f"{BASE_URL}/api/admin/rfqs/{rfq_id}", headers=admin_headers)
        assert "(Admin Updated)" in get_response.json()["title"]
        
        # Restore original
        requests.put(
            f"{BASE_URL}/api/admin/rfqs/{rfq_id}",
            headers=admin_headers,
            json={"title": original_title}
        )
        print(f"PASS: Update RFQ")


class TestAdminQuotes:
    """Admin quote management tests"""
    
    def test_list_quotes(self, admin_headers):
        """Test GET /admin/quotes lists all quotes"""
        response = requests.get(f"{BASE_URL}/api/admin/quotes", headers=admin_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        
        if len(data) > 0:
            quote = data[0]
            assert "quote_id" in quote
            assert "price" in quote
            assert "status" in quote
            assert "rfq_info" in quote  # Enriched
            assert "vendor_info" in quote  # Enriched
        print(f"PASS: List quotes - count={len(data)}")
    
    def test_list_quotes_filter_by_status(self, admin_headers):
        """Test quotes can be filtered by status"""
        response = requests.get(f"{BASE_URL}/api/admin/quotes?status=pending", headers=admin_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        for quote in data:
            assert quote["status"] == "pending"
        print(f"PASS: List quotes by status - pending count={len(data)}")
    
    def test_update_quote(self, admin_headers):
        """Test updating a quote"""
        list_response = requests.get(f"{BASE_URL}/api/admin/quotes", headers=admin_headers)
        quotes = list_response.json()
        
        if len(quotes) == 0:
            pytest.skip("No quotes to test update")
        
        quote_id = quotes[0]["quote_id"]
        original_price = quotes[0]["price"]
        
        # Update quote
        response = requests.put(
            f"{BASE_URL}/api/admin/quotes/{quote_id}",
            headers=admin_headers,
            json={"price": original_price + 100, "notes": "Admin updated"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        # Restore original
        requests.put(
            f"{BASE_URL}/api/admin/quotes/{quote_id}",
            headers=admin_headers,
            json={"price": original_price}
        )
        print(f"PASS: Update quote")


class TestAdminOrders:
    """Admin order management tests"""
    
    def test_list_orders(self, admin_headers):
        """Test GET /admin/orders lists all orders"""
        response = requests.get(f"{BASE_URL}/api/admin/orders", headers=admin_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        
        if len(data) > 0:
            order = data[0]
            assert "order_id" in order
            assert "total_amount" in order
            assert "status" in order
            assert "buyer_info" in order
            assert "vendor_info" in order
        print(f"PASS: List orders - count={len(data)}")
    
    def test_list_orders_filter_by_status(self, admin_headers):
        """Test orders can be filtered by status"""
        response = requests.get(f"{BASE_URL}/api/admin/orders?status=pending_payment", headers=admin_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        print(f"PASS: List orders by status")
    
    def test_update_order(self, admin_headers):
        """Test updating an order"""
        list_response = requests.get(f"{BASE_URL}/api/admin/orders", headers=admin_headers)
        orders = list_response.json()
        
        if len(orders) == 0:
            pytest.skip("No orders to test update")
        
        order_id = orders[0]["order_id"]
        
        # Update order status
        response = requests.put(
            f"{BASE_URL}/api/admin/orders/{order_id}",
            headers=admin_headers,
            json={"status": "in_production"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        print(f"PASS: Update order status")


class TestAdminDrawings:
    """Admin drawing management tests"""
    
    def test_list_drawings(self, admin_headers):
        """Test GET /admin/drawings lists all drawings"""
        response = requests.get(f"{BASE_URL}/api/admin/drawings", headers=admin_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        
        if len(data) > 0:
            drawing = data[0]
            assert "drawing_id" in drawing
            assert "filename" in drawing
            assert "file_size" in drawing
            assert "file_data" not in drawing  # Should be excluded
            assert "rfq_info" in drawing
        print(f"PASS: List drawings - count={len(data)}")
    
    def test_get_single_drawing(self, admin_headers):
        """Test getting a single drawing with file data"""
        list_response = requests.get(f"{BASE_URL}/api/admin/drawings", headers=admin_headers)
        drawings = list_response.json()
        
        if len(drawings) == 0:
            pytest.skip("No drawings to test")
        
        drawing_id = drawings[0]["drawing_id"]
        response = requests.get(f"{BASE_URL}/api/admin/drawings/{drawing_id}", headers=admin_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "file_data" in data  # Should include file data for single get
        print(f"PASS: Get single drawing with file data")


class TestAdminVendors:
    """Admin vendor management tests"""
    
    def test_list_all_vendors(self, admin_headers):
        """Test GET /admin/vendors lists all vendors"""
        response = requests.get(f"{BASE_URL}/api/admin/vendors", headers=admin_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        
        if len(data) > 0:
            vendor = data[0]
            assert "vendor_id" in vendor
            assert "company_name" in vendor
            assert "is_approved" in vendor
            assert "user_info" in vendor  # Enriched
            assert "machine_count" in vendor  # Enriched
        print(f"PASS: List vendors - count={len(data)}")
    
    def test_list_vendors_filter_approved(self, admin_headers):
        """Test vendors can be filtered by approval status"""
        response = requests.get(f"{BASE_URL}/api/admin/vendors?approved=true", headers=admin_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        for vendor in data:
            assert vendor["is_approved"] == True
        print(f"PASS: List approved vendors - count={len(data)}")
    
    def test_approve_vendor(self, admin_headers):
        """Test approving a vendor"""
        # Get pending vendors
        pending_response = requests.get(f"{BASE_URL}/api/admin/vendors/pending", headers=admin_headers)
        pending = pending_response.json()
        
        if len(pending) == 0:
            pytest.skip("No pending vendors to approve")
        
        vendor_id = pending[0]["vendor_id"]
        
        # Approve vendor
        response = requests.post(f"{BASE_URL}/api/admin/vendors/{vendor_id}/approve", headers=admin_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        # Verify approval
        verify_response = requests.get(f"{BASE_URL}/api/admin/vendors", headers=admin_headers)
        vendors = verify_response.json()
        approved_vendor = next((v for v in vendors if v["vendor_id"] == vendor_id), None)
        assert approved_vendor["is_approved"] == True
        print(f"PASS: Approve vendor")
    
    def test_reject_vendor(self, admin_headers):
        """Test rejecting/unapproving a vendor"""
        # Get approved vendors
        approved_response = requests.get(f"{BASE_URL}/api/admin/vendors?approved=true", headers=admin_headers)
        approved = approved_response.json()
        
        if len(approved) == 0:
            pytest.skip("No approved vendors to reject")
        
        vendor_id = approved[0]["vendor_id"]
        
        # Reject vendor
        response = requests.post(f"{BASE_URL}/api/admin/vendors/{vendor_id}/reject", headers=admin_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        # Re-approve for cleanup
        requests.post(f"{BASE_URL}/api/admin/vendors/{vendor_id}/approve", headers=admin_headers)
        print(f"PASS: Reject vendor")
    
    def test_update_vendor(self, admin_headers):
        """Test updating vendor details"""
        list_response = requests.get(f"{BASE_URL}/api/admin/vendors", headers=admin_headers)
        vendors = list_response.json()
        
        if len(vendors) == 0:
            pytest.skip("No vendors to test update")
        
        vendor_id = vendors[0]["vendor_id"]
        original_rating = vendors[0].get("rating", 0)
        
        # Update vendor
        response = requests.put(
            f"{BASE_URL}/api/admin/vendors/{vendor_id}",
            headers=admin_headers,
            json={"rating": 4.5, "description": "Admin updated description"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        # Restore original
        requests.put(
            f"{BASE_URL}/api/admin/vendors/{vendor_id}",
            headers=admin_headers,
            json={"rating": original_rating}
        )
        print(f"PASS: Update vendor")


class TestAdminNDAs:
    """Admin NDA management tests"""
    
    def test_list_ndas(self, admin_headers):
        """Test GET /admin/ndas lists all NDAs"""
        response = requests.get(f"{BASE_URL}/api/admin/ndas", headers=admin_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        
        if len(data) > 0:
            nda = data[0]
            assert "nda_id" in nda
            assert "title" in nda
            assert "status" in nda
            assert "buyer_info" in nda
            assert "vendor_info" in nda
        print(f"PASS: List NDAs - count={len(data)}")
    
    def test_create_nda(self, admin_headers):
        """Test creating a new NDA"""
        # Need buyer and vendor IDs
        users_response = requests.get(f"{BASE_URL}/api/admin/users?role=buyer", headers=admin_headers)
        buyers = users_response.json()
        
        vendors_response = requests.get(f"{BASE_URL}/api/admin/vendors?approved=true", headers=admin_headers)
        vendors = vendors_response.json()
        
        if len(buyers) == 0 or len(vendors) == 0:
            pytest.skip("Need buyers and vendors to create NDA")
        
        buyer_id = buyers[0]["user_id"]
        vendor_id = vendors[0]["vendor_id"]
        
        # Create NDA
        response = requests.post(
            f"{BASE_URL}/api/admin/ndas",
            headers=admin_headers,
            json={
                "title": f"{TEST_PREFIX}NDA Test",
                "buyer_id": buyer_id,
                "vendor_id": vendor_id,
                "content": "Test NDA content for testing purposes",
                "valid_until": "2027-01-01"
            }
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "nda_id" in data
        nda_id = data["nda_id"]
        print(f"PASS: Create NDA - id={nda_id}")
        
        # Cleanup - delete the test NDA
        requests.delete(f"{BASE_URL}/api/admin/ndas/{nda_id}", headers=admin_headers)
    
    def test_nda_lifecycle(self, admin_headers):
        """Test full NDA lifecycle: create, update, send, delete"""
        # Get test data
        users_response = requests.get(f"{BASE_URL}/api/admin/users?role=buyer", headers=admin_headers)
        buyers = users_response.json()
        vendors_response = requests.get(f"{BASE_URL}/api/admin/vendors?approved=true", headers=admin_headers)
        vendors = vendors_response.json()
        
        if len(buyers) == 0 or len(vendors) == 0:
            pytest.skip("Need buyers and vendors for NDA lifecycle test")
        
        buyer_id = buyers[0]["user_id"]
        vendor_id = vendors[0]["vendor_id"]
        
        # CREATE
        create_response = requests.post(
            f"{BASE_URL}/api/admin/ndas",
            headers=admin_headers,
            json={
                "title": f"{TEST_PREFIX}Lifecycle NDA",
                "buyer_id": buyer_id,
                "vendor_id": vendor_id,
                "content": "Lifecycle test content"
            }
        )
        assert create_response.status_code == 200
        nda_id = create_response.json()["nda_id"]
        
        # GET
        get_response = requests.get(f"{BASE_URL}/api/admin/ndas/{nda_id}", headers=admin_headers)
        assert get_response.status_code == 200
        assert get_response.json()["status"] == "draft"
        
        # UPDATE
        update_response = requests.put(
            f"{BASE_URL}/api/admin/ndas/{nda_id}",
            headers=admin_headers,
            json={"title": f"{TEST_PREFIX}Updated Lifecycle NDA", "content": "Updated content"}
        )
        assert update_response.status_code == 200
        
        # SEND
        send_response = requests.post(f"{BASE_URL}/api/admin/ndas/{nda_id}/send", headers=admin_headers)
        assert send_response.status_code == 200
        
        # Verify status changed to sent
        verify_response = requests.get(f"{BASE_URL}/api/admin/ndas/{nda_id}", headers=admin_headers)
        assert verify_response.json()["status"] == "sent"
        
        # DELETE
        delete_response = requests.delete(f"{BASE_URL}/api/admin/ndas/{nda_id}", headers=admin_headers)
        assert delete_response.status_code == 200
        
        # Verify deletion
        verify_delete = requests.get(f"{BASE_URL}/api/admin/ndas/{nda_id}", headers=admin_headers)
        assert verify_delete.status_code == 404
        
        print(f"PASS: NDA lifecycle (create, update, send, delete)")


class TestAdminAuthorization:
    """Test admin authorization is enforced"""
    
    def test_non_admin_cannot_access_admin_routes(self):
        """Test that regular users cannot access admin endpoints"""
        # Register a regular buyer
        test_email = f"{TEST_PREFIX}buyer_{uuid.uuid4().hex[:8]}@test.com"
        reg_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": test_email,
            "name": "Test Buyer",
            "password": "TestPass123!",
            "role": "buyer"
        })
        
        if reg_response.status_code != 200:
            pytest.skip("Could not create test user")
        
        buyer_token = reg_response.json()["access_token"]
        buyer_headers = {
            "Authorization": f"Bearer {buyer_token}",
            "Content-Type": "application/json"
        }
        
        # Test admin endpoints return 403
        endpoints = [
            ("GET", "/api/admin/stats"),
            ("GET", "/api/admin/users"),
            ("GET", "/api/admin/rfqs"),
            ("GET", "/api/admin/quotes"),
            ("GET", "/api/admin/orders"),
            ("GET", "/api/admin/drawings"),
            ("GET", "/api/admin/ndas"),
            ("GET", "/api/admin/vendors"),
        ]
        
        for method, endpoint in endpoints:
            if method == "GET":
                response = requests.get(f"{BASE_URL}{endpoint}", headers=buyer_headers)
            assert response.status_code == 403, f"Endpoint {endpoint} should require admin role"
        
        print("PASS: All admin endpoints require admin role")
        
        # Cleanup - use admin to delete test user
        admin_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        admin_token = admin_response.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        user_id = reg_response.json()["user"]["user_id"]
        requests.delete(f"{BASE_URL}/api/admin/users/{user_id}", headers=admin_headers)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
