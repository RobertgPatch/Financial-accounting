import React, { useState, useEffect } from 'react';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import Modal from '../components/ui/Modal';
import Table from '../components/ui/Table';
import Badge from '../components/ui/Badge';
import { PlusIcon, PencilIcon, TrashIcon } from '@heroicons/react/24/outline';
import { getEntities, createEntity, updateEntity, deleteEntity } from '../api/entities';
import { toArray } from '../api/utils';
import { format, parseISO } from 'date-fns';

const typeColors = { individual: 'blue', company: 'purple', LLC: 'green', trust: 'yellow', partnership: 'orange', other: 'gray' };
const entityTypes = ['individual', 'company', 'LLC', 'trust', 'partnership', 'other'];

const emptyForm = { name: '', entity_type: 'individual', description: '', email: '' };

export default function Entities() {
  const [entities, setEntities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const load = () => {
    setLoading(true);
    getEntities().then(r => setEntities(toArray(r))).catch(() => setEntities([])).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const openAdd = () => { setEditing(null); setForm(emptyForm); setError(''); setModalOpen(true); };
  const openEdit = (e) => { setEditing(e); setForm({ name: e.name, entity_type: e.entity_type, description: e.description || '', email: e.email || '' }); setError(''); setModalOpen(true); };

  const handleSave = async (ev) => {
    ev.preventDefault();
    setSaving(true);
    setError('');
    try {
      if (editing) await updateEntity(editing.id, form);
      else await createEntity(form);
      setModalOpen(false);
      load();
    } catch (e) {
      setError(e.response?.data ? JSON.stringify(e.response.data) : 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this entity?')) return;
    try { await deleteEntity(id); load(); } catch (e) { alert('Delete failed'); }
  };

  const columns = [
    { header: 'Name', key: 'name', render: r => <span className="font-medium text-gray-900">{r.name}</span> },
    { header: 'Type', key: 'entity_type', render: r => <Badge color={typeColors[r.entity_type] || 'gray'}>{r.entity_type}</Badge> },
    { header: 'Email', key: 'email', render: r => r.email || '-' },
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
      <Card title="Entities" subtitle={`${entities.length} total`} action={<Button onClick={openAdd}><PlusIcon className="h-4 w-4" /> Add Entity</Button>}>
        <Table columns={columns} data={entities} loading={loading} emptyMessage="No entities yet. Add your first entity." />
      </Card>

      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title={editing ? 'Edit Entity' : 'Add Entity'}>
        <form onSubmit={handleSave} className="space-y-4">
          {error && <div className="text-red-600 text-sm bg-red-50 p-3 rounded-lg">{error}</div>}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
            <input required className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" value={form.name} onChange={e => setForm(f => ({...f, name: e.target.value}))} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Type *</label>
            <select required className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" value={form.entity_type} onChange={e => setForm(f => ({...f, entity_type: e.target.value}))}>
              {entityTypes.map(t => <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input type="email" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" value={form.email} onChange={e => setForm(f => ({...f, email: e.target.value}))} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea rows={3} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" value={form.description} onChange={e => setForm(f => ({...f, description: e.target.value}))} />
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
