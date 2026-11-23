import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('shopmind_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const authService = {
  login: async (email: string, password: string) => {
    const res = await api.post('/auth/login', { email, password });
    localStorage.setItem('shopmind_token', res.data.access_token);
    localStorage.setItem('shopmind_user', JSON.stringify(res.data.user));
    return res.data;
  },
  register: async (email: string, full_name: string, password: string) => {
    const res = await api.post('/auth/register', { email, full_name, password });
    localStorage.setItem('shopmind_token', res.data.access_token);
    localStorage.setItem('shopmind_user', JSON.stringify(res.data.user));
    return res.data;
  },
  logout: () => {
    localStorage.removeItem('shopmind_token');
    localStorage.removeItem('shopmind_user');
  },
  getStoredUser: () => {
    const raw = localStorage.getItem('shopmind_user');
    return raw ? JSON.parse(raw) : null;
  },
};

export const chatService = {
  sendMessage: async (message: string, conversation_id?: string | null) => {
    const res = await api.post('/chat', { message, conversation_id });
    return res.data;
  },
  getHistory: async (conversation_id?: string) => {
    const res = await api.get('/chat/history', { params: conversation_id ? { conversation_id } : {} });
    return res.data;
  },
  deleteConversation: async (conversation_id: string) => {
    const res = await api.delete(`/chat/${conversation_id}`);
    return res.data;
  },
};

export const productService = {
  listProducts: async (params?: Record<string, any>) => {
    const res = await api.get('/products', { params });
    return res.data;
  },
  getProduct: async (productId: string) => {
    const res = await api.get(`/products/${productId}`);
    return res.data;
  },
  compareProducts: async (product_ids: string[], focus_criteria?: string[]) => {
    const res = await api.post('/products/compare', { product_ids, focus_criteria });
    return res.data;
  },
  recommendProducts: async (payload: Record<string, any>) => {
    const res = await api.post('/products/recommend', payload);
    return res.data;
  },
};

export const ragService = {
  search: async (payload: Record<string, any>) => {
    const res = await api.post('/rag/search', payload);
    return res.data;
  },
  getStatus: async () => {
    const res = await api.get('/rag/status');
    return res.data;
  },
  reindex: async () => {
    const res = await api.post('/rag/reindex');
    return res.data;
  },
};

export const evaluationService = {
  runEvaluation: async (sample_size?: number) => {
    const res = await api.post('/evaluation/run', { sample_size });
    return res.data;
  },
  getLatestResults: async () => {
    const res = await api.get('/evaluation/results');
    return res.data;
  },
  getHistory: async () => {
    const res = await api.get('/evaluation/history');
    return res.data;
  },
  getReportDownloadUrl: (runId: string, format: 'json' | 'csv') => {
    return `${API_BASE_URL}/evaluation/report/${runId}?format=${format}`;
  },
};

export const securityService = {
  getStatus: async () => {
    const res = await api.get('/security/status');
    return res.data;
  },
  getEvents: async (limit = 50) => {
    const res = await api.get('/security/events', { params: { limit } });
    return res.data;
  },
  runSecurityTests: async () => {
    const res = await api.post('/security/test');
    return res.data;
  },
};

export const adminService = {
  uploadDataset: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await api.post('/admin/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },
  addManualProduct: async (payload: Record<string, any>) => {
    const res = await api.post('/admin/products', payload);
    return res.data;
  },
  getAnalytics: async () => {
    const res = await api.get('/admin/analytics');
    return res.data;
  },
  getSystemHealth: async () => {
    const res = await api.get('/admin/system-health');
    return res.data;
  },
};
