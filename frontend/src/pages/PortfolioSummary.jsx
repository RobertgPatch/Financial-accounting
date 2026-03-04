import React, { useState, useEffect, useCallback } from 'react';
import {
  Paper, Typography, Table as MuiTable, TableBody, TableCell, TableContainer,
  TableHead, TableRow, Alert, Box,
} from '@mui/material';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import { getPortfolioSummary, exportPortfolioSummary } from '../api/reports';
import { getEntities } from '../api/entities';
import { toArray } from '../api/utils';

const formatCurrency = (v) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(v || 0);

const fmtRatio = (v) => (v === null || v === undefined ? '—' : Number(v).toFixed(2));
const fmtPct = (v) => (v === null || v === undefined ? '—' : `${Number(v).toFixed(2)}%`);
const fmtIrr = (v) => (v === null || v === undefined ? 'N/A' : `${Number(v).toFixed(2)}%`);

export default function PortfolioSummary() {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState('');
  const [entities, setEntities] = useState([]);
  const [selectedEntities, setSelectedEntities] = useState([]);

  useEffect(() => {
    getEntities()
      .then((res) => setEntities(toArray(res)))
      .catch(() => {});
  }, []);

  const handleGenerate = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const params = {};
      if (selectedEntities.length > 0) params.entity_ids = selectedEntities.join(',');
      const res = await getPortfolioSummary(params);
      setReport(res.data);
    } catch {
      setError('Failed to generate portfolio summary.');
      setReport(null);
    } finally {
      setLoading(false);
    }
  }, [selectedEntities]);

  // Auto-generate on mount
  useEffect(() => {
    handleGenerate();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleExport = async () => {
    setExporting(true);
    try {
      const params = {};
      if (selectedEntities.length > 0) params.entity_ids = selectedEntities.join(',');
      await exportPortfolioSummary(params);
    } catch {
      alert('Export failed.');
    } finally {
      setExporting(false);
    }
  };

  const toggleEntity = (id) => {
    setSelectedEntities((prev) =>
      prev.includes(id) ? prev.filter((e) => e !== id) : [...prev, id],
    );
  };

  const COLUMNS = [
    { key: 'entity_name', label: 'Entity', align: 'left' },
    { key: 'original_commitment', label: 'Original Commitment', fmt: formatCurrency },
    { key: 'pct_called', label: '% Called', fmt: fmtPct },
    { key: 'unfunded_commitment', label: 'Unfunded', fmt: formatCurrency },
    { key: 'paid_in', label: 'Paid-In', fmt: formatCurrency },
    { key: 'distributions', label: 'Distributions', fmt: formatCurrency },
    { key: 'residual', label: 'Residual Value', fmt: formatCurrency },
    { key: 'dpi', label: 'DPI', fmt: fmtRatio },
    { key: 'rvpi', label: 'RVPI', fmt: fmtRatio },
    { key: 'tvpi', label: 'TVPI', fmt: fmtRatio },
    { key: 'irr', label: 'IRR', fmt: fmtIrr },
  ];

  return (
    <div className="space-y-6">
      {/* Filters */}
      <Card title="Filters" subtitle="Optionally filter by entity">
        <div className="space-y-4">
          {entities.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Entities</label>
              <div className="flex flex-wrap gap-2">
                {entities.map((e) => (
                  <button
                    key={e.id}
                    onClick={() => toggleEntity(e.id)}
                    className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
                      selectedEntities.includes(e.id)
                        ? 'bg-blue-100 border-blue-300 text-blue-700'
                        : 'bg-white border-gray-300 text-gray-600 hover:bg-gray-50'
                    }`}
                  >
                    {e.name}
                  </button>
                ))}
              </div>
            </div>
          )}
          <div className="flex gap-3">
            <Button onClick={handleGenerate} disabled={loading}>
              {loading ? 'Loading...' : 'Refresh'}
            </Button>
            {report && (
              <Button variant="secondary" onClick={handleExport} disabled={exporting}>
                {exporting ? 'Exporting...' : 'Export to Excel'}
              </Button>
            )}
          </div>
        </div>
      </Card>

      {error && <Alert severity="error">{error}</Alert>}
      {loading && <LoadingSpinner />}

      {/* Data Table */}
      {report && !loading && (
        <Card
          title="Portfolio Summary — Entity Rollups"
          subtitle={`As of ${report.as_of_date}`}
        >
          <TableContainer component={Paper} elevation={0}>
            <MuiTable size="small">
              <TableHead>
                <TableRow>
                  {COLUMNS.map((col) => (
                    <TableCell
                      key={col.key}
                      align={col.align || 'right'}
                      sx={{ fontWeight: 700, whiteSpace: 'nowrap', fontSize: '0.75rem' }}
                    >
                      {col.label}
                    </TableCell>
                  ))}
                </TableRow>
              </TableHead>
              <TableBody>
                {(report.entities || []).map((row) => (
                  <TableRow key={row.entity_id} hover>
                    {COLUMNS.map((col) => (
                      <TableCell
                        key={col.key}
                        align={col.align || 'right'}
                        sx={{ whiteSpace: 'nowrap', fontSize: '0.8rem' }}
                      >
                        {col.fmt ? col.fmt(row[col.key]) : row[col.key]}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}

                {/* All-Entities Total Row */}
                {report.all_entities && (
                  <TableRow sx={{ backgroundColor: '#F8FAFC' }}>
                    <TableCell
                      align="left"
                      sx={{ fontWeight: 700, fontSize: '0.8rem' }}
                    >
                      All Entities
                    </TableCell>
                    {COLUMNS.slice(1).map((col) => (
                      <TableCell
                        key={col.key}
                        align="right"
                        sx={{ fontWeight: 700, whiteSpace: 'nowrap', fontSize: '0.8rem' }}
                      >
                        {col.fmt
                          ? col.fmt(report.all_entities[col.key])
                          : report.all_entities[col.key]}
                      </TableCell>
                    ))}
                  </TableRow>
                )}
              </TableBody>
            </MuiTable>
          </TableContainer>

          {(report.entities || []).length === 0 && (
            <div className="text-center py-8 text-gray-400">
              <p className="text-lg">No entity data available</p>
              <p className="text-sm mt-1">Add commitments and capital calls to see portfolio data.</p>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
