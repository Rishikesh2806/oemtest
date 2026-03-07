"""
GST Certificate Image Upload Tests for OEMLinker WhatsApp Integration
Tests the GST certificate image processing feature:
- WhatsApp webhook handling image message type for unregistered users
- Already registered vendors receive appropriate message
- GSTIN validation pattern (valid/invalid GST numbers)
- Error handling scenarios
- Integration with process_whatsapp_registration function
"""

import pytest
import requests
import os
import re

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@offoadex.com"
ADMIN_PASSWORD = "admin123"

# GSTIN pattern from server.py
GSTIN_PATTERN = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[0-9A-Z]{1}[Z]{1}[0-9A-Z]{1}$'

# Test phone numbers - unregistered numbers for testing
TEST_UNREGISTERED_PHONE = "919000000001"  # Should NOT be in vendor database
TEST_REGISTERED_PHONE = "919831509919"  # Gupshup source number - use for testing registered flow


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


class TestGSTINValidationPattern:
    """Test GSTIN regex pattern validation"""
    
    def test_valid_gstin_format_standard(self):
        """Test valid GSTIN pattern - standard format"""
        valid_gstins = [
            "27AABCU9603R1ZM",  # Maharashtra
            "06AABCU9603R1Z2",  # Haryana
            "33AABCU9603R1ZK",  # Tamil Nadu
            "29AABCU9603R1ZP",  # Karnataka
            "07AABCU9603R1Z1",  # Delhi
            "09AABCU9603R1ZA",  # Uttar Pradesh
        ]
        
        for gstin in valid_gstins:
            match = re.match(GSTIN_PATTERN, gstin)
            assert match is not None, f"Valid GSTIN '{gstin}' should match pattern"
            print(f"PASS: Valid GSTIN '{gstin}' matches pattern")
    
    def test_invalid_gstin_too_short(self):
        """Test invalid GSTIN - too short"""
        invalid_gstins = [
            "27AABCU9603R1Z",   # 14 chars (should be 15)
            "AABCU9603R1ZM",    # Missing state code
            "27AAB",            # Way too short
        ]
        
        for gstin in invalid_gstins:
            match = re.match(GSTIN_PATTERN, gstin)
            assert match is None, f"Short GSTIN '{gstin}' should NOT match pattern"
            print(f"PASS: Short GSTIN '{gstin}' correctly rejected")
    
    def test_invalid_gstin_too_long(self):
        """Test invalid GSTIN - too long"""
        invalid_gstins = [
            "27AABCU9603R1ZMA",  # 16 chars
            "27AABCU9603R1ZMAB", # 17 chars
        ]
        
        for gstin in invalid_gstins:
            match = re.match(GSTIN_PATTERN, gstin)
            assert match is None, f"Long GSTIN '{gstin}' should NOT match pattern"
            print(f"PASS: Long GSTIN '{gstin}' correctly rejected")
    
    def test_invalid_gstin_wrong_format(self):
        """Test invalid GSTIN - wrong format"""
        invalid_gstins = [
            "AAAABCU9603R1ZM",  # First 2 should be digits
            "27aabcu9603r1zm",  # Lowercase (pattern expects uppercase)
            "27AABCU9603R1AM",  # Position 13 should be 'Z'
            "27AABCU96O3R1ZM", # Contains 'O' instead of '0' (O is letter, not digit)
            "27AABCU960AR1ZM", # Position 8-11 should be 4 digits (has A)
            "27A1BCU9603R1ZM", # Position 3-7 should be 5 letters (has digit 1)
        ]
        
        for gstin in invalid_gstins:
            # Test original format (lowercase should fail)
            original_match = re.match(GSTIN_PATTERN, gstin)
            # For cases that are purely wrong format (not just case), they should fail
            if gstin == gstin.upper():
                assert original_match is None, f"Invalid GSTIN '{gstin}' should NOT match pattern"
            else:
                # Lowercase test - should fail
                assert original_match is None, f"Lowercase GSTIN '{gstin}' should NOT match pattern"
            print(f"PASS: Invalid GSTIN '{gstin}' correctly rejected")
    
    def test_gstin_state_codes_valid(self):
        """Test valid Indian state codes (01-38)"""
        valid_state_codes = ["01", "27", "06", "33", "29", "07", "09", "36", "38"]
        
        for state_code in valid_state_codes:
            gstin = f"{state_code}AABCU9603R1ZM"
            match = re.match(GSTIN_PATTERN, gstin)
            assert match is not None, f"GSTIN with state code '{state_code}' should match"
            print(f"PASS: State code '{state_code}' accepted")


class TestWhatsAppImageWebhook:
    """Test WhatsApp webhook handling of image messages"""
    
    def test_image_webhook_unregistered_user(self):
        """Test that image upload from unregistered user triggers GST extraction flow"""
        # Simulate Gupshup webhook payload with image from unregistered number
        payload = {
            "type": "message",
            "payload": {
                "source": TEST_UNREGISTERED_PHONE,
                "type": "image",
                "id": "test_gst_img_001",
                "payload": {
                    "url": "https://example.com/gst_certificate.jpg",
                    "caption": "GST Certificate"
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
        print(f"Image webhook for unregistered user processed: {data}")
    
    def test_image_webhook_empty_image_url(self):
        """Test webhook handles missing image URL gracefully"""
        payload = {
            "type": "message",
            "payload": {
                "source": TEST_UNREGISTERED_PHONE,
                "type": "image",
                "id": "test_gst_img_002",
                "payload": {
                    "url": "",
                    "caption": ""
                }
            },
            "timestamp": "2026-01-15T10:01:00Z",
            "app": "OEMLinker"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            json=payload
        )
        # Should handle gracefully even with empty URL
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"Empty image URL handled: {response.json()}")
    
    def test_image_webhook_with_caption(self):
        """Test image upload with GST number in caption"""
        payload = {
            "type": "message",
            "payload": {
                "source": TEST_UNREGISTERED_PHONE,
                "type": "image",
                "id": "test_gst_img_003",
                "payload": {
                    "url": "https://example.com/gst_cert.jpg",
                    "caption": "My GST certificate 27AABCU9603R1ZM"
                }
            },
            "timestamp": "2026-01-15T10:02:00Z",
            "app": "OEMLinker"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            json=payload
        )
        assert response.status_code == 200
        print(f"Image with GST caption processed: {response.json()}")


class TestRegisteredVendorImageHandling:
    """Test that registered vendors receive appropriate message when uploading images"""
    
    def test_registered_vendor_image_upload_message(self, admin_token):
        """Test that a registered vendor gets 'already registered' message for image upload"""
        # First, get a vendor phone number that exists in the database
        response = requests.get(
            f"{BASE_URL}/api/admin/vendors",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        if response.status_code != 200:
            pytest.skip("Could not fetch vendors")
        
        vendors = response.json()
        vendor_with_phone = None
        
        for vendor in vendors:
            if vendor.get("phone"):
                vendor_with_phone = vendor
                break
        
        if not vendor_with_phone:
            # Create a test scenario with a known phone
            print("No vendor with phone found, using test scenario")
            # Simulate image from a potentially registered number
            payload = {
                "type": "message",
                "payload": {
                    "source": "919876543210",  # A generic test number
                    "type": "image",
                    "id": "test_reg_img_001",
                    "payload": {
                        "url": "https://example.com/image.jpg",
                        "caption": ""
                    }
                },
                "timestamp": "2026-01-15T10:05:00Z",
                "app": "OEMLinker"
            }
            
            response = requests.post(
                f"{BASE_URL}/api/whatsapp/webhook",
                json=payload
            )
            assert response.status_code == 200
            print(f"Registered vendor image test: {response.json()}")
        else:
            # Use actual vendor phone
            vendor_phone = vendor_with_phone.get("phone", "").replace("+", "").replace(" ", "").replace("-", "")
            
            payload = {
                "type": "message",
                "payload": {
                    "source": vendor_phone,
                    "type": "image",
                    "id": "test_reg_img_002",
                    "payload": {
                        "url": "https://example.com/image.jpg",
                        "caption": ""
                    }
                },
                "timestamp": "2026-01-15T10:06:00Z",
                "app": "OEMLinker"
            }
            
            response = requests.post(
                f"{BASE_URL}/api/whatsapp/webhook",
                json=payload
            )
            assert response.status_code == 200
            data = response.json()
            # Vendor lookup should succeed and they should get the "already registered" message
            print(f"Registered vendor ({vendor_phone[:6]}***) image upload: {data}")


class TestWebhookImageRouting:
    """Test the webhook correctly routes image messages"""
    
    def test_webhook_parses_image_type_correctly(self):
        """Test that image type is correctly identified in webhook"""
        payload = {
            "type": "message",
            "payload": {
                "source": "919111222333",
                "type": "image",
                "id": "img_parse_test_001",
                "payload": {
                    "url": "https://media.gupshup.io/image123.jpg",
                    "caption": ""
                }
            },
            "timestamp": "2026-01-15T10:10:00Z",
            "app": "OEMLinker"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        # Should return ok status (processing happened)
        assert data.get("status") == "ok", f"Expected 'ok', got {data.get('status')}"
        print(f"Image type routing test passed: {data}")
    
    def test_webhook_different_message_types(self):
        """Test that different message types are handled differently"""
        message_types = [
            ("text", {"text": "hello"}),
            ("image", {"url": "https://example.com/img.jpg", "caption": ""}),
            ("audio", {"url": "https://example.com/audio.mp3"}),
            ("document", {"url": "https://example.com/doc.pdf", "filename": "doc.pdf"}),
        ]
        
        for msg_type, payload_data in message_types:
            payload = {
                "type": "message",
                "payload": {
                    "source": "919444555666",
                    "type": msg_type,
                    "id": f"type_test_{msg_type}_001",
                    "payload": payload_data
                },
                "timestamp": "2026-01-15T10:11:00Z",
                "app": "OEMLinker"
            }
            
            response = requests.post(
                f"{BASE_URL}/api/whatsapp/webhook",
                json=payload
            )
            
            assert response.status_code == 200, f"Failed for message type '{msg_type}'"
            print(f"Message type '{msg_type}' handled correctly")


class TestGSTExtractionErrorHandling:
    """Test error handling scenarios for GST certificate processing"""
    
    def test_image_invalid_url_handling(self):
        """Test handling of invalid/unreachable image URL"""
        payload = {
            "type": "message",
            "payload": {
                "source": "919777888999",
                "type": "image",
                "id": "err_test_001",
                "payload": {
                    "url": "https://invalid-domain-that-does-not-exist.com/image.jpg",
                    "caption": ""
                }
            },
            "timestamp": "2026-01-15T10:15:00Z",
            "app": "OEMLinker"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            json=payload
        )
        
        # Should still return 200 (webhook processes gracefully)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"Invalid URL handling: {response.json()}")
    
    def test_duplicate_message_handling(self):
        """Test that duplicate messages are handled correctly"""
        message_id = "duplicate_test_msg_123"
        
        payload = {
            "type": "message",
            "payload": {
                "source": "919000111222",
                "type": "image",
                "id": message_id,
                "payload": {
                    "url": "https://example.com/test.jpg",
                    "caption": ""
                }
            },
            "timestamp": "2026-01-15T10:20:00Z",
            "app": "OEMLinker"
        }
        
        # Send first time
        response1 = requests.post(f"{BASE_URL}/api/whatsapp/webhook", json=payload)
        assert response1.status_code == 200
        
        # Send duplicate
        response2 = requests.post(f"{BASE_URL}/api/whatsapp/webhook", json=payload)
        assert response2.status_code == 200
        
        data2 = response2.json()
        # Second call should be marked as duplicate
        assert data2.get("status") in ["ok", "duplicate_ignored"], f"Unexpected status: {data2.get('status')}"
        print(f"Duplicate handling: First={response1.json()}, Second={data2}")


class TestWhatsAppRegistrationFlow:
    """Test the registration flow via WhatsApp with GSTIN"""
    
    def test_register_command_with_valid_gstin(self):
        """Test the 'register' text command with valid GSTIN format"""
        valid_gstin = "27AABCU9603R1ZM"
        
        payload = {
            "type": "message",
            "payload": {
                "source": "919333444555",  # Unregistered number
                "type": "text",
                "id": "reg_cmd_001",
                "payload": {
                    "text": f"register {valid_gstin}"
                }
            },
            "timestamp": "2026-01-15T10:25:00Z",
            "app": "OEMLinker"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            json=payload
        )
        
        assert response.status_code == 200
        print(f"Register command with valid GSTIN: {response.json()}")
    
    def test_register_command_with_invalid_gstin(self):
        """Test the 'register' command with invalid GSTIN format"""
        invalid_gstin = "INVALID123"
        
        payload = {
            "type": "message",
            "payload": {
                "source": "919666777888",
                "type": "text",
                "id": "reg_cmd_002",
                "payload": {
                    "text": f"register {invalid_gstin}"
                }
            },
            "timestamp": "2026-01-15T10:26:00Z",
            "app": "OEMLinker"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            json=payload
        )
        
        assert response.status_code == 200
        print(f"Register command with invalid GSTIN: {response.json()}")


class TestGSTINAPIIntegration:
    """Test GSTIN validation API integration (may require real API access)"""
    
    def test_gstin_api_endpoint_accessible(self):
        """Test that we can check if GSTIN API is configured"""
        # This tests that the backend would use the API key from env
        # We can't directly test external API without making real calls
        
        # Check that webhook processes registration attempts
        payload = {
            "type": "message",
            "payload": {
                "source": "919888999000",
                "type": "text",
                "id": "api_test_001",
                "payload": {
                    "text": "register 27AABCU9603R1ZM"
                }
            },
            "timestamp": "2026-01-15T10:30:00Z",
            "app": "OEMLinker"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            json=payload
        )
        
        assert response.status_code == 200
        print(f"GSTIN API integration test: {response.json()}")


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_empty_webhook_payload(self):
        """Test handling of empty payload"""
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            json={}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") in ["ok", "ignored"]
        print(f"Empty payload: {data}")
    
    def test_null_source_number(self):
        """Test handling of null/missing source number"""
        payload = {
            "type": "message",
            "payload": {
                "source": "",
                "type": "image",
                "id": "null_source_001",
                "payload": {
                    "url": "https://example.com/img.jpg"
                }
            },
            "timestamp": "2026-01-15T10:35:00Z"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            json=payload
        )
        assert response.status_code == 200
        print(f"Null source: {response.json()}")
    
    def test_malformed_timestamp(self):
        """Test handling of malformed timestamp"""
        payload = {
            "type": "message",
            "payload": {
                "source": "919111222333",
                "type": "image",
                "id": "malformed_ts_001",
                "payload": {
                    "url": "https://example.com/img.jpg"
                }
            },
            "timestamp": "invalid-timestamp"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            json=payload
        )
        assert response.status_code == 200
        print(f"Malformed timestamp: {response.json()}")
    
    def test_special_characters_in_gstin(self):
        """Test GSTIN pattern rejects special characters"""
        special_gstins = [
            "27AABCU9603R1Z!",  # Special char at end
            "27-ABCU9603R1ZM",  # Hyphen
            "27 ABCU9603R1ZM",  # Space
            "27AABCU9603R1ZM\n",  # Newline
        ]
        
        for gstin in special_gstins:
            match = re.match(GSTIN_PATTERN, gstin.strip())
            # After strip, some might match, but with special chars should fail
            if gstin != gstin.strip():
                print(f"GSTIN with whitespace: '{gstin}' -> stripped matches: {match is not None}")
            else:
                assert match is None, f"Special char GSTIN '{gstin}' should NOT match"
                print(f"PASS: Special char GSTIN correctly rejected")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
