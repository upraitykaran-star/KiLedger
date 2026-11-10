# KiLedger

KiLedger is a vanilla HTML/CSS/JavaScript bookkeeping interface with a Python FastAPI API and MongoDB storage. The original green and white frontend is kept. The browser sends customer and transaction changes to the API; the API scopes those records to the signed-in business.

## What works in this version

- Account registration and login with Argon2 password hashes.
- HttpOnly session cookie, seven-day expiry, logout revocation, and CSRF header checks on writes.
- Business membership records, an owner role, and owner-managed staff/admin role changes for existing members.
- Business-isolated customer create/list/read/update/archive operations.
- Business-isolated transaction recording and filtering, customer ledger, report summary, and pagination.
- INR stored as integer paise. A credit sale adds to customer balance; a payment subtracts from it. Expenses and paid sales do not change the customer balance.
- MongoDB transaction and audit event for a financial write; idempotency keys for retried submissions.
- A small set of schema and MongoDB-backed integration tests.

This is a practical development core, not an audited accounting or production-ready financial service. There is no migration of old localStorage data into MongoDB, email verification, password reset, member invitation flow, report CSV export, or external payment provider integration. The existing browser-only profile records are left untouched and are not displayed by the server-backed app.

## Requirements

- macOS with Python 3.11 or newer (Python 3.14 is supported by the selected dependencies).
- MongoDB Community Server and `mongosh` for local database setup.
- A browser. Node.js and npm are not needed for this vanilla frontend.

MongoDB financial writes use multi-document transactions, so the local MongoDB server must run as a single-node replica set. A standalone `mongod` can start, but financial writes will return an explicit setup error until replica-set mode is enabled.

## Local setup (Mac)

Open Terminal in this project folder.

1. Create a virtual environment and install the pinned Python packages:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip
   pip install -r backend/requirements.txt
   ```

2. Copy the example configuration. If you already have a `.env`, keep it and edit it yourself rather than overwriting it:

   ```bash
   cp backend/.env.example .env
   ```

3. Start MongoDB as a local one-member replica set. Install MongoDB Community Server and `mongosh` using the official MongoDB macOS instructions if they are not already installed. In Terminal 1:

   ```bash
   mkdir -p mongodb-data
   mongod --replSet rs0 --bind_ip localhost --port 27017 --dbpath mongodb-data
   ```

   In Terminal 2, initialize the replica set once:

   ```bash
   mongosh --eval 'rs.initiate()'
   ```

   Wait until `mongosh --eval 'rs.status().ok'` returns `1`. Data is held in the ignored `mongodb-data/` folder.

4. Initialize connectivity and indexes. This command creates indexes only; it does not create users or sample financial records:

   ```bash
   python -m backend.init_db
   ```

5. Start the API in Terminal 2:

   ```bash
   uvicorn backend.main:app --reload --host 127.0.0.1 --port 8001
   ```

   API health: <http://127.0.0.1:8001/api/v1/health>. Interactive API docs: <http://127.0.0.1:8001/api/v1/docs>.

6. Start the frontend in Terminal 3:

   ```bash
   python3 -m http.server 8000 --bind 127.0.0.1
   ```

   Open <http://127.0.0.1:8000>. Create an account from **Log in → Create an account**.

The frontend API URL is set in `api-config.js` to `http://localhost:8001/api/v1`. Change it for another local port or deployment. Add the frontend's exact origin to `KILEDGER_ALLOWED_ORIGINS` in `.env`; restart the API after changing configuration.

## Run tests

Schema tests do not need MongoDB. Activate the environment first:

```bash
pytest backend/tests/test_schemas.py -q
```

The API tests use a unique throwaway database and drop only that database when the test run finishes. Point them at a disposable replica-set MongoDB instance:

```bash
KILEDGER_TEST_MONGODB_URI='mongodb://localhost:27017/?replicaSet=rs0' pytest backend/tests -q
```

Do not point `KILEDGER_TEST_MONGODB_URI` at a database with data you need. The API integration suite drops its uniquely named `kileger_test_*` database after running.

## Financial rules and API

Money requests use `amount_minor` (paise), a positive integer. For example, ₹125.50 is `12550`. INR is the only supported currency in this version. For a customer, the outstanding balance is:

```text
sum(credit income amount_minor) - sum(payment amount_minor)
```

A payment greater than the currently due amount is accepted and can result in a customer credit (negative balance); this preserves the actual entries rather than silently capping the payment. Financial history has no update/delete endpoint; corrections should be added as explicit correcting entries in a future workflow.

API prefix is `/api/v1`; FastAPI publishes request schemas at `/api/v1/docs`. Key routes:

- `POST /auth/register`, `POST /auth/login`, `GET /auth/me`, `POST /auth/logout`
- `GET|POST /customers`, `GET|PATCH|DELETE /customers/{id}` (`DELETE` archives)
- `GET|POST /transactions` (filter by customer, type, date range; POST accepts `Idempotency-Key`)
- `GET /customers/{id}/ledger`, `GET /reports/summary`
- `POST /businesses`, `GET /businesses/members`, `PATCH /businesses/members/{user_id}`

The session token stays in an HttpOnly cookie. JavaScript keeps only the short-lived CSRF value in memory and reloads it from `/auth/me`; it does not save authentication tokens in localStorage. The cookie is `SameSite=Lax`. Production must use HTTPS and set `KILEDGER_COOKIE_SECURE=true`.

## Troubleshooting

- **Backend cannot connect:** check that `mongod` is running and the URI in `.env` points to it.
- **Financial write says replica set required:** start `mongod` with `--replSet rs0`, run `rs.initiate()` once, then wait for primary election.
- **CORS error:** the page origin must exactly match an entry in `KILEDGER_ALLOWED_ORIGINS` (including scheme and port).
- **Sign-in says API unavailable:** start the API on port 8001 and confirm `/api/v1/health` responds.
- **Existing local profiles are missing:** they remain in this browser's localStorage but are intentionally not treated as server accounts. No automatic transfer is performed.

## Deployment checklist

- Use a managed MongoDB replica set with network access limited to the application; never expose MongoDB publicly.
- Use HTTPS, `KILEDGER_COOKIE_SECURE=true`, strong unique database credentials, and a secret manager for credentials.
- Set explicit production CORS origins and allowed hosts; do not use wildcards with credentialed cookies.
- Put the API behind a maintained TLS-terminating reverse proxy, enforce request-size and timeout limits, and use centralized rate limiting. The included login limiter is in process memory and is not sufficient across multiple workers.
- Back up MongoDB and test restore procedures. Monitor errors and audit event retention.
- Complete independent security review, dependency vulnerability checks, privacy/data retention review, and accounting review before using real financial records.

## Dependency versions

Exact dependency pins are in `backend/requirements.txt`. They were chosen from releases available on 28 October 2026. Recheck and update them deliberately before deployment.
