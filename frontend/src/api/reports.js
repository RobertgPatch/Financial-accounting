import client from './client';

export const generateReport = (params) => client.post('/reports/generate/', params);
export const getDashboardSummary = () => client.get('/reports/dashboard-summary/');
export const exportReport = async (params) => {
  const response = await client.post('/reports/export/', params, {
    responseType: 'blob',
  });
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', `distribution_report.xlsx`);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};
