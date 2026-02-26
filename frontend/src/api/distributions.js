import client from './client';

export const getDistributions = () => client.get('/distributions/');
export const getDistribution = (id) => client.get(`/distributions/${id}/`);
export const createDistribution = (data) => client.post('/distributions/', data);
export const updateDistribution = (id, data) => client.put(`/distributions/${id}/`, data);
export const deleteDistribution = (id) => client.delete(`/distributions/${id}/`);
