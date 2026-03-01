import client from './client';

export function getAssetPerformance(assetId, params = {}) {
  return client.get(`/assets/${assetId}/performance/`, { params });
}

export function getEntityPerformance(entityId, params = {}) {
  return client.get(`/entities/${entityId}/performance/`, { params });
}

export function getPerformanceSummary(params = {}) {
  return client.get('/performance/summary/', { params });
}
