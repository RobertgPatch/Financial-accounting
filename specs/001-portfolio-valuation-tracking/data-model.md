# Data Model: Portfolio Valuation & Tracking

**Branch**: `001-portfolio-valuation-tracking`  
**Date**: 2026-02-28  
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Research**: [research.md](research.md)

---

## Entity Relationship Diagram (Text)

```
Entity ──< EntityAssetOwnership >── Asset ──< FMVSnapshot
  │                                   │          │
  │                                   │          └── source: manual | plaid
  │                                   │
  │                                   ├──< Distribution ──< DistributionAllocation >── Entity
  │                                   │
  │                                   ├──< BudgetLineItem >── Budget
  │                                   │
  │                                   └──<< AssetTag (M2M)
  │
  └── (aggregate TWR/IRR via ownership)

PlaidItem ──< PlaidAccount ──> Asset (FK, nullable)
```

---

## Existing Entities (Modified)

### Asset (MODIFIED)

Extends the existing `api.Asset` model with expanded type choices and M2M tags.

| Field | Type | Change | Details |
|-------|------|--------|---------|
| `name` | CharField(255) | Unchanged | |
| `asset_type` | CharField(50) | **MODIFIED** | Expanded choices (see below) |
| `description` | TextField | Unchanged | nullable |
| `address` | TextField | Unchanged | nullable |
| `ticker_symbol` | CharField(20) | Unchanged | nullable |
| `tags` | **M2M → AssetTag** | **NEW** | Many-to-many via `asset_tags` intermediate table |
| `created_at` | DateTimeField | Unchanged | auto_now_add |
| `updated_at` | DateTimeField | Unchanged | auto_now |

**Expanded `asset_type` choices**:

| Value | Display | New? |
|-------|---------|------|
| `property` | Property | existing → rename to `real_estate` |
| `real_estate` | Real Estate | ✅ replaces `property` |
| `stock` | Stock | existing → rename to `public_equity` |
| `public_equity` | Public Equity | ✅ replaces `stock` |
| `fund` | Fund | existing → rename to `hedge_fund` |
| `hedge_fund` | Hedge Fund | ✅ replaces `fund` |
| `bond` | Bond | existing → rename to `fixed_income` |
| `fixed_income` | Fixed Income | ✅ replaces `bond` |
| `private_equity` | Private Equity | ✅ new |
| `cash` | Cash & Equivalents | ✅ new |
| `crypto` | Cryptocurrency | ✅ new |
| `collectible` | Collectible | ✅ new |
| `other` | Other | existing |

**Migration strategy**: Data migration to map old values to new: `property`→`real_estate`, `stock`→`public_equity`, `fund`→`hedge_fund`, `bond`→`fixed_income`. Keep `other` as-is.

**Computed properties** (not stored, derived):
- `current_fmv`: Most recent FMVSnapshot value, or `None`
- `current_fmv_date`: Date of most recent FMVSnapshot

---

## New Entities

### FMVSnapshot

Point-in-time fair market value record for an asset.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | AutoField (PK) | | |
| `asset` | FK → Asset | `on_delete=CASCADE`, `related_name='fmv_snapshots'` | |
| `snapshot_date` | DateField | required | Date of the valuation |
| `value` | DecimalField(15, 2) | required, >= 0 | FMV in USD |
| `source` | CharField(20) | choices: `manual`, `plaid` | How this value was obtained |
| `notes` | TextField | nullable, blank | Optional notes |
| `created_at` | DateTimeField | auto_now_add | |

**Indexes**: `(asset, snapshot_date)` unique together — one FMV per asset per date.  
**Ordering**: `['-snapshot_date']`

**Validation rules**:
- `value` must be >= 0 (no negative FMV)
- `snapshot_date` must not be in the future
- One snapshot per asset per date (unique constraint)

---

### AssetTag

Reusable tag for classifying assets.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | AutoField (PK) | | |
| `name` | CharField(100) | required, unique | Display name (e.g., "Illiquid") |
| `slug` | SlugField(100) | required, unique, auto-generated | URL-safe identifier (e.g., "illiquid") |
| `color` | CharField(7) | default `#6B7280` | Hex color for UI chip display |
| `created_at` | DateTimeField | auto_now_add | |

**M2M relationship**: `Asset.tags` → through default Django M2M table  
**Ordering**: `['name']`

**Validation rules**:
- `name` is case-insensitive unique (enforced at save: `name__iexact`)
- `slug` auto-generated from `name` via `django.utils.text.slugify`
- `color` must be valid hex (regex: `^#[0-9A-Fa-f]{6}$`)

---

### PlaidItem

Represents a linked financial institution via Plaid.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | AutoField (PK) | | |
| `item_id` | CharField(255) | unique, required | Plaid's `item_id` |
| `access_token` | CharField(255) | required | Plaid access token (encrypt at rest in production) |
| `institution_id` | CharField(100) | nullable | Plaid institution ID |
| `institution_name` | CharField(255) | nullable | Human-readable institution name |
| `status` | CharField(20) | choices: `active`, `error`, `needs_relink` | Current link status |
| `last_synced` | DateTimeField | nullable | Last successful balance sync |
| `error_message` | TextField | nullable | Last error details |
| `created_at` | DateTimeField | auto_now_add | |
| `updated_at` | DateTimeField | auto_now | |

**Ordering**: `['-created_at']`  
**App**: `plaid_integration`

**Validation rules**:
- `item_id` must be unique
- `access_token` must not be empty

---

### PlaidAccount

An individual account within a Plaid-linked institution.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | AutoField (PK) | | |
| `plaid_item` | FK → PlaidItem | `on_delete=CASCADE`, `related_name='accounts'` | Parent institution link |
| `account_id` | CharField(255) | unique, required | Plaid's `account_id` |
| `name` | CharField(255) | required | Account name from Plaid |
| `mask` | CharField(10) | nullable | Last 4 digits |
| `type` | CharField(50) | required | Plaid account type (investment, depository, credit, etc.) |
| `subtype` | CharField(50) | nullable | Plaid subtype (401k, ira, brokerage, etc.) |
| `asset` | FK → Asset | `on_delete=SET_NULL`, nullable, `related_name='plaid_accounts'` | Mapped asset (null = unmapped) |
| `current_balance` | DecimalField(15, 2) | nullable | Last known balance |
| `last_synced` | DateTimeField | nullable | Last balance update |
| `created_at` | DateTimeField | auto_now_add | |

**Ordering**: `['plaid_item', 'name']`  
**App**: `plaid_integration`

**Validation rules**:
- `account_id` must be unique
- `asset` is nullable (unmapped accounts exist until user maps them)

---

## State Transitions

### PlaidItem.status

```
[created] → active → error → needs_relink → active (re-linked)
                  ↘ needs_relink → active (re-linked)
```

| From | To | Trigger |
|------|----|---------|
| (created) | `active` | Successful token exchange |
| `active` | `error` | Sync failure (API error, rate limit) |
| `active` | `needs_relink` | Token expiration / ITEM_LOGIN_REQUIRED |
| `error` | `active` | Successful re-sync |
| `needs_relink` | `active` | User re-links via Plaid Link update mode |

### FMVSnapshot.source

No transitions — set once at creation:
- `manual`: User entered via UI
- `plaid`: Auto-created by Plaid balance sync

---

## Relationships Summary

| From | To | Type | Notes |
|------|----|------|-------|
| Asset | FMVSnapshot | 1:N | `asset.fmv_snapshots.all()` |
| Asset | AssetTag | M2M | `asset.tags.all()` |
| Asset | PlaidAccount | 1:N | `asset.plaid_accounts.all()` (nullable FK) |
| PlaidItem | PlaidAccount | 1:N | `plaid_item.accounts.all()` |
| Entity | Asset | M2M (via EntityAssetOwnership) | Existing, unchanged |
| Asset | Distribution | 1:N | Existing, unchanged |

---

## Migration Plan

### Migration 0003: Expand Asset types + AssetTag

1. Add `AssetTag` model
2. Add `Asset.tags` M2M field
3. Alter `Asset.asset_type` choices (expanded list)
4. Data migration: `property`→`real_estate`, `stock`→`public_equity`, `fund`→`hedge_fund`, `bond`→`fixed_income`

### Migration 0004: FMVSnapshot

1. Add `FMVSnapshot` model with unique constraint on `(asset, snapshot_date)`

### Migration 0001 (plaid_integration): PlaidItem + PlaidAccount

1. Add `PlaidItem` model
2. Add `PlaidAccount` model with FK to `PlaidItem` and nullable FK to `api.Asset`
