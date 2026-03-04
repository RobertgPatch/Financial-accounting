# API Contract: FMV Report

**Feature**: 002-fmv-auto-reporting | **Date**: 2026-02-28

This document defines the REST API contracts for the FMV report endpoints. Existing Distribution report endpoints remain unchanged.

---

## Endpoints Summary

| Method | URL | Description |
|--------|-----|-------------|
| `POST` | `/api/reports/fmv/generate/` | Generate FMV report |
| `POST` | `/api/reports/fmv/export/` | Export FMV report to Excel |

Existing (unchanged):
| Method | URL | Description |
|--------|-----|-------------|
| `POST` | `/api/reports/generate/` | Generate Distribution report |
| `POST` | `/api/reports/export/` | Export Distribution report to Excel |

---

## POST /api/reports/fmv/generate/

Generate a consolidated FMV report combining Plaid account balances and manual asset FMV snapshots.

### Request

```json
{
  "type_filters": ["cash", "real_estate", "public_equity"],
  "entity_ids": "1,2,3"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type_filters` | `string[]` | No | Filter by asset type categories. Values from Asset.ASSET_TYPE_CHOICES: `real_estate`, `public_equity`, `private_equity`, `fixed_income`, `cash`, `hedge_fund`, `crypto`, `collectible`, `other`. If omitted or empty, all types included. |
| `entity_ids` | `string` | No | Comma-separated entity IDs. When set, only includes: (a) manual assets with ownership records to these entities, (b) Plaid accounts mapped to assets owned by these entities. Unmapped Plaid accounts are excluded. |

### Response (200 OK)

```json
{
  "total_fmv": "935000.00",
  "item_count": 8,
  "filters": {
    "type_filters": ["cash", "real_estate", "public_equity"],
    "entity_ids": [1, 2, 3]
  },
  "by_type": [
    {
      "asset_type": "real_estate",
      "label": "Real Estate",
      "total_value": "500000.00",
      "count": 2,
      "percentage": "53.48"
    },
    {
      "asset_type": "cash",
      "label": "Cash & Equivalents",
      "total_value": "250000.00",
      "count": 4,
      "percentage": "26.74"
    },
    {
      "asset_type": "public_equity",
      "label": "Public Equity",
      "total_value": "185000.00",
      "count": 2,
      "percentage": "19.79"
    }
  ],
  "items": [
    {
      "name": "Beach House",
      "value": "350000.00",
      "source": "manual",
      "asset_type": "real_estate",
      "label": "Real Estate",
      "asset_id": 5,
      "snapshot_date": "2026-02-15",
      "institution": null,
      "subtype": null,
      "plaid_account_id": null,
      "mask": null,
      "needs_sync": false
    },
    {
      "name": "Chase Checking",
      "value": "45000.00",
      "source": "plaid",
      "asset_type": "cash",
      "label": "Cash & Equivalents",
      "asset_id": null,
      "snapshot_date": null,
      "institution": "Chase",
      "subtype": "checking",
      "plaid_account_id": 1,
      "mask": "1234",
      "needs_sync": false
    },
    {
      "name": "Fidelity 401k",
      "value": "185000.00",
      "source": "plaid",
      "asset_type": "public_equity",
      "label": "Public Equity",
      "asset_id": null,
      "snapshot_date": null,
      "institution": "Fidelity",
      "subtype": "401k",
      "plaid_account_id": 3,
      "mask": "5678",
      "needs_sync": false
    },
    {
      "name": "Visa Credit Card",
      "value": "-3500.00",
      "source": "plaid",
      "asset_type": "cash",
      "label": "Cash & Equivalents",
      "asset_id": null,
      "snapshot_date": null,
      "institution": "Chase",
      "subtype": "credit card",
      "plaid_account_id": 2,
      "mask": "9012",
      "needs_sync": false
    }
  ]
}
```

### Response Fields

**Top-level:**

| Field | Type | Description |
|-------|------|-------------|
| `total_fmv` | `string` (Decimal) | Grand total of all included items. May be negative if liabilities exceed assets. |
| `item_count` | `int` | Number of line items in the report. |
| `filters` | `object` | Echo of applied filters for frontend display. |

**`by_type[]` (type breakdown):**

| Field | Type | Description |
|-------|------|-------------|
| `asset_type` | `string` | Asset type key (matches `Asset.ASSET_TYPE_CHOICES`). |
| `label` | `string` | Human-readable display label for the asset type. |
| `total_value` | `string` (Decimal) | Sum of all item values in this type. |
| `count` | `int` | Number of items in this type. |
| `percentage` | `string` (Decimal) | Percentage of `total_fmv` this type represents. Calculated as `(total_value / total_fmv * 100)`. |

**`items[]` (line items):**

| Field | Type | Description |
|-------|------|-------------|
| `name` | `string` | Account or asset name. |
| `value` | `string` (Decimal) | FMV value. Plaid: `current_balance`. Manual: latest `FMVSnapshot.value`. |
| `source` | `string` | `"plaid"` or `"manual"`. |
| `asset_type` | `string` | Categorized type. Plaid: from `PLAID_TYPE_MAP` (or mapped asset's type). Manual: from `Asset.asset_type`. |
| `label` | `string` | Human-readable type label. |
| `asset_id` | `int \| null` | Asset ID (for manual items, or for Plaid items mapped to an asset). |
| `snapshot_date` | `string \| null` | Date of the FMV snapshot (manual items only). |
| `institution` | `string \| null` | Plaid institution name (Plaid items only). |
| `subtype` | `string \| null` | Plaid account subtype for display (Plaid items only). |
| `plaid_account_id` | `int \| null` | PlaidAccount ID (Plaid items only). |
| `mask` | `string \| null` | Last 4 digits of account number (Plaid items only). |
| `needs_sync` | `bool` | `true` if Plaid account has never been synced (`current_balance` is null). |

### Edge Cases

| Scenario | Behavior |
|----------|----------|
| No Plaid accounts AND no manual assets | Returns `total_fmv: "0.00"`, `item_count: 0`, empty `by_type` and `items` |
| Plaid account with `current_balance = NULL` | Included with `value: "0.00"` and `needs_sync: true` |
| Negative Plaid balance (credit card) | Included with negative value, reduces `total_fmv` |
| Mapped Plaid account (has `asset` FK) | Uses mapped asset's `asset_type` instead of PLAID_TYPE_MAP |
| Manual asset mapped to Plaid account | Excluded from `items` (Plaid account row represents it) |
| Type filter with no matching items | Returns `total_fmv: "0.00"` for that filter, empty results |
| Entity filter active | Unmapped Plaid accounts excluded; only manual assets with ownership + their mapped Plaid accounts included |

---

## POST /api/reports/fmv/export/

Export the FMV report as an Excel (.xlsx) file. Accepts the same parameters as `/fmv/generate/` and produces a downloadable spreadsheet.

### Request

Same as `POST /api/reports/fmv/generate/` (identical body).

### Response (200 OK)

- **Content-Type**: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- **Content-Disposition**: `attachment; filename="fmv_report_YYYY-MM-DD.xlsx"`
- **Body**: Binary Excel file

### Excel File Structure

| Sheet | Content |
|-------|---------|
| **Summary** | Total FMV, type breakdown table (type, total value, count, percentage), applied filters |
| **Line Items** | All items with columns: Name, Value, Source, Asset Type, Institution, Subtype, Snapshot Date |

---

## Frontend API Client

New functions in `frontend/src/api/reports.js`:

```javascript
// New — FMV report
export const generateFmvReport = (params) =>
  client.post('/reports/fmv/generate/', params);

export const exportFmvReport = async (params) => {
  const response = await client.post('/reports/fmv/export/', params, {
    responseType: 'blob',
  });
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;
  const today = new Date().toISOString().split('T')[0];
  link.setAttribute('download', `fmv_report_${today}.xlsx`);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};

// Existing (unchanged):
// export const generateReport = (params) => client.post('/reports/generate/', params);
// export const exportReport = async (params) => { ... };
```
