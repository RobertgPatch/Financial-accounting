# Financial-Accounting Constitution

## Core Principles

### I. Django + React Full-Stack
All features are built using the existing Django REST Framework backend and React + Vite frontend. No new frameworks or languages unless justified. Backend serves JSON APIs; frontend consumes them. Shared data contracts via DRF serializers.

### II. Mobile-First Responsive Design
All UI must be responsive — mobile, tablet, and desktop. Use Tailwind CSS responsive utilities (sm:, md:, lg:). No desktop-only layouts. Test at 320px, 768px, and 1280px breakpoints minimum.

### III. Data Integrity First
All financial data operations must be atomic (use Django transactions). Decimal precision for all monetary values. Audit-critical operations must be logged. No floating-point arithmetic for money.

### IV. Incremental Migration Safety
Database changes must use Django migrations. No raw SQL schema changes. Migrations must be reversible where possible. Existing data must not be destroyed during migrations.

### V. Simplicity & YAGNI
Start with the simplest implementation that satisfies requirements. No premature abstraction. No over-engineering patterns (repository pattern, service layers, event buses) unless justified by concrete need. Direct model access is preferred.

### VI. Test Coverage
New features require tests — at minimum: model validation tests, API endpoint tests (status codes, response shape), and critical business logic unit tests. Frontend: manual QA is acceptable for MVP; automated tests are a plus.

## Technology Stack

- **Backend**: Python 3.12, Django 4.2, Django REST Framework, PostgreSQL 16
- **Frontend**: React 19, Vite 7, Tailwind CSS 3, MUI 7 (selective), recharts, axios
- **Infrastructure**: Docker Compose (local), Railway (production)
- **External APIs**: Plaid (account linking), potential market data providers

## Constraints

- **Max 3 Django apps**: Currently `api` is the sole app. Add new apps only if domain separation is clearly needed (e.g., a `plaid` app for external integrations). Justify any new app.
- **No authentication yet**: System is single-tenant for now. Auth will be added later. Do not add auth scaffolding prematurely.
- **Budget consciousness**: Use free tiers of external services where possible. Plaid sandbox for development.

## Governance

- Constitution supersedes ad-hoc decisions
- Amendments require documentation and justification
- All PRs should verify compliance with these principles

**Version**: 1.0.0 | **Ratified**: 2026-02-28 | **Last Amended**: 2026-02-28
