# API Contract: Performance Analytics

**Base path**: `/api/`  
**Auth**: None (single-tenant)  
**Format**: JSON (DRF)

---

## Endpoints

### `GET /api/assets/{id}/performance/`

Calculate TWR and IRR for a single asset across all standard periods.

**Query parameters**:
| Parameter    | Type   | Default | Description                                         |
|-------------|--------|---------|-----------------------------------------------------|
| `calc_date` | date   | today   | ISO 8601 date to use as the calculation end date.  |

**Response** `200 OK`:
```json
{
  "asset_id": 5,
  "asset_name": "Chase Brokerage",
  "metrics": {
    "ytd": {
      "label": "YTD",
      "start_date": "2026-01-01",
      "end_date": "2026-02-28",
      "days": 58,
      "twr": 0.0412,
      "annualized_twr": 0.2634,
      "irr": null,
      "annualized_irr": null,
      "data_quality": {
        "snapshots_count": 3,
        "has_gaps": false
      }
    },
    "1y": {
      "label": "1Y",
      "start_date": "2025-02-28",
      "end_date": "2026-02-28",
      "days": 365,
      "twr": 0.1245,
      "annualized_twr": 0.1245,
      "irr": 0.1182,
      "annualized_irr": 0.1182,
      "data_quality": {
        "snapshots_count": 12,
        "has_gaps": false
      }
    },
    "3y": {
      "label": "3Y",
      "start_date": "2023-02-28",
      "end_date": "2026-02-28",
      "days": 1095,
      "twr": null,
      "annualized_twr": null,
      "irr": null,
      "annualized_irr": null,
      "data_quality": {}
    },
    "since_inception": {
      "label": "Since Inception",
      "start_date": "2024-06-01",
      "end_date": "2026-02-28",
      "days": 637,
      "twr": 0.0890,
      "annualized_twr": 0.0510,
      "irr": null,
      "annualized_irr": null,
      "data_quality": {
        "snapshots_count": 8,
        "has_gaps": false
      }
    }
  },
  "fmv_series": [
    {"snapshot_date": "2025-02-28", "value": "100000.00"},
    {"snapshot_date": "2025-03-31", "value": "103200.00"}
  ]
}
```

**Errors**:
- `404` — Asset not found
- `400` — Invalid `calc_date` format

---

### `GET /api/entities/{id}/performance/`

Calculate aggregated performance for all assets owned by an entity, weighted by ownership percentage.

**Query parameters**:
| Parameter    | Type   | Default | Description                                         |
|-------------|--------|---------|-----------------------------------------------------|
| `calc_date` | date   | today   | ISO 8601 date to use as the calculation end date.  |

**Response** `200 OK`:
```json
{
  "entity_id": 1,
  "metrics": {
    "ytd": {
      "label": "YTD",
      "start_date": "2026-01-01",
      "end_date": "2026-02-28",
      "days": 58,
      "twr": 0.0832,
      "irr": 0.0795
    },
    "1y": {
      "label": "1Y",
      "start_date": "2025-02-28",
      "end_date": "2026-02-28",
      "days": 365,
      "twr": null,
      "irr": null
    },
    "3y": {
      "label": "3Y",
      "start_date": "2023-02-28",
      "end_date": "2026-02-28",
      "days": 1095,
      "twr": null,
      "irr": null
    },
    "since_inception": {
      "label": "Since Inception",
      "start_date": "2024-06-01",
      "end_date": "2026-02-28",
      "days": 637,
      "twr": null,
      "irr": null
    }
  },
  "assets": [
    {
      "asset_id": 5,
      "asset_name": "Chase Brokerage",
      "ownership_pct": 100.0,
      "current_fmv": "112450.00",
      "entity_share": "112450.00"
    }
  ]
}
```

**Errors**:
- `404` — Entity not found
- `400` — Invalid `calc_date` format

---

### `GET /api/performance/summary/`

Portfolio-wide performance summary across all assets (dashboard widget data).

**Query parameters**:
| Parameter    | Type   | Default | Description                                         |
|-------------|--------|---------|-----------------------------------------------------|
| `calc_date` | date   | today   | ISO 8601 date to use as the calculation end date.  |

**Response** `200 OK`:
```json
{
  "total_assets": 10,
  "total_fmv": "15000000.0",
  "by_asset_type": {
    "public_equity": {"count": 3, "total_fmv": 4500000.0},
    "real_estate": {"count": 4, "total_fmv": 6000000.0}
  },
  "top_performers": [
    {
      "asset_id": 5,
      "asset_name": "Chase Brokerage",
      "asset_type": "public_equity",
      "current_fmv": "112450.00",
      "ytd_twr": 0.1245
    }
  ],
  "bottom_performers": [
    {
      "asset_id": 8,
      "asset_name": "Municipal Bond Fund",
      "asset_type": "fixed_income",
      "current_fmv": "50000.00",
      "ytd_twr": -0.0120
    }
  ],
  "all_assets": [
    {
      "asset_id": 5,
      "asset_name": "Chase Brokerage",
      "asset_type": "public_equity",
      "current_fmv": "112450.00",
      "ytd_twr": 0.1245
    }
  ]
}
```

**Errors**:
- `400` — Invalid `calc_date` format

---

## Calculation Notes

- **TWR**: Sub-period returns between snapshots, compounded geometrically. External cash flows (distributions/contributions on snapshot dates) used to split periods.
- **IRR**: Newton's method XIRR on irregular-date cash flows with Brent's method fallback. Returns `null` if solver doesn't converge.
- **Periods**: Always returns metrics for `ytd`, `1y`, `3y`, and `since_inception`. A period's `twr`/`irr` will be `null` if there are fewer than 2 FMV snapshots in that range.
- **Ownership weighting**: Entity performance uses value-weighted TWR (beginning-of-period FMV × ownership %) and combined XIRR across all owned assets.
- **`since_inception`**: Uses the date of the first FMV snapshot for the asset (or earliest across all entity-owned assets for entity performance).
