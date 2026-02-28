# Feature Specification: Portfolio Valuation & Tracking (A1 + A2 + A3)

**Feature Branch**: `001-portfolio-valuation-tracking`  
**Created**: 2026-02-28  
**Status**: Draft  
**Input**: User description: "FMV tracker with Plaid integration, performance & return tracking (TWR/IRR), and asset classification with tagging. Two wealthy principals. CPA-managed family office. Mobile/tablet responsive."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Manual FMV Entry & History (Priority: P1)

As a CPA, I need to record the fair market value of each asset at a point in time so I can track net worth across illiquid holdings (real estate, private equity, art) that cannot be auto-pulled from Plaid. I want to see a historical timeline of FMV snapshots per asset, with change indicators.

**Why this priority**: FMV tracking is the foundational data layer — performance calculations, net worth dashboards, and Plaid enrichment all depend on FMV records existing first.

**Independent Test**: Navigate to any asset's detail page on mobile, tap "Record FMV", enter a value and date, save. Verify it appears in the FMV history table and the asset's current value updates.

**Acceptance Scenarios**:

1. **Given** an existing asset with no FMV records, **When** user adds an FMV snapshot ($1,500,000, 2026-01-01), **Then** the asset detail shows current value = $1,500,000 and FMV history has one row.
2. **Given** an asset with 3 FMV snapshots, **When** user views the asset detail page, **Then** a timeline/chart shows value over time with absolute and percentage change between snapshots.
3. **Given** an asset with FMV records, **When** user edits or deletes a historical FMV entry, **Then** the timeline updates and the current value reflects the most recent remaining snapshot.
4. **Given** a mobile viewport (375px), **When** user views FMV history, **Then** the table is horizontally scrollable or stacks into cards and all actions are touch-accessible.

---

### User Story 2 - Plaid Account Linking & Balance Sync (Priority: P2)

As a CPA, I need to link brokerage and bank accounts via Plaid so that balances and holdings are automatically pulled and stored as FMV snapshots without manual data entry for liquid assets.

**Why this priority**: Automates the tedious manual balance entry for liquid accounts (banks, brokerages). Depends on FMV data model from P1.

**Independent Test**: Click "Link Account" on the Accounts page, complete Plaid Link flow in sandbox mode, verify account balances appear as FMV snapshots on the linked asset.

**Acceptance Scenarios**:

1. **Given** user is on the Accounts page, **When** they click "Link Account", **Then** the Plaid Link modal opens (sandbox mode in dev) and they can select an institution and authenticate.
2. **Given** a Plaid link is established, **When** the system syncs, **Then** each account's balance is stored as an FMV snapshot on the corresponding asset (auto-created if needed).
3. **Given** linked accounts exist, **When** user views the dashboard, **Then** linked account balances are marked with a "🔗 Plaid" badge and show last-synced timestamp.
4. **Given** a Plaid token expires or errors, **When** the system attempts sync, **Then** the user sees a clear error state with a "Re-link" button.
5. **Given** a tablet viewport (768px), **When** user completes Plaid Link, **Then** the modal is properly sized and the callback handles correctly.

---

### User Story 3 - Asset Classification & Tagging (Priority: P3)

As a CPA, I need to classify assets with richer types and apply custom tags (liquid/illiquid, tax-advantaged/taxable, geography, sector) so I can filter and group the portfolio in multiple dimensions — like Addepar's analysis views.

**Why this priority**: Enables the "slice and dice" portfolio views. Foundation for filtered reporting. Low data-model risk.

**Independent Test**: Edit an asset, select asset class "Private Equity", add tags "illiquid", "domestic". Go to Assets page, filter by tag "illiquid" — only tagged assets appear.

**Acceptance Scenarios**:

1. **Given** an existing asset, **When** user edits it, **Then** they can select from expanded asset types (real_estate, private_equity, public_equity, fixed_income, cash, crypto, collectible, other) and add/remove tags.
2. **Given** assets have tags, **When** user is on the Assets list page, **Then** they can filter by tag and asset class using a filter bar (responsive on mobile).
3. **Given** assets have classifications, **When** user views the Dashboard, **Then** a new "Portfolio by Class" pie chart shows allocation by asset class weighted by current FMV.
4. **Given** a mobile viewport, **When** user manages tags on an asset, **Then** tags render as tappable chips with an add input that doesn't overflow the screen.

---

### User Story 4 - Performance & Return Tracking (Priority: P4)

As a CPA managing two principals' wealth, I need to see Time-Weighted Return (TWR) and Internal Rate of Return (IRR) per asset and per entity portfolio so I can report investment performance to each principal.

**Why this priority**: High-value insight but depends on FMV history (P1) and distributions already existing. Computationally more complex.

**Independent Test**: View an asset that has 4+ FMV snapshots and 2+ distributions. Verify the detail page shows TWR and IRR values. Navigate to an entity's portfolio view and verify aggregate TWR/IRR.

**Acceptance Scenarios**:

1. **Given** an asset with FMV history and distributions, **When** user views asset detail, **Then** TWR and IRR are displayed for 1Y, 3Y, YTD, and since-inception periods.
2. **Given** an entity that owns multiple assets, **When** user views entity detail, **Then** aggregate portfolio TWR and IRR are shown, weighted by ownership percentage.
3. **Given** a performance period with no FMV data points, **When** system calculates returns, **Then** it shows "Insufficient data" instead of misleading numbers.
4. **Given** a mobile viewport, **When** user views performance metrics, **Then** the performance cards stack vertically and are readable without horizontal scrolling.

---

### User Story 5 - Consolidated Net Worth Dashboard (Priority: P5)

As a CPA, I need a net worth view per principal (and consolidated) that sums current FMV across all assets weighted by ownership percentage, broken down by asset class and tag dimensions.

**Why this priority**: The capstone view that ties everything together. Depends on FMV data, ownership, and classification all being in place.

**Independent Test**: Navigate to Dashboard, see "Net Worth" section showing per-principal totals and consolidated total, with breakdowns by asset class.

**Acceptance Scenarios**:

1. **Given** assets have current FMV and ownership records, **When** user views the Dashboard, **Then** a "Net Worth" card shows each principal's total (entity-filtered) and a consolidated total.
2. **Given** the net worth section, **When** user taps a principal's name, **Then** a breakdown by asset class is shown (pie chart + table).
3. **Given** a tablet viewport, **When** user views the net worth dashboard, **Then** the layout is two-column (one per principal) and switches to single-column stacked on mobile.

---

### Edge Cases

- What happens when an asset has zero FMV records? → Show "No valuation data" placeholder, not $0.
- What happens when Plaid Link fails mid-flow? → Graceful error, no orphan records, retry possible.
- What happens when an asset has FMV records but no distributions? → TWR/IRR should still compute based on value changes alone (capital appreciation).
- What happens when ownership percentages don't sum to 100%? → System should warn but not block.
- What happens when a Plaid-linked account is deleted? → FMV snapshots remain (they're historical records), Plaid link is severed.
- What happens when tags contain special characters? → Sanitize to alphanumeric + hyphens, case-insensitive.

## Requirements *(mandatory)*

### Functional Requirements

**A1 — Fair Market Value Tracker with Plaid**
- **FR-001**: System MUST allow manual FMV snapshot creation per asset (value, date, source, notes).
- **FR-002**: System MUST display FMV history as a sortable table and a line chart per asset.
- **FR-003**: System MUST store Plaid access tokens securely and sync account balances as FMV snapshots.
- **FR-004**: System MUST support Plaid Link flow (sandbox in dev, production when API key is configured).
- **FR-005**: System MUST auto-create assets for new Plaid accounts or allow mapping to existing assets.
- **FR-006**: System MUST show "last synced" timestamp and sync status per linked account.
- **FR-007**: System MUST allow manual re-sync and re-link for expired Plaid tokens.

**A2 — Performance & Return Tracking**
- **FR-008**: System MUST compute Time-Weighted Return (TWR) per asset given FMV snapshots and cash flows.
- **FR-009**: System MUST compute Internal Rate of Return (IRR) per asset given FMV snapshots and cash flows.
- **FR-010**: System MUST display TWR/IRR for periods: YTD, 1Y, 3Y, Since Inception.
- **FR-011**: System MUST aggregate TWR/IRR at entity level weighted by ownership percentage.
- **FR-012**: System MUST show "Insufficient data" when fewer than 2 FMV data points exist.

**A3 — Asset Classification & Tagging**
- **FR-013**: System MUST expand asset types to: real_estate, private_equity, public_equity, fixed_income, cash, hedge_fund, crypto, collectible, other.
- **FR-014**: System MUST support arbitrary user-defined tags on assets (many-to-many).
- **FR-015**: System MUST allow filtering assets by asset class and/or tags on the Assets list page.
- **FR-016**: System MUST show a "Portfolio by Class" breakdown on the Dashboard weighted by current FMV.

**Cross-cutting**
- **FR-017**: All new UI MUST be responsive at 320px (mobile), 768px (tablet), 1280px+ (desktop).
- **FR-018**: All new API endpoints MUST return JSON via DRF and follow existing REST conventions.

### Key Entities

- **FMVSnapshot**: Point-in-time fair market value for an asset (asset, date, value, source [manual/plaid], notes).
- **PlaidItem**: A linked Plaid institution (access_token, item_id, institution_name, status, last_synced).
- **PlaidAccount**: An account within a PlaidItem (account_id, name, type, subtype, linked asset FK).
- **AssetTag**: A tag that can be applied to assets (name, slug). Many-to-many with Asset.
- **Asset (extended)**: Expanded asset_type choices, M2M to AssetTag, computed current_fmv property.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: CPA can record an FMV snapshot and see it reflected in net worth within 3 clicks / 10 seconds.
- **SC-002**: Plaid-linked accounts auto-sync balances and display on dashboard without manual entry.
- **SC-003**: TWR and IRR values are computed within 2 seconds for any asset with up to 1,000 FMV snapshots.
- **SC-004**: All pages are fully usable at 375px width (iPhone SE) — no horizontal scroll, all CTAs accessible.
- **SC-005**: Asset filtering by class and tag returns results in < 500ms with up to 500 assets.
- **SC-006**: Dashboard "Portfolio by Class" chart accurately reflects current FMV × ownership percentage.
