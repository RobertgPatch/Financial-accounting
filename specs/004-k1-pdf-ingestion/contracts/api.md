# API Contracts: K-1 PDF Ingestion

**Feature**: 004-k1-pdf-ingestion  
**Date**: 2026-03-04  
**Base URL**: `/api/`

---

## Endpoints Overview

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/k1-documents/upload/` | Upload K-1 PDF and extract fields |
| GET | `/api/k1-documents/` | List all K-1 documents (filterable) |
| GET | `/api/k1-documents/{id}/` | Get K-1 document detail with all extracted data |
| PUT | `/api/k1-documents/{id}/` | Update K-1 document (edit extracted fields, classify) |
| POST | `/api/k1-documents/{id}/confirm/` | Confirm K-1 and create portfolio records |
| GET | `/api/k1-documents/{id}/download/` | Download original PDF |
| DELETE | `/api/k1-documents/{id}/` | Delete K-1 document (draft only) |
| POST | `/api/k1-documents/{id}/check-duplicate/` | Check for potential duplicates |

---

## POST /api/k1-documents/upload/

Upload a K-1 PDF. System extracts fields and returns structured data in draft status.

### Request

- **Content-Type**: `multipart/form-data`
- **Body**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| document | File (PDF) | Yes | K-1 PDF file, max 10 MB |

### Response (201 Created)

```json
{
  "id": 42,
  "status": "draft",
  "tax_year": 2025,
  "is_final": true,
  "is_amended": false,
  "extraction_method": "text",
  "original_filename": "Sch. K-1.pdf",
  "uploaded_at": "2026-03-04T15:30:00Z",
  "entity": null,
  "asset": null,
  "asset_type_classification": null,
  "partnership_info": {
    "ein": "65-1123456",
    "name": "Example Partners LP",
    "address": "123 Main Street",
    "city": "New York",
    "state": "NY",
    "zip_code": "10001",
    "irs_center": "E-FILE",
    "is_ptp": false
  },
  "partner_info": {
    "tin": "XXX-XX-1234",
    "name": "John Smith",
    "address": "456 Oak Ave",
    "city": "Chicago",
    "state": "IL",
    "zip_code": "60601",
    "is_general_partner": false,
    "is_domestic": true,
    "entity_type": "",
    "is_retirement_plan": false,
    "profit_beginning_pct": "3.032900",
    "profit_ending_pct": "0.000000",
    "loss_beginning_pct": "3.032900",
    "loss_ending_pct": "0.000000",
    "capital_beginning_pct": "3.032900",
    "capital_ending_pct": "0.000000",
    "nonrecourse_beginning": "498211.00",
    "nonrecourse_ending": null,
    "qualified_nonrecourse_beginning": null,
    "qualified_nonrecourse_ending": null,
    "recourse_beginning": null,
    "recourse_ending": null,
    "has_lower_tier_liabilities": true,
    "has_guarantee_obligations": false,
    "section_704c_beginning": "-5373.00",
    "section_704c_ending": null,
    "built_in_gain": false
  },
  "income_items": [
    {
      "id": 1,
      "line_number": "1",
      "code": null,
      "description": "Ordinary business income (loss)",
      "amount": null,
      "raw_text": "",
      "is_supplemental": false
    },
    {
      "id": 2,
      "line_number": "11",
      "code": "ZZ",
      "description": "Other income (loss)",
      "amount": "-409615.00",
      "raw_text": "ZZ* (409,615)",
      "is_supplemental": false
    },
    {
      "id": 3,
      "line_number": "19",
      "code": "A",
      "description": "Distributions - Cash",
      "amount": "4493757.00",
      "raw_text": "A 4,493,757",
      "is_supplemental": false
    },
    {
      "id": 4,
      "line_number": "20",
      "code": "A",
      "description": "Other information",
      "amount": null,
      "raw_text": "A SEE STMT",
      "is_supplemental": false
    }
  ],
  "capital_account": {
    "beginning_balance": "4903568.00",
    "capital_contributed": null,
    "net_income": "-409811.00",
    "other_increase_decrease": null,
    "withdrawals": "4493757.00",
    "ending_balance": null,
    "tax_basis_method": ""
  },
  "warnings": [
    "Line 20 code A references supplemental statement - manual entry may be needed",
    "Line 20 code B references supplemental statement - manual entry may be needed"
  ]
}
```

### Error Responses

| Status | Body | Condition |
|--------|------|-----------|
| 400 | `{"document": ["Only PDF files are allowed."]}` | Non-PDF file uploaded |
| 400 | `{"document": ["File size exceeds the 10 MB limit."]}` | File too large |
| 400 | `{"document": ["File does not appear to be a valid PDF."]}` | Invalid magic bytes |
| 422 | `{"error": "Could not recognize this document as a Schedule K-1 (Form 1065)."}` | PDF parsed but no K-1 fields found |

---

## GET /api/k1-documents/

List all K-1 documents with filtering and pagination.

### Query Parameters

| Param | Type | Notes |
|-------|------|-------|
| tax_year | int | Filter by tax year |
| entity | int | Filter by entity ID |
| asset_type | string | Filter by asset_type_classification |
| status | string | Filter by status (draft/confirmed) |
| page | int | Pagination (default page size: 100) |

### Response (200 OK)

```json
{
  "count": 12,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 42,
      "tax_year": 2025,
      "status": "confirmed",
      "asset_type_classification": "private_equity",
      "is_final": true,
      "is_amended": false,
      "original_filename": "Sch. K-1.pdf",
      "uploaded_at": "2026-03-04T15:30:00Z",
      "confirmed_at": "2026-03-04T15:35:00Z",
      "entity": {
        "id": 1,
        "name": "Acme Capital LLC"
      },
      "asset": {
        "id": 5,
        "name": "Example Partners LP"
      },
      "partnership_name": "Example Partners LP",
      "total_distributions": "4493757.00",
      "net_income": "-409811.00"
    }
  ]
}
```

---

## GET /api/k1-documents/{id}/

Full detail of a K-1 document including all extracted fields. Same shape as the upload response but includes entity/asset data if mapped.

### Response (200 OK)

Same as POST upload response, plus `confirmed_at` field and populated `entity`/`asset` objects if set.

---

## PUT /api/k1-documents/{id}/

Update extracted fields, set entity/asset mapping, classify asset type. Used during the review step.

### Request (JSON)

```json
{
  "entity": 1,
  "asset": 5,
  "tax_year": 2025,
  "asset_type_classification": "private_equity",
  "notes": "Final K-1 for 2025",
  "partnership_info": {
    "ein": "65-1123456",
    "name": "Example Partners LP"
  },
  "partner_info": {
    "profit_beginning_pct": "3.032900"
  },
  "income_items": [
    {
      "id": 2,
      "amount": "-409615.00"
    }
  ],
  "capital_account": {
    "beginning_balance": "4903568.00",
    "ending_balance": "0.00"
  }
}
```

### Response (200 OK)

Full K-1 document detail (same shape as GET detail).

---

## POST /api/k1-documents/{id}/confirm/

Confirm a draft K-1 document, creating portfolio records (Distribution, DistributionAllocation).

### Prerequisites
- `status` must be `draft`
- `entity` must be set
- `asset` must be set
- `asset_type_classification` must be set

### Request (JSON)

```json
{
  "duplicate_action": "skip"
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| duplicate_action | string | Only if duplicate detected | "skip" / "overwrite" / "create_new" |

### Response (200 OK)

```json
{
  "id": 42,
  "status": "confirmed",
  "confirmed_at": "2026-03-04T15:35:00Z",
  "created_records": {
    "distribution": {
      "id": 15,
      "asset": 5,
      "distribution_date": "2025-12-31",
      "total_amount": "4493757.00"
    },
    "distribution_allocation": {
      "id": 22,
      "entity": 1,
      "amount": "4493757.00"
    }
  }
}
```

### Error Responses

| Status | Body | Condition |
|--------|------|-----------|
| 400 | `{"error": "Asset type classification is required before confirmation."}` | Missing classification |
| 400 | `{"error": "Entity must be selected before confirmation."}` | Missing entity |
| 400 | `{"error": "Asset must be selected before confirmation."}` | Missing asset |
| 409 | `{"duplicate": true, "existing_id": 38, "message": "A K-1 for this partnership/partner/year already exists."}` | Duplicate detected, no duplicate_action provided |

---

## POST /api/k1-documents/{id}/check-duplicate/

Pre-check for duplicates before confirmation.

### Response (200 OK)

```json
{
  "is_duplicate": true,
  "existing_documents": [
    {
      "id": 38,
      "tax_year": 2025,
      "partnership_name": "Example Partners LP",
      "status": "confirmed",
      "confirmed_at": "2026-02-15T10:00:00Z"
    }
  ]
}
```

---

## GET /api/k1-documents/{id}/download/

Stream the original uploaded PDF file.

### Response (200 OK)

- **Content-Type**: `application/pdf`
- **Content-Disposition**: `inline; filename="Sch. K-1.pdf"`
- Body: raw PDF bytes

---

## DELETE /api/k1-documents/{id}/

Delete a K-1 document. Only draft documents can be deleted.

### Response

| Status | Condition |
|--------|-----------|
| 204 No Content | Successfully deleted (draft) |
| 400 | `{"error": "Confirmed K-1 documents cannot be deleted."}` |

---

## Asset Type Classification Values

Maps to existing `Asset.ASSET_TYPE_CHOICES`:

| Value | Display |
|-------|---------|
| `private_equity` | Private Equity |
| `real_estate` | Real Estate |
| `hedge_fund` | Hedge Fund |
| `public_equity` | Public Equity |
| `fixed_income` | Fixed Income |
| `other` | Other |

Note: `venture_capital` is not currently in `Asset.ASSET_TYPE_CHOICES`. If needed, it should be added to the Asset model choices first. For now, map VC funds to `private_equity` or add the choice in this feature.
