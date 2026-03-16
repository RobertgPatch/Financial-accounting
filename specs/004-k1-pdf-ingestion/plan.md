# Implementation Plan: K-1 PDF Ingestion

**Branch**: `004-k1-pdf-ingestion` | **Date**: 2026-03-04 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/004-k1-pdf-ingestion/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Build a K-1 PDF ingestion pipeline that accepts Schedule K-1 (Form 1065) uploads, extracts all financial fields using pdfplumber text extraction (with pytesseract OCR fallback), presents a review/classification UI, and on confirmation persists K-1 data to new Django models and auto-creates Distribution and capital account records in the existing portfolio tracker.

## Technical Context

**Language/Version**: Python 3.12, JavaScript (ES2022+)
**Primary Dependencies**: Django 4.2, DRF, pdfplumber (PDF text extraction), pytesseract + Pillow (OCR fallback), React 19, Vite 7, MUI 7, Tailwind CSS 3
**Storage**: PostgreSQL 16 (models), filesystem/MEDIA_ROOT (uploaded PDFs)
**Testing**: Django TestCase (model + API tests), manual frontend QA
**Target Platform**: Docker Compose (local), Railway (production)
**Project Type**: Web application (Django API + React SPA)
**Performance Goals**: Extract K-1 fields in <30 seconds, full workflow <3 minutes
**Constraints**: PDF uploads ≤10 MB, digitally-generated PDFs primary target, scanned PDFs best-effort via OCR
**Scale/Scope**: Single-tenant, ~10–50 K-1s per tax year, 3 new frontend pages (upload, review, list)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Django + React Full-Stack | ✅ PASS | All new code in Django backend (models, views, parser) + React frontend (pages, API client). No new frameworks. |
| II. Mobile-First Responsive Design | ✅ PASS | Review/list pages will use Tailwind responsive utilities. Upload and form layouts tested at 320px/768px/1280px. |
| III. Data Integrity First | ✅ PASS | All monetary values use DecimalField. K-1 confirmation uses Django transactions (atomic save of document + income items + distributions). No floating-point math. |
| IV. Incremental Migration Safety | ✅ PASS | New models added via Django migrations. No raw SQL. No destructive changes to existing models. Fully reversible. |
| V. Simplicity & YAGNI | ✅ PASS | Direct model access. Parser is a single module, no service layer abstraction. PDF extraction via pdfplumber (simple text extraction), not a full ML pipeline. |
| VI. Test Coverage | ✅ PASS | Model validation tests, API endpoint tests (upload, CRUD), parser unit tests with sample K-1 text fixtures. |
| Max 3 Django apps | ✅ PASS | K-1 models and views added to existing `api` app. No new Django app needed. Currently 2 apps (`api`, `plaid_integration`). |
| No authentication yet | ✅ PASS | No auth changes. K-1 endpoints follow existing AllowAny pattern. |
| Budget consciousness | ✅ PASS | pdfplumber is MIT-licensed/free. pytesseract uses free Tesseract OCR. No paid APIs. |

**Gate result: ALL PASS — no violations, proceed to Phase 0.**

## Project Structure

### Documentation (this feature)

```text
specs/004-k1-pdf-ingestion/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (API contracts)
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
backend/
├── api/
│   ├── models.py              # + K1Document, K1PartnershipInfo, K1PartnerInfo, K1IncomeItem, K1CapitalAccount
│   ├── serializers.py         # + K-1 serializers (document, income items, capital account)
│   ├── views.py               # + K-1 upload, review, confirm, list, detail endpoints
│   ├── urls.py                # + K-1 URL routes
│   ├── k1_parser.py           # NEW: PDF text extraction + field parsing logic
│   ├── tests.py               # + K-1 model tests, API tests, parser unit tests
│   └── migrations/
│       └── 0006_k1_models.py  # NEW: K-1 model migration
├── media/
│   └── k1_documents/          # Uploaded PDF storage
└── requirements.txt           # + pdfplumber, pytesseract, Pillow

frontend/
└── src/
    ├── api/
    │   └── k1.js              # NEW: K-1 API client functions
    └── pages/
        ├── K1Upload.jsx       # NEW: Upload page with drag-and-drop
        ├── K1Review.jsx       # NEW: Review/classify/confirm page
        └── K1Documents.jsx    # NEW: List view with filters + detail drill-in
```

**Structure Decision**: Web application structure. All backend K-1 code lives in the existing `api` app per constitution constraint (max 3 apps; currently 2). A dedicated `k1_parser.py` module isolates parsing logic. Frontend adds 3 new pages under `src/pages/` and a new API client module.

## Complexity Tracking

> No violations found — table not needed.
