import React, { useState, useEffect } from 'react';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import Modal from '../components/ui/Modal';
import Table from '../components/ui/Table';
import Badge from '../components/ui/Badge';
import { PlusIcon, PencilIcon, TrashIcon } from '@heroicons/react/24/outline';
import { getDistributions, createDistribution, updateDistribution, deleteDistribution } from '../api/distributions';
import { getAssets } from '../api/assets';
import { getOwnerships } from '../api/ownerships';
import { getEntities } from '../api/entities';
import { format, parseISO } from 'date-fns';

const distTypes = ['dividend', 'interest', 'capital_gain', 'return_of_capital', 'other'];
const typeColors = { dividend: 'green', interest: 'blue', capital_gain: 'purple', return_of_capital: 'yellow', other: 'gray' };
const formatCurrency = (v) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(v || 0);

const emptyForm = { asset: '', date: '', total_amount: '', distribution_type: 'dividend', notes: '', allocations: [] };

export default function Distributions() {
  const [distributions, setDistributions] = useState([]);
  const [assets, setAssets] = useState([]);
  const [ownerships, setOwnerships] = useState([]);
  const [entities, setEntities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const load = () => {
    setLoading(true);
    Promise.all([getDistributions(), getAssets(), getOwnerships(), getEntities()])
      .then(([d, a, o, e]) => {
        setDistributions(d.data.results || d.data || []);
        setAssets(a.data.results || a.data || []);
        setOwnerships(o.data.results || o.data || []);
        setEntities(e.data.results || e.data || []);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const openAdd = () => { setForm(emptyForm); setError(''); setModalOpen(true); };

  const handleAssetChange = (assetId) => {
    const assetOwnerships = ownerships.filter(o => {
      const oAssetId = o.asset?.id || o.asset;
      return oAssetId == assetId;
    });
    const allocations = assetOwnerships.map(o => {
      const entityId = o.entity?.id || o.entity;
      const entity = entities.find(e => e.id == entityId);
      return {
        entity: entityId,
        entity_name: entity?.name || entityId,
        percentage: parseFloat(o.percentage || 0),
        amount: '',
      };
    });
    setForm(f => ({ ...f, asset: assetId, allocations }));
  };

  const handleTotalAmountChange = (total) => {
    const totalNum = parseFloat(total) || 0;
    const allocations = form.allocations.map(a => ({
      ...a,
      amount: totalNum > 0 ? ((a.percentage / 100) * totalNum).toFixed(2) : '',
    }));
    setForm(f => ({ ...f, total_amount: total, allocations }));
  };

  const handleSave = async (ev) => {
    ev.preventDefault();
    setSaving(true);
    setError('');
    try {
      const payload = {
        asset: form.asset,
        date: form.date,
        total_amount: form.total_amount,
        distribution_type: form.distribution_type,
        notes: form.notes,
        allocations: form.allocations.map(a => ({ entity: a.entity, amount: a.amount, percentage: a.percentage })),
      };
      await createDistribution(payload);
      setModalOpen(false);
      load();
    } catch (e) {
      setError(e.response?.data ? JSON.stringify(e.response.data) : 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this distribution?')) return;
    try { await deleteDistribution(id); load(); } catch { alert('Delete failed'); }
  };

  const getAssetName = (a) => {
    if (typeof a === 'object' && a?.name) return a.name;
    const found = assets.find(x => x.id == a);
    return found?.name || a || '-';
  };

  const columns = [
    { header: 'Date', key: 'date', render: r => r.date ? format(parseISO(r.date), 'MMM dd, yyyy') : '-' },
    { header: 'Asset', key: 'asset', render: r => <span className="font-medium text-gray-900">{getAssetName(r.asset)}</span> },
    { header: 'Type', key: 'distribution_type', render: r => <Badge color={typeColors[r.distribution_type] || 'gray'}>{(r.distribution_type || '').replace('_', ' ')}</Badge> },
    { header: 'Total Amount', key: 'total_amount', render: r => <span className="font-semibold text-emerald-600">{formatCurrency(r.total_amount)}</span> },
    { header: 'Notes', key: 'notes', render: r => <span className="text-gray-500 truncate max-w-xs block">{r.notes || '-'}</span> },
    {
      header: 'Actions', key: 'actions', render: r => (
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={() => handleDelete(r.id)} className="text-red-500 hover:text-red-700"><TrashIcon className="h-4 w-4" /></Button>
        </div>
      )
    },
  ];

  return (
    <>
      <Card title="Distributions" subtitle={`${distributions.length} total`} action={<Button onClick={openAdd}><PlusIcon className="h-4 w-4" /> Add Distribution</Button>}>
        <Table columns={columns} data={distributions} loading={loading} emptyMessage="No distributions yet." />
      </Card>

      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title="Add Distribution" size="lg">
        <form onSubmit={handleSave} className="space-y-4">
          {error && <div className="text-red-600 text-sm bg-red-50 p-3 rounded-lg">{error}</div>}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Asset *</label>
              <select required className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" value={form.asset} onChange={e => handleAssetChange(e.target.value)}>
                <option value="">Select asset...</option>
                {assets.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Date *</label>
              <input required type="date" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" value={form.date} onChange={e => setForm(f => ({...f, date: e.target.value}))} />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Total Amount *</label>
              <input required type="number" min="0.01" step="0.01" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" value={form.total_amount} onChange={e => handleTotalAmountChange(e.target.value)} />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Type *</label>
              <select required className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" value={form.distribution_type} onChange={e => setForm(f => ({...f, distribution_type: e.target.value}))}>
                {distTypes.map(t => <option key={t} value={t}>{t.replace('_', ' ')}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
            <textarea rows={2} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" value={form.notes} onChange={e => setForm(f => ({...f, notes: e.target.value}))} />
          </div>

          {form.allocations.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Allocations</label>
              <div className="border border-gray-200 rounded-lg overflow-hidden">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Entity</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Ownership %</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Amount</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {form.allocations.map((a, i) => (
                      <tr key={i}>
                        <td className="px-4 py-2 text-sm text-gray-700">{a.entity_name}</td>
                        <td className="px-4 py-2 text-sm text-gray-500">{a.percentage.toFixed(2)}%</td>
                        <td className="px-4 py-2 text-sm">
                          <input type="number" min="0" step="0.01" className="w-32 border border-gray-300 rounded px-2 py-1 text-sm" value={a.amount}
                            onChange={e => setForm(f => ({ ...f, allocations: f.allocations.map((x, j) => j === i ? {...x, amount: e.target.value} : x) }))} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setModalOpen(false)}>Cancel</Button>
            <Button type="submit" disabled={saving}>{saving ? 'Saving...' : 'Create'}</Button>
          </div>
        </form>
      </Modal>
    </>
  );
}
