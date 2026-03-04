# API Contract: Portfolio Tracker

**Feature**: 003-portfolio-tracker-redesign | **Date**: 2026-03-04

## New Endpoints

### POST `/api/portfolio/summary/`

Generate Portfolio Summary with entity rollups.

**Request Body** (all optional):
```json
{
  "entity_ids": "1,2",
  "as_of_date": "2026-03-04"
}
```

**Response** `200 OK`:
```json
{
  "as_of_date": "2026-03-04",
  "entities": [
    {
      "entity_id": 1,
      "entity_name": "Entity #1",
      "entity_type": "LLC",
      "original_commitment": "1000000.00",
      "pct_called": "100.00",
      "unfunded_commitment": "0.00",
      "paid_in": "1000000.00",
      "distributions": "2000000.00",
      "residual": "0.00",
      "dpi": "2.00",
      "rvpi": "0.00",
      "tvpi": "2.00",
      "irr": "15.23"
    },
    {
      "entity_id": 2,
      "entity_name": "Entity #2",
      "entity_type": "trust",
      "original_commitment": "0.00",
      "pct_called": null,
      "unfunded_commitment": "0.00",
      "paid_in": "0.00",
      "distributions": "0.00",
      "residual": "0.00",
      "dpi": null,
      "rvpi": null,
      "tvpi": null,
      "irr": null
    }
  ],
  "all_entities": {
    "original_commitment": "1000000.00",
    "pct_called": "100.00",
    "unfunded_commitment": "0.00",
    "paid_in": "1000000.00",
    "distributions": "2000000.00",
    "residual": "0.00",
    "dpi": "2.00",
    "rvpi": "0.00",
    "tvpi": "2.00",
    "irr": "15.23"
  },
  "filters": {
    "entity_ids": [1, 2],
    "as_of_date": "2026-03-04"
  }
}
```

**Notes**:
- `null` for ratio fields (dpi, rvpi, tvpi, irr) when paid_in is zero or XIRR fails to converge
- `pct_called` is `null` when original_commitment is zero
- All monetary values are string-encoded Decimals with 2 decimal places
- Ratios are string-encoded Decimals with 2 decimal places
- IRR is percentage (e.g., "15.23" means 15.23%)

---

### POST `/api/portfolio/asset-class-summary/`

Generate Asset Class Summary with allocation breakdown.

**Request Body** (all optional):
```json
{
  "entity_ids": "1,2",
  "type_filters": ["cash", "real_estate"]
}
```

**Response** `200 OK`:
```json
{
  "total_value": "1000000.00",
  "item_count": 12,
  "by_class": [
    {
      "asset_type": "real_estate",
      "label": "Real Estate",
      "total_value": "500000.00",
      "pct_of_portfolio": "50.00",
      "item_count": 3
    },
    {
      "asset_type": "private_equity",
      "label": "Private Equity",
      "total_value": "300000.00",
      "pct_of_portfolio": "30.00",
      "item_count": 2
    },
    {
      "asset_type": "cash",
      "label": "Cash & Equivalents",
      "total_value": "200000.00",
      "pct_of_portfolio": "20.00",
      "item_count": 7
    }
  ],
  "items": [
    {
      "name": "Beach House",
      "value": "500000.00",
      "source": "manual",
      "asset_type": "real_estate",
      "institution": null,
      "snapshot_date": "2026-02-28"
    }
  ],
  "filters": {
    "entity_ids": [],
    "type_filters": ["cash", "real_estate"]
  }
}
```

**Notes**:
- Reuses existing FMV report core logic (_collect_valued_items) for Plaid+manual item collection and dedup
- `pct_of_portfolio` values sum to 100.00 across all classes
- Empty portfolio returns `total_value: "0.00"`, `by_class: []`, `items: []`

---

### POST `/api/portfolio/performance/`

Generate Investment Performance view.

**Request Body** (all optional):
```json
{
  "entity_ids": "1",
  "as_of_date": "2026-03-04"
}
```

**Response** `200 OK`:
```json
{
  "as_of_date": "2026-03-04",
  "investments": [
    {
      "asset_id": 1,
      "asset_name": "PE Fund I",
      "asset_type": "private_equity",
      "entity_id": 1,
      "entity_name": "Entity #1",
      "original_commitment": "1000000.00",
      "paid_in": "1000000.00",
      "distributions": "2000000.00",
      "residual": "0.00",
      "dpi": "2.00",
      "rvpi": "0.00",
      "tvpi": "2.00",
      "irr": "18.50"
    }
  ],
  "entity_totals": [
    {
      "entity_id": 1,
      "entity_name": "Entity #1",
      "paid_in": "1000000.00",
      "distributions": "2000000.00",
      "residual": "0.00",
      "dpi": "2.00",
      "rvpi": "0.00",
      "tvpi": "2.00",
      "irr": "15.23"
    }
  ],
  "filters": {
    "entity_ids": [1],
    "as_of_date": "2026-03-04"
  }
}
```

**Notes**:
- `investments` is per-asset per-entity (one row per Commitment)
- `entity_totals` is aggregated per entity (pooled XIRR)
- IRR is `null` when XIRR cannot converge or insufficient data

---

### POST `/api/portfolio/summary/export/`

Export Portfolio Summary to Excel.

**Request Body**: Same as `/api/portfolio/summary/`

**Response** `200 OK`:
- Content-Type: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- Content-Disposition: `attachment; filename="portfolio_summary_2026-03-04.xlsx"`
- Body: Excel file binary

---

### POST `/api/portfolio/asset-class-summary/export/`

Export Asset Class Summary to Excel. Same pattern as above.

---

### POST `/api/portfolio/performance/export/`

Export Investment Performance to Excel. Same pattern as above.

---

## CRUD Endpoints

### Commitments

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/commitments/` | List all commitments (supports `?entity=` and `?asset=` filters) |
| POST | `/api/commitments/` | Create commitment |
| GET | `/api/commitments/{id}/` | Get commitment detail |
| PUT | `/api/commitments/{id}/` | Update commitment |
| DELETE | `/api/commitments/{id}/` | Delete commitment |

**Commitment object**:
```json
{
  "id": 1,
  "entity": 1,
  "entity_name": "Entity #1",
  "asset": 1,
  "asset_name": "PE Fund I",
  "commitment_date": "2024-01-15",
  "original_amount": "1000000.00",
  "notes": null,
  "paid_in": "600000.00",
  "pct_called": "60.00",
  "unfunded": "400000.00",
  "call_count": 3,
  "created_at": "2026-03-04T12:00:00Z",
  "updated_at": "2026-03-04T12:00:00Z"
}
```

**Notes**:
- `paid_in`, `pct_called`, `unfunded`, `call_count` are read-only computed fields
- POST/PUT only accept: `entity`, `asset`, `commitment_date`, `original_amount`, `notes`
- Returns 400 if entity+asset pair already exists (unique constraint)

### Capital Calls

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/capital-calls/` | List all capital calls (supports `?commitment=` filter) |
| POST | `/api/capital-calls/` | Create capital call |
| GET | `/api/capital-calls/{id}/` | Get capital call detail |
| PUT | `/api/capital-calls/{id}/` | Update capital call |
| DELETE | `/api/capital-calls/{id}/` | Delete capital call |

**CapitalCall object**:
```json
{
  "id": 1,
  "commitment": 1,
  "commitment_display": "Entity #1 → PE Fund I",
  "call_date": "2024-06-15",
  "amount": "200000.00",
  "notes": null,
  "created_at": "2026-03-04T12:00:00Z"
}
```

**Notes**:
- If call causes overcall (sum > original_amount), response includes `warnings: ["Capital calls exceed original commitment"]` but still saves (200 OK)
