import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:5000/api';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

// ── Animals ──
export const animalAPI = {
  getAll: (type) => api.get('/animals', { params: type ? { type } : {} }),
  getById: (id) => api.get(`/animals/${id}`),
};

// ── Diagnosis ──
export const diagnosisAPI = {
  diagnose: (data) => api.post('/diagnose', data),
};

// ── Milk ──
export const milkAPI = {
  estimate: (data) => api.post('/milk-estimate', data),
};

// ── Stats ──
export const statsAPI = {
  getStats: () => api.get('/stats'),
};

// ── Vocab (symptoms, diseases, animal types for dropdowns) ──
export const vocabAPI = {
  getVocab: () => api.get('/vocab'),
};

// ── Graph ──
export const graphAPI = {
  getGraphData: (type) => api.get('/graph-data', { params: type ? { type } : {} }),
};

// ── Diseases ──
export const diseaseAPI = {
  getAll: () => api.get('/diseases'),
  getById: (name) => api.get(`/diseases/${encodeURIComponent(name)}`),
};

// ── Health check ──
export const healthAPI = {
  check: () => api.get('/health'),
};

export default api;
