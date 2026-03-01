import client from './client';

/**
 * FMV Snapshots API client.
 */

export const listSnapshots = (params = {}) =>
  client.get('/fmv-snapshots/', { params }).then((r) => r.data);

export const getSnapshot = (id) =>
  client.get(`/fmv-snapshots/${id}/`).then((r) => r.data);

export const createSnapshot = (data) =>
  client.post('/fmv-snapshots/', data).then((r) => r.data);

export const updateSnapshot = (id, data) =>
  client.put(`/fmv-snapshots/${id}/`, data).then((r) => r.data);

export const deleteSnapshot = (id) =>
  client.delete(`/fmv-snapshots/${id}/`);

export const getAssetFmvHistory = (assetId) =>
  client.get(`/assets/${assetId}/fmv-history/`).then((r) => r.data);
