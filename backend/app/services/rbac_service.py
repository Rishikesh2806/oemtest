"""
Role-Based Access Control (RBAC) Service
Manages custom roles and permissions for OEMLinker
"""

import os
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)

# MongoDB connection
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "oemlinker")

# ============== PERMISSION DEFINITIONS ==============
# All available permissions in the system organized by module

PERMISSIONS = {
    # User Management
    "users.view": {"label": "View Users", "module": "User Management", "description": "View list of all users"},
    "users.create": {"label": "Create Users", "module": "User Management", "description": "Create new user accounts"},
    "users.edit": {"label": "Edit Users", "module": "User Management", "description": "Edit user details"},
    "users.delete": {"label": "Delete Users", "module": "User Management", "description": "Delete user accounts"},
    "users.assign_roles": {"label": "Assign Roles", "module": "User Management", "description": "Assign roles to users"},
    
    # Vendor Management
    "vendors.view": {"label": "View Vendors", "module": "Vendor Management", "description": "View vendor profiles"},
    "vendors.approve": {"label": "Approve Vendors", "module": "Vendor Management", "description": "Approve vendor applications"},
    "vendors.edit": {"label": "Edit Vendors", "module": "Vendor Management", "description": "Edit vendor profiles"},
    "vendors.delete": {"label": "Delete Vendors", "module": "Vendor Management", "description": "Delete vendor accounts"},
    "vendors.verify": {"label": "Verify Vendors", "module": "Vendor Management", "description": "Verify vendor documents"},
    "vendors.search_machines": {"label": "Search by Machines", "module": "Vendor Management", "description": "Search vendors by machine capabilities"},
    
    # Machine Management
    "machines.view": {"label": "View Machines", "module": "Machine Management", "description": "View vendor machines"},
    "machines.create": {"label": "Add Machines", "module": "Machine Management", "description": "Add machines to vendor profiles"},
    "machines.edit": {"label": "Edit Machines", "module": "Machine Management", "description": "Edit machine details"},
    "machines.delete": {"label": "Delete Machines", "module": "Machine Management", "description": "Delete machines from vendor profiles"},
    "machines.manage_images": {"label": "Manage Machine Images", "module": "Machine Management", "description": "Upload and delete machine images"},
    
    # Buyer Management
    "buyers.view": {"label": "View Buyers", "module": "Buyer Management", "description": "View buyer profiles"},
    "buyers.edit": {"label": "Edit Buyers", "module": "Buyer Management", "description": "Edit buyer profiles"},
    "buyers.delete": {"label": "Delete Buyers", "module": "Buyer Management", "description": "Delete buyer accounts"},
    
    # RFQ Management
    "rfqs.view": {"label": "View RFQs", "module": "RFQ Management", "description": "View all RFQs"},
    "rfqs.create": {"label": "Create RFQs", "module": "RFQ Management", "description": "Create new RFQs"},
    "rfqs.edit": {"label": "Edit RFQs", "module": "RFQ Management", "description": "Edit RFQ details"},
    "rfqs.delete": {"label": "Delete RFQs", "module": "RFQ Management", "description": "Delete RFQs"},
    "rfqs.analyze": {"label": "Analyze RFQs", "module": "RFQ Management", "description": "Run AI analysis on RFQs"},
    "rfqs.match_vendors": {"label": "Match Vendors", "module": "RFQ Management", "description": "Find matching vendors for RFQs"},
    
    # Quote Management
    "quotes.view": {"label": "View Quotes", "module": "Quote Management", "description": "View all quotes"},
    "quotes.create": {"label": "Create Quotes", "module": "Quote Management", "description": "Submit quotes"},
    "quotes.edit": {"label": "Edit Quotes", "module": "Quote Management", "description": "Edit quote details"},
    "quotes.approve": {"label": "Approve Quotes", "module": "Quote Management", "description": "Approve/reject quotes"},
    "quotes.negotiate": {"label": "Negotiate Quotes", "module": "Quote Management", "description": "Handle quote negotiations"},
    
    # Order Management
    "orders.view": {"label": "View Orders", "module": "Order Management", "description": "View all orders"},
    "orders.create": {"label": "Create Orders", "module": "Order Management", "description": "Create purchase orders"},
    "orders.edit": {"label": "Edit Orders", "module": "Order Management", "description": "Edit order details"},
    "orders.cancel": {"label": "Cancel Orders", "module": "Order Management", "description": "Cancel orders"},
    "orders.update_status": {"label": "Update Order Status", "module": "Order Management", "description": "Update order/delivery status"},
    
    # Payments & Finance
    "payments.view": {"label": "View Payments", "module": "Payments & Finance", "description": "View payment transactions"},
    "payments.process": {"label": "Process Payments", "module": "Payments & Finance", "description": "Process payment releases"},
    "payments.refund": {"label": "Issue Refunds", "module": "Payments & Finance", "description": "Process refunds"},
    "payments.reports": {"label": "Financial Reports", "module": "Payments & Finance", "description": "View financial reports"},
    
    # WhatsApp Management
    "whatsapp.view_messages": {"label": "View Messages", "module": "WhatsApp", "description": "View WhatsApp conversations"},
    "whatsapp.send_messages": {"label": "Send Messages", "module": "WhatsApp", "description": "Send WhatsApp messages"},
    "whatsapp.send_templates": {"label": "Send Templates", "module": "WhatsApp", "description": "Send template messages"},
    "whatsapp.view_logs": {"label": "View Logs", "module": "WhatsApp", "description": "View WhatsApp logs and analytics"},
    
    # Analytics & Reports
    "analytics.view_dashboard": {"label": "View Dashboard", "module": "Analytics", "description": "View analytics dashboard"},
    "analytics.export_reports": {"label": "Export Reports", "module": "Analytics", "description": "Export data and reports"},
    "analytics.view_financials": {"label": "View Financials", "module": "Analytics", "description": "View financial analytics"},
    
    # Disputes
    "disputes.view": {"label": "View Disputes", "module": "Disputes", "description": "View dispute cases"},
    "disputes.manage": {"label": "Manage Disputes", "module": "Disputes", "description": "Handle and resolve disputes"},
    "disputes.escalate": {"label": "Escalate Disputes", "module": "Disputes", "description": "Escalate dispute cases"},
    
    # System Administration
    "admin.roles": {"label": "Manage Roles", "module": "System Admin", "description": "Create and manage custom roles"},
    "admin.settings": {"label": "System Settings", "module": "System Admin", "description": "Manage system settings"},
    "admin.file_manager": {"label": "File Manager", "module": "System Admin", "description": "Access file manager"},
    "admin.audit_logs": {"label": "Audit Logs", "module": "System Admin", "description": "View audit/activity logs"},
}

# Default system roles (cannot be deleted)
DEFAULT_ROLES = {
    "super_admin": {
        "name": "Super Admin",
        "description": "Full system access with all permissions",
        "permissions": list(PERMISSIONS.keys()),  # All permissions
        "is_system": True,
        "color": "#dc2626"  # Red
    },
    "admin": {
        "name": "Admin",
        "description": "Administrative access to manage the platform",
        "permissions": [
            "users.view", "users.create", "users.edit", "users.assign_roles",
            "vendors.view", "vendors.approve", "vendors.edit", "vendors.verify", "vendors.search_machines",
            "machines.view", "machines.create", "machines.edit", "machines.delete", "machines.manage_images",
            "buyers.view", "buyers.edit",
            "rfqs.view", "rfqs.edit", "rfqs.analyze", "rfqs.match_vendors",
            "quotes.view", "quotes.approve", "quotes.negotiate",
            "orders.view", "orders.edit", "orders.update_status",
            "payments.view", "payments.reports",
            "whatsapp.view_messages", "whatsapp.send_messages", "whatsapp.send_templates", "whatsapp.view_logs",
            "analytics.view_dashboard", "analytics.export_reports", "analytics.view_financials",
            "disputes.view", "disputes.manage",
            "admin.file_manager", "admin.audit_logs"
        ],
        "is_system": True,
        "color": "#2563eb"  # Blue
    },
    "sales_manager": {
        "name": "Sales Manager",
        "description": "Manage RFQs, quotes, and vendor relationships",
        "permissions": [
            "vendors.view", "vendors.search_machines", "buyers.view",
            "machines.view",
            "rfqs.view", "rfqs.create", "rfqs.edit", "rfqs.analyze", "rfqs.match_vendors",
            "quotes.view", "quotes.approve", "quotes.negotiate",
            "orders.view", "orders.create",
            "analytics.view_dashboard"
        ],
        "is_system": True,
        "color": "#16a34a"  # Green
    },
    "vendor_manager": {
        "name": "Vendor Manager",
        "description": "Manage vendor profiles and machines",
        "permissions": [
            "vendors.view", "vendors.edit", "vendors.verify", "vendors.search_machines",
            "machines.view", "machines.create", "machines.edit", "machines.delete", "machines.manage_images",
            "analytics.view_dashboard"
        ],
        "is_system": True,
        "color": "#f59e0b"  # Amber
    },
    "support_agent": {
        "name": "Support Agent",
        "description": "Handle customer support and disputes",
        "permissions": [
            "users.view", "vendors.view", "buyers.view",
            "rfqs.view", "quotes.view", "orders.view",
            "whatsapp.view_messages", "whatsapp.send_messages",
            "disputes.view", "disputes.manage"
        ],
        "is_system": True,
        "color": "#9333ea"  # Purple
    },
    "finance_admin": {
        "name": "Finance Admin",
        "description": "Manage payments and financial operations",
        "permissions": [
            "payments.view", "payments.process", "payments.refund", "payments.reports",
            "orders.view",
            "analytics.view_dashboard", "analytics.view_financials", "analytics.export_reports"
        ],
        "is_system": True,
        "color": "#ca8a04"  # Yellow
    },
    "vendor": {
        "name": "Vendor",
        "description": "Vendor user with access to their own data",
        "permissions": [
            "rfqs.view",  # Only matched RFQs
            "quotes.view", "quotes.create", "quotes.edit",
            "orders.view", "orders.update_status",
            "disputes.view"
        ],
        "is_system": True,
        "is_base_role": True,  # Base role for vendor users
        "color": "#0891b2"  # Cyan
    },
    "buyer": {
        "name": "Buyer",
        "description": "Buyer user with access to their own data",
        "permissions": [
            "rfqs.view", "rfqs.create", "rfqs.edit", "rfqs.analyze", "rfqs.match_vendors",
            "quotes.view", "quotes.approve", "quotes.negotiate",
            "orders.view", "orders.create",
            "disputes.view"
        ],
        "is_system": True,
        "is_base_role": True,  # Base role for buyer users
        "color": "#0d9488"  # Teal
    },
    "supervisor": {
        "name": "Supervisor",
        "description": "Oversee team operations and performance",
        "permissions": [
            "users.view",
            "vendors.view",
            "rfqs.view",
            "quotes.view",
            "orders.view",
            "whatsapp.view_messages",
            "disputes.view",
            "analytics.view_dashboard"
        ],
        "is_system": True,
        "color": "#3b82f6"  # Blue
    }
}


class RBACService:
    """Role-Based Access Control Service"""
    
    _instance = None
    _db = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def _get_db(self):
        """Get MongoDB database connection"""
        if self._db is None:
            client = AsyncIOMotorClient(MONGO_URL)
            self._db = client[DB_NAME]
            # Create indexes
            await self._db.roles.create_index("role_id", unique=True)
            await self._db.roles.create_index("name")
        return self._db
    
    async def initialize_default_roles(self):
        """Initialize default system roles if they don't exist"""
        if self._initialized:
            return
        
        db = await self._get_db()
        
        for role_id, role_data in DEFAULT_ROLES.items():
            existing = await db.roles.find_one({"role_id": role_id})
            if not existing:
                await db.roles.insert_one({
                    "role_id": role_id,
                    **role_data,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                })
                logger.info(f"Created default role: {role_id}")
        
        self._initialized = True
    
    def get_all_permissions(self) -> Dict[str, Any]:
        """Get all available permissions grouped by module"""
        modules = {}
        for perm_id, perm_data in PERMISSIONS.items():
            module = perm_data["module"]
            if module not in modules:
                modules[module] = []
            modules[module].append({
                "id": perm_id,
                "label": perm_data["label"],
                "description": perm_data["description"]
            })
        return modules
    
    def get_permissions_list(self) -> List[Dict[str, Any]]:
        """Get flat list of all permissions"""
        return [
            {"id": perm_id, **perm_data}
            for perm_id, perm_data in PERMISSIONS.items()
        ]
    
    async def get_role(self, role_id: str) -> Optional[Dict[str, Any]]:
        """Get a role by ID"""
        db = await self._get_db()
        role = await db.roles.find_one({"role_id": role_id}, {"_id": 0})
        return role
    
    async def get_all_roles(self, include_base_roles: bool = True) -> List[Dict[str, Any]]:
        """Get all roles"""
        db = await self._get_db()
        await self.initialize_default_roles()
        
        query = {}
        if not include_base_roles:
            query["is_base_role"] = {"$ne": True}
        
        cursor = db.roles.find(query, {"_id": 0}).sort("name", 1)
        roles = await cursor.to_list(length=100)
        return roles
    
    async def create_role(
        self,
        name: str,
        description: str,
        permissions: List[str],
        color: str = "#6b7280",
        created_by: str = None
    ) -> Dict[str, Any]:
        """Create a new custom role"""
        db = await self._get_db()
        
        # Generate role_id from name
        role_id = name.lower().replace(" ", "_").replace("-", "_")
        
        # Check if role already exists
        existing = await db.roles.find_one({"$or": [{"role_id": role_id}, {"name": name}]})
        if existing:
            raise ValueError(f"Role with name '{name}' already exists")
        
        # Validate permissions
        valid_permissions = [p for p in permissions if p in PERMISSIONS]
        
        role = {
            "role_id": role_id,
            "name": name,
            "description": description,
            "permissions": valid_permissions,
            "color": color,
            "is_system": False,
            "is_base_role": False,
            "created_by": created_by,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.roles.insert_one(role)
        role.pop("_id", None)
        
        logger.info(f"Created custom role: {role_id}")
        return role
    
    async def update_role(
        self,
        role_id: str,
        name: str = None,
        description: str = None,
        permissions: List[str] = None,
        color: str = None,
        updated_by: str = None
    ) -> Dict[str, Any]:
        """Update an existing role"""
        db = await self._get_db()
        
        # Check if role exists
        existing = await db.roles.find_one({"role_id": role_id})
        if not existing:
            raise ValueError(f"Role '{role_id}' not found")
        
        # System roles have limited editable fields
        is_system = existing.get("is_system", False)
        
        update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
        
        if name and not is_system:
            update_data["name"] = name
        if description:
            update_data["description"] = description
        if permissions is not None:
            # Validate permissions
            valid_permissions = [p for p in permissions if p in PERMISSIONS]
            update_data["permissions"] = valid_permissions
        if color:
            update_data["color"] = color
        if updated_by:
            update_data["updated_by"] = updated_by
        
        await db.roles.update_one({"role_id": role_id}, {"$set": update_data})
        
        updated_role = await db.roles.find_one({"role_id": role_id}, {"_id": 0})
        logger.info(f"Updated role: {role_id}")
        return updated_role
    
    async def delete_role(self, role_id: str) -> bool:
        """Delete a custom role (system roles cannot be deleted)"""
        db = await self._get_db()
        
        # Check if role exists and is not a system role
        existing = await db.roles.find_one({"role_id": role_id})
        if not existing:
            raise ValueError(f"Role '{role_id}' not found")
        
        if existing.get("is_system", False):
            raise ValueError("System roles cannot be deleted")
        
        # Check if any users are assigned to this role
        users_with_role = await db.users.count_documents({"custom_role": role_id})
        if users_with_role > 0:
            raise ValueError(f"Cannot delete role: {users_with_role} users are assigned to this role")
        
        await db.roles.delete_one({"role_id": role_id})
        logger.info(f"Deleted role: {role_id}")
        return True
    
    async def assign_role_to_user(
        self,
        user_id: str,
        role_id: str,
        assigned_by: str = None
    ) -> bool:
        """Assign a custom role to a user"""
        db = await self._get_db()
        
        # Verify role exists
        role = await db.roles.find_one({"role_id": role_id})
        if not role:
            raise ValueError(f"Role '{role_id}' not found")
        
        # Update user
        result = await db.users.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "custom_role": role_id,
                    "custom_role_assigned_at": datetime.now(timezone.utc).isoformat(),
                    "custom_role_assigned_by": assigned_by
                }
            }
        )
        
        if result.matched_count == 0:
            raise ValueError(f"User '{user_id}' not found")
        
        logger.info(f"Assigned role '{role_id}' to user '{user_id}'")
        return True
    
    async def remove_role_from_user(self, user_id: str) -> bool:
        """Remove custom role from a user"""
        db = await self._get_db()
        
        result = await db.users.update_one(
            {"user_id": user_id},
            {
                "$unset": {
                    "custom_role": "",
                    "custom_role_assigned_at": "",
                    "custom_role_assigned_by": ""
                }
            }
        )
        
        if result.matched_count == 0:
            raise ValueError(f"User '{user_id}' not found")
        
        logger.info(f"Removed custom role from user '{user_id}'")
        return True
    
    async def get_user_permissions(self, user_id: str) -> List[str]:
        """Get all permissions for a user based on their roles"""
        db = await self._get_db()
        
        user = await db.users.find_one({"user_id": user_id}, {"_id": 0, "role": 1, "custom_role": 1})
        if not user:
            return []
        
        permissions = set()
        
        # Get base role permissions
        base_role = user.get("role", "buyer")
        base_role_doc = await db.roles.find_one({"role_id": base_role})
        if base_role_doc:
            permissions.update(base_role_doc.get("permissions", []))
        
        # Get custom role permissions (additive)
        custom_role = user.get("custom_role")
        if custom_role:
            custom_role_doc = await db.roles.find_one({"role_id": custom_role})
            if custom_role_doc:
                permissions.update(custom_role_doc.get("permissions", []))
        
        return list(permissions)
    
    async def check_permission(self, user_id: str, permission: str) -> bool:
        """Check if a user has a specific permission"""
        permissions = await self.get_user_permissions(user_id)
        return permission in permissions
    
    async def get_users_by_role(self, role_id: str) -> List[Dict[str, Any]]:
        """Get all users assigned to a role"""
        db = await self._get_db()
        
        # Users can have the role as base role or custom role
        cursor = db.users.find(
            {"$or": [{"role": role_id}, {"custom_role": role_id}]},
            {"_id": 0, "user_id": 1, "name": 1, "email": 1, "role": 1, "custom_role": 1}
        )
        users = await cursor.to_list(length=100)
        return users


# Singleton instance
rbac_service = RBACService()
