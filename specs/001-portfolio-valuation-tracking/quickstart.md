# Quickstart: Portfolio Valuation & Tracking

Dev setup guide for feature `001-portfolio-valuation-tracking`.

---

## Prerequisites

- Docker & Docker Compose
- Node.js 18+ and npm
- Python 3.12+ (for local development outside Docker)
- Plaid developer account (sandbox) — [https://dashboard.plaid.com/signup](https://dashboard.plaid.com/signup)

---

## 1. Clone & Branch

```bash
git clone https://github.com/RobertgPatch/Financial-accounting.git
cd Financial-accounting
git checkout 001-portfolio-valuation-tracking
```

---

## 2. Environment Variables

Add these to your environment or a `.env` file in the project root:

```env
# Existing
DATABASE_URL=postgres://postgres:postgres@db:5432/financial_accounting
SECRET_KEY=dev-secret-key-change-in-production
DEBUG=True

# NEW — Plaid (get from https://dashboard.plaid.com/developers/keys)
PLAID_CLIENT_ID=your_client_id_here
PLAID_SECRET=your_sandbox_secret_here
PLAID_ENV=sandbox
```

---

## 3. Docker Start

```bash
docker compose up --build -d
```

This starts:
- **db**: PostgreSQL 16 on port 5432
- **backend**: Django on port 8000
- **frontend**: Vite dev server on port 5173

---

## 4. Run Migrations

```bash
docker compose exec backend python manage.py migrate
```

Expected new migrations:
- `api.0003_assettag_asset_type_expansion` — Tags M2M, expanded asset types
- `api.0004_fmvsnapshot` — FMV snapshots table
- `plaid_integration.0001_initial` — PlaidItem and PlaidAccount tables

---

## 5. Seed Data (Optional)

```bash
docker compose exec backend python manage.py seed_data
```

The seed command will be updated to include sample FMV snapshots and tags.

---

## 6. Verify Setup

| Check                     | Command / URL                             | Expected                            |
|--------------------------|-------------------------------------------|-------------------------------------|
| Backend health           | `http://localhost:8000/api/`              | DRF browsable API root              |
| FMV endpoints            | `http://localhost:8000/api/fmv-snapshots/`| Empty list `[]`                     |
| Tags endpoints           | `http://localhost:8000/api/tags/`         | Empty list `[]`                     |
| Plaid endpoints          | `http://localhost:8000/api/plaid/items/`  | Empty list `[]`                     |
| Performance endpoint     | `http://localhost:8000/api/performance/summary/` | Summary with zero values     |
| Frontend                 | `http://localhost:5173`                   | Dashboard loads                     |

---

## 7. Plaid Sandbox Testing

In sandbox mode, Plaid provides test credentials:

- **Institution**: Use any sandbox institution (e.g., "Chase" in Link)
- **Credentials**: `user_good` / `pass_good`
- **MFA**: `1234` (if prompted)

Plaid Link flow:
1. Click "Link Account" in the UI
2. Select an institution
3. Enter sandbox credentials above
4. Accounts appear in the mapping screen
5. Map accounts to existing assets
6. Click "Sync" to pull balances → FMV snapshots created

---

## 8. Key Development Paths

| Feature Area        | Backend Files                                              | Frontend Files                            |
|--------------------|-----------------------------------------------------------|--------------------------------------------|
| FMV Snapshots      | `api/models.py`, `api/views.py`, `api/serializers.py`    | `pages/Assets.jsx`, `api/assets.js`       |
| Plaid Integration  | `plaid_integration/` (new app)                            | `components/PlaidLink.jsx`, `pages/PlaidAccounts.jsx` |
| Performance        | `api/performance.py` (new module)                         | `pages/Reports.jsx`, `components/PerformanceChart.jsx` |
| Classification     | `api/models.py` (AssetTag), `api/views.py`               | `components/TagManager.jsx`, filter UI     |
| Dashboard          | `api/views.py` (dashboard_summary)                        | `pages/Dashboard.jsx`                      |

---

## 9. Running Tests

```bash
# Backend
docker compose exec backend python manage.py test

# Frontend
docker compose exec frontend npm test
```

---

## 10. New Dependencies

**Backend** (`requirements.txt`):
```
plaid-python>=38.0.0,<39.0.0
```

**Frontend** (`package.json`):
```
react-plaid-link: ^4.1.0
```

Install frontend dependency:
```bash
docker compose exec frontend npm install react-plaid-link
```
