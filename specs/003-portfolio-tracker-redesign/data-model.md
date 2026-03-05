# Data Model: Portfolio Tracker Redesign

**Feature**: 003-portfolio-tracker-redesign | **Date**: 2026-03-04

## New Models

### Commitment

Represents an entity's original commitment to an asset/fund. One per entity-asset pair.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | AutoField | PK | Auto-generated primary key |
| entity | FK → Entity | CASCADE, related_name='commitments' | The investing entity |
| asset | FK → Asset | CASCADE, related_name='commitments' | The investment/fund |
| commitment_date | DateField | required | Date commitment was made |
| original_amount | DecimalField(15,2) | required, >= 0 | Original commitment amount |
| notes | TextField | blank, null | Optional notes |
| created_at | DateTimeField | auto_now_add | Record creation timestamp |
| updated_at | DateTimeField | auto_now | Last modification timestamp |

**Constraints**:
- `unique_together: (entity, asset)` — one commitment per entity-asset pair
- `ordering: ['entity', 'asset']`

**Computed properties** (not stored):
- `paid_in`: SUM of related CapitalCall amounts
- `pct_called`: paid_in / original_amount × 100
- `unfunded`: original_amount − paid_in

### CapitalCall

Represents a draw-down (capital call) against a commitment.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | AutoField | PK | Auto-generated primary key |
| commitment | FK → Commitment | CASCADE, related_name='capital_calls' | Parent commitment |
| call_date | DateField | required | Date of capital call |
| amount | DecimalField(15,2) | required, > 0 | Amount called |
| notes | TextField | blank, null | Optional notes |
| created_at | DateTimeField | auto_now_add | Record creation timestamp |

**Constraints**:
- `ordering: ['call_date']`
- No DB-level constraint preventing overcall (sum > original_amount)
- Overcall allowed — serializer returns warning but saves

## Existing Models (unchanged)

### Entity (api.models.Entity)
- No structural changes
- Enhanced with rollup calculations via Commitment relationship
- Types: individual, company, LLC, trust, partnership, other

### Asset (api.models.Asset)
- No structural changes
- Types: real_estate, public_equity, private_equity, fixed_income, cash, hedge_fund, crypto, collectible, other
- Linked to commitments via `asset.commitments` reverse relation

### Distribution + DistributionAllocation
- No changes — continues to provide distribution data
- `DistributionAllocation.amount` is the source for DPI calculations (per entity)
- Preserves historical splits, handles non-proportional PE waterfall distributions

### FMVSnapshot
- No changes — provides Residual Value for manual assets
- Latest snapshot per asset used as current valuation

### PlaidAccount (plaid_integration.models)
- No changes — `current_balance` feeds into Residual Value for Plaid-linked assets
- Mapped accounts (`PlaidAccount.asset_id`) participate in entity residual
- Unmapped accounts appear in Asset Class Summary only

### EntityAssetOwnership
- No changes — provides ownership percentage for pro-rating residual values
- Used for entity filtering across all views

## Entity Relationship Diagram

```
Entity ──┬── Commitment ──── CapitalCall (1:N)
         │      │
         │      └── Asset
         │
         ├── EntityAssetOwnership ── Asset
         │
         ├── DistributionAllocation ── Distribution ── Asset
         │
         └── (Reports: Portfolio Summary rolls up all of the above)

Asset ──┬── FMVSnapshot (latest = Residual for manual)
        ├── PlaidAccount (balance = Residual for Plaid-linked)
        ├── Commitment (1:N from entities)
        └── Distribution (1:N)
```

## Computed Metrics (not stored — all calculated on-the-fly)

### Per-Entity (Portfolio Summary row)

| Metric | Formula | Source |
|--------|---------|--------|
| Original Commitment | SUM(Commitment.original_amount) | Commitment where entity matches |
| Paid-In (ABS) | SUM(CapitalCall.amount) across all entity's commitments | CapitalCall via Commitment FK |
| % Called | Paid-In / Original Commitment × 100 | Computed |
| Unfunded Commitment | Original Commitment − Paid-In | Computed |
| Distributions | SUM(DistributionAllocation.amount) where entity matches | DistributionAllocation |
| Residual Value | SUM(latest FMV or Plaid balance × ownership %) | FMVSnapshot + PlaidAccount |
| DPI | Distributions / Paid-In | Computed; None if Paid-In = 0 |
| RVPI | Residual / Paid-In | Computed; None if Paid-In = 0 |
| TVPI | (Distributions + Residual) / Paid-In | Computed; None if Paid-In = 0 |
| IRR (XIRR) | XIRR of pooled cash flows | calculate_xirr() with entity's calls/distributions/residual |

### "All Entities" Summary Row

All monetary columns: SUM across all entities.  
All ratio columns (DPI, RVPI, TVPI): recomputed from aggregate sums, NOT averaged.  
IRR: pooled XIRR across ALL entities' cash flows.

### Per-Asset-Class (Asset Class Summary)

| Metric | Formula | Source |
|--------|---------|--------|
| Total Value | SUM of item values in this class | _collect_valued_items() |
| % of Portfolio | Total Value / Grand Total × 100 | Computed |
| Item Count | COUNT of items in this class | Computed |

## Migration

**Migration file**: `0005_commitment_capitalcall.py` (auto-generated by `makemigrations`)

- Creates `Commitment` table with unique_together constraint
- Creates `CapitalCall` table with FK to Commitment
- No changes to existing tables
- Reversible (drop tables on reverse)
- No data migration needed — new tables start empty
