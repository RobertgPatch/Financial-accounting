# Research: Portfolio Tracker Redesign

**Feature**: 003-portfolio-tracker-redesign | **Date**: 2026-03-04

## Decision 1: Commitment + CapitalCall Data Model

**Decision**: One Commitment per entity-per-asset (`unique_together`), CapitalCall as FK to Commitment. Allow overcall. All computed fields (% Called, Unfunded, Paid-In) calculated on-the-fly.

**Rationale**:
- Spec explicitly states "One commitment per entity-asset pair." The CSV shows one "Original Commitment" column per entity row.
- CapitalCall → Commitment FK ensures calls are meaningless without a commitment. Computing `paid_in = Commitment.capital_calls.aggregate(Sum('amount'))` is a single ORM call.
- Overcall is allowed at the model level (no DB constraint on sum(calls) > original_amount) — PE/VC funds routinely have bridge financing and follow-on calls. The `% Called` can truthfully exceed 100%; `Unfunded` goes negative.
- Computed on-the-fly avoids stale-data bugs and matches existing codebase precedent (FMV report, distribution report, performance metrics all compute live). Dataset is small (~4 entities, ~50 assets, <500 calls).

**Alternatives considered**:
- Multiple commitments per entity-per-asset: Rejected — spec says one. Follow-on commitments are modeled as separate Asset records (Fund I, Fund II).
- Stored computed fields: Rejected — requires invalidation triggers, no precedent in codebase, dataset is small enough for live computation.
- Standalone CapitalCall with entity+asset FKs: Rejected — loses commitment linkage, complicates the query.

## Decision 2: Residual Value Computation

**Decision**: Compute on-the-fly using a unified `compute_entity_residual()` helper. Plaid-mapped assets use `PlaidAccount.current_balance`; manual assets use latest `FMVSnapshot.value`. Pro-rated by `EntityAssetOwnership.percentage`. Unmapped Plaid accounts excluded from entity-level residual.

**Rationale**:
- The existing `generate_fmv_report()` already solves Plaid+manual merging with anti-double-counting logic (`mapped_asset_ids` exclusion). Residual computation follows the same pattern.
- Entity-scoped: get entity's Commitment assets, look up latest value for each (Plaid balance or FMV snapshot), multiply by ownership percentage.
- No caching — Plaid balances change on sync, FMV snapshots are added periodically. At ~50 assets, query cost is negligible.

**Alternatives considered**:
- Cached/stored residual: Rejected — requires invalidation on both PlaidAccount sync and FMVSnapshot creation.
- Always use FMVSnapshot (no Plaid): Rejected — Plaid accounts would need manual FMV snapshot entry, defeating the purpose of Plaid auto-sync.

## Decision 3: Entity-Level Aggregation (DPI/RVPI/TVPI)

**Decision**: Aggregate from raw monetary sums across all entity's assets, then compute ratios. "All Entities" row recomputes from aggregate sums (not averaged per-entity ratios). Return `None` when `paid_in == 0`.

**Rationale**:
- Averaging entity-level ratios is mathematically wrong — a $10M entity and a $100K entity would be weighted equally. Sum-then-divide is the standard PE/VC methodology.
- Matches SC-003: "DPI/RVPI/TVPI recomputed from aggregated totals."
- `None` for zero-paid-in is clean for frontend rendering as "—" (dash), matching FR-015.

**Formulas**:
- `paid_in = SUM(CapitalCall.amount)` across all entity's commitments
- `distributions = SUM(DistributionAllocation.amount)` where entity matches
- `residual = compute_entity_residual(entity_id)`
- DPI = distributions / paid_in
- RVPI = residual / paid_in
- TVPI = (distributions + residual) / paid_in

## Decision 4: Entity-Level XIRR

**Decision**: Pool all dated cash flows across all assets for one entity into a single list, then call the existing `calculate_xirr()` directly. Capital calls are negative, distributions are positive, terminal residual is positive.

**Rationale**:
- IRR is non-additive — you cannot weight-average per-asset IRRs to get a correct portfolio IRR. Pooling is the standard PE/VC methodology (ILPA guidelines).
- The existing `calculate_xirr()` takes `List[Tuple[date, float]]` — exactly the format produced by pooling entity cash flows. Newton's method + Brent's fallback handles convergence. No changes needed to the function itself.
- "All Entities" IRR: pool ALL entities' cash flows into one list and call `calculate_xirr()` once.

**Alternatives considered**:
- Per-asset IRR weighted by capital deployed: Rejected — IRR does not aggregate this way and would produce incorrect results.
- Per-entity IRR averaged: Same problem — dollar-weighted pooled XIRR is the only correct approach.

## Decision 5: Distribution Source for DPI

**Decision**: Use `SUM(DistributionAllocation.amount)` where entity matches — not `Distribution.total_amount × ownership %`.

**Rationale**:
- `DistributionAllocation` records capture the actual entity-level split at distribution time, preserving historical accuracy when ownership changes. Using current `ownership %` would silently break for distributions where the split didn't match.
- PE waterfall structures commonly have non-proportional splits (preferred returns, catch-up provisions), which are reflected in explicit allocation amounts but not in ownership percentages.
- Matches existing codebase precedent: `get_entity_performance()`, the distribution report, and retained earnings calculations all aggregate via `DistributionAllocation`.

**Alternatives considered**:
- `Distribution.total_amount × EntityAssetOwnership.percentage / 100`: Rejected — assumes current ownership % applied historically, breaks with time-varying ownership and non-proportional PE splits.

## Decision 6: Asset Class Summary vs Existing FMV Report

**Decision**: Extract a shared `_collect_valued_items(entity_ids=None, type_filters=None)` helper from `generate_fmv_report()`, then have both `generate_fmv_report()` and `generate_asset_class_summary()` call it. Asset Class Summary adds commitment data overlay.

**Rationale**:
- `generate_fmv_report()` already handles the hard part: Plaid balance querying, manual asset FMV snapshot lookup, double-count prevention (`mapped_asset_ids` exclusion), entity filtering via `EntityAssetOwnership`, and grouping by asset type.
- Asset Class Summary needs the identical core logic plus commitment context (shows unfunded commitment contributing to understanding allocation).
- Sharing at the data-collection layer avoids duplicating the nuanced Plaid+manual+dedup+entity-filter logic.

**Alternatives considered**:
- Call `generate_fmv_report()` and post-process output: Rejected — returns string-serialized values and a response shape that would need unpacking.
- Completely separate implementation: Rejected — would duplicate ~60 lines of dedup/entity-filter logic that's error-prone to maintain in two places.
