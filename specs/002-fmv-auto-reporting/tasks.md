# Tasks: FMV Auto-Reporting

**Input**: Design documents from `/specs/002-fmv-auto-reporting/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/fmv-report-api.md ✅, quickstart.md ✅

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Register new URL routes and API client functions so endpoints are wired before implementation.

- [X] T001 Add FMV report URL routes in backend/api/urls.py — add `path('reports/fmv/generate/', views.fmv_report, name='fmv-report-generate')` and `path('reports/fmv/export/', views.fmv_export, name='fmv-report-export')`
- [X] T002 [P] Add `generateFmvReport()` and `exportFmvReport()` functions in frontend/src/api/reports.js — `generateFmvReport` posts to `/reports/fmv/generate/`, `exportFmvReport` posts to `/reports/fmv/export/` with blob responseType and triggers download as `fmv_report_YYYY-MM-DD.xlsx`

---

## Phase 2: Foundational (Backend Core)

**Purpose**: Complete backend FMV report generation and endpoint — MUST be complete before any frontend user story work.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T003 Add `PLAID_TYPE_MAP` constant and `ASSET_TYPE_LABELS` dict in backend/api/reports.py — `PLAID_TYPE_MAP = {'depository': 'cash', 'investment': 'public_equity', 'loan': 'fixed_income', 'credit': 'cash'}` with fallback to `'other'`; `ASSET_TYPE_LABELS` maps each asset_type key to its display label (e.g., `'cash': 'Cash & Equivalents'`) using the 9 types from `Asset.ASSET_TYPE_CHOICES`
- [X] T004 Implement `generate_fmv_report()` function in backend/api/reports.py — accepts `type_filters=None, entity_ids=None`; Step 1: query all `PlaidAccount` objects with `select_related('plaid_item', 'asset')`, collect `mapped_asset_ids` set from accounts with `asset_id`; Step 2: for each Plaid account build item dict with name, value (`current_balance` or `Decimal('0.00')`), source `'plaid'`, asset_type (from mapped `asset.asset_type` or `PLAID_TYPE_MAP`), label, institution, subtype, mask, `needs_sync` flag, `plaid_account_id`; Step 3: query manual `Asset` objects with `fmv_snapshots__isnull=False` excluding `id__in=mapped_asset_ids`, get latest FMV snapshot per asset, build item dict with name, value, source `'manual'`, asset_type, label, asset_id, snapshot_date; Step 4: if `entity_ids` set, filter manual assets to those with `EntityAssetOwnership` records for given entities, filter Plaid accounts to those mapped to assets owned by those entities, exclude unmapped Plaid accounts; Step 5: if `type_filters` set, filter items to matching `asset_type`; Step 6: aggregate `by_type` list with `asset_type`, `label`, `total_value`, `count`, `percentage` (using `Decimal`); return dict with `total_fmv`, `item_count`, `filters`, `by_type`, `items` per API contract in contracts/fmv-report-api.md
- [X] T005 Implement `_parse_fmv_params()` helper and `fmv_report` view function in backend/api/views.py — `_parse_fmv_params(data)` extracts `type_filters` (list of strings) and `entity_ids` (comma-separated string → list of ints); `@api_view(['POST']) fmv_report(request)` parses params, calls `generate_fmv_report(**params)`, returns `Response(report)`; import `generate_fmv_report` from `.reports`
- [X] T006 [P] Add core FMV report generation tests in backend/api/tests.py — `class FMVReportTests(TestCase)`: test basic report generation with Plaid accounts returns correct total and items; test `PLAID_TYPE_MAP` categorizes depository→cash, investment→public_equity, loan→fixed_income, credit→cash; test double-count prevention (mapped Plaid account excludes manual asset's FMV snapshot); test empty state (no accounts, no assets) returns `total_fmv: '0.00'`, empty items; test negative Plaid balance (credit card) reduces total; test Plaid account with `current_balance=None` appears with value `'0.00'` and `needs_sync=True`

**Checkpoint**: Backend FMV report generation is fully functional and tested. Frontend work can now begin.

---

## Phase 3: User Story 1 — View FMV Report with Automatic Plaid Totals (Priority: P1) 🎯 MVP

**Goal**: Users can generate an FMV Report showing consolidated Plaid account balances + manual asset values with source labels.

**Independent Test**: Link a Plaid sandbox institution, navigate to Reports → FMV Report, click Generate. Report shows all Plaid account balances auto-included, manual assets with FMV snapshots included, each item labeled "Plaid" or "Manual".

- [X] T007 [US1] Create `FmvReport` component in frontend/src/pages/FmvReport.jsx — import React/useState/useEffect, Card, Button, LoadingSpinner, Badge from existing UI components, `generateFmvReport` from api/reports; component accepts no props (manages own state); state: `report` (null), `loading` (false), `error` (''); `handleGenerate` calls `generateFmvReport({})` and sets report data; render: generate button, loading spinner, error alert; when report loaded: total FMV card with formatted currency, items count; items table using MUI TableContainer/Table/TableHead/TableBody/TableRow/TableCell — columns: Name, Value (formatted currency, red for negative), Source (Badge: blue "Plaid" / green "Manual"), Asset Type (label), Institution (for Plaid items, show institution + subtype), Account (mask with •••• prefix for Plaid); empty state: when `report.item_count === 0` show alert with message "No FMV data available. Link accounts in the Accounts page or add assets with FMV snapshots."; needs_sync: for items with `needs_sync === true`, show yellow warning chip "Needs Sync" next to value; responsive: use Tailwind `overflow-x-auto` on table wrapper, stack cards on mobile
- [X] T008 [P] [US1] Add FMV API endpoint tests in backend/api/tests.py — test `POST /api/reports/fmv/generate/` returns 200 with correct JSON shape (`total_fmv`, `item_count`, `filters`, `by_type`, `items`); test that Plaid accounts are auto-included without any mapping; test `needs_sync` flag is True when `current_balance` is None

**Checkpoint**: FMV Report is fully functional with automatic Plaid totals and manual asset inclusion. Can be tested independently.

---

## Phase 4: User Story 2 — Report Page Selection (Priority: P1)

**Goal**: Reports page presents a selector between "FMV Report" and "Distribution Report". Distribution report has no FMV data.

**Independent Test**: Navigate to Reports page, see two report type options. Select each and confirm the correct report type renders. Distribution report shows no FMV totals.

- [X] T009 [US2] Add report type selector and conditional rendering to frontend/src/pages/Reports.jsx — add `reportType` state (default `'distribution'`); at the top of the page (before any filters), render two styled buttons/tabs: "FMV Report" and "Distribution Report" with active state styling (e.g., primary color for selected, outlined for unselected); when `reportType === 'fmv'`, render `<FmvReport />` (import from `'./FmvReport'`); when `reportType === 'distribution'`, render existing Distribution JSX (all current content below the selector); on type switch, call `setReport(null)` to clear previous Distribution data; ensure existing Distribution filters (period, year, entity, asset) only show when Distribution is selected
- [X] T010 [P] [US2] Add Distribution report no-FMV assertion in backend/api/tests.py — test that `generate_distribution_report()` response does NOT contain keys like `total_fmv`, `fmv`, `net_worth`, or `by_type`; confirm Distribution report output keys are unchanged (`period`, `summary`, `by_entity`, `by_asset`, `detail`, `budget_comparison`, `yoy_comparison`, `retained_earnings`)

**Checkpoint**: Reports page has functional type selector. Both FMV and Distribution reports are independently accessible.

---

## Phase 5: User Story 3 — Filter FMV Report by Asset Type (Priority: P2)

**Goal**: Users can filter the FMV Report by one or more asset type categories (Cash, Real Estate, Public Equity, etc.) and see updated totals.

**Independent Test**: Generate FMV Report, select "Cash & Equivalents" filter, confirm only cash-type items shown with recalculated total. Select multiple filters. Clear all filters to see full report.

- [X] T011 [US3] Add type filter UI to FmvReport.jsx in frontend/src/pages/FmvReport.jsx — add `selectedTypes` state (empty array = all types); render a filter section above the generate button with checkboxes or MUI Chip components for each of the 9 asset types: Cash & Equivalents, Real Estate, Public Equity, Private Equity, Fixed Income, Hedge Fund, Cryptocurrency, Collectible, Other; toggling a chip adds/removes the `asset_type` key to/from `selectedTypes`; "Clear Filters" button resets to empty array; "Select All" button selects all 9; pass `type_filters: selectedTypes.length > 0 ? selectedTypes : undefined` in the `generateFmvReport()` call; show active filter count badge when filters applied
- [X] T012 [P] [US3] Add type filter tests in backend/api/tests.py — test `generate_fmv_report(type_filters=['cash'])` returns only cash-typed items; test multiple filters `['cash', 'public_equity']` returns combined results; test filter with no matching items returns `total_fmv: '0.00'` and empty items list; test filter=None returns all items (no filtering)

**Checkpoint**: FMV Report supports type-based filtering with correct totals.

---

## Phase 6: User Story 4 — Manual Assets + Entity Filter (Priority: P2)

**Goal**: Manual assets with FMV snapshots are included with "Manual" source label. Entity filter narrows results to assets owned by selected entities.

**Independent Test**: Create a manual asset with FMV snapshot, generate FMV Report — asset appears labeled "Manual". Apply entity filter — only assets owned by that entity shown; unmapped Plaid accounts excluded.

- [X] T013 [US4] Add entity filter dropdown to FmvReport.jsx in frontend/src/pages/FmvReport.jsx — add `entities` state (loaded via `getEntities()` on mount), `selectedEntities` state (empty array); render multi-select dropdown (MUI Select with multiple + checkboxes or custom) in the filter section alongside type filters; pass `entity_ids: selectedEntities.length > 0 ? selectedEntities.join(',') : undefined` in `generateFmvReport()` call; show entity filter only when entities exist (hide if no entities in system)
- [X] T014 [P] [US4] Add entity filter and manual asset tests in backend/api/tests.py — test entity filter excludes unmapped Plaid accounts; test entity filter includes manual assets with ownership records to the filtered entity; test entity filter includes Plaid accounts mapped to assets owned by filtered entity; test manual asset without FMV snapshot is excluded; test manual asset with FMV snapshot and source `'manual'` appears correctly; test mapped asset's FMV snapshot excluded when entity filter active (double-count prevention with entity filter)

**Checkpoint**: FMV Report correctly includes manual assets and supports entity-based filtering.

---

## Phase 7: User Story 5 — Visualization (Priority: P3)

**Goal**: FMV Report displays a PieChart and summary table showing allocation breakdown by asset type.

**Independent Test**: Generate FMV Report with assets across multiple types. Verify pie chart shows proportional slices, summary table shows type/value/count/percentage per type. Apply type filter — both chart and table update.

- [X] T015 [US5] Add PieChart and type breakdown summary table to FmvReport.jsx in frontend/src/pages/FmvReport.jsx — import `PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer` from recharts; add a visualization section (below total, above items table) that renders when `report.by_type` has data; transform `report.by_type` to `[{ name: item.label, value: parseFloat(item.total_value) }]` for PieChart; use existing `COLORS` array pattern (`COLORS[i % COLORS.length]`), add a 9th color if needed; use `<ResponsiveContainer width="100%" height={300}>` for responsive sizing; add `<Tooltip formatter={v => formatCurrency(v)} />` and `<Legend />`; below the chart, render a summary table (MUI or Tailwind) with columns: Asset Type (label), Total Value (formatted currency), Items (count), Allocation (percentage + "%" suffix); sort by total_value descending; use Tailwind responsive grid (`grid grid-cols-1 lg:grid-cols-2`) to show chart and table side-by-side on desktop, stacked on mobile

**Checkpoint**: FMV Report has full visualization with chart and summary table.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Excel export, final integration, end-to-end validation.

- [X] T016 Implement `export_fmv_report()` function in backend/api/excel_export.py — create workbook with 2 sheets: "Summary" sheet (title row "FMV Report", date, total FMV, applied filters, then type breakdown table: Asset Type / Total Value / Items / Allocation %); "Line Items" sheet (headers: Name / Value / Source / Asset Type / Institution / Subtype / Snapshot Date; one row per item from report `items` list); use existing style constants (`HEADER_FILL`, `HEADER_FONT`, `TITLE_FONT`, `DATA_FONT`, `THIN_BORDER`, `ALT_ROW_FILL`), `_apply_header_row()`, and `_auto_width()` helpers; return BytesIO buffer
- [X] T017 Implement `fmv_export` view in backend/api/views.py — `@api_view(['POST']) fmv_export(request)`: parse params with `_parse_fmv_params()`, call `generate_fmv_report()`, call `export_fmv_report()`, return `HttpResponse` with content-type `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` and Content-Disposition `attachment; filename="fmv_report_YYYY-MM-DD.xlsx"`; import `export_fmv_report` from `.excel_export`
- [X] T018 [P] Add export button and handler to frontend/src/pages/FmvReport.jsx — add "Export to Excel" button (disabled when no report generated or during export); `handleExport` calls `exportFmvReport()` with same params as last generate (type_filters, entity_ids); show loading state on button during export; use `exporting` state to prevent double-clicks
- [X] T019 [P] Add FMV export endpoint test in backend/api/tests.py — test `POST /api/reports/fmv/export/` returns 200 with content-type `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`; test Content-Disposition header contains `fmv_report_` and `.xlsx`; test export with type_filters produces valid response
- [X] T020 Run quickstart.md end-to-end validation — follow all steps in specs/002-fmv-auto-reporting/quickstart.md: start Docker environment, seed data, link Plaid sandbox institution, add manual asset with FMV snapshot, generate FMV report via API and frontend, verify type filters work, verify entity filter works, verify export downloads Excel file, verify Distribution report has no FMV data

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on T001 (URL routes) — BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion (T003-T006)
  - US1 (Phase 3): First frontend work — creates `FmvReport.jsx`
  - US2 (Phase 4): Depends on US1 (imports `FmvReport` component) — T009 requires T007
  - US3 (Phase 5): Depends on US1 (modifies `FmvReport.jsx`) — T011 requires T007
  - US4 (Phase 6): Depends on US1 (modifies `FmvReport.jsx`) — T013 requires T007
  - US5 (Phase 7): Depends on US1 (modifies `FmvReport.jsx`) — T015 requires T007
- **Polish (Phase 8)**: Depends on all user story phases

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2 — No dependencies on other stories
- **US2 (P1)**: Depends on US1 (needs `FmvReport.jsx` to import). Backend test (T010) is independent [P].
- **US3 (P2)**: Depends on US1 (modifies `FmvReport.jsx`). Backend test (T012) is independent [P].
- **US4 (P2)**: Depends on US1 (modifies `FmvReport.jsx`). Backend test (T014) is independent [P].
- **US5 (P3)**: Depends on US1 (modifies `FmvReport.jsx`).

### Within Each User Story

- Frontend tasks depend on the `FmvReport.jsx` file from US1
- Backend tests marked [P] can run in parallel with frontend tasks
- Core implementation before integration

### Parallel Opportunities

- **Phase 1**: T001 and T002 can run in parallel (different codebases: backend vs frontend)
- **Phase 2**: T006 (tests) can run in parallel with T003-T005 (implementation) since tests target a different file section
- **Phase 3**: T008 (backend test) can run in parallel with T007 (frontend component)
- **Phase 4**: T010 (backend test) can run in parallel with T009 (frontend changes)
- **Phase 5**: T012 (backend test) can run in parallel with T011 (frontend changes)
- **Phase 6**: T014 (backend test) can run in parallel with T013 (frontend changes)
- **Phase 8**: T018 (frontend export) and T019 (backend test) can run in parallel with T016-T017

---

## Parallel Example: Phase 2 (Foundational)

```
# Sequential (T003 → T004 → T005 — same file, dependent):
Task T003: Add PLAID_TYPE_MAP and ASSET_TYPE_LABELS in backend/api/reports.py
Task T004: Implement generate_fmv_report() in backend/api/reports.py
Task T005: Implement FMV report view in backend/api/views.py

# Parallel with above (different file):
Task T006: Add core FMV report tests in backend/api/tests.py
```

## Parallel Example: User Story 3

```
# Frontend (sequential, same file):
Task T011: Add type filter UI to FmvReport.jsx

# Backend (parallel, different file):
Task T012: Add type filter tests in backend/api/tests.py
```

---

## Implementation Strategy

### MVP First (US1 + US2 Only)

1. Complete Phase 1: Setup (T001-T002)
2. Complete Phase 2: Foundational backend (T003-T006)
3. Complete Phase 3: US1 — FMV Report component (T007-T008)
4. Complete Phase 4: US2 — Report type selector (T009-T010)
5. **STOP and VALIDATE**: FMV Report generates with auto Plaid totals, type selector works, Distribution report unchanged
6. Deploy/demo if ready — **10 tasks for functional MVP**

### Incremental Delivery

1. Setup + Foundational → Backend ready (T001-T006)
2. Add US1 → FMV Report renders with data (T007-T008) → Test independently
3. Add US2 → Report selector works (T009-T010) → Test independently → **MVP deployed**
4. Add US3 → Type filters work (T011-T012) → Test independently
5. Add US4 → Entity filter works (T013-T014) → Test independently
6. Add US5 → Charts and tables render (T015) → Test independently
7. Add Polish → Export works, full validation (T016-T020) → **Feature complete**

Each story adds value without breaking previous stories.

---

## Notes

- **No new models or migrations** — this feature is entirely computed views on existing data
- Backend test tasks marked [P] can always run alongside frontend tasks (different files)
- `FmvReport.jsx` is a new file created in US1 (T007) — all subsequent frontend US tasks modify it
- All monetary calculations use Python `Decimal` — no floating-point arithmetic
- The `generate_fmv_report()` function handles ALL parameters from the start (type_filters, entity_ids) — user story phases focus on frontend UI for those features + corresponding tests
- Commit after each task or logical group
- Stop at any checkpoint to validate the story independently
