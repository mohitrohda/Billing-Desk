# Billing Desk — Billing & Invoicing Software

A runnable MVP built with React + Vite, FastAPI, SQLAlchemy, and SQLite by default (PostgreSQL supported through `DATABASE_URL`). It uses original branding and independently written code.

## Included and working in this MVP
- Registration/login, hashed passwords, JWT-protected business endpoints
- Dashboard with database-backed counts, invoiced amount, payments, balance, overdue count, expenses, and recent invoices
- Customer and product/service CRUD
- Invoice creation with server-side line totals/tax, status updates, and PDF downloads
- Full/partial manual payments with overpayment protection and payment history
- Basic quotation records/status, expense records, and business settings
- Responsive React UI, API docs, health endpoint, basic smoke test

## Important scope limits
This is a functional MVP, not yet a production-certified accounting system. It does **not** currently include automated recurring-invoice scheduling, reminder delivery, email sending, online payment processing, quote-to-invoice conversion, a customer portal, full audit logging, migration scripts, or comprehensive test coverage. Configure tax/currency rules with the reviewer before real business use. Do not expose it publicly until secrets, HTTPS, backups, database migrations, rate limiting, authorization roles, and production deployment are reviewed.

## Requirements
- Python 3.10+
- Node.js 20+ recommended
- macOS, Windows, or Linux

## Run backend (Mac/Linux)
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Change SECRET_KEY in .env before any deployment.
uvicorn app.main:app --reload
```
API docs: http://127.0.0.1:8000/docs
Health check: http://127.0.0.1:8000/api/health

The default database is local SQLite (`backend/billing.db`), so no PostgreSQL installation is required for the first run. To use PostgreSQL, set a suitable SQLAlchemy URL in `backend/.env`, e.g. `postgresql+psycopg://user:password@localhost:5432/billing_db`, and install `psycopg[binary]` in the backend environment.

## Run frontend (second terminal)
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```
Open http://localhost:5173. Create the first account using **Create an account**. The first registered account receives the `admin` role; later accounts receive `staff`, but detailed role-based permission policies are not yet implemented.

## Test
From `backend/` with its virtual environment active:
```bash
pytest -q
```

## Data and business rules
- Invoice totals are recalculated by the backend using the saved product price/tax values at invoice creation time.
- Invoice items keep a snapshot of description, quantity, price, and tax values.
- Payment entries are manual records only; no money is moved by this application.
- Dashboard invoiced amount includes non-cancelled invoices, including drafts. Overdue count is limited to sent/partially paid invoices with a due date in the past.
- SQLite schema creation is automatic for local use. This MVP does not include Alembic migrations; use migrations before schema changes in production.

## Folder structure
```text
backend/
  app/main.py       FastAPI routes and business logic
  app/models.py     SQLAlchemy database models
  app/schemas.py    Request validation
  app/security.py   Password hashing and JWT helpers
  app/database.py   Database setup
  tests/            Smoke test
frontend/
  src/App.jsx       Responsive application and modules
  src/api.js        API helper with auth token
  src/style.css     Responsive styling
```
