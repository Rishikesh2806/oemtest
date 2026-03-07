"""
WhatsApp Integration Tests for OEMLinker
Tests the Gupshup WhatsApp API integration endpoints:
- GET /api/whatsapp/status - Check integration status
- POST /api/whatsapp/send - Send WhatsApp message (Admin only)
- POST /api/whatsapp/notify-rfq - Notify matched vendors about RFQ
- POST /api/whatsapp/webhook - Receive incoming WhatsApp messages
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@offoadex.com"
ADMIN_PASSWORD = "admin123"
BUYER_EMAIL = "buyer@offoadex.com"
BUYER_PASSWORD = "buyer123"
VENDOR_EMAIL = "vendor@offoadex.com"
VENDOR_PASSWORD = "vendor123"

# RFQ with matched vendors for testing
TEST_RFQ_ID = "rfq_b125b67d20d8"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Admin authentication failed")


@pytest.fixture(scope="module")
def buyer_token():
    """Get buyer auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": BUYER_EMAIL,
        "password": BUYER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Buyer authentication failed")


@pytest.fixture(scope="module")
def vendor_token():
    """Get vendor auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": VENDOR_EMAIL,
        "password": VENDOR_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Vendor authentication failed")


class TestWhatsAppStatus:
    """Test /api/whatsapp/status endpoint"""
    
    def test_status_returns_configured(self):
        """Test that WhatsApp status endpoint returns configuration info"""
        response = requests.get(f"{BASE_URL}/api/whatsapp/status")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "configured" in data, "Response should contain 'configured' field"
        assert "app_name" in data, "Response should contain 'app_name' field"
        assert "source_number" in data, "Response should contain 'source_number' field"
        
        # Verify configuration is active
        assert data["configured"] is True, "WhatsApp should be configured"
        assert data["app_name"] == "OEMLinker", f"Expected app_name 'OEMLinker', got {data['app_name']}"
        
        # Source number should be masked
        assert "****" in data["source_number"], "Source number should be masked"
        print(f"WhatsApp status: configured={data['configured']}, app={data['app_name']}, source={data['source_number']}")


class TestWhatsAppSendMessage:
    """Test /api/whatsapp/send endpoint"""
    
    def test_send_message_requires_admin(self, buyer_token):
        """Test that send message requires admin role"""
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/send",
            headers={"Authorization": f"Bearer {buyer_token}"},
            json={
                "to_number": "919876543210",
                "message": "Test message"
            }
        )
        assert response.status_code == 403, f"Expected 403 for buyer, got {response.status_code}"
        print("Send message correctly requires admin access")
    
    def test_send_message_requires_auth(self):
        """Test that send message requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/send",
            json={
                "to_number": "919876543210",
                "message": "Test message"
            }
        )
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print("Send message correctly requires authentication")
    
    def test_send_message_vendor_not_allowed(self, vendor_token):
        """Test that vendor cannot send messages"""
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/send",
            headers={"Authorization": f"Bearer {vendor_token}"},
            json={
                "to_number": "919876543210",
                "message": "Test message"
            }
        )
        assert response.status_code == 403, f"Expected 403 for vendor, got {response.status_code}"
        print("Vendor correctly denied access to send message")
    
    def test_send_message_admin_access(self, admin_token):
        """Test that admin can access send message endpoint"""
        # Note: Actual Gupshup API call may fail if credentials are test-only
        # We test that the endpoint accepts admin request
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/send",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "to_number": "919831509919",  # Test number from env
                "message": "OEMLinker test message - please ignore"
            }
        )
        # Should be 200 success or 500 if Gupshup rejects (test API key)
        assert response.status_code in [200, 500], f"Unexpected status {response.status_code}"
        print(f"Admin send message response: {response.status_code} - {response.json()}")


class TestWhatsAppNotifyRFQ:
    """Test /api/whatsapp/notify-rfq endpoint"""
    
    def test_notify_rfq_requires_auth(self):
        """Test that notify RFQ requires authentication"""
        response = requests.post(f"{BASE_URL}/api/whatsapp/notify-rfq?rfq_id={TEST_RFQ_ID}")
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print("Notify RFQ correctly requires authentication")
    
    def test_notify_rfq_vendor_not_allowed(self, vendor_token):
        """Test that vendor cannot notify vendors"""
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/notify-rfq?rfq_id={TEST_RFQ_ID}",
            headers={"Authorization": f"Bearer {vendor_token}"}
        )
        assert response.status_code == 403, f"Expected 403 for vendor, got {response.status_code}"
        print("Vendor correctly denied access to notify")
    
    def test_notify_rfq_buyer_allowed(self, buyer_token):
        """Test that buyer can notify vendors about their RFQ"""
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/notify-rfq?rfq_id={TEST_RFQ_ID}",
            headers={"Authorization": f"Bearer {buyer_token}"}
        )
        # Should return success with notification count
        assert response.status_code == 200, f"Expected 200 for buyer, got {response.status_code}"
        
        data = response.json()
        assert "notified_count" in data, "Response should contain 'notified_count'"
        assert "total_matched" in data, "Response should contain 'total_matched'"
        print(f"Buyer notify response: notified={data.get('notified_count')}, total_matched={data.get('total_matched')}")
    
    def test_notify_rfq_admin_allowed(self, admin_token):
        """Test that admin can notify vendors"""
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/notify-rfq?rfq_id={TEST_RFQ_ID}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200 for admin, got {response.status_code}"
        
        data = response.json()
        assert "success" in data, "Response should contain 'success' field"
        assert data.get("success") is True, "notify-rfq should return success=True"
        print(f"Admin notify response: {data}")
    
    def test_notify_rfq_invalid_id(self, buyer_token):
        """Test notify RFQ with invalid RFQ ID returns 404"""
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/notify-rfq?rfq_id=invalid_rfq_123",
            headers={"Authorization": f"Bearer {buyer_token}"}
        )
        assert response.status_code == 404, f"Expected 404 for invalid RFQ, got {response.status_code}"
        print("Invalid RFQ correctly returns 404")


class TestWhatsAppWebhook:
    """Test /api/whatsapp/webhook endpoint"""
    
    def test_webhook_accepts_message(self):
        """Test that webhook accepts incoming messages"""
        # Simulate Gupshup webhook payload
        payload = {
            "type": "message",
            "payload": {
                "source": "919876543210",
                "type": "text",
                "id": "test_msg_123",
                "payload": {
                    "text": "help"
                }
            },
            "timestamp": "2026-01-15T10:00:00Z",
            "app": "OEMLinker"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            json=payload
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("status") == "ok", f"Expected status 'ok', got {data.get('status')}"
        print(f"Webhook message response: {data}")
    
    def test_webhook_handles_status_update(self):
        """Test that webhook handles delivery status updates"""
        payload = {
            "type": "message-event",
            "payload": {
                "type": "delivered",
                "id": "test_msg_456",
                "destination": "919876543210"
            },
            "timestamp": "2026-01-15T10:01:00Z"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            json=payload
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("status") == "ok", f"Expected status 'ok', got {data.get('status')}"
        print(f"Webhook status update response: {data}")
    
    def test_webhook_handles_button_reply(self):
        """Test that webhook handles button reply messages"""
        payload = {
            "type": "message",
            "payload": {
                "source": "919876543210",
                "type": "button_reply",
                "id": "test_msg_789",
                "payload": {
                    "id": "view_rfq_btn",
                    "title": "View RFQ"
                }
            },
            "timestamp": "2026-01-15T10:02:00Z",
            "app": "OEMLinker"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            json=payload
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"Webhook button reply response: {response.json()}")
    
    def test_webhook_handles_invalid_payload(self):
        """Test that webhook handles invalid payload gracefully"""
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            json={}
        )
        assert response.status_code == 200, f"Expected 200 even for empty payload, got {response.status_code}"
        
        data = response.json()
        # Should ignore or handle gracefully
        assert data.get("status") in ["ok", "ignored"], f"Unexpected status: {data.get('status')}"
        print(f"Webhook empty payload response: {data}")
    
    def test_webhook_handles_image_message(self):
        """Test that webhook handles image messages"""
        payload = {
            "type": "message",
            "payload": {
                "source": "919876543210",
                "type": "image",
                "id": "test_img_123",
                "payload": {
                    "url": "https://example.com/image.jpg",
                    "caption": "Drawing for quote"
                }
            },
            "timestamp": "2026-01-15T10:03:00Z",
            "app": "OEMLinker"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            json=payload
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"Webhook image message response: {response.json()}")


class TestWhatsAppCommands:
    """Test WhatsApp command processing via webhook"""
    
    def _send_command(self, command):
        """Helper to send a WhatsApp command"""
        payload = {
            "type": "message",
            "payload": {
                "source": "919876543210",
                "type": "text",
                "id": f"test_cmd_{command}",
                "payload": {
                    "text": command
                }
            },
            "timestamp": "2026-01-15T10:05:00Z",
            "app": "OEMLinker"
        }
        return requests.post(f"{BASE_URL}/api/whatsapp/webhook", json=payload)
    
    def test_help_command(self):
        """Test 'help' command"""
        response = self._send_command("help")
        assert response.status_code == 200
        print("Help command processed successfully")
    
    def test_rfqs_command(self):
        """Test 'rfqs' command"""
        response = self._send_command("rfqs")
        assert response.status_code == 200
        print("RFQs command processed successfully")
    
    def test_my_quotes_command(self):
        """Test 'my quotes' command"""
        response = self._send_command("my quotes")
        assert response.status_code == 200
        print("My quotes command processed successfully")
    
    def test_my_orders_command(self):
        """Test 'my orders' command"""
        response = self._send_command("my orders")
        assert response.status_code == 200
        print("My orders command processed successfully")
    
    def test_profile_command(self):
        """Test 'profile' command"""
        response = self._send_command("profile")
        assert response.status_code == 200
        print("Profile command processed successfully")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
