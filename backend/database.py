from pymongo import ASCENDING, DESCENDING, MongoClient


def connect(uri: str, database_name: str):
    client = MongoClient(uri, serverSelectionTimeoutMS=3000, connectTimeoutMS=3000)
    client.admin.command("ping")
    db = client[database_name]
    db.users.create_index([("email", ASCENDING)], unique=True)
    db.businesses.create_index([("_id", ASCENDING)])
    db.memberships.create_index([("business_id", ASCENDING), ("user_id", ASCENDING)], unique=True)
    db.memberships.create_index([("user_id", ASCENDING), ("business_id", ASCENDING)])
    db.customers.create_index([("business_id", ASCENDING), ("archived", ASCENDING), ("name", ASCENDING)])
    db.transactions.create_index([("business_id", ASCENDING), ("date", DESCENDING), ("_id", DESCENDING)])
    db.transactions.create_index([("business_id", ASCENDING), ("customer_id", ASCENDING), ("date", DESCENDING)])
    db.transactions.create_index([("business_id", ASCENDING), ("idempotency_key", ASCENDING)], unique=True,
                                 partialFilterExpression={"idempotency_key": {"$exists": True}})
    db.audit_events.create_index([("business_id", ASCENDING), ("created_at", DESCENDING)])
    db.sessions.create_index([("expires_at", ASCENDING)], expireAfterSeconds=0)
    db.sessions.create_index([("token_hash", ASCENDING)], unique=True)
    return client, db
