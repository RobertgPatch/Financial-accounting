import client from './client';

// ---------------------------------------------------------------------------
// Activity Ledger
// ---------------------------------------------------------------------------

export const getActivities = (params = {}) =>
  client.get('/activities/', { params });

export const getActivity = (id) =>
  client.get(`/activities/${id}/`);

export const createActivity = (data) =>
  client.post('/activities/', data);

export const updateActivity = (id, data) =>
  client.put(`/activities/${id}/`, data);

export const deleteActivity = (id) =>
  client.delete(`/activities/${id}/`);

export const exportActivities = async (params = {}) => {
  const response = await client.post('/activity/export/', params, {
    responseType: 'blob',
  });
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;
  const today = new Date().toISOString().split('T')[0];
  link.setAttribute('download', `activity_report_${today}.xlsx`);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};
