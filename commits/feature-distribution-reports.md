# feature/distribution-reports

**Branch:** `feature/distribution-reports`
**Base:** `main`
**Date:** 2026-02-28

---

## Summary

Comprehensive distribution reporting enhancements and an interactive, filter-driven dashboard. This branch adds Year-over-Year comparison reports, retained earnings rollforward, Excel export with multiple sheets, auto-allocation for distributions, and a fully filterable dashboard where every card, chart, and table reacts to user-selected criteria.

---

## Changes

### Backend

| File | Description |
|------|-------------|
| `backend/api/reports.py` | Added `generate_yoy_report()`, `generate_retained_earnings()`, `generate_dashboard_summary()` — new report generators for YoY comparison, retained earnings rollforward, and dashboard KPI data |
| `backend/api/views.py` | Added `yoy_comparison`, `retained_earnings`, `dashboard_summary`, and `auto_allocate_distribution` API endpoints |
| `backend/api/urls.py` | Registered new routes: `reports/yoy/`, `reports/retained-earnings/`, `reports/dashboard-summary/`, `distributions/<id>/auto-allocate/` |
| `backend/api/excel_export.py` | Added `add_budget_sheet()`, `add_yoy_sheet()`, `add_retained_earnings_sheet()` — multi-sheet Excel export support |

### Frontend

| File | Description |
|------|-------------|
| `frontend/src/pages/Dashboard.jsx` | **Major rewrite** — added global filter bar (Year, Entity, Asset, Distribution Type) with active-filter pills; all KPI cards, secondary stats, bar chart, pie chart, and recent distributions table now reactively filter via `useMemo`; added top-entity/top-asset/avg-distribution cards computed from filtered data |
| `frontend/src/pages/Reports.jsx` | Added YoY Comparison section and Retained Earnings Rollforward section with dedicated generate/export actions |
| `frontend/src/pages/Distributions.jsx` | Added Auto-Allocate button that calls the new backend endpoint |
| `frontend/src/api/reports.js` | Added `getDashboardSummary()` API call |
| `frontend/src/api/distributions.js` | Added `autoAllocateDistribution()` API call |

---

## New API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/reports/dashboard-summary/` | Dashboard KPI summary (totals, averages, top entity/asset, YoY %) |
| `POST` | `/api/reports/generate/` | Generate distribution report (includes `yoy_comparison` and `retained_earnings` in response) |
| `POST` | `/api/reports/export/` | Export distribution report as Excel (includes YoY and retained earnings sheets) |
| `POST` | `/api/distributions/<id>/auto-allocate/` | Auto-allocate a distribution across entities by ownership percentage |

---

## Dashboard Filters

The dashboard now features a persistent filter bar at the top of the page:

- **Year** — dropdown populated from all years present in distribution data
- **Entity** — scopes all cards/charts to distributions involving the selected entity
- **Asset** — filters to distributions on a specific asset
- **Distribution Type** — regular / special / return_of_capital / liquidating
- **Clear** button + removable active-filter pills with live match count

All filtering is client-side using React `useMemo` — no extra API calls on filter change.

---

## Stats

- **9 files changed**
- **~1,030 lines added** across backend and frontend
- **0 breaking changes** — all new endpoints and UI features are additive
