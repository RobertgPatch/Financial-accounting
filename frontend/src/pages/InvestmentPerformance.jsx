import React, { useState, useEffect, useCallback } from 'react';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import { getInvestmentPerformance, exportInvestmentPerformance } from '../api/reports';
import { getEntities } from '../api/entities';
import { toArray } from '../api/utils';

const fmtCurrency = (v) =>
  v === null || v === undefined
    ? '—'
    : new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(v);

const fmtRatio = (v) => (v === null || v === undefined ? '—' : Number(v).toFixed(2));
const fmtPct = (v) => (v === null || v === undefined ? '' : `${Number(v).toFixed(0)}%`);
const fmtIrr = (v) => (v === null || v === undefined ? '' : `${Number(v).toFixed(2)}%`);

const INV_COLUMNS = [
  { key: 'asset_name', label: 'Investment', align: 'left', className: 'font-medium text-gray-900' },
  { key: 'entity_name', label: 'Entity', align: 'left', className: 'text-gray-600' },
  { key: 'original_commitment', label: 'Original Commitment', fmt: fmtCurrency },
  { key: 'pct_called', label: '% Called', fmt: fmtPct },
  { key: 'unfunded_commitment', label: 'Unfunded Commitment', fmt: fmtCurrency },
  { key: 'paid_in', label: 'Paid-In (ABS)', fmt: fmtCurrency },
  { key: 'distributions', label: 'Distributions', fmt: fmtCurrency },
  { key: 'residual', label: 'Residual Value', fmt: fmtCurrency },
  { key: 'dpi', label: 'DPI', fmt: fmtRatio },
  { key: 'rvpi', label: 'RVPI', fmt: fmtRatio },
  { key: 'tvpi', label: 'TVPI', fmt: fmtRatio },
  { key: 'irr', label: 'IRR (XIRR)', fmt: fmtIrr },
];

const TOTAL_COLUMNS = [
  { key: 'entity_name', label: 'Entity', align: 'left', className: 'font-medium text-gray-900' },
  { key: 'original_commitment', label: 'Original Commitment', fmt: fmtCurrency },
  { key: 'pct_called', label: '% Called', fmt: fmtPct },
  { key: 'unfunded_commitment', label: 'Unfunded Commitment', fmt: fmtCurrency },
  { key: 'paid_in', label: 'Paid-In (ABS)', fmt: fmtCurrency },
  { key: 'distributions', label: 'Distributions', fmt: fmtCurrency },
  { key: 'residual', label: 'Residual Value', fmt: fmtCurrency },
  { key: 'dpi', label: 'DPI', fmt: fmtRatio },
  { key: 'rvpi', label: 'RVPI', fmt: fmtRatio },
  { key: 'tvpi', label: 'TVPI', fmt: fmtRatio },
  { key: 'irr', label: 'IRR (XIRR)', fmt: fmtIrr },
];

export default function InvestmentPerformance({ dateRange = {} }) {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState('');
  const [entities, setEntities] = useState([]);
  const [selectedEntities, setSelectedEntities] = useState([]);

  useEffect(() => {
    getEntities().then((res) => setEntities(toArray(res))).catch(() => {});
  }, []);

  const handleGenerate = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const params = { ...dateRange };
      if (selectedEntities.length > 0) params.entity_ids = selectedEntities.join(',');
      const res = await getInvestmentPerformance(params);
      setReport(res.data);
    } catch {
      setError('Failed to generate investment performance report.');
      setReport(null);
    } finally {
      setLoading(false);
    }
  }, [selectedEntities, dateRange]);

  useEffect(() => { handleGenerate(); }, [handleGenerate]);

  const handleExport = async () => {
    setExporting(true);
    try {
      const params = { ...dateRange };
      if (selectedEntities.length > 0) params.entity_ids = selectedEntities.join(',');
      await exportInvestmentPerformance(params);
    } catch { alert('Export failed.'); }
    finally { setExporting(false); }
  };

  const toggleEntity = (id) =>
    setSelectedEntities((prev) =>
      prev.includes(id) ? prev.filter((e) => e !== id) : [...prev, id],
    );

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        {entities.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {entities.map((e) => (
              <button
                key={e.id}
                onClick={() => toggleEntity(e.id)}
                className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
                  selectedEntities.includes(e.id)
                    ? 'bg-blue-100 border-blue-300 text-blue-700'
                    : 'bg-white border-gray-300 text-gray-600 hover:bg-gray-50'
                }`}
              >
                {e.name}
              </button>
            ))}
          </div>
        )}
        <div className="flex gap-2 ml-auto">
          <Button size="sm" onClick={handleGenerate} disabled={loading}>
            {loading ? 'Loading…' : 'Refresh'}
          </Button>
          {report && (
            <Button size="sm" variant="secondary" onClick={handleExport} disabled={exporting}>
              {exporting ? 'Exporting…' : 'Export Excel'}
            </Button>
          )}
        </div>
      </div>

      {error && <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-2 rounded-lg text-sm">{error}</div>}
      {loading && <LoadingSpinner />}

      {/* Individual Investments Table */}
      {report && !loading && (
        <>
          <Card
            title="Investment-Level Performance"
            subtitle={`As of ${report.as_of_date}`}
          >
            <div className="overflow-x-auto -mx-4 sm:-mx-6">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200">
                    {INV_COLUMNS.map((col) => (
                      <th
                        key={col.key}
                        className={`px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider whitespace-nowrap ${
                          col.align === 'left' ? 'text-left' : 'text-right'
                        }`}
                      >
                        {col.label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {(report.investments || []).map((row, idx) => (
                    <tr key={`${row.entity_id}-${row.asset_id}-${idx}`} className="hover:bg-gray-50 transition-colors">
                      {INV_COLUMNS.map((col) => (
                        <td
                          key={col.key}
                          className={`px-3 py-2.5 whitespace-nowrap ${
                            col.align === 'left' ? 'text-left' : 'text-right'
                          } ${col.className || 'text-gray-700'}`}
                        >
                          {col.fmt ? col.fmt(row[col.key]) : row[col.key]}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {(report.investments || []).length === 0 && (
              <div className="text-center py-8 text-gray-400">
                <p className="text-lg">No investment data available</p>
                <p className="text-sm mt-1">Add commitments and capital calls to see investment performance.</p>
              </div>
            )}
          </Card>

          {/* Entity Totals Table */}
          {(report.entity_totals || []).length > 0 && (
            <Card
              title="Entity Totals"
              subtitle="Aggregated performance by entity"
            >
              <div className="overflow-x-auto -mx-4 sm:-mx-6">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-200">
                      {TOTAL_COLUMNS.map((col) => (
                        <th
                          key={col.key}
                          className={`px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider whitespace-nowrap ${
                            col.align === 'left' ? 'text-left' : 'text-right'
                          }`}
                        >
                          {col.label}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {report.entity_totals.map((row) => (
                      <tr key={row.entity_id} className="hover:bg-gray-50 transition-colors">
                        {TOTAL_COLUMNS.map((col) => (
                          <td
                            key={col.key}
                            className={`px-3 py-2.5 whitespace-nowrap ${
                              col.align === 'left' ? 'text-left' : 'text-right'
                            } ${col.className || 'text-gray-700'}`}
                          >
                            {col.fmt ? col.fmt(row[col.key]) : row[col.key]}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
