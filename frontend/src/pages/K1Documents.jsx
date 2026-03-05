import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import Badge from '../components/ui/Badge';
import Table from '../components/ui/Table';
import Modal from '../components/ui/Modal';
import { PlusIcon, TrashIcon, ArrowDownTrayIcon, EyeIcon } from '@heroicons/react/24/outline';
import { getK1Documents, deleteK1Document, downloadK1Document } from '../api/k1';
import { getEntities } from '../api/entities';
import { toArray } from '../api/utils';
import { format, parseISO } from 'date-fns';

const currentYear = new Date().getFullYear();
const taxYears = Array.from({ length: 10 }, (_, i) => currentYear - i);
const statusColors = { draft: 'yellow', confirmed: 'green' };
const formatCurrency = (v) =>
  v != null ? new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(v) : '—';

export default function K1Documents() {
  const navigate = useNavigate();
  const [documents, setDocuments] = useState([]);
  const [entities, setEntities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);

  // Filters
  const [filterYear, setFilterYear] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [filterEntity, setFilterEntity] = useState('');

  const load = () => {
    setLoading(true);
    const params = {};
    if (filterYear) params.tax_year = filterYear;
    if (filterStatus) params.status = filterStatus;
    if (filterEntity) params.entity = filterEntity;

    Promise.all([getK1Documents(params), getEntities()])
      .then(([d, e]) => {
        setDocuments(toArray(d));
        setEntities(toArray(e));
      })
      .catch(() => setError('Failed to load K-1 documents.'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [filterYear, filterStatus, filterEntity]);

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await deleteK1Document(deleteTarget.id);
      setDeleteTarget(null);
      load();
    } catch (err) {
      setError(err.response?.data?.error || 'Delete failed.');
    } finally {
      setDeleting(false);
    }
  };

  const handleDownload = async (doc) => {
    try {
      const res = await downloadK1Document(doc.id);
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', doc.original_filename || `k1_${doc.id}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      setError('Download failed.');
    }
  };

  const columns = [
    {
      header: 'Partnership',
      accessor: (row) => row.partnership_name || row.original_filename,
    },
    { header: 'Tax Year', accessor: 'tax_year' },
    {
      header: 'Status',
      accessor: (row) => (
        <Badge color={statusColors[row.status] || 'gray'}>{row.status}</Badge>
      ),
    },
    { header: 'Entity', accessor: (row) => row.entity_name || '—' },
    {
      header: 'Distributions',
      accessor: (row) => (row.total_distributions ? formatCurrency(row.total_distributions) : '—'),
    },
    {
      header: 'Uploaded',
      accessor: (row) =>
        row.uploaded_at ? format(parseISO(row.uploaded_at), 'MMM d, yyyy') : '—',
    },
    {
      header: 'Actions',
      accessor: (row) => (
        <div className="flex gap-1">
          <button
            className="p-1 text-gray-500 hover:text-indigo-600"
            title="Review"
            onClick={(e) => {
              e.stopPropagation();
              navigate(`/k1/${row.id}/review`);
            }}
          >
            <EyeIcon className="h-4 w-4" />
          </button>
          <button
            className="p-1 text-gray-500 hover:text-blue-600"
            title="Download"
            onClick={(e) => {
              e.stopPropagation();
              handleDownload(row);
            }}
          >
            <ArrowDownTrayIcon className="h-4 w-4" />
          </button>
          <button
            className="p-1 text-gray-500 hover:text-red-600"
            title="Delete"
            onClick={(e) => {
              e.stopPropagation();
              setDeleteTarget(row);
            }}
          >
            <TrashIcon className="h-4 w-4" />
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">K-1 Documents</h1>
        <Button onClick={() => navigate('/k1/upload')}>
          <PlusIcon className="h-4 w-4 mr-2" />
          Upload K-1
        </Button>
      </div>

      {error && (
        <div className="rounded-md bg-red-50 p-3">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Filters */}
      <Card>
        <div className="flex flex-wrap gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Tax Year</label>
            <select
              value={filterYear}
              onChange={(e) => setFilterYear(e.target.value)}
              className="border border-gray-300 rounded-md shadow-sm px-3 py-1.5 text-sm"
            >
              <option value="">All Years</option>
              {taxYears.map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Status</label>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="border border-gray-300 rounded-md shadow-sm px-3 py-1.5 text-sm"
            >
              <option value="">All Statuses</option>
              <option value="draft">Draft</option>
              <option value="confirmed">Confirmed</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Entity</label>
            <select
              value={filterEntity}
              onChange={(e) => setFilterEntity(e.target.value)}
              className="border border-gray-300 rounded-md shadow-sm px-3 py-1.5 text-sm"
            >
              <option value="">All Entities</option>
              {entities.map((ent) => (
                <option key={ent.id} value={ent.id}>{ent.name}</option>
              ))}
            </select>
          </div>
        </div>
      </Card>

      {/* Table */}
      <Card>
        {loading ? (
          <div className="flex items-center justify-center py-10">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
          </div>
        ) : documents.length === 0 ? (
          <div className="text-center py-10 text-gray-500">
            <p>No K-1 documents found.</p>
            <Button className="mt-3" onClick={() => navigate('/k1/upload')}>
              Upload your first K-1
            </Button>
          </div>
        ) : (
          <Table
            columns={columns}
            data={documents}
            onRowClick={(row) => navigate(`/k1/${row.id}/review`)}
          />
        )}
      </Card>

      {/* Delete confirmation */}
      <Modal
        isOpen={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        title="Delete K-1 Document"
      >
        <p className="text-sm text-gray-600 mb-4">
          Are you sure you want to delete{' '}
          <strong>{deleteTarget?.partnership_name || deleteTarget?.original_filename}</strong>?
          This cannot be undone.
        </p>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setDeleteTarget(null)}>
            Cancel
          </Button>
          <Button variant="danger" onClick={handleDelete} disabled={deleting}>
            {deleting ? 'Deleting...' : 'Delete'}
          </Button>
        </div>
      </Modal>
    </div>
  );
}
