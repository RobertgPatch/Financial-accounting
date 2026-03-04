import React, { useState, useEffect, useCallback } from 'react';
import { Tabs, Tab, Box } from '@mui/material';
import PortfolioSummary from './PortfolioSummary';
import AssetClassSummary from './AssetClassSummary';
import InvestmentPerformance from './InvestmentPerformance';

const TAB_KEY = 'portfolio_tracker_tab';
const PERIOD_KEY = 'portfolio_tracker_period';

const TABS = [
  { label: 'Portfolio Summary', Component: PortfolioSummary },
  { label: 'Asset Class Summary', Component: AssetClassSummary },
  { label: 'Investment Performance', Component: InvestmentPerformance },
];

const currentYear = new Date().getFullYear();
const YEARS = Array.from({ length: 15 }, (_, i) => currentYear - i);
const QUARTERS = [
  { label: 'Q1 (Jan–Mar)', value: 1 },
  { label: 'Q2 (Apr–Jun)', value: 2 },
  { label: 'Q3 (Jul–Sep)', value: 3 },
  { label: 'Q4 (Oct–Dec)', value: 4 },
];

function computeDateRange(mode, year, quarter, startYear, endYear) {
  if (mode === 'year' && year) {
    return { start_date: `${year}-01-01`, end_date: `${year}-12-31` };
  }
  if (mode === 'quarter' && year && quarter) {
    const qStartMonth = (quarter - 1) * 3 + 1;
    const qEndMonth = quarter * 3;
    const lastDay = new Date(year, qEndMonth, 0).getDate();
    const sm = String(qStartMonth).padStart(2, '0');
    const em = String(qEndMonth).padStart(2, '0');
    return {
      start_date: `${year}-${sm}-01`,
      end_date: `${year}-${em}-${String(lastDay).padStart(2, '0')}`,
    };
  }
  if (mode === 'range' && startYear && endYear) {
    return { start_date: `${startYear}-01-01`, end_date: `${endYear}-12-31` };
  }
  return {}; // all time — no date filtering
}

export default function Reports() {
  const [tabIndex, setTabIndex] = useState(() => {
    const stored = localStorage.getItem(TAB_KEY);
    const idx = stored !== null ? Number(stored) : 0;
    return idx >= 0 && idx < TABS.length ? idx : 0;
  });

  // Period filter state
  const [periodMode, setPeriodMode] = useState('all'); // all | year | quarter | range
  const [year, setYear] = useState(currentYear);
  const [quarter, setQuarter] = useState(1);
  const [startYear, setStartYear] = useState(currentYear - 2);
  const [endYear, setEndYear] = useState(currentYear);

  // The dateRange object passed to each tab
  const [dateRange, setDateRange] = useState({});

  // Recalculate dateRange when filter changes
  const applyPeriod = useCallback(() => {
    setDateRange(computeDateRange(periodMode, year, quarter, startYear, endYear));
  }, [periodMode, year, quarter, startYear, endYear]);

  // Apply on mode / param changes
  useEffect(() => { applyPeriod(); }, [applyPeriod]);

  useEffect(() => {
    localStorage.setItem(TAB_KEY, String(tabIndex));
  }, [tabIndex]);

  const ActiveComponent = TABS[tabIndex].Component;

  const pillCls = (active) =>
    `px-3 py-1 rounded-full text-xs font-medium border transition-colors cursor-pointer ${
      active
        ? 'bg-blue-100 border-blue-300 text-blue-700'
        : 'bg-white border-gray-300 text-gray-600 hover:bg-gray-50'
    }`;

  const selectCls =
    'px-2 py-1 rounded border border-gray-300 text-xs bg-white text-gray-700 focus:outline-none focus:ring-1 focus:ring-blue-400';

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Portfolio Tracker</h1>
        <p className="text-sm text-gray-500 mt-1">
          Track portfolio performance, asset allocation, and investment returns.
        </p>
      </div>

      {/* Period Filters */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide mr-1">Period:</span>
        <button className={pillCls(periodMode === 'all')} onClick={() => setPeriodMode('all')}>
          All Time
        </button>
        <button className={pillCls(periodMode === 'year')} onClick={() => setPeriodMode('year')}>
          Year
        </button>
        <button className={pillCls(periodMode === 'quarter')} onClick={() => setPeriodMode('quarter')}>
          Quarter
        </button>
        <button className={pillCls(periodMode === 'range')} onClick={() => setPeriodMode('range')}>
          Year Range
        </button>

        {periodMode === 'year' && (
          <select className={selectCls} value={year} onChange={(e) => setYear(Number(e.target.value))}>
            {YEARS.map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        )}

        {periodMode === 'quarter' && (
          <>
            <select className={selectCls} value={year} onChange={(e) => setYear(Number(e.target.value))}>
              {YEARS.map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
            <select className={selectCls} value={quarter} onChange={(e) => setQuarter(Number(e.target.value))}>
              {QUARTERS.map((q) => (
                <option key={q.value} value={q.value}>{q.label}</option>
              ))}
            </select>
          </>
        )}

        {periodMode === 'range' && (
          <>
            <select className={selectCls} value={startYear} onChange={(e) => setStartYear(Number(e.target.value))}>
              {YEARS.map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
            <span className="text-xs text-gray-500">to</span>
            <select className={selectCls} value={endYear} onChange={(e) => setEndYear(Number(e.target.value))}>
              {YEARS.map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
          </>
        )}

        {periodMode !== 'all' && (
          <span className="text-xs text-gray-400 ml-1">
            {dateRange.start_date} → {dateRange.end_date}
          </span>
        )}
      </div>

      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs
          value={tabIndex}
          onChange={(_, v) => setTabIndex(v)}
          variant="scrollable"
          scrollButtons="auto"
          sx={{
            '& .MuiTab-root': {
              textTransform: 'none',
              fontWeight: 600,
              fontSize: '0.875rem',
            },
          }}
        >
          {TABS.map((t, i) => (
            <Tab key={i} label={t.label} />
          ))}
        </Tabs>
      </Box>

      <ActiveComponent dateRange={dateRange} />
    </div>
  );
}
