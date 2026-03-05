# Research: FMV Auto-Reporting Design Decisions

**Branch**: `002-fmv-auto-reporting` | **Date**: 2026-02-28  
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

---

## Decision 1: API Endpoint Design

### Decision: Separate endpoint — `POST /api/reports/fmv/generate/` and `POST /api/reports/fmv/export/`

### Rationale

The FMV report and Distribution report have **completely disjoint parameter sets**:

| Parameter | Distribution | FMV |
|-----------|-------------|-----|
| `period_type` | ✅ yearly/quarterly/monthly | ❌ not applicable |
| `year` / `quarter` / `month` | ✅ | ❌ |
| `entity_ids` | ✅ filters allocations | ✅ filters manual assets only |
| `asset_ids` | ✅ | ❌ not applicable |
| `type_filters` | ❌ | ✅ list of asset_type values |

The existing `generate_report` view in `views.py` (line 271) calls `_parse_report_params()` which extracts `period_type`, `year`, `quarter`, `month`, `entity_ids`, `asset_ids` — none of which apply to FMV reports except `entity_ids`. Forcing both through a single endpoint with a `report_type` discriminator would mean:

1. `_parse_report_params()` becomes a conditional mess — must parse different fields depending on `report_type`.
2. The two report functions (`generate_distribution_report` and `generate_fmv_report`) would share no code path.
3. Error handling diverges — Distribution requires `year`, FMV requires neither `year` nor `period_type`.
4. The existing `export_report` view builds filenames from `period` data that FMV doesn't have.

Separate endpoints keep the existing Distribution code **100% untouched** (zero regression risk) and give the FMV endpoint its own clean parameter parsing. The URL pattern is consistent with the existing structure:

```
POST /api/reports/generate/          # Distribution (existing, unchanged)
POST /api/reports/export/            # Distribution export (existing, unchanged)
POST /api/reports/fmv/generate/      # FMV (new)
POST /api/reports/fmv/export/        # FMV export (new)
```

Frontend API client adds `generateFmvReport()` and `exportFmvReport()` alongside existing functions — no changes to `generateReport()` or `exportReport()`.

### Alternatives Considered

- **Single endpoint with `report_type` parameter**: Rejected. Adds conditional complexity to `_parse_report_params()`, pollutes the existing Distribution logic, and violates the Single Responsibility Principle. The two reports share zero query logic — a shared endpoint gives false cohesion.
- **Extending `generate_report` view with if/else**: Rejected. The existing view is 8 lines and clean. Adding a branch doubles its size and creates coupling between two independent features.

---

## Decision 2: Plaid Subtype Utilization

### Decision: Map at `type` level only (4 types → asset categories). Store `subtype` in the response for display purposes, but do NOT use it for categorization.

### Mapping:

```python
PLAID_TYPE_MAP = {
    'depository': 'cash',           # checking, savings, money market, cd, etc.
    'investment': 'public_equity',  # 401k, brokerage, ira, etc.
    'loan':       'fixed_income',   # mortgage, student, auto, etc.
    'credit':     'cash',           # credit card debt → reduces cash position
}
```

Fallback: any unmapped type → `'other'`.

### Rationale

1. **Spec explicitly uses type-level mapping** (FR-006): "depository → Cash & Equivalents, investment → Public Equity, loan → Fixed Income, credit → Cash & Equivalents". Diverging from the spec adds scope.

2. **Subtype-level mapping is unreliable for accuracy**:
   - `investment` subtype `401k` might hold bonds, REITs, international stocks — calling it all `public_equity` is already an approximation at the type level. Going to subtype doesn't actually improve accuracy since Plaid doesn't expose the *holdings* composition.
   - `depository` subtypes (checking, savings, money market, cd) are all reasonably classified as `cash` — subtype granularity adds no value here.
   - `loan` subtypes (mortgage, student, auto) could arguably map differently (mortgage → real_estate?) but a mortgage liability is not a real estate *asset* — `fixed_income` (as a liability/debt instrument) is the most defensible classification.

3. **YAGNI principle** (Constitution V): Subtype mapping introduces a larger lookup table that must be maintained as Plaid adds subtypes. The feature spec doesn't ask for it. If users need finer categorization, they can map the Plaid account to an Asset with the correct `asset_type`.

4. **Include subtype in the response** for informational display: the FMV report line items for Plaid accounts should show `subtype` (e.g., "checking", "brokerage") so users can identify what each account is. This doesn't affect categorization — it's label-only.

### Alternatives Considered

- **Full subtype mapping (e.g., `401k` → `private_equity`, `mortgage` → `real_estate`)**: Rejected. Semantically incorrect — a 401k is not necessarily private equity, and a mortgage is a liability, not a real estate asset. Would confuse FMV totals.
- **Let user configure mapping per account**: Rejected. Violates the core design goal ("I don't want to have to create an asset for all of the accounts") and adds UI complexity the spec doesn't call for. Users who need custom classification can use the existing asset-mapping FK.
- **Subtype override table in settings**: Rejected. YAGNI — adds a config surface with no user request. Maintainability cost is not justified.

---

## Decision 3: Entity Filter Behavior for Plaid Accounts

### Decision: Option (a) — Exclude unmapped Plaid accounts when an entity filter is active.

### Rationale

1. **The spec says** (FR-010): "when applicable (for manual assets that have entity ownership records)". This defines entity filtering as scoped to manual assets. Plaid accounts without asset mapping have **no entity relationship** — they cannot logically belong to any entity.

2. **User intent for entity filtering** is "show me what Entity X owns." Including unrelated Plaid accounts in that view would be misleading — the user would see accounts that have no proven relationship to the selected entity, inflating that entity's apparent FMV.

3. **When no entity filter is applied** (the default), all Plaid accounts are included (mapped and unmapped). This gives the user the complete net worth picture. Entity filtering is an intentional narrowing.

4. **Mapped Plaid accounts** (those with `asset` FK set where the asset has ownership records to the selected entity) ARE included under the entity filter — they pass through because the linked asset has an ownership record.

5. **Behavioral summary**:

   | Scenario | Entity Filter OFF | Entity Filter ON (Entity X) |
   |----------|------------------|-----------------------------|
   | Unmapped Plaid account | ✅ Included | ❌ Excluded |
   | Plaid account mapped to asset owned by Entity X | ✅ Included | ✅ Included (via asset ownership) |
   | Plaid account mapped to asset NOT owned by Entity X | ✅ Included | ❌ Excluded |
   | Manual asset owned by Entity X | ✅ Included | ✅ Included |
   | Manual asset NOT owned by Entity X | ✅ Included | ❌ Excluded |

### Alternatives Considered

- **Option (b): Show in separate "unassigned" group**: Rejected. Adds UI complexity (a new section), muddies the entity-filtered view with non-entity data, and no spec requirement asks for it. If the user wanted to see all accounts, they would not apply an entity filter.
- **Option (c): Always include unmapped Plaid accounts**: Rejected. Defeats the purpose of entity filtering. If a user filters to "Trust A", seeing random Chase checking accounts that aren't in Trust A is confusing and incorrect.

---

## Decision 4: Frontend Component Architecture

### Decision: Option (a) — Extract FMV report view into a new `FmvReport.jsx` component file. Keep the report type selector and Distribution report in `Reports.jsx`.

### Rationale

1. **Reports.jsx is already 628 lines.** Adding FMV report rendering (summary cards, type breakdown table, pie chart, line items table, filter controls) would push it well past 900+ lines. This is a maintainability problem regardless of YAGNI — the file is already at the practical limit.

2. **The two report types share almost no rendering logic.** Distribution shows: entity summary table, asset summary table, timeline bar chart, entity pie chart, budget comparison, YoY comparison, retained earnings, detail rows. FMV shows: type breakdown table, type pie chart, line items with source labels, totals. The only shared elements are the page shell, the `Card` component, and `formatCurrency`.

3. **Clean separation of concerns**: `Reports.jsx` becomes the orchestrator — it holds the report type selector state and conditionally renders either `<DistributionReport />` (existing JSX extracted) or `<FmvReport />` (new). Each file owns its own state, data, and rendering.

4. **YAGNI compliance**: This isn't speculative abstraction — it's practical file splitting driven by the spec's explicit requirement (FR-001) for two distinct report types. A single 1000+ line file with two interleaved report UIs is harder to maintain than two focused files.

5. **Approach**:
   - `Reports.jsx` — Report type selector at top, renders `<FmvReport>` or existing Distribution JSX
   - `src/pages/FmvReport.jsx` — New file, ~200-300 lines, contains FMV-specific filter panel, generate/export, results rendering
   - Existing Distribution code stays in `Reports.jsx` (no extraction needed — avoids touching working code)

### Alternatives Considered

- **Option (b): Section within Reports.jsx**: Rejected. The FMV report needs its own filter panel (type filters vs period/year), its own state (fmvReport, typeFilters), its own generate/export handlers. Interleaving with Distribution state creates confusion. The file would exceed 900 lines.
- **Option (c): Conditional rendering in Reports.jsx only**: Rejected for the same reasons as (b). Conditional rendering is fine for the *selector*, but the report body should live in its own file. A `{reportType === 'fmv' ? <FmvReport /> : <DistributionContent />}` in Reports.jsx is the right split point.
- **Full extraction of both reports**: Rejected. Extracting the Distribution report into its own file means touching ~500 lines of working, tested JSX for no user-facing benefit. YAGNI applies here — leave Distribution in Reports.jsx.

---

## Decision 5: Chart Visualization

### Decision: Use `PieChart` (already imported in `Reports.jsx` via recharts) for the FMV allocation breakdown by type.

### Data Format

recharts `PieChart` expects an array of objects with a value key and a label key:

```javascript
const typeBreakdown = [
  { name: 'Cash & Equivalents', value: 250000.00 },
  { name: 'Public Equity', value: 180000.00 },
  { name: 'Real Estate', value: 500000.00 },
  // ...
];

<PieChart>
  <Pie data={typeBreakdown} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80}>
    {typeBreakdown.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
  </Pie>
  <Tooltip formatter={v => formatCurrency(v)} />
  <Legend />
</PieChart>
```

### Rationale

1. **PieChart is the canonical choice for allocation/composition data.** The FMV report shows "what percentage of my portfolio is in each asset type" — this is a parts-of-a-whole question, which is exactly what pie charts communicate.

2. **Already imported and used.** `Reports.jsx` line 2 imports `PieChart, Pie, Cell, Legend` from recharts. The existing entity allocation pie chart (line ~290) demonstrates the exact same pattern. Zero new dependencies.

3. **The `COLORS` array** (line 18) already has 8 entries. With 9 asset types, we need one more color. The array uses modulo indexing (`COLORS[i % COLORS.length]`), so even without adding a 9th color it won't break — but adding one more hex value is trivial.

4. **Data format from backend**: The API response `by_type` array maps directly:
   ```python
   # Backend returns:
   'by_type': [
       {'asset_type': 'cash', 'label': 'Cash & Equivalents', 'total_value': '250000.00', 'count': 5, 'percentage': '26.88'},
       ...
   ]
   ```
   Frontend transforms: `byType.map(t => ({ name: t.label, value: parseFloat(t.total_value) }))`.

### Alternatives Considered

- **BarChart (horizontal)**: Reasonable for type comparison but doesn't communicate "parts of whole" as intuitively. Pie chart is better for allocation questions ("what's my split?"). Could be added later as a toggle — YAGNI for now.
- **Treemap**: Overkill for 9 categories. Treemaps shine with hierarchical or high-cardinality data. Nine flat categories are better as a pie.
- **Donut chart** (PieChart with `innerRadius`): This is a stylistic variant of PieChart in recharts (`<Pie innerRadius={40} outerRadius={80} ...>`). Could be used for a more modern look. Low-stakes aesthetic decision — defaulting to standard pie matches the existing entity allocation chart style. Easy to adjust later by adding `innerRadius`.

---

## Decision 6: Double-Counting Prevention Strategy

### Decision: Option (a) — Exclude the mapped asset's FMV snapshot from the manual items list entirely. The Plaid account balance replaces it.

### Rationale

1. **Clearest mental model for the user.** Each line item appears exactly once. A mapped Plaid account shows as a single "Plaid" source row with the Plaid balance. The corresponding manual asset simply doesn't appear — because the Plaid account *is* the authoritative source for that asset's value.

2. **The spec says** (FR-012): "the system MUST use the Plaid balance and NOT double-count by also including the asset's manual FMV snapshot." The most literal reading is: don't include the manual snapshot. Option (a) achieves this by exclusion.

3. **Implementation is simpler:**

   ```python
   # Step 1: Get all Plaid accounts, note which asset IDs are mapped
   plaid_accounts = PlaidAccount.objects.select_related('plaid_item', 'asset').all()
   mapped_asset_ids = set(pa.asset_id for pa in plaid_accounts if pa.asset_id)

   # Step 2: Get manual assets with FMV snapshots, EXCLUDING mapped ones
   manual_assets = Asset.objects.exclude(id__in=mapped_asset_ids).filter(fmv_snapshots__isnull=False).distinct()
   ```

   This is a single `.exclude()` call — clean and auditable.

4. **No ambiguity in the line items table.** With option (b) (include but mark as Plaid), you'd have a line item that references an Asset name but shows a Plaid balance and "Plaid" source — confusing because the user sees their manually-created asset but with a value they didn't enter. With option (a), the Plaid account row uses the Plaid account's own name (e.g., "Chase Checking ****1234") and the manual asset row simply isn't there.

5. **Edge case — mapped Plaid account with `current_balance = NULL` (never synced):** The Plaid account still appears (with $0 and a sync warning per US-1 acceptance scenario 3). The manual FMV snapshot is still excluded — this is correct because the user chose to map them, indicating Plaid is the authoritative source. If they want the manual value back, they unlink the mapping.

### Implementation detail:

```python
# In generate_fmv_report():
items = []

# 1. All Plaid accounts → items (with mapped asset_type override if mapped)
for pa in plaid_accounts:
    asset_type = pa.asset.asset_type if pa.asset else PLAID_TYPE_MAP.get(pa.type, 'other')
    items.append({
        'name': pa.name,
        'value': pa.current_balance or Decimal('0.00'),
        'source': 'plaid',
        'asset_type': asset_type,
        'plaid_account_id': pa.id,
        'institution': pa.plaid_item.institution_name,
        'subtype': pa.subtype,
    })

# 2. Manual assets with FMV snapshots, excluding those mapped to a Plaid account
for asset in manual_assets:  # already filtered with .exclude(id__in=mapped_asset_ids)
    latest_snapshot = asset.fmv_snapshots.order_by('-snapshot_date').first()
    if latest_snapshot:
        items.append({
            'name': asset.name,
            'value': latest_snapshot.value,
            'source': 'manual',
            'asset_type': asset.asset_type,
            'asset_id': asset.id,
            'snapshot_date': str(latest_snapshot.snapshot_date),
        })
```

### Alternatives Considered

- **Option (b): Include mapped asset but override value with Plaid balance and mark as "Plaid" source**: Rejected. Creates a confusing line item — an asset row with a Plaid value. The user sees "My Investment Property" with source "Plaid" and wonders why. Also requires more complex logic: for each manual asset, check if a Plaid account maps to it, and if so, swap the value. Option (a) is simpler — just exclude mapped asset IDs from the manual query.

---

## Summary Table

| # | Decision | Choice |
|---|----------|--------|
| 1 | API endpoint design | Separate `POST /api/reports/fmv/generate/` and `fmv/export/` endpoints |
| 2 | Plaid subtype utilization | Map at `type` level only; include `subtype` in response for display |
| 3 | Entity filter + Plaid accounts | Exclude unmapped Plaid accounts when entity filter is active |
| 4 | Frontend component architecture | New `FmvReport.jsx` file; selector stays in `Reports.jsx` |
| 5 | Chart visualization | PieChart via recharts (already imported); `{name, value}` data format |
| 6 | Double-counting prevention | Exclude mapped asset's FMV snapshot; Plaid account row replaces it |
