# Implementation Plan: Portfolio Tracker Redesign

**Branch**: `003-portfolio-tracker-redesign` | **Date**: 2026-03-04 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-portfolio-tracker-redesign/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Redesign the Reports page from a distribution report generator into a full portfolio tracker with three configurable views: **Portfolio Summary** (entity-level PE/VC rollups with commitment tracking, DPI/RVPI/TVPI/IRR), **Asset Class Summary** (allocation breakdown by asset type with pie charts), and **Investment Performance** (per-asset IRR/DPI/RVPI/TVPI with filters). Requires two new Django models (Commitment, CapitalCall), new API endpoints, a new portfolio calculation engine, and a redesigned frontend tab-based Reports page.

## Technical Context

**Language/Version**: Python 3.12, JavaScript (ES2022+)
**Primary Dependencies**: Django 4.2, Django REST Framework, React 19, Vite 7, Tailwind CSS 3, MUI 7, recharts, axios, openpyxl
**Storage**: PostgreSQL 16 via Django ORM (2 new tables: Commitment, CapitalCall)
**Testing**: Django TestCase (`python manage.py test api`), run inside Docker Compose
**Target Platform**: Web (Docker Compose local, Railway production)
**Project Type**: Web application (Django REST API + React SPA)
**Performance Goals**: Portfolio Summary loads within 3 seconds; tab switches < 1 second; exports < 5 seconds
**Constraints**: Decimal precision for all monetary values; no floating-point for money; XIRR tolerance ≤ 0.01% vs Excel; division-by-zero guarded
**Scale/Scope**: Single-tenant, ~4 entities, ~50 assets, < 500 capital call records

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Django + React Full-Stack | ✅ PASS | All work stays within Django REST + React. No new frameworks. |
| II. Mobile-First Responsive | ✅ PASS | Tab-based views will use Tailwind responsive utilities. Tables scroll horizontally on mobile. |
| III. Data Integrity First | ✅ PASS | Commitment/CapitalCall use Decimal fields. PE metrics computed from Decimal. Django transactions on writes. |
| IV. Incremental Migration Safety | ✅ PASS | 2 new models via Django migrations. No destructive changes to existing tables. Existing Distribution/FMV models unchanged. |
| V. Simplicity & YAGNI | ✅ PASS | Direct model access for queries. No repository pattern. Calculation functions are pure functions. No premature view configuration backend — tabs stored in localStorage. |
| VI. Test Coverage | ✅ PASS | Model validation tests, API endpoint tests, PE metric calculation unit tests, division-by-zero edge case tests. |
| Max 3 Django apps | ✅ PASS | Commitment + CapitalCall go in existing `api` app. No new Django apps. |
| No authentication | ✅ PASS | No auth added. |
| Budget consciousness | ✅ PASS | No new external services. |

**Gate result: PASS — no violations. Proceed to Phase 0.**

## Project Structure

### Documentation (this feature)

```text
specs/003-portfolio-tracker-redesign/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── portfolio-api.md
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
backend/
├── api/
│   ├── models.py           # ADD: Commitment, CapitalCall models
│   ├── serializers.py      # ADD: CommitmentSerializer, CapitalCallSerializer
│   ├── views.py            # ADD: portfolio summary/class/performance endpoints, commitment/call CRUD
│   ├── urls.py             # ADD: new URL routes
│   ├── reports.py          # ADD: portfolio_summary(), asset_class_summary() functions
│   ├── performance.py      # MODIFY: add commitment-based IRR calculation
│   ├── excel_export.py     # ADD: export functions for all 3 views
│   ├── tests.py            # ADD: model, API, calculation tests
│   └── migrations/
│       └── 0005_commitment_capitalcall.py  # AUTO-GENERATED

frontend/
├── src/
│   ├── pages/
│   │   ├── Reports.jsx         # REWRITE: tab-based view container
│   │   ├── PortfolioSummary.jsx  # NEW: entity rollup table
│   │   ├── AssetClassSummary.jsx # NEW: allocation breakdown + chart
│   │   └── InvestmentPerformance.jsx # NEW: per-asset performance table
│   └── api/
│       ├── reports.js          # ADD: portfolio/class/performance API functions
│       └── commitments.js      # NEW: commitment + capital call CRUD API
```

**Structure Decision**: Follows existing web-app layout (backend/ + frontend/). All new models in `api` app. Three new frontend page components matching the three view tabs. No new Django apps.

## Complexity Tracking

> No constitution violations — table not needed.
