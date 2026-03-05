import client from './client';

export const generateReport = (params) => client.post('/reports/generate/', params);
export const getDashboardSummary = () => client.get('/reports/dashboard-summary/');
export const getPortfolioByClass = (params = {}) => client.get('/reports/portfolio-by-class/', { params });
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

export const generateFmvReport = (params) => client.post('/reports/fmv/generate/', params);

export const exportFmvReport = async (params) => {
  const response = await client.post('/reports/fmv/export/', params, {
    responseType: 'blob',
  });
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;
  const today = new Date().toISOString().split('T')[0];
  link.setAttribute('download', `fmv_report_${today}.xlsx`);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};

// ---------------------------------------------------------------------------
// Portfolio Tracker APIs
// ---------------------------------------------------------------------------

export const getPortfolioSummary = (params) =>
  client.post('/portfolio/summary/', params);

export const getAssetClassSummary = (params) =>
  client.post('/portfolio/asset-class-summary/', params);

export const getInvestmentPerformance = (params) =>
  client.post('/portfolio/performance/', params);

const _downloadBlob = (blob, filename) => {
  const url = window.URL.createObjectURL(new Blob([blob]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};

export const exportPortfolioSummary = async (params) => {
  const response = await client.post('/portfolio/summary/export/', params, {
    responseType: 'blob',
  });
  const today = new Date().toISOString().split('T')[0];
  _downloadBlob(response.data, `portfolio_summary_${today}.xlsx`);
};

export const exportAssetClassSummary = async (params) => {
  const response = await client.post('/portfolio/asset-class-summary/export/', params, {
    responseType: 'blob',
  });
  const today = new Date().toISOString().split('T')[0];
  _downloadBlob(response.data, `asset_class_summary_${today}.xlsx`);
};

export const exportInvestmentPerformance = async (params) => {
  const response = await client.post('/portfolio/performance/export/', params, {
    responseType: 'blob',
  });
  const today = new Date().toISOString().split('T')[0];
  _downloadBlob(response.data, `investment_performance_${today}.xlsx`);
};
