# Data Model: K-1 PDF Ingestion

**Feature**: 004-k1-pdf-ingestion  
**Date**: 2026-03-04  
**Spec**: [spec.md](spec.md) | **Research**: [research.md](research.md)

---

## Entity Relationship Diagram

```
┌─────────────────┐     ┌─────────────────┐
│  Entity (existing) │     │  Asset (existing)  │
└────────┬────────┘     └────────┬────────┘
         │ FK                     │ FK
         │                        │
         ▼                        ▼
┌──────────────────────────────────────────┐
│              K1Document                   │
│──────────────────────────────────────────│
│  id (PK)                                 │
│  entity (FK → Entity, nullable)          │
│  asset (FK → Asset, nullable)            │
│  tax_year (int)                          │
│  status (enum: draft/confirmed)          │
│  asset_type_classification (enum)        │
│  is_final (bool)                         │
│  is_amended (bool)                       │
│  document (FileField)                    │
│  original_filename (str)                 │
│  extraction_method (enum: text/ocr)      │
│  uploaded_at (datetime)                  │
│  confirmed_at (datetime, nullable)       │
│  notes (text, nullable)                  │
└──────────┬───────────────────────────────┘
           │ 1:1           │ 1:N          │ 1:1
           ▼               ▼              ▼
┌────────────────┐ ┌─────────────┐ ┌──────────────────┐
│K1PartnershipInfo│ │K1IncomeItem │ │K1CapitalAccount  │
│────────────────│ │─────────────│ │──────────────────│
│ document (FK)  │ │ document(FK)│ │ document (FK)    │
│ ein (str)      │ │ line_number │ │ beginning_bal    │
│ name (str)     │ │ code (str?) │ │ capital_contrib  │
│ address (text) │ │ description │ │ net_income       │
│ city (str)     │ │ amount (dec)│ │ other_increase   │
│ state (str)    │ │ raw_text    │ │ withdrawals      │
│ zip_code (str) │ └─────────────┘ │ ending_bal       │
│ irs_center(str)│                  └──────────────────┘
│ is_ptp (bool)  │
└────────────────┘
           │ 1:1 (via K1Document)
           ▼
┌──────────────────────┐
│   K1PartnerInfo       │
│──────────────────────│
│ document (FK)         │
│ tin (str, encrypted?) │
│ name (str)            │
│ address (text)        │
│ city (str)            │
│ state (str)           │
│ zip_code (str)        │
│ is_general_partner    │
│ is_domestic           │
│ entity_type (str)     │
│ is_retirement_plan    │
│ profit_beg_pct (dec)  │
│ profit_end_pct (dec)  │
│ loss_beg_pct (dec)    │
│ loss_end_pct (dec)    │
│ capital_beg_pct (dec) │
│ capital_end_pct (dec) │
│ nonrecourse_beg (dec) │
│ nonrecourse_end (dec) │
│ qnr_beg (dec)         │
│ qnr_end (dec)         │
│ recourse_beg (dec)    │
│ recourse_end (dec)    │
│ has_lower_tier (bool) │
│ has_guarantee (bool)  │
│ section_704c_beg(dec) │
│ section_704c_end(dec) │
│ built_in_gain (bool)  │
└───────────────────────┘
```

---

## Model Definitions

### K1Document (root model)

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | BigAutoField (PK) | auto | — |
| entity | FK → Entity | nullable, SET_NULL | Mapped during review; null while in draft |
| asset | FK → Asset | nullable, SET_NULL | Mapped during review; null while in draft |
| tax_year | IntegerField | required, range 2020–current | Extracted from K-1 header |
| status | CharField(20) | choices: draft, confirmed | draft = just uploaded; confirmed = user reviewed & saved |
| asset_type_classification | CharField(50) | choices matching Asset.ASSET_TYPE_CHOICES, nullable | Required before confirmation; manually set by user |
| is_final | BooleanField | default False | Final K-1 indicator from form header |
| is_amended | BooleanField | default False | Amended K-1 indicator from form header |
| document | FileField | upload_to=k1_upload_path, validators=[validate_pdf_file] | Original PDF stored at k1_documents/{tax_year}/{entity_id}/ |
| original_filename | CharField(255) | required | Preserved before Django renames file |
| extraction_method | CharField(10) | choices: text, ocr | How fields were extracted |
| uploaded_at | DateTimeField | auto_now_add | — |
| confirmed_at | DateTimeField | nullable | Set when user confirms; null while draft |
| notes | TextField | nullable, blank | User notes |

**Unique constraint**: `(partnership_ein, partner_tin, tax_year)` — where partnership_ein and partner_tin come from related K1PartnershipInfo and K1PartnerInfo. Enforced at the application level (not DB constraint) since they're on related models. Duplicate detection query in the confirmation flow.

**Relationships**:
- `entity` and `asset` are nullable because they're set during review, not during initial upload/extraction
- `K1PartnershipInfo` (1:1), `K1PartnerInfo` (1:1), `K1CapitalAccount` (1:1), `K1IncomeItem` (1:N)

---

### K1PartnershipInfo (Part I)

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | BigAutoField (PK) | auto | — |
| document | OneToOneField → K1Document | CASCADE, related_name='partnership_info' | — |
| ein | CharField(20) | blank=True | Partnership EIN (e.g., "65-1123456") |
| name | CharField(255) | blank=True | Partnership name |
| address | TextField | blank=True | Street address |
| city | CharField(100) | blank=True | — |
| state | CharField(50) | blank=True | — |
| zip_code | CharField(20) | blank=True | — |
| irs_center | CharField(100) | blank=True | Where return filed (e.g., "E-FILE") |
| is_ptp | BooleanField | default False | Publicly traded partnership |

---

### K1PartnerInfo (Part II)

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | BigAutoField (PK) | auto | — |
| document | OneToOneField → K1Document | CASCADE, related_name='partner_info' | — |
| tin | CharField(20) | blank=True | Partner's TIN/SSN — may be partially masked |
| name | CharField(255) | blank=True | Partner name |
| address | TextField | blank=True | Street address |
| city | CharField(100) | blank=True | — |
| state | CharField(50) | blank=True | — |
| zip_code | CharField(20) | blank=True | — |
| is_general_partner | BooleanField | default False | G: General partner or LLC member-manager |
| is_domestic | BooleanField | default True | H1: Domestic vs Foreign |
| entity_type | CharField(100) | blank=True | I1: Type of entity |
| is_retirement_plan | BooleanField | default False | I2: IRA/SEP/Keogh indicator |
| profit_beginning_pct | DecimalField(10,6) | nullable | J: Profit % beginning |
| profit_ending_pct | DecimalField(10,6) | nullable | J: Profit % ending |
| loss_beginning_pct | DecimalField(10,6) | nullable | J: Loss % beginning |
| loss_ending_pct | DecimalField(10,6) | nullable | J: Loss % ending |
| capital_beginning_pct | DecimalField(10,6) | nullable | J: Capital % beginning |
| capital_ending_pct | DecimalField(10,6) | nullable | J: Capital % ending |
| nonrecourse_beginning | DecimalField(15,2) | nullable | K1: Nonrecourse beginning |
| nonrecourse_ending | DecimalField(15,2) | nullable | K1: Nonrecourse ending |
| qualified_nonrecourse_beginning | DecimalField(15,2) | nullable | K1: QNR beginning |
| qualified_nonrecourse_ending | DecimalField(15,2) | nullable | K1: QNR ending |
| recourse_beginning | DecimalField(15,2) | nullable | K1: Recourse beginning |
| recourse_ending | DecimalField(15,2) | nullable | K1: Recourse ending |
| has_lower_tier_liabilities | BooleanField | default False | K2 checkbox |
| has_guarantee_obligations | BooleanField | default False | K3 checkbox |
| section_704c_beginning | DecimalField(15,2) | nullable | N: Beginning 704(c) gain/loss |
| section_704c_ending | DecimalField(15,2) | nullable | N: Ending 704(c) gain/loss |
| built_in_gain | NullBooleanField | nullable | M: Yes/No/null |

---

### K1IncomeItem (Part III — line items)

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | BigAutoField (PK) | auto | — |
| document | FK → K1Document | CASCADE, related_name='income_items' | — |
| line_number | CharField(10) | required | IRS line number (e.g., "1", "4a", "9b", "11", "20") |
| code | CharField(10) | blank=True, nullable | Letter code for multi-code lines (e.g., "A", "ZZ") |
| description | CharField(255) | blank=True | Line description / code description |
| amount | DecimalField(15,2) | nullable | Parsed monetary value (normalized) |
| raw_text | CharField(500) | blank=True | Raw text as extracted — preserved for audit/debugging |
| is_supplemental | BooleanField | default False | True if extracted from supplemental statement |

**Ordering**: `['line_number', 'code']`

**Notes**:
- Single-value lines (1, 2, 3, 4a, 4b, 4c, 5, 6a, 6b, 6c, 7, 8, 9a, 9b, 9c, 10, 12): one row per line, `code` is null
- Multi-code lines (11, 13, 14, 15, 17, 18, 19, 20, 21): one row per code-value pair (e.g., line 20 code A = $4,493,757)
- Lines referencing "SEE STMT" will have the raw_text preserved and attempt to extract from supplemental pages
- Amounts store normalized decimals; raw_text preserves original format for audit

---

### K1CapitalAccount (Section L)

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | BigAutoField (PK) | auto | — |
| document | OneToOneField → K1Document | CASCADE, related_name='capital_account' | — |
| beginning_balance | DecimalField(15,2) | nullable | Beginning capital account |
| capital_contributed | DecimalField(15,2) | nullable | Capital contributed during the year |
| net_income | DecimalField(15,2) | nullable | Current year net income (loss) |
| other_increase_decrease | DecimalField(15,2) | nullable | Other increase (decrease) |
| withdrawals | DecimalField(15,2) | nullable | Withdrawals and distributions |
| ending_balance | DecimalField(15,2) | nullable | Ending capital account |
| tax_basis_method | CharField(50) | blank=True | Tax basis / GAAP / Section 704(b) / Other |

---

## Relationships to Existing Models

### On Confirmation (K1Document.status = 'confirmed')

1. **Distribution** (existing model):
   - Created from K1IncomeItem where `line_number='19'` and `code='A'` (cash distributions)
   - `asset` = K1Document.asset
   - `distribution_date` = last day of K1Document.tax_year (Dec 31)
   - `total_amount` = K1IncomeItem.amount
   - `distribution_type` = 'regular'
   - `notes` = f"Auto-created from K-1 {tax_year} line 19A"

2. **DistributionAllocation** (existing model):
   - `distribution` = newly created Distribution
   - `entity` = K1Document.entity
   - `amount` = same as distribution total (100% allocation to the entity on the K-1)
   - `percentage` = 100.0000

3. **K1CapitalAccount** (new model, already populated during extraction)
   - No additional records needed — the K1CapitalAccount IS the capital account record for this entity/asset/year

### Duplicate Detection Query

```
K1PartnershipInfo.objects.filter(
    ein=extracted_ein,
    document__partner_info__tin=extracted_tin,
    document__tax_year=extracted_tax_year,
    document__status='confirmed'
).exists()
```

---

## State Machine: K1Document Lifecycle

```
                    ┌───────────┐
   Upload PDF ───→  │   DRAFT   │
                    └─────┬─────┘
                          │ User reviews, classifies,
                          │ maps entity/asset
                          ▼
                    ┌───────────┐
   Confirm ──────→  │ CONFIRMED │ ──→ Distribution + DistributionAllocation created
                    └───────────┘
```

- **DRAFT**: K-1 uploaded and parsed. Fields extracted but not yet reviewed. Entity/asset not mapped. Asset type not classified.
- **CONFIRMED**: User has reviewed all fields, set asset type, mapped entity and asset, and clicked "Confirm & Save". Portfolio records (Distribution, etc.) are created atomically.

---

## Validation Rules

1. **On upload**: PDF file must pass `validate_pdf_file` (magic bytes, extension, MIME, size ≤ 10 MB)
2. **On confirmation**:
   - `asset_type_classification` must be set (not null/empty)
   - `entity` must be set (FK required)
   - `asset` must be set (FK required)
   - `tax_year` must be in range 2020–current year
   - If duplicate detected (same EIN/TIN/year), user must acknowledge before proceeding
3. **Monetary fields**: All DecimalField(15,2) — matches existing model patterns (Distribution, Commitment, CapitalCall, FMVSnapshot)
4. **Percentage fields**: DecimalField(10,6) — matches existing EntityAssetOwnership.percentage pattern
