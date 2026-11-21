import hashlib
import json
import logging
import secrets
from contextlib import asynccontextmanager
from datetime import date

from fastapi import FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .config import get_settings
from .database import AuditEvent, Business, Customer, Membership, SessionRecord, Transaction, User, create_database, init_database
from .schemas import BusinessIn, CustomerIn, LoginIn, RegisterIn, RoleIn, TransactionIn
from .security import check_login_rate, hash_token, issue_session, password_hasher, require_session, utcnow

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("kileger")
settings = get_settings()
engine = None
SessionFactory = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine, SessionFactory
    engine, SessionFactory = create_database(settings.database_url)
    init_database(engine)
    yield
    engine.dispose()


app = FastAPI(title="KiLedger API", version="2.0.0", lifespan=lifespan, docs_url="/api/v1/docs", openapi_url="/api/v1/openapi.json")
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.hosts)
app.add_middleware(CORSMiddleware, allow_origins=settings.origins, allow_credentials=True,
                   allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
                   allow_headers=["Content-Type", "X-CSRF-Token", "Idempotency-Key"])


def clean(row):
    if row is None:
        return None
    if isinstance(row, Customer):
        return {"id": row.id, "business_id": row.business_id, "name": row.name, "email": row.email, "phone": row.phone,
                "notes": row.notes, "archived": row.archived, "created_at": row.created_at.isoformat(), "updated_at": row.updated_at.isoformat()}
    if isinstance(row, Transaction):
        return {"id": row.id, "business_id": row.business_id, "description": row.description, "amount_minor": row.amount_minor,
                "currency": row.currency, "type": row.type, "customer_id": row.customer_id,
                "date": row.date.isoformat(), "method": row.method, "on_credit": row.on_credit, "created_at": row.created_at.isoformat()}
    if isinstance(row, Business):
        return {"id": row.id, "name": row.name, "currency": row.currency, "created_at": row.created_at.isoformat(), "updated_at": row.updated_at.isoformat()}
    return row


def auth(request: Request, response: Response, session, write: bool = True) -> dict:
    return require_session(request, response, session, settings, csrf_required=write)


def audit(session, actor: dict, action: str, entity: str, entity_id: str, **details):
    session.add(AuditEvent(business_id=actor["business_id"], actor_id=actor["user_id"], action=action,
                           entity=entity, entity_id=entity_id, details=json.dumps(details), created_at=utcnow()))


@app.exception_handler(IntegrityError)
async def integrity_handler(_request: Request, exc: IntegrityError):
    logger.info("MySQL constraint rejected a write: %s", type(exc.orig).__name__)
    return Response(content='{"detail":"A record with these details already exists."}', status_code=409, media_type="application/json")


@app.exception_handler(SQLAlchemyError)
async def database_handler(_request: Request, exc: SQLAlchemyError):
    logger.error("Database operation failed: %s", type(exc).__name__)
    return Response(content='{"detail":"Database operation failed. Check the service configuration and retry."}', status_code=503, media_type="application/json")


@app.get("/api/v1/health")
def health():
    try:
        with SessionFactory() as session:
            session.execute(select(1))
        return {"status": "ok"}
    except SQLAlchemyError:
        return Response(content='{"status":"unavailable"}', status_code=503, media_type="application/json")


@app.post("/api/v1/auth/register", status_code=201)
def register(payload: RegisterIn, request: Request, response: Response):
    check_login_rate(request, settings)
    with SessionFactory() as session:
        user_id, business_id = secrets.token_hex(18), secrets.token_hex(18)
        now = utcnow()
        user = User(id=user_id, email=str(payload.email).lower(), name=payload.name,
                    password_hash=password_hasher.hash(payload.password), disabled=False, created_at=now)
        business = Business(id=business_id, name=payload.business_name, currency="INR", created_at=now, updated_at=now)
        session.add_all([user, business])
        session.flush()
        session.add(Membership(business_id=business_id, user_id=user_id, role="owner", created_at=now))
        audit(session, {"business_id": business_id, "user_id": user_id}, "user.register", "business", business_id)
        csrf = issue_session(session, response, user_id, business_id, settings)
        return {"user": {"id": user_id, "email": user.email, "name": user.name},
                "business": {"id": business_id, "name": business.name, "currency": "INR"}, "csrf_token": csrf}


@app.post("/api/v1/auth/login")
def login(payload: LoginIn, request: Request, response: Response):
    check_login_rate(request, settings)
    with SessionFactory() as session:
        user = session.scalar(select(User).where(User.email == str(payload.email).lower()))
        if not user or user.disabled or not password_hasher.verify(payload.password, user.password_hash):
            raise HTTPException(401, "Email or password is incorrect.")
        membership = session.scalar(select(Membership).where(Membership.user_id == user.id).order_by(Membership.role != "owner"))
        business = session.get(Business, membership.business_id) if membership else None
        if not membership or not business:
            raise HTTPException(403, "No active business workspace is available.")
        csrf = issue_session(session, response, user.id, business.id, settings)
        return {"user": {"id": user.id, "email": user.email, "name": user.name}, "business": clean(business), "csrf_token": csrf}


@app.get("/api/v1/auth/me")
def me(request: Request, response: Response):
    with SessionFactory() as session:
        actor = auth(request, response, session, write=False)
        business = session.get(Business, actor["business_id"])
        csrf = secrets.token_urlsafe(24)
        record = session.get(SessionRecord, actor["session_hash"])
        record.csrf_hash = hash_token(csrf)
        session.commit()
        return {"user": {"id": actor["user_id"], "email": actor["email"], "name": actor["name"]},
                "business": clean(business), "role": actor["role"], "csrf_token": csrf}


@app.post("/api/v1/auth/logout", status_code=204)
def logout(request: Request, response: Response):
    with SessionFactory() as session:
        actor = auth(request, response, session)
        session.delete(session.get(SessionRecord, actor["session_hash"]))
        session.commit()
        response.delete_cookie(settings.session_cookie, path="/")
        return Response(status_code=204)


@app.post("/api/v1/businesses", status_code=201)
def create_business(payload: BusinessIn, request: Request, response: Response):
    with SessionFactory() as session:
        actor = auth(request, response, session)
        business_id, now = secrets.token_hex(18), utcnow()
        business = Business(id=business_id, name=payload.name, currency="INR", created_at=now, updated_at=now)
        session.add_all([business, Membership(business_id=business_id, user_id=actor["user_id"], role="owner", created_at=now)])
        record = session.get(SessionRecord, actor["session_hash"])
        record.business_id = business_id
        audit(session, {**actor, "business_id": business_id}, "business.create", "business", business_id)
        session.commit()
        return clean(business)


@app.get("/api/v1/businesses/members")
def list_members(request: Request, response: Response):
    with SessionFactory() as session:
        actor = auth(request, response, session, write=False)
        rows = session.execute(select(Membership, User.email).join(User, User.id == Membership.user_id).where(Membership.business_id == actor["business_id"])).all()
        return [{"user_id": membership.user_id, "role": membership.role, "email": email} for membership, email in rows]


@app.patch("/api/v1/businesses/members/{user_id}")
def set_member_role(user_id: str, payload: RoleIn, request: Request, response: Response):
    with SessionFactory() as session:
        actor = auth(request, response, session)
        if actor["role"] != "owner":
            raise HTTPException(403, "Only the business owner can change roles.")
        member = session.scalar(select(Membership).where(Membership.business_id == actor["business_id"], Membership.user_id == user_id, Membership.role != "owner"))
        if not member:
            raise HTTPException(404, "Business member not found.")
        member.role = payload.role
        audit(session, actor, "membership.role_update", "membership", user_id, role=payload.role)
        session.commit()
        return {"user_id": user_id, "role": payload.role}


@app.get("/api/v1/customers")
def customers(request: Request, response: Response, page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), q: str = ""):
    with SessionFactory() as session:
        actor = auth(request, response, session, write=False)
        query = select(Customer).where(Customer.business_id == actor["business_id"], Customer.archived.is_(False))
        if q.strip():
            query = query.where(Customer.name.ilike(f"%{q.strip()}%"))
        total = session.scalar(select(func.count()).select_from(query.subquery()))
        rows = session.scalars(query.order_by(Customer.name).offset((page - 1) * page_size).limit(page_size)).all()
        return {"items": [clean(row) for row in rows], "page": page, "page_size": page_size, "total": total}


@app.post("/api/v1/customers", status_code=201)
def create_customer(payload: CustomerIn, request: Request, response: Response):
    with SessionFactory() as session:
        actor = auth(request, response, session)
        now = utcnow()
        row = Customer(id=secrets.token_hex(18), business_id=actor["business_id"], name=payload.name,
                       email=str(payload.email).lower() if payload.email else None, phone=payload.phone, notes=payload.notes,
                       archived=False, created_at=now, updated_at=now, created_by=actor["user_id"])
        session.add(row)
        audit(session, actor, "customer.create", "customer", row.id)
        session.commit()
        return clean(row)


def get_customer_row(session, customer_id: str, business_id: str, include_archived: bool = False):
    query = select(Customer).where(Customer.id == customer_id, Customer.business_id == business_id)
    if not include_archived:
        query = query.where(Customer.archived.is_(False))
    return session.scalar(query)


@app.get("/api/v1/customers/{customer_id}")
def get_customer(customer_id: str, request: Request, response: Response):
    with SessionFactory() as session:
        actor = auth(request, response, session, write=False)
        row = get_customer_row(session, customer_id, actor["business_id"])
        if not row:
            raise HTTPException(404, "Customer not found.")
        return clean(row)


@app.patch("/api/v1/customers/{customer_id}")
def update_customer(customer_id: str, payload: CustomerIn, request: Request, response: Response):
    with SessionFactory() as session:
        actor = auth(request, response, session)
        row = get_customer_row(session, customer_id, actor["business_id"])
        if not row:
            raise HTTPException(404, "Customer not found.")
        row.name, row.email, row.phone, row.notes = payload.name, str(payload.email).lower() if payload.email else None, payload.phone, payload.notes
        row.updated_at = utcnow()
        audit(session, actor, "customer.update", "customer", customer_id)
        session.commit()
        return clean(row)


@app.delete("/api/v1/customers/{customer_id}", status_code=204)
def archive_customer(customer_id: str, request: Request, response: Response):
    with SessionFactory() as session:
        actor = auth(request, response, session)
        row = get_customer_row(session, customer_id, actor["business_id"])
        if not row:
            raise HTTPException(404, "Customer not found.")
        row.archived, row.updated_at = True, utcnow()
        audit(session, actor, "customer.archive", "customer", customer_id)
        session.commit()
        return Response(status_code=204)


@app.post("/api/v1/transactions", status_code=201)
def create_transaction(payload: TransactionIn, request: Request, response: Response, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    with SessionFactory() as session:
        actor = auth(request, response, session)
        if payload.type == "payment" and not payload.customer_id:
            raise HTTPException(422, "Payments must reference a customer.")
        if payload.on_credit and not payload.customer_id:
            raise HTTPException(422, "Credit sales must reference a customer.")
        if payload.customer_id and not get_customer_row(session, payload.customer_id, actor["business_id"]):
            raise HTTPException(422, "Customer does not belong to this business or is archived.")
        if idempotency_key and len(idempotency_key) > 100:
            raise HTTPException(422, "Idempotency key is too long.")
        request_hash = hashlib.sha256(json.dumps(payload.model_dump(mode="json"), sort_keys=True).encode()).hexdigest()
        if idempotency_key:
            prior = session.scalar(select(Transaction).where(Transaction.business_id == actor["business_id"], Transaction.idempotency_key == idempotency_key))
            if prior:
                if prior.request_hash != request_hash:
                    raise HTTPException(409, "This idempotency key was already used for a different transaction.")
                return clean(prior)
        row = Transaction(id=secrets.token_hex(18), business_id=actor["business_id"], description=payload.description,
                          amount_minor=payload.amount_minor, currency=payload.currency, type=payload.type, customer_id=payload.customer_id,
                          date=payload.date, method=payload.method, on_credit=payload.on_credit, idempotency_key=idempotency_key,
                          request_hash=request_hash if idempotency_key else None, created_at=utcnow(), created_by=actor["user_id"])
        session.add(row)
        audit(session, actor, "transaction.create", "transaction", row.id, type=payload.type, amount_minor=payload.amount_minor)
        session.commit()
        return clean(row)


@app.get("/api/v1/transactions")
def list_transactions(request: Request, response: Response, page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), customer_id: str | None = None, type: str | None = Query(default=None, pattern="^(income|expense|payment)$"), date_from: date | None = None, date_to: date | None = None):
    with SessionFactory() as session:
        actor = auth(request, response, session, write=False)
        query = select(Transaction).where(Transaction.business_id == actor["business_id"])
        if customer_id:
            query = query.where(Transaction.customer_id == customer_id)
        if type:
            query = query.where(Transaction.type == type)
        if date_from:
            query = query.where(Transaction.date >= date_from)
        if date_to:
            query = query.where(Transaction.date <= date_to)
        total = session.scalar(select(func.count()).select_from(query.subquery()))
        rows = session.scalars(query.order_by(Transaction.date.desc(), Transaction.id.desc()).offset((page - 1) * page_size).limit(page_size)).all()
        return {"items": [clean(row) for row in rows], "page": page, "page_size": page_size, "total": total}


def customer_balance(session, business_id: str, customer_id: str) -> int:
    credit = func.coalesce(func.sum(Transaction.amount_minor), 0)
    income_due = select(credit).where(Transaction.business_id == business_id, Transaction.customer_id == customer_id,
                                       Transaction.type == "income", Transaction.on_credit.is_(True)).scalar_subquery()
    payments = select(func.coalesce(func.sum(Transaction.amount_minor), 0)).where(Transaction.business_id == business_id,
                         Transaction.customer_id == customer_id, Transaction.type == "payment").scalar_subquery()
    return int(session.scalar(select(income_due - payments)) or 0)


@app.get("/api/v1/customers/{customer_id}/ledger")
def ledger(customer_id: str, request: Request, response: Response, page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100)):
    with SessionFactory() as session:
        actor = auth(request, response, session, write=False)
        customer = get_customer_row(session, customer_id, actor["business_id"])
        if not customer:
            raise HTTPException(404, "Customer not found.")
        query = select(Transaction).where(Transaction.business_id == actor["business_id"], Transaction.customer_id == customer_id)
        total = session.scalar(select(func.count()).select_from(query.subquery()))
        records = session.scalars(query.order_by(Transaction.date.desc(), Transaction.id.desc()).offset((page - 1) * page_size).limit(page_size)).all()
        return {"customer": clean(customer), "balance_minor": customer_balance(session, actor["business_id"], customer_id),
                "transactions": [clean(row) for row in records], "page": page, "page_size": page_size, "total": total}


@app.get("/api/v1/reports/summary")
def report(request: Request, response: Response, date_from: date | None = None, date_to: date | None = None):
    with SessionFactory() as session:
        actor = auth(request, response, session, write=False)
        query = select(Transaction).where(Transaction.business_id == actor["business_id"])
        if date_from:
            query = query.where(Transaction.date >= date_from)
        if date_to:
            query = query.where(Transaction.date <= date_to)
        amounts = {"income_minor": 0, "expense_minor": 0, "payment_minor": 0}
        for kind, total in session.execute(select(Transaction.type, func.sum(Transaction.amount_minor)).where(query.whereclause).group_by(Transaction.type)):
            amounts[f"{kind}_minor"] = int(total or 0)
        amounts["outstanding_minor"] = int(session.scalar(select(func.coalesce(func.sum(Transaction.amount_minor), 0)).where(
            Transaction.business_id == actor["business_id"], Transaction.type == "income", Transaction.on_credit.is_(True))) or 0) - int(
            session.scalar(select(func.coalesce(func.sum(Transaction.amount_minor), 0)).where(Transaction.business_id == actor["business_id"], Transaction.type == "payment")) or 0)
        amounts["outstanding_minor"] = max(0, amounts["outstanding_minor"])
        amounts["customer_count"] = session.scalar(select(func.count()).select_from(Customer).where(Customer.business_id == actor["business_id"], Customer.archived.is_(False)))
        return amounts
