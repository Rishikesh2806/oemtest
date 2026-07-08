import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = "mongodb+srv://oemlinker_app:Rishikesh%402806_%2B@cluster0.k2sudev.mongodb.net/oemlinker?appName=Cluster0"

async def create_indexes():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client["oemlinker"]

    # rfqs
    await db.rfqs.create_index("rfq_id", unique=True)
    await db.rfqs.create_index("buyer_id")
    await db.rfqs.create_index([("buyer_id", 1), ("created_at", -1)])
    print("rfqs done")

    # orders
    await db.orders.create_index("order_id", unique=True)
    await db.orders.create_index("buyer_id")
    await db.orders.create_index("vendor_id")
    print("orders done")

    # quotes
    await db.quotes.create_index("quote_id", unique=True)
    await db.quotes.create_index("rfq_id")
    await db.quotes.create_index("vendor_id")
    await db.quotes.create_index([("rfq_id", 1), ("vendor_id", 1)])
    print("quotes done")

    # users
    await db.users.create_index("email")
    await db.users.create_index("user_id", unique=True)
    print("users done")

    client.close()
    print("All indexes created successfully.")

asyncio.run(create_indexes())