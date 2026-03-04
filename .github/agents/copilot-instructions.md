# Financial-accounting Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-02-28

## Active Technologies
- Python 3.12, JavaScript (React 19) + Django 4.2, DRF 3.x, Vite 7, Tailwind CSS 3, MUI 7, recharts, axios, plaid-python 38.x, openpyxl (002-fmv-auto-reporting)
- PostgreSQL 16 (002-fmv-auto-reporting)
- Python 3.12, JavaScript (ES2022+) + Django 4.2, Django REST Framework, React 19, Vite 7, Tailwind CSS 3, MUI 7, recharts, axios, openpyxl (003-portfolio-tracker-redesign)
- PostgreSQL 16 via Django ORM (2 new tables: Commitment, CapitalCall) (003-portfolio-tracker-redesign)

- Python 3.12, JavaScript (React 19 / ES2022) + Django 4.2, Django REST Framework, React 19, Vite 7, Tailwind CSS 3, MUI 7 (selective), recharts, axios, `plaid-python` 38.x (new), `react-plaid-link` 4.1.x (new), pure Python TWR/IRR (Newton's method XIRR) (001-portfolio-valuation-tracking)

## Project Structure

```text
backend/
  api/               # Core models, views, serializers, reports
  plaid_integration/  # Plaid API wrapper (new app)
  financial_accounting/  # Django settings
frontend/
  src/
    api/             # Axios API clients
    components/      # Reusable UI (layout, ui)
    pages/           # Route pages
```

## Commands

docker compose up --build -d
docker compose exec backend python manage.py test
docker compose exec frontend npm test

## Code Style

- Python: Django/DRF conventions, Decimal for money, snake_case
- JavaScript: React functional components, Tailwind utility classes, camelCase
- Mobile-first responsive: 320px → 768px → 1280px+

## Recent Changes
- 003-portfolio-tracker-redesign: Added Python 3.12, JavaScript (ES2022+) + Django 4.2, Django REST Framework, React 19, Vite 7, Tailwind CSS 3, MUI 7, recharts, axios, openpyxl
- 002-fmv-auto-reporting: Added Python 3.12, JavaScript (React 19) + Django 4.2, DRF 3.x, Vite 7, Tailwind CSS 3, MUI 7, recharts, axios, plaid-python 38.x, openpyxl

- 001-portfolio-valuation-tracking: FMV snapshots, Plaid integration, TWR/IRR performance analytics, asset classification & tagging

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
