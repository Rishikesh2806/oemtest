"""
Migration script: Normalize vendor approval fields.
Sets both `is_approved: True` and `status: "approved"` for all vendors
that have EITHER field set, ensuring consistency across the codebase.

Run once on production: python3 migrate_vendor_approval.py
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient


async def migrate():
    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME", "oemlinker")
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    # 1. Find vendors that have EITHER approval indicator but not both
    needs_fix = await db.vendors.find(
        {"$or": [
            {"is_approved": True, "status": {"$ne": "approved"}},
            {"status": "approved", "is_approved": {"$ne": True}},
        ]},
        {"_id": 0, "vendor_id": 1, "company_name": 1, "is_approved": 1, "status": 1},
    ).to_list(500)

    print(f"Found {len(needs_fix)} vendors needing normalization")
    for v in needs_fix:
        print(f"  {v.get('company_name', '?')} (vendor_id={v.get('vendor_id')}): "
              f"is_approved={v.get('is_approved')}, status={v.get('status')}")

    # 2. Bulk update: set both fields for any vendor with either
    result = await db.vendors.update_many(
        {"$or": [{"is_approved": True}, {"status": "approved"}]},
        {"$set": {"is_approved": True, "status": "approved"}},
    )
    print(f"\nNormalized {result.modified_count} vendors (matched {result.matched_count})")

    # 3. Verify
    total = await db.vendors.count_documents({})
    approved = await db.vendors.count_documents({"is_approved": True, "status": "approved"})
    pending = total - approved
    print(f"\nPost-migration: {total} total, {approved} approved, {pending} pending")

    client.close()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(migrate())
