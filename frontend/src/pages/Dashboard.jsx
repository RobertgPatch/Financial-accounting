import React, { useState, useEffect, useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts';
import Card from '../components/ui/Card';
import Table from '../components/ui/Table';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import { getEntities } from '../api/entities';
import { getAssets } from '../api/assets';
import { getDistributions } from '../api/distributions';
import { toArray } from '../api/utils';
import { format, parseISO } from 'date-fns';

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899'];
const DIST_TYPES = ['regular', 'special', 'return_of_capital', 'liquidating'];

const formatCurrency = (v) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(v || 0);

/* ── helper: resolve an entity / asset id from a field that may be an object or raw id ── */
const resolveId = (val) => String(typeof val === 'object' ? val?.id : val);

export default function Dashboard() {
  const [entities, setEntities] = useState([]);
  const [assets, setAssets] = useState([]);
  const [distributions, setDistributions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  /* ── Filter state ── */
  const [filterYear, setFilterYear] = useState(new Date().getFullYear());
  const [filterEntity, setFilterEntity] = useState('');
  const [filterAsset, setFilterAsset] = useState('');
  const [filterType, setFilterType] = useState('');

  useEffect(() => {
    Promise.all([getEntities(), getAssets(), getDistributions()])
      .then(([e, a, d]) => {
        setEntities(toArray(e));
        setAssets(toArray(a));
        setDistributions(toArray(d));
      })
      .catch((err) => {
        console.error('Dashboard data fetch failed:', err);
        setError('Unable to load dashboard data. The server may be starting up — please try again in a moment.');
      })
      .finally(() => setLoading(false));
  }, []);

  /* ── Available years derived from data ── */
  const availableYears = useMemo(() => {
    const years = new Set();
    distributions.forEach(d => { if (d.distribution_date) years.add(new Date(d.distribution_date).getFullYear()); });
    if (years.size === 0) years.add(new Date().getFullYear());
    return Array.from(years).sort((a, b) => b - a);
  }, [distributions]);

  /* ── Effective year: falls back to first available year if selected year has no data ── */
  const effectiveFilterYear = useMemo(
    () => (availableYears.length > 0 && !availableYears.includes(filterYear) ? availableYears[0] : filterYear),
    [availableYears, filterYear],
  );

  /* ── Filtered distributions (all cards / charts react to these) ── */
  const filtered = useMemo(() => {
    return distributions.filter(d => {
      if (!d.distribution_date) return false;
      if (new Date(d.distribution_date).getFullYear() !== effectiveFilterYear) return false;
      if (filterType && d.distribution_type !== filterType) return false;
      if (filterAsset && resolveId(d.asset) !== String(filterAsset)) return false;
      if (filterEntity) {
        const hasEntity = (d.allocations || []).some(a => resolveId(a.entity) === String(filterEntity));
        if (!hasEntity) return false;
      }
      return true;
    });
  }, [distributions, effectiveFilterYear, filterEntity, filterAsset, filterType]);

  /* ── KPI values ── */
  const totalAmount = useMemo(() => filtered.reduce((s, d) => s + parseFloat(d.total_amount || 0), 0), [filtered]);
  const avgAmount  = useMemo(() => (filtered.length ? totalAmount / filtered.length : 0), [filtered, totalAmount]);

  const filteredEntityCount = useMemo(() => {
    const ids = new Set();
    filtered.forEach(d => (d.allocations || []).forEach(a => ids.add(resolveId(a.entity))));
    return ids.size;
  }, [filtered]);

  const filteredAssetCount = useMemo(() => {
    const ids = new Set();
    filtered.forEach(d => ids.add(resolveId(d.asset)));
    return ids.size;
  }, [filtered]);

  /* ── Monthly bar chart ── */
  const monthNames = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const monthlyData = useMemo(() =>
    monthNames.map((month, i) => ({
      month,
      amount: filtered.filter(d => new Date(d.distribution_date).getMonth() === i).reduce((s, d) => s + parseFloat(d.total_amount || 0), 0),
    })), [filtered]);

  /* ── Pie chart by entity ── */
  const pieData = useMemo(() => {
    const map = {};
    filtered.forEach(dist => {
      (dist.allocations || []).forEach(alloc => {
        if (filterEntity && resolveId(alloc.entity) !== String(filterEntity)) return;
        const name = alloc.entity_name || alloc.entity || 'Unknown';
        map[name] = (map[name] || 0) + parseFloat(alloc.amount || 0);
      });
    });
    return Object.entries(map).map(([name, value]) => ({ name, value })).sort((a, b) => b.value - a.value).slice(0, 6);
  }, [filtered, filterEntity]);

  /* ── Top entity / asset from filtered data ── */
  const topEntity = useMemo(() => {
    const map = {};
    filtered.forEach(dist => (dist.allocations || []).forEach(a => {
      const name = a.entity_name || a.entity || 'Unknown';
      map[name] = (map[name] || 0) + parseFloat(a.amount || 0);
    }));
    const entries = Object.entries(map);
    if (!entries.length) return null;
    const [name, total] = entries.sort((a, b) => b[1] - a[1])[0];
    return { name, total };
  }, [filtered]);

  const topAsset = useMemo(() => {
    const map = {};
    filtered.forEach(dist => {
      const name = (typeof dist.asset === 'object' ? dist.asset?.name : null) || dist.asset_name || assets.find(a => String(a.id) === resolveId(dist.asset))?.name || resolveId(dist.asset);
      map[name] = (map[name] || 0) + parseFloat(dist.total_amount || 0);
    });
    const entries = Object.entries(map);
    if (!entries.length) return null;
    const [name, total] = entries.sort((a, b) => b[1] - a[1])[0];
    return { name, total };
  }, [filtered, assets]);

  /* ── Table columns ── */
  const recentColumns = [
    { header: 'Date', key: 'distribution_date', render: r => r.distribution_date ? format(parseISO(r.distribution_date), 'MMM dd, yyyy') : '-' },
    { header: 'Asset', key: 'asset_name', render: r => {
      return r.asset_name || (typeof r.asset === 'object' ? r.asset?.name : null) || assets.find(a => String(a.id) === resolveId(r.asset))?.name || '-';
    }},
    { header: 'Type', key: 'distribution_type', render: r => <span className="capitalize">{(r.distribution_type || '').replace(/_/g, ' ')}</span> },
    { header: 'Amount', key: 'total_amount', render: r => <span className="font-semibold text-emerald-600">{formatCurrency(r.total_amount)}</span> },
  ];

  const hasActiveFilter = filterEntity || filterAsset || filterType;

  const clearFilters = () => { setFilterEntity(''); setFilterAsset(''); setFilterType(''); };

  /* ── Shared dropdown class ── */
  const selectCls = 'w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white';

  if (loading) return <LoadingSpinner className="min-h-96" size="lg" />;

  if (error) return (
    <div className="flex flex-col items-center justify-center min-h-96 text-center p-6">
      <p className="text-red-600 text-lg font-medium mb-4">{error}</p>
      <button onClick={() => window.location.reload()} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
        Retry
      </button>
    </div>
  );

  return (
    <div className="space-y-6">
      {/* ══════════════ Filter Bar ══════════════ */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
        <div className="flex flex-wrap items-end gap-4">
          {/* Year */}
          <div className="flex-1 min-w-[120px]">
            <label className="block text-xs font-medium text-gray-500 mb-1">Year</label>
            <select className={selectCls} value={effectiveFilterYear} onChange={e => setFilterYear(parseInt(e.target.value))}>
              {availableYears.map(y => <option key={y} value={y}>{y}</option>)}
            </select>
          </div>
          {/* Entity */}
          <div className="flex-1 min-w-[160px]">
            <label className="block text-xs font-medium text-gray-500 mb-1">Entity</label>
            <select className={selectCls} value={filterEntity} onChange={e => setFilterEntity(e.target.value)}>
              <option value="">All Entities</option>
              {entities.map(en => <option key={en.id} value={en.id}>{en.name}</option>)}
            </select>
          </div>
          {/* Asset */}
          <div className="flex-1 min-w-[160px]">
            <label className="block text-xs font-medium text-gray-500 mb-1">Asset</label>
            <select className={selectCls} value={filterAsset} onChange={e => setFilterAsset(e.target.value)}>
              <option value="">All Assets</option>
              {assets.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
            </select>
          </div>
          {/* Distribution Type */}
          <div className="flex-1 min-w-[150px]">
            <label className="block text-xs font-medium text-gray-500 mb-1">Distribution Type</label>
            <select className={selectCls} value={filterType} onChange={e => setFilterType(e.target.value)}>
              <option value="">All Types</option>
              {DIST_TYPES.map(t => <option key={t} value={t} className="capitalize">{t.replace(/_/g, ' ')}</option>)}
            </select>
          </div>
          {/* Clear */}
          {hasActiveFilter && (
            <button onClick={clearFilters} className="px-3 py-2 text-sm text-gray-500 hover:text-red-600 border border-gray-300 rounded-lg hover:border-red-300 transition-colors whitespace-nowrap">
              ✕ Clear
            </button>
          )}
        </div>

        {/* Active filter pills */}
        {hasActiveFilter && (
          <div className="flex flex-wrap items-center gap-2 mt-3 pt-3 border-t border-gray-100">
            <span className="text-xs text-gray-400">Active:</span>
            {filterEntity && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 text-xs font-medium">
                Entity: {entities.find(e => String(e.id) === String(filterEntity))?.name || filterEntity}
                <button onClick={() => setFilterEntity('')} className="ml-0.5 hover:text-blue-900">×</button>
              </span>
            )}
            {filterAsset && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-purple-50 text-purple-700 text-xs font-medium">
                Asset: {assets.find(a => String(a.id) === String(filterAsset))?.name || filterAsset}
                <button onClick={() => setFilterAsset('')} className="ml-0.5 hover:text-purple-900">×</button>
              </span>
            )}
            {filterType && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 text-xs font-medium capitalize">
                Type: {filterType.replace(/_/g, ' ')}
                <button onClick={() => setFilterType('')} className="ml-0.5 hover:text-amber-900">×</button>
              </span>
            )}
            <span className="text-xs text-gray-400 ml-2">
              {filtered.length} distribution{filtered.length !== 1 ? 's' : ''} matched
            </span>
          </div>
        )}
      </div>

      {/* ══════════════ KPI Cards ══════════════ */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Entities', value: filterEntity ? 1 : filteredEntityCount, icon: '🏢' },
          { label: 'Assets', value: filterAsset ? 1 : filteredAssetCount, icon: '💼' },
          { label: `Distributions (${effectiveFilterYear})`, value: filtered.length, icon: '📊' },
          { label: `Total Distributed (${effectiveFilterYear})`, value: formatCurrency(totalAmount), icon: '💰' },
        ].map(({ label, value, icon }) => (
          <div key={label} className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
            <div className="flex items-center gap-3 mb-2">
              <span className="text-2xl">{icon}</span>
              <span className="text-sm font-medium text-gray-500">{label}</span>
            </div>
            <p className="text-2xl font-bold text-gray-900">{value}</p>
          </div>
        ))}
      </div>

      {/* ══════════════ Secondary KPI Cards ══════════════ */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {avgAmount > 0 && (
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
            <div className="flex items-center gap-3 mb-2"><span className="text-2xl">📐</span><span className="text-sm font-medium text-gray-500">Avg Distribution</span></div>
            <p className="text-xl font-bold text-gray-900">{formatCurrency(avgAmount)}</p>
          </div>
        )}
        {topEntity && (
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
            <div className="flex items-center gap-3 mb-2"><span className="text-2xl">🏆</span><span className="text-sm font-medium text-gray-500">Top Entity ({effectiveFilterYear})</span></div>
            <p className="text-lg font-bold text-gray-900">{topEntity.name}</p>
            <p className="text-sm text-emerald-600 font-semibold">{formatCurrency(topEntity.total)}</p>
          </div>
        )}
        {topAsset && (
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
            <div className="flex items-center gap-3 mb-2"><span className="text-2xl">⭐</span><span className="text-sm font-medium text-gray-500">Top Asset ({effectiveFilterYear})</span></div>
            <p className="text-lg font-bold text-gray-900">{topAsset.name}</p>
            <p className="text-sm text-emerald-600 font-semibold">{formatCurrency(topAsset.total)}</p>
          </div>
        )}
      </div>

      {/* ══════════════ Charts ══════════════ */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Monthly Distributions" subtitle={`${effectiveFilterYear}`}>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={monthlyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="month" tick={{ fontSize: 12 }} />
              <YAxis tickFormatter={v => `$${(v/1000).toFixed(0)}k`} tick={{ fontSize: 12 }} />
              <Tooltip formatter={v => formatCurrency(v)} />
              <Bar dataKey="amount" fill="#3B82F6" radius={[4,4,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card title="Distribution by Entity" subtitle={filterEntity ? entities.find(e => String(e.id) === String(filterEntity))?.name : 'All entities'}>
          {pieData.length === 0 ? (
            <div className="flex items-center justify-center h-60 text-gray-400">No allocation data available</div>
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label={({ name, percent }) => `${name} (${(percent*100).toFixed(0)}%)`} labelLine={false}>
                  {pieData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip formatter={v => formatCurrency(v)} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          )}
        </Card>
      </div>

      {/* ══════════════ Recent Distributions ══════════════ */}
      <Card title="Recent Distributions" subtitle={`Last ${Math.min(filtered.length, 10)} of ${filtered.length} matched`}>
        <Table columns={recentColumns} data={filtered.slice(0, 10)} loading={false} emptyMessage="No distributions match the selected filters." />
      </Card>
    </div>
  );
}
