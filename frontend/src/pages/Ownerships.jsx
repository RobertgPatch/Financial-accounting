import React, { useState, useEffect } from 'react';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import Modal from '../components/ui/Modal';
import Table from '../components/ui/Table';
import { PlusIcon, PencilIcon, TrashIcon } from '@heroicons/react/24/outline';
import { getOwnerships, createOwnership, updateOwnership, deleteOwnership } from '../api/ownerships';
import { getEntities } from '../api/entities';
import { getAssets } from '../api/assets';
import { format, parseISO } from 'date-fns';

const emptyForm = { entity: '', asset: '', percentage: '', effective_date: '', notes: '' };

export default function Ownerships() {
  const [ownerships, setOwnerships] = useState([]);
  const [entities, setEntities] = useState([]);
  const [assets, setAssets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const load = () => {
    setLoading(true);
    const toArray = (res) => { const d = res.data?.results || res.data; return Array.isArray(d) ? d : []; };
    Promise.all([getOwnerships(), getEntities(), getAssets()])
      .then(([o, e, a]) => {
        setOwnerships(toArray(o));
        setEntities(toArray(e));
        setAssets(toArray(a));
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const openAdd = () => { setEditing(null); setForm(emptyForm); setError(''); setModalOpen(true); };
  const openEdit = (o) => {
    setEditing(o);
    setForm({
      entity: o.entity?.id || o.entity || '',
      asset: o.asset?.id || o.asset || '',
      percentage: o.percentage,
      effective_date: o.effective_date || '',
      notes: o.notes || '',
    });
    setError('');
    setModalOpen(true);
  };

  const validateOwnership = () => {
    const assetId = form.asset;
    const pct = parseFloat(form.percentage);
    const existing = ownerships.filter(o => {
      const oAssetId = String(o.asset?.id ?? o.asset);
      if (oAssetId !== String(assetId)) return false;
      if (editing && String(o.id) === String(editing.id)) return false;
      return true;
    });
    const total = existing.reduce((s, o) => s + parseFloat(o.percentage || 0), 0);
    if (total + pct > 100) return `Total ownership for this asset would be ${(total + pct).toFixed(2)}% (max 100%)`;
    return null;
  };

  const handleSave = async (ev) => {
    ev.preventDefault();
    const validationError = validateOwnership();
    if (validationError) { setError(validationError); return; }
    setSaving(true);
    setError('');
    try {
      if (editing) await updateOwnership(editing.id, form);
      else await createOwnership(form);
      setModalOpen(false);
      load();
    } catch (e) {
      setError(e.response?.data ? JSON.stringify(e.response.data) : 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this ownership?')) return;
    try { await deleteOwnership(id); load(); } catch { alert('Delete failed'); }
  };

  const getName = (obj, list) => {
    if (typeof obj === 'object' && obj?.name) return obj.name;
    const found = list.find(i => String(i.id) === String(obj));
    return found?.name || obj || '-';
  };

  const columns = [
    { header: 'Entity', key: 'entity', render: r => <span className="font-medium text-gray-900">{getName(r.entity, entities)}</span> },
    { header: 'Asset', key: 'asset', render: r => getName(r.asset, assets) },
    { header: 'Ownership %', key: 'percentage', render: r => <span className="font-semibold text-blue-600">{parseFloat(r.percentage).toFixed(2)}%</span> },
    { header: 'Effective Date', key: 'effective_date', render: r => r.effective_date ? format(parseISO(r.effective_date), 'MMM dd, yyyy') : '-' },
    { header: 'Notes', key: 'notes', render: r => <span className="text-gray-500">{r.notes || '-'}</span> },
    {
      header: 'Actions', key: 'actions', render: r => (
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={() => openEdit(r)}><PencilIcon className="h-4 w-4" /></Button>
          <Button variant="ghost" size="sm" onClick={() => handleDelete(r.id)} className="text-red-500 hover:text-red-700"><TrashIcon className="h-4 w-4" /></Button>
        </div>
      )
    },
  ];

  return (
    <>
      <Card title="Ownerships" subtitle={`${ownerships.length} total`} action={<Button onClick={openAdd}><PlusIcon className="h-4 w-4" /> Add Ownership</Button>}>
        <Table columns={columns} data={ownerships} loading={loading} emptyMessage="No ownerships yet." />
      </Card>

      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title={editing ? 'Edit Ownership' : 'Add Ownership'}>
        <form onSubmit={handleSave} className="space-y-4">
          {error && <div className="text-red-600 text-sm bg-red-50 p-3 rounded-lg">{error}</div>}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Entity *</label>
            <select required className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" value={form.entity} onChange={e => setForm(f => ({...f, entity: e.target.value}))}>
              <option value="">Select entity...</option>
              {entities.map(e => <option key={e.id} value={e.id}>{e.name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Asset *</label>
            <select required className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" value={form.asset} onChange={e => setForm(f => ({...f, asset: e.target.value}))}>
              <option value="">Select asset...</option>
              {assets.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Percentage *</label>
            <input required type="number" min="0.01" max="100" step="0.01" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" value={form.percentage} onChange={e => setForm(f => ({...f, percentage: e.target.value}))} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Effective Date</label>
            <input type="date" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" value={form.effective_date} onChange={e => setForm(f => ({...f, effective_date: e.target.value}))} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
            <textarea rows={2} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" value={form.notes} onChange={e => setForm(f => ({...f, notes: e.target.value}))} />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setModalOpen(false)}>Cancel</Button>
            <Button type="submit" disabled={saving}>{saving ? 'Saving...' : editing ? 'Update' : 'Create'}</Button>
          </div>
        </form>
      </Modal>
    </>
  );
}
