import client from './client';

export const uploadK1Document = (file, taxYear, opts = {}) => {
  const formData = new FormData();
  formData.append('document', file);
  formData.append('tax_year', taxYear);
  if (opts.entity) formData.append('entity', opts.entity);
  if (opts.asset) formData.append('asset', opts.asset);
  if (opts.notes) formData.append('notes', opts.notes);

  return client.post('/k1-documents/upload/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: opts.onUploadProgress,
  });
};

export const getK1Documents = (params = {}) =>
  client.get('/k1-documents/', { params });

export const getK1Document = (id) =>
  client.get(`/k1-documents/${id}/`);

export const updateK1Document = (id, data) =>
  client.put(`/k1-documents/${id}/`, data);

export const confirmK1Document = (id) =>
  client.post(`/k1-documents/${id}/confirm/`);

export const deleteK1Document = (id) =>
  client.delete(`/k1-documents/${id}/`);

export const downloadK1Document = (id) =>
  client.get(`/k1-documents/${id}/download/`, { responseType: 'blob' });

export const populateK1Document = (id) =>
  client.post(`/k1-documents/${id}/populate/`);
