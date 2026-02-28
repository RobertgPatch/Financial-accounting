import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import Modal from '../components/ui/Modal';
import Table from '../components/ui/Table';
import Badge from '../components/ui/Badge';
import TagInput from '../components/ui/TagInput';
import { PlusIcon, PencilIcon, TrashIcon, FunnelIcon } from '@heroicons/react/24/outline';
import { getAssets, createAsset, updateAsset, deleteAsset } from '../api/assets';
import { getTags, setAssetTags } from '../api/tags';
import { toArray } from '../api/utils';
import { format, parseISO } from 'date-fns';

const typeColors = {
  real_estate: 'green', public_equity: 'blue', private_equity: 'indigo',
  fixed_income: 'yellow', cash: 'gray', hedge_fund: 'purple',
  crypto: 'orange', collectible: 'pink', other: 'gray',
};
const assetTypes = [
  { value: 'real_estate', label: 'Real Estate' },
  { value: 'public_equity', label: 'Public Equity' },
  { value: 'private_equity', label: 'Private Equity' },
  { value: 'fixed_income', label: 'Fixed Income' },
  { value: 'cash', label: 'Cash & Equivalents' },
  { value: 'hedge_fund', label: 'Hedge Fund' },
  { value: 'crypto', label: 'Cryptocurrency' },
  { value: 'collectible', label: 'Collectible' },
  { value: 'other', label: 'Other' },
];

const emptyForm = { name: '', asset_type: 'real_estate', description: '', address: '', ticker_symbol: '' };

export default function Assets() {
  const [assets, setAssets] = useState([]);
  const [allTags, setAllTags] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const [formTags, setFormTags] = useState([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  // Filters
  const [filterType, setFilterType] = useState('');
  const [filterTag, setFilterTag] = useState('');
  const [showFilters, setShowFilters] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const [assetsRes, tagsRes] = await Promise.all([getAssets(), getTags()]);
      setAssets(toArray(assetsRes));
      setAllTags(toArray(tagsRes));
    } catch {
      setAssets([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const filteredAssets = assets.filter((a) => {
    if (filterType && a.asset_type !== filterType) return false;
    if (filterTag) {
      const hasThat = a.tags?.some((t) => t.slug === filterTag);
      if (!hasThat) return false;
    }
    return true;
  });

  const openAdd = () => { setEditing(null); setForm(emptyForm); setFormTags([]); setError(''); setModalOpen(true); };
  const openEdit = (a) => { setEditing(a); setForm({ name: a.name, asset_type: a.asset_type, description: a.description || '', address: a.address || '', ticker_symbol: a.ticker_symbol || '' }); setFormTags(a.tags || []); setError(''); setModalOpen(true); };

  const handleSave = async (ev) => {
    ev.preventDefault();
    setSaving(true);
    setError('');
    try {
      let saved;
      if (editing) {
        saved = await updateAsset(editing.id, form);
        saved = saved?.data || saved;
        await setAssetTags(editing.id, formTags.map((t) => t.id));
      } else {
        saved = await createAsset(form);
        saved = saved?.data || saved;
        if (formTags.length > 0 && saved?.id) {
          await setAssetTags(saved.id, formTags.map((t) => t.id));
        }
      }
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
    { header: 'Name', key: 'name', render: r => <Link to={`/assets/${r.id}`} className="font-medium text-blue-600 hover:text-blue-800 hover:underline">{r.name}</Link> },
    { header: 'Type', key: 'asset_type', render: r => <Badge color={typeColors[r.asset_type] || 'gray'}>{r.asset_type_display || r.asset_type}</Badge> },
    { header: 'Tags', key: 'tags', render: r => (
      <div className="flex flex-wrap gap-1">
        {r.tags?.map((t) => (
          <span key={t.id} className="inline-flex items-center px-1.5 py-0.5 rounded-full text-xs font-medium text-white" style={{ backgroundColor: t.color || '#6B7280' }}>{t.name}</span>
        ))}
      </div>
    )},
    { header: 'Current FMV', key: 'latest_fmv', render: r => r.latest_fmv ? <span className="font-medium">${parseFloat(r.latest_fmv).toLocaleString('en-US', { minimumFractionDigits: 2 })}</span> : <span className="text-gray-400">—</span> },
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
      <Card title="Assets" subtitle={`${filteredAssets.length} of ${assets.length}`} action={
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => setShowFilters((f) => !f)}><FunnelIcon className="h-4 w-4" /> Filter</Button>
          <Button onClick={openAdd}><PlusIcon className="h-4 w-4" /> Add Asset</Button>
        </div>
      }>
        {showFilters && (
          <div className="flex flex-col sm:flex-row gap-3 mb-4 p-3 bg-gray-50 rounded-lg">
            <div className="flex-1">
              <label className="block text-xs font-medium text-gray-500 mb-1">Asset Type</label>
              <select className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm" value={filterType} onChange={(e) => setFilterType(e.target.value)}>
                <option value="">All Types</option>
                {assetTypes.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>
            <div className="flex-1">
              <label className="block text-xs font-medium text-gray-500 mb-1">Tag</label>
              <select className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm" value={filterTag} onChange={(e) => setFilterTag(e.target.value)}>
                <option value="">All Tags</option>
                {allTags.map((t) => <option key={t.slug} value={t.slug}>{t.name}</option>)}
              </select>
            </div>
            {(filterType || filterTag) && (
              <div className="flex items-end">
                <Button variant="ghost" size="sm" onClick={() => { setFilterType(''); setFilterTag(''); }}>Clear</Button>
              </div>
            )}
          </div>
        )}
        <Table columns={columns} data={filteredAssets} loading={loading} emptyMessage="No assets yet. Add your first asset." />
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
              {assetTypes.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea rows={2} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" value={form.description} onChange={e => setForm(f => ({...f, description: e.target.value}))} />
          </div>
          {form.asset_type === 'real_estate' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Address</label>
              <input className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" value={form.address} onChange={e => setForm(f => ({...f, address: e.target.value}))} />
            </div>
          )}
          {form.asset_type === 'public_equity' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Ticker Symbol</label>
              <input className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" value={form.ticker_symbol} onChange={e => setForm(f => ({...f, ticker_symbol: e.target.value.toUpperCase()}))} />
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Tags</label>
            <TagInput value={formTags} suggestions={allTags} onChange={setFormTags} placeholder="Add tags..." />
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
