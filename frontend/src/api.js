import axios from 'axios';

const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api';
const api = axios.create({ baseURL });

export const tokens = {
  get access() { return localStorage.getItem('access_token'); },
  get refresh() { return localStorage.getItem('refresh_token'); },
  set(access, refresh) {
    if (access) localStorage.setItem('access_token', access);
    if (refresh) localStorage.setItem('refresh_token', refresh);
  },
  clear() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  },
};

api.interceptors.request.use((config) => {
  if (tokens.access) config.headers.Authorization = `Bearer ${tokens.access}`;
  return config;
});

// One shared refresh request, so several 401s at once do not trigger several refreshes.
let refreshing = null;

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    const isAuthCall = original?.url?.includes('/auth/login/') || original?.url?.includes('/auth/refresh/');
    if (error.response?.status === 401 && tokens.refresh && original && !original._retried && !isAuthCall) {
      original._retried = true; // never retry twice: avoids infinite refresh loops
      try {
        if (!refreshing) {
          refreshing = axios
            .post(`${baseURL}/auth/refresh/`, { refresh: tokens.refresh })
            .then((res) => { tokens.set(res.data.access, res.data.refresh); return res.data.access; })
            .finally(() => { refreshing = null; });
        }
        const access = await refreshing;
        original.headers.Authorization = `Bearer ${access}`;
        return api(original);
      } catch {
        tokens.clear();
        window.dispatchEvent(new Event('auth:expired'));
      }
    }
    return Promise.reject(error);
  },
);

export default api;
