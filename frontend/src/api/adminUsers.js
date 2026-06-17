/**
 * adminUsers.js
 * Capa de acceso a API — Panel Administración de Usuarios
 * Endpoints: GET /admin/users · PATCH /admin/users/{id}/role
 * Sprint 2 · E02 · R-0204
 *
 * Usa la instancia axios del proyecto (axiosInstance.js) que ya maneja:
 *   - Inyección automática del Bearer token desde Zustand
 *   - Silent refresh en 401
 *   - Retry automático tras refresh
 */
import api from "./axiosInstance";

/**
 * GET /admin/users
 * @param {Object} params
 * @param {number}  params.page
 * @param {number}  params.page_size  máx 100
 * @param {string}  [params.search]   filtro nombre/email
 * @param {string}  [params.role]     'admin' | 'editor' | 'viewer' | ''
 * @returns {Promise<{ items: User[], total: number, page: number, page_size: number }>}
 */
export async function fetchUsers({
  page = 1,
  page_size = 20,
  search = "",
  role = "",
} = {}) {
  const params = new URLSearchParams({ page, page_size });
  if (search.trim()) params.set("search", search.trim());
  if (role) params.set("role", role);

  const { data } = await api.get(`/admin/users?${params}`);
  return data;
}

/**
 * PATCH /admin/users/{id}/role
 * Cambia el rol de un usuario. El backend valida "último admin".
 * @param {string} userId
 * @param {'admin'|'editor'|'viewer'} newRole
 * @returns {Promise<User>}
 */
export async function updateUserRole(userId, newRole) {
  const { data } = await api.patch(`/admin/users/${userId}/role`, {
    role: newRole,
  });
  return data;
}

/**
 * @typedef {Object} User
 * @property {string} id
 * @property {string} name
 * @property {string} username
 * @property {string} email
 * @property {'admin'|'editor'|'viewer'} role
 * @property {boolean} email_verified
 * @property {string} created_at   ISO 8601
 * @property {boolean} has_active_timer
 * @property {string|null} active_timer_task
 */