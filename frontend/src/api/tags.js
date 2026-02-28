import client from './client';

export const getTags = () => client.get('/tags/').then((r) => r.data);
export const createTag = (data) => client.post('/tags/', data).then((r) => r.data);
export const updateTag = (id, data) => client.patch(`/tags/${id}/`, data).then((r) => r.data);
export const deleteTag = (id) => client.delete(`/tags/${id}/`);
export const setAssetTags = (assetId, tagIds) =>
  client.post(`/assets/${assetId}/tags/`, { tag_ids: tagIds }).then((r) => r.data);
