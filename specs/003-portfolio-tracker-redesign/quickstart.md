# Quickstart: Portfolio Tracker Redesign

**Feature**: 003-portfolio-tracker-redesign | **Date**: 2026-03-04

## Prerequisites

- Docker Compose running (`docker-compose up --build`)
- At least one entity created
- Optionally: Plaid sandbox institution linked via Accounts page
- Optionally: manual assets with FMV snapshots

## Quick Test After Implementation

### 1. Start the environment

```bash
docker-compose up --build
```

### 2. Run migrations

```bash
docker-compose exec backend python manage.py migrate
```

### 3. Seed test data (if empty)

```bash
docker-compose exec backend python manage.py seed_data
```

### 4. Create a commitment and capital calls

```bash
# Create a commitment: Entity #1 commits $1M to an asset
curl -X POST http://localhost:8000/api/commitments/ \
  -H "Content-Type: application/json" \
  -d '{"entity": 1, "asset": 1, "commitment_date": "2024-01-15", "original_amount": "1000000.00"}'

# Record capital calls against it (use commitment ID from response)
curl -X POST http://localhost:8000/api/capital-calls/ \
  -H "Content-Type: application/json" \
  -d '{"commitment": 1, "call_date": "2024-03-01", "amount": "500000.00"}'

curl -X POST http://localhost:8000/api/capital-calls/ \
  -H "Content-Type: application/json" \
  -d '{"commitment": 1, "call_date": "2024-09-01", "amount": "500000.00"}'
```

### 5. View Portfolio Summary

**Via API:**
```bash
# Full summary (all entities)
curl -X POST http://localhost:8000/api/portfolio/summary/ \
  -H "Content-Type: application/json" \
  -d '{}'

# Filtered by entity
curl -X POST http://localhost:8000/api/portfolio/summary/ \
  -H "Content-Type: application/json" \
  -d '{"entity_ids": "1"}'
```

**Via frontend:**
1. Navigate to `http://localhost:5173/reports`
2. The "Portfolio Summary" tab is selected by default
3. See entity rows with: Original Commitment, % Called, Unfunded, Paid-In, Distributions, Residual, DPI, RVPI, TVPI, IRR
4. See "All Entities" total row at the bottom

### 6. View Asset Class Summary

**Via API:**
```bash
curl -X POST http://localhost:8000/api/portfolio/asset-class-summary/ \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Via frontend:**
1. Click the "Asset Class Summary" tab
2. See allocation breakdown by asset type with pie chart
3. See total value and percentage per class

### 7. View Investment Performance

**Via API:**
```bash
curl -X POST http://localhost:8000/api/portfolio/performance/ \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Via frontend:**
1. Click the "Investment Performance" tab
2. See per-asset IRR, DPI, RVPI, TVPI
3. Filter by entity using the dropdown

### 8. Export to Excel

1. On any view tab, click the "Export" button
2. An .xlsx file downloads with headers matching the on-screen data

### 9. Verify tab persistence

1. Select the "Investment Performance" tab
2. Refresh the browser (F5)
3. Confirm "Investment Performance" is still selected

## Key Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/portfolio/summary/` | POST | Portfolio Summary (entity rollups) |
| `/api/portfolio/asset-class-summary/` | POST | Asset Class Summary (allocation) |
| `/api/portfolio/performance/` | POST | Investment Performance (IRR/DPI/RVPI/TVPI) |
| `/api/portfolio/summary/export/` | POST | Export Portfolio Summary to Excel |
| `/api/portfolio/asset-class-summary/export/` | POST | Export Asset Class Summary to Excel |
| `/api/portfolio/performance/export/` | POST | Export Investment Performance to Excel |
| `/api/commitments/` | CRUD | Commitment management |
| `/api/capital-calls/` | CRUD | Capital Call management |

## What to Look For

### Portfolio Summary should show:
- ✅ One row per entity with all 10 columns from the CSV
- ✅ "All Entities" summary row at the bottom
- ✅ DPI = 2.00 for the CSV example ($1M paid-in, $2M distributions)
- ✅ "—" (dash) for ratios when paid-in is zero
- ✅ "N/A" for IRR when XIRR fails to converge
- ✅ % Called can exceed 100% (overcall scenario)

### Asset Class Summary should show:
- ✅ Breakdown by asset type with values and percentages
- ✅ Pie chart visualization
- ✅ Percentages total to 100%
- ✅ Both Plaid and manual assets included without double-counting

### Investment Performance should show:
- ✅ Per-asset IRR, DPI, RVPI, TVPI
- ✅ Entity-level aggregated metrics
- ✅ Entity filter works
- ✅ IRR values consistent with Excel XIRR to within 0.01%

### Old Distribution report:
- ❌ Distribution report selector is no longer on the Reports page
- ✅ Distribution data entry (Distributions page) still works

## Running Tests

```bash
docker-compose exec backend python manage.py test api -v 2
```

Expected new test coverage:
- `test_commitment_*` — Commitment model validation and CRUD
- `test_capital_call_*` — CapitalCall model validation and CRUD
- `test_portfolio_summary_*` — PE metric calculations, entity rollups
- `test_asset_class_summary_*` — Allocation grouping and percentages
- `test_investment_performance_*` — Per-asset and entity IRR
- `test_zero_paid_in_*` — Division by zero edge cases
- `test_overcall_*` — Overcall handling
- `test_export_*` — Excel export for each view
