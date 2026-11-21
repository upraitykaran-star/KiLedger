# KiLedger

KiLedger is a vanilla HTML/CSS/JavaScript bookkeeping interface with a Python FastAPI backend and MySQL database. The browser calls the API for authentication, customer records, transactions, customer ledgers, and report summaries. Records are scoped to the signed-in business.

## Features

- Registration and login with Argon2 password hashes, HttpOnly sessions, CSRF checks, and login rate limiting.
- MySQL tables for users, businesses, memberships, customers, transactions, sessions, and audit events.
- Tenant-scoped customer CRUD/archive and transaction recording, filtering, pagination, ledgers, and report summaries.
- Money stored as integer paise; financial history is append-only. Transaction writes and audit rows commit together.
- Idempotency keys prevent duplicate financial submissions.

This is a learning and development app, not an audited or production-ready financial service. There is no automatic import of old browser localStorage data. Existing records are not deleted or migrated by the setup commands.

## Requirements

- Python 3.11 or newer.
- MySQL 8.0 or newer.
- A browser. Node.js/npm are not needed for the vanilla frontend.

## Local setup on macOS

1. In Terminal, move to this project folder and create a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip
   pip install -r backend/requirements.txt
   ```

2. Start MySQL, then create a database and a local-only app user. In the MySQL shell, replace the password with a strong local password:

   ```sql
   CREATE DATABASE kileger CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
   CREATE USER 'kileger'@'localhost' IDENTIFIED BY 'replace-with-a-local-password';
   GRANT ALL PRIVILEGES ON kileger.* TO 'kileger'@'localhost';
   ```

3. Copy the example environment file and edit `.env` to use the same password. Keep `.env` private:

   ```bash
   cp backend/.env.example .env
   ```

   `KILEDGER_DATABASE_URL` should look like:

   ```text
   mysql+pymysql://kileger:your-password@127.0.0.1:3306/kileger?charset=utf8mb4
   ```

   URL-encode special characters in the password (for example, `@` becomes `%40`).

4. Create the tables and verify the MySQL connection. This creates missing tables only; it does not seed, delete, or migrate data:

   ```bash
   python -m backend.init_db
   ```

5. Start the API:

   ```bash
   uvicorn backend.main:app --reload --host 127.0.0.1 --port 8001
   ```

   Health check: <http://127.0.0.1:8001/api/v1/health>. API docs: <http://127.0.0.1:8001/api/v1/docs>.

6. In another Terminal, serve the frontend:

   ```bash
   python3 -m http.server 8000 --bind 127.0.0.1
   ```

   Open <http://127.0.0.1:8000>, then choose **Create an account** on the login screen. The frontend API URL is in `api-config.js`.

## API routes

All routes use `/api/v1`:

- `POST /auth/register`, `POST /auth/login`, `GET /auth/me`, `POST /auth/logout`
- `POST /businesses`, `GET /businesses/members`, `PATCH /businesses/members/{user_id}`
- `GET|POST /customers`, `GET|PATCH|DELETE /customers/{id}` (`DELETE` archives)
- `GET|POST /transactions` (POST accepts `Idempotency-Key`)
- `GET /customers/{id}/ledger`, `GET /reports/summary`

The session token is held in an HttpOnly cookie. JavaScript keeps only a CSRF value in memory, not the login token in localStorage. For a public deployment, use HTTPS and set `KILEDGER_COOKIE_SECURE=true`; configure exact frontend origins in `KILEDGER_ALLOWED_ORIGINS`.

## Tests

Run tests from the project root with the virtual environment active:

```bash
pytest backend/tests -q
```

The test suite uses an isolated SQLite database by default and does not connect to or modify your MySQL data. Schema tests and API tests can run without a MySQL server.

## Troubleshooting

- **API reports database unavailable:** confirm MySQL is running and `.env` has the correct `KILEDGER_DATABASE_URL`.
- **Access denied:** check the MySQL username/password and that the account has privileges on `kileger`.
- **Browser CORS error:** use the configured frontend origin exactly, including its port.
- **Sign-in redirects to login:** start the API on port 8001 and check `/api/v1/health`.
- **Old browser-only records are not visible:** the server backend does not import localStorage data automatically.

For real financial records, add HTTPS, managed secret storage, database backups and restore checks, rate limiting across workers, and an independent security/accounting review before deployment.
