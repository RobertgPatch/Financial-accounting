import client from './client';

// ---------------------------------------------------------------------------
// Commitments
// ---------------------------------------------------------------------------

export const getCommitments = (params = {}) =>
  client.get('/commitments/', { params });

export const getCommitment = (id) =>
  client.get(`/commitments/${id}/`);

export const createCommitment = (data) =>
  client.post('/commitments/', data);

export const updateCommitment = (id, data) =>
  client.put(`/commitments/${id}/`, data);

export const deleteCommitment = (id) =>
  client.delete(`/commitments/${id}/`);

// ---------------------------------------------------------------------------
// Capital Calls
// ---------------------------------------------------------------------------

export const getCapitalCalls = (params = {}) =>
  client.get('/capital-calls/', { params });

export const getCapitalCall = (id) =>
  client.get(`/capital-calls/${id}/`);

export const createCapitalCall = (data) =>
  client.post('/capital-calls/', data);

export const updateCapitalCall = (id, data) =>
  client.put(`/capital-calls/${id}/`, data);

export const deleteCapitalCall = (id) =>
  client.delete(`/capital-calls/${id}/`);
