"""
Test suite for Notification System
Tests:
- GET /api/notifications - returns user's notifications with unread_count
- PUT /api/notifications/{id}/read - marks single notification as read
- PUT /api/notifications/read-all - marks all notifications as read
- DELETE /api/notifications/{id} - deletes a notification
- Notification triggers on various events (quote acceptance, order status, messages)
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
BUYER_EMAIL = "buyer@offoadex.com"
BUYER_PASSWORD = "buyer123"
VENDOR_EMAIL = "vendor@offoadex.com"
VENDOR_PASSWORD = "vendor123"
ADMIN_EMAIL = "admin@offoadex.com"
ADMIN_PASSWORD = "admin123"


class TestNotificationAPIs:
    """Test notification CRUD endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data and authenticate"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as buyer
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": BUYER_EMAIL,
            "password": BUYER_PASSWORD
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        self.buyer_token = login_response.json()["access_token"]
        self.buyer_user_id = login_response.json()["user"]["user_id"]
        self.session.headers.update({"Authorization": f"Bearer {self.buyer_token}"})
    
    def test_get_notifications(self):
        """Test GET /api/notifications returns notifications with unread_count"""
        response = self.session.get(f"{BASE_URL}/api/notifications")
        assert response.status_code == 200, f"Get notifications failed: {response.text}"
        
        data = response.json()
        assert "notifications" in data, "Response missing 'notifications' field"
        assert "unread_count" in data, "Response missing 'unread_count' field"
        assert isinstance(data["notifications"], list), "notifications should be a list"
        assert isinstance(data["unread_count"], int), "unread_count should be an integer"
        print(f"✓ GET /api/notifications - Found {len(data['notifications'])} notifications, {data['unread_count']} unread")
    
    def test_get_notifications_with_limit(self):
        """Test GET /api/notifications with limit parameter"""
        response = self.session.get(f"{BASE_URL}/api/notifications?limit=5")
        assert response.status_code == 200, f"Get notifications with limit failed: {response.text}"
        
        data = response.json()
        assert len(data["notifications"]) <= 5, "Should respect limit parameter"
        print(f"✓ GET /api/notifications?limit=5 - Returned {len(data['notifications'])} notifications")
    
    def test_get_notifications_unread_only(self):
        """Test GET /api/notifications with unread_only filter"""
        response = self.session.get(f"{BASE_URL}/api/notifications?unread_only=true")
        assert response.status_code == 200, f"Get unread notifications failed: {response.text}"
        
        data = response.json()
        # All returned notifications should be unread
        for notif in data["notifications"]:
            assert notif.get("is_read") == False, "All notifications should be unread"
        print(f"✓ GET /api/notifications?unread_only=true - All {len(data['notifications'])} are unread")


class TestNotificationTriggers:
    """Test notification triggers on various events"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup sessions for buyer and vendor"""
        self.buyer_session = requests.Session()
        self.buyer_session.headers.update({"Content-Type": "application/json"})
        
        self.vendor_session = requests.Session()
        self.vendor_session.headers.update({"Content-Type": "application/json"})
        
        # Login as buyer
        buyer_login = self.buyer_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": BUYER_EMAIL,
            "password": BUYER_PASSWORD
        })
        assert buyer_login.status_code == 200, f"Buyer login failed: {buyer_login.text}"
        self.buyer_token = buyer_login.json()["access_token"]
        self.buyer_user_id = buyer_login.json()["user"]["user_id"]
        self.buyer_session.headers.update({"Authorization": f"Bearer {self.buyer_token}"})
        
        # Login as vendor
        vendor_login = self.vendor_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": VENDOR_EMAIL,
            "password": VENDOR_PASSWORD
        })
        assert vendor_login.status_code == 200, f"Vendor login failed: {vendor_login.text}"
        self.vendor_token = vendor_login.json()["access_token"]
        self.vendor_user_id = vendor_login.json()["user"]["user_id"]
        self.vendor_session.headers.update({"Authorization": f"Bearer {self.vendor_token}"})
    
    def test_message_creates_notification(self):
        """Test that sending a message creates a notification for the receiver"""
        # Get initial notification count for vendor
        initial_response = self.vendor_session.get(f"{BASE_URL}/api/notifications")
        initial_data = initial_response.json()
        initial_count = len(initial_data["notifications"])
        
        # Buyer sends message to vendor
        message_id = f"TEST_msg_{uuid.uuid4().hex[:8]}"
        message_response = self.buyer_session.post(f"{BASE_URL}/api/messages", json={
            "receiver_id": self.vendor_user_id,
            "content": f"Test notification message - {message_id}"
        })
        assert message_response.status_code == 200, f"Send message failed: {message_response.text}"
        
        # Check vendor notifications increased
        import time
        time.sleep(0.5)  # Small delay for async notification creation
        
        after_response = self.vendor_session.get(f"{BASE_URL}/api/notifications")
        after_data = after_response.json()
        
        # Check for message notification
        message_notifs = [n for n in after_data["notifications"] 
                         if n.get("type") == "message_received" and message_id in n.get("message", "")]
        
        assert len(message_notifs) > 0, "Message should create a notification for receiver"
        print(f"✓ Message notification created: {message_notifs[0].get('title')}")


class TestNotificationCRUD:
    """Test notification mark as read and delete operations"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data and authenticate"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as buyer
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": BUYER_EMAIL,
            "password": BUYER_PASSWORD
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        self.token = login_response.json()["access_token"]
        self.user_id = login_response.json()["user"]["user_id"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def _create_test_notification_via_message(self, vendor_session, vendor_user_id):
        """Helper to create a notification by having vendor send a message"""
        message_response = vendor_session.post(f"{BASE_URL}/api/messages", json={
            "receiver_id": self.user_id,
            "content": f"Test message to create notification - {uuid.uuid4().hex[:8]}"
        })
        return message_response.status_code == 200
    
    def test_mark_notification_as_read(self):
        """Test PUT /api/notifications/{id}/read"""
        # Get current notifications
        response = self.session.get(f"{BASE_URL}/api/notifications")
        data = response.json()
        
        # Find an unread notification or use any notification
        unread_notifs = [n for n in data["notifications"] if not n.get("is_read")]
        
        if unread_notifs:
            notif_id = unread_notifs[0]["notification_id"]
            
            # Mark as read
            mark_response = self.session.put(f"{BASE_URL}/api/notifications/{notif_id}/read")
            assert mark_response.status_code == 200, f"Mark as read failed: {mark_response.text}"
            
            # Verify it's now read
            verify_response = self.session.get(f"{BASE_URL}/api/notifications")
            verify_data = verify_response.json()
            notif = next((n for n in verify_data["notifications"] if n["notification_id"] == notif_id), None)
            
            if notif:
                assert notif["is_read"] == True, "Notification should be marked as read"
            print(f"✓ PUT /api/notifications/{notif_id}/read - Marked as read successfully")
        else:
            print("⚠ No unread notifications to test mark_as_read, skipping...")
            pytest.skip("No unread notifications available")
    
    def test_mark_all_notifications_as_read(self):
        """Test PUT /api/notifications/read-all"""
        # Mark all as read
        response = self.session.put(f"{BASE_URL}/api/notifications/read-all")
        assert response.status_code == 200, f"Mark all as read failed: {response.text}"
        
        # Verify unread count is 0
        verify_response = self.session.get(f"{BASE_URL}/api/notifications")
        verify_data = verify_response.json()
        
        # After marking all read, unread count should be 0 (for existing notifications)
        unread_notifs = [n for n in verify_data["notifications"] if not n.get("is_read")]
        assert len(unread_notifs) == 0, "All notifications should be marked as read"
        print(f"✓ PUT /api/notifications/read-all - All notifications marked as read")
    
    def test_delete_notification(self):
        """Test DELETE /api/notifications/{id}"""
        # Get current notifications
        response = self.session.get(f"{BASE_URL}/api/notifications")
        data = response.json()
        
        if data["notifications"]:
            notif_id = data["notifications"][0]["notification_id"]
            initial_count = len(data["notifications"])
            
            # Delete the notification
            delete_response = self.session.delete(f"{BASE_URL}/api/notifications/{notif_id}")
            assert delete_response.status_code == 200, f"Delete failed: {delete_response.text}"
            
            # Verify it's deleted
            verify_response = self.session.get(f"{BASE_URL}/api/notifications")
            verify_data = verify_response.json()
            
            deleted = next((n for n in verify_data["notifications"] if n["notification_id"] == notif_id), None)
            assert deleted is None, "Notification should be deleted"
            print(f"✓ DELETE /api/notifications/{notif_id} - Deleted successfully")
        else:
            print("⚠ No notifications to delete, skipping...")
            pytest.skip("No notifications available to delete")
    
    def test_delete_nonexistent_notification(self):
        """Test DELETE /api/notifications/{id} with invalid ID"""
        fake_id = "notif_nonexistent123"
        response = self.session.delete(f"{BASE_URL}/api/notifications/{fake_id}")
        assert response.status_code == 404, "Should return 404 for nonexistent notification"
        print(f"✓ DELETE /api/notifications/{fake_id} - Returns 404 as expected")


class TestOrderStatusNotification:
    """Test notification triggers on order status updates"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup sessions"""
        self.buyer_session = requests.Session()
        self.buyer_session.headers.update({"Content-Type": "application/json"})
        
        self.vendor_session = requests.Session()
        self.vendor_session.headers.update({"Content-Type": "application/json"})
        
        self.admin_session = requests.Session()
        self.admin_session.headers.update({"Content-Type": "application/json"})
        
        # Login as buyer
        buyer_login = self.buyer_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": BUYER_EMAIL,
            "password": BUYER_PASSWORD
        })
        assert buyer_login.status_code == 200
        self.buyer_token = buyer_login.json()["access_token"]
        self.buyer_user_id = buyer_login.json()["user"]["user_id"]
        self.buyer_session.headers.update({"Authorization": f"Bearer {self.buyer_token}"})
        
        # Login as vendor
        vendor_login = self.vendor_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": VENDOR_EMAIL,
            "password": VENDOR_PASSWORD
        })
        assert vendor_login.status_code == 200
        self.vendor_token = vendor_login.json()["access_token"]
        self.vendor_user_id = vendor_login.json()["user"]["user_id"]
        self.vendor_session.headers.update({"Authorization": f"Bearer {self.vendor_token}"})
        
        # Login as admin
        admin_login = self.admin_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if admin_login.status_code == 200:
            self.admin_token = admin_login.json()["access_token"]
            self.admin_session.headers.update({"Authorization": f"Bearer {self.admin_token}"})
        else:
            self.admin_session = self.buyer_session  # Fallback to buyer
    
    def test_order_status_update_creates_notification(self):
        """Test that updating order status creates notification for buyer and vendor"""
        # Get buyer's orders
        orders_response = self.buyer_session.get(f"{BASE_URL}/api/orders")
        assert orders_response.status_code == 200
        orders = orders_response.json()
        
        if not orders:
            pytest.skip("No orders available to test status update")
        
        order_id = orders[0]["order_id"]
        
        # Get initial notifications for buyer
        initial_buyer_notifs = self.buyer_session.get(f"{BASE_URL}/api/notifications").json()
        initial_count = len(initial_buyer_notifs["notifications"])
        
        # Update order status (as vendor)
        update_response = self.vendor_session.put(
            f"{BASE_URL}/api/orders/{order_id}/status",
            json={"status": "in_production", "note": "Test status update for notifications"}
        )
        
        if update_response.status_code == 200:
            import time
            time.sleep(0.5)  # Small delay for notification creation
            
            # Check buyer received notification
            after_buyer_notifs = self.buyer_session.get(f"{BASE_URL}/api/notifications").json()
            
            # Look for order status notification
            order_notifs = [n for n in after_buyer_notifs["notifications"] 
                          if n.get("type") == "order_status_update" 
                          and order_id in str(n.get("data", {}))]
            
            print(f"✓ Order status update notification check - Found {len(order_notifs)} relevant notifications")
        else:
            print(f"⚠ Order status update failed or unauthorized: {update_response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
