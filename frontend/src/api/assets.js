import client from './client';

export const getAssets = () => client.get('/assets/');
export const getAsset = (id) => client.get(`/assets/${id}/`);
export const createAsset = (data) => client.post('/assets/', data);
export const updateAsset = (id, data) => client.put(`/assets/${id}/`, data);
export const deleteAsset = (id) => client.delete(`/assets/${id}/`);
