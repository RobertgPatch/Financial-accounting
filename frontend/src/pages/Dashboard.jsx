import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts';
import Card from '../components/ui/Card';
import Table from '../components/ui/Table';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import { getEntities } from '../api/entities';
import { getAssets } from '../api/assets';
import { getDistributions } from '../api/distributions';
import { format, parseISO } from 'date-fns';

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899'];

const formatCurrency = (v) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(v || 0);

export default function Dashboard() {
  const [entities, setEntities] = useState([]);
  const [assets, setAssets] = useState([]);
  const [distributions, setDistributions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([getEntities(), getAssets(), getDistributions()])
      .then(([e, a, d]) => {
        setEntities(e.data.results || e.data || []);
        setAssets(a.data.results || a.data || []);
        setDistributions(d.data.results || d.data || []);
      })
      .catch((err) => {
        console.error('Dashboard data fetch failed:', err);
        setError('Unable to load dashboard data. The server may be starting up — please try again in a moment.');
      })
      .finally(() => setLoading(false));
  }, []);

  const currentYear = new Date().getFullYear();
  const yearDists = distributions.filter(d => new Date(d.distribution_date).getFullYear() === currentYear);
  const totalAmount = yearDists.reduce((sum, d) => sum + parseFloat(d.total_amount || 0), 0);

  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const monthlyData = months.map((month, i) => ({
    month,
    amount: yearDists
      .filter(d => new Date(d.distribution_date).getMonth() === i)
      .reduce((sum, d) => sum + parseFloat(d.total_amount || 0), 0)
  }));

  const entityMap = {};
  distributions.forEach(dist => {
    (dist.allocations || []).forEach(alloc => {
      const name = alloc.entity_name || alloc.entity || 'Unknown';
      entityMap[name] = (entityMap[name] || 0) + parseFloat(alloc.amount || 0);
    });
  });
  const pieData = Object.entries(entityMap).map(([name, value]) => ({ name, value })).sort((a,b) => b.value - a.value).slice(0, 6);

  const recentColumns = [
    { header: 'Date', key: 'distribution_date', render: r => r.distribution_date ? format(parseISO(r.distribution_date), 'MMM dd, yyyy') : '-' },
    { header: 'Asset', key: 'asset_name', render: r => r.asset_name || r.asset || '-' },
    { header: 'Type', key: 'distribution_type' },
    { header: 'Amount', key: 'total_amount', render: r => <span className="font-semibold text-emerald-600">{formatCurrency(r.total_amount)}</span> },
  ];

  if (loading) return <LoadingSpinner className="min-h-96" size="lg" />;

  if (error) return (
    <div className="flex flex-col items-center justify-center min-h-96 text-center p-6">
      <p className="text-red-600 text-lg font-medium mb-4">{error}</p>
      <button onClick={() => window.location.reload()} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
        Retry
      </button>
    </div>
  );

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Total Entities', value: entities.length, color: 'blue', icon: '🏢' },
          { label: 'Total Assets', value: assets.length, color: 'purple', icon: '💼' },
          { label: 'Distributions (YTD)', value: yearDists.length, color: 'orange', icon: '📊' },
          { label: 'Total Distributed (YTD)', value: formatCurrency(totalAmount), color: 'green', icon: '💰' },
        ].map(({ label, value, icon }) => (
          <div key={label} className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
            <div className="flex items-center gap-3 mb-2">
              <span className="text-2xl">{icon}</span>
              <span className="text-sm font-medium text-gray-500">{label}</span>
            </div>
            <p className="text-2xl font-bold text-gray-900">{value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Monthly Distributions" subtitle={`${currentYear}`}>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={monthlyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="month" tick={{ fontSize: 12 }} />
              <YAxis tickFormatter={v => `$${(v/1000).toFixed(0)}k`} tick={{ fontSize: 12 }} />
              <Tooltip formatter={v => formatCurrency(v)} />
              <Bar dataKey="amount" fill="#3B82F6" radius={[4,4,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card title="Distribution by Entity">
          {pieData.length === 0 ? (
            <div className="flex items-center justify-center h-60 text-gray-400">No allocation data available</div>
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label={({ name, percent }) => `${name} (${(percent*100).toFixed(0)}%)`} labelLine={false}>
                  {pieData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip formatter={v => formatCurrency(v)} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          )}
        </Card>
      </div>

      <Card title="Recent Distributions" subtitle="Last 5 distributions">
        <Table columns={recentColumns} data={distributions.slice(0, 5)} loading={false} emptyMessage="No distributions yet" />
      </Card>
    </div>
  );
}
