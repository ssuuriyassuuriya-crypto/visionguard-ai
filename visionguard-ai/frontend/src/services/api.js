 import axios from 'axios';

// Development keeps the standalone Vite workflow; deployed builds use same-origin FastAPI routes.
const apiBaseUrl = 'https://visionguard-ai-1.onrender.com';

const api = axios.create({
  baseURL: apiBaseUrl,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const healthCheck = () => api.get('/api/health');

export const analyzeImage = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  return api.post('/api/analyze/image', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};

export const analyzeVideo = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  return api.post('/api/analyze/video', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};

export const fetchHistory = () => api.get('/api/history');
export const fetchHistoryItem = (id) => api.get(`/api/history/${id}`);
export const deleteHistoryItem = (id) => api.delete(`/api/history/${id}`);

export const getApiUrl = (path) => {
  if (!path || path.startsWith('http')) return path;
  return `${apiBaseUrl}${path.startsWith('/') ? path : `/${path}`}`;
};

export default api;
