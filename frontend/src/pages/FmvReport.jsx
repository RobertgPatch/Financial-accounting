import React, { useState, useEffect } from 'react';
import {
  PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer,
} from 'recharts';
import {
  Paper, Typography, Table as MuiTable, TableBody, TableCell, TableContainer,
  TableHead, TableRow, Chip, Alert, Box,
} from '@mui/material';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import Badge from '../components/ui/Badge';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import { generateFmvReport, exportFmvReport } from '../api/reports';
import { getEntities } from '../api/entities';
import { toArray } from '../api/utils';

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#06B6D4', '#84CC16', '#F97316'];
const formatCurrency = (v) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(v || 0);

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

export default function FmvReport() {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState('');
  const [selectedTypes, setSelectedTypes] = useState([]);
  const [entities, setEntities] = useState([]);
  const [selectedEntities, setSelectedEntities] = useState([]);

  useEffect(() => {
    getEntities()
      .then((res) => setEntities(toArray(res)))
      .catch(() => {});
  }, []);

  const buildParams = () => {
    const params = {};
    if (selectedTypes.length > 0) params.type_filters = selectedTypes;
    if (selectedEntities.length > 0) params.entity_ids = selectedEntities.join(',');
    return params;
  };

  const handleGenerate = async () => {
    setLoading(true);
    setError('');
    try {
      const r = await generateFmvReport(buildParams());
      setReport(r.data);
    } catch (e) {
      setError('Failed to generate FMV report. Make sure the backend is running.');
      setReport(null);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      await exportFmvReport(buildParams());
    } catch {
      alert('Export failed. Make sure the backend is running.');
    } finally {
      setExporting(false);
    }
  };

  const toggleType = (key) => {
    setSelectedTypes((s) => s.includes(key) ? s.filter((t) => t !== key) : [...s, key]);
  };

  const toggleEntity = (id) => {
    setSelectedEntities((s) => s.includes(id) ? s.filter((x) => x !== id) : [...s, id]);
  };

  const byType = report?.by_type || [];
  const items = report?.items || [];
  const pieData = byType.map((t) => ({ name: t.label, value: parseFloat(t.total_value) }));

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Filter Panel */}
        <div className="lg:col-span-1">
          <Card title="FMV Report Configuration">
            <div className="space-y-4">
              {/* Type Filters */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="block text-sm font-medium text-gray-700">Asset Type Filter</label>
                  {selectedTypes.length > 0 && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                      {selectedTypes.length} selected
                    </span>
                  )}
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {ASSET_TYPES.map(({ key, label }) => (
                    <button
                      key={key}
                      type="button"
                      className={`px-2.5 py-1 text-xs rounded-full border transition-colors ${
                        selectedTypes.includes(key)
                          ? 'bg-blue-600 text-white border-blue-600'
                          : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'
                      }`}
                      onClick={() => toggleType(key)}
                    >
                      {label}
                    </button>
                  ))}
                </div>
                <div className="flex gap-2 mt-2">
                  <button
                    type="button"
                    className="text-xs text-blue-600 hover:text-blue-800"
                    onClick={() => setSelectedTypes(ASSET_TYPES.map((t) => t.key))}
                  >
                    Select All
                  </button>
                  <button
                    type="button"
                    className="text-xs text-gray-500 hover:text-gray-700"
                    onClick={() => setSelectedTypes([])}
                  >
                    Clear Filters
                  </button>
                </div>
              </div>

              {/* Entity Filter */}
              {entities.length > 0 && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Filter by Entity</label>
                  <div className="space-y-1 max-h-36 overflow-y-auto border border-gray-200 rounded-lg p-2">
                    {entities.map((e) => (
                      <label key={e.id} className="flex items-center gap-2 cursor-pointer hover:bg-gray-50 p-1 rounded">
                        <input
                          type="checkbox"
                          className="rounded text-blue-600"
                          checked={selectedEntities.includes(e.id)}
                          onChange={() => toggleEntity(e.id)}
                        />
                        <span className="text-sm text-gray-700">{e.name}</span>
                      </label>
                    ))}
                  </div>
                </div>
              )}

              <div className="space-y-2 pt-2">
                <Button className="w-full justify-center" onClick={handleGenerate} disabled={loading}>
                  {loading ? 'Generating...' : 'Generate FMV Report'}
                </Button>
                <Button
                  variant="success"
                  className="w-full justify-center"
                  onClick={handleExport}
                  disabled={exporting || !report}
                >
                  {exporting ? 'Exporting...' : '📥 Export to Excel'}
                </Button>
              </div>
            </div>
          </Card>
        </div>

        {/* Report Content */}
        <div className="lg:col-span-3 space-y-6">
          {error && <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl p-4">{error}</div>}

          {loading && <LoadingSpinner className="py-24" size="lg" />}

          {!loading && !report && !error && (
            <div className="bg-white rounded-xl border border-gray-200 p-16 text-center">
              <p className="text-4xl mb-4">📊</p>
              <p className="text-gray-500 text-lg font-medium">FMV Report</p>
              <p className="text-gray-400 text-sm mt-1">Configure filters and click "Generate FMV Report" to view your portfolio valuation</p>
            </div>
          )}

          {!loading && report && (
            <>
              {/* Total FMV Card */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="bg-white rounded-xl border border-gray-200 p-4">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xl">💰</span>
                    <span className="text-xs font-medium text-gray-500">Total FMV</span>
                  </div>
                  <p className="text-2xl font-bold text-gray-900">{formatCurrency(report.total_fmv)}</p>
                </div>
                <div className="bg-white rounded-xl border border-gray-200 p-4">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xl">📋</span>
                    <span className="text-xs font-medium text-gray-500">Items</span>
                  </div>
                  <p className="text-2xl font-bold text-gray-900">{report.item_count}</p>
                </div>
              </div>

              {/* Empty state */}
              {report.item_count === 0 && (
                <Alert severity="info" sx={{ borderRadius: 3 }}>
                  No FMV data available. Link accounts in the Accounts page or add assets with FMV snapshots.
                </Alert>
              )}

              {/* Visualization: Pie Chart + Summary Table */}
              {byType.length > 0 && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <Card title="Allocation by Asset Type">
                    <ResponsiveContainer width="100%" height={300}>
                      <PieChart>
                        <Pie
                          data={pieData}
                          dataKey="value"
                          nameKey="name"
                          cx="50%"
                          cy="50%"
                          outerRadius={100}
                        >
                          {pieData.map((_, i) => (
                            <Cell key={i} fill={COLORS[i % COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip formatter={(v) => formatCurrency(v)} />
                        <Legend />
                      </PieChart>
                    </ResponsiveContainer>
                  </Card>

                  <Card title="Type Breakdown">
                    <div className="overflow-x-auto">
                      <table className="min-w-full divide-y divide-gray-200">
                        <thead>
                          <tr className="bg-gray-50">
                            {['Asset Type', 'Total Value', 'Items', 'Allocation'].map((h) => (
                              <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">{h}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                          {byType.map((row, i) => (
                            <tr key={i} className="hover:bg-gray-50">
                              <td className="px-4 py-3 text-sm font-medium text-gray-900">
                                <span className="inline-block w-3 h-3 rounded-full mr-2" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                                {row.label}
                              </td>
                              <td className="px-4 py-3 text-sm font-semibold text-emerald-600">{formatCurrency(row.total_value)}</td>
                              <td className="px-4 py-3 text-sm text-gray-600">{row.count}</td>
                              <td className="px-4 py-3 text-sm text-gray-600">{row.percentage}%</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </Card>
                </div>
              )}

              {/* Line Items Table */}
              {items.length > 0 && (
                <Card title="Line Items">
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead>
                        <tr className="bg-gray-50">
                          {['Name', 'Value', 'Source', 'Asset Type', 'Institution', 'Account'].map((h) => (
                            <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {items.map((item, i) => (
                          <tr key={i} className="hover:bg-gray-50">
                            <td className="px-4 py-3 text-sm font-medium text-gray-900">{item.name}</td>
                            <td className="px-4 py-3 text-sm font-semibold">
                              <span className={parseFloat(item.value) < 0 ? 'text-red-600' : 'text-emerald-600'}>
                                {formatCurrency(item.value)}
                              </span>
                              {item.needs_sync && (
                                <Chip label="Needs Sync" size="small" color="warning" sx={{ ml: 1, height: 20, fontSize: '0.65rem' }} />
                              )}
                            </td>
                            <td className="px-4 py-3 text-sm">
                              <Badge color={item.source === 'plaid' ? 'blue' : 'green'}>
                                {item.source === 'plaid' ? 'Plaid' : 'Manual'}
                              </Badge>
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-600">{item.label}</td>
                            <td className="px-4 py-3 text-sm text-gray-600">
                              {item.institution ? (
                                <span>{item.institution}{item.subtype ? ` · ${item.subtype}` : ''}</span>
                              ) : (
                                item.snapshot_date || '-'
                              )}
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-500">
                              {item.mask ? `••••${item.mask}` : '-'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Card>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
