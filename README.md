# Financial Accounting — Distribution Manager

A scalable, extensible financial accounting application built with a **React + Vite** frontend and a **Django REST Framework** backend.

---

## Screenshots

| Dashboard | Distribution Report |
|-----------|-------------------|
| ![Dashboard](https://github.com/user-attachments/assets/833980a1-402c-4819-80e5-4c90909fc750) | ![Report](https://github.com/user-attachments/assets/21187cf6-021a-4bcf-9586-f66c0bb53c18) |

| Report Charts | Entity Management |
|--------------|-------------------|
| ![Charts](https://github.com/user-attachments/assets/077cb9fe-49a4-44ed-94cc-f691fd3f7756) | Timeline + Pie allocation charts |

---

## Architecture

```
Financial-accounting/
├── backend/                 # Django REST API
│   ├── api/
│   │   ├── models.py        # Entity, Asset, EntityAssetOwnership, Distribution, DistributionAllocation
│   │   ├── serializers.py   # DRF serializers (read + nested write)
│   │   ├── views.py         # ModelViewSets + report endpoints
│   │   ├── urls.py          # API routing
│   │   ├── reports.py       # Report generation logic
│   │   ├── excel_export.py  # Excel (openpyxl) export
│   │   ├── admin.py         # Django admin registration
│   │   └── tests.py         # API + report tests (14 tests)
│   ├── financial_accounting/
│   │   └── settings.py      # Django settings (CORS, DRF, SQLite)
│   ├── manage.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                # React + Vite
│   ├── src/
│   │   ├── api/             # Axios API clients
│   │   ├── components/      # Reusable UI (Button, Card, Modal, Table, Badge…)
│   │   ├── pages/           # Dashboard, Entities, Assets, Ownerships, Distributions, Reports
│   │   └── main.jsx
│   ├── package.json
│   └── Dockerfile
├── .github/
│   └── workflows/
│       ├── ci.yml           # CI: test backend + build frontend on every push/PR
│       └── deploy.yml       # Deploy: GitHub Pages (frontend) + artifact (backend)
└── docker-compose.yml       # Local dev environment
```

---

## Data Model

The schema is intentionally **extensible** — `Asset` supports any asset type, not just properties:

| Model | Purpose |
|-------|---------|
| `Entity` | Any stakeholder: individual, company, LLC, trust, partnership |
| `Asset` | Any asset: **property**, **stock**, **fund**, **bond**, or other |
| `EntityAssetOwnership` | % ownership of an entity in an asset (with effective date) |
| `Distribution` | A distribution event on an asset with a total amount |
| `DistributionAllocation` | How a distribution is split among entities |

---

## API Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| GET/POST | `/api/entities/` | List / create entities |
| GET/PUT/DELETE | `/api/entities/{id}/` | Retrieve / update / delete entity |
| GET/POST | `/api/assets/` | List / create assets |
| GET/POST | `/api/ownerships/` | List / create ownership records |
| GET/POST | `/api/distributions/` | List / create distributions (with nested allocations) |
| GET/POST | `/api/distribution-allocations/` | List / create allocations |
| **POST** | `/api/reports/generate/` | **Generate a distribution report (JSON)** |
| **POST** | `/api/reports/export/` | **Download distribution report (Excel)** |

### Report Parameters

```json
{
  "period_type": "yearly | quarterly | monthly",
  "year": 2024,
  "quarter": 1,       // 1–4, for quarterly
  "month": 6,         // 1–12, for monthly
  "entity_ids": "1,2,3",   // optional filter
  "asset_ids": "1,2"        // optional filter
}
```

---

## Quick Start

### Prerequisites
- Python 3.12+
- Node.js 20+

### Backend

```bash
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data      # loads sample entities, assets, distributions
python manage.py runserver
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

### Docker Compose (both services)

```bash
docker-compose up --build
```

---

## Features

### Distribution Reports
- **Period types**: Yearly, Quarterly (Q1–Q4), Monthly
- **Filters**: by entity, by asset, by year
- **Outputs**:
  - Dashboard-style UI with summary cards, entity/asset breakdowns, distribution timeline bar chart, entity allocation pie chart, and a detailed allocations table
  - **Excel export** with 3 sheets: Summary, Distribution Detail, Asset Allocations

### Entity Management
- CRUD for any entity type (individual, company, LLC, trust, partnership)
- Colored type badges

### Asset Management
- CRUD for any asset type (property, stock, fund, bond, other)
- Conditional fields: address for properties, ticker symbol for stocks

### Ownership Management
- Assign % ownership of entities in assets with effective dates
- Validation: total ownership per asset validated against 100%

### Distribution Management
- Record distribution events with automatic allocation rows pre-filled from ownership %

---

## Railway Deployment

Both the backend and frontend Dockerfiles are configured to read Railway's `PORT` environment variable, which is the key requirement for avoiding **502 errors**.

### Setup Steps

1. **Create a new Railway project** at [railway.app](https://railway.app).

2. **Add a PostgreSQL plugin** — Railway will provide two connection URLs:
   - `DATABASE_URL` — private internal network (preferred).
   - `DATABASE_PUBLIC_URL` — public proxy (use if the private URL is unreachable).
   
   The backend automatically tries `DATABASE_URL` first and falls back to `DATABASE_PUBLIC_URL`.  Make sure the PostgreSQL plugin is **linked** to the backend service so Railway injects the variables, or copy the connection string from the plugin's **Connect** tab and set `DATABASE_URL` (or `DATABASE_PUBLIC_URL`) manually in the backend service's **Variables** tab.

3. **Deploy the backend**:
   - Click **New → GitHub Repo** and select this repository.
   - Set the **Root Directory** to `backend`.
   - Add these environment variables in the service **Variables** tab:
     | Variable | Value |
     |----------|-------|
     | `SECRET_KEY` | A strong random key (see `.env.example`) |
     | `DJANGO_DEBUG` | `False` |
     | `DJANGO_ALLOWED_HOSTS` | `.up.railway.app` |
     | `CORS_ALLOWED_ORIGINS` | `https://<your-frontend>.up.railway.app` |
     | `DATABASE_URL` | Linked automatically when the Postgres plugin is connected to this service. If the backend logs show *"Database unavailable"*, copy the **public** URL from the plugin's **Connect** tab and set `DATABASE_PUBLIC_URL` instead. |

   - Railway detects the `Dockerfile`, builds, and runs the backend on the `PORT` it assigns.

4. **Deploy the frontend**:
   - Click **New → GitHub Repo** and select this repository again.
   - Set the **Root Directory** to `frontend`.
   - Add this environment variable:
     | Variable | Value |
     |----------|-------|
     | `VITE_API_BASE_URL` | `https://<your-backend>.up.railway.app/api` |

   - Railway detects the `Dockerfile`, builds the React app, and serves it on the assigned `PORT`.

5. **Generate domains** for both services under **Settings → Networking → Generate Domain**.

### How It Works

- Railway injects a `PORT` environment variable into each container.
- The **backend** Dockerfile runs: `gunicorn ... --bind 0.0.0.0:$PORT`
- The **frontend** Dockerfile builds the React app and serves it with `serve -s dist -l tcp://0.0.0.0:$PORT`
- If `PORT` is not set (e.g., local Docker), the backend defaults to `8000` and the frontend to `3000`.

---

## CI/CD (GitHub Actions)

| Workflow | Trigger | What it does |
|----------|---------|--------------|
| **CI** (`ci.yml`) | Push / PR to main | Runs Django tests (14), builds frontend, uploads artifact |
| **Deploy** (`deploy.yml`) | Push to main / manual | Builds frontend → **GitHub Pages**, packages backend artifact |

To enable GitHub Pages deployment:
1. Go to **Settings → Pages** in your repo
2. Set Source to **GitHub Actions**
3. Push to `main` — the frontend will be deployed automatically

---

## Running Tests

```bash
cd backend
python manage.py test api --verbosity=2
```

All 14 tests cover: entity CRUD, asset CRUD, ownership creation, distribution creation, yearly/quarterly/monthly report generation, and Excel export.

