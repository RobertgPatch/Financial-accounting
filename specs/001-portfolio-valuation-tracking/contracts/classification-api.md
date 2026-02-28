# API Contract: Asset Classification & Tagging

**Base path**: `/api/`  
**Auth**: None (single-tenant)  
**Format**: JSON (DRF)

---

## Endpoints

### Tags CRUD

#### `GET /api/tags/`

List all asset tags.

**Response** `200 OK`:
```json
[
  {
    "id": 1,
    "name": "High Yield",
    "slug": "high-yield",
    "color": "#10B981",
    "assets_count": 4
  },
  {
    "id": 2,
    "name": "Tax Advantaged",
    "slug": "tax-advantaged",
    "color": "#6366F1",
    "assets_count": 7
  }
]
```

---

#### `POST /api/tags/`

Create a new tag.

**Request body**:
```json
{
  "name": "High Yield",
  "color": "#10B981"
}
```

- `slug` auto-generated from `name` via `django.utils.text.slugify`
- `color` optional, defaults to `"#6B7280"` (gray-500)

**Response** `201 Created`:
```json
{
  "id": 1,
  "name": "High Yield",
  "slug": "high-yield",
  "color": "#10B981",
  "assets_count": 0
}
```

**Errors**:
- `400` — Duplicate name or slug

---

#### `PATCH /api/tags/{id}/`

Update a tag.

**Request body** (partial):
```json
{
  "color": "#EF4444"
}
```

**Response** `200 OK`: Full tag object.

---

#### `DELETE /api/tags/{id}/`

Delete a tag. Removes from all assets (M2M cleared).

**Response** `204 No Content`.

---

### Asset Filtering (Enhanced)

#### `GET /api/assets/`

Enhanced with additional filter parameters.

**New query parameters** (in addition to existing):
| Parameter      | Type   | Description                                                |
|---------------|--------|------------------------------------------------------------|
| `asset_type`  | string | Filter by type (e.g., `public_equity`, `real_estate`)      |
| `tag`         | string | Filter by tag slug. Multiple: `?tag=high-yield&tag=growth` |
| `has_fmv`     | bool   | Filter assets with at least one FMV snapshot               |
| `plaid_linked`| bool   | Filter assets linked to a Plaid account                    |

**Response** `200 OK`:
```json
[
  {
    "id": 5,
    "name": "Chase Brokerage",
    "asset_type": "public_equity",
    "asset_type_display": "Public Equity",
    "description": "Primary brokerage account",
    "tags": [
      {
        "id": 1,
        "name": "High Yield",
        "slug": "high-yield",
        "color": "#10B981"
      }
    ],
    "latest_fmv": "250000.00",
    "latest_fmv_date": "2026-02-28",
    "plaid_linked": true
  }
]
```

---

### Asset Tag Assignment

#### `POST /api/assets/{id}/tags/`

Assign tags to an asset.

**Request body**:
```json
{
  "tag_ids": [1, 2, 3]
}
```

**Behavior**: Replaces all current tag assignments (set semantics, not append).

**Response** `200 OK`:
```json
{
  "asset_id": 5,
  "tags": [
    {"id": 1, "name": "High Yield", "slug": "high-yield", "color": "#10B981"},
    {"id": 2, "name": "Tax Advantaged", "slug": "tax-advantaged", "color": "#6366F1"},
    {"id": 3, "name": "Growth", "slug": "growth", "color": "#F59E0B"}
  ]
}
```

**Errors**:
- `400` — One or more tag_ids not found

---

### Portfolio Allocation Report

#### `GET /api/reports/portfolio-by-class/`

Portfolio allocation breakdown by asset type (for pie/donut chart on dashboard).

**Query parameters**:
| Parameter   | Type   | Default | Description                        |
|------------|--------|---------|------------------------------------|
| `entity_id`| int    | —       | Filter by entity (all if omitted)  |
| `tag`      | string | —       | Filter by tag slug                 |

**Response** `200 OK`:
```json
{
  "total_value": "15000000.00",
  "as_of_date": "2026-02-28",
  "allocations": [
    {
      "asset_type": "real_estate",
      "label": "Real Estate",
      "total_value": "6000000.00",
      "allocation_pct": 40.0,
      "asset_count": 3,
      "assets": [
        {
          "id": 1,
          "name": "123 Main St",
          "value": "2500000.00",
          "pct_of_class": 41.67
        }
      ]
    },
    {
      "asset_type": "public_equity",
      "label": "Public Equity",
      "total_value": "4500000.00",
      "allocation_pct": 30.0,
      "asset_count": 5,
      "assets": [
        {
          "id": 5,
          "name": "Chase Brokerage",
          "value": "250000.00",
          "pct_of_class": 5.56
        }
      ]
    }
  ]
}
```

---

## Asset Type Reference

| Value            | Display Label    |
|-----------------|-----------------|
| `real_estate`   | Real Estate      |
| `public_equity` | Public Equity    |
| `private_equity`| Private Equity   |
| `fixed_income`  | Fixed Income     |
| `cash`          | Cash             |
| `hedge_fund`    | Hedge Fund       |
| `crypto`        | Cryptocurrency   |
| `collectible`   | Collectible      |
| `other`         | Other            |
