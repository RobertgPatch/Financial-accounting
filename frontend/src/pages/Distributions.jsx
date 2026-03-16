import React, { useState, useEffect } from 'react';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import Modal from '../components/ui/Modal';
import Table from '../components/ui/Table';
import Badge from '../components/ui/Badge';
import { PlusIcon, TrashIcon, ArrowPathIcon } from '@heroicons/react/24/outline';
import { getDistributions, createDistribution, deleteDistribution, autoAllocateDistribution } from '../api/distributions';
import { getAssets } from '../api/assets';
import { getOwnerships } from '../api/ownerships';
import { getEntities } from '../api/entities';
import { toArray } from '../api/utils';
import { format, parseISO } from 'date-fns';

const distTypes = ['regular', 'special', 'return_of_capital', 'liquidating'];
const typeColors = { regular: 'green', special: 'blue', return_of_capital: 'yellow', liquidating: 'red' };
const formatCurrency = (v) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(v || 0);

const emptyForm = { asset: '', distribution_date: '', total_amount: '', distribution_type: 'regular', notes: '', allocations: [] };

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

  // Available entities for the selected asset (from ownerships)
  const [availableEntities, setAvailableEntities] = useState([]);
  // Set of selected entity IDs (user opts in via checkboxes)
  const [selectedEntityIds, setSelectedEntityIds] = useState(new Set());

  const load = () => {
    setLoading(true);
    Promise.all([getDistributions(), getAssets(), getOwnerships(), getEntities()])
      .then(([d, a, o, e]) => {
        setDistributions(toArray(d));
        setAssets(toArray(a));
        setOwnerships(toArray(o));
        setEntities(toArray(e));
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const openAdd = () => {
    setForm(emptyForm);
    setAvailableEntities([]);
    setSelectedEntityIds(new Set());
    setError('');
    setModalOpen(true);
  };

  // Build the list of available entities when asset changes
  const handleAssetChange = (assetId) => {
    const assetOwnerships = ownerships.filter(o => {
      const oAssetId = o.asset?.id ?? o.asset;
      return String(oAssetId) === String(assetId);
    });
    const available = assetOwnerships.map(o => {
      const entityId = o.entity?.id ?? o.entity;
      const entity = entities.find(e => String(e.id) === String(entityId));
      return {
        entity: entityId,
        entity_name: entity?.name || entityId,
        percentage: parseFloat(o.percentage || 0),
      };
    });
    setAvailableEntities(available);
    setSelectedEntityIds(new Set()); // nothing selected by default
    setForm(f => ({ ...f, asset: assetId, allocations: [] }));
  };

  // Toggle entity selection
  const handleEntityToggle = (entityId) => {
    setSelectedEntityIds(prev => {
      const next = new Set(prev);
      if (next.has(entityId)) {
        next.delete(entityId);
      } else {
        next.add(entityId);
      }
      return next;
    });
  };

  // Rebuild allocations whenever selection or total changes
  useEffect(() => {
    if (availableEntities.length === 0) return;
    const selected = availableEntities.filter(a => selectedEntityIds.has(a.entity));
    const totalNum = parseFloat(form.total_amount) || 0;
    const totalPct = selected.reduce((s, a) => s + a.percentage, 0);
    const allocations = selected.map(a => ({
      entity: a.entity,
      entity_name: a.entity_name,
      percentage: a.percentage,
      amount: totalNum > 0 && totalPct > 0
        ? ((a.percentage / totalPct) * totalNum).toFixed(2)
        : '',
    }));
    setForm(f => ({ ...f, allocations }));
   // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedEntityIds, form.total_amount, availableEntities]);

  const handleSave = async (ev) => {
    ev.preventDefault();
    setSaving(true);
    setError('');
    try {
      const payload = {
        asset: form.asset,
        distribution_date: form.distribution_date,
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

  const handleAutoAllocate = async (id) => {
    if (!window.confirm('Auto-allocate this distribution based on current ownership percentages? This will replace any existing allocations.')) return;
    try {
      await autoAllocateDistribution(id);
      load();
    } catch (e) {
      alert(e.response?.data?.error || 'Auto-allocate failed. Make sure ownership records exist for this asset.');
    }
  };

  const getAssetName = (a) => {
    if (typeof a === 'object' && a?.name) return a.name;
    const found = assets.find(x => String(x.id) === String(a));
    return found?.name || a || '-';
  };

  const columns = [
    { header: 'Date', key: 'distribution_date', render: r => r.distribution_date ? format(parseISO(r.distribution_date), 'MMM dd, yyyy') : '-' },
    { header: 'Asset', key: 'asset', render: r => <span className="font-medium text-gray-900">{getAssetName(r.asset)}</span> },
    { header: 'Type', key: 'distribution_type', render: r => <Badge color={typeColors[r.distribution_type] || 'gray'}>{(r.distribution_type || '').replace('_', ' ')}</Badge> },
    { header: 'Total Amount', key: 'total_amount', render: r => <span className="font-semibold text-emerald-600">{formatCurrency(r.total_amount)}</span> },
    { header: 'Notes', key: 'notes', render: r => <span className="text-gray-500 truncate max-w-xs block">{r.notes || '-'}</span> },
    {
      header: 'Actions', key: 'actions', render: r => (
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={() => handleAutoAllocate(r.id)} className="text-blue-500 hover:text-blue-700" title="Auto-allocate based on ownership">
            <ArrowPathIcon className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="sm" onClick={() => handleDelete(r.id)} className="text-red-500 hover:text-red-700">
            <TrashIcon className="h-4 w-4" />
          </Button>
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
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Asset *</label>
              <select required className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" value={form.asset} onChange={e => handleAssetChange(e.target.value)}>
                <option value="">Select asset...</option>
                {assets.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Date *</label>
              <input required type="date" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" value={form.distribution_date} onChange={e => setForm(f => ({...f, distribution_date: e.target.value}))} />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Total Amount *</label>
              <input required type="number" min="0.01" step="0.01" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" value={form.total_amount} onChange={e => setForm(f => ({...f, total_amount: e.target.value}))} />
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

          {availableEntities.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Allocate to Entities</label>
              <p className="text-xs text-gray-500 mb-2">Select which entities should receive this distribution.</p>
              <div className="border border-gray-200 rounded-lg overflow-hidden">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 w-10"></th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Entity</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Ownership %</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Amount</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {availableEntities.map((ae) => {
                      const checked = selectedEntityIds.has(ae.entity);
                      const alloc = form.allocations.find(a => a.entity === ae.entity);
                      return (
                        <tr key={ae.entity} className={checked ? 'bg-blue-50/40' : ''}>
                          <td className="px-4 py-2">
                            <input
                              type="checkbox"
                              checked={checked}
                              onChange={() => handleEntityToggle(ae.entity)}
                              className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                            />
                          </td>
                          <td className="px-4 py-2 text-sm text-gray-700">{ae.entity_name}</td>
                          <td className="px-4 py-2 text-sm text-gray-500">{ae.percentage.toFixed(2)}%</td>
                          <td className="px-4 py-2 text-sm">
                            {checked ? (
                              <input
                                type="number" min="0" step="0.01"
                                className="w-32 border border-gray-300 rounded px-2 py-1 text-sm"
                                value={alloc?.amount || ''}
                                onChange={e => setForm(f => ({
                                  ...f,
                                  allocations: f.allocations.map(x =>
                                    x.entity === ae.entity ? { ...x, amount: e.target.value } : x
                                  ),
                                }))}
                              />
                            ) : (
                              <span className="text-gray-400 text-sm">—</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
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
