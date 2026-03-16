# Tasks – K-1 PDF Ingestion

## Feature
K-1 PDF Document Ingestion — Upload Schedule K-1 PDF documents, automatically extract financial data via pdfplumber with OCR fallback, review/classify extracted fields, and auto-populate the portfolio tracker.

---

## Phase 1 — Setup

**Goal:** Configure project dependencies, Docker environment, and Django settings to support PDF upload and processing.

- [x] T001 Add pdfplumber, pytesseract, and Pillow to `backend/requirements.txt`
- [x] T002 Add `tesseract-ocr` apt-get install to `backend/Dockerfile`
- [x] T003 Add media volume mount `./backend/media:/app/media` to `docker-compose.yml`
- [x] T004 Add `DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024` to `backend/financial_accounting/settings.py`
- [x] T005 Add media file serving for DEBUG mode in `backend/financial_accounting/urls.py`

### Checkpoint
Run `docker compose build` — image builds successfully with tesseract-ocr available.
Run `python manage.py check` — Django system check passes.

---

## Phase 2 — Foundational

**Goal:** Create all data models, validators, serializers, and URL routing needed by multiple user stories. These are blocking prerequisites.

- [x] T006 Create PDF file validator function `validate_pdf_file` in `backend/api/validators.py`
- [x] T007 Add K1Document model with FileField, status choices (uploaded/processing/extracted/confirmed/error), and metadata fields in `backend/api/models.py`
- [x] T008 Add K1PartnershipInfo model (EIN, name, address, tax_year, etc.) linked to K1Document in `backend/api/models.py`
- [x] T009 Add K1PartnerInfo model (name, TIN, ownership_pct, profit_sharing_pct, etc.) linked to K1Document in `backend/api/models.py`
- [x] T010 Add K1IncomeItem model (box_number, description, amount as DecimalField, category choices) linked to K1Document in `backend/api/models.py`
- [x] T011 Add K1CapitalAccount model (beginning_balance, contributions, withdrawals, ending_balance, etc.) linked to K1Document in `backend/api/models.py`
- [x] T012 Generate and apply Django migration for all 5 new K-1 models via `python manage.py makemigrations api`
- [x] T013 Register all 5 K-1 models in Django admin in `backend/api/admin.py`
- [x] T014 [P] Create K1DocumentSerializer (upload context) in `backend/api/serializers.py`
- [x] T015 [P] Create K1PartnershipInfoSerializer in `backend/api/serializers.py`
- [x] T016 [P] Create K1PartnerInfoSerializer in `backend/api/serializers.py`
- [x] T017 [P] Create K1IncomeItemSerializer in `backend/api/serializers.py`
- [x] T018 [P] Create K1CapitalAccountSerializer in `backend/api/serializers.py`
- [x] T019 Create K1DocumentDetailSerializer that nests partnership_info, partner_info, income_items[], capital_account in `backend/api/serializers.py`
- [x] T020 Add K-1 API URL patterns (k1-documents/ prefix) in `backend/api/urls.py`
- [x] T021 Create empty K-1 ViewSet skeleton in `backend/api/views.py` with list, retrieve, create, update, destroy, and confirm action

### Checkpoint
Run `python manage.py migrate` — migration applies cleanly.
Run `python manage.py shell -c "from api.models import K1Document, K1PartnershipInfo, K1PartnerInfo, K1IncomeItem, K1CapitalAccount; print('OK')"` — all models importable.
Hit `GET /api/k1-documents/` — returns empty list (200).

---

## Phase 3 — User Story 1: Upload & Extract K-1 Data (P1)

**Goal:** Users can upload a K-1 PDF file. The system extracts text via pdfplumber (with pytesseract OCR fallback), parses partnership info, partner info, income items, and capital account data, and stores extracted fields in the database.

**Independent Test Criteria:** Upload a K-1 PDF via `POST /api/k1-documents/upload/` → receive 201 with extracted data populated in response. Document status transitions from `uploaded` → `processing` → `extracted`. All 4 child records (partnership_info, partner_info, income_items, capital_account) are created.

- [x] T022 [US1] Create `backend/api/k1_parser.py` with `extract_text_from_pdf(file_path)` function using pdfplumber with pytesseract OCR fallback
- [x] T023 [US1] Add `parse_partnership_info(text)` function to `backend/api/k1_parser.py` — extract EIN, partnership name, address, tax year from K-1 Part I fields
- [x] T024 [US1] Add `parse_partner_info(text)` function to `backend/api/k1_parser.py` — extract partner name, TIN, ownership percentage, profit/loss sharing percentage from K-1 Part II fields
- [x] T025 [US1] Add `parse_income_items(text)` function to `backend/api/k1_parser.py` — extract box numbers (1-20+), descriptions, amounts, and categorize (ordinary_income, rental_income, interest, dividends, royalties, capital_gain, other) from K-1 Part III fields
- [x] T026 [US1] Add `parse_capital_account(text)` function to `backend/api/k1_parser.py` — extract beginning balance, contributions, current year income/loss, withdrawals, ending balance from capital account analysis section
- [x] T027 [US1] Add `parse_k1_document(file_path)` orchestrator function to `backend/api/k1_parser.py` — calls all parse functions, returns structured dict with partnership_info, partner_info, income_items[], capital_account
- [x] T028 [US1] Implement `create` action in K-1 ViewSet in `backend/api/views.py` — accept multipart PDF upload, save K1Document, call `parse_k1_document`, create child records atomically, return K1DocumentDetailSerializer response
- [x] T029 [US1] Add error handling and status transitions to upload flow in `backend/api/views.py` — set status to `error` with error_message on parse failure, wrap in `transaction.atomic()`
- [x] T030 [P] [US1] Create frontend API client for K-1 endpoints in `frontend/src/api/k1.js` — uploadK1Document(file), getK1Documents(), getK1Document(id), updateK1Document(id, data), confirmK1Document(id), deleteK1Document(id)
- [x] T031 [US1] Create K1Upload page component in `frontend/src/pages/K1Upload.jsx` — drag-and-drop file zone, upload button, progress indicator, success redirect to review page
- [x] T032 [US1] Add K1Upload route (`/k1/upload`) to `frontend/src/App.jsx`
- [x] T033 [US1] Add "K-1 Upload" link to sidebar navigation in `frontend/src/components/layout/Sidebar.jsx`

### Checkpoint
Upload a test K-1 PDF file via the UI at `/k1/upload`.
Verify 201 response with `status: "extracted"`.
Confirm partnership_info, partner_info, income_items, and capital_account are populated in the response.
Verify the PDF file is saved to `backend/media/k1_documents/`.

---

## Phase 4 — User Story 2: Review, Classify & Confirm (P1)

**Goal:** Users can review extracted K-1 data side-by-side with the original PDF, edit any incorrectly parsed fields, classify income items to asset types, link to existing entities/assets, and confirm the document as accurate.

**Independent Test Criteria:** Navigate to review page for an extracted K-1 → see all extracted fields in editable form alongside PDF preview. Edit a field → save → verify update persists. Classify income items by category. Click confirm → document status changes to `confirmed`, fields become read-only.

- [x] T034 [US2] Implement `update` action in K-1 ViewSet in `backend/api/views.py` — accept PUT with nested partnership_info, partner_info, income_items[], capital_account fields; validate status is `extracted`; update child records atomically
- [x] T035 [US2] Implement `confirm` custom action (`POST /api/k1-documents/{id}/confirm/`) in `backend/api/views.py` — validate all required fields present, transition status from `extracted` to `confirmed`, set confirmed_at timestamp
- [x] T036 [US2] Add entity and asset linking fields (entity FK, asset FK) to K1Document model if not present, and to K1DocumentDetailSerializer in `backend/api/serializers.py`
- [x] T037 [US2] Create K1Review page component in `frontend/src/pages/K1Review.jsx` — two-panel layout: left panel shows PDF viewer (iframe/embed), right panel shows editable form with all extracted fields grouped by section
- [x] T038 [US2] Add entity dropdown (fetched from `/api/entities/`) and asset dropdown (fetched from `/api/assets/`) to K1Review form in `frontend/src/pages/K1Review.jsx`
- [x] T039 [US2] Add income item category classification dropdown (ordinary_income, rental_income, interest, dividends, royalties, capital_gain, other) per item in K1Review in `frontend/src/pages/K1Review.jsx`
- [x] T040 [US2] Add save and confirm buttons to K1Review in `frontend/src/pages/K1Review.jsx` — save calls PUT, confirm calls POST confirm endpoint, show success/error snackbar
- [x] T041 [US2] Add K1Review route (`/k1/:id/review`) to `frontend/src/App.jsx`

### Checkpoint
Navigate to `/k1/{id}/review` for an extracted document.
Verify PDF displays in left panel, extracted fields in right panel.
Edit a field, click save → verify PUT succeeds and changes persist on reload.
Click confirm → status changes to `confirmed`, form becomes read-only.

---

## Phase 5 — User Story 3: View & Manage K-1 Documents (P2)

**Goal:** Users can browse all uploaded K-1 documents with filtering by tax year, status, and entity. View document details. Delete documents. Download original PDFs.

**Independent Test Criteria:** Navigate to K-1 documents list → see table of all K-1s with partnership name, tax year, status, upload date columns. Apply tax year filter → list updates. Click a row → navigate to detail view. Delete a document → confirm removal. Download original PDF.

- [x] T042 [US3] Implement `list` action with filtering (tax_year, status, entity) and ordering in K-1 ViewSet in `backend/api/views.py`
- [x] T043 [US3] Implement `retrieve` action returning full nested detail in K-1 ViewSet in `backend/api/views.py`
- [x] T044 [US3] Implement `destroy` action with file cleanup (delete PDF from media) in K-1 ViewSet in `backend/api/views.py`
- [x] T045 [P] [US3] Implement `download` custom action (`GET /api/k1-documents/{id}/download/`) returning the original PDF file in `backend/api/views.py`
- [x] T046 [US3] Create K1Documents list page component in `frontend/src/pages/K1Documents.jsx` — MUI DataGrid/table with columns: partnership name, tax year, status (chip), entity, upload date, actions (view/delete/download)
- [x] T047 [US3] Add filter controls (tax year select, status select, entity select) to K1Documents list page in `frontend/src/pages/K1Documents.jsx`
- [x] T048 [US3] Add delete confirmation dialog and download action handlers in `frontend/src/pages/K1Documents.jsx`
- [x] T049 [US3] Add K1Documents route (`/k1`) and K1Detail route (`/k1/:id`) to `frontend/src/App.jsx`
- [x] T050 [US3] Add "K-1 Documents" link to sidebar navigation in `frontend/src/components/layout/Sidebar.jsx`

### Checkpoint
Navigate to `/k1` → see list of uploaded K-1 documents.
Filter by tax year → list filters correctly.
Click a document → navigate to `/k1/{id}` showing full detail.
Delete a document → removed from list and file deleted from disk.
Download a PDF → file downloads to browser.

---

## Phase 6 — User Story 4: Auto-populate Portfolio Data (P2)

**Goal:** When a K-1 document is confirmed, users can trigger auto-population of portfolio data — creating Distribution and DistributionAllocation records from confirmed K-1 income items, with duplicate detection to prevent double-entry.

**Independent Test Criteria:** Confirm a K-1 document → click "Populate Portfolio" → Distribution and DistributionAllocation records are created. Verify amounts match K-1 income items. Attempt to populate again → duplicate detection prevents double-entry. Navigate to the existing Distributions page → see newly created distribution.

- [x] T051 [US4] Create `backend/api/k1_portfolio.py` with `populate_portfolio_from_k1(k1_document)` function — builds Distribution + DistributionAllocation records from confirmed K-1 income items, maps K-1 categories to distribution_type
- [x] T052 [US4] Add duplicate detection to `populate_portfolio_from_k1` in `backend/api/k1_portfolio.py` — check for existing distributions linked to this K1Document (via source_k1_document FK), raise error if already populated
- [x] T053 [US4] Add `source_k1_document` nullable ForeignKey field to Distribution model in `backend/api/models.py` to link distributions back to their K-1 source, generate migration
- [x] T054 [US4] Implement `populate` custom action (`POST /api/k1-documents/{id}/populate/`) in `backend/api/views.py` — validate status is `confirmed`, call `populate_portfolio_from_k1`, return created distribution summary, wrap in `transaction.atomic()`
- [x] T055 [US4] Add `downloadK1Document(id)` and `populateK1Document(id)` to frontend API client in `frontend/src/api/k1.js`
- [x] T056 [US4] Add "Populate Portfolio" button to K1Review page (visible only when status is `confirmed`) in `frontend/src/pages/K1Review.jsx` — calls populate endpoint, shows success summary dialog with created distributions
- [x] T057 [US4] Show populated status indicator and link to created distributions on K1Review page in `frontend/src/pages/K1Review.jsx`

### Checkpoint
Confirm a K-1 document, then click "Populate Portfolio".
Verify Distribution records appear on the existing Distributions page.
Verify DistributionAllocation amounts match K-1 income items.
Click "Populate Portfolio" again → see "already populated" error message.

---

## Phase 7 — Polish & Cross-Cutting Concerns

**Goal:** Documentation, edge case handling, error states, and code quality improvements.

- [x] T058 Add OCR fallback logging and user-visible quality indicator (extracted_via: text vs ocr) to K1Document model and serializer in `backend/api/models.py` and `backend/api/serializers.py`
- [x] T059 Add comprehensive error states and user-friendly error messages to all K-1 frontend pages (upload failure, parse failure, network errors) in `frontend/src/pages/K1Upload.jsx`, `frontend/src/pages/K1Review.jsx`, `frontend/src/pages/K1Documents.jsx`
- [x] T060 Add loading skeletons/spinners to K1Review and K1Documents pages in `frontend/src/pages/K1Review.jsx` and `frontend/src/pages/K1Documents.jsx`
- [x] T061 Update `backend/api/excel_export.py` to include K-1 summary data in reports (if applicable)
- [x] T062 Validate quickstart workflow end-to-end: upload sample K-1 → review → confirm → populate portfolio → verify distributions

---

## Dependencies

```
Phase 1 (Setup)
  └──▶ Phase 2 (Foundational)
         ├──▶ Phase 3 (US1: Upload & Extract)
         │      └──▶ Phase 4 (US2: Review & Confirm)
         │             ├──▶ Phase 5 (US3: List & Manage) — can start after Phase 2, but benefits from US1/US2 data
         │             └──▶ Phase 6 (US4: Auto-populate) — requires US2 confirm flow
         └──▶ Phase 7 (Polish) — after all user stories complete
```

**Story dependency order:**
1. US1 (Upload & Extract) — independent, first to implement
2. US2 (Review & Confirm) — depends on US1 (needs extracted document)
3. US3 (List & Manage) — depends on Phase 2 models, benefits from US1 data
4. US4 (Auto-populate) — depends on US2 (needs confirmed document)

**Note:** US3 (List & Manage) can be developed in parallel with US2 since it only reads data, but testing requires documents from US1.

## Parallel Execution Examples

**Within Phase 2 (Foundational):**
T014, T015, T016, T017, T018 — all serializers can be written in parallel (different model serializers in same file, no dependencies between them).

**Within Phase 3 (US1):**
T022-T026 — individual parser functions can be written in parallel (each parses a different K-1 section).
T030 — frontend API client can be written in parallel with backend endpoint implementation.

**Within Phase 5 (US3):**
T045 — download endpoint can be written in parallel with list/detail/destroy actions.

**Cross-story parallelism:**
- US3 backend (T042-T045) can be developed in parallel with US2 frontend (T037-T041) since they touch different files.

## Implementation Strategy

**MVP Scope:** User Stories 1 + 2 (Phases 1-4)
- Users can upload K-1 PDFs and review/confirm extracted data
- This delivers core value: PDF → structured data pipeline

**Increment 2:** User Story 3 (Phase 5)
- Browsing, filtering, and managing documents
- Builds on MVP with list/detail views

**Increment 3:** User Story 4 (Phase 6)
- Portfolio auto-population from confirmed K-1s
- Connects K-1 data to existing portfolio tracker

**Final:** Polish (Phase 7)
- Error handling, loading states, OCR quality indicators, export integration

---

## Summary

| Phase | Description | Task Count |
|-------|-------------|------------|
| 1 | Setup | 5 |
| 2 | Foundational | 16 |
| 3 | US1: Upload & Extract | 12 |
| 4 | US2: Review & Confirm | 8 |
| 5 | US3: List & Manage | 9 |
| 6 | US4: Auto-populate | 7 |
| 7 | Polish | 5 |
| **Total** | | **62** |
