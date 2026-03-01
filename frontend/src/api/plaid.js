import client from './client';

const PLAID_BASE = '/plaid';

/**
 * Plaid API client.
 */

export const createLinkToken = () =>
  client.post(`${PLAID_BASE}/create-link-token/`).then((r) => r.data);

export const exchangeToken = (data) =>
  client.post(`${PLAID_BASE}/exchange-token/`, data).then((r) => r.data);

export const getItems = () =>
  client.get(`${PLAID_BASE}/items/`).then((r) => r.data);

export const getItemAccounts = (itemId) =>
  client.get(`${PLAID_BASE}/items/${itemId}/accounts/`).then((r) => r.data);

export const syncItem = (itemId) =>
  client.post(`${PLAID_BASE}/items/${itemId}/sync/`).then((r) => r.data);

export const mapAsset = (accountId, assetId) =>
  client.patch(`${PLAID_BASE}/accounts/${accountId}/map-asset/`, { asset_id: assetId }).then((r) => r.data);

export const deleteItem = (itemId) =>
  client.delete(`${PLAID_BASE}/items/${itemId}/`);
