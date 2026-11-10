import logging
import hashlib
import json
import secrets
from contextlib import asynccontextmanager
from datetime import date, datetime, time, timedelta, timezone

from bson import ObjectId
from fastapi import FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pymongo.errors import DuplicateKeyError, PyMongoError
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern

from .config import get_settings
from .database import connect
from .schemas import BusinessIn, CustomerIn, LoginIn, RegisterIn, RoleIn, TransactionIn
from .security import check_login_rate, hash_token, issue_session, password_hasher, require_session, utcnow

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("kileger")
settings = get_settings()
client = None
db = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global client, db
    local_client, local_db = connect(settings.mongodb_uri, settings.database)
    client, db = local_client, local_db
    try:
        yield
    finally:
        local_client.close()


app = FastAPI(title="KiLedger API", version="1.0.0", lifespan=lifespan, docs_url="/api/v1/docs", openapi_url="/api/v1/openapi.json")
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.hosts)
app.add_middleware(CORSMiddleware, allow_origins=settings.origins, allow_credentials=True,
                   allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
                   allow_headers=["Content-Type", "X-CSRF-Token", "Idempotency-Key"])


def clean(doc: dict | None) -> dict | None:
    if doc is None:
        return None
    result = {key: value for key, value in doc.items() if not key.startswith("_") and key not in {"password_hash", "token_hash", "csrf_hash"}}
    if "_id" in doc:
        result["id"] = str(doc["_id"])
    return result


def oid(value: str) -> ObjectId:
    if not ObjectId.is_valid(value):
        raise HTTPException(404, "Record not found.")
    return ObjectId(value)


def auth(request: Request, response: Response, write: bool = True) -> dict:
    if db is None:
        raise HTTPException(503, "Database is not available.")
    return require_session(request, response, db, settings, csrf_required=write)


def audit(actor: dict, action: str, entity: str, entity_id: str, **details):
    db.audit_events.insert_one({"business_id": actor["business_id"], "actor_id": actor["user_id"], "action": action,
                                "entity": entity, "entity_id": entity_id, "details": details, "created_at": utcnow()})


@app.exception_handler(DuplicateKeyError)
async def duplicate_handler(_request: Request, _exc: DuplicateKeyError):
    return Response(content='{"detail":"A record with these details already exists."}', status_code=409, media_type="application/json")


@app.exception_handler(PyMongoError)
async def database_handler(_request: Request, exc: PyMongoError):
    logger.error("Database operation failed: %s", type(exc).__name__)
    return Response(content='{"detail":"Database operation failed. Check the service configuration and retry."}', status_code=503, media_type="application/json")


@app.get("/api/v1/health")
def health():
    return {"status": "ok" if db is not None else "starting"}


@app.post("/api/v1/auth/register", status_code=201)
def register(payload: RegisterIn, request: Request, response: Response):
    check_login_rate(request, settings)
    user_id, business_id = str(ObjectId()), str(ObjectId())
    now = utcnow()
    db.users.insert_one({"_id": user_id, "email": str(payload.email).lower(), "name": payload.name,
                         "password_hash": password_hasher.hash(payload.password), "disabled": False, "created_at": now})
    db.businesses.insert_one({"_id": business_id, "name": payload.business_name, "currency": "INR", "created_at": now, "updated_at": now})
    db.memberships.insert_one({"business_id": business_id, "user_id": user_id, "role": "owner", "created_at": now})
    audit({"business_id": business_id, "user_id": user_id}, "user.register", "business", business_id)
    csrf = issue_session(db, response, user_id, business_id, settings)
    return {"user": {"id": user_id, "email": str(payload.email).lower(), "name": payload.name},
            "business": {"id": business_id, "name": payload.business_name, "currency": "INR"}, "csrf_token": csrf}


@app.post("/api/v1/auth/login")
def login(payload: LoginIn, request: Request, response: Response):
    check_login_rate(request, settings)
    user = db.users.find_one({"email": str(payload.email).lower()})
    if not user or user.get("disabled") or not password_hasher.verify(payload.password, user["password_hash"]):
        raise HTTPException(401, "Email or password is incorrect.")
    membership = db.memberships.find_one({"user_id": user["_id"], "role": "owner"}) or db.memberships.find_one({"user_id": user["_id"]})
    business = db.businesses.find_one({"_id": membership["business_id"]}) if membership else None
    if not membership or not business:
        raise HTTPException(403, "No active business workspace is available.")
    csrf = issue_session(db, response, user["_id"], business["_id"], settings)
    return {"user": {"id": user["_id"], "email": user["email"], "name": user["name"]},
            "business": clean(business), "csrf_token": csrf}


@app.get("/api/v1/auth/me")
def me(request: Request, response: Response):
    actor = auth(request, response, write=False)
    business = db.businesses.find_one({"_id": actor["business_id"]})
    csrf = secrets.token_urlsafe(24)
    db.sessions.update_one({"token_hash": actor["session_hash"]}, {"$set": {"csrf_hash": hash_token(csrf)}})
    return {"user": {"id": actor["user_id"], "email": actor["email"], "name": actor["name"]},
            "business": clean(business), "role": actor["role"], "csrf_token": csrf}


@app.post("/api/v1/auth/logout", status_code=204)
def logout(request: Request, response: Response):
    actor = auth(request, response)
    db.sessions.delete_one({"token_hash": actor["session_hash"]})
    response.delete_cookie(settings.session_cookie, path="/")
    return Response(status_code=204)


@app.post("/api/v1/businesses", status_code=201)
def create_business(payload: BusinessIn, request: Request, response: Response):
    actor = auth(request, response)
    business_id = str(ObjectId())
    now = utcnow()
    db.businesses.insert_one({"_id": business_id, "name": payload.name, "currency": "INR", "created_at": now, "updated_at": now})
    db.memberships.insert_one({"business_id": business_id, "user_id": actor["user_id"], "role": "owner", "created_at": now})
    db.sessions.update_one({"token_hash": actor["session_hash"]}, {"$set": {"business_id": business_id}})
    audit({**actor, "business_id": business_id}, "business.create", "business", business_id)
    return clean(db.businesses.find_one({"_id": business_id}))


@app.get("/api/v1/businesses/members")
def list_members(request: Request, response: Response):
    actor = auth(request, response, write=False)
    rows = db.memberships.find({"business_id": actor["business_id"]})
    return [{"user_id": row["user_id"], "role": row["role"], "email": (db.users.find_one({"_id": row["user_id"]}) or {}).get("email")} for row in rows]


@app.patch("/api/v1/businesses/members/{user_id}")
def set_member_role(user_id: str, payload: RoleIn, request: Request, response: Response):
    actor = auth(request, response)
    if actor["role"] != "owner":
        raise HTTPException(403, "Only the business owner can change roles.")
    result = db.memberships.update_one({"business_id": actor["business_id"], "user_id": user_id, "role": {"$ne": "owner"}}, {"$set": {"role": payload.role}})
    if result.matched_count == 0:
        raise HTTPException(404, "Business member not found.")
    audit(actor, "membership.role_update", "membership", user_id, role=payload.role)
    return {"user_id": user_id, "role": payload.role}


@app.get("/api/v1/customers")
def customers(request: Request, response: Response, page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), q: str = ""):
    actor = auth(request, response, write=False)
    query = {"business_id": actor["business_id"], "archived": {"$ne": True}}
    if q.strip():
        query["name"] = {"$regex": __import__("re").escape(q.strip()), "$options": "i"}
    total = db.customers.count_documents(query)
    docs = db.customers.find(query).sort("name", 1).skip((page - 1) * page_size).limit(page_size)
    return {"items": [clean(doc) for doc in docs], "page": page, "page_size": page_size, "total": total}


@app.post("/api/v1/customers", status_code=201)
def create_customer(payload: CustomerIn, request: Request, response: Response):
    actor = auth(request, response)
    now = utcnow()
    doc = {"_id": str(ObjectId()), **payload.model_dump(), "email": str(payload.email).lower() if payload.email else None,
           "business_id": actor["business_id"], "archived": False, "created_at": now, "updated_at": now, "created_by": actor["user_id"]}
    db.customers.insert_one(doc)
    audit(actor, "customer.create", "customer", doc["_id"])
    return clean(doc)


@app.get("/api/v1/customers/{customer_id}")
def get_customer(customer_id: str, request: Request, response: Response):
    actor = auth(request, response, write=False)
    doc = db.customers.find_one({"_id": customer_id, "business_id": actor["business_id"], "archived": {"$ne": True}})
    if not doc:
        raise HTTPException(404, "Customer not found.")
    return clean(doc)


@app.patch("/api/v1/customers/{customer_id}")
def update_customer(customer_id: str, payload: CustomerIn, request: Request, response: Response):
    actor = auth(request, response)
    update = payload.model_dump()
    update["email"] = str(payload.email).lower() if payload.email else None
    update["updated_at"] = utcnow()
    result = db.customers.update_one({"_id": customer_id, "business_id": actor["business_id"], "archived": {"$ne": True}}, {"$set": update})
    if not result.matched_count:
        raise HTTPException(404, "Customer not found.")
    audit(actor, "customer.update", "customer", customer_id)
    return clean(db.customers.find_one({"_id": customer_id, "business_id": actor["business_id"]}))


@app.delete("/api/v1/customers/{customer_id}", status_code=204)
def archive_customer(customer_id: str, request: Request, response: Response):
    actor = auth(request, response)
    result = db.customers.update_one({"_id": customer_id, "business_id": actor["business_id"], "archived": {"$ne": True}}, {"$set": {"archived": True, "updated_at": utcnow()}})
    if not result.matched_count:
        raise HTTPException(404, "Customer not found.")
    audit(actor, "customer.archive", "customer", customer_id)
    return Response(status_code=204)


@app.post("/api/v1/transactions", status_code=201)
def create_transaction(payload: TransactionIn, request: Request, response: Response, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    actor = auth(request, response)
    if payload.type == "payment" and not payload.customer_id:
        raise HTTPException(422, "Payments must reference a customer.")
    if payload.on_credit and not payload.customer_id:
        raise HTTPException(422, "Credit sales must reference a customer.")
    if payload.customer_id and not db.customers.find_one({"_id": payload.customer_id, "business_id": actor["business_id"], "archived": {"$ne": True}}):
        raise HTTPException(422, "Customer does not belong to this business or is archived.")
    if idempotency_key and len(idempotency_key) > 100:
        raise HTTPException(422, "Idempotency key is too long.")
    serialized_payload = payload.model_dump(mode="json")
    request_hash = hashlib.sha256(json.dumps(serialized_payload, sort_keys=True).encode()).hexdigest()
    doc = {"_id": str(ObjectId()), **payload.model_dump(), "date": payload.date.isoformat(), "business_id": actor["business_id"],
           "amount_minor": int(payload.amount_minor), "created_at": utcnow(), "created_by": actor["user_id"]}
    if idempotency_key:
        doc["idempotency_key"] = idempotency_key
        doc["request_hash"] = request_hash
    try:
        with client.start_session() as session:
            with session.start_transaction(read_concern=ReadConcern("snapshot"), write_concern=WriteConcern("majority")):
                if idempotency_key:
                    prior = db.transactions.find_one({"business_id": actor["business_id"], "idempotency_key": idempotency_key}, session=session)
                    if prior:
                        if prior.get("request_hash") != request_hash:
                            raise HTTPException(409, "This idempotency key was already used for a different transaction.")
                        return clean(prior)
                db.transactions.insert_one(doc, session=session)
                db.audit_events.insert_one({"business_id": actor["business_id"], "actor_id": actor["user_id"], "action": "transaction.create",
                    "entity": "transaction", "entity_id": doc["_id"], "details": {"type": payload.type, "amount_minor": payload.amount_minor}, "created_at": utcnow()}, session=session)
    except PyMongoError as exc:
        if idempotency_key:
            prior = db.transactions.find_one({"business_id": actor["business_id"], "idempotency_key": idempotency_key})
            if prior:
                if prior.get("request_hash") != request_hash:
                    raise HTTPException(409, "This idempotency key was already used for a different transaction.")
                return clean(prior)
        if "Transaction numbers are only allowed" in str(exc) or "replica set" in str(exc).lower():
            raise HTTPException(503, "Financial writes require MongoDB configured as a replica set. See the local setup guide.") from exc
        raise
    return clean(doc)


@app.get("/api/v1/transactions")
def list_transactions(request: Request, response: Response, page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), customer_id: str | None = None, type: str | None = Query(default=None, pattern="^(income|expense|payment)$"), date_from: date | None = None, date_to: date | None = None):
    actor = auth(request, response, write=False)
    query = {"business_id": actor["business_id"]}
    if customer_id:
        query["customer_id"] = customer_id
    if type:
        query["type"] = type
    if date_from or date_to:
        query["date"] = {}
        if date_from:
            query["date"]["$gte"] = date_from.isoformat()
        if date_to:
            query["date"]["$lte"] = date_to.isoformat()
    total = db.transactions.count_documents(query)
    docs = db.transactions.find(query).sort([("date", -1), ("_id", -1)]).skip((page - 1) * page_size).limit(page_size)
    return {"items": [clean(doc) for doc in docs], "page": page, "page_size": page_size, "total": total}


def customer_balance(business_id: str, customer_id: str) -> int:
    pipeline = [{"$match": {"business_id": business_id, "customer_id": customer_id, "type": {"$in": ["income", "payment"]}}},
                {"$group": {"_id": None, "balance": {"$sum": {"$cond": [{"$eq": ["$type", "income"]}, {"$cond": ["$on_credit", "$amount_minor", 0]}, {"$multiply": ["$amount_minor", -1]}]}}}}]
    row = next(iter(db.transactions.aggregate(pipeline)), None)
    return row["balance"] if row else 0


@app.get("/api/v1/customers/{customer_id}/ledger")
def ledger(customer_id: str, request: Request, response: Response, page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100)):
    actor = auth(request, response, write=False)
    customer = db.customers.find_one({"_id": customer_id, "business_id": actor["business_id"], "archived": {"$ne": True}})
    if not customer:
        raise HTTPException(404, "Customer not found.")
    query = {"business_id": actor["business_id"], "customer_id": customer_id}
    total = db.transactions.count_documents(query)
    records = db.transactions.find(query).sort([("date", -1), ("_id", -1)]).skip((page - 1) * page_size).limit(page_size)
    return {"customer": clean(customer), "balance_minor": customer_balance(actor["business_id"], customer_id),
            "transactions": [clean(record) for record in records], "page": page, "page_size": page_size, "total": total}


@app.get("/api/v1/reports/summary")
def report(request: Request, response: Response, date_from: date | None = None, date_to: date | None = None):
    actor = auth(request, response, write=False)
    match = {"business_id": actor["business_id"]}
    if date_from or date_to:
        match["date"] = {}
        if date_from:
            match["date"]["$gte"] = date_from.isoformat()
        if date_to:
            match["date"]["$lte"] = date_to.isoformat()
    amounts = {"income_minor": 0, "expense_minor": 0, "payment_minor": 0}
    for row in db.transactions.aggregate([{"$match": match}, {"$group": {"_id": "$type", "total": {"$sum": "$amount_minor"}, "count": {"$sum": 1}}}]):
        amounts[f"{row['_id']}_minor"] = row["total"]
    dues = db.transactions.aggregate([{"$match": {"business_id": actor["business_id"], "customer_id": {"$ne": None}, "type": {"$in": ["income", "payment"]}}}, {"$group": {"_id": {"customer": "$customer_id", "type": "$type", "credit": "$on_credit"}, "total": {"$sum": "$amount_minor"}}}])
    outstanding = sum(row["total"] if row["_id"]["type"] == "income" and row["_id"].get("credit") else -row["total"] if row["_id"]["type"] == "payment" else 0 for row in dues)
    amounts["outstanding_minor"] = max(0, outstanding)
    amounts["customer_count"] = db.customers.count_documents({"business_id": actor["business_id"], "archived": {"$ne": True}})
    return amounts
