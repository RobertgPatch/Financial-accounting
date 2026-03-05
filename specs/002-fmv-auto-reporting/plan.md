# Implementation Plan: FMV Auto-Reporting

**Branch**: `002-fmv-auto-reporting` | **Date**: 2026-02-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-fmv-auto-reporting/spec.md`

## Summary

Split the Reports page into separate FMV and Distribution report views. The FMV Report automatically totals all Plaid-linked account balances (no mapping required) alongside manually-added asset FMV snapshots, with type-based filtering and Excel export. The Distribution Report is cleaned of all FMV data. Backend adds a new `generate_fmv_report()` function that queries `PlaidAccount` balances and `FMVSnapshot` latest values, applies a hardcoded Plaid type → asset type mapping, and prevents double-counting for mapped accounts. Frontend adds a report type selector and a dedicated FMV report view with recharts visualization.

## Technical Context

**Language/Version**: Python 3.12, JavaScript (React 19)
**Primary Dependencies**: Django 4.2, DRF 3.x, Vite 7, Tailwind CSS 3, MUI 7, recharts, axios, plaid-python 38.x, openpyxl
**Storage**: PostgreSQL 16
**Testing**: Django TestCase (`python manage.py test`), 88 existing tests
**Target Platform**: Docker Compose (local), Railway (production)
**Project Type**: Web application (Django REST API + React SPA)
**Performance Goals**: FMV report generation < 3s (SC-001), filter updates < 2s (SC-003)
**Constraints**: Single-tenant (no auth), Decimal precision for all monetary values, no floating-point arithmetic for money
**Scale/Scope**: Single user, ~10s of Plaid accounts, ~10s of manual assets, 2 Django apps (`api`, `plaid_integration`)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Status | Notes |
|---|-----------|--------|-------|
| I | Django + React Full-Stack | ✅ PASS | Uses existing Django/DRF backend and React frontend. No new frameworks. |
| II | Mobile-First Responsive | ✅ PASS | Report views will use Tailwind responsive utilities (sm:, md:, lg:). Charts use ResponsiveContainer. |
| III | Data Integrity First | ✅ PASS | All monetary values use `Decimal`. Plaid `current_balance` is `DecimalField(max_digits=15, decimal_places=2)`. No floating-point math. |
| IV | Incremental Migration Safety | ✅ PASS | No new models or migrations needed. Uses existing `PlaidAccount`, `Asset`, `FMVSnapshot` models as-is. |
| V | Simplicity & YAGNI | ✅ PASS | Direct model queries in `reports.py`. Hardcoded type mapping dict (no config UI). No new abstraction layers. |
| VI | Test Coverage | ✅ PASS | Will add: FMV report generation tests, Plaid type mapping tests, double-count prevention tests, API endpoint tests. |

**Constraints Check:**

| Constraint | Status | Notes |
|------------|--------|-------|
| Max 3 Django apps | ✅ PASS | Currently 2 apps (`api`, `plaid_integration`). No new app needed. |
| No authentication | ✅ PASS | No auth scaffolding added. |
| Budget consciousness | ✅ PASS | Uses existing Plaid sandbox. No new paid services. |

**Gate Result: ✅ ALL PASS — proceeding to Phase 0.**

### Post-Design Re-Check (after Phase 1)

| # | Principle | Status | Post-Design Notes |
|---|-----------|--------|-------------------|
| I | Django + React Full-Stack | ✅ PASS | All changes in existing Django views/reports.py + React. No new frameworks. |
| II | Mobile-First Responsive | ✅ PASS | FmvReport.jsx uses Tailwind responsive + `<ResponsiveContainer>` for charts. |
| III | Data Integrity First | ✅ PASS | All values `Decimal` throughout. Backend aggregation in Python Decimal. |
| IV | Incremental Migration Safety | ✅ PASS | Zero new models, zero migrations. Pure read-only report from existing data. |
| V | Simplicity & YAGNI | ✅ PASS | Hardcoded type map, direct model queries, no service layer. |
| VI | Test Coverage | ✅ PASS | FMV generation, type mapping, dedup, entity filter, endpoint, export tests planned. |

**Post-Design Gate: ✅ ALL PASS. No violations. No complexity justifications needed.**

## Project Structure

### Documentation (this feature)

```text
specs/002-fmv-auto-reporting/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── fmv-report-api.md
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
backend/
├── api/
│   ├── models.py              # Existing — no changes (Asset, FMVSnapshot)
│   ├── reports.py             # MODIFY — add generate_fmv_report(), PLAID_TYPE_MAP
│   ├── views.py               # MODIFY — add fmv_report endpoint, fmv_export endpoint
│   ├── excel_export.py        # MODIFY — add export_fmv_report()
│   ├── urls.py                # MODIFY — add FMV report/export URL routes
│   ├── serializers.py         # Existing — no changes expected
│   └── tests.py               # MODIFY — add FMV report tests
├── plaid_integration/
│   └── models.py              # Existing — no changes (PlaidAccount with type, current_balance)

frontend/
├── src/
│   ├── pages/
│   │   └── Reports.jsx        # MODIFY — add report type selector, FMV report view
│   ├── api/
│   │   └── reports.js         # MODIFY — add generateFmvReport(), exportFmvReport()
│   └── components/            # May add FMV-specific sub-components if needed
```

**Structure Decision**: Web application structure (Option 2). All changes are modifications to existing files — no new Django apps, no new top-level directories. The FMV report logic lives in `api/reports.py` alongside existing report functions. Frontend changes are contained in the existing `Reports.jsx` page and `reports.js` API client.

## Complexity Tracking

> No constitution violations found. No complexity justifications needed.
