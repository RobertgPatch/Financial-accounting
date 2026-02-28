# Implementation Plan: Portfolio Valuation & Tracking (A1 + A2 + A3)

**Branch**: `001-portfolio-valuation-tracking` | **Date**: 2026-02-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-portfolio-valuation-tracking/spec.md`

## Summary

Add fair market value (FMV) tracking with optional Plaid account linking, performance & return calculations (TWR/IRR), and asset classification with custom tagging to the family office financial accounting platform. All new UI must be mobile/tablet responsive. The feature extends the existing Django `api` app models and adds a new `plaid` Django app for external API integration, with corresponding React pages and components on the frontend.

## Technical Context

**Language/Version**: Python 3.12, JavaScript (React 19 / ES2022)  
**Primary Dependencies**: Django 4.2, Django REST Framework, React 19, Vite 7, Tailwind CSS 3, MUI 7 (selective), recharts, axios, `plaid-python` 38.x (new), `react-plaid-link` 4.1.x (new), pure Python TWR/IRR (no external math libs)  
**Storage**: PostgreSQL 16 (existing)  
**Testing**: Django TestCase (existing pattern in `api/tests.py`), manual QA for frontend  
**Target Platform**: Web (responsive: 320px mobile, 768px tablet, 1280px+ desktop), Docker Compose local, Railway production  
**Project Type**: Web application (Django backend + React SPA frontend)  
**Performance Goals**: FMV/tag queries < 500ms with 500 assets; TWR/IRR computation < 2s for 1000 snapshots; Plaid sync < 5s per item  
**Constraints**: No authentication (single-tenant); Plaid sandbox in dev; Decimal precision for all money; Atomic DB operations for financial writes  
**Scale/Scope**: 2 principals, ~50-200 assets, ~500-5000 FMV snapshots, 1-10 Plaid linked accounts

### Unknowns (NEEDS CLARIFICATION)

1. **Plaid environment configuration**: NEEDS CLARIFICATION — how to structure Plaid API key storage (env vars vs Django settings), sandbox vs production switching
2. **TWR/IRR calculation approach**: ✅ RESOLVED — pure Python implementation (Newton's method for XIRR, geometric linking for TWR). No new dependencies. See [research.md](research.md)
3. **Plaid webhook handling**: NEEDS CLARIFICATION — do we need webhooks for real-time balance updates or is manual/scheduled sync sufficient for MVP
4. **Asset-to-Plaid-account mapping**: NEEDS CLARIFICATION — auto-create new assets for each Plaid account or require user to map to existing assets

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Django + React Full-Stack | ✅ PASS | All work extends existing Django `api` app + new `plaid` app; React frontend |
| II. Mobile-First Responsive | ✅ PASS | FR-017 mandates responsive at 320/768/1280px. All new UI uses Tailwind responsive utilities |
| III. Data Integrity First | ✅ PASS | All FMV writes atomic; Decimal fields for monetary values; Plaid tokens stored securely |
| IV. Incremental Migration Safety | ✅ PASS | New models via Django migrations; no destructive changes to existing models |
| V. Simplicity & YAGNI | ✅ PASS | Direct model access; no service layers; TWR/IRR as simple utility functions. Plaid app justified by external API isolation |
| VI. Test Coverage | ✅ PASS | Model tests + API endpoint tests planned for all new endpoints |
| Max 3 Django apps | ⚠️ JUSTIFIED | Adding `plaid` app (2 total). Justified: Plaid integration has its own models, token management, and sync logic that is cleanly separable from core financial data |

**Gate result: PASS** — One justified deviation (new Django app for Plaid).

## Project Structure

### Documentation (this feature)

```text
specs/001-portfolio-valuation-tracking/
├── plan.md              # This file
├── research.md          # Phase 0: resolved unknowns
├── data-model.md        # Phase 1: entity definitions
├── quickstart.md        # Phase 1: dev onboarding
├── contracts/           # Phase 1: API contracts
│   ├── fmv-api.md
│   ├── plaid-api.md
│   ├── performance-api.md
│   └── classification-api.md
└── tasks.md             # Phase 2 (NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
backend/
├── api/
│   ├── models.py          # Extended: Asset.asset_type choices, AssetTag M2M, FMVSnapshot
│   ├── serializers.py     # New serializers for FMV, tags, performance
│   ├── views.py           # New viewsets/endpoints for FMV CRUD, performance, classification
│   ├── urls.py            # New routes
│   ├── reports.py         # Extended: net worth, portfolio-by-class calculations
│   ├── performance.py     # NEW: TWR/IRR calculation utilities
│   └── tests.py           # Extended: FMV, tag, performance tests
├── plaid_integration/     # NEW Django app
│   ├── models.py          # PlaidItem, PlaidAccount
│   ├── views.py           # Link token, exchange, sync endpoints
│   ├── serializers.py
│   ├── urls.py
│   ├── services.py        # Plaid API client wrapper
│   └── tests.py
└── requirements.txt       # + plaid-python

frontend/
├── src/
│   ├── api/
│   │   ├── fmv.js         # NEW: FMV snapshot CRUD
│   │   ├── plaid.js       # NEW: Plaid link/sync
│   │   └── performance.js # NEW: TWR/IRR fetch
│   ├── components/
│   │   ├── ui/
│   │   │   └── TagInput.jsx    # NEW: reusable tag chip input
│   │   └── plaid/
│   │       └── PlaidLink.jsx   # NEW: Plaid Link wrapper
│   ├── pages/
│   │   ├── Assets.jsx          # Extended: tags, FMV column, filter bar
│   │   ├── AssetDetail.jsx     # NEW: FMV history, performance, tags
│   │   ├── Accounts.jsx        # NEW: Plaid linked accounts management
│   │   ├── Dashboard.jsx       # Extended: net worth card, portfolio-by-class chart
│   │   └── EntityDetail.jsx    # NEW: entity portfolio view with aggregate performance
│   └── App.jsx                 # Updated routes
└── package.json               # + react-plaid-link
```

**Structure Decision**: Web application (Option 2). Extends existing `backend/api/` app for core features. New `backend/plaid_integration/` app for Plaid isolation (justified above). Frontend adds new pages and components following existing patterns.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| 2nd Django app (`plaid_integration`) | Plaid has its own models (tokens, accounts), its own API client, and its own sync lifecycle that is cleanly separable | Putting Plaid models/views in `api` app would mix external integration concerns with core financial data, making it harder to disable/swap Plaid later |

## Post-Design Constitution Re-Check

*Re-evaluated after Phase 1 (data-model.md, contracts/, quickstart.md complete)*

| Principle | Status | Post-Design Notes |
|-----------|--------|-------------------|
| I. Django + React Full-Stack | ✅ PASS | All contracts use DRF endpoints. No new frameworks. `plaid-python` is a client library, not a framework. Pure Python for TWR/IRR (no numpy-financial). |
| II. Mobile-First Responsive | ✅ PASS | Contracts define JSON APIs (UI-agnostic). Quickstart documents 320/768/1280px targets. Implementation phase must use Tailwind responsive classes. |
| III. Data Integrity First | ✅ PASS | data-model.md specifies: DecimalField(15,2) for all monetary values, unique_together constraints, atomic Plaid sync operations, FMV snapshots never deleted on Plaid unlink. |
| IV. Incremental Migration Safety | ✅ PASS | 3 additive migrations planned (no destructive changes). Asset.asset_type migration maps old→new values. All migrations reversible. |
| V. Simplicity & YAGNI | ✅ PASS | No service layers (except Plaid client wrapper which is justified for external API isolation). Direct model queries. No webhooks for MVP (manual sync only). No scheduled tasks. |
| VI. Test Coverage | ✅ PASS | Quickstart documents test commands. Contracts define expected status codes/responses (testable). Performance calculations have clear edge cases documented in research.md. |
| Max 3 Django apps | ⚠️ JUSTIFIED | `plaid_integration` app confirmed necessary — has 2 models, own serializers, own URL namespace, Plaid API client. Clean separation from core `api` app. |

**Post-design gate result: PASS** — All principles satisfied. No new deviations introduced during design phase. Research resolved all unknowns: pure Python TWR/IRR (no new math dependencies), manual Plaid sync (no webhooks/celery), user maps accounts to existing assets (no auto-create).
