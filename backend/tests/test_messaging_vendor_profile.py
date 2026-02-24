"""
Test Suite for Vendor Profile and Messaging APIs
Tests: /api/vendors/{vendor_id}/full, /api/messages/* endpoints
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://vendor-matching-demo.preview.emergentagent.com').rstrip('/')

# Test users for messaging flow
TEST_BUYER_EMAIL = f"test_buyer_{uuid.uuid4().hex[:8]}@test.com"
TEST_BUYER_PASSWORD = "TestPass123!"
TEST_BUYER_NAME = "Test Buyer"

TEST_VENDOR_EMAIL = f"test_vendor_{uuid.uuid4().hex[:8]}@test.com"
TEST_VENDOR_PASSWORD = "TestPass123!"
TEST_VENDOR_NAME = "Test Vendor Company"


class TestSetup:
    """Setup test users for messaging tests"""
    buyer_token = None
    buyer_user_id = None
    vendor_token = None
    vendor_user_id = None
    vendor_id = None
    
    @classmethod
    def setup_class(cls):
        """Register test buyer and vendor"""
        # Register buyer
        print(f"\n=== Registering test buyer: {TEST_BUYER_EMAIL} ===")
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": TEST_BUYER_EMAIL,
            "password": TEST_BUYER_PASSWORD,
            "name": TEST_BUYER_NAME,
            "role": "buyer"
        })
        print(f"Buyer registration: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            cls.buyer_token = data.get("access_token")
            cls.buyer_user_id = data.get("user", {}).get("user_id")
            print(f"Buyer user_id: {cls.buyer_user_id}")
        else:
            print(f"Buyer registration failed: {response.text}")
        
        # Register vendor
        print(f"\n=== Registering test vendor: {TEST_VENDOR_EMAIL} ===")
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": TEST_VENDOR_EMAIL,
            "password": TEST_VENDOR_PASSWORD,
            "name": TEST_VENDOR_NAME,
            "role": "vendor"
        })
        print(f"Vendor registration: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            cls.vendor_token = data.get("access_token")
            cls.vendor_user_id = data.get("user", {}).get("user_id")
            print(f"Vendor user_id: {cls.vendor_user_id}")
        else:
            print(f"Vendor registration failed: {response.text}")
        
        # Create vendor profile
        if cls.vendor_token:
            print(f"\n=== Creating vendor profile ===")
            response = requests.post(
                f"{BASE_URL}/api/vendors/profile",
                json={
                    "company_name": "Test Manufacturing Co",
                    "description": "Test manufacturing company for testing",
                    "address": "123 Test Street",
                    "city": "Test City",
                    "country": "Test Country",
                    "phone": "+1-555-123-4567",
                    "website": "https://test-vendor.com",
                    "certifications": ["ISO 9001", "AS9100"],
                    "industries": ["Aerospace", "Automotive"],
                    "materials_handled": ["Aluminum", "Steel", "Titanium"]
                },
                headers={"Authorization": f"Bearer {cls.vendor_token}"}
            )
            print(f"Vendor profile creation: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                cls.vendor_id = data.get("vendor_id")
                print(f"Vendor ID: {cls.vendor_id}")
            else:
                print(f"Vendor profile creation failed: {response.text}")


class TestVendorFullProfile:
    """Test /api/vendors/{vendor_id}/full endpoint"""
    
    def test_get_vendor_full_profile_success(self):
        """Test getting full vendor profile with machines and stats"""
        if not TestSetup.vendor_id or not TestSetup.buyer_token:
            pytest.skip("Test users not created")
        
        response = requests.get(
            f"{BASE_URL}/api/vendors/{TestSetup.vendor_id}/full",
            headers={"Authorization": f"Bearer {TestSetup.buyer_token}"}
        )
        
        print(f"\n=== Get vendor full profile ===")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        
        # Check vendor basic info
        assert "vendor_id" in data, "Missing vendor_id"
        assert "company_name" in data, "Missing company_name"
        assert data["company_name"] == "Test Manufacturing Co"
        
        # Check contact info is included
        assert "contact" in data, "Missing contact info"
        assert data["contact"]["email"] == TEST_VENDOR_EMAIL, "Contact email mismatch"
        assert data["contact"]["phone"] == "+1-555-123-4567", "Contact phone mismatch"
        assert data["contact"]["website"] == "https://test-vendor.com", "Contact website mismatch"
        
        # Check stats section
        assert "stats" in data, "Missing stats section"
        assert "completed_orders" in data["stats"], "Missing completed_orders stat"
        assert "total_quotes" in data["stats"], "Missing total_quotes stat"
        
        # Check machines array (could be empty)
        assert "machines" in data, "Missing machines array"
        assert isinstance(data["machines"], list), "machines should be a list"
        
        print("PASS: Vendor full profile retrieved successfully")
    
    def test_get_vendor_full_profile_not_found(self):
        """Test getting non-existent vendor profile"""
        if not TestSetup.buyer_token:
            pytest.skip("Buyer not created")
        
        response = requests.get(
            f"{BASE_URL}/api/vendors/nonexistent_vendor_123/full",
            headers={"Authorization": f"Bearer {TestSetup.buyer_token}"}
        )
        
        print(f"\n=== Get non-existent vendor profile ===")
        print(f"Status: {response.status_code}")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: 404 returned for non-existent vendor")
    
    def test_get_vendor_full_profile_unauthenticated(self):
        """Test getting vendor profile without authentication"""
        if not TestSetup.vendor_id:
            pytest.skip("Vendor not created")
        
        response = requests.get(
            f"{BASE_URL}/api/vendors/{TestSetup.vendor_id}/full"
        )
        
        print(f"\n=== Get vendor profile unauthenticated ===")
        print(f"Status: {response.status_code}")
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: 401 returned for unauthenticated request")


class TestMessagingAPI:
    """Test messaging APIs: /api/messages/*"""
    
    conversation_id = None
    
    def test_send_message(self):
        """Test sending a message from buyer to vendor"""
        if not TestSetup.buyer_token or not TestSetup.vendor_user_id:
            pytest.skip("Test users not created")
        
        response = requests.post(
            f"{BASE_URL}/api/messages",
            json={
                "receiver_id": TestSetup.vendor_user_id,
                "content": "Hello, I am interested in your manufacturing services."
            },
            headers={"Authorization": f"Bearer {TestSetup.buyer_token}"}
        )
        
        print(f"\n=== Send message from buyer to vendor ===")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "message_id" in data, "Missing message_id"
        assert "conversation_id" in data, "Missing conversation_id"
        
        TestMessagingAPI.conversation_id = data["conversation_id"]
        print(f"PASS: Message sent, conversation_id: {TestMessagingAPI.conversation_id}")
    
    def test_send_message_with_rfq(self):
        """Test sending a message with RFQ reference"""
        if not TestSetup.buyer_token or not TestSetup.vendor_user_id:
            pytest.skip("Test users not created")
        
        response = requests.post(
            f"{BASE_URL}/api/messages",
            json={
                "receiver_id": TestSetup.vendor_user_id,
                "rfq_id": "test_rfq_123",
                "content": "Can you quote on this RFQ?"
            },
            headers={"Authorization": f"Bearer {TestSetup.buyer_token}"}
        )
        
        print(f"\n=== Send message with RFQ reference ===")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "message_id" in data
        assert "conversation_id" in data
        # Conversation ID should include RFQ reference
        assert "test_rfq_123" in data["conversation_id"]
        print("PASS: Message with RFQ reference sent")
    
    def test_get_conversations(self):
        """Test getting user's conversations"""
        if not TestSetup.buyer_token:
            pytest.skip("Buyer not created")
        
        response = requests.get(
            f"{BASE_URL}/api/messages/conversations",
            headers={"Authorization": f"Bearer {TestSetup.buyer_token}"}
        )
        
        print(f"\n=== Get buyer conversations ===")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        assert len(data) > 0, "Should have at least one conversation"
        
        # Check conversation structure
        conv = data[0]
        assert "conversation_id" in conv, "Missing conversation_id"
        assert "participants" in conv, "Missing participants"
        assert "other_party" in conv, "Missing other_party info"
        assert "last_message" in conv or conv.get("last_message") is None, "Missing last_message"
        
        print(f"PASS: Found {len(data)} conversation(s)")
    
    def test_get_conversation_messages(self):
        """Test getting messages in a conversation"""
        if not TestSetup.buyer_token or not TestMessagingAPI.conversation_id:
            pytest.skip("Conversation not created")
        
        response = requests.get(
            f"{BASE_URL}/api/messages/conversation/{TestMessagingAPI.conversation_id}",
            headers={"Authorization": f"Bearer {TestSetup.buyer_token}"}
        )
        
        print(f"\n=== Get conversation messages ===")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "conversation" in data, "Missing conversation info"
        assert "messages" in data, "Missing messages array"
        assert isinstance(data["messages"], list), "messages should be a list"
        assert len(data["messages"]) > 0, "Should have at least one message"
        
        # Check message structure
        msg = data["messages"][0]
        assert "message_id" in msg, "Missing message_id"
        assert "sender_id" in msg, "Missing sender_id"
        assert "content" in msg, "Missing content"
        assert "created_at" in msg, "Missing created_at"
        
        print(f"PASS: Retrieved {len(data['messages'])} message(s)")
    
    def test_get_or_create_conversation(self):
        """Test getting or creating a conversation with another user"""
        if not TestSetup.buyer_token or not TestSetup.vendor_user_id:
            pytest.skip("Test users not created")
        
        response = requests.get(
            f"{BASE_URL}/api/messages/with/{TestSetup.vendor_user_id}",
            headers={"Authorization": f"Bearer {TestSetup.buyer_token}"}
        )
        
        print(f"\n=== Get or create conversation ===")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "conversation" in data, "Missing conversation info"
        assert "messages" in data, "Missing messages array"
        assert "other_party" in data.get("conversation", {}), "Missing other_party info"
        
        print("PASS: Got/created conversation successfully")
    
    def test_get_unread_count(self):
        """Test getting unread message count"""
        if not TestSetup.vendor_token:
            pytest.skip("Vendor not created")
        
        response = requests.get(
            f"{BASE_URL}/api/messages/unread-count",
            headers={"Authorization": f"Bearer {TestSetup.vendor_token}"}
        )
        
        print(f"\n=== Get unread count for vendor ===")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "unread_count" in data, "Missing unread_count"
        assert isinstance(data["unread_count"], int), "unread_count should be int"
        
        print(f"PASS: Unread count: {data['unread_count']}")
    
    def test_vendor_reply_to_buyer(self):
        """Test vendor sending reply to buyer"""
        if not TestSetup.vendor_token or not TestSetup.buyer_user_id:
            pytest.skip("Test users not created")
        
        response = requests.post(
            f"{BASE_URL}/api/messages",
            json={
                "receiver_id": TestSetup.buyer_user_id,
                "content": "Thank you for your interest! We can definitely help with your project."
            },
            headers={"Authorization": f"Bearer {TestSetup.vendor_token}"}
        )
        
        print(f"\n=== Vendor reply to buyer ===")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "message_id" in data
        print("PASS: Vendor reply sent successfully")
    
    def test_send_message_unauthenticated(self):
        """Test sending message without authentication"""
        response = requests.post(
            f"{BASE_URL}/api/messages",
            json={
                "receiver_id": "some_user",
                "content": "This should fail"
            }
        )
        
        print(f"\n=== Send message unauthenticated ===")
        print(f"Status: {response.status_code}")
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: 401 returned for unauthenticated request")


class TestVendorListAndBasicInfo:
    """Test basic vendor APIs"""
    
    def test_get_vendor_by_id(self):
        """Test getting vendor by ID (basic info)"""
        if not TestSetup.vendor_id:
            pytest.skip("Vendor not created")
        
        response = requests.get(
            f"{BASE_URL}/api/vendors/{TestSetup.vendor_id}"
        )
        
        print(f"\n=== Get vendor by ID (basic) ===")
        print(f"Status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["vendor_id"] == TestSetup.vendor_id
        assert data["company_name"] == "Test Manufacturing Co"
        print("PASS: Vendor basic info retrieved")
    
    def test_list_vendors(self):
        """Test listing vendors"""
        response = requests.get(f"{BASE_URL}/api/vendors/list")
        
        print(f"\n=== List vendors ===")
        print(f"Status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"PASS: Found {len(data)} approved vendors")


# Entry point for pytest
if __name__ == "__main__":
    # Run setup first
    TestSetup.setup_class()
    
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
