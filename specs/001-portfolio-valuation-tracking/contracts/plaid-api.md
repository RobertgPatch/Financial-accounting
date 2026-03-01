# API Contract: Plaid Integration

**Base path**: `/api/plaid/`  
**Auth**: None (single-tenant)  
**Format**: JSON (DRF)  
**Django app**: `plaid_integration`

---

## Endpoints

### `POST /api/plaid/create-link-token/`

Create a Plaid Link token for the frontend.

**Request body**: (empty or optional)
```json
{
  "products": ["investments"]
}
```

**Response** `200 OK`:
```json
{
  "link_token": "link-sandbox-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "expiration": "2026-02-28T18:30:00Z"
}
```

**Errors**:
- `503` — Plaid API unavailable

---

### `POST /api/plaid/exchange-token/`

Exchange a public token for an access token after Plaid Link completes. Creates PlaidItem and PlaidAccount records.

**Request body**:
```json
{
  "public_token": "public-sandbox-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "institution": {
    "institution_id": "ins_109508",
    "name": "Chase"
  },
  "accounts": [
    {
      "id": "account_abc123",
      "name": "Brokerage Account",
      "mask": "1234",
      "type": "investment",
      "subtype": "brokerage"
    }
  ]
}
```

**Response** `201 Created`:
```json
{
  "plaid_item_id": 1,
  "institution_name": "Chase",
  "accounts": [
    {
      "id": 1,
      "account_id": "account_abc123",
      "name": "Brokerage Account",
      "mask": "1234",
      "type": "investment",
      "subtype": "brokerage",
      "asset": null,
      "current_balance": null
    }
  ]
}
```

**Errors**:
- `400` — Missing or invalid public_token
- `502` — Plaid API rejected the token exchange

---

### `GET /api/plaid/items/`

List all linked Plaid institutions.

**Response** `200 OK`:
```json
[
  {
    "id": 1,
    "institution_name": "Chase",
    "status": "active",
    "last_synced": "2026-02-28T10:00:00Z",
    "accounts_count": 3,
    "created_at": "2026-02-15T09:00:00Z"
  }
]
```

---

### `GET /api/plaid/items/{id}/accounts/`

List accounts for a linked institution.

**Response** `200 OK`:
```json
[
  {
    "id": 1,
    "account_id": "account_abc123",
    "name": "Brokerage Account",
    "mask": "1234",
    "type": "investment",
    "subtype": "brokerage",
    "asset": 5,
    "asset_name": "Chase Brokerage",
    "current_balance": "250000.00",
    "last_synced": "2026-02-28T10:00:00Z"
  }
]
```

---

### `POST /api/plaid/items/{id}/sync/`

Manually trigger a balance sync for all accounts under a Plaid item. Creates FMV snapshots for mapped assets.

**Request body**: (empty)

**Response** `200 OK`:
```json
{
  "synced_accounts": 3,
  "fmv_snapshots_created": 2,
  "errors": [],
  "last_synced": "2026-02-28T14:30:00Z"
}
```

**Errors**:
- `502` — Plaid API error
- `409` — Item needs re-link (`status = needs_relink`)

---

### `PATCH /api/plaid/accounts/{id}/map-asset/`

Map a Plaid account to an existing asset.

**Request body**:
```json
{
  "asset_id": 5
}
```

**Response** `200 OK`:
```json
{
  "id": 1,
  "account_id": "account_abc123",
  "name": "Brokerage Account",
  "asset": 5,
  "asset_name": "Chase Brokerage"
}
```

**Errors**:
- `400` — Asset not found
- `409` — Asset already mapped to another Plaid account

---

### `DELETE /api/plaid/items/{id}/`

Unlink a Plaid institution. Removes PlaidItem and PlaidAccount records. Does NOT delete FMV snapshots (historical data preserved).

**Response** `204 No Content`.
