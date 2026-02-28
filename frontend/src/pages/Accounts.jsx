import React, { useState, useEffect } from 'react';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import Table from '../components/ui/Table';
import Badge from '../components/ui/Badge';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import PlaidLink from '../components/plaid/PlaidLink';
import {
  ArrowPathIcon,
  TrashIcon,
  LinkIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { getItems, getItemAccounts, syncItem, mapAsset, deleteItem } from '../api/plaid';
import { getAssets } from '../api/assets';
import { toArray } from '../api/utils';
import { format, parseISO } from 'date-fns';

export default function Accounts() {
  const [items, setItems] = useState([]);
  const [accounts, setAccounts] = useState({});
  const [assets, setAssets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState({});
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  const loadData = async () => {
    setLoading(true);
    try {
      const [itemsData, assetsData] = await Promise.all([
        getItems(),
        getAssets(),
      ]);
      const itemsList = Array.isArray(itemsData) ? itemsData : itemsData?.results || [];
      setItems(itemsList);
      setAssets(toArray(assetsData));

      // Load accounts for each item
      const acctMap = {};
      await Promise.all(
        itemsList.map(async (item) => {
          try {
            const data = await getItemAccounts(item.id);
            acctMap[item.id] = Array.isArray(data) ? data : data?.results || [];
          } catch {
            acctMap[item.id] = [];
          }
        })
      );
      setAccounts(acctMap);
    } catch (e) {
      console.error('Failed to load accounts', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  const handleLinkSuccess = (result) => {
    setSuccessMsg(`Successfully linked ${result.institution_name || 'account'}`);
    setError('');
    loadData();
    setTimeout(() => setSuccessMsg(''), 5000);
  };

  const handleLinkError = (errMsg) => {
    setError(typeof errMsg === 'string' ? errMsg : 'Failed to link account');
    setSuccessMsg('');
  };

  const handleSync = async (itemId) => {
    setSyncing((s) => ({ ...s, [itemId]: true }));
    try {
      const result = await syncItem(itemId);
      setSuccessMsg(`Synced ${result.synced_accounts} account(s). ${result.fmv_snapshots_created} FMV snapshot(s) created.`);
      setError('');
      loadData();
    } catch (e) {
      setError(e.response?.data?.error || 'Sync failed');
    } finally {
      setSyncing((s) => ({ ...s, [itemId]: false }));
      setTimeout(() => setSuccessMsg(''), 5000);
    }
  };

  const handleDelete = async (itemId) => {
    if (!window.confirm('Unlink this institution? FMV snapshots will be preserved.')) return;
    try {
      await deleteItem(itemId);
      loadData();
    } catch {
      setError('Failed to delete');
    }
  };

  const handleMapAsset = async (accountId, assetId) => {
    try {
      await mapAsset(accountId, assetId);
      setSuccessMsg('Asset mapped successfully');
      loadData();
      setTimeout(() => setSuccessMsg(''), 3000);
    } catch (e) {
      setError(e.response?.data?.error || 'Failed to map asset');
    }
  };

  const statusColors = {
    active: 'green',
    error: 'red',
    needs_relink: 'yellow',
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div className="space-y-6">
      <Card
        title="Linked Accounts"
        subtitle={`${items.length} institution(s)`}
        action={
          <PlaidLink
            onSuccess={handleLinkSuccess}
            onError={handleLinkError}
            buttonText="Link Account"
          />
        }
      >
        {error && (
          <div className="text-red-600 text-sm bg-red-50 p-3 rounded-lg mb-4 flex items-center gap-2">
            <ExclamationTriangleIcon className="h-5 w-5 flex-shrink-0" /> {error}
          </div>
        )}
        {successMsg && (
          <div className="text-green-600 text-sm bg-green-50 p-3 rounded-lg mb-4">{successMsg}</div>
        )}

        {items.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <LinkIcon className="h-12 w-12 mx-auto mb-3 text-gray-300" />
            <p className="text-lg font-medium">No linked accounts</p>
            <p className="text-sm mt-1">Click "Link Account" to connect a bank or brokerage via Plaid.</p>
          </div>
        ) : (
          <div className="space-y-6">
            {items.map((item) => (
              <div key={item.id} className="border rounded-lg p-4">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
                  <div>
                    <h3 className="font-medium text-gray-900">{item.institution_name || 'Unknown Institution'}</h3>
                    <div className="flex items-center gap-2 mt-1">
                      <Badge color={statusColors[item.status] || 'gray'}>{item.status}</Badge>
                      {item.last_synced && (
                        <span className="text-xs text-gray-500">
                          Last synced: {format(parseISO(item.last_synced), 'MMM dd, yyyy h:mm a')}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => handleSync(item.id)}
                      disabled={syncing[item.id]}
                    >
                      <ArrowPathIcon className={`h-4 w-4 ${syncing[item.id] ? 'animate-spin' : ''}`} />
                      {syncing[item.id] ? 'Syncing...' : 'Sync'}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDelete(item.id)}
                      className="text-red-500 hover:text-red-700"
                    >
                      <TrashIcon className="h-4 w-4" />
                    </Button>
                  </div>
                </div>

                {/* Accounts table */}
                <Table
                  columns={[
                    {
                      header: 'Account', key: 'name',
                      render: (r) => (
                        <div>
                          <span className="font-medium">{r.name}</span>
                          {r.mask && <span className="text-gray-400 ml-1">···{r.mask}</span>}
                        </div>
                      ),
                    },
                    {
                      header: 'Type', key: 'type',
                      render: (r) => <Badge color="gray">{r.subtype || r.type}</Badge>,
                    },
                    {
                      header: 'Balance', key: 'current_balance',
                      render: (r) => r.current_balance != null
                        ? <span className="font-medium">${parseFloat(r.current_balance).toLocaleString('en-US', { minimumFractionDigits: 2 })}</span>
                        : <span className="text-gray-400">—</span>,
                    },
                    {
                      header: 'Mapped Asset', key: 'asset',
                      render: (r) => (
                        <select
                          className="border border-gray-300 rounded px-2 py-1 text-sm w-full max-w-xs"
                          value={r.asset || ''}
                          onChange={(e) => {
                            const val = e.target.value;
                            if (val) handleMapAsset(r.id, Number(val));
                          }}
                        >
                          <option value="">— Select Asset —</option>
                          {assets.map((a) => (
                            <option key={a.id} value={a.id}>{a.name}</option>
                          ))}
                        </select>
                      ),
                    },
                  ]}
                  data={accounts[item.id] || []}
                  emptyMessage="No accounts found"
                />
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
