/**
 * Cliente HTTP base — axios con interceptores (R-0103).
 * Request: agrega Bearer token desde Zustand.
 * Response: 401 → silent refresh → reintento. Máx 1 reintento.
 * credentials:include solo en /auth/refresh para enviar cookie HttpOnly.
 */
import axios from "axios";
 
const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";
 
export const api = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 10000,
});
 
api.interceptors.request.use((config) => {
  const token = window.__authStore?.getState?.().accessToken;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});
 
let isRefreshing = false;
let failedQueue = [];
 
const processQueue = (error, token = null) => {
  failedQueue.forEach((p) => (error ? p.reject(error) : p.resolve(token)));
  failedQueue = [];
};
 
api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const orig = error.config;
    if (
      error.response?.status === 401 &&
      !orig._retry &&
      !orig.url?.includes("/auth/refresh")
    ) {
      if (isRefreshing) {
        return new Promise((resolve, reject) =>
          failedQueue.push({ resolve, reject })
        ).then((token) => {
          orig.headers.Authorization = `Bearer ${token}`;
          return api(orig);
        });
      }
      orig._retry = true;
      isRefreshing = true;
      try {
        const res = await axios.post(
          `${BASE_URL}/auth/refresh`,
          {},
          { withCredentials: true }
        );
        const { access_token } = res.data;
        window.__authStore?.getState?.().setAccessToken(access_token);
        processQueue(null, access_token);
        orig.headers.Authorization = `Bearer ${access_token}`;
        return api(orig);
      } catch (err) {
        processQueue(err, null);
        window.__authStore?.getState?.().clearAuth();
        window.location.href = "/login";
        return Promise.reject(err);
      } finally {
        isRefreshing = false;
      }
    }
    return Promise.reject(error);
  }
);
 
export default api;
