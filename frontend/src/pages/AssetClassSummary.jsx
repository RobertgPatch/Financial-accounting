import React, { useState, useEffect, useCallback } from 'react';
import {
  PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer,
} from 'recharts';
import {
  Paper, Typography, Table as MuiTable, TableBody, TableCell, TableContainer,
  TableHead, TableRow, Alert, Box, Chip,
} from '@mui/material';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import { getAssetClassSummary, exportAssetClassSummary } from '../api/reports';
import { getEntities } from '../api/entities';
import { toArray } from '../api/utils';

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#06B6D4', '#84CC16', '#F97316'];
const formatCurrency = (v) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(v || 0);

const ASSET_TYPES = [
  { key: 'cash', label: 'Cash & Equivalents' },
  { key: 'real_estate', label: 'Real Estate' },
  { key: 'public_equity', label: 'Public Equity' },
  { key: 'private_equity', label: 'Private Equity' },
  { key: 'fixed_income', label: 'Fixed Income' },
  { key: 'hedge_fund', label: 'Hedge Fund' },
  { key: 'crypto', label: 'Cryptocurrency' },
  { key: 'collectible', label: 'Collectible' },
  { key: 'other', label: 'Other' },
];

export default function AssetClassSummary() {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState('');
  const [entities, setEntities] = useState([]);
  const [selectedEntities, setSelectedEntities] = useState([]);
  const [selectedTypes, setSelectedTypes] = useState([]);

  useEffect(() => {
    getEntities()
      .then((res) => setEntities(toArray(res)))
      .catch(() => {});
  }, []);

  const handleGenerate = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const params = {};
      if (selectedEntities.length > 0) params.entity_ids = selectedEntities.join(',');
      if (selectedTypes.length > 0) params.type_filters = selectedTypes;
      const res = await getAssetClassSummary(params);
      setReport(res.data);
    } catch {
      setError('Failed to generate asset class summary.');
      setReport(null);
    } finally {
      setLoading(false);
    }
  }, [selectedEntities, selectedTypes]);

  useEffect(() => {
    handleGenerate();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleExport = async () => {
    setExporting(true);
    try {
      const params = {};
      if (selectedEntities.length > 0) params.entity_ids = selectedEntities.join(',');
      if (selectedTypes.length > 0) params.type_filters = selectedTypes;
      await exportAssetClassSummary(params);
    } catch {
      alert('Export failed.');
    } finally {
      setExporting(false);
    }
  };

  const toggleEntity = (id) => {
    setSelectedEntities((prev) =>
      prev.includes(id) ? prev.filter((e) => e !== id) : [...prev, id],
    );
  };

  const toggleType = (key) => {
    setSelectedTypes((prev) =>
      prev.includes(key) ? prev.filter((t) => t !== key) : [...prev, key],
    );
  };

  // Prepare pie chart data
  const pieData = (report?.by_class || []).map((c, i) => ({
    name: c.label,
    value: Number(c.total_value),
    color: COLORS[i % COLORS.length],
  }));

  return (
    <div className="space-y-6">
      {/* Filters */}
      <Card title="Filters">
        <div className="space-y-4">
          {entities.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Entities</label>
              <div className="flex flex-wrap gap-2">
                {entities.map((e) => (
                  <button
                    key={e.id}
                    onClick={() => toggleEntity(e.id)}
                    className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
                      selectedEntities.includes(e.id)
                        ? 'bg-blue-100 border-blue-300 text-blue-700'
                        : 'bg-white border-gray-300 text-gray-600 hover:bg-gray-50'
                    }`}
                  >
                    {e.name}
                  </button>
                ))}
              </div>
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Asset Types</label>
            <div className="flex flex-wrap gap-2">
              {ASSET_TYPES.map((t) => (
                <button
                  key={t.key}
                  onClick={() => toggleType(t.key)}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
                    selectedTypes.includes(t.key)
                      ? 'bg-emerald-100 border-emerald-300 text-emerald-700'
                      : 'bg-white border-gray-300 text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>
          <div className="flex gap-3">
            <Button onClick={handleGenerate} disabled={loading}>
              {loading ? 'Loading...' : 'Refresh'}
            </Button>
            {report && (
              <Button variant="secondary" onClick={handleExport} disabled={exporting}>
                {exporting ? 'Exporting...' : 'Export to Excel'}
              </Button>
            )}
          </div>
        </div>
      </Card>

      {error && <Alert severity="error">{error}</Alert>}
      {loading && <LoadingSpinner />}

      {report && !loading && (
        <>
          {/* Summary KPIs */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Card>
              <p className="text-sm text-gray-500">Total Portfolio Value</p>
              <p className="text-2xl font-bold text-gray-900">
                {formatCurrency(report.total_value)}
              </p>
            </Card>
            <Card>
              <p className="text-sm text-gray-500">Asset Classes</p>
              <p className="text-2xl font-bold text-gray-900">
                {(report.by_class || []).length}
              </p>
            </Card>
            <Card>
              <p className="text-sm text-gray-500">Total Items</p>
              <p className="text-2xl font-bold text-gray-900">{report.item_count}</p>
            </Card>
          </div>

          {/* Pie Chart + Table Side-by-Side */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Pie Chart */}
            {pieData.length > 0 && (
              <Card title="Allocation by Asset Class">
                <ResponsiveContainer width="100%" height={320}>
                  <PieChart>
                    <Pie
                      data={pieData}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={110}
                      label={({ name, percent }) =>
                        `${name} ${(percent * 100).toFixed(1)}%`
                      }
                    >
                      {pieData.map((entry, i) => (
                        <Cell key={i} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(v) => formatCurrency(v)}
                    />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </Card>
            )}

            {/* Asset Class Table */}
            <Card title="Breakdown">
              <TableContainer component={Paper} elevation={0}>
                <MuiTable size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ fontWeight: 700, fontSize: '0.75rem' }}>
                        Asset Class
                      </TableCell>
                      <TableCell align="right" sx={{ fontWeight: 700, fontSize: '0.75rem' }}>
                        Value
                      </TableCell>
                      <TableCell align="right" sx={{ fontWeight: 700, fontSize: '0.75rem' }}>
                        % of Portfolio
                      </TableCell>
                      <TableCell align="right" sx={{ fontWeight: 700, fontSize: '0.75rem' }}>
                        Items
                      </TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {(report.by_class || []).map((cls, i) => (
                      <TableRow key={cls.asset_type} hover>
                        <TableCell sx={{ fontSize: '0.8rem' }}>
                          <div className="flex items-center gap-2">
                            <span
                              className="w-3 h-3 rounded-full inline-block"
                              style={{ backgroundColor: COLORS[i % COLORS.length] }}
                            />
                            {cls.label}
                          </div>
                        </TableCell>
                        <TableCell align="right" sx={{ fontSize: '0.8rem' }}>
                          {formatCurrency(cls.total_value)}
                        </TableCell>
                        <TableCell align="right" sx={{ fontSize: '0.8rem' }}>
                          {Number(cls.pct_of_portfolio).toFixed(2)}%
                        </TableCell>
                        <TableCell align="right" sx={{ fontSize: '0.8rem' }}>
                          {cls.item_count}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </MuiTable>
              </TableContainer>

              {(report.by_class || []).length === 0 && (
                <div className="text-center py-8 text-gray-400">
                  <p>No assets found. Add assets with FMV snapshots or link Plaid accounts.</p>
                </div>
              )}
            </Card>
          </div>

          {/* Individual Items Table */}
          {(report.items || []).length > 0 && (
            <Card title="Individual Assets">
              <TableContainer component={Paper} elevation={0}>
                <MuiTable size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ fontWeight: 700, fontSize: '0.75rem' }}>Name</TableCell>
                      <TableCell sx={{ fontWeight: 700, fontSize: '0.75rem' }}>Type</TableCell>
                      <TableCell sx={{ fontWeight: 700, fontSize: '0.75rem' }}>Source</TableCell>
                      <TableCell align="right" sx={{ fontWeight: 700, fontSize: '0.75rem' }}>Value</TableCell>
                      <TableCell sx={{ fontWeight: 700, fontSize: '0.75rem' }}>As Of</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {report.items.map((item, i) => (
                      <TableRow key={i} hover>
                        <TableCell sx={{ fontSize: '0.8rem' }}>{item.name}</TableCell>
                        <TableCell sx={{ fontSize: '0.8rem' }}>
                          <Chip
                            label={item.asset_type}
                            size="small"
                            variant="outlined"
                            sx={{ fontSize: '0.7rem' }}
                          />
                        </TableCell>
                        <TableCell sx={{ fontSize: '0.8rem' }}>
                          <Chip
                            label={item.source}
                            size="small"
                            color={item.source === 'plaid' ? 'primary' : 'default'}
                            sx={{ fontSize: '0.7rem' }}
                          />
                        </TableCell>
                        <TableCell align="right" sx={{ fontSize: '0.8rem' }}>
                          {formatCurrency(item.value)}
                        </TableCell>
                        <TableCell sx={{ fontSize: '0.8rem' }}>
                          {item.snapshot_date || '—'}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </MuiTable>
              </TableContainer>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
