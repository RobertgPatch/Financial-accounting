import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import Modal from '../components/ui/Modal';
import Table from '../components/ui/Table';
import Badge from '../components/ui/Badge';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import {
  ArrowLeftIcon,
  PlusIcon,
  PencilIcon,
  TrashIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
} from '@heroicons/react/24/outline';
import { getAsset } from '../api/assets';
import {
  getAssetFmvHistory,
  createSnapshot,
  updateSnapshot,
  deleteSnapshot,
} from '../api/fmv';
import { getAssetPerformance } from '../api/performance';
import { toArray } from '../api/utils';
import { format, parseISO } from 'date-fns';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from 'recharts';

const typeColors = {
  real_estate: 'green', public_equity: 'blue', private_equity: 'indigo',
  fixed_income: 'yellow', cash: 'gray', hedge_fund: 'purple',
  crypto: 'orange', collectible: 'pink', other: 'gray',
};

const sourceLabels = { manual: 'Manual', plaid: 'Plaid' };

const emptyFmvForm = { snapshot_date: '', value: '', source: 'manual', notes: '' };

export default function AssetDetail() {
  const { id } = useParams();
  const [asset, setAsset] = useState(null);
  const [fmvHistory, setFmvHistory] = useState(null);
  const [performance, setPerformance] = useState(null);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingSnap, setEditingSnap] = useState(null);
  const [form, setForm] = useState(emptyFmvForm);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [assetRes, historyRes] = await Promise.all([
        getAsset(id),
        getAssetFmvHistory(id),
      ]);
      setAsset(assetRes?.data || assetRes);
      setFmvHistory(historyRes);
      // Load performance in background — don't block UI
      getAssetPerformance(id)
        .then((res) => setPerformance(res?.data || res))
        .catch(() => setPerformance(null));
    } catch (e) {
      console.error('Failed to load asset data', e);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { loadData(); }, [loadData]);

  const openAddFmv = () => {
    setEditingSnap(null);
    setForm({ ...emptyFmvForm, snapshot_date: new Date().toISOString().split('T')[0] });
    setError('');
    setModalOpen(true);
  };

  const openEditFmv = (snap) => {
    setEditingSnap(snap);
    setForm({
      snapshot_date: snap.snapshot_date,
      value: snap.value,
      source: snap.source || 'manual',
      notes: snap.notes || '',
    });
    setError('');
    setModalOpen(true);
  };

  const handleSaveFmv = async (ev) => {
    ev.preventDefault();
    setSaving(true);
    setError('');
    try {
      const payload = { ...form, asset: Number(id) };
      if (editingSnap?.id) {
        await updateSnapshot(editingSnap.id, payload);
      } else {
        await createSnapshot(payload);
      }
      setModalOpen(false);
      loadData();
    } catch (e) {
      const errData = e.response?.data;
      setError(errData ? (typeof errData === 'string' ? errData : JSON.stringify(errData)) : 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteFmv = async (snapId) => {
    if (!window.confirm('Delete this FMV snapshot?')) return;
    try {
      await deleteSnapshot(snapId);
      loadData();
    } catch {
      alert('Delete failed');
    }
  };

  if (loading) return <LoadingSpinner />;
  if (!asset) return <div className="text-center py-12 text-gray-500">Asset not found.</div>;

  const snapshots = fmvHistory?.snapshots || [];
  const chartData = [...snapshots].reverse().map((s) => ({
    date: s.snapshot_date,
    value: parseFloat(s.value),
  }));

  const fmvColumns = [
    {
      header: 'Date', key: 'snapshot_date',
      render: (r) => format(parseISO(r.snapshot_date), 'MMM dd, yyyy'),
    },
    {
      header: 'Value', key: 'value',
      render: (r) => (
        <span className="font-medium">
          ${parseFloat(r.value).toLocaleString('en-US', { minimumFractionDigits: 2 })}
        </span>
      ),
    },
    {
      header: 'Change', key: 'change_amount',
      render: (r) => {
        if (r.change_amount === null) return <span className="text-gray-400">—</span>;
        const amt = parseFloat(r.change_amount);
        const pct = r.change_pct ? parseFloat(r.change_pct) : 0;
        const isPositive = amt >= 0;
        return (
          <span className={`inline-flex items-center gap-1 ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
            {isPositive ? <ArrowTrendingUpIcon className="h-4 w-4" /> : <ArrowTrendingDownIcon className="h-4 w-4" />}
            ${Math.abs(amt).toLocaleString('en-US', { minimumFractionDigits: 2 })} ({pct > 0 ? '+' : ''}{pct.toFixed(2)}%)
          </span>
        );
      },
    },
    {
      header: 'Source', key: 'source',
      render: (r) => <Badge color={r.source === 'plaid' ? 'blue' : 'gray'}>{sourceLabels[r.source] || r.source}</Badge>,
    },
    {
      header: 'Actions', key: 'actions',
      render: (r) => (
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={() => openEditFmv(r)}>
            <PencilIcon className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="sm" onClick={() => handleDeleteFmv(r.id)} className="text-red-500 hover:text-red-700">
            <TrashIcon className="h-4 w-4" />
          </Button>
        </div>
      ),
    },
  ];

  // Need to look up snapshot ids — merge from the full list if we fetched via fmv-history
  // The fmv-history endpoint doesn't return ids, so let's fall back to re-fetching
  // Actually, the fmv_history only returns computed fields. For edit/delete we need snapshot IDs.
  // Let's augment snapshots with ids by loading from the FMV snapshots API.

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-4">
        <Link to="/assets" className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700">
          <ArrowLeftIcon className="h-4 w-4" /> Back to Assets
        </Link>
      </div>

      <Card>
        <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4 p-1">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">{asset.name}</h2>
            <div className="flex flex-wrap gap-2 mt-2">
              <Badge color={typeColors[asset.asset_type] || 'gray'}>
                {asset.asset_type_display || asset.asset_type}
              </Badge>
              {asset.tags?.map((tag) => (
                <span key={tag.id} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium text-white" style={{ backgroundColor: tag.color || '#6B7280' }}>
                  {tag.name}
                </span>
              ))}
            </div>
            {asset.description && <p className="text-sm text-gray-500 mt-2">{asset.description}</p>}
            {asset.ticker_symbol && <p className="text-sm text-gray-500">Ticker: <span className="font-medium">{asset.ticker_symbol}</span></p>}
            {asset.address && <p className="text-sm text-gray-500">Address: {asset.address}</p>}
          </div>
          <div className="text-right">
            {fmvHistory?.current_fmv ? (
              <>
                <div className="text-2xl font-bold text-gray-900">
                  ${parseFloat(fmvHistory.current_fmv).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                </div>
                <div className="text-sm text-gray-500">
                  as of {fmvHistory.current_fmv_date ? format(parseISO(fmvHistory.current_fmv_date), 'MMM dd, yyyy') : 'N/A'}
                </div>
              </>
            ) : (
              <div className="text-sm text-gray-400">No FMV recorded</div>
            )}
          </div>
        </div>
      </Card>

      {/* FMV Chart */}
      {chartData.length > 1 && (
        <Card title="FMV History">
          <div className="h-64 sm:h-72 md:h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 5, right: 20, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 12 }}
                  tickFormatter={(v) => {
                    try { return format(parseISO(v), 'MMM yy'); } catch { return v; }
                  }}
                />
                <YAxis
                  tick={{ fontSize: 12 }}
                  tickFormatter={(v) => `$${(v / 1000000).toFixed(1)}M`}
                />
                <Tooltip
                  formatter={(v) => [`$${v.toLocaleString('en-US', { minimumFractionDigits: 2 })}`, 'FMV']}
                  labelFormatter={(v) => {
                    try { return format(parseISO(v), 'MMM dd, yyyy'); } catch { return v; }
                  }}
                />
                <Line type="monotone" dataKey="value" stroke="#3B82F6" strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 6 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}

      {/* Performance Metrics */}
      <PerformanceMetrics performance={performance} />

      {/* FMV Snapshots Table */}
      <Card
        title="FMV Snapshots"
        subtitle={`${snapshots.length} records`}
        action={
          <Button onClick={openAddFmv}>
            <PlusIcon className="h-4 w-4" /> Record FMV
          </Button>
        }
      >
        <FmvTable snapshots={snapshots} fmvColumns={fmvColumns} assetId={id} onEdit={openEditFmv} onDelete={handleDeleteFmv} loadData={loadData} />
      </Card>

      {/* Add/Edit FMV Modal */}
      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title={editingSnap ? 'Edit FMV Snapshot' : 'Record FMV'}>
        <form onSubmit={handleSaveFmv} className="space-y-4">
          {error && <div className="text-red-600 text-sm bg-red-50 p-3 rounded-lg">{error}</div>}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Date *</label>
            <input
              type="date"
              required
              max={new Date().toISOString().split('T')[0]}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={form.snapshot_date}
              onChange={(e) => setForm((f) => ({ ...f, snapshot_date: e.target.value }))}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Fair Market Value *</label>
            <input
              type="number"
              required
              min="0"
              step="0.01"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={form.value}
              onChange={(e) => setForm((f) => ({ ...f, value: e.target.value }))}
              placeholder="0.00"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Source</label>
            <select
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={form.source}
              onChange={(e) => setForm((f) => ({ ...f, source: e.target.value }))}
            >
              <option value="manual">Manual</option>
              <option value="plaid">Plaid</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
            <textarea
              rows={2}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={form.notes}
              onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
            />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setModalOpen(false)}>Cancel</Button>
            <Button type="submit" disabled={saving}>{saving ? 'Saving...' : editingSnap ? 'Update' : 'Save'}</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}

/**
 * Sub-component: loads FMV snapshots (with IDs) for edit/delete actions.
 */
function FmvTable({ snapshots, assetId, onEdit, onDelete, loadData }) {
  const [snapsWithIds, setSnapsWithIds] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    import('../api/fmv').then(({ listSnapshots }) => {
      listSnapshots({ asset: assetId })
        .then((data) => {
          const arr = toArray(data);
          setSnapsWithIds(arr);
        })
        .catch(() => setSnapsWithIds([]))
        .finally(() => setLoading(false));
    });
  }, [assetId, snapshots]); // re-fetch when parent data changes

  const columns = [
    {
      header: 'Date', key: 'snapshot_date',
      render: (r) => format(parseISO(r.snapshot_date), 'MMM dd, yyyy'),
    },
    {
      header: 'Value', key: 'value',
      render: (r) => (
        <span className="font-medium">
          ${parseFloat(r.value).toLocaleString('en-US', { minimumFractionDigits: 2 })}
        </span>
      ),
    },
    {
      header: 'Source', key: 'source',
      render: (r) => (
        <Badge color={r.source === 'plaid' ? 'blue' : 'gray'}>
          {sourceLabels[r.source] || r.source}
        </Badge>
      ),
    },
    {
      header: 'Actions', key: 'actions',
      render: (r) => (
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={() => onEdit(r)}>
            <PencilIcon className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="sm" onClick={() => onDelete(r.id)} className="text-red-500 hover:text-red-700">
            <TrashIcon className="h-4 w-4" />
          </Button>
        </div>
      ),
    },
  ];

  return <Table columns={columns} data={snapsWithIds} loading={loading} emptyMessage="No FMV snapshots yet. Record the first one." />;
}

/**
 * Sub-component: performance metrics across standard periods.
 */
function PerformanceMetrics({ performance }) {
  if (!performance || !performance.metrics) return null;

  const periods = ['ytd', '1y', '3y', 'since_inception'];
  const hasData = periods.some((p) => performance.metrics[p]?.twr !== null && performance.metrics[p]?.twr !== undefined);
  if (!hasData) return null;

  const fmtPct = (v) => {
    if (v === null || v === undefined) return <span className="text-gray-400">—</span>;
    const num = parseFloat(v);
    const color = num >= 0 ? 'text-green-600' : 'text-red-600';
    return <span className={color}>{num >= 0 ? '+' : ''}{num.toFixed(2)}%</span>;
  };

  return (
    <Card title="Performance Returns">
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="text-left py-2 pr-4 font-medium text-gray-500">Metric</th>
              {periods.map((p) => (
                <th key={p} className="text-right py-2 px-3 font-medium text-gray-500">
                  {performance.metrics[p]?.label || p}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-gray-100">
              <td className="py-2 pr-4 font-medium text-gray-700">TWR</td>
              {periods.map((p) => (
                <td key={p} className="text-right py-2 px-3">{fmtPct(performance.metrics[p]?.twr)}</td>
              ))}
            </tr>
            <tr className="border-b border-gray-100">
              <td className="py-2 pr-4 font-medium text-gray-700">TWR (Ann.)</td>
              {periods.map((p) => (
                <td key={p} className="text-right py-2 px-3">{fmtPct(performance.metrics[p]?.annualized_twr)}</td>
              ))}
            </tr>
            <tr className="border-b border-gray-100">
              <td className="py-2 pr-4 font-medium text-gray-700">IRR</td>
              {periods.map((p) => (
                <td key={p} className="text-right py-2 px-3">{fmtPct(performance.metrics[p]?.irr)}</td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>
      {/* Data quality indicators */}
      {Object.entries(performance.metrics).some(([, m]) => m?.data_quality?.stale) && (
        <p className="text-xs text-amber-600 mt-3">
          ⚠ Some periods have stale data (&gt;90 days since last snapshot).
        </p>
      )}
    </Card>
  );
}
