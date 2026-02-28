import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import { ArrowLeftIcon } from '@heroicons/react/24/outline';
import { getEntity } from '../api/entities';
import { getOwnerships } from '../api/ownerships';
import { getEntityPerformance } from '../api/performance';
import { toArray } from '../api/utils';

export default function EntityDetail() {
  const { id } = useParams();
  const [entity, setEntity] = useState(null);
  const [ownerships, setOwnerships] = useState([]);
  const [performance, setPerformance] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [entityRes, ownershipsRes] = await Promise.all([
        getEntity(id),
        getOwnerships(),
      ]);
      setEntity(entityRes?.data || entityRes);
      const allOwnerships = toArray(ownershipsRes);
      setOwnerships(allOwnerships.filter((o) => String(o.entity) === String(id) || String(o.entity_id) === String(id)));

      getEntityPerformance(id)
        .then((res) => setPerformance(res?.data || res))
        .catch(() => setPerformance(null));
    } catch (e) {
      console.error('Failed to load entity data', e);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { loadData(); }, [loadData]);

  if (loading) return <LoadingSpinner />;
  if (!entity) return <div className="text-center py-12 text-gray-500">Entity not found.</div>;

  const periods = ['ytd', '1y', '3y', 'since_inception'];
  const metrics = performance?.metrics || {};
  const assets = performance?.assets || [];
  const hasPerf = periods.some((p) => metrics[p]?.twr !== null && metrics[p]?.twr !== undefined);

  const fmtPct = (v) => {
    if (v === null || v === undefined) return <span className="text-gray-400">—</span>;
    const num = parseFloat(v);
    const color = num >= 0 ? 'text-green-600' : 'text-red-600';
    return <span className={color}>{num >= 0 ? '+' : ''}{num.toFixed(2)}%</span>;
  };

  const fmtCurrency = (v) => {
    if (!v) return <span className="text-gray-400">—</span>;
    return '$' + parseFloat(v).toLocaleString('en-US', { minimumFractionDigits: 2 });
  };

  return (
    <div className="space-y-6">
      <Link to="/entities" className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700">
        <ArrowLeftIcon className="h-4 w-4" /> Back to Entities
      </Link>

      <Card>
        <div className="p-1">
          <h2 className="text-xl font-semibold text-gray-900">{entity.name}</h2>
          <Badge color="blue" className="mt-2">{entity.entity_type_display || entity.entity_type}</Badge>
          {entity.tax_id && <p className="text-sm text-gray-500 mt-2">Tax ID: {entity.tax_id}</p>}
        </div>
      </Card>

      {/* Portfolio Performance */}
      {hasPerf && (
        <Card title="Portfolio Performance">
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-2 pr-4 font-medium text-gray-500">Metric</th>
                  {periods.map((p) => (
                    <th key={p} className="text-right py-2 px-3 font-medium text-gray-500">
                      {metrics[p]?.label || p}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-gray-100">
                  <td className="py-2 pr-4 font-medium text-gray-700">TWR</td>
                  {periods.map((p) => (
                    <td key={p} className="text-right py-2 px-3">{fmtPct(metrics[p]?.twr)}</td>
                  ))}
                </tr>
                <tr className="border-b border-gray-100">
                  <td className="py-2 pr-4 font-medium text-gray-700">IRR</td>
                  {periods.map((p) => (
                    <td key={p} className="text-right py-2 px-3">{fmtPct(metrics[p]?.irr)}</td>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Asset Holdings */}
      <Card title="Asset Holdings" subtitle={`${assets.length || ownerships.length} assets`}>
        {assets.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-2 pr-4 font-medium text-gray-500">Asset</th>
                  <th className="text-right py-2 px-3 font-medium text-gray-500">Ownership</th>
                  <th className="text-right py-2 px-3 font-medium text-gray-500">Current FMV</th>
                  <th className="text-right py-2 px-3 font-medium text-gray-500">Entity Share</th>
                </tr>
              </thead>
              <tbody>
                {assets.map((a) => (
                  <tr key={a.asset_id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-2 pr-4">
                      <Link to={`/assets/${a.asset_id}`} className="text-blue-600 hover:text-blue-800 font-medium">
                        {a.asset_name}
                      </Link>
                    </td>
                    <td className="text-right py-2 px-3">{a.ownership_pct}%</td>
                    <td className="text-right py-2 px-3">{fmtCurrency(a.current_fmv)}</td>
                    <td className="text-right py-2 px-3 font-medium">{fmtCurrency(a.entity_share)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-gray-500 py-4 text-center">No asset ownerships found. Add ownerships to see performance data.</p>
        )}
      </Card>
    </div>
  );
}
