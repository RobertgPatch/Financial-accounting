# Feature Specification: Portfolio Tracker Redesign

**Feature Branch**: `003-portfolio-tracker-redesign`  
**Created**: 2026-03-04  
**Status**: Draft  
**Input**: User description: "Complete redesign where I display the data in a views tab, views are configurable but the defaults will be 'Asset Class Summary', 'Portfolio Summary' and 'Investment Performance'. This is no longer a distribution report generator — it's an asset and performance tracker. Use the CSV to dictate the model supporting PE/VC commitment tracking with entity rollups, DPI/RVPI/TVPI/IRR metrics."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Portfolio Summary View (Priority: P1)

As an investor, I want to see a Portfolio Summary view that rolls up all my investments by entity, showing Original Commitment, % Called, Unfunded Commitment, Paid-In, Distributions, Residual Value, DPI, RVPI, TVPI, and IRR (XIRR) — so I can assess each entity's overall fund performance at a glance.

**Why this priority**: This is the core data model from the CSV. It defines the commitment-tracking schema that all other views depend on. Without entity-level rollups and PE/VC metrics, the other views have no data to display.

**Independent Test**: Can be fully tested by creating an entity with commitment records and capital-call/distribution transactions, then navigating to the Portfolio Summary view to confirm all columns render with correct calculated values and an "All Entities" total row.

**Acceptance Scenarios**:

1. **Given** an entity with a $1,000,000 original commitment that is 100% called, has received $2,000,000 in distributions, and has $0 residual value, **When** I open the Portfolio Summary view, **Then** I see a row for that entity showing: Original Commitment = $1,000,000, % Called = 100%, Unfunded = $0, Paid-In = $1,000,000, Distributions = $2,000,000, Residual = $0, DPI = 2.00, RVPI = 0.00, TVPI = 2.00.
2. **Given** multiple entities with varying commitment and call data, **When** I open the Portfolio Summary view, **Then** I see an "All Entities" summary row that sums Original Commitment, Paid-In, Distributions, and Residual across all entities, and computes aggregate DPI, RVPI, and TVPI.
3. **Given** an entity with no commitments or transactions, **When** I open the Portfolio Summary view, **Then** that entity's row shows $0 for all monetary columns, "—" for % Called (division by zero), and "—" for ratio columns (DPI, RVPI, TVPI, IRR).
4. **Given** an entity with partial capital calls (e.g., 60% called), **When** I open the view, **Then** Unfunded Commitment = Original Commitment × (1 − % Called), and Paid-In = sum of all capital calls for that entity.

---

### User Story 2 — Asset Class Summary View (Priority: P2)

As an investor, I want to see an Asset Class Summary view that groups my portfolio by asset type (Real Estate, Private Equity, Public Equity, Cash, Fixed Income, etc.), showing the total value, percentage of portfolio, and item count per class — so I can understand my allocation and diversification.

**Why this priority**: Asset class breakdown is the most common portfolio analysis view. It builds on the valuation data established in P1 and provides the allocation perspective investors check most frequently.

**Independent Test**: Can be tested by creating assets across multiple asset types with FMV snapshots and/or Plaid account balances, then opening Asset Class Summary to verify each type shows correct total value, percentage of total portfolio, and item count with a pie/bar chart visualization.

**Acceptance Scenarios**:

1. **Given** assets across 3 asset types (Real Estate: $500K, Private Equity: $300K, Cash: $200K), **When** I open Asset Class Summary, **Then** I see three rows showing values and percentages (50%, 30%, 20%) with a total of $1,000,000.
2. **Given** both Plaid-linked accounts and manual assets with FMV snapshots, **When** I open Asset Class Summary, **Then** both sources are included in the totals without double-counting.
3. **Given** the view is open, **When** I look at the visualization, **Then** I see a pie chart showing allocation by asset class with each class color-coded.
4. **Given** no assets exist in the system, **When** I open Asset Class Summary, **Then** I see an empty state message indicating no assets have been added yet.

---

### User Story 3 — Investment Performance View (Priority: P3)

As an investor, I want to see an Investment Performance view that shows asset-level and entity-level returns including IRR (XIRR), DPI, RVPI, and TVPI, with the ability to filter by entity and time period — so I can evaluate which investments are performing well.

**Why this priority**: Performance analysis is the deepest analytical view. It depends on the data model from P1 and enriches it with time-series calculations.

**Independent Test**: Can be tested by creating an entity with commitment, capital call, and distribution records spanning multiple dates, then opening the Investment Performance view and verifying the IRR, DPI, RVPI, and TVPI calculations match expected values.

**Acceptance Scenarios**:

1. **Given** an asset with capital calls on specific dates and distributions on later dates, **When** I open Investment Performance, **Then** I see an IRR (XIRR) value calculated from the dated cash flows.
2. **Given** multiple assets owned by an entity, **When** I filter by that entity, **Then** I see aggregated performance metrics for only that entity's holdings.
3. **Given** an asset with $1M paid-in and $2M in distributions, **When** I view its performance, **Then** DPI = 2.00, and if residual value is $0 then TVPI = 2.00.
4. **Given** the view is open, **When** I select a valuation date, **Then** all residual values and metrics are computed as of that date.
5. **Given** an asset with insufficient cash flow data for IRR calculation, **When** I view its performance, **Then** IRR shows "N/A" rather than an error.

---

### User Story 4 — Configurable View Tabs (Priority: P2)

As an investor, I want to switch between views (Asset Class Summary, Portfolio Summary, Investment Performance) using tabs on the Reports page, and have my last-selected view remembered — so I can quickly navigate between different perspectives of my portfolio.

**Why this priority**: The view-switching mechanism is the UI foundation for all three views. Without it, users can't access the different perspectives.

**Independent Test**: Can be tested by navigating to the Reports page, clicking each tab, and verifying the correct view loads. Refreshing the page should retain the last-selected tab.

**Acceptance Scenarios**:

1. **Given** I am on the Reports page, **When** I see the tab bar, **Then** I see three tabs: "Asset Class Summary", "Portfolio Summary", "Investment Performance" with "Portfolio Summary" selected by default.
2. **Given** I am viewing Portfolio Summary, **When** I click "Asset Class Summary" tab, **Then** the view switches to the Asset Class Summary content.
3. **Given** I selected "Investment Performance" and refresh the browser, **When** the page reloads, **Then** "Investment Performance" is still the selected tab.
4. **Given** I am on any view tab, **When** I observe the layout, **Then** the old distribution report selector is no longer present — Reports is now the portfolio tracker.

---

### User Story 5 — Commitment & Capital Call Tracking (Priority: P1)

As an investor, I want to record original commitments, capital calls, and residual values for my investments — so that the Portfolio Summary and Performance views can compute % Called, Unfunded Commitment, DPI, RVPI, and TVPI automatically.

**Why this priority**: This is the data-entry prerequisite for the Portfolio Summary (US1). Without commitment and capital-call records, the PE/VC metrics cannot be calculated.

**Independent Test**: Can be tested by creating a commitment record for an entity/asset, recording capital calls against it, and verifying the system correctly computes Paid-In, % Called, and Unfunded Commitment.

**Acceptance Scenarios**:

1. **Given** I create a commitment of $1,000,000 for Entity #1 on Asset A, **When** I view the commitment, **Then** I see Original Commitment = $1,000,000, % Called = 0%, Unfunded = $1,000,000.
2. **Given** a commitment exists, **When** I record a capital call of $600,000, **Then** % Called updates to 60%, Unfunded updates to $400,000, and Paid-In = $600,000.
3. **Given** multiple capital calls totaling the full commitment, **When** I view the commitment, **Then** % Called = 100% and Unfunded = $0.
4. **Given** I update the residual value (current NAV) of the investment, **When** I view Portfolio Summary, **Then** RVPI = Residual ÷ Paid-In is correctly shown.
5. **Given** an entity has commitments across multiple assets, **When** I view Portfolio Summary, **Then** the entity row aggregates all commitments, calls, distributions, and residuals.

---

### User Story 6 — Excel Export for Each View (Priority: P3)

As an investor, I want to export any of the three views (Asset Class Summary, Portfolio Summary, Investment Performance) to Excel — so I can share reports with advisors or archive them.

**Why this priority**: Export is a polish feature that adds distribution value but isn't needed for the core analysis workflow.

**Independent Test**: Can be tested by generating each view with data, clicking Export, and verifying the downloaded .xlsx file contains the correct headers and values matching what's displayed on screen.

**Acceptance Scenarios**:

1. **Given** I am viewing Portfolio Summary with data, **When** I click Export, **Then** an Excel file downloads with entity rows, all columns from the view, and an "All Entities" total row.
2. **Given** I am viewing Asset Class Summary, **When** I click Export, **Then** the Excel file contains a sheet with asset class breakdown matching the on-screen data.
3. **Given** I am viewing Investment Performance, **When** I click Export, **Then** the Excel file contains performance metrics per asset/entity.

---

### Edge Cases

- What happens when an entity has distributions exceeding paid-in capital? DPI > 1.0 is valid and should display normally.
- How does the system handle a commitment with zero paid-in? % Called = 0%, and DPI/RVPI/TVPI should show "—" (division by zero guarded).
- What happens when XIRR calculation fails to converge? Display "N/A" for IRR.
- How are Plaid accounts handled in Portfolio Summary? Plaid balances feed into the Residual Value column for the mapped asset's entity. They do not have commitments unless manually entered.
- What happens when an asset has no entity ownership? It appears in Asset Class Summary but not in Portfolio Summary (which is entity-scoped).
- How are negative balances handled? Credit card / loan balances are negative and reduce totals.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support recording an Original Commitment amount for an entity's investment in an asset, along with a commitment date.
- **FR-002**: System MUST support recording Capital Calls against a commitment, each with a date and amount, to track Paid-In capital.
- **FR-003**: System MUST compute % Called as (total capital calls ÷ original commitment × 100) and Unfunded Commitment as (original commitment − total capital calls).
- **FR-004**: System MUST compute Residual Value for an investment from the latest FMV snapshot or Plaid account balance (using the same logic as the existing FMV report).
- **FR-005**: System MUST compute DPI (Distributions to Paid-In) as total distributions ÷ total paid-in for each entity.
- **FR-006**: System MUST compute RVPI (Residual Value to Paid-In) as residual value ÷ total paid-in for each entity.
- **FR-007**: System MUST compute TVPI (Total Value to Paid-In) as (distributions + residual) ÷ total paid-in for each entity.
- **FR-008**: System MUST compute IRR (XIRR) from dated cash flows (capital calls as negative, distributions as positive, residual as terminal positive value).
- **FR-009**: System MUST aggregate all entity-level metrics into an "All Entities" summary row in the Portfolio Summary view.
- **FR-010**: System MUST provide an Asset Class Summary view that groups all valued items by asset type, showing total value, percentage of portfolio, and count per class.
- **FR-011**: System MUST provide an Investment Performance view showing per-asset and per-entity IRR, DPI, RVPI, and TVPI with entity and time-period filters.
- **FR-012**: System MUST display three tabs on the Reports page: "Asset Class Summary", "Portfolio Summary", and "Investment Performance".
- **FR-013**: System MUST remember the user's last-selected tab across page refreshes (using browser local storage).
- **FR-014**: System MUST replace the existing distribution report selector with the new three-tab view system. The old distribution report content is removed from the Reports page.
- **FR-015**: System MUST guard against division by zero — when Paid-In is zero, DPI, RVPI, and TVPI display as "—" (dash); when Original Commitment is zero, % Called displays as "—" (dash) while Unfunded displays as "$0.00".
- **FR-016**: System MUST handle XIRR convergence failures gracefully, displaying "N/A" for IRR.
- **FR-017**: System MUST support Excel export for each of the three views, producing an .xlsx file with headers and data matching the on-screen display.
- **FR-018**: System MUST use Decimal precision for all monetary values and ratios (no floating-point).
- **FR-019**: System MUST include Plaid account balances in Residual Value computation without requiring separate commitment records (Plaid accounts with no commitment show balance only in Asset Class Summary).
- **FR-020**: System MUST prevent double-counting between Plaid-linked accounts and manual assets that map to the same underlying account (existing FMV report logic).

### Key Entities

- **Commitment**: Represents an entity's original commitment to an asset/fund. Key attributes: entity, asset, commitment_date, original_amount, notes. One commitment per entity-asset pair.
- **CapitalCall**: Represents a draw-down against a commitment. Key attributes: commitment (FK), call_date, amount, notes. Multiple calls per commitment over time.
- **Entity**: (Existing) The investment entity — individual, LLC, trust, etc. Enhanced with rollup calculations.
- **Asset**: (Existing) The investment — real estate, PE fund, public equity, etc. No structural changes.
- **Distribution**: (Existing) Cash returned from an asset. Already tracks per-asset distributions with entity allocations.
- **FMVSnapshot**: (Existing) Point-in-time valuations. Used for Residual Value in PE metrics.
- **PlaidAccount**: (Existing) Linked bank/brokerage accounts. Balances feed into Residual Value and Asset Class Summary.
- **View Configuration**: User's selected tab, persisted in browser local storage. No backend storage needed.

## Clarifications

### Session 2026-03-04

- Q: Should zero-value ratios (e.g., RVPI = 0.00 when residual is $0 but paid-in > 0) display as "0.00" or "—"? → A: Display "0.00". The CSV dash is a spreadsheet number format artifact, not an intentional UX decision. Dashes are reserved for incalculable ratios (paid-in = 0).
- Q: How should % Called and Unfunded display when original commitment is $0? → A: "—" for % Called (division by zero), "$0.00" for Unfunded (mathematically valid). Matches API contract's pct_called: null.

## Assumptions

- The existing Distribution model and DistributionAllocation model remain unchanged and continue to provide distribution data for DPI calculations.
- The existing FMVSnapshot and Plaid integration remain the sources for Residual Value (current NAV). No new valuation source is introduced.
- The Portfolio Summary "Valuation Year" referenced in the CSV header defaults to the current year. A date/period picker may be added but is not mandatory for the initial release.
- XIRR calculation reuses the existing XIRR logic in the performance module (backend/api/performance.py).
- The "Residual Used" column in the CSV maps to the latest FMV snapshot or Plaid balance for the entity's owned assets, pro-rated by ownership percentage.
- Entity types (individual, company, LLC, trust, partnership, other) remain unchanged.
- All monetary values use 2-decimal-place display and Decimal storage.
- The old Distribution Report view content is removed from the Reports page entirely as part of the redesign.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can view a Portfolio Summary with entity rollups showing all 10 CSV columns (Original Commitment through IRR) within 3 seconds of page load.
- **SC-002**: Users can switch between the three views (Asset Class Summary, Portfolio Summary, Investment Performance) in under 1 second via tab selection.
- **SC-003**: Portfolio Summary "All Entities" row totals match the sum of individual entity rows for all monetary columns, with DPI/RVPI/TVPI recomputed from aggregated totals.
- **SC-004**: Given the CSV sample data ($1M commitment, 100% called, $2M distributions, $0 residual), the system produces DPI = 2.00, RVPI = 0.00, TVPI = 2.00 exactly.
- **SC-005**: XIRR calculation produces results consistent with Excel's XIRR function to within 0.01% tolerance.
- **SC-006**: Asset Class Summary shows correct percentage allocation totaling 100% across all classes.
- **SC-007**: Excel exports for each view produce valid .xlsx files with correct headers and data within 5 seconds.
- **SC-008**: Users can record commitments and capital calls and see Portfolio Summary update with correct computed metrics immediately after data entry.
- **SC-009**: Zero paid-in edge case produces dash displays (not errors or NaN) for ratio columns.
- **SC-010**: All existing tests continue to pass (zero regressions from the redesign).
