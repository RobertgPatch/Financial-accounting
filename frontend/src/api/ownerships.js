import client from './client';

export const getOwnerships = () => client.get('/ownerships/');
export const getOwnership = (id) => client.get(`/ownerships/${id}/`);
export const createOwnership = (data) => client.post('/ownerships/', data);
export const updateOwnership = (id, data) => client.put(`/ownerships/${id}/`, data);
export const deleteOwnership = (id) => client.delete(`/ownerships/${id}/`);
