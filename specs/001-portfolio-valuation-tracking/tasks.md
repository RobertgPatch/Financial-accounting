# Tasks: Portfolio Valuation & Tracking (A1 + A2 + A3)

**Input**: Design documents from `/specs/001-portfolio-valuation-tracking/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Tests**: Included — constitution.md Principle VI mandates model validation tests, API endpoint tests, and critical business logic unit tests. Frontend: manual QA per constitution.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks in this phase)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4, US5)
- Include exact file paths in descriptions

## Path Conventions

- **Backend**: `backend/` (Django 4.2 + DRF)
- **Frontend**: `frontend/src/` (React 19 + Vite 7)
- **Plaid app**: `backend/plaid_integration/` (new Django app)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add new dependencies, create the `plaid_integration` app skeleton, wire configuration.

- [x] T001 Add `plaid-python>=38.0.0,<39.0.0` to backend/requirements.txt
- [x] T002 [P] Install `react-plaid-link` and add to dependencies in frontend/package.json
- [x] T003 [P] Create `plaid_integration` Django app with __init__.py, apps.py, admin.py, models.py, views.py, serializers.py, urls.py, services.py, tests.py, and migrations/__init__.py in backend/plaid_integration/
- [x] T004 Register `plaid_integration` in INSTALLED_APPS in backend/financial_accounting/settings.py
- [x] T005 Add Plaid environment settings (PLAID_CLIENT_ID, PLAID_SECRET, PLAID_ENV) to backend/financial_accounting/settings.py
- [x] T006 Add `path('api/plaid/', include('plaid_integration.urls'))` to backend/financial_accounting/urls.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core model changes and migrations that ALL user stories depend on. Modifies the shared `api` app models.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T007 Add AssetTag model (name, slug, color, created_at) with unique constraints to backend/api/models.py
- [x] T008 Add FMVSnapshot model (asset FK, snapshot_date, value, source, notes) with unique_together on (asset, snapshot_date) to backend/api/models.py
- [x] T009 Expand Asset.asset_type to 9 choices (real_estate, public_equity, private_equity, fixed_income, cash, hedge_fund, crypto, collectible, other) and add tags M2M field to Asset in backend/api/models.py
- [x] T010 Create migration 0003 with AssetTag model, Asset.tags M2M, Asset.asset_type expansion, and data migration mapping property→real_estate, stock→public_equity, fund→hedge_fund, bond→fixed_income in backend/api/migrations/
- [x] T011 Create migration 0004 for FMVSnapshot model with unique_together constraint in backend/api/migrations/
- [x] T012 [P] Update seed_data command to create sample AssetTags and FMVSnapshot records for existing assets in backend/api/management/commands/seed_data.py

**Checkpoint**: Foundation ready — all new models exist, migrations applied, user story implementation can begin.

---

## Phase 3: User Story 1 — Manual FMV Entry & History (Priority: P1) 🎯 MVP

**Goal**: CPA can record, view, edit, and delete FMV snapshots per asset. Asset detail page shows FMV history as a table and line chart with change indicators.

**Independent Test**: Navigate to any asset's detail page on mobile, tap "Record FMV", enter a value and date, save. Verify it appears in the FMV history table and the asset's current value updates.

**Contracts**: [fmv-api.md](contracts/fmv-api.md)

### Implementation for User Story 1

- [x] T013 [P] [US1] Create FMVSnapshotSerializer with validation (value >= 0, date not future, unique asset+date) and extend AssetSerializer with latest_fmv/latest_fmv_date annotations in backend/api/serializers.py
- [x] T014 [P] [US1] Create FMVSnapshotViewSet with list/create/retrieve/update/destroy and filtering by asset, source, date_from, date_to in backend/api/views.py
- [x] T015 [US1] Add fmv_history detail_route action to AssetViewSet returning snapshots with change_amount and change_pct in backend/api/views.py
- [x] T016 [US1] Register fmv-snapshots router and assets/{id}/fmv-history/ URL in backend/api/urls.py
- [x] T017 [P] [US1] Create FMV API client (list, create, update, delete, getAssetHistory) in frontend/src/api/fmv.js
- [x] T018 [US1] Create AssetDetail page with FMV history table (date, value, change, source), line chart (recharts), and add/edit/delete FMV modal — responsive at 320/768/1280px in frontend/src/pages/AssetDetail.jsx
- [x] T019 [US1] Update Assets list page to show current FMV column and link asset name to detail page in frontend/src/pages/Assets.jsx
- [x] T020 [US1] Add `/assets/:id` route to App.jsx in frontend/src/App.jsx
- [x] T021 [US1] Add "Asset Detail" link/navigation pattern to Sidebar (or via Assets page row click) in frontend/src/components/layout/Sidebar.jsx

**Checkpoint**: User Story 1 complete — CPA can record FMV, see history, view charts. MVP deliverable.

---

## Phase 4: User Story 2 — Plaid Account Linking & Balance Sync (Priority: P2)

**Goal**: CPA can link brokerage/bank accounts via Plaid Link, view linked accounts, map them to existing assets, and manually sync balances which are stored as FMV snapshots.

**Independent Test**: Click "Link Account" on the Accounts page, complete Plaid Link flow in sandbox mode (user_good/pass_good), verify accounts appear. Map an account to an asset, click Sync, verify FMV snapshot created.

**Contracts**: [plaid-api.md](contracts/plaid-api.md)

### Implementation for User Story 2

- [x] T022 [P] [US2] Create PlaidItem model (item_id, access_token, institution_name, status, last_synced, error_message) and PlaidAccount model (plaid_item FK, account_id, name, mask, type, subtype, asset FK nullable, current_balance) in backend/plaid_integration/models.py
- [x] T023 [US2] Create migration 0001_initial for PlaidItem and PlaidAccount with FK to api.Asset in backend/plaid_integration/migrations/
- [x] T024 [P] [US2] Implement Plaid API client wrapper with create_link_token, exchange_public_token, get_accounts, get_balances methods using plaid-python SDK in backend/plaid_integration/services.py
- [x] T025 [P] [US2] Create PlaidItemSerializer, PlaidAccountSerializer, ExchangeTokenSerializer, and MapAssetSerializer in backend/plaid_integration/serializers.py
- [x] T026 [US2] Create Plaid views: CreateLinkTokenView, ExchangeTokenView, PlaidItemListView, PlaidItemDeleteView, PlaidAccountListView, SyncBalancesView, MapAssetView — sync creates FMV snapshots via atomic transaction in backend/plaid_integration/views.py
- [x] T027 [US2] Define URL patterns for all Plaid endpoints in backend/plaid_integration/urls.py
- [x] T028 [P] [US2] Create Plaid API client (createLinkToken, exchangeToken, getItems, getAccounts, syncItem, mapAsset, deleteItem) in frontend/src/api/plaid.js
- [x] T029 [P] [US2] Create PlaidLink wrapper component using react-plaid-link with onSuccess/onError callbacks, responsive modal in frontend/src/components/plaid/PlaidLink.jsx
- [x] T030 [US2] Create Accounts page with linked institutions list, accounts table with asset mapping dropdown, sync button, re-link button, and PlaidLink trigger — responsive at 320/768/1280px in frontend/src/pages/Accounts.jsx
- [x] T031 [US2] Add `/accounts` route to App.jsx and "Accounts" link to Sidebar navigation in frontend/src/App.jsx and frontend/src/components/layout/Sidebar.jsx

**Checkpoint**: User Story 2 complete — CPA can link Plaid accounts, map to assets, sync balances as FMV snapshots.

---

## Phase 5: User Story 3 — Asset Classification & Tagging (Priority: P3)

**Goal**: CPA can assign expanded asset types and custom tags to assets, then filter the asset list by type and tag. Dashboard shows portfolio-by-class allocation.

**Independent Test**: Edit an asset, select "Private Equity" type, add tags "illiquid" and "domestic". Go to Assets page, filter by tag "illiquid" — only tagged assets appear.

**Contracts**: [classification-api.md](contracts/classification-api.md)

### Implementation for User Story 3

- [x] T032 [P] [US3] Create AssetTagSerializer with assets_count annotation and extend AssetSerializer with nested tags and asset_type_display in backend/api/serializers.py
- [x] T033 [P] [US3] Create AssetTagViewSet with list/create/partial_update/destroy in backend/api/views.py
- [x] T034 [US3] Add set_tags action to AssetViewSet (POST /api/assets/{id}/tags/ — set semantics) in backend/api/views.py
- [x] T035 [US3] Add filtering to AssetViewSet: by asset_type, tag slug (multi-value), has_fmv, plaid_linked in backend/api/views.py
- [x] T036 [US3] Register tags router and assets/{id}/tags/ URL in backend/api/urls.py
- [x] T037 [P] [US3] Create reusable TagInput component with chip display, add input, color dots, and autocomplete — responsive in frontend/src/components/ui/TagInput.jsx
- [x] T038 [US3] Add tag management (TagInput) and asset_type selector to asset create/edit form in frontend/src/pages/Assets.jsx
- [x] T039 [US3] Add filter bar with asset_type dropdown and tag multi-select to Assets list page — responsive at 320/768/1280px in frontend/src/pages/Assets.jsx

**Checkpoint**: User Story 3 complete — CPA can classify assets with types and tags, and filter the asset list.

---

## Phase 6: User Story 4 — Performance & Return Tracking (Priority: P4)

**Goal**: CPA can view TWR and IRR per asset (for multiple periods) and per entity (ownership-weighted aggregate). Performance summary available for dashboard.

**Independent Test**: View an asset that has 4+ FMV snapshots and 2+ distributions. Verify the detail page shows TWR and IRR values for YTD, 1Y, since inception. Navigate to entity detail, verify aggregate performance.

**Contracts**: [performance-api.md](contracts/performance-api.md) | **Research**: [research.md](research.md) (TWR/IRR formulas)

### Implementation for User Story 4

- [X] T040 [P] [US4] Implement TWR calculation (sub-period geometric linking with external cash flow handling) as pure Python function in backend/api/performance.py
- [X] T041 [US4] Implement IRR/XIRR calculation (Newton's method, 100 max iterations, null on non-convergence) in backend/api/performance.py
- [X] T042 [US4] Implement period date resolver (ytd, 1y, 3y, 5y, since_inception, custom) utility in backend/api/performance.py
- [X] T043 [US4] Create asset_performance view (GET /api/assets/{id}/performance/) returning metrics, fmv_series, data_quality in backend/api/views.py
- [X] T044 [US4] Create entity_performance view (GET /api/entities/{id}/performance/) with ownership-weighted aggregation in backend/api/views.py
- [X] T045 [US4] Create performance_summary view (GET /api/performance/summary/) with total_portfolio, by_asset_type, top/bottom performers in backend/api/views.py
- [X] T046 [US4] Register performance endpoint URLs in backend/api/urls.py
- [X] T047 [P] [US4] Create performance API client (getAssetPerformance, getEntityPerformance, getSummary) in frontend/src/api/performance.js
- [X] T048 [US4] Add performance metrics section (TWR/IRR cards, period selector) to AssetDetail page in frontend/src/pages/AssetDetail.jsx
- [X] T049 [US4] Create EntityDetail page with aggregate performance metrics, asset breakdown table, and performance chart — responsive at 320/768/1280px in frontend/src/pages/EntityDetail.jsx
- [X] T050 [US4] Add `/entities/:id` route to App.jsx and entity name links on Entities page in frontend/src/App.jsx and frontend/src/pages/Entities.jsx

**Checkpoint**: User Story 4 complete — CPA can view TWR/IRR per asset and per entity portfolio.

---

## Phase 7: User Story 5 — Consolidated Net Worth Dashboard (Priority: P5)

**Goal**: Dashboard shows net worth per principal and consolidated, with portfolio allocation by asset class (pie/donut chart). Filterable by entity.

**Independent Test**: Navigate to Dashboard, see "Net Worth" section showing per-principal totals and consolidated total, with portfolio-by-class donut chart.

**Contracts**: [classification-api.md](contracts/classification-api.md) (portfolio-by-class endpoint) | [performance-api.md](contracts/performance-api.md) (performance summary)

### Implementation for User Story 5

- [X] T051 [P] [US5] Create portfolio_by_class report view (GET /api/reports/portfolio-by-class/) with entity/tag filtering in backend/api/reports.py
- [X] T052 [US5] Extend dashboard_summary view to include net_worth_by_entity and consolidated_net_worth data in backend/api/views.py
- [X] T053 [US5] Register portfolio-by-class report URL in backend/api/urls.py
- [X] T054 [US5] Add Net Worth KPI cards (per-principal + consolidated) to Dashboard page in frontend/src/pages/Dashboard.jsx
- [X] T055 [US5] Add Portfolio by Class donut chart (recharts PieChart) with entity filter to Dashboard page in frontend/src/pages/Dashboard.jsx
- [X] T056 [US5] Ensure Dashboard layout is responsive — two-column on tablet (one per principal), single-column stacked on mobile in frontend/src/pages/Dashboard.jsx

**Checkpoint**: User Story 5 complete — full net worth dashboard with allocation views. All user stories independently functional.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Tests (constitution Principle VI), responsive validation, documentation, cleanup.

### Backend Tests

- [X] T057 [P] Write model validation tests for FMVSnapshot (value >= 0, no future dates, unique constraint) and AssetTag (slug auto-gen, color regex, unique name) in backend/api/tests.py
- [X] T058 [P] Write API endpoint tests for FMV CRUD (status codes, response shape, filtering) in backend/api/tests.py
- [X] T059 [P] Write API endpoint tests for Tags CRUD and asset tag assignment in backend/api/tests.py
- [X] T060 [P] Write unit tests for TWR and IRR calculations including edge cases (insufficient data, zero values, non-convergence) in backend/api/tests.py
- [X] T061 [P] Write API endpoint tests for performance endpoints (asset, entity, summary) in backend/api/tests.py
- [X] T062 [P] Write tests for Plaid views with mocked plaid-python client (create-link-token, exchange, sync, map-asset) in backend/plaid_integration/tests.py
- [X] T063 [P] Write API endpoint tests for portfolio-by-class report and dashboard net worth in backend/api/tests.py

### Cross-Cutting

- [X] T064 Verify all new pages are responsive at 320px, 768px, and 1280px breakpoints — fix any overflow or touch issues
- [X] T065 Run quickstart.md validation end-to-end (Docker build, migrate, seed, verify all endpoints return expected shapes)
- [X] T066 Code cleanup: remove unused imports, add docstrings to performance.py functions, verify consistent error response format across all new endpoints

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 completion — **BLOCKS all user stories**
- **US1 (Phase 3)**: Depends on Phase 2 — first MVP increment
- **US2 (Phase 4)**: Depends on Phase 2 — can run in parallel with US1 (creates FMV snapshots via Plaid, model exists from Phase 2)
- **US3 (Phase 5)**: Depends on Phase 2 — can run in parallel with US1 and US2 (AssetTag model exists from Phase 2)
- **US4 (Phase 6)**: Depends on Phase 2 — benefits from US1 being complete (needs FMV data to test meaningfully)
- **US5 (Phase 7)**: Depends on Phase 2 + US1 (needs FMV data) + US3 (needs classification for portfolio-by-class)
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

```
Phase 1 (Setup)
    │
    ▼
Phase 2 (Foundational) ─── BLOCKS ALL ───┐
    │                                      │
    ▼                                      ▼
┌─────────┐  ┌─────────┐  ┌─────────┐    │
│ US1 (P1)│  │ US2 (P2)│  │ US3 (P3)│    │
│ FMV     │  │ Plaid   │  │ Tags    │    │
└────┬────┘  └─────────┘  └────┬────┘    │
     │                          │         │
     ▼                          ▼         │
┌─────────┐              ┌─────────┐     │
│ US4 (P4)│◄─────────────│ US5 (P5)│     │
│ Perf    │              │ NetWorth│     │
└─────────┘              └─────────┘     │
                               │         │
                               ▼         │
                         Phase 8 (Polish)│
```

- **US1 → US4**: US4 benefits from FMV history test data created by US1
- **US1 + US3 → US5**: US5 needs FMV data and classification for net worth + allocation views
- **US2** is fully independent after Foundational (creates its own FMV snapshots via Plaid sync)
- **US3** is fully independent after Foundational (AssetTag model exists from Phase 2)

### Within Each User Story

- Backend serializers and API clients can be parallel (different files)
- Views depend on serializers being defined
- URL registration depends on views being defined
- Frontend pages depend on API clients being defined
- Route/navigation updates depend on pages being created

---

## Parallel Opportunities

### Phase 1 (Setup)

```
┌──────────────────────────┐
│ T001 requirements.txt    │  ← sequential (same concern)
│ T002 package.json        │  [P] different file
│ T003 plaid_integration/  │  [P] new directory
│ T004 settings.py         │  ← after T003
│ T005 settings.py         │  ← after T004 (same file)
│ T006 urls.py             │  ← after T003
└──────────────────────────┘
Parallel group: {T001, T002, T003} → then {T004, T005, T006}
```

### Phase 3 (User Story 1) — Example

```
Parallel group 1 (backend + frontend API):
  T013 serializers.py  ─┐
  T014 views.py         ├─ all different files, no interdependency
  T017 fmv.js           ─┘

Sequential after group 1:
  T015 views.py (depends on T014 — same file, adds action)
  T016 urls.py (depends on T014 — needs viewset defined)
  T018 AssetDetail.jsx (depends on T017 — needs API client)
  T019 Assets.jsx (depends on T013 — needs serializer response)
  T020 App.jsx (depends on T018 — needs page component)
  T021 Sidebar.jsx (depends on T020 — navigation)
```

### Cross-Story Parallelism (after Phase 2)

```
Developer A: US1 (T013-T021)     ─── can start immediately
Developer B: US2 (T022-T031)     ─── can start immediately
Developer C: US3 (T032-T039)     ─── can start immediately
                                      ↓ after US1 done
Developer A: US4 (T040-T050)     ─── benefits from US1 data
                                      ↓ after US1 + US3 done
Developer B: US5 (T051-T056)     ─── needs FMV + classification
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T006)
2. Complete Phase 2: Foundational (T007–T012)
3. Complete Phase 3: User Story 1 (T013–T021)
4. **STOP and VALIDATE**: Record FMV → view history → chart → mobile responsive
5. Deploy/demo — CPA can manually track asset values

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. **Add US1** → FMV tracking works → Deploy (MVP!)
3. **Add US3** → Tags and classification → Deploy (quick win, no external deps)
4. **Add US2** → Plaid linking → Deploy (automates liquid asset tracking)
5. **Add US4** → TWR/IRR metrics → Deploy (high-value insight)
6. **Add US5** → Net worth dashboard → Deploy (capstone view)
7. Polish → Tests, responsive QA, cleanup

### Suggested MVP Scope

**User Story 1 only** (T001–T021, 21 tasks). Delivers the core FMV data layer that all other stories build upon. CPA can immediately start recording asset valuations.

---

## Notes

- All monetary values use `DecimalField(15, 2)` — never `FloatField`
- All FMV write operations wrapped in `@transaction.atomic`
- Plaid tokens: plain storage in dev/sandbox; encrypt at rest in production (future concern)
- TWR/IRR: pure Python (no numpy-financial) — Newton's method XIRR per research.md
- Frontend responsive: Tailwind `sm:`, `md:`, `lg:` breakpoints — test at 320px, 768px, 1280px
- Commit after each task or logical group
- Each user story checkpoint = independently testable and deployable increment
