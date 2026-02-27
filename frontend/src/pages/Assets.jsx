import React, { useState, useEffect } from 'react';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import Modal from '../components/ui/Modal';
import Table from '../components/ui/Table';
import Badge from '../components/ui/Badge';
import { PlusIcon, PencilIcon, TrashIcon } from '@heroicons/react/24/outline';
import { getAssets, createAsset, updateAsset, deleteAsset } from '../api/assets';
import { toArray } from '../api/utils';
import { format, parseISO } from 'date-fns';

const typeColors = { property: 'green', stock: 'blue', fund: 'purple', bond: 'yellow', other: 'gray' };
const assetTypes = ['property', 'stock', 'fund', 'bond', 'other'];

const emptyForm = { name: '', asset_type: 'property', description: '', address: '', ticker_symbol: '' };

export default function Assets() {
  const [assets, setAssets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const load = () => {
    setLoading(true);
    getAssets().then(r => setAssets(toArray(r))).catch(() => setAssets([])).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const openAdd = () => { setEditing(null); setForm(emptyForm); setError(''); setModalOpen(true); };
  const openEdit = (a) => { setEditing(a); setForm({ name: a.name, asset_type: a.asset_type, description: a.description || '', address: a.address || '', ticker_symbol: a.ticker_symbol || '' }); setError(''); setModalOpen(true); };

  const handleSave = async (ev) => {
    ev.preventDefault();
    setSaving(true);
    setError('');
    try {
      if (editing) await updateAsset(editing.id, form);
      else await createAsset(form);
      setModalOpen(false);
      load();
    } catch (e) {
      setError(e.response?.data ? JSON.stringify(e.response.data) : 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this asset?')) return;
    try { await deleteAsset(id); load(); } catch { alert('Delete failed'); }
  };

  const columns = [
    { header: 'Name', key: 'name', render: r => <span className="font-medium text-gray-900">{r.name}</span> },
    { header: 'Type', key: 'asset_type', render: r => <Badge color={typeColors[r.asset_type] || 'gray'}>{r.asset_type}</Badge> },
    { header: 'Description', key: 'description', render: r => <span className="text-gray-500 truncate max-w-xs block">{r.description || '-'}</span> },
    { header: 'Created', key: 'created_at', render: r => r.created_at ? format(parseISO(r.created_at), 'MMM dd, yyyy') : '-' },
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
      <Card title="Assets" subtitle={`${assets.length} total`} action={<Button onClick={openAdd}><PlusIcon className="h-4 w-4" /> Add Asset</Button>}>
        <Table columns={columns} data={assets} loading={loading} emptyMessage="No assets yet. Add your first asset." />
      </Card>

      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title={editing ? 'Edit Asset' : 'Add Asset'}>
        <form onSubmit={handleSave} className="space-y-4">
          {error && <div className="text-red-600 text-sm bg-red-50 p-3 rounded-lg">{error}</div>}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
            <input required className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" value={form.name} onChange={e => setForm(f => ({...f, name: e.target.value}))} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Type *</label>
            <select required className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" value={form.asset_type} onChange={e => setForm(f => ({...f, asset_type: e.target.value}))}>
              {assetTypes.map(t => <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea rows={2} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" value={form.description} onChange={e => setForm(f => ({...f, description: e.target.value}))} />
          </div>
          {form.asset_type === 'property' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Address</label>
              <input className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" value={form.address} onChange={e => setForm(f => ({...f, address: e.target.value}))} />
            </div>
          )}
          {form.asset_type === 'stock' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Ticker Symbol</label>
              <input className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" value={form.ticker_symbol} onChange={e => setForm(f => ({...f, ticker_symbol: e.target.value.toUpperCase()}))} />
            </div>
          )}
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setModalOpen(false)}>Cancel</Button>
            <Button type="submit" disabled={saving}>{saving ? 'Saving...' : editing ? 'Update' : 'Create'}</Button>
          </div>
        </form>
      </Modal>
    </>
  );
}
