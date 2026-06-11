/**
 * projects.js
 * Capa de acceso a API — Proyectos y membresía
 * Sprint 2 · E03 · R-0301 a R-0305
 *
 * Usa la instancia axios del proyecto (axiosInstance.js):
 *   - Token inyectado automáticamente por interceptor
 *   - Silent refresh en 401
 */
import api from "./axiosInstance";

// ── Proyectos ──────────────────────────────────────────────────────────────────

/**
 * GET /projects
 * Lista proyectos donde el usuario tiene membresía activa.
 * @param {{ page?: number, page_size?: number, search?: string }} params
 * @returns {Promise<{ items: Project[], total: number, page: number, page_size: number, total_pages: number }>}
 */
export async function fetchProjects({ page = 1, page_size = 20, search = "" } = {}) {
  const params = new URLSearchParams({ page, page_size });
  if (search.trim()) params.set("search", search.trim());
  const { data } = await api.get(`/projects?${params}`);
  return data;
}

/**
 * POST /projects
 * @param {{ name: string, description?: string }} body
 * @returns {Promise<Project>}
 */
export async function createProject(body) {
  const { data } = await api.post("/projects", body);
  return data;
}

/**
 * PATCH /projects/{id}
 * @param {string} projectId
 * @param {{ name?: string, description?: string }} body
 * @returns {Promise<Project>}
 */
export async function updateProject(projectId, body) {
  const { data } = await api.patch(`/projects/${projectId}`, body);
  return data;
}

/**
 * DELETE /projects/{id}
 * Soft delete — backend rechaza con 409 si hay tareas activas.
 * @param {string} projectId
 * @returns {Promise<void>}
 */
export async function deleteProject(projectId) {
  await api.delete(`/projects/${projectId}`);
}

// ── Membresía ──────────────────────────────────────────────────────────────────

/**
 * GET /projects/{id}/members
 * @param {string} projectId
 * @returns {Promise<ProjectMember[]>}
 */
export async function fetchMembers(projectId) {
  const { data } = await api.get(`/projects/${projectId}/members`);
  return data;
}

/**
 * @typedef {Object} Project
 * @property {string}      id
 * @property {string}      name
 * @property {string|null} description
 * @property {string}      owner_id
 * @property {string}      created_at     ISO 8601
 * @property {string}      updated_at     ISO 8601
 * @property {string|null} deleted_at
 * @property {number|null} member_count
 * @property {string}      [my_role]      rol del usuario autenticado en este proyecto
 *
 * @typedef {Object} ProjectMember
 * @property {string}      id
 * @property {string}      project_id
 * @property {string}      user_id
 * @property {string}      role           owner | editor | viewer
 * @property {string}      joined_at
 * @property {string|null} removed_at
 * @property {boolean}     is_active
 */