import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import Badge from '../components/ui/Badge';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import { generateReport, exportReport } from '../api/reports';
import { getEntities } from '../api/entities';
import { getAssets } from '../api/assets';
import { format, parseISO } from 'date-fns';

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#06B6D4', '#84CC16'];
const formatCurrency = (v) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(v || 0);
const currentYear = new Date().getFullYear();
const years = Array.from({ length: 4 }, (_, i) => currentYear - i);
const months = ['January','February','March','April','May','June','July','August','September','October','November','December'];

export default function Reports() {
  const [entities, setEntities] = useState([]);
  const [assets, setAssets] = useState([]);
  const [periodType, setPeriodType] = useState('yearly');
  const [year, setYear] = useState(currentYear);
  const [quarter, setQuarter] = useState(1);
  const [month, setMonth] = useState(1);
  const [selectedEntities, setSelectedEntities] = useState([]);
  const [selectedAssets, setSelectedAssets] = useState([]);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([getEntities(), getAssets()])
      .then(([e, a]) => {
        setEntities(e.data.results || e.data || []);
        setAssets(a.data.results || a.data || []);
      })
      .catch(() => {});
  }, []);

  const buildParams = () => {
    const params = { period_type: periodType, year };
    if (periodType === 'quarterly') params.quarter = quarter;
    if (periodType === 'monthly') params.month = month;
    if (selectedEntities.length > 0) params.entity_ids = selectedEntities.join(',');
    if (selectedAssets.length > 0) params.asset_ids = selectedAssets.join(',');
    return params;
  };

  const handleGenerate = async () => {
    setLoading(true);
    setError('');
    try {
      const r = await generateReport(buildParams());
      setReport(r.data);
    } catch (e) {
      setError('Failed to generate report. Make sure the backend is running.');
      setReport(null);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      await exportReport(buildParams());
    } catch {
      alert('Export failed. Make sure the backend is running.');
    } finally {
      setExporting(false);
    }
  };

  const toggleEntity = (id) => setSelectedEntities(s => s.includes(id) ? s.filter(x => x !== id) : [...s, id]);
  const toggleAsset = (id) => setSelectedAssets(s => s.includes(id) ? s.filter(x => x !== id) : [...s, id]);

  const summary = report?.summary || {};
  const byEntity = report?.by_entity || [];
  const byAsset = report?.by_asset || [];
  const details = report?.detail || [];

  // Build timeline from detail data (group by month)
  const timelineMap = {};
  details.forEach(row => {
    const monthKey = row.distribution_date ? row.distribution_date.slice(0, 7) : '';
    if (!monthKey) return;
    if (!timelineMap[monthKey]) timelineMap[monthKey] = { month: monthKey, amount: 0 };
    timelineMap[monthKey].amount += parseFloat(row.amount || 0);
  });
  const timeline = Object.values(timelineMap).sort((a, b) => a.month.localeCompare(b.month));

  const entityPieData = byEntity.map(e => ({ name: e.entity_name || e.name, value: parseFloat(e.total_amount || 0) }));
  const totalAmount = byEntity.reduce((s, e) => s + parseFloat(e.total_amount || 0), 0);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-1">
          <Card title="Report Configuration">
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Period Type</label>
                <div className="flex rounded-lg border border-gray-300 overflow-hidden">
                  {['yearly', 'quarterly', 'monthly'].map(p => (
                    <button key={p} type="button"
                      className={`flex-1 py-1.5 text-xs font-medium transition-colors ${periodType === p ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}`}
                      onClick={() => setPeriodType(p)}>
                      {p.charAt(0).toUpperCase() + p.slice(1)}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Year</label>
                <select className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" value={year} onChange={e => setYear(parseInt(e.target.value))}>
                  {years.map(y => <option key={y} value={y}>{y}</option>)}
                </select>
              </div>

              {periodType === 'quarterly' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Quarter</label>
                  <select className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" value={quarter} onChange={e => setQuarter(parseInt(e.target.value))}>
                    {[1,2,3,4].map(q => <option key={q} value={q}>Q{q}</option>)}
                  </select>
                </div>
              )}

              {periodType === 'monthly' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Month</label>
                  <select className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" value={month} onChange={e => setMonth(parseInt(e.target.value))}>
                    {months.map((m, i) => <option key={i+1} value={i+1}>{m}</option>)}
                  </select>
                </div>
              )}

              {entities.length > 0 && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Filter by Entity</label>
                  <div className="space-y-1 max-h-36 overflow-y-auto border border-gray-200 rounded-lg p-2">
                    {entities.map(e => (
                      <label key={e.id} className="flex items-center gap-2 cursor-pointer hover:bg-gray-50 p-1 rounded">
                        <input type="checkbox" className="rounded text-blue-600" checked={selectedEntities.includes(e.id)} onChange={() => toggleEntity(e.id)} />
                        <span className="text-sm text-gray-700">{e.name}</span>
                      </label>
                    ))}
                  </div>
                </div>
              )}

              {assets.length > 0 && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Filter by Asset</label>
                  <div className="space-y-1 max-h-36 overflow-y-auto border border-gray-200 rounded-lg p-2">
                    {assets.map(a => (
                      <label key={a.id} className="flex items-center gap-2 cursor-pointer hover:bg-gray-50 p-1 rounded">
                        <input type="checkbox" className="rounded text-blue-600" checked={selectedAssets.includes(a.id)} onChange={() => toggleAsset(a.id)} />
                        <span className="text-sm text-gray-700">{a.name}</span>
                      </label>
                    ))}
                  </div>
                </div>
              )}

              <div className="space-y-2 pt-2">
                <Button className="w-full justify-center" onClick={handleGenerate} disabled={loading}>
                  {loading ? 'Generating...' : 'Generate Report'}
                </Button>
                <Button variant="success" className="w-full justify-center" onClick={handleExport} disabled={exporting || !report}>
                  {exporting ? 'Exporting...' : '📥 Export to Excel'}
                </Button>
              </div>
            </div>
          </Card>
        </div>

        <div className="lg:col-span-3 space-y-6">
          {error && <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl p-4">{error}</div>}

          {loading && <LoadingSpinner className="py-24" size="lg" />}

          {!loading && !report && !error && (
            <div className="bg-white rounded-xl border border-gray-200 p-16 text-center">
              <p className="text-4xl mb-4">📊</p>
              <p className="text-gray-500 text-lg font-medium">Configure and generate a report</p>
              <p className="text-gray-400 text-sm mt-1">Select your parameters and click "Generate Report"</p>
            </div>
          )}

          {!loading && report && (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {[
                  { label: 'Total Distributed', value: formatCurrency(summary.total_distributions || totalAmount), icon: '💰' },
                  { label: 'Distributions', value: summary.distribution_count || details.length, icon: '📋' },
                  { label: 'Entities', value: summary.entity_count || byEntity.length, icon: '🏢' },
                  { label: 'Assets', value: summary.asset_count || byAsset.length, icon: '💼' },
                ].map(({ label, value, icon }) => (
                  <div key={label} className="bg-white rounded-xl border border-gray-200 p-4">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xl">{icon}</span>
                      <span className="text-xs font-medium text-gray-500">{label}</span>
                    </div>
                    <p className="text-xl font-bold text-gray-900">{value}</p>
                  </div>
                ))}
              </div>

              {byEntity.length > 0 && (
                <Card title="Distributions by Entity">
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead>
                        <tr className="bg-gray-50">
                          {['Entity', 'Type', 'Distributions', 'Total Amount', '% of Total'].map(h => (
                            <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {byEntity.map((row, i) => {
                          const pct = totalAmount > 0 ? ((parseFloat(row.total_amount || 0) / totalAmount) * 100).toFixed(1) : '0.0';
                          return (
                            <tr key={i} className="hover:bg-gray-50">
                              <td className="px-4 py-3 text-sm font-medium text-gray-900">{row.entity_name || row.name}</td>
                              <td className="px-4 py-3 text-sm"><Badge color="blue">{row.entity_type || '-'}</Badge></td>
                              <td className="px-4 py-3 text-sm text-gray-600">{row.distribution_count || row.count || '-'}</td>
                              <td className="px-4 py-3 text-sm font-semibold text-emerald-600">{formatCurrency(row.total_amount)}</td>
                              <td className="px-4 py-3 text-sm text-gray-600">{pct}%</td>
                            </tr>
                          );
                        })}
                        <tr className="bg-gray-50 font-semibold">
                          <td className="px-4 py-3 text-sm">Total</td>
                          <td className="px-4 py-3" /><td className="px-4 py-3" />
                          <td className="px-4 py-3 text-sm text-emerald-600">{formatCurrency(totalAmount)}</td>
                          <td className="px-4 py-3 text-sm">100%</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </Card>
              )}

              {byAsset.length > 0 && (
                <Card title="Distributions by Asset">
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead>
                        <tr className="bg-gray-50">
                          {['Asset', 'Type', 'Distributions', 'Total Amount', '% of Total'].map(h => (
                            <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {byAsset.map((row, i) => {
                          const assetTotal = byAsset.reduce((s, r) => s + parseFloat(r.total_amount || 0), 0);
                          const pct = assetTotal > 0 ? ((parseFloat(row.total_amount || 0) / assetTotal) * 100).toFixed(1) : '0.0';
                          return (
                            <tr key={i} className="hover:bg-gray-50">
                              <td className="px-4 py-3 text-sm font-medium text-gray-900">{row.asset_name || row.name}</td>
                              <td className="px-4 py-3 text-sm"><Badge color="green">{row.asset_type || '-'}</Badge></td>
                              <td className="px-4 py-3 text-sm text-gray-600">{row.distribution_count || row.count || '-'}</td>
                              <td className="px-4 py-3 text-sm font-semibold text-emerald-600">{formatCurrency(row.total_amount)}</td>
                              <td className="px-4 py-3 text-sm text-gray-600">{pct}%</td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </Card>
              )}

              {(timeline.length > 0 || entityPieData.length > 0) && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {timeline.length > 0 && (
                    <Card title="Distribution Timeline">
                      <ResponsiveContainer width="100%" height={240}>
                        <BarChart data={timeline}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                          <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                          <YAxis tickFormatter={v => `$${(v/1000).toFixed(0)}k`} tick={{ fontSize: 11 }} />
                          <Tooltip formatter={v => formatCurrency(v)} />
                          <Bar dataKey="amount" fill="#3B82F6" radius={[4,4,0,0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    </Card>
                  )}
                  {entityPieData.length > 0 && (
                    <Card title="Entity Allocation">
                      <ResponsiveContainer width="100%" height={240}>
                        <PieChart>
                          <Pie data={entityPieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80}>
                            {entityPieData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                          </Pie>
                          <Tooltip formatter={v => formatCurrency(v)} />
                          <Legend formatter={(value, entry) => `${value}: ${formatCurrency(entry.payload.value)}`} />
                        </PieChart>
                      </ResponsiveContainer>
                    </Card>
                  )}
                </div>
              )}

              {details.length > 0 && (
                <Card title="Distribution Details">
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead>
                        <tr className="bg-gray-50">
                          {['Date', 'Asset', 'Entity', 'Amount', 'Type', 'Notes'].map(h => (
                            <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {details.map((row, i) => (
                          <tr key={i} className="hover:bg-gray-50">
                            <td className="px-4 py-3 text-sm text-gray-600">{row.distribution_date ? format(parseISO(row.distribution_date), 'MMM dd, yyyy') : '-'}</td>
                            <td className="px-4 py-3 text-sm font-medium text-gray-900">{row.asset_name || row.asset || '-'}</td>
                            <td className="px-4 py-3 text-sm text-gray-700">{row.entity_name || row.entity || '-'}</td>
                            <td className="px-4 py-3 text-sm font-semibold text-emerald-600">{formatCurrency(row.amount)}</td>
                            <td className="px-4 py-3 text-sm"><Badge color="blue">{(row.distribution_type || '').replace('_', ' ')}</Badge></td>
                            <td className="px-4 py-3 text-sm text-gray-500">{row.notes || '-'}</td>
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
