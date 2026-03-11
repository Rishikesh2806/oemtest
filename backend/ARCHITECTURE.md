# OEMLinker Backend Architecture

## Directory Structure

```
/app/backend/
├── app/
│   ├── __init__.py
│   ├── config.py              # Environment variables and settings
│   ├── database.py            # MongoDB connection
│   ├── dependencies.py        # FastAPI dependencies (auth, etc.)
│   │
│   ├── core/                  # Core utilities
│   │   ├── __init__.py
│   │   ├── auth.py            # JWT, password hashing
│   │   └── security.py        # Rate limiting, OTP, validation
│   │
│   ├── models/                # Pydantic models
│   │   ├── __init__.py
│   │   ├── base.py            # Common models (UserRole, Status enums)
│   │   ├── user.py            # User-related models
│   │   ├── vendor.py          # Vendor models
│   │   ├── machine.py         # Machine models
│   │   ├── rfq.py             # RFQ models
│   │   ├── quote.py           # Quote models
│   │   ├── order.py           # Order models
│   │   └── notification.py    # Notification models
│   │
│   ├── routes/                # API route handlers
│   │   ├── __init__.py
│   │   ├── auth.py            # Authentication routes
│   │   ├── users.py           # User profile routes
│   │   ├── vendors.py         # Vendor routes
│   │   ├── machines.py        # Machine routes
│   │   ├── rfqs.py            # RFQ routes
│   │   ├── quotes.py          # Quote routes
│   │   ├── orders.py          # Order routes
│   │   ├── admin.py           # Admin routes
│   │   ├── notifications.py   # Notification routes
│   │   ├── whatsapp.py        # WhatsApp integration routes
│   │   └── voice.py           # Voice agent routes
│   │
│   ├── services/              # Business logic
│   │   ├── __init__.py
│   │   ├── user_service.py    # User operations
│   │   ├── vendor_service.py  # Vendor operations
│   │   ├── notification_service.py
│   │   ├── email_service.py   # Email sending
│   │   ├── whatsapp_service.py # WhatsApp API
│   │   └── matching_service.py # RFQ-Vendor matching
│   │
│   └── utils/                 # Helper utilities
│       ├── __init__.py
│       └── helpers.py
│
├── server.py                  # Main FastAPI application (legacy monolith)
├── requirements.txt
├── .env
└── uploads/                   # File uploads directory
```

## Refactoring Status

### Completed ✅
- [x] Core security utilities (`app/core/security.py`)
- [x] Authentication utilities (`app/core/auth.py`)
- [x] Base models (`app/models/base.py`)
- [x] Vendor models (`app/models/vendor.py`)
- [x] Dependencies (`app/dependencies.py`)
- [x] User service (`app/services/user_service.py`)
- [x] Vendor service (`app/services/vendor_service.py`)
- [x] Notification service (`app/services/notification_service.py`)

### In Progress 🔄
- [ ] Auth routes extraction
- [ ] Vendor routes extraction
- [ ] Admin routes extraction

### Pending 📋
- [ ] Machine routes
- [ ] RFQ routes
- [ ] Quote routes
- [ ] Order routes
- [ ] WhatsApp bot logic
- [ ] Voice agent routes
- [ ] Dispute routes

## Migration Strategy

The refactoring follows a gradual migration approach:

1. **Create modular structure** - New code goes into proper modules
2. **Import from modules** - `server.py` imports from new modules
3. **Test thoroughly** - Each migration step is tested
4. **Remove duplicates** - Once stable, remove from `server.py`

## Usage

### Importing Models
```python
from app.models import UserRole, UserResponse, VendorProfile
```

### Importing Services
```python
from app.services import get_user_by_id, create_vendor_profile
```

### Importing Core Utilities
```python
from app.core import hash_password, validate_password_strength
```

### Using Dependencies
```python
from app.dependencies import get_current_user, require_admin

@router.get("/protected")
async def protected_route(user: dict = Depends(get_current_user)):
    return {"user": user}
```

## Key Files

- `server.py` - Main monolithic file (13,400+ lines) - being gradually refactored
- `app/config.py` - All environment variables and settings
- `app/database.py` - MongoDB connection singleton
- `app/dependencies.py` - FastAPI dependency injection

## API Sections in server.py

| Section | Lines | Status |
|---------|-------|--------|
| Models | 604-1130 | Partially extracted |
| Auth Routes | 1233-1950 | Pending |
| User Routes | 2200-2260 | Pending |
| Vendor Routes | 2260-2450 | Pending |
| GSTIN Routes | 2460-2615 | Pending |
| Machine Routes | 2700-3300 | Pending |
| RFQ Routes | 3300-4500 | Pending |
| Quote Routes | 4500-5500 | Pending |
| Order Routes | 5500-6500 | Pending |
| Admin Routes | 6500-8100 | Pending |
| WhatsApp Admin | 8143-8850 | Pending |
| Disputes | 8853-9340 | Pending |
| Notifications | 9348-9400 | Pending |
| Voice Agent | 9402-9630 | Pending |
| WhatsApp Bot | 9629-13440 | Pending |
