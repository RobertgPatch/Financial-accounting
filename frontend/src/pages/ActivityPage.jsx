import React, { useState, useEffect, useCallback } from 'react';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import Modal from '../components/ui/Modal';
import { PlusIcon, TrashIcon, PencilIcon, ArrowDownTrayIcon } from '@heroicons/react/24/outline';
import { getActivities, createActivity, updateActivity, deleteActivity, exportActivities } from '../api/activity';
import { getEntities } from '../api/entities';
import { getAssets } from '../api/assets';
import { toArray } from '../api/utils';

const fmt = (v) => {
  const n = parseFloat(v);
  if (!n && n !== 0) return '—';
  if (n === 0) return '—';
  return new Intl.NumberFormat('en-US', {
    style: 'currency', currency: 'USD', minimumFractionDigits: 0, maximumFractionDigits: 0,
  }).format(n);
};

const fmtSigned = (v) => {
  const n = parseFloat(v);
  if (!n && n !== 0) return '—';
  if (n === 0) return '—';
  const abs = Math.abs(n);
  const formatted = new Intl.NumberFormat('en-US', {
    style: 'currency', currency: 'USD', minimumFractionDigits: 0, maximumFractionDigits: 0,
  }).format(abs);
  return n < 0 ? `(${formatted})` : formatted;
};

const emptyForm = {
  year: new Date().getFullYear(),
  entity: '',
  asset: '',
  beginning_basis: '0',
  contributions: '0',
  interest: '0',
  dividends: '0',
  capital_gains: '0',
  remaining_k1_income: '0',
  total_income: '0',
  distributions: '0',
  other_adjustments: '0',
  ending_tax_basis: '0',
  ending_gl_balance: '0',
  book_to_tax_adj: '0',
  ending_k1_capital: '0',
  k1_capital_vs_tax_diff: '0',
  excess_distribution: '0',
  negative_basis: false,
  basis_change: '0',
  notes: '',
};

export default function ActivityPage() {
  const [activities, setActivities] = useState([]);
  const [entities, setEntities] = useState([]);
  const [assets, setAssets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null); // null = add, id = edit
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  // Filters
  const [filterEntity, setFilterEntity] = useState('');
  const [filterAsset, setFilterAsset] = useState('');
  const [filterYear, setFilterYear] = useState(String(new Date().getFullYear()));

  const load = useCallback(() => {
    setLoading(true);
    const params = {};
    if (filterEntity) params.entity = filterEntity;
    if (filterAsset) params.asset = filterAsset;
    if (filterYear) params.year = filterYear;

    Promise.all([getActivities(params), getEntities(), getAssets()])
      .then(([a, e, as_]) => {
        setActivities(toArray(a));
        setEntities(toArray(e));
        setAssets(toArray(as_));
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [filterEntity, filterAsset, filterYear]);

  useEffect(() => { load(); }, [load]);

  const openAdd = () => {
    setEditing(null);
    setForm(emptyForm);
    setError('');
    setModalOpen(true);
  };

  const openEdit = (row) => {
    setEditing(row.id);
    setForm({
      year: row.year,
      entity: row.entity,
      asset: row.asset,
      beginning_basis: row.beginning_basis || '0',
      contributions: row.contributions || '0',
      interest: row.interest || '0',
      dividends: row.dividends || '0',
      capital_gains: row.capital_gains || '0',
      remaining_k1_income: row.remaining_k1_income || '0',
      total_income: row.total_income || '0',
      distributions: row.distributions || '0',
      other_adjustments: row.other_adjustments || '0',
      ending_tax_basis: row.ending_tax_basis || '0',
      ending_gl_balance: row.ending_gl_balance || '0',
      book_to_tax_adj: row.book_to_tax_adj || '0',
      ending_k1_capital: row.ending_k1_capital || '0',
      k1_capital_vs_tax_diff: row.k1_capital_vs_tax_diff || '0',
      excess_distribution: row.excess_distribution || '0',
      negative_basis: row.negative_basis || false,
      basis_change: row.basis_change || '0',
      notes: row.notes || '',
    });
    setError('');
    setModalOpen(true);
  };

  const handleSave = async () => {
    if (!form.entity || !form.asset || !form.year) {
      setError('Year, Entity, and Partnership are required.');
      return;
    }
    setSaving(true);
    setError('');
    try {
      if (editing) {
        await updateActivity(editing, form);
      } else {
        await createActivity(form);
      }
      setModalOpen(false);
      load();
    } catch (err) {
      const msg = err.response?.data?.error
        || err.response?.data?.detail
        || JSON.stringify(err.response?.data)
        || err.message;
      setError(msg);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this activity record?')) return;
    try {
      await deleteActivity(id);
      load();
    } catch (err) {
      console.error(err);
    }
  };

  const handleExport = async () => {
    try {
      const params = {};
      if (filterEntity) params.entity = filterEntity;
      if (filterAsset) params.asset = filterAsset;
      if (filterYear) params.year = filterYear;
      await exportActivities(params);
    } catch (err) {
      console.error(err);
    }
  };

  const field = (label, name, opts = {}) => {
    const disabled = opts.computed || false;
    const disabledCls = disabled ? 'bg-gray-50 text-gray-400 cursor-not-allowed' : '';
    return (
      <div className={opts.full ? 'col-span-2' : ''}>
        <label className="block text-xs font-medium text-gray-500 mb-1">
          {label}
          {opts.computed && <span className="ml-1 text-blue-400 text-[10px] font-normal">auto</span>}
        </label>
        {opts.type === 'checkbox' ? (
          <input
            type="checkbox"
            checked={form[name]}
            onChange={e => setForm(f => ({ ...f, [name]: e.target.checked }))}
            disabled={disabled}
            className="h-4 w-4 text-blue-600"
          />
        ) : opts.type === 'select' ? (
          <select
            value={form[name]}
            onChange={e => setForm(f => ({ ...f, [name]: e.target.value }))}
            disabled={disabled}
            className={`w-full border rounded px-2 py-1.5 text-sm ${disabledCls}`}
          >
            <option value="">— Select —</option>
            {opts.options.map(o => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        ) : opts.type === 'textarea' ? (
          <textarea
            value={form[name]}
            onChange={e => setForm(f => ({ ...f, [name]: e.target.value }))}
            disabled={disabled}
            className={`w-full border rounded px-2 py-1.5 text-sm ${disabledCls}`}
            rows={2}
          />
        ) : (
          <input
            type={opts.type || 'text'}
            value={form[name]}
            onChange={e => setForm(f => ({ ...f, [name]: e.target.value }))}
            disabled={disabled}
            className={`w-full border rounded px-2 py-1.5 text-sm ${disabledCls}`}
          />
        )}
      </div>
    );
  };

  // Year dropdown: current year and preceding 9 years
  const _currentYear = new Date().getFullYear();
  const years = Array.from({ length: 10 }, (_, i) => _currentYear - i);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Activity</h1>
          <p className="text-gray-500 text-sm mt-1">
            All Entities &amp; Partnerships — Tax Basis Ledger
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={handleExport}>
            <ArrowDownTrayIcon className="h-4 w-4 mr-1" /> Export
          </Button>
          <Button onClick={openAdd}>
            <PlusIcon className="h-4 w-4 mr-1" /> Add Record
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <div className="flex flex-wrap gap-4 items-end">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Entity</label>
            <select
              value={filterEntity}
              onChange={e => setFilterEntity(e.target.value)}
              className="border rounded px-2 py-1.5 text-sm min-w-[180px]"
            >
              <option value="">All Entities</option>
              {entities.map(e => (
                <option key={e.id} value={e.id}>{e.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Partnership</label>
            <select
              value={filterAsset}
              onChange={e => setFilterAsset(e.target.value)}
              className="border rounded px-2 py-1.5 text-sm min-w-[180px]"
            >
              <option value="">All Partnerships</option>
              {assets.map(a => (
                <option key={a.id} value={a.id}>{a.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Year</label>
            <select
              value={filterYear}
              onChange={e => setFilterYear(e.target.value)}
              className="border rounded px-2 py-1.5 text-sm min-w-[100px]"
            >
              <option value="">All Years</option>
              {years.map(y => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
          </div>
        </div>
      </Card>

      {/* Table */}
      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                {[
                  'Year', 'Entity', 'Partnership',
                  'Beg Basis', 'Contributions',
                  'Interest (5)', 'Dividends (6)', 'Cap Gains (8/9/10)',
                  'Remaining K-1', 'Total Income',
                  'Distributions', 'Other Adj (18-c)',
                  'Ending Tax Basis', 'Ending GL Bal',
                  'Book-to-Tax Adj', 'Ending K-1 Capital',
                  'K-1 vs Tax Diff', 'Excess Dist', 'Neg Basis?',
                  'Δ Basis', 'Notes', 'Source', '',
                ].map(h => (
                  <th key={h} className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider whitespace-nowrap">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {loading ? (
                <tr><td colSpan={23} className="px-3 py-8 text-center text-gray-400">Loading…</td></tr>
              ) : activities.length === 0 ? (
                <tr><td colSpan={23} className="px-3 py-8 text-center text-gray-400">No activity records found</td></tr>
              ) : (
                activities.map(row => (
                  <tr key={row.id} className="hover:bg-gray-50">
                    <td className="px-3 py-2 whitespace-nowrap font-medium">{row.year}</td>
                    <td className="px-3 py-2 whitespace-nowrap">{row.entity_name}</td>
                    <td className="px-3 py-2 whitespace-nowrap">{row.asset_name}</td>
                    <td className="px-3 py-2 whitespace-nowrap text-right">{fmtSigned(row.beginning_basis)}</td>
                    <td className="px-3 py-2 whitespace-nowrap text-right">{fmtSigned(row.contributions)}</td>
                    <td className="px-3 py-2 whitespace-nowrap text-right">{fmtSigned(row.interest)}</td>
                    <td className="px-3 py-2 whitespace-nowrap text-right">{fmtSigned(row.dividends)}</td>
                    <td className="px-3 py-2 whitespace-nowrap text-right">{fmtSigned(row.capital_gains)}</td>
                    <td className="px-3 py-2 whitespace-nowrap text-right">{fmtSigned(row.remaining_k1_income)}</td>
                    <td className="px-3 py-2 whitespace-nowrap text-right font-medium">{fmtSigned(row.total_income)}</td>
                    <td className="px-3 py-2 whitespace-nowrap text-right">{fmtSigned(row.distributions)}</td>
                    <td className="px-3 py-2 whitespace-nowrap text-right">{fmtSigned(row.other_adjustments)}</td>
                    <td className="px-3 py-2 whitespace-nowrap text-right font-medium">{fmtSigned(row.ending_tax_basis)}</td>
                    <td className="px-3 py-2 whitespace-nowrap text-right">{fmtSigned(row.ending_gl_balance)}</td>
                    <td className="px-3 py-2 whitespace-nowrap text-right">{fmtSigned(row.book_to_tax_adj)}</td>
                    <td className="px-3 py-2 whitespace-nowrap text-right">{fmtSigned(row.ending_k1_capital)}</td>
                    <td className="px-3 py-2 whitespace-nowrap text-right">{fmtSigned(row.k1_capital_vs_tax_diff)}</td>
                    <td className="px-3 py-2 whitespace-nowrap text-right">{fmtSigned(row.excess_distribution)}</td>
                    <td className="px-3 py-2 whitespace-nowrap text-center">
                      {row.negative_basis ? (
                        <span className="text-red-600 font-semibold">YES</span>
                      ) : '—'}
                    </td>
                    <td className="px-3 py-2 whitespace-nowrap text-right">{fmtSigned(row.basis_change)}</td>
                    <td className="px-3 py-2 whitespace-nowrap max-w-[200px] truncate" title={row.notes}>{row.notes || '—'}</td>
                    <td className="px-3 py-2 whitespace-nowrap text-xs text-gray-400">
                      {row.source_k1_document_display || 'Manual'}
                    </td>
                    <td className="px-3 py-2 whitespace-nowrap">
                      <div className="flex gap-1">
                        <button
                          onClick={() => openEdit(row)}
                          className="text-blue-600 hover:text-blue-800"
                          title="Edit"
                        >
                          <PencilIcon className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(row.id)}
                          className="text-red-500 hover:text-red-700"
                          title="Delete"
                        >
                          <TrashIcon className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Add / Edit Modal */}
      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title={editing ? 'Edit Activity Record' : 'Add Activity Record'}>
        <div className="grid grid-cols-2 gap-3 max-h-[70vh] overflow-y-auto pr-2">
          {field('Year', 'year', { type: 'number', computed: !!editing })}
          {field('Entity', 'entity', {
            type: 'select',
            options: entities.map(e => ({ value: e.id, label: e.name })),
            computed: !!editing,
          })}
          {field('Partnership (Asset)', 'asset', {
            type: 'select',
            options: assets.map(a => ({ value: a.id, label: a.name })),
            computed: !!editing,
          })}

          <div className="col-span-2 border-t pt-2 mt-1">
            <p className="text-xs font-semibold text-gray-400 uppercase">Capital In</p>
          </div>
          {field('Beginning Basis', 'beginning_basis', { type: 'number', computed: true })}
          {field('Contributions', 'contributions', { type: 'number' })}

          <div className="col-span-2 border-t pt-2 mt-1">
            <p className="text-xs font-semibold text-gray-400 uppercase">Income (K-1)</p>
          </div>
          {field('Interest (Line 5)', 'interest', { type: 'number' })}
          {field('Dividends (Line 6)', 'dividends', { type: 'number' })}
          {field('Cap Gains (Lines 8/9/10)', 'capital_gains', { type: 'number' })}
          {field('Remaining K-1 Income/Ded.', 'remaining_k1_income', { type: 'number' })}

          <div className="col-span-2 border-t pt-2 mt-1">
            <p className="text-xs font-semibold text-gray-400 uppercase">Outflows &amp; Adjustments</p>
          </div>
          {field('Distributions', 'distributions', { type: 'number' })}
          {field('Other Adj (18-c)', 'other_adjustments', { type: 'number' })}

          <div className="col-span-2 border-t pt-2 mt-1">
            <p className="text-xs font-semibold text-gray-400 uppercase">Book Values</p>
          </div>
          {field('Ending GL Balance', 'ending_gl_balance', { type: 'number' })}
          {field('Ending K-1 Capital', 'ending_k1_capital', { type: 'number' })}

          {field('Notes', 'notes', { type: 'textarea', full: true })}

          {editing && (
            <>
              <div className="col-span-2 border-t pt-2 mt-1">
                <p className="text-xs font-semibold text-blue-400 uppercase">Computed Values</p>
              </div>
              {field('Total Income', 'total_income', { type: 'number', computed: true })}
              {field('Ending Tax Basis', 'ending_tax_basis', { type: 'number', computed: true })}
              {field('Book-to-Tax Adj', 'book_to_tax_adj', { type: 'number', computed: true })}
              {field('K-1 Capital vs Tax Diff', 'k1_capital_vs_tax_diff', { type: 'number', computed: true })}
              {field('Excess Distribution', 'excess_distribution', { type: 'number', computed: true })}
              {field('Negative Basis?', 'negative_basis', { type: 'checkbox', computed: true })}
              {field('Δ Ending Basis vs Prior Year', 'basis_change', { type: 'number', computed: true })}
            </>
          )}
        </div>

        {error && <p className="text-red-600 text-sm mt-3">{error}</p>}

        <div className="flex justify-end gap-2 mt-4 pt-3 border-t">
          <Button variant="secondary" onClick={() => setModalOpen(false)}>Cancel</Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? 'Saving…' : (editing ? 'Update' : 'Create')}
          </Button>
        </div>
      </Modal>
    </div>
  );
}
