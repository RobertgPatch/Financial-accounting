# API Contract: Performance Analytics

**Base path**: `/api/`  
**Auth**: None (single-tenant)  
**Format**: JSON (DRF)

---

## Endpoints

### `GET /api/assets/{id}/performance/`

Calculate TWR and IRR for a single asset.

**Query parameters**:
| Parameter    | Type   | Default            | Description                                         |
|-------------|--------|--------------------|----------------------------------------------------|
| `period`    | string | `since_inception`  | One of: `ytd`, `1y`, `3y`, `5y`, `since_inception` |
| `start_date`| date   | —                  | Custom start (ISO 8601). Overrides `period`.       |
| `end_date`  | date   | today              | Custom end (ISO 8601). Overrides `period`.         |

**Response** `200 OK`:
```json
{
  "asset_id": 5,
  "asset_name": "Chase Brokerage",
  "asset_type": "public_equity",
  "period": {
    "label": "1y",
    "start_date": "2025-02-28",
    "end_date": "2026-02-28"
  },
  "metrics": {
    "twr_pct": 12.45,
    "irr_pct": 11.82,
    "beginning_value": "100000.00",
    "ending_value": "112450.00",
    "net_distributions": "5000.00",
    "net_contributions": "0.00",
    "gain_loss": "17450.00"
  },
  "fmv_series": [
    {
      "date": "2025-02-28",
      "value": "100000.00",
      "source": "plaid"
    },
    {
      "date": "2025-03-31",
      "value": "103200.00",
      "source": "plaid"
    }
  ],
  "data_quality": {
    "snapshots_count": 12,
    "avg_gap_days": 30,
    "has_gaps_over_90_days": false
  }
}
```

**Errors**:
- `404` — Asset not found
- `422` — Insufficient FMV data for calculation (< 2 snapshots in range)

---

### `GET /api/entities/{id}/performance/`

Calculate aggregated performance for all assets owned by an entity, weighted by ownership percentage.

**Query parameters**: Same as asset performance.

**Response** `200 OK`:
```json
{
  "entity_id": 1,
  "entity_name": "John Smith Trust",
  "period": {
    "label": "ytd",
    "start_date": "2026-01-01",
    "end_date": "2026-02-28"
  },
  "aggregate_metrics": {
    "twr_pct": 8.32,
    "irr_pct": 7.95,
    "beginning_value": "5000000.00",
    "ending_value": "5416000.00",
    "total_distributions": "25000.00",
    "total_contributions": "0.00",
    "total_gain_loss": "441000.00"
  },
  "asset_breakdown": [
    {
      "asset_id": 5,
      "asset_name": "Chase Brokerage",
      "asset_type": "public_equity",
      "ownership_pct": "100.00",
      "twr_pct": 12.45,
      "irr_pct": 11.82,
      "beginning_value": "100000.00",
      "ending_value": "112450.00",
      "weight_pct": 2.07
    }
  ]
}
```

**Errors**:
- `404` — Entity not found
- `422` — No assets with FMV data for this entity

---

### `GET /api/performance/summary/`

Portfolio-wide performance summary across all entities (dashboard widget data).

**Query parameters**:
| Parameter    | Type   | Default   | Description                    |
|-------------|--------|-----------|---------------------------------|
| `period`    | string | `ytd`     | Same options as asset endpoint  |

**Response** `200 OK`:
```json
{
  "period": {
    "label": "ytd",
    "start_date": "2026-01-01",
    "end_date": "2026-02-28"
  },
  "total_portfolio": {
    "beginning_value": "15000000.00",
    "ending_value": "15832000.00",
    "twr_pct": 5.55,
    "irr_pct": 5.12,
    "net_gain_loss": "832000.00"
  },
  "by_asset_type": [
    {
      "asset_type": "public_equity",
      "label": "Public Equity",
      "current_value": "4500000.00",
      "allocation_pct": 28.42,
      "twr_pct": 8.20
    },
    {
      "asset_type": "real_estate",
      "label": "Real Estate",
      "current_value": "6000000.00",
      "allocation_pct": 37.90,
      "twr_pct": 3.10
    }
  ],
  "top_performers": [
    {
      "asset_id": 5,
      "asset_name": "Chase Brokerage",
      "twr_pct": 12.45
    }
  ],
  "bottom_performers": [
    {
      "asset_id": 8,
      "asset_name": "Municipal Bond Fund",
      "twr_pct": -1.20
    }
  ]
}
```

---

## Calculation Notes

- **TWR**: Sub-period returns between snapshots, compounded geometrically. External cash flows (distributions/contributions on snapshot dates) used to split periods.
- **IRR**: Newton's method XIRR on irregular-date cash flows. Returns `null` if solver doesn't converge in 100 iterations.
- **Ownership weighting**: Entity performance uses `EntityAssetOwnership.ownership_percentage` as weight.
- **Minimum data**: At least 2 FMV snapshots required in the selected period. Return 422 if insufficient.
