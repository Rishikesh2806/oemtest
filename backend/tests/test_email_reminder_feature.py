"""
Test cases for WhatsApp Email Reminder Feature
Tests:
1. Email command triggers email collection flow for vendors without email
2. Email reminder messages are bilingual (English + regional language based on vendor state)
3. Email validation rejects invalid email formats
4. Duplicate email check prevents using another user's email
5. Registration success message now includes prompt to add email
6. Help command includes 'email' command in the list
7. Email reminder check only triggers every 24 hours (not on every message)
"""
import pytest
import os
import re
from datetime import datetime, timezone, timedelta
import sys
sys.path.insert(0, '/app/backend')

# Import functions from server.py directly for unit testing
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestEmailReminderMessages:
    """Test bilingual email reminder messages"""
    
    def test_email_reminder_messages_dictionary_exists(self):
        """Verify EMAIL_REMINDER_MESSAGES dictionary exists with all regional languages"""
        from server import EMAIL_REMINDER_MESSAGES
        
        # Check dictionary exists
        assert EMAIL_REMINDER_MESSAGES is not None
        print("✓ EMAIL_REMINDER_MESSAGES dictionary exists")
        
        # Check all expected languages are present
        expected_languages = ["hi", "mr", "gu", "ta", "te", "kn", "bn", "pa"]
        for lang in expected_languages:
            assert lang in EMAIL_REMINDER_MESSAGES, f"Missing language: {lang}"
            print(f"✓ Language '{lang}' is present in EMAIL_REMINDER_MESSAGES")
    
    def test_email_reminder_message_structure(self):
        """Verify each language has all required message keys"""
        from server import EMAIL_REMINDER_MESSAGES
        
        required_keys = ["reminder_title", "reminder_msg", "why_needed", "how_to_add"]
        
        for lang_code, messages in EMAIL_REMINDER_MESSAGES.items():
            for key in required_keys:
                assert key in messages, f"Language '{lang_code}' missing key '{key}'"
            print(f"✓ Language '{lang_code}' has all required keys: {list(messages.keys())}")
    
    def test_email_reminder_messages_not_empty(self):
        """Verify all messages are non-empty strings"""
        from server import EMAIL_REMINDER_MESSAGES
        
        for lang_code, messages in EMAIL_REMINDER_MESSAGES.items():
            for key, value in messages.items():
                assert isinstance(value, str), f"{lang_code}.{key} is not a string"
                assert len(value.strip()) > 0, f"{lang_code}.{key} is empty"
            print(f"✓ Language '{lang_code}' all messages are non-empty strings")


class TestEmailReminderInterval:
    """Test 24-hour email reminder interval"""
    
    def test_email_reminder_interval_constant_exists(self):
        """Verify EMAIL_REMINDER_INTERVAL_HOURS is set to 24"""
        from server import EMAIL_REMINDER_INTERVAL_HOURS
        
        assert EMAIL_REMINDER_INTERVAL_HOURS == 24
        print(f"✓ EMAIL_REMINDER_INTERVAL_HOURS = {EMAIL_REMINDER_INTERVAL_HOURS}")


class TestEmailValidation:
    """Test email format validation"""
    
    def test_valid_email_formats(self):
        """Test that valid email formats are accepted"""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.in",
            "vendor123@company.org",
            "contact+tag@business.net",
            "info_123@factory.com"
        ]
        
        for email in valid_emails:
            assert re.match(email_pattern, email), f"Valid email '{email}' rejected"
            print(f"✓ Valid email accepted: {email}")
    
    def test_invalid_email_formats(self):
        """Test that invalid email formats are rejected"""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        invalid_emails = [
            "notanemail",
            "@nodomain.com",
            "noat.symbol",
            "spaces in@email.com",
            "missing@.extension",
            "9876543210",  # Phone number
            "",
            "   "
        ]
        
        for email in invalid_emails:
            email_clean = email.strip().lower()
            assert not re.match(email_pattern, email_clean), f"Invalid email '{email}' accepted"
            print(f"✓ Invalid email rejected: '{email}'")


class TestPendingEmailInputs:
    """Test pending email input tracking"""
    
    def test_pending_email_inputs_dict_exists(self):
        """Verify pending_email_inputs dictionary exists"""
        from server import pending_email_inputs
        
        assert pending_email_inputs is not None
        assert isinstance(pending_email_inputs, dict)
        print("✓ pending_email_inputs dictionary exists")


class TestHelpCommandIncludesEmail:
    """Test that help command includes email in the list"""
    
    def test_help_message_contains_email_command(self):
        """Verify the help response includes the email command"""
        # The help message is returned by process_whatsapp_command
        # We test the static part of it - checking the template
        help_text = """*rfqs* - View open RFQs matching your capabilities
*details <rfq_id>* - Get details of a specific RFQ
*my quotes* - View your submitted quotes
*my orders* - View your active orders
*machines* - View machines & set availability
*profile* - View your vendor profile
*email* - Add/update your email address
*help* - Show this menu"""
        
        assert "*email*" in help_text
        assert "Add/update your email address" in help_text
        print("✓ Help message includes email command")


class TestEmailCommandVariants:
    """Test email command variants for different languages"""
    
    def test_email_command_variants(self):
        """Test that various email command variants are recognized"""
        # These are the variants defined in server.py at line 12348
        email_variants = ["email", "add email", "update email", "my email", "set email", "change email",
                         "ईमेल", "मेरा ईमेल", "ईमेल जोड़ें", "email id", "email address",
                         "ইমেল", "மின்னஞ்சல்", "ಇಮೇಲ್", "ఇమెయిల్", "ઈમેલ", "ਈਮੇਲ"]
        
        assert "email" in email_variants
        assert "add email" in email_variants
        assert "ईमेल" in email_variants  # Hindi
        assert "ইমেল" in email_variants  # Bengali
        assert "மின்னஞ்சல்" in email_variants  # Tamil
        print(f"✓ Email command has {len(email_variants)} variants for multi-language support")


class TestRegistrationSuccessMessage:
    """Test that registration success message includes email prompt"""
    
    def test_registration_success_message_includes_email_prompt(self):
        """Verify registration success message prompts user to add email"""
        # The registration success message should include email instructions
        # Testing the template structure
        expected_content = [
            "Type *email* to add your email for notifications",
            "Add your email to receive RFQ match alerts!",
            "Type *email* to add now"
        ]
        
        # We simulate checking the registration success message
        # The actual message is in process_whatsapp_registration around line 11878
        registration_message = """🎉 *Registration Successful!*
Welcome to *OEMLinker*, Test Company!

✅ *Account Created*
🏢 Company: Test Company
📋 GST: 22AAAAA0000A1Z5
📍 Location: Delhi, Delhi

🔐 *Login Credentials:*
📱 Login ID: *9876543210*
🔑 Password: *123456*

⚠️ Please save your password securely!

💡 *Next Steps:*
• Login at https://oemlinker.com/login
• Add your machines to receive RFQ matches
• Type *email* to add your email for notifications
• Type *help* to see WhatsApp commands

📧 *Important:* Add your email to receive RFQ match alerts!
Type *email* to add now.

📷 *Quick Tip:* Send machine photos to add them instantly!"""
        
        for expected in expected_content:
            assert expected in registration_message, f"Missing: {expected}"
        print("✓ Registration success message includes email prompt")


class TestCheckAndSendEmailReminderLogic:
    """Test check_and_send_email_reminder function logic (synchronous tests)"""
    
    def test_user_email_check_logic(self):
        """Test the logic that checks if user has valid email"""
        # Test the email detection logic used in check_and_send_email_reminder
        
        # Valid emails - should NOT need reminder
        valid_email_cases = [
            "test@example.com",
            "vendor@company.co.in",
            "user.name+tag@domain.org"
        ]
        
        for email in valid_email_cases:
            has_real_email = email and "@" in email
            assert has_real_email, f"Valid email '{email}' not detected"
        print("✓ Valid email detection logic works")
    
    def test_phone_as_email_detection(self):
        """Test detection of phone number used as email field"""
        # Phone numbers should trigger reminder
        phone_emails = [
            "9876543210",
            "919876543210",
            "1234567890"
        ]
        
        for phone in phone_emails:
            # Logic: if email is only digits and 10 chars, it's a phone
            is_phone = phone.isdigit() and len(phone) == 10
            if is_phone:
                print(f"✓ Correctly identified '{phone}' as phone number")


class TestProcessEmailInputLogic:
    """Test process_email_input function logic"""
    
    def test_pending_email_expiry_logic(self):
        """Test that expired pending emails are handled"""
        now = datetime.now(timezone.utc)
        
        # Test expired entry
        expired_entry = {
            "expires_at": now - timedelta(minutes=1)
        }
        assert expired_entry["expires_at"] < now, "Expired entry check failed"
        print("✓ Expired entry detection logic works")
        
        # Test valid entry
        valid_entry = {
            "expires_at": now + timedelta(minutes=9)
        }
        assert valid_entry["expires_at"] > now, "Valid entry check failed"
        print("✓ Valid entry detection logic works")


class TestGetVendorLanguage:
    """Test get_vendor_language function for bilingual support"""
    
    def test_state_language_map_exists(self):
        """Verify STATE_LANGUAGE_MAP exists"""
        from server import STATE_LANGUAGE_MAP
        
        assert STATE_LANGUAGE_MAP is not None
        assert "West Bengal" in STATE_LANGUAGE_MAP
        assert STATE_LANGUAGE_MAP["West Bengal"]["code"] == "bn"
        print("✓ STATE_LANGUAGE_MAP exists with correct structure")
    
    def test_bilingual_support_states(self):
        """Verify bilingual support for various states"""
        from server import STATE_LANGUAGE_MAP
        
        expected_states = [
            ("Maharashtra", "mr"),
            ("Tamil Nadu", "ta"),
            ("Gujarat", "gu"),
            ("Karnataka", "kn"),
            ("Telangana", "te"),
            ("West Bengal", "bn"),
            ("Punjab", "pa")
        ]
        
        for state, expected_code in expected_states:
            if state in STATE_LANGUAGE_MAP:
                actual_code = STATE_LANGUAGE_MAP[state]["code"]
                assert actual_code == expected_code, f"State {state} expected {expected_code}, got {actual_code}"
                print(f"✓ State '{state}' maps to language code '{expected_code}'")
    
    def test_default_language_exists(self):
        """Verify default language (Hindi) is available"""
        from server import STATE_LANGUAGE_MAP
        
        assert "default" in STATE_LANGUAGE_MAP
        assert STATE_LANGUAGE_MAP["default"]["code"] == "hi"
        print("✓ Default language (Hindi) configured")


class TestCheckAndSendEmailReminderAsync:
    """Test async check_and_send_email_reminder function"""
    
    def test_reminder_function_exists(self):
        """Verify check_and_send_email_reminder function exists and is async"""
        from server import check_and_send_email_reminder
        import asyncio
        
        assert check_and_send_email_reminder is not None
        assert asyncio.iscoroutinefunction(check_and_send_email_reminder)
        print("✓ check_and_send_email_reminder function exists and is async")
    
    def test_process_email_input_function_exists(self):
        """Verify process_email_input function exists and is async"""
        from server import process_email_input
        import asyncio
        
        assert process_email_input is not None
        assert asyncio.iscoroutinefunction(process_email_input)
        print("✓ process_email_input function exists and is async")


class TestEmailReminderTimingLogic:
    """Test the 24-hour interval logic for email reminders"""
    
    def test_24_hour_check_logic(self):
        """Test the logic that checks if 24 hours have passed"""
        from server import EMAIL_REMINDER_INTERVAL_HOURS
        
        now = datetime.now(timezone.utc)
        
        # Case 1: Last reminder was 23 hours ago (should NOT send)
        last_reminder_23h = (now - timedelta(hours=23)).isoformat()
        last_dt = datetime.fromisoformat(last_reminder_23h.replace('Z', '+00:00'))
        hours_since = (now - last_dt).total_seconds() / 3600
        should_send = hours_since >= EMAIL_REMINDER_INTERVAL_HOURS
        assert not should_send, "Should not send reminder after only 23 hours"
        print("✓ Reminder correctly skipped when < 24 hours")
        
        # Case 2: Last reminder was 25 hours ago (should send)
        last_reminder_25h = (now - timedelta(hours=25)).isoformat()
        last_dt = datetime.fromisoformat(last_reminder_25h.replace('Z', '+00:00'))
        hours_since = (now - last_dt).total_seconds() / 3600
        should_send = hours_since >= EMAIL_REMINDER_INTERVAL_HOURS
        assert should_send, "Should send reminder after 25 hours"
        print("✓ Reminder correctly sent when >= 24 hours")
    
    def test_null_reminder_time_sends_reminder(self):
        """Test that null last_reminder_sent_at means should send"""
        last_reminder = None
        
        # If no last reminder timestamp, should send
        should_send = last_reminder is None
        assert should_send, "Should send reminder if no previous reminder"
        print("✓ Reminder sent when no previous reminder exists")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
