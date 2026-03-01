# Research: Portfolio Valuation & Tracking

**Date**: 2026-02-28  
**Status**: Resolved  
**Spec**: [spec.md](spec.md) — FR-001 through FR-018  
**Context**: Python 3.12 / Django 4.2, up to 1,000 FMV snapshots per asset, ~50-200 assets, 2 principals. Constitution mandates: no floating-point for money (Decimal), simplicity/YAGNI, no premature abstraction.

---

## Resolved Unknowns

### Unknown 1: Plaid Environment Configuration

**Decision**: Use environment variables (`PLAID_CLIENT_ID`, `PLAID_SECRET`, `PLAID_ENV`) referenced in Django `settings.py`. Toggle between Sandbox and Production via `PLAID_ENV`.

**Rationale**: 
- Plaid has only 2 environments: **Sandbox** (`sandbox.plaid.com`) and **Production** (`production.plaid.com`). Development environment was decommissioned June 2024.
- API credentials are a `client_id` + `secret` pair.
- The `plaid-python` SDK (v38.x) accepts them via `plaid.Configuration(host=plaid.Environment.Sandbox, api_key={'clientId': ..., 'secret': ...})`.
- For Docker Compose: define in `.env`. For Railway: set as env vars.

**Alternatives Considered**:
- Secrets in `settings.py` directly — insecure in version control
- Django encrypted fields — overkill for server-side secrets
- Vault/AWS SSM — unnecessary for small family office app

---

### Unknown 2: Plaid Webhooks vs Manual Sync

**Decision**: Start with **manual sync** (on-demand button + optional daily scheduled sync). Webhooks deferred.

**Rationale**: 
- For 1-10 linked accounts, daily sync via `/investments/holdings/get` is simple, reliable, debuggable
- Webhooks require: public HTTPS endpoint, webhook verification, idempotent processing, retry handling (Plaid retries up to 24h with exponential backoff)
- A "Sync Now" button per linked account provides immediate user feedback
- Scheduled sync (daily via management command) handles background updates

**Alternatives Considered**:
- Webhooks-first — premature for ≤10 accounts
- Real-time polling — wasteful and rate-limited

---

### Unknown 3: Asset-to-Plaid-Account Mapping

**Decision**: After Plaid Link completes, show a **mapping screen** where user maps each Plaid account to an existing asset or creates a new one (pre-filled from Plaid metadata).

**Rationale**:
- Plaid Link's `onSuccess` returns `metadata.accounts` array with `id`, `name`, `mask`, `type`, `subtype` per account
- Multiple accounts per institution (checking + IRA + 401k) → one-to-one Item-to-Asset is too coarse
- Auto-creation by name is fragile (names vary across institutions)
- UX flow: (1) Link institution → (2) Show accounts with name/mask/type/balance → (3) Map each to existing Asset or "Create New" (pre-filled) → (4) Subsequent syncs update mapped assets

**Alternatives Considered**:
- Fully automatic mapping by name — fragile
- One Item = one Asset — too coarse for multi-account institutions

---

### Unknown 4: TWR/IRR Calculation Approach

**Decision**: Implement TWR and XIRR in **pure Python** (~50 lines each). No numpy-financial dependency.

### Rationale

**numpy-financial does not solve the actual problem.** The package's `irr()` function computes IRR for **regular-period** (equally-spaced) cash flows only — it finds the roots of a polynomial. Our data has **irregular dates** (FMV snapshots and distributions land on arbitrary dates), which requires XIRR — a fundamentally different calculation that numpy-financial does not provide. We would need to build the XIRR solver ourselves regardless.

Additionally:
- **Dependency weight**: numpy-financial v2.0.0 requires `numpy>=1.23.5` and uses Cython/Meson for compiled extensions. numpy alone is ~30-60MB installed. This violates the constitution's simplicity principle for a feature that uses exactly two functions.
- **XIRR is ~30 lines of Python**: Newton's method on a well-defined NPV equation with its analytical derivative. The math is straightforward, well-documented, and deterministic. There is no numerical edge case that numpy handles but pure Python `Decimal`/`float` cannot.
- **TWR is pure arithmetic**: Multiply sub-period growth factors. No numerical solver needed at all. ~20 lines of Python.
- **Performance at scale**: For ≤1,000 data points, Python's `math` module with `float` arithmetic completes the Newton iteration in microseconds. The performance constraint (SC-003: < 2 seconds) is trivially met. The bottleneck will be the database query, not the math.
- **Decimal compatibility**: Our constitution mandates `Decimal` for money. numpy operates on `float64`. A pure Python implementation can accept `Decimal` inputs, convert to `float` only for the iterative solver, and return results as `float` (return percentages are inherently approximate — Decimal precision is not meaningful for IRR/TWR results).

### Alternatives Considered

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **numpy-financial** | Well-tested, maintained by NumPy team | Does NOT support XIRR (irregular dates). Requires numpy (~30-60MB). Compiled C/Cython extensions complicate Docker builds. Last PyPI release was 2019 (v1.0.0); v2.0.0 is unreleased. | ❌ Rejected — doesn't solve our problem |
| **scipy.optimize** | Production-grade Newton/Brent solvers. Handles convergence edge cases. | Requires scipy (~150MB installed). Extreme overkill for one root-finding call. Our problem has an analytical derivative, so we don't need scipy's generic optimizer machinery. | ❌ Rejected — massive dependency for trivial use |
| **pyxirr** (Rust-based) | Blazing fast, purpose-built for XIRR/XNPV | Third-party crate with compiled Rust extensions. Less mainstream, platform-specific wheels. Adds build complexity for Docker. | ❌ Rejected — unnecessary complexity for our scale |
| **Pure Python (Newton's method)** | Zero dependencies. ~50 total lines. Full control over edge cases. Easy to test. Matches constitution's simplicity principle. Uses Python `math` module only. | Must handle edge cases ourselves (no convergence, multiple roots). | ✅ Selected |

### Key Implementation Notes (for Phase 2)

- Use `float` for the iterative solver (IRR percentages don't benefit from Decimal precision)
- Accept `Decimal` inputs and convert with `float()` at the boundary
- Newton's method converges in 10-50 iterations for typical financial data
- Set a maximum iteration limit (100) and tolerance (1e-10) for safety

---

## Question 2: TWR Calculation Formula

### Decision: **True Time-Weighted Return with sub-period geometric linking**

### The Formula

TWR uses the "true time-weighted return" method per GIPS (Global Investment Performance Standards). The overall period is divided into sub-periods at each point where an external cash flow occurs, and the portfolio must be valued at each such point.

**Step 1 — Define sub-periods.** A sub-period boundary occurs at each date where there is either:
- A cash flow (distribution received, capital call/contribution)
- An FMV snapshot

**Step 2 — Calculate each sub-period return.** For sub-period *i*, the growth factor is:

$$1 + R_i = \frac{V_{\text{end},i}}{V_{\text{start},i} + C_i}$$

Where:
- $V_{\text{end},i}$ = FMV at end of sub-period
- $V_{\text{start},i}$ = FMV at start of sub-period (= end value of previous sub-period)
- $C_i$ = net external cash flow at the **start** of the sub-period (contributions are positive inflows to the asset, distributions/withdrawals are negative — they flow out of the asset to the investor)

**Cash flow sign convention for TWR** (from the asset's perspective):
- Capital contribution / investment → **positive** (money flows into the asset)
- Distribution received by investor → **negative** (money flows out of the asset)

**Step 3 — Geometric linking.** Chain-multiply all sub-period growth factors:

$$TWR = \prod_{i=1}^{n}(1 + R_i) - 1$$

**Step 4 — Annualize (if period > 1 year):**

$$TWR_{\text{annual}} = (1 + TWR)^{365.25 / D} - 1$$

Where $D$ is the total number of days in the measurement period.

### How to Handle Sub-Periods in Our Data Model

Given:
- **FMVSnapshot**: `(asset, date, value)` — point-in-time valuations
- **Distribution**: `(asset, date, amount)` — cash flowing OUT of the asset to investors

Build a merged, date-sorted timeline:

1. Collect all FMV snapshots for the asset in the period
2. Collect all distributions for the asset in the period
3. Merge and sort by date
4. For each consecutive pair of FMV snapshots, sum any distributions that occurred between them
5. Calculate the sub-period growth factor

**Critical requirement**: We need an FMV snapshot at (or near) each cash flow date. If a distribution occurs on a date without an FMV snapshot, we must either:
- (a) Use the most recent prior FMV snapshot (carry-forward) — **our approach**
- (b) Interpolate between adjacent snapshots
- (c) Require the user to enter an FMV snapshot

Carry-forward is the standard approach for illiquid assets (real estate, private equity) where daily pricing is unavailable. This matches our user base (CPA managing illiquid holdings).

### Edge Cases

| Case | Handling |
|------|----------|
| Only 1 FMV snapshot | Return "Insufficient data" (FR-012) |
| 2+ FMV snapshots, no distributions | TWR = simple return: `(FMV_end / FMV_start) - 1` |
| Distribution on same date as FMV snapshot | Apply distribution **before** the snapshot valuation |
| FMV goes to zero mid-period | Sub-period return = -100%. Chain breaks. Report "Terminal loss" |
| Negative FMV (shouldn't happen) | Reject / flag as data error |
| Sub-period start value = 0 | Skip sub-period, log warning |

### Alternatives Considered

| Method | Pros | Cons | Verdict |
|--------|------|------|---------|
| **True TWR (geometric linking)** | GIPS-compliant, industry standard. Eliminates effect of cash flow timing. Best for measuring investment performance independent of investor behavior. | Requires FMV at each cash flow date. | ✅ Selected |
| **Modified Dietz** (single-period approximation) | Doesn't require interim valuations. Simpler computation. | Less accurate when cash flows are large relative to portfolio value. Not a true TWR. Approximates IRR, not TWR. | ❌ Rejected — we have FMV snapshots available |
| **Daily TWR** (daily pricing) | Most granular. Used by liquid fund managers. | We don't have daily FMV for illiquid assets. Over-engineering for our use case. | ❌ Rejected — data not available |

---

## Question 3: IRR / XIRR Calculation

### Decision: **XIRR via Newton's method with analytical derivative, pure Python**

### The Formula

XIRR finds the annual rate $r$ such that the Net Present Value of all cash flows equals zero:

$$NPV(r) = \sum_{i=0}^{N} \frac{C_i}{(1 + r)^{t_i}} = 0$$

Where:
- $C_i$ = cash flow at time $i$ (negative for money out, positive for money in)
- $t_i$ = `(date_i - date_0).days / 365.25` — time in fractional years from the first cash flow
- $r$ = the annual rate we're solving for

**Cash flow construction for our model** (from the **investor's** perspective — opposite of TWR):
- Initial investment → **negative** (investor pays money out)
- Distributions received → **positive** (investor receives money)
- Current FMV × ownership % as terminal value → **positive** (what the investor could get today)

### Newton's Method

Newton's method iteratively refines a guess for $r$:

$$r_{k+1} = r_k - \frac{NPV(r_k)}{NPV'(r_k)}$$

The derivative of NPV with respect to $r$ is:

$$NPV'(r) = -\sum_{i=0}^{N} \frac{C_i \cdot t_i}{(1 + r)^{t_i + 1}}$$

**Initial guess**: $r_0 = 0.10$ (10%) is standard. An alternative smarter starting point:

$$r_0 = \frac{\sum \text{inflows}}{|\sum \text{outflows}|} - 1$$

**Convergence criteria**:
- Tolerance: $|NPV(r_k)| < 1 \times 10^{-10}$
- Max iterations: 100
- If $1 + r_k \leq 0$, clamp to a small positive value to avoid domain errors

### Edge Cases

| Case | Detection | Handling |
|------|-----------|----------|
| **No solution** (all positive or all negative cash flows) | All $C_i$ have same sign | Return `None` with reason "All cash flows are same sign — IRR undefined" |
| **Multiple solutions** | Cash flow sign changes > 1 (Descartes' rule) | Per Descartes' rule of signs, the number of positive real roots ≤ number of sign changes. For our typical case (one negative initial investment, then positive distributions + terminal FMV), there is exactly **one sign change → one unique solution**. If multiple sign changes detected, log a warning and return the first convergent result. |
| **Does not converge** | Iteration count exceeds 100 | Return `None` with reason "IRR did not converge" |
| **Very high return** | $r > 10$ (1000%) | Cap at 1000% and flag. Likely data error. |
| **Very negative return** | $r < -0.99$ (-99%) | Cap at -99%. Total loss. |
| **Only 1 cash flow** | `len(cash_flows) < 2` | Return `None` — need at least an outflow and an inflow/terminal value |
| **Zero initial investment** | $C_0 = 0$ | Return `None` — IRR is undefined without an initial outflow |
| **All cash flows on same date** | All $t_i = 0$ | Return `None` — need time passage for a rate of return |

### Why Newton's Method Over Alternatives

| Method | Pros | Cons | Verdict |
|--------|------|------|---------|
| **Newton's method** | Quadratic convergence. Uses analytical derivative (no approximation). Typical convergence in 10-20 iterations. Standard in financial software. | Requires derivative (trivially available for NPV). Can diverge with bad initial guess. | ✅ Selected |
| **Secant method** | Doesn't need derivative. | Slower (superlinear, not quadratic). Needs two initial guesses. | ❌ Rejected — we have the derivative, so Newton is strictly better |
| **Brent's method** | Guaranteed convergence in a bracket. | Requires knowing a bracket [a, b] where NPV changes sign. Slower. Over-engineering. | ❌ Rejected — Newton with clamping is sufficient |
| **Bisection** | Simplest, guaranteed convergence. | Very slow (linear convergence). Would need ~50 iterations for 1e-10 tolerance. | ❌ Rejected — unnecessarily slow |

### Fallback Strategy

If Newton's method fails to converge (rare for well-formed financial data), fall back to **Brent's method** on the bracket $[-0.99, 10.0]$ using a simple bisection loop. This provides guaranteed convergence as a safety net, at the cost of ~50 additional iterations. This is the same strategy used by Excel's XIRR function.

---

## Question 4: Period Calculations (YTD, 1Y, 3Y, Since Inception)

### Decision: **Standard calendar-based boundaries with available-data lookback**

### Date Boundaries

All periods are computed **relative to the calculation date** (typically today). For the "current date" = `calc_date`:

| Period | Start Date | End Date | Notes |
|--------|-----------|----------|-------|
| **YTD** | Jan 1 of `calc_date.year` | `calc_date` | Year-to-date from calendar year start |
| **1Y** | `calc_date - 365 days` | `calc_date` | Trailing 12 months (not calendar year) |
| **3Y** | `calc_date - 1095 days` | `calc_date` | Trailing 36 months (use `3 * 365` = 1095) |
| **Since Inception** | Date of first FMV snapshot or first cash flow (whichever is earlier) | `calc_date` | Full history |

### FMV at Period Boundaries

A critical detail: we need an FMV value **at the start and end** of each period. But FMV snapshots are entered on arbitrary dates. Resolution:

1. **End-of-period FMV**: Use the **most recent** FMV snapshot on or before `calc_date`. If none exists within 90 days, mark as "Stale data."
2. **Start-of-period FMV**: Use the **closest** FMV snapshot to the period start date. Specifically:
   - Look for an FMV snapshot on exactly the start date
   - If none, use the most recent FMV snapshot **on or before** the start date (carry-forward)
   - If no prior snapshot exists, use the **earliest** FMV snapshot **after** the start date, and adjust the period start to that date
3. **Since Inception**: The start FMV is simply the first FMV snapshot ever recorded for the asset.

### Annualization Rules

| Period | Annualize? | Formula |
|--------|-----------|---------|
| **YTD** | **No** if < 1 year into the year. **Yes** if reporting annualized equivalent. | If annualizing: $(1 + R)^{365.25/D} - 1$ |
| **1Y** | No (already ~1 year) | Report as-is |
| **3Y** | **Yes** — report as annualized rate | $(1 + R_{3Y})^{1/3} - 1$ |
| **Since Inception** | **Yes** if > 1 year. **No** if < 1 year. | $(1 + R)^{365.25/D} - 1$ |

**Convention**: For periods less than 1 year, report the **cumulative** (non-annualized) return. Annualizing a 2-month return of 5% into ~34% annual is misleading. Display as "5.0% (2 months)" instead.

### Insufficient Data Rules

| Condition | Result |
|-----------|--------|
| Fewer than 2 FMV snapshots in the period | "Insufficient data" (FR-012) |
| Period requested extends before first FMV snapshot (e.g., 3Y requested but only 1Y of data) | Shorten to available period. Display "1.2Y" instead of "3Y". Or show "N/A — only X months of data." |
| No distributions and < 2 FMV snapshots for IRR | IRR = "Insufficient data" |
| TWR calculable but IRR is not (or vice versa) | Show whichever is available. Don't suppress both. |

### Alternatives Considered

| Approach | Verdict |
|----------|---------|
| Calendar-year periods (Jan 1 – Dec 31) | ❌ Rejected — trailing periods are more useful for performance monitoring |
| Fiscal-year alignment | ❌ Rejected — YAGNI, add later if CPA requests it |
| Strict "must have FMV on exact boundary date" | ❌ Rejected — too rigid for illiquid assets with quarterly valuations |
| Carry-forward FMV with staleness cutoff | ✅ Selected — pragmatic for illiquid assets |

---

## Question 5: Aggregation (Asset → Entity Portfolio)

### Decision: **TWR = value-weighted aggregation from sub-returns. IRR = recalculate from aggregated cash flows.**

### TWR Aggregation

TWR aggregation at the entity/portfolio level uses **value-weighted individual asset TWRs**:

$$TWR_{\text{portfolio}} = \sum_{j=1}^{M} w_j \times TWR_j$$

Where:
- $w_j$ = weight of asset $j$ = `(FMV_j × ownership_pct_j) / Σ(FMV_k × ownership_pct_k)`
- $TWR_j$ = time-weighted return of asset $j$ over the period
- Weights are calculated using **beginning-of-period** FMV values

**Why beginning-of-period weights**: Using end-of-period weights would introduce circularity (the return affects the weight which affects the return). Beginning-of-period weights are the GIPS-standard approach.

**Ownership percentage handling**: Entity X owns 60% of Asset A (per `EntityAssetOwnership`). The entity's share of Asset A's FMV is `FMV_A × 0.60`. The TWR of Asset A itself is the same regardless of ownership percentage — ownership only affects the **weight** in the portfolio, not the return.

### IRR Aggregation

**IRR cannot be meaningfully weight-averaged.** Instead, recalculate from aggregated cash flows:

1. Collect all cash flows across all assets owned by the entity
2. Scale each cash flow by the entity's ownership percentage at the time of the cash flow
3. For each asset, create a scaled initial investment (negative) at the first FMV date: `-(FMV_first × ownership_pct)`
4. For each distribution, create a scaled positive flow: `distribution_amount × entity_allocation_pct`
5. For each asset, create a scaled terminal value (positive) at calc_date: `FMV_current × ownership_pct`
6. Feed all scaled, dated cash flows into the XIRR solver as a single combined stream

This is the correct approach because IRR is inherently a money-weighted measure — it must account for the actual timing and magnitude of all capital deployed.

### Why Not Weight-Average IRR?

Weight-averaging individual IRRs is mathematically **incorrect** and produces misleading results. Consider:
- Asset A: IRR = 20%, invested $100
- Asset B: IRR = 5%, invested $900
- Naive weighted average: `(100/1000 × 20%) + (900/1000 × 5%) = 6.5%`
- But the actual portfolio IRR depends on the timing of cash flows, not just magnitudes. The correct approach is to solve XIRR on the combined cash flow stream.

The weighted average can diverge significantly from the true portfolio IRR when:
- Cash flow timing differs between assets
- Asset sizes are very different
- Return magnitudes vary widely

### Summary Table

| Metric | Aggregation Method | Weights |
|--------|-------------------|---------|
| **TWR** | Weighted average of individual asset TWRs | Beginning-of-period FMV × ownership % |
| **IRR** | Recalculate XIRR from combined, ownership-scaled cash flow stream | N/A — single combined calculation |
| **Current FMV** | Sum of `(asset_FMV × ownership_pct)` across all assets | Direct sum |

### Edge Cases

| Case | Handling |
|------|----------|
| Entity ownership changes mid-period | Use the ownership percentage in effect **at the time of each cash flow**. Query `EntityAssetOwnership` with `effective_date <= cash_flow_date` to get the applicable percentage. |
| Entity owns 0% of an asset (sold out) | Exclude from current portfolio view but include historical cash flows for Since Inception IRR |
| Entity has no assets with sufficient data | Show "No performance data available" |
| Ownership percentages don't sum to 100% across entities | Not relevant — each entity's portfolio is calculated independently. Warn in UI if an asset's total ownership > 100%. |

### Alternatives Considered

| Approach | Verdict |
|----------|---------|
| Weight-average IRR | ❌ Rejected — mathematically incorrect |
| Recalculate TWR from aggregated cash flows | ❌ Rejected — harder to implement and the weighted-average approach is GIPS-compliant for TWR |
| Use Modified Dietz for portfolio-level | ❌ Rejected — we have the data for true TWR |
| Value-weighted TWR + recalculated IRR | ✅ Selected — each metric uses its correct aggregation method |

---

## Summary of Decisions

| # | Question | Decision | Key Rationale |
|---|----------|----------|---------------|
| 1 | numpy-financial vs pure Python | **Pure Python (Newton's method)** | numpy-financial doesn't support XIRR. ~50 lines of code. Zero new dependencies. Constitution: simplicity. |
| 2 | TWR formula | **True TWR with geometric linking** | GIPS-compliant. Use FMV snapshots as sub-period boundaries. Carry-forward FMV for illiquid assets. |
| 3 | IRR / XIRR approach | **Newton's method on NPV equation** | Analytical derivative available → quadratic convergence. Brent's method as fallback. Handle edge cases explicitly. |
| 4 | Period calculations | **Trailing calendar periods with carry-forward FMV** | YTD/1Y/3Y/SI with staleness detection. Annualize only periods > 1 year. |
| 5 | Aggregation | **TWR: value-weighted average. IRR: recalculate from combined cash flows.** | Each metric uses its mathematically correct aggregation. Ownership-scaled. |

### New Dependencies for Performance: **None**

The `requirements.txt` remains unchanged for TWR/IRR. All calculations use Python stdlib (`math`, `datetime`, `decimal`).

### New Dependencies for Plaid

| Package | Version | Purpose |
|---------|---------|---------|
| `plaid-python` | 38.x | Official Plaid SDK (Python 3, MIT, auto-generated from OpenAPI) |
| `react-plaid-link` | 4.1.x | Official Plaid Link React hook (`usePlaidLink`) |

### Plaid Link Flow (Django + React)

1. Frontend calls `POST /api/plaid/create-link-token/`
2. Backend calls Plaid `/link/token/create` → returns `link_token` (expires 4h)
3. Frontend passes `link_token` to `usePlaidLink` hook → opens Plaid Link modal
4. On success, `onSuccess(public_token, metadata)` fires with accounts array
5. Frontend sends `public_token` + account selection to `POST /api/plaid/exchange-token/`
6. Backend calls `/item/public_token/exchange` → receives `access_token` (non-expiring) + `item_id`
7. Backend stores `access_token` and `item_id`, creates PlaidItem + PlaidAccount records
8. User maps Plaid accounts to Assets (mapping screen)
9. Backend calls `/investments/holdings/get` → stores balances as FMV snapshots

### File Placement

Per the plan:
- TWR/IRR calculation logic → `backend/api/performance.py` (pure utility functions, no Django ORM in math layer)
- Plaid integration → `backend/plaid_integration/` (separate Django app per constitution — justified by external API isolation)
- FMV CRUD + asset classification → `backend/api/` (extends existing app)