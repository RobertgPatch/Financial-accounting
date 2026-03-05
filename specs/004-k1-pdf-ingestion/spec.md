# Feature Specification: K-1 PDF Ingestion

**Feature Branch**: `004-k1-pdf-ingestion`  
**Created**: 2025-01-27  
**Status**: Draft  
**Input**: User description: "Add K-1 PDF ingestion system to extract fields from federal Schedule K-1 documents and allow manual classification of asset type and anything else required that can't be derived from the K-1 itself"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Upload and Extract K-1 Data (Priority: P1)

As an investor, I want to upload a federal Schedule K-1 (Form 1065) PDF so the system automatically extracts partnership, partner, income, deduction, distribution, and capital account data—eliminating manual data entry.

**Why this priority**: Core value proposition. Without PDF extraction, users must manually key in dozens of fields per K-1. This single story delivers the primary time savings.

**Independent Test**: Upload a K-1 PDF via the UI, confirm the system parses all extractable fields and displays them in a review screen. Delivers immediate value even without linking to existing entities.

**Acceptance Scenarios**:

1. **Given** a user is on the K-1 ingestion page, **When** they upload a valid Schedule K-1 PDF (Form 1065), **Then** the system extracts and displays all recognized fields grouped by section (Partnership Info, Partner Info, Income, Deductions, Credits, Capital Account, Distributions).
2. **Given** a user uploads a K-1 PDF, **When** extraction completes, **Then** each extracted field shows the IRS line number, field label, and parsed value so the user can verify accuracy.
3. **Given** a user uploads a multi-page K-1 with supplemental statements, **When** extraction completes, **Then** the system extracts fields from all pages including coded items on lines 11, 13, 17, 18, and 20.
4. **Given** a user uploads a non-K-1 or corrupted PDF, **When** the system attempts extraction, **Then** it displays a clear error message indicating the document could not be recognized as a Schedule K-1.

---

### User Story 2 - Review, Classify, and Confirm Extracted Data (Priority: P1)

As an investor, I want to review all extracted K-1 data on a confirmation screen, manually classify the asset type, map the K-1 to an existing entity and asset (or create new ones), and correct any misread values before saving.

**Why this priority**: Extraction alone is insufficient—users must be able to classify fields that cannot be derived from the K-1 (asset type, entity mapping) and fix OCR/parsing errors before data enters the system.

**Independent Test**: After extraction, open the review screen, assign asset type, map to an entity, edit a value, and save. Verify all data persists correctly.

**Acceptance Scenarios**:

1. **Given** a K-1 has been extracted, **When** the user views the review screen, **Then** they see all extracted values in editable fields, with a required "Asset Type" dropdown (e.g., Private Equity, Venture Capital, Real Estate, Hedge Fund, Fixed Income, Public Equity) that must be set before saving.
2. **Given** the review screen is displayed, **When** the user selects an Entity from a dropdown, **Then** the system shows existing entities and an option to create a new one. The same applies for Asset (partnership/fund).
3. **Given** the user has classified asset type, mapped entity and asset, and reviewed all values, **When** they click "Confirm & Save", **Then** the K-1 data is persisted as a K-1 Document record with all extracted fields, and linked to the selected entity and asset.
4. **Given** the user has not yet selected an asset type, **When** they attempt to save, **Then** the system prevents saving and highlights the required classification fields.

---

### User Story 3 - View and Manage Ingested K-1 Documents (Priority: P2)

As an investor, I want to browse all previously ingested K-1 documents, filter by tax year, entity, or asset, and drill into any K-1 to view its full extracted data.

**Why this priority**: After ingesting multiple K-1s across tax years, users need a central view to manage and reference historical data. This is valuable once a critical mass of K-1s exists.

**Independent Test**: Ingest two or more K-1s for different tax years and entities. Navigate to the K-1 list view, apply filters, and open a detail view for one document.

**Acceptance Scenarios**:

1. **Given** one or more K-1 documents have been ingested, **When** the user navigates to the K-1 Documents page, **Then** they see a table listing all K-1s with columns: Tax Year, Partnership Name, Entity, Asset Type, Total Distributions, Net Income, and Ingestion Date.
2. **Given** the K-1 list is displayed, **When** the user filters by tax year or entity, **Then** the list updates to show only matching K-1 documents.
3. **Given** the user clicks on a K-1 row, **When** the detail view opens, **Then** they see all extracted fields organized by IRS section with the ability to edit and re-save.

---

### User Story 4 - Auto-populate Portfolio Data from K-1 (Priority: P2)

As an investor, I want confirmed K-1 data to automatically flow into my portfolio tracking—creating or updating distributions, capital account snapshots, and income records—so my portfolio reports stay current without additional manual entry.

**Why this priority**: This closes the loop between K-1 ingestion and the existing portfolio tracker. Without it, K-1 data lives in isolation. With it, a single PDF upload keeps the entire portfolio up to date.

**Independent Test**: Ingest and confirm a K-1 for an entity/asset that already exists. Verify that a Distribution record is created for line 19A amounts and that capital account data is reflected in the system.

**Acceptance Scenarios**:

1. **Given** a K-1 is confirmed with a mapped entity and asset, **When** the K-1 contains a distribution amount (line 19A), **Then** the system creates a Distribution record for that entity/asset with the K-1's tax year end date and distribution amount.
2. **Given** a K-1 is confirmed, **When** the K-1 contains capital account data (Section L), **Then** the system stores beginning balance, contributions, net income, withdrawals, and ending balance associated with the entity and asset for that tax year.
3. **Given** a distribution already exists for the same entity, asset, and period, **When** a duplicate K-1 is ingested, **Then** the system warns the user of the potential duplicate and asks whether to skip, overwrite, or create a new record.

---

### Edge Cases

- What happens when a K-1 PDF is scanned (image-based) rather than digitally generated? The system should attempt OCR and warn the user that accuracy may be reduced, prompting careful review.
- What happens when a K-1 contains supplemental statement references (e.g., "SEE STMT" on lines 11, 20)? The system should extract coded items from supplemental pages where possible and flag items it cannot parse.
- What happens when the same K-1 is uploaded twice? The system should detect the duplicate based on partnership EIN + partner TIN + tax year and alert the user.
- What happens when a K-1 is from a different form type (e.g., Form 1120-S for S-Corps instead of Form 1065 for partnerships)? The system should initially support only Form 1065 K-1s and display a clear message for unsupported form types.
- What happens when extracted numeric values contain formatting artifacts (parentheses for negatives, commas, dollar signs)? The system must normalize all amounts to standard numeric format.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept PDF file uploads of Schedule K-1 (Form 1065) documents up to 10 MB in size.
- **FR-002**: System MUST extract all standard K-1 fields from Part I (Partnership Information), Part II (Partner Information), and Part III (Income, Deductions, Credits) including lines 1 through 23.
- **FR-003**: System MUST extract Capital Account Analysis data from Section L: beginning balance, capital contributed, current year net income/loss, other increases/decreases, withdrawals and distributions, and ending balance.
- **FR-004**: System MUST extract partner's share percentages (profit, loss, capital) for both beginning and ending periods from Section J.
- **FR-005**: System MUST extract liability information (nonrecourse, qualified nonrecourse, recourse) for both beginning and ending periods from Section K1.
- **FR-006**: System MUST handle coded line items (lines 11, 13, 15, 17, 18, 20) that contain multiple sub-items identified by letter codes, extracting each code-value pair.
- **FR-007**: System MUST normalize all monetary values by stripping currency symbols, commas, and converting parenthesized values to negative numbers.
- **FR-008**: System MUST present a review screen after extraction where users can verify, edit, and correct any extracted value before saving.
- **FR-009**: System MUST require manual classification of **Asset Type** before saving (options: Private Equity, Venture Capital, Real Estate, Hedge Fund, Fixed Income, Public Equity, Other).
- **FR-010**: System MUST allow users to map the K-1 to an existing Entity or create a new Entity during review.
- **FR-011**: System MUST allow users to map the K-1 to an existing Asset (partnership/fund) or create a new Asset during review.
- **FR-012**: System MUST persist the original uploaded PDF file for audit reference.
- **FR-013**: System MUST detect potential duplicate K-1 uploads based on partnership EIN, partner TIN, and tax year, and warn the user before saving.
- **FR-014**: System MUST display a list view of all ingested K-1 documents with filtering by tax year, entity, and asset type.
- **FR-015**: System MUST allow users to drill into any ingested K-1 to view and edit its full extracted data.
- **FR-016**: Upon confirmation, system MUST auto-create a Distribution record from K-1 line 19A (cash distributions) linked to the mapped entity and asset.
- **FR-017**: Upon confirmation, system MUST store capital account data (Section L) as a historical record linked to the entity, asset, and tax year.
- **FR-018**: System MUST support K-1s for tax years 2020 through current year.
- **FR-019**: System MUST identify the tax year from the K-1 header and pre-fill it, allowing user override.
- **FR-020**: System MUST extract the Final K-1 / Amended K-1 indicator and store it as metadata.

### Key Entities

- **K1Document**: Represents a single ingested K-1 filing. Links to an Entity (the partner) and an Asset (the partnership/fund). Stores tax year, ingestion date, processing status (draft/confirmed), asset type classification, original PDF reference, and the Final/Amended indicator.
- **K1PartnershipInfo**: Partnership-level data extracted from Part I — EIN, name, address, IRS filing center, PTP indicator.
- **K1PartnerInfo**: Partner-level data from Part II — TIN, name, address, partner type (general/limited), domestic/foreign, entity type, share percentages (profit/loss/capital for beginning and ending), liabilities (nonrecourse, qualified nonrecourse, recourse for beginning and ending).
- **K1IncomeItem**: Individual income, deduction, credit, or other line item from Part III. Each record stores the IRS line number, optional letter code (for multi-value lines), description, and amount. A K1Document has many K1IncomeItems.
- **K1CapitalAccount**: Section L data — beginning balance, capital contributed, net income/loss, other increases/decreases, withdrawals/distributions, ending balance. One record per K1Document.

## Assumptions

- K-1 PDFs are digitally generated (not hand-written scans). The system will attempt OCR for image-based PDFs but accuracy is not guaranteed and users will be warned.
- Only Schedule K-1 from Form 1065 (partnerships) is in scope. Form 1120-S (S-Corp) K-1s are out of scope for this feature.
- The system will use a PDF text-extraction approach first, falling back to OCR only when text extraction yields insufficient data.
- Users uploading K-1s have access to the full application and can view/manage all entities and assets (no role-based access control changes needed for this feature).
- Supplemental statements ("SEE STMT" references) follow common formatting patterns but may not be parseable in all cases. Unparseable items will be flagged for manual entry.
- One K-1 PDF may contain multiple pages (including supplemental statements) but represents a single K-1 filing for one partner from one partnership for one tax year.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can upload a K-1 PDF and see extracted data on a review screen within 30 seconds.
- **SC-002**: 90% of fields from a digitally-generated K-1 PDF are correctly extracted without manual correction.
- **SC-003**: Users can complete the full ingestion workflow (upload → review → classify → confirm) in under 3 minutes per K-1.
- **SC-004**: Duplicate K-1 uploads are detected and flagged 100% of the time when partnership EIN, partner TIN, and tax year match an existing record.
- **SC-005**: After confirmation, distribution and capital account records appear in portfolio reports without any additional manual steps.
- **SC-006**: Users can locate and view any previously ingested K-1 within 2 clicks from the main navigation.
