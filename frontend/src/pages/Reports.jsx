import React, { useState, useEffect } from 'react';
import { Tabs, Tab, Box } from '@mui/material';
import PortfolioSummary from './PortfolioSummary';
import AssetClassSummary from './AssetClassSummary';
import InvestmentPerformance from './InvestmentPerformance';

const TAB_KEY = 'portfolio_tracker_tab';

const TABS = [
  { label: 'Portfolio Summary', Component: PortfolioSummary },
  { label: 'Asset Class Summary', Component: AssetClassSummary },
  { label: 'Investment Performance', Component: InvestmentPerformance },
];

export default function Reports() {
  const [tabIndex, setTabIndex] = useState(() => {
    const stored = localStorage.getItem(TAB_KEY);
    const idx = stored !== null ? Number(stored) : 0;
    return idx >= 0 && idx < TABS.length ? idx : 0;
  });

  useEffect(() => {
    localStorage.setItem(TAB_KEY, String(tabIndex));
  }, [tabIndex]);

  const ActiveComponent = TABS[tabIndex].Component;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Portfolio Tracker</h1>
        <p className="text-sm text-gray-500 mt-1">
          Track portfolio performance, asset allocation, and investment returns.
        </p>
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

      <ActiveComponent />
    </div>
  );
}
