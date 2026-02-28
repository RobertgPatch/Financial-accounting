# API Contract: FMV Snapshots

**Base path**: `/api/fmv-snapshots/`  
**Auth**: None (single-tenant)  
**Format**: JSON (DRF)

---

## Endpoints

### `GET /api/fmv-snapshots/`

List all FMV snapshots. Supports filtering.

**Query Parameters**:

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `asset` | integer | no | Filter by asset ID |
| `source` | string | no | Filter by source: `manual` or `plaid` |
| `date_from` | date (YYYY-MM-DD) | no | Snapshots on or after this date |
| `date_to` | date (YYYY-MM-DD) | no | Snapshots on or before this date |

**Response** `200 OK`:
```json
[
  {
    "id": 1,
    "asset": 5,
    "asset_name": "123 Main St Property",
    "snapshot_date": "2026-01-15",
    "value": "1500000.00",
    "source": "manual",
    "notes": "Annual appraisal",
    "created_at": "2026-01-15T10:30:00Z"
  }
]
```

---

### `POST /api/fmv-snapshots/`

Create a new FMV snapshot.

**Request body**:
```json
{
  "asset": 5,
  "snapshot_date": "2026-02-01",
  "value": "1550000.00",
  "source": "manual",
  "notes": "Updated estimate"
}
```

**Response** `201 Created`: Same shape as GET item.

**Errors**:
- `400` — `snapshot_date` in the future, `value` < 0, duplicate (asset, date) pair

---

### `GET /api/fmv-snapshots/{id}/`

Retrieve a single FMV snapshot.

**Response** `200 OK`: Single object (same shape as list item).

---

### `PUT /api/fmv-snapshots/{id}/`

Update an FMV snapshot.

**Request body**: Same as POST (all fields).

**Response** `200 OK`: Updated object.

---

### `DELETE /api/fmv-snapshots/{id}/`

Delete an FMV snapshot.

**Response** `204 No Content`.

---

### `GET /api/assets/{id}/fmv-history/`

Get the FMV timeline for a specific asset (convenience endpoint).

**Response** `200 OK`:
```json
{
  "asset_id": 5,
  "asset_name": "123 Main St Property",
  "current_fmv": "1550000.00",
  "current_fmv_date": "2026-02-01",
  "snapshots": [
    {
      "snapshot_date": "2026-02-01",
      "value": "1550000.00",
      "source": "manual",
      "change_amount": "50000.00",
      "change_pct": "3.33"
    },
    {
      "snapshot_date": "2026-01-15",
      "value": "1500000.00",
      "source": "manual",
      "change_amount": null,
      "change_pct": null
    }
  ]
}
```
