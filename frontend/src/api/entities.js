import client from './client';

export const getEntities = () => client.get('/entities/');
export const getEntity = (id) => client.get(`/entities/${id}/`);
export const createEntity = (data) => client.post('/entities/', data);
export const updateEntity = (id, data) => client.put(`/entities/${id}/`, data);
export const deleteEntity = (id) => client.delete(`/entities/${id}/`);
