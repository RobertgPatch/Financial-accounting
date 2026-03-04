# Data Model: FMV Auto-Reporting

**Feature**: 002-fmv-auto-reporting | **Date**: 2026-02-28

## Overview

This feature requires **no new models or migrations**. All data is sourced from existing models created in feature 001 (portfolio-valuation-tracking). The FMV report is a computed view that aggregates data from `PlaidAccount` and `Asset`/`FMVSnapshot` at query time.

---

## Existing Entities (No Changes)

### PlaidAccount (plaid_integration app)

Primary source for automatic FMV data.

| Field | Type | Notes |
|-------|------|-------|
| `id` | AutoField (PK) | |
| `plaid_item` | FK → PlaidItem | Institution link |
| `account_id` | CharField(255), unique | Plaid's account identifier |
| `name` | CharField(255) | Account display name (e.g., "Chase Checking") |
| `mask` | CharField(10), nullable | Last 4 digits |
| `type` | CharField(50) | Plaid type: `depository`, `investment`, `loan`, `credit` |
| `subtype` | CharField(50), nullable | Plaid subtype: `checking`, `savings`, `401k`, `brokerage`, etc. |
| `asset` | FK → Asset, nullable | Optional mapping to a manual asset (SET_NULL) |
| `current_balance` | DecimalField(15,2), nullable | Latest synced balance |
| `last_synced` | DateTimeField, nullable | When balance was last updated |

**FMV Report Usage**: All PlaidAccount rows are included in the FMV report. `current_balance` provides the value. `type` determines the asset category via `PLAID_TYPE_MAP`. If `asset` is set, the mapped asset's `asset_type` overrides the Plaid type mapping.

### Asset (api app)

Source for manually-tracked assets in the FMV report.

| Field | Type | Notes |
|-------|------|-------|
| `id` | AutoField (PK) | |
| `name` | CharField(255) | Asset display name |
| `asset_type` | CharField(50) | One of 9 types (see below) |
| `description` | TextField, nullable | |
| `tags` | M2M → AssetTag | Reusable classification tags |

**Asset Type Choices** (used for FMV report type filters):

| Value | Display Label |
|-------|--------------|
| `real_estate` | Real Estate |
| `public_equity` | Public Equity |
| `private_equity` | Private Equity |
| `fixed_income` | Fixed Income |
| `cash` | Cash & Equivalents |
| `hedge_fund` | Hedge Fund |
| `crypto` | Cryptocurrency |
| `collectible` | Collectible |
| `other` | Other |

**FMV Report Usage**: Assets are included only when they have at least one `FMVSnapshot` AND are not mapped to a Plaid account (double-counting prevention).

### FMVSnapshot (api app)

Provides point-in-time valuation for manual assets.

| Field | Type | Notes |
|-------|------|-------|
| `id` | AutoField (PK) | |
| `asset` | FK → Asset | |
| `snapshot_date` | DateField | Unique per asset+date |
| `value` | DecimalField(15,2) | Must be ≥ 0 |
| `source` | CharField(20) | `manual` or `plaid` |
| `notes` | TextField, nullable | |

**FMV Report Usage**: The latest snapshot (by `snapshot_date`) per asset provides the FMV value for manual items.

### EntityAssetOwnership (api app)

Used for entity-based filtering on the FMV report.

| Field | Type | Notes |
|-------|------|-------|
| `entity` | FK → Entity | |
| `asset` | FK → Asset | |
| `percentage` | DecimalField(7,4) | Ownership percentage |
| `effective_date` | DateField | |

**FMV Report Usage**: When entity filter is active, only manual assets with an ownership record to the filtered entity are included. Plaid accounts mapped to such assets are also included. Unmapped Plaid accounts are excluded when entity filter is active.

### PlaidItem (plaid_integration app)

Parent of PlaidAccount, provides institution context.

| Field | Type | Notes |
|-------|------|-------|
| `institution_name` | CharField(255), nullable | Displayed in FMV report line items |
| `status` | CharField(20) | `active`, `error`, `needs_relink` |

---

## New Computed Concept: PLAID_TYPE_MAP

Not a database entity — a Python dict constant in `reports.py`:

```python
PLAID_TYPE_MAP = {
    'depository': 'cash',
    'investment': 'public_equity',
    'loan': 'fixed_income',
    'credit': 'cash',
}
# Fallback: unmapped types → 'other'
```

This maps Plaid account `type` to the Asset `asset_type` choices for categorization in the FMV report.

---

## Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                     FMV Report Generation                        │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Step 1: Collect Plaid accounts                                  │
│  ┌─────────────┐                                                 │
│  │ PlaidAccount │──→ All rows with current_balance               │
│  │  .type       │    Categorize via PLAID_TYPE_MAP               │
│  │  .asset (FK) │    Track mapped_asset_ids for dedup            │
│  └─────────────┘                                                 │
│                                                                  │
│  Step 2: Collect manual assets (excluding mapped)                │
│  ┌─────────┐    ┌─────────────┐                                  │
│  │  Asset   │──→│ FMVSnapshot  │  Latest per asset               │
│  │ (excl.   │    │ (latest by  │  Value used for FMV             │
│  │  mapped) │    │  snap_date) │                                  │
│  └─────────┘    └─────────────┘                                  │
│                                                                  │
│  Step 3: Apply filters                                           │
│  ┌──────────────────────────────────────┐                        │
│  │ type_filters → filter items by type  │                        │
│  │ entity_ids → filter manual assets    │                        │
│  │              by EntityAssetOwnership  │                        │
│  └──────────────────────────────────────┘                        │
│                                                                  │
│  Step 4: Aggregate                                               │
│  ┌──────────────────────────────────────┐                        │
│  │ Group by asset_type → totals, counts │                        │
│  │ Calculate percentages                │                        │
│  │ Grand total across all items         │                        │
│  └──────────────────────────────────────┘                        │
└──────────────────────────────────────────────────────────────────┘
```

---

## Validation Rules

| Rule | Source | Enforcement |
|------|--------|-------------|
| FMV snapshot value ≥ 0 | FMVSnapshot.clean() | Existing model validation |
| Plaid balance can be negative (credit cards, loans) | FR-003, Edge Case | Included as-is in FMV total |
| No double-counting for mapped accounts | FR-012 | `.exclude(id__in=mapped_asset_ids)` in query |
| Manual assets without FMV snapshots excluded | Assumptions | `.filter(fmv_snapshots__isnull=False)` |
| Unmapped Plaid accounts excluded when entity filter active | Research Decision 3 | Conditional query logic |

---

## State Transitions

No state transitions. The FMV report is a stateless read-only computation — it queries current data and returns results. No records are created, updated, or deleted during report generation.
