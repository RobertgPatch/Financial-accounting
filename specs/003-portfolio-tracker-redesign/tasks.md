# Tasks: Portfolio Tracker Redesign

**Input**: Design documents from `/specs/003-portfolio-tracker-redesign/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/portfolio-api.md, quickstart.md

**Tests**: Included — quickstart.md defines expected test coverage with specific test function names.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Path Conventions

- **Backend**: `backend/api/` (Django REST API)
- **Frontend**: `frontend/src/` (React SPA)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create new Django models and migration for commitment/capital-call tracking

- [X] T001 Add Commitment model (entity FK, asset FK, commitment_date, original_amount, notes, timestamps; unique_together entity+asset) and CapitalCall model (commitment FK, call_date, amount, notes, created_at; ordering by call_date) to backend/api/models.py
- [X] T002 Run makemigrations to generate backend/api/migrations/0005_commitment_capitalcall.py
- [X] T003 Register Commitment and CapitalCall with list_display and list_filter in backend/api/admin.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Serializers, shared calculation helpers, URL routing, and frontend API clients that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Add CommitmentSerializer (read-only computed fields: paid_in, pct_called, unfunded, call_count from aggregate CapitalCall.amount) and CapitalCallSerializer (read-only commitment_display as "Entity → Asset") in backend/api/serializers.py
- [X] T005 Extract _collect_valued_items(entity_ids=None, type_filters=None) helper from generate_fmv_report() in backend/api/reports.py — must handle Plaid balance lookup, manual FMV snapshot lookup, mapped_asset_ids dedup, entity filtering via EntityAssetOwnership, and return list of dicts with name/value/source/asset_type/institution/snapshot_date; refactor generate_fmv_report() to call the new helper
- [X] T006 Implement compute_entity_residual(entity_id, as_of_date=None) in backend/api/reports.py — for each asset owned by entity via EntityAssetOwnership, get latest FMVSnapshot.value or PlaidAccount.current_balance (Plaid preferred for mapped assets), multiply by ownership percentage/100, sum all; return Decimal
- [X] T007 Add all new URL routes in backend/api/urls.py: POST portfolio/summary/, POST portfolio/asset-class-summary/, POST portfolio/performance/, POST portfolio/summary/export/, POST portfolio/asset-class-summary/export/, POST portfolio/performance/export/, and CRUD routers for /commitments/ and /capital-calls/
- [X] T008 [P] Create frontend API client in frontend/src/api/commitments.js — CRUD functions: getCommitments(filters), createCommitment(data), updateCommitment(id, data), deleteCommitment(id), getCapitalCalls(filters), createCapitalCall(data), updateCapitalCall(id, data), deleteCapitalCall(id)
- [X] T009 [P] Add portfolio view API functions in frontend/src/api/reports.js — getPortfolioSummary(params), getAssetClassSummary(params), getInvestmentPerformance(params), exportPortfolioSummary(params), exportAssetClassSummary(params), exportInvestmentPerformance(params); export functions must handle blob response and trigger file download

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 5 — Commitment & Capital Call Tracking (Priority: P1)

**Goal**: CRUD API for recording commitments and capital calls so PE/VC metrics can be computed

**Independent Test**: Create a commitment via POST /api/commitments/, record capital calls via POST /api/capital-calls/, verify computed fields (paid_in, pct_called, unfunded) update correctly

- [X] T010 [US5] Implement CommitmentViewSet in backend/api/views.py
- [X] T011 [US5] Implement CapitalCallViewSet in backend/api/views.py
- [X] T012 [US5] Add tests in backend/api/tests.py: test_commitment_create, test_commitment_unique_constraint, test_commitment_computed_fields (paid_in/pct_called/unfunded from capital calls), test_capital_call_create, test_capital_call_overcall_warning, test_commitment_delete_cascades_calls

**Checkpoint**: Commitment and CapitalCall CRUD fully functional — data entry for PE metrics ready

---

## Phase 4: User Story 1 — Portfolio Summary View (Priority: P1) 🎯 MVP

**Goal**: Entity-level rollup table showing Original Commitment, % Called, Unfunded, Paid-In, Distributions, Residual, DPI, RVPI, TVPI, IRR for each entity plus an "All Entities" total row

**Independent Test**: Create entity with commitment + capital calls + distributions, POST /api/portfolio/summary/ and verify all 10 columns compute correctly; verify "All Entities" row sums monetary values and recomputes ratios from aggregates (not averages)

- [X] T013 [US1] Add compute_entity_xirr(entity_id, as_of_date=None) in backend/api/performance.py
- [X] T014 [US1] Implement generate_portfolio_summary(entity_ids=None, as_of_date=None) in backend/api/reports.py
- [X] T015 [US1] Add PortfolioSummaryView as APIView with POST method in backend/api/views.py
- [X] T016 [P] [US1] Create PortfolioSummary.jsx in frontend/src/pages/PortfolioSummary.jsx
- [X] T017 [US1] Add tests in backend/api/tests.py: test_portfolio_summary_basic, test_portfolio_summary_all_entities_row, test_portfolio_summary_zero_paid_in, test_portfolio_summary_entity_filter, test_entity_xirr_basic, test_entity_xirr_no_data_returns_none

**Checkpoint**: Portfolio Summary fully functional — core MVP deliverable complete

---

## Phase 5: User Story 4 — Configurable View Tabs (Priority: P2)

**Goal**: Tab-based navigation on Reports page with three views and localStorage persistence

**Independent Test**: Navigate to /reports, see three tabs, click each tab to switch views, refresh browser and verify last-selected tab persists

- [X] T018 [US4] Rewrite Reports.jsx in frontend/src/pages/Reports.jsx — replace existing distribution report content with MUI Tabs component; three tabs: "Portfolio Summary" (default), "Asset Class Summary", "Investment Performance"; persist selected tab to localStorage
- [X] T019 [P] [US4] Update Sidebar.jsx navigation — subtitle changed to "Portfolio Tracker"
- [X] T020 [P] [US4] Verify /reports route in frontend/src/App.jsx still renders the Reports page component correctly

**Checkpoint**: Tab navigation working — all three views accessible from one page

---

## Phase 6: User Story 2 — Asset Class Summary View (Priority: P2)

**Goal**: Portfolio allocation breakdown by asset type with total value, percentage, item count, and pie chart visualization

**Independent Test**: Create assets across multiple types with FMV snapshots and/or Plaid accounts, POST /api/portfolio/asset-class-summary/ and verify by_class percentages sum to 100%, item counts are correct, no double-counting between Plaid and manual

- [X] T021 [US2] Implement generate_asset_class_summary(entity_ids=None, type_filters=None) in backend/api/reports.py
- [X] T022 [US2] Add AssetClassSummaryView as APIView with POST method in backend/api/views.py
- [X] T023 [P] [US2] Create AssetClassSummary.jsx in frontend/src/pages/AssetClassSummary.jsx
- [X] T024 [US2] Add tests in backend/api/tests.py: test_asset_class_summary_grouping, test_asset_class_summary_percentages_sum_to_100, test_asset_class_summary_no_double_counting, test_asset_class_summary_empty_portfolio, test_asset_class_summary_type_filter

**Checkpoint**: Asset Class Summary fully functional with chart visualization

---

## Phase 7: User Story 3 — Investment Performance View (Priority: P3)

**Goal**: Per-asset and per-entity IRR, DPI, RVPI, TVPI with entity filter and as-of-date support

**Independent Test**: Create entity with multiple committed assets, capital calls, and distributions across dates, POST /api/portfolio/performance/ and verify per-asset IRR/DPI/RVPI/TVPI; verify entity_totals uses pooled XIRR (not weighted average)

- [X] T025 [US3] Implement generate_investment_performance(entity_ids=None, as_of_date=None) in backend/api/reports.py
- [X] T026 [US3] Add InvestmentPerformanceView as APIView with POST method in backend/api/views.py
- [X] T027 [P] [US3] Create InvestmentPerformance.jsx in frontend/src/pages/InvestmentPerformance.jsx
- [X] T028 [US3] Add tests in backend/api/tests.py: test_investment_performance_per_asset_metrics, test_investment_performance_entity_totals_pooled_xirr, test_investment_performance_entity_filter, test_investment_performance_insufficient_data_irr_null

**Checkpoint**: Investment Performance fully functional — all three views complete

---

## Phase 8: User Story 6 — Excel Export (Priority: P3)

**Goal**: Export any of the three views to .xlsx Excel file with headers and data matching on-screen display

**Independent Test**: POST /api/portfolio/summary/export/ with data, verify response is valid .xlsx with correct headers and values; repeat for asset-class and performance exports

- [X] T029 [US6] Implement export_portfolio_summary(data) in backend/api/excel_export.py
- [X] T030 [US6] Implement export_asset_class_summary(data) in backend/api/excel_export.py
- [X] T031 [US6] Implement export_investment_performance(data) in backend/api/excel_export.py
- [X] T032 [US6] Add export POST endpoints in backend/api/views.py
- [X] T033 [US6] Add export buttons to all 3 view components
- [X] T034 [US6] Add tests in backend/api/tests.py: test_export_portfolio_summary_xlsx, test_export_asset_class_summary_xlsx, test_export_investment_performance_xlsx, test_export_content_type_header

**Checkpoint**: Excel export working for all three views

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Edge case hardening, regression verification, and end-to-end validation

- [X] T035 Add edge case tests in backend/api/tests.py: test_zero_paid_in_null_ratios, test_overcall_pct_called_above_100, test_xirr_convergence_failure_returns_none, test_negative_plaid_balance_reduces_residual, test_no_commitment_entity_excluded_from_summary, test_distributions_use_allocation_not_ownership_pct
- [X] T036 Verify all existing tests pass with zero regressions (SC-010) by running docker-compose exec backend python manage.py test api -v 2
- [X] T037 Run quickstart.md end-to-end validation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (models must exist for serializers and helpers)
- **US5 (Phase 3)**: Depends on Phase 2 (serializers, URL routes)
- **US1 (Phase 4)**: Depends on Phase 2 (helpers) + Phase 3 (commitment data needed for testing)
- **US4 (Phase 5)**: Depends on Phase 4 (at least one view component must exist to render in tabs)
- **US2 (Phase 6)**: Depends on Phase 2 (_collect_valued_items helper) + Phase 5 (tab container to host view)
- **US3 (Phase 7)**: Depends on Phase 2 (helpers) + Phase 5 (tab container)
- **US6 (Phase 8)**: Depends on Phases 4, 6, 7 (all 3 view generators must exist)
- **Polish (Phase 9)**: Depends on all prior phases

### User Story Dependencies

- **US5 (P1)**: Can start after Foundational — no dependencies on other stories
- **US1 (P1)**: Can start after Foundational — depends on US5 only for manual testing (ORM for automated tests)
- **US4 (P2)**: Depends on US1 (needs at least one view component to render)
- **US2 (P2)**: Can start after Foundational — independent of US1/US5, but needs US4 tab container for frontend
- **US3 (P3)**: Can start after Foundational — independent of US2, but needs US4 tab container for frontend
- **US6 (P3)**: Depends on all view generators (US1, US2, US3 backend functions)

### Within Each User Story

- Backend report function before API endpoint
- API endpoint before frontend component (though [P] frontend tasks can start from contract)
- Core implementation before tests
- Story complete before moving to next priority

### Parallel Opportunities

- T008 and T009 (frontend API clients) can run in parallel with T004–T007 (backend foundational)
- T016 (PortfolioSummary.jsx) can start in parallel with T013–T015 (backend) using API contract
- T019 and T020 (Sidebar/App.jsx) can run in parallel with T018 (Reports.jsx rewrite)
- T023 (AssetClassSummary.jsx) can start in parallel with T021–T022 (backend)
- T027 (InvestmentPerformance.jsx) can start in parallel with T025–T026 (backend)

---

## Parallel Example: User Story 1

```text
# Backend and frontend can proceed in parallel:

# Backend track (sequential):
T013: compute_entity_xirr() in performance.py
T014: generate_portfolio_summary() in reports.py
T015: PortfolioSummaryView in views.py

# Frontend track (parallel with backend, uses API contract):
T016: PortfolioSummary.jsx (mock data → swap to live API when backend ready)

# After both tracks complete:
T017: Tests in tests.py
```

---

## Implementation Strategy

### MVP First (User Stories 5 + 1 Only)

1. Complete Phase 1: Setup (models + migration)
2. Complete Phase 2: Foundational (serializers, helpers, routes, API clients)
3. Complete Phase 3: US5 — Commitment/CapitalCall CRUD
4. Complete Phase 4: US1 — Portfolio Summary
5. **STOP and VALIDATE**: Test Portfolio Summary independently via API (curl)
6. Deploy/demo the MVP — entity rollup table with all PE/VC metrics

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. US5 + US1 → Portfolio Summary works → **MVP!**
3. US4 → Tab navigation → Views accessible from Reports page
4. US2 → Asset Class Summary → Allocation view added
5. US3 → Investment Performance → Per-asset analysis added
6. US6 → Excel Export → All views exportable
7. Polish → Edge cases hardened, regression-free

### Key Technical Notes

- **Decimal everywhere**: All monetary values use Python `Decimal` — no `float` for money
- **XIRR reuse**: `calculate_xirr()` in performance.py is battle-tested (Newton + Brent fallback) — call it directly, don't reimplement
- **_collect_valued_items()**: Single source of truth for Plaid+manual asset valuation with dedup — used by both FMV report and Asset Class Summary
- **Aggregation rule**: Sum raw monetary values across entities, THEN compute ratios (DPI/RVPI/TVPI) — never average per-entity ratios
- **Distribution source**: Always `SUM(DistributionAllocation.amount)` where entity matches — not `Distribution.total_amount × ownership %`
- **IRR pooling**: Entity-level IRR pools all asset cash flows into one list, then calls `calculate_xirr()` once — IRR is non-additive

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks in same phase
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- All API response shapes defined in contracts/portfolio-api.md
- Computed fields (paid_in, pct_called, unfunded) are calculated on-the-fly, never stored
