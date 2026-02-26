import client from './client';

export const getBudgets = () => client.get('/budgets/');
export const getBudget = (id) => client.get(`/budgets/${id}/`);
export const createBudget = (data) => client.post('/budgets/', data);
export const updateBudget = (id, data) => client.put(`/budgets/${id}/`, data);
export const deleteBudget = (id) => client.delete(`/budgets/${id}/`);
