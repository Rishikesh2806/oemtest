"""
Phone number normalization and duplicate detection utilities for OEMLinker.
All phone numbers stored in E.164 format: +91XXXXXXXXXX
"""
import re


def normalize_phone(phone: str, default_country: str = "IN") -> str:
    """
    Normalize phone number to E.164 format.
    
    Examples:
        9831379959      → +919831379959
        09831379959     → +919831379959
        919831379959    → +919831379959
        +919831379959   → +919831379959
        98313 79959     → +919831379959
        +91 98313-79959 → +919831379959
    """
    if not phone or not phone.strip():
        return ""

    # Remove all spaces, dashes, brackets, dots
    cleaned = re.sub(r'[\s\-\(\)\.]', '', phone.strip())

    # Remove leading zeros
    cleaned = cleaned.lstrip('0')

    if not cleaned:
        return ""

    # Add country code if missing
    if not cleaned.startswith('+'):
        if cleaned.startswith('91') and len(cleaned) == 12:
            cleaned = '+' + cleaned
        elif len(cleaned) == 10 and cleaned.isdigit():
            cleaned = '+91' + cleaned
        else:
            cleaned = '+' + cleaned

    return cleaned


def is_valid_phone(phone: str) -> bool:
    """Check if a normalized phone number is valid (basic format check)."""
    if not phone:
        return False
    normalized = normalize_phone(phone)
    # E.164: + followed by 10-15 digits
    return bool(re.match(r'^\+\d{10,15}$', normalized))
