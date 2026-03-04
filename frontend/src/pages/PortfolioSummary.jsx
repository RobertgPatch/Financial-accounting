import React, { useState, useEffect, useCallback } from 'react';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import { getPortfolioSummary, exportPortfolioSummary } from '../api/reports';
import { getEntities } from '../api/entities';
import { toArray } from '../api/utils';

const fmtCurrency = (v) =>
  v === null || v === undefined
    ? '—'
    : new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(v);

const fmtRatio = (v) => (v === null || v === undefined ? '—' : Number(v).toFixed(2));
const fmtPct = (v) => (v === null || v === undefined ? '' : `${Number(v).toFixed(0)}%`);
const fmtIrr = (v) => (v === null || v === undefined ? '' : `${Number(v).toFixed(2)}%`);

const COLUMNS = [
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

export default function PortfolioSummary({ dateRange = {} }) {
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
      const res = await getPortfolioSummary(params);
      setReport(res.data);
    } catch {
      setError('Failed to generate portfolio summary.');
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
      await exportPortfolioSummary(params);
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

      {/* Data Table */}
      {report && !loading && (
        <Card
          title="Portfolio Summary — Entity Rollups"
          subtitle={`As of ${report.as_of_date}`}
        >
          <div className="overflow-x-auto -mx-4 sm:-mx-6">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  {COLUMNS.map((col) => (
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
                {(report.entities || []).map((row) => (
                  <tr key={row.entity_id} className="hover:bg-gray-50 transition-colors">
                    {COLUMNS.map((col) => (
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

                {/* All Entities summary row */}
                {report.all_entities && (
                  <tr className="bg-gray-50 border-t-2 border-gray-300 font-semibold">
                    <td className="px-3 py-2.5 whitespace-nowrap text-left text-gray-900">
                      All Entities
                    </td>
                    {COLUMNS.slice(1).map((col) => (
                      <td
                        key={col.key}
                        className="px-3 py-2.5 whitespace-nowrap text-right text-gray-900"
                      >
                        {col.fmt ? col.fmt(report.all_entities[col.key]) : report.all_entities[col.key]}
                      </td>
                    ))}
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {(report.entities || []).length === 0 && (
            <div className="text-center py-8 text-gray-400">
              <p className="text-lg">No entity data available</p>
              <p className="text-sm mt-1">Add commitments and capital calls to see portfolio data.</p>
            </div>
          )}
        </Card>
      )}

      {/* Metric Guide */}
      <MetricGuide />
    </div>
  );
}

function MetricGuide() {
  return (
    <Card title="Metric Guide" subtitle="PE / VC performance metrics explained">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-3 text-sm">
        <Metric
          label="DPI — Distributions to Paid-In"
          desc="Cash-on-cash return. How much cash has been returned relative to what you invested. DPI = Distributions ÷ Paid-In. A DPI of 2.0× means you've received 2× your money back in cash."
        />
        <Metric
          label="RVPI — Residual Value to Paid-In"
          desc="Unrealized value remaining. The current market value of your remaining holdings divided by what you invested. RVPI = Residual ÷ Paid-In."
        />
        <Metric
          label="TVPI — Total Value to Paid-In"
          desc="Total multiple of money. Combines realized (cash returned) and unrealized (residual). TVPI = DPI + RVPI = (Distributions + Residual) ÷ Paid-In."
        />
        <Metric
          label="IRR (XIRR) — Internal Rate of Return"
          desc="Annualized return accounting for the timing of each cash flow. Unlike TVPI, a quick 2× return has a higher IRR than a slow 2× return."
        />
        <Metric
          label="% Called"
          desc="Percentage of the original commitment that has been drawn (called) by the fund via capital calls. % Called = Paid-In ÷ Original Commitment."
        />
        <Metric
          label="Unfunded Commitment"
          desc="The remaining amount you've pledged but hasn't been called yet. Unfunded = Original Commitment − Paid-In."
        />
      </div>
    </Card>
  );
}

function Metric({ label, desc }) {
  return (
    <div>
      <dt className="font-semibold text-gray-900">{label}</dt>
      <dd className="text-gray-500 mt-0.5 leading-relaxed">{desc}</dd>
    </div>
  );
}
