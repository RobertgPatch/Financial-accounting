# Feature Specification: FMV Auto-Reporting

**Feature Branch**: `002-fmv-auto-reporting`  
**Created**: 2026-02-28  
**Status**: Draft  
**Input**: User description: "The FMV tool should work differently, I want the reports page to give options for FMV report or Distribution report. Remove the FMV total from the distribution report. The FMV should be totaled automatically from the assets that have been linked in Accounts with plaid. Mapping is not necessary, I dont want to have to create an assets for all of the accounts that get linked, just take the assets and total them for the FMV but give the option to add assets so they get included with FMV, give filters so that I can select the various types like cash, real estate, stocks and bonds etc"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View FMV Report with Automatic Plaid Totals (Priority: P1)

As a user, I want to open the Reports page and select "FMV Report" to see a consolidated Fair Market Value total that automatically includes all my Plaid-linked accounts — without needing to create or map individual assets for each account. The report shows a single FMV total that combines Plaid account balances with any manually-added assets, broken down by category.

**Why this priority**: This is the core value proposition — users get an accurate net worth snapshot without the overhead of manually managing every Plaid account as a separate asset. It removes the mapping requirement and auto-totals from linked accounts.

**Independent Test**: Can be fully tested by linking a Plaid institution (sandbox), syncing balances, then navigating to Reports → FMV Report. The report displays the total across all linked accounts plus any manual assets, grouped by type.

**Acceptance Scenarios**:

1. **Given** the user has Plaid-linked accounts with synced balances, **When** they navigate to Reports and select "FMV Report", **Then** they see a consolidated FMV total that includes all linked account balances automatically.
2. **Given** the user has both Plaid-linked accounts and manually-added assets with FMV snapshots, **When** they generate the FMV Report, **Then** the total reflects the sum of both Plaid balances and manual asset FMV values.
3. **Given** the user has Plaid-linked accounts but has never synced balances, **When** they generate the FMV Report, **Then** accounts with no balance data are shown with $0 and a note indicating they need to be synced.
4. **Given** the user has no Plaid-linked accounts and no manual assets, **When** they generate the FMV Report, **Then** they see a $0 total with a helpful message suggesting they link accounts or add assets.

---

### User Story 2 - Report Page Selection Between FMV and Distribution Reports (Priority: P1)

As a user, I want the Reports page to clearly present two report options — "FMV Report" and "Distribution Report" — so I can choose which report to view. The Distribution Report no longer includes FMV totals.

**Why this priority**: Equal to P1 because the current reports page only generates distribution reports, and this restructuring is a prerequisite for the FMV report to exist as a separate view.

**Independent Test**: Can be tested by navigating to the Reports page and confirming two report type options are presented. Selecting each generates the corresponding report type. The Distribution Report no longer shows any FMV-related totals.

**Acceptance Scenarios**:

1. **Given** the user navigates to the Reports page, **When** the page loads, **Then** they see a choice between "FMV Report" and "Distribution Report" before generating a report.
2. **Given** the user selects "Distribution Report", **When** the report is generated, **Then** it contains distribution data only — no FMV totals, net worth data, or asset valuations are included.
3. **Given** the user selects "FMV Report", **When** the report is generated, **Then** it contains FMV data with Plaid account totals and manual asset values.
4. **Given** the user switches between report types, **When** they switch, **Then** the previous report data is cleared and the appropriate filters/options for the selected report type are shown.

---

### User Story 3 - Filter FMV Report by Asset Type (Priority: P2)

As a user, I want to filter the FMV Report by asset type categories (cash, real estate, stocks, bonds, etc.) so that I can see the FMV total for specific categories of my portfolio rather than everything at once.

**Why this priority**: Filtering is essential for meaningful analysis — users typically want to see how much they have in liquid assets vs. real estate vs. investments, not just a single total number.

**Independent Test**: Can be tested by generating an FMV Report and selecting one or more type filters (e.g., "Cash" only). The displayed total and breakdown update to reflect only the filtered types.

**Acceptance Scenarios**:

1. **Given** the user is viewing the FMV Report, **When** they select the "Cash & Equivalents" filter, **Then** the report shows only Plaid accounts classified as cash/depository and manual assets typed as cash, with the total recalculated.
2. **Given** the user selects multiple type filters (e.g., "Cash" and "Public Equity"), **When** the report regenerates, **Then** it shows combined totals for both selected types.
3. **Given** the user has filters applied, **When** they clear all filters, **Then** the report reverts to showing all asset types with the full FMV total.
4. **Given** the user selects a type filter that has no matching accounts or assets, **When** the report regenerates, **Then** it shows $0 with a message indicating no items match the selected filter.

---

### User Story 4 - Include Manual Assets in FMV Report (Priority: P2)

As a user, I want the ability to add manual assets (with their FMV values) that get included in the FMV total alongside my Plaid-linked accounts. This is for assets not trackable through Plaid — real estate, private equity, collectibles, etc.

**Why this priority**: Complements the automatic Plaid totaling by allowing users to have a complete picture. Many high-value assets (real estate, private investments) cannot be linked through Plaid.

**Independent Test**: Can be tested by creating an asset with a manual FMV snapshot, then generating the FMV Report. The manual asset's FMV appears in the report alongside Plaid account balances.

**Acceptance Scenarios**:

1. **Given** the user has created a manual asset (e.g., a real estate property) with an FMV snapshot, **When** they generate the FMV Report, **Then** the manual asset's latest FMV value is included in the total.
2. **Given** the user has both Plaid accounts and manual assets, **When** they view the FMV Report, **Then** items are clearly labeled as either "Plaid" or "Manual" so the user knows the data source.
3. **Given** the user adds a new FMV snapshot for a manual asset, **When** they regenerate the FMV Report, **Then** the report reflects the updated (latest) FMV value.

---

### User Story 5 - FMV Report Breakdown and Visualization (Priority: P3)

As a user, I want the FMV Report to show a visual breakdown (chart and table) of my total FMV by asset type so I can quickly understand my portfolio composition.

**Why this priority**: Visualization enhances usability but is not strictly necessary for the core FMV reporting function.

**Independent Test**: Can be tested by generating an FMV Report with assets across multiple types and confirming a chart and summary table are rendered showing the allocation breakdown.

**Acceptance Scenarios**:

1. **Given** the user has FMV data across multiple asset types, **When** they generate the FMV Report, **Then** a chart displays the allocation breakdown by type (e.g., 40% Cash, 30% Real Estate, 20% Public Equity, 10% Other).
2. **Given** the user has FMV data, **When** they view the FMV Report, **Then** a summary table lists each type with its total FMV value, number of items, and percentage of the whole.
3. **Given** the user applies a type filter, **When** viewing the chart and table, **Then** both visuals update to reflect only the filtered types.

---

### Edge Cases

- What happens when a Plaid account type doesn't map to any known asset type? — The system categorizes it as "Other" and includes it in the FMV total.
- What happens when the same asset has both a Plaid balance and a manual FMV snapshot (i.e., a mapped account)? — The Plaid balance takes precedence for mapped accounts to avoid double-counting.
- What happens when a Plaid account has a negative balance (e.g., credit card)? — Negative balances are included in the FMV total, reducing the net value. They are displayed clearly with a negative amount.
- How does the system categorize Plaid account types into the asset type filters? — Plaid account types (depository, investment, loan, credit) are mapped to the existing asset type categories using a standard mapping (e.g., depository → Cash & Equivalents, investment → Public Equity).
- What happens when the user exports the FMV report? — The export includes the same data as the on-screen report, formatted for Excel.
- What if a user has no Plaid accounts linked and no manual assets? — The report shows $0 with a helpful empty state message.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Reports page MUST present a report type selector allowing the user to choose between "FMV Report" and "Distribution Report" before generating a report.
- **FR-002**: The Distribution Report MUST NOT include any FMV totals, net worth data, or asset valuation information. It must contain only distribution-related data (allocations, amounts, entities, assets, budget comparison, year-over-year, retained earnings).
- **FR-003**: The FMV Report MUST automatically include the current balance of all Plaid-linked accounts in the FMV total, without requiring the user to create corresponding assets or map accounts to assets.
- **FR-004**: The FMV Report MUST include the latest FMV snapshot value from manually-added assets that have FMV data.
- **FR-005**: The FMV Report MUST support filtering by asset type categories. The available categories are: Cash & Equivalents, Real Estate, Public Equity, Private Equity, Fixed Income, Hedge Fund, Cryptocurrency, Collectible, and Other.
- **FR-006**: Plaid account types MUST be automatically categorized into the asset type filter categories using a standard mapping (depository → Cash & Equivalents, investment → Public Equity, loan → Fixed Income, credit → Cash & Equivalents).
- **FR-007**: Each line item in the FMV Report MUST indicate its data source — either "Plaid" (for auto-included account balances) or "Manual" (for user-created assets with FMV snapshots).
- **FR-008**: The FMV Report MUST display a consolidated total across all included items (both Plaid and manual).
- **FR-009**: The FMV Report MUST show a breakdown by asset type, including the total value, item count, and percentage allocation for each type.
- **FR-010**: The FMV Report MUST support filtering by entity when applicable (for manual assets that have entity ownership records).
- **FR-011**: The FMV Report MUST be exportable in Excel format, consistent with the existing Distribution Report export.
- **FR-012**: When a Plaid account is mapped to an asset, the system MUST use the Plaid balance and NOT double-count by also including the asset's manual FMV snapshot.

### Key Entities

- **Plaid Account (existing)**: Represents a linked financial account from Plaid. Has type, subtype, current_balance, and optional asset foreign key. Key source for automatic FMV data.
- **Asset (existing)**: Represents a manually-tracked asset. Has asset_type, tags, and optional FMV snapshots. Included in FMV report when FMV snapshot data exists.
- **FMV Snapshot (existing)**: Point-in-time valuation for a manual asset. The latest snapshot per asset is used for FMV report calculations.
- **FMV Report (new concept)**: A generated report combining Plaid account balances and manual asset FMV snapshots into a consolidated valuation view with type-based filtering and breakdown.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can generate an FMV Report showing their total portfolio value within 3 seconds of clicking "Generate", with no prior asset-creation or mapping steps required for Plaid-linked accounts.
- **SC-002**: FMV Report totals are accurate to within $0.01, matching the sum of all Plaid account current balances plus latest manual asset FMV snapshots (without double-counting mapped accounts).
- **SC-003**: Users can filter the FMV Report by any of the 9 asset type categories and see updated totals within 2 seconds.
- **SC-004**: The Distribution Report loads without any FMV-related fields or totals, confirming a clean separation of report types.
- **SC-005**: Users with both Plaid accounts and manual assets can clearly distinguish the source of each line item in the FMV Report.
- **SC-006**: The FMV Report export produces a complete Excel file containing the same data visible on screen.

## Assumptions

- Plaid account balances reflect the latest synced values. The FMV report uses whatever balance was last synced — it does not trigger a new Plaid sync on report generation.
- The Plaid account type-to-asset-type mapping uses a sensible default. Users do not need to configure this mapping themselves.
- Manual assets are included in the FMV report only when they have at least one FMV snapshot. Assets without any FMV data are excluded (they have no valuation to report).
- Negative Plaid balances (credit cards, loans) are included in the total, reducing overall FMV. This gives an accurate net position.
- The existing FMV snapshot model and Plaid integration from the `001-portfolio-valuation-tracking` feature are in place and working.
