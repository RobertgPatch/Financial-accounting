# Quickstart: FMV Auto-Reporting

**Feature**: 002-fmv-auto-reporting | **Date**: 2026-02-28

## Prerequisites

- Docker Compose running (`docker-compose up --build`)
- Plaid sandbox credentials in `.env` (PLAID_CLIENT_ID, PLAID_SECRET, PLAID_ENV=sandbox)
- At least one Plaid institution linked via the Accounts page (for Plaid data)
- Optionally: manual assets with FMV snapshots (for manual data)

## Quick Test After Implementation

### 1. Start the environment

```bash
docker-compose up --build
```

### 2. Seed test data (if empty)

```bash
docker-compose exec backend python manage.py seed_data
```

### 3. Link a Plaid sandbox institution

1. Navigate to `http://localhost:5173/accounts`
2. Click "Link Account" to open Plaid Link
3. Use sandbox credentials: `user_good` / `pass_good`
4. Select any institution (e.g., Chase)
5. Accounts appear with balances after sync

### 4. Add a manual asset with FMV

```bash
# Create a manual real estate asset
curl -X POST http://localhost:8000/api/assets/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Beach House", "asset_type": "real_estate"}'

# Add an FMV snapshot (use the asset ID from the response)
curl -X POST http://localhost:8000/api/fmv-snapshots/ \
  -H "Content-Type: application/json" \
  -d '{"asset": 1, "snapshot_date": "2026-02-28", "value": "500000.00", "source": "manual"}'
```

### 5. Generate the FMV report

**Via API:**
```bash
# Full report (no filters)
curl -X POST http://localhost:8000/api/reports/fmv/generate/ \
  -H "Content-Type: application/json" \
  -d '{}'

# Filtered by type
curl -X POST http://localhost:8000/api/reports/fmv/generate/ \
  -H "Content-Type: application/json" \
  -d '{"type_filters": ["cash", "real_estate"]}'

# Filtered by entity
curl -X POST http://localhost:8000/api/reports/fmv/generate/ \
  -H "Content-Type: application/json" \
  -d '{"entity_ids": "1,2"}'
```

**Via frontend:**
1. Navigate to `http://localhost:5173/reports`
2. Select "FMV Report" from the report type selector
3. Optionally select type filters and/or entity filters
4. Click "Generate Report"
5. View breakdown by type with pie chart and line items table
6. Click "Export" for Excel download

### 6. Verify Distribution report is unchanged

1. On the Reports page, select "Distribution Report"
2. Confirm it shows distribution data only — no FMV totals or asset valuations
3. Export works as before

## Key Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/reports/fmv/generate/` | POST | Generate FMV report |
| `/api/reports/fmv/export/` | POST | Export FMV report to Excel |
| `/api/reports/generate/` | POST | Distribution report (unchanged) |
| `/api/reports/export/` | POST | Distribution export (unchanged) |

## What to Look For

### FMV Report should show:
- ✅ All Plaid-linked account balances (auto-included, no mapping needed)
- ✅ Manual assets with FMV snapshots
- ✅ Each item labeled "Plaid" or "Manual" source
- ✅ Type breakdown with totals, counts, and percentages
- ✅ Pie chart showing allocation by type
- ✅ Grand total across all items
- ✅ Negative balances (credit cards) reducing total

### FMV Report should NOT show:
- ❌ Manual assets that are mapped to Plaid accounts (prevents double-counting)
- ❌ Manual assets without any FMV snapshots
- ❌ Unmapped Plaid accounts when entity filter is active

### Distribution Report should NOT show:
- ❌ FMV totals or net worth data
- ❌ Asset valuation information

## Running Tests

```bash
docker-compose exec backend python manage.py test api -v 2
```

Expected new test coverage:
- `test_fmv_report_*` — FMV report generation logic
- `test_plaid_type_mapping` — Type mapping correctness
- `test_double_count_prevention` — Mapped account exclusion
- `test_entity_filter_plaid_accounts` — Entity filter behavior
- `test_fmv_export` — Excel export generation
